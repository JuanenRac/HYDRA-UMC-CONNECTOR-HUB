# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_simulation_bench.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Simulation bench: the real health probes of the hub against simulated machines that misbehave.

The simulated machines are small TCP and HTTP servers on loopback that speak (or fail to speak) the protocol a manifest declares: a broker, an OPC UA server,
a vehicle that streams MAVLink, a controller with a declared exchange, a web endpoint. No hardware is involved. The bench proves that every way a machine can
fail (silence, a reset, a half answer, noise, a wrong checksum, a refusal, a slow answer, an endless stream, a link that flaps) ends in an UNHEALTHY result with
a reason, never in an exception and never in a healthy result, and that a fleet of 40 machines with a fixed seed is classified exactly as expected."""
from __future__ import annotations

import random
import socket
import struct
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from hydra_umc_connector_hub.health_probe import (
    HealthResult,
    Place,
    ProbeCache,
    _x25,
    gcs_heartbeat_frame,
    run_health_check,
)

SEED = 20260101
FAST = 0.4  # seconds a simulated silence costs


def manifest(check: dict, name: str = "sim") -> dict:
    return {"adapterId": name, "timeoutMs": int(FAST * 1000), "healthCheck": check}


def heartbeat_v1() -> bytes:
    body = bytes([9, 1, 1, 1, 0]) + bytes(9)
    return bytes([254]) + body + struct.pack("<H", _x25(body + bytes([50])))


def heartbeat_v2() -> bytes:
    body = bytes([9, 0, 0, 1, 1, 1, 0, 0, 0]) + bytes([2, 3, 4, 5, 0, 0, 3, 3, 3])
    return bytes([253]) + body + struct.pack("<H", _x25(body + bytes([50])))


class SimulatedMachine:
    """A TCP server whose behaviour for each connection is `script(conn)`; it is closed with the machine."""

    def __init__(self, script: Callable[[socket.socket], None]) -> None:
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(16)
        self.port = self._listener.getsockname()[1]
        self.connections = 0
        self._script = script
        self._open: list[socket.socket] = []
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        while True:
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            self.connections += 1
            self._open.append(conn)
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(3)
            self._script(conn)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def place(self, **extra: object) -> Place:
        return Place("127.0.0.1", self.port, **extra)  # type: ignore[arg-type]

    def close(self) -> None:
        self._listener.close()
        for conn in self._open:
            try:
                conn.close()
            except OSError:
                pass


def after_request(reply: Callable[[bytes], bytes | None]) -> Callable[[socket.socket], None]:
    def script(conn: socket.socket) -> None:
        data = conn.recv(1024)
        answer = reply(data)
        if answer:
            conn.sendall(answer)
            time.sleep(0.05)

    return script


def stream(frames: list[bytes], gap_s: float = 0.0, chunk: int = 0) -> Callable[[socket.socket], None]:
    def script(conn: socket.socket) -> None:
        for frame in frames:
            parts = [frame[i : i + chunk] for i in range(0, len(frame), chunk)] if chunk else [frame]
            for part in parts:
                conn.sendall(part)
                if gap_s:
                    time.sleep(gap_s)
        time.sleep(0.1)

    return script


def silent(conn: socket.socket) -> None:
    time.sleep(1.5)


def reset_at_once(conn: socket.socket) -> None:
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))  # close() sends a RST


CONNACK_OK = bytes([0x20, 0x02, 0x00, 0x00])


class BenchCase(unittest.TestCase):
    def machine(self, script: Callable[[socket.socket], None]) -> SimulatedMachine:
        simulated = SimulatedMachine(script)
        self.addCleanup(simulated.close)
        return simulated

    def check(self, check: dict, place: Place, **kwargs: object) -> HealthResult:
        started = time.monotonic()
        result = run_health_check(manifest(check), place, **kwargs)  # type: ignore[arg-type]
        self.assertLess(time.monotonic() - started, 5.0, "a failing machine must never hold the probe beyond its timeout")
        self.assertTrue(result.detail)
        return result


class MqttScenarios(BenchCase):
    PING = {"type": "mqtt-ping"}

    def test_a_broker_that_accepts(self) -> None:
        result = self.check(self.PING, self.machine(after_request(lambda _: CONNACK_OK)).place())
        self.assertTrue(result.healthy and result.checked == "mqtt-connack")

    def test_every_refusal_code_is_unhealthy_and_named(self) -> None:
        for code in range(1, 6):
            broker = self.machine(after_request(lambda _, c=code: bytes([0x20, 0x02, 0x00, c])))
            result = self.check(self.PING, broker.place())
            self.assertFalse(result.healthy, code)
            self.assertIn(str(code), result.detail)

    def test_half_answers_noise_silence_and_resets_are_unhealthy(self) -> None:
        scripts = {
            "one byte": after_request(lambda _: b"\x20"),
            "truncated": after_request(lambda _: CONNACK_OK[:3]),
            "noise": after_request(lambda _: b"HTTP/1.1 400 Bad Request\r\n\r\n"),
            "wrong packet": after_request(lambda _: bytes([0x30, 0x02, 0x00, 0x00])),
            "silence": silent,
            "closes without a word": lambda conn: None,
            "reset": reset_at_once,
        }
        for name, script in scripts.items():
            result = self.check(self.PING, self.machine(script).place())
            self.assertFalse(result.healthy, name)
            self.assertTrue(result.supported, name)

    def test_the_active_probe_wants_the_pingresp(self) -> None:
        def broker(conn: socket.socket) -> None:
            conn.recv(1024)
            conn.sendall(CONNACK_OK)
            if conn.recv(2) == b"\xc0\x00":
                conn.sendall(b"\xd0\x00")
            time.sleep(0.05)

        good = self.check(self.PING, self.machine(broker).place(active=True), active=True)
        self.assertTrue(good.healthy and good.active and good.checked == "mqtt-pingresp")
        def mute_broker(conn: socket.socket) -> None:
            conn.recv(1024)
            conn.sendall(CONNACK_OK)
            time.sleep(1.5)  # accepts, then says nothing to the PINGREQ

        mute = self.check(self.PING, self.machine(mute_broker).place(active=True), active=True)
        self.assertFalse(mute.healthy)
        self.assertIn("did not answer the PINGREQ", mute.detail)

    def test_a_profile_that_asks_for_active_is_ignored_without_the_host_switch(self) -> None:
        sent: list[bytes] = []

        def broker(conn: socket.socket) -> None:
            sent.append(conn.recv(1024))
            conn.sendall(CONNACK_OK)
            time.sleep(0.2)
            try:
                sent.append(conn.recv(16))
            except OSError:
                pass

        result = self.check(self.PING, self.machine(broker).place(active=True), active=False)
        self.assertTrue(result.healthy and not result.active)
        self.assertIn("host switch is off", result.detail)
        self.assertNotIn(b"\xc0\x00", sent[1:])  # no PINGREQ was ever sent


class OpcUaScenarios(BenchCase):
    READ = {"type": "opcua-read", "node": "ns=2;s=Temp"}

    def test_ack_error_garbage_and_silence(self) -> None:
        expectations = {
            "ack": (after_request(lambda _: b"ACKF" + bytes(24)), True),
            "error": (after_request(lambda _: b"ERRF" + bytes(8)), False),
            "garbage": (after_request(lambda _: b"\x00\x01\x02\x03\x04\x05\x06\x07"), False),
            "short": (after_request(lambda _: b"AC"), False),
            "silence": (silent, False),
            "reset": (reset_at_once, False),
        }
        for name, (script, healthy) in expectations.items():
            result = self.check(self.READ, self.machine(script).place())
            self.assertEqual(result.healthy, healthy, name)
            if healthy:
                self.assertEqual(result.checked, "opcua-hello")
                self.assertIn("was not read", result.detail)  # a handshake is never taken for a value


class MavlinkScenarios(BenchCase):
    BEAT = {"type": "mavlink-heartbeat"}

    def test_a_vehicle_that_streams(self) -> None:
        for frames in ([heartbeat_v1()], [heartbeat_v2()], [b"\x00noise\xff", heartbeat_v2()]):
            result = self.check(self.BEAT, self.machine(stream(frames)).place())
            self.assertTrue(result.healthy)

    def test_a_heartbeat_dribbled_one_byte_at_a_time_still_counts(self) -> None:
        result = self.check(self.BEAT, self.machine(stream([heartbeat_v2()], gap_s=0.002, chunk=1)).place())
        self.assertTrue(result.healthy)

    def test_a_wrong_checksum_a_wrong_message_and_a_cut_frame_do_not_count(self) -> None:
        broken = bytearray(heartbeat_v1())
        broken[-1] ^= 0x5A
        other_message = bytearray(heartbeat_v1())
        other_message[5] = 24  # GPS_RAW_INT, not HEARTBEAT
        for name, frame in {"crc": bytes(broken), "message": bytes(other_message), "cut": heartbeat_v2()[:-3], "empty": b""}.items():
            result = self.check(self.BEAT, self.machine(stream([frame] if frame else [])).place())
            self.assertFalse(result.healthy, name)

    def test_an_endless_stream_of_noise_is_bounded(self) -> None:
        noise = bytes(random.Random(SEED).randrange(0, 200) for _ in range(512))  # no 0xFD / 0xFE magic bytes
        started = time.monotonic()
        result = self.check(self.BEAT, self.machine(stream([noise] * 40)).place())
        self.assertFalse(result.healthy)
        self.assertLess(time.monotonic() - started, 3.0)

    def test_a_vehicle_that_talks_only_after_a_ground_station_heartbeat(self) -> None:
        def vehicle(conn: socket.socket) -> None:
            if conn.recv(64) == gcs_heartbeat_frame():
                conn.sendall(heartbeat_v2())
            time.sleep(0.1)

        quiet = self.check(self.BEAT, self.machine(vehicle).place())
        self.assertFalse(quiet.healthy)  # passive: nothing is sent, so nothing is heard
        heard = self.check(self.BEAT, self.machine(vehicle).place(active=True), active=True)
        self.assertTrue(heard.healthy and heard.active and heard.checked == "mavlink-gcs-heartbeat")


class DeclaredExchangeScenarios(BenchCase):
    RPC = {"type": "rpc-ping"}

    def place(self, machine: SimulatedMachine) -> Place:
        return machine.place(active=True, send=b"PING\r\n", expect=b"PONG")

    def test_the_declared_answer_even_when_split_or_surrounded(self) -> None:
        def talk(chunks: list[bytes]) -> Callable[[socket.socket], None]:
            def script(conn: socket.socket) -> None:
                conn.recv(64)
                for chunk in chunks:
                    conn.sendall(chunk)
                    time.sleep(0.02)
                time.sleep(0.05)

            return script

        for chunks in ([b"PONG"], [b"PO", b"NG"], [b"junk before PO", b"NG after"]):
            result = self.check(self.RPC, self.place(self.machine(talk(chunks))), active=True)
            self.assertTrue(result.healthy, chunks)
            self.assertEqual(result.checked, "tcp-exchange")

    def test_a_wrong_or_missing_answer_is_unhealthy(self) -> None:
        for name, script in {"wrong": after_request(lambda _: b"NOPE"), "silence": silent, "reset": reset_at_once, "empty close": lambda c: None}.items():
            result = self.check(self.RPC, self.place(self.machine(script)), active=True)
            self.assertFalse(result.healthy, name)

    def test_without_the_host_switch_only_reach_is_proven(self) -> None:
        machine = self.machine(after_request(lambda _: b"NOPE"))
        result = self.check(self.RPC, self.place(machine), active=False)
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "tcp-reach")
        self.assertFalse(result.active)


class _Web(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        behaviour = self.server.behaviour  # type: ignore[attr-defined]
        if behaviour == "slow":
            time.sleep(1.5)
        if behaviour == "big":
            body = b"x" * 200_000
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass
            return
        if behaviour == "reset":
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            self.connection.close()
            return
        status = {"ok": 200, "created": 204, "down": 503, "gone": 404, "boom": 500}.get(behaviour, 200)
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


class HttpScenarios(BenchCase):
    def serve(self, behaviour: str) -> Place:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Web)
        server.behaviour = behaviour  # type: ignore[attr-defined]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return Place("127.0.0.1", server.server_address[1])

    def test_status_codes(self) -> None:
        expected = {"ok": True, "created": True, "down": False, "gone": False, "boom": False}
        for behaviour, healthy in expected.items():
            result = self.check({"type": "http-get", "path": "/probe"}, self.serve(behaviour))
            self.assertEqual(result.healthy, healthy, behaviour)

    def test_slow_reset_and_oversized_answers(self) -> None:
        for behaviour in ("slow", "reset"):
            result = self.check({"type": "http-get", "path": "/probe"}, self.serve(behaviour))
            self.assertFalse(result.healthy, behaviour)
            self.assertTrue(result.supported)
        big = self.check({"type": "http-get", "path": "/probe"}, self.serve("big"))
        self.assertTrue(big.healthy)  # only a bounded part of the body is ever read

    def test_a_path_that_tries_to_leave_the_adapter_is_refused_not_probed(self) -> None:
        from hydra_umc_connector_hub.health_probe import ProbeProfileError

        for path in ("/../etc/passwd", "no-slash", "/a b", "/x\r\nHost: evil"):
            with self.assertRaises(ProbeProfileError, msg=path):
                run_health_check(manifest({"type": "http-get", "path": path}), Place("127.0.0.1", 1))


class FleetScenarios(BenchCase):
    """Forty simulated machines with a fault assigned from a fixed seed: every one is classified as its fault says, and none raises."""

    FAULTS = ("ok", "refused", "silent", "reset", "half", "noise")

    def build(self, kind: str, fault: str) -> tuple[dict, Place, bool]:
        if kind == "tcp":
            if fault == "refused":
                closed = socket.socket()
                closed.bind(("127.0.0.1", 0))
                port = closed.getsockname()[1]
                closed.close()
                return {"type": "tcp-connect"}, Place("127.0.0.1", port), False
            return {"type": "tcp-connect"}, self.machine(lambda c: None).place(), True  # reach is all a tcp check proves
        scripts = {
            "ok": (after_request(lambda _: CONNACK_OK), True),
            "silent": (silent, False),
            "reset": (reset_at_once, False),
            "half": (after_request(lambda _: CONNACK_OK[:2]), False),
            "noise": (after_request(lambda _: b"\x13\x37" * 4), False),
        }
        if fault == "refused":
            closed = socket.socket()
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]
            closed.close()
            return {"type": "mqtt-ping"}, Place("127.0.0.1", port), False
        script, healthy = scripts[fault]
        return {"type": "mqtt-ping"}, self.machine(script).place(), healthy

    def test_the_fleet_is_classified_exactly(self) -> None:
        rng = random.Random(SEED)
        plan = [(rng.choice(("tcp", "mqtt")), rng.choice(self.FAULTS)) for _ in range(40)]
        again = random.Random(SEED)
        self.assertEqual(plan, [(again.choice(("tcp", "mqtt")), again.choice(self.FAULTS)) for _ in range(40)])  # the seed fixes the fleet
        built = [(index, *self.build(kind, fault)) for index, (kind, fault) in enumerate(plan)]
        results: dict[int, HealthResult] = {}

        def probe(index: int, check: dict, place: Place) -> None:
            results[index] = run_health_check(manifest(check, f"machine-{index}"), place)

        started = time.monotonic()
        threads = [threading.Thread(target=probe, args=item[:3]) for item in built]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(len(results), 40, "every probe must return")
        self.assertLess(time.monotonic() - started, 10.0)
        for index, _check, _place, expected in built:
            self.assertEqual(results[index].healthy, expected, f"machine-{index} {plan[index]}")
            self.assertEqual(results[index].adapter_id, f"machine-{index}")
        self.assertTrue(any(r.healthy for r in results.values()) and any(not r.healthy for r in results.values()))


class FlappingLink(BenchCase):
    def test_a_link_that_goes_down_and_comes_back(self) -> None:
        clock = [1000.0]
        cache = ProbeCache(ttl=5.0, clock=lambda: clock[0])
        up = {"value": True}
        machine = self.machine(lambda conn: None)
        runs = []

        def run() -> HealthResult:
            runs.append(1)
            place = machine.place() if up["value"] else Place("127.0.0.1", 1)
            return run_health_check(manifest({"type": "tcp-connect"}), place, timeout=0.3)

        self.assertTrue(cache.get_or_run("m", run).healthy)
        up["value"] = False
        self.assertTrue(cache.get_or_run("m", run).healthy, "inside the window the answer is remembered, so a flood cannot reach the device")
        self.assertEqual(len(runs), 1)
        clock[0] += 5.0  # the window ends exactly here
        self.assertFalse(cache.get_or_run("m", run).healthy)
        up["value"] = True
        clock[0] += 5.0
        self.assertTrue(cache.get_or_run("m", run).healthy)
        self.assertEqual(len(runs), 3)

    def test_two_adapters_do_not_share_an_answer(self) -> None:
        cache = ProbeCache(ttl=60.0, clock=lambda: 0.0)
        first = cache.get_or_run("a", lambda: HealthResult("a", "tcp-connect", True, True, "up"))
        second = cache.get_or_run("b", lambda: HealthResult("b", "tcp-connect", True, False, "down"))
        self.assertTrue(first.healthy) and self.assertFalse(second.healthy)  # type: ignore[func-returns-value]


if __name__ == "__main__":
    unittest.main()
