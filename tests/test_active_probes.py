# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_active_probes.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The active probes: off by default, on only with the host switch AND the profile, and never an order the operator did not write."""
import json
import os
import socket
import struct
import tempfile
import threading
import unittest
from pathlib import Path

from hydra_umc_connector_hub.health_probe import (
    ACTIVE_ENV,
    Place,
    ProbeProfileError,
    _x25,
    active_probes_enabled,
    find_mavlink_heartbeat,
    gcs_heartbeat_frame,
    load_profile,
    run_health_check,
)


def _manifest(check_type: str) -> dict:
    return {"adapterId": "x", "timeoutMs": 800, "healthCheck": {"type": check_type}}


class _Scripted:
    """A TCP listener that records what it receives and replies step by step: each step is bytes to send after the next read (None = read and stay silent)."""

    def __init__(self, steps, *, talk_first=b""):
        self.received: list[bytes] = []
        self._steps = list(steps)
        self._talk_first = talk_first
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(5)
        self.port = self.listener.getsockname()[1]
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                conn, _ = self.listener.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(1.5)
                try:
                    if self._talk_first:
                        conn.sendall(self._talk_first)
                    for reply in self._steps:
                        data = conn.recv(512)
                        self.received.append(data)
                        if not data:
                            break
                        if reply:
                            conn.sendall(reply)
                    try:
                        data = conn.recv(512)
                        if data:
                            self.received.append(data)
                    except OSError:
                        pass
                except OSError:
                    pass

    def close(self):
        self.listener.close()


CONNACK_OK = b"\x20\x02\x00\x00"
PINGRESP = b"\xd0\x00"


class SwitchTests(unittest.TestCase):
    def test_the_switch_is_off_without_the_variable(self):
        self.assertFalse(active_probes_enabled({}))

    def test_only_the_exact_value_one_turns_it_on(self):
        for value in ("", "0", "true", "yes", "01", " 1", "1 "):
            self.assertFalse(active_probes_enabled({ACTIVE_ENV: value}), value)
        self.assertTrue(active_probes_enabled({ACTIVE_ENV: "1"}))

    def test_the_real_environment_is_read_when_none_is_given(self):
        old = os.environ.pop(ACTIVE_ENV, None)
        try:
            self.assertFalse(active_probes_enabled())
            os.environ[ACTIVE_ENV] = "1"
            self.assertTrue(active_probes_enabled())
        finally:
            os.environ.pop(ACTIVE_ENV, None)
            if old is not None:
                os.environ[ACTIVE_ENV] = old


class ProfileTests(unittest.TestCase):
    def _load(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "endpoints.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_profile(str(path))

    def test_active_defaults_to_off(self):
        place = self._load({"a": {"host": "127.0.0.1", "port": 1883}})["a"]
        self.assertFalse(place.active)
        self.assertEqual((place.send, place.expect), (b"", b""))

    def test_true_asks_for_the_builtin_exchange(self):
        place = self._load({"a": {"host": "127.0.0.1", "port": 1883, "active": True}})["a"]
        self.assertTrue(place.active)

    def test_false_and_null_are_off(self):
        for value in (False, None):
            self.assertFalse(self._load({"a": {"host": "127.0.0.1", "port": 1, "active": value}})["a"].active)

    def test_the_operator_declares_the_bytes_in_hex(self):
        place = self._load({"a": {"host": "127.0.0.1", "port": 9, "active": {"sendHex": "50494e470a", "expectHex": "504f4e47"}}})["a"]
        self.assertEqual(place.send, b"PING\n")
        self.assertEqual(place.expect, b"PONG")

    def test_a_device_entry_can_be_active(self):
        place = self._load({"a": {"device": "/dev/ttyUSB0", "active": {"sendHex": "01", "expectHex": "02"}}})["a"]
        self.assertEqual((place.device, place.send, place.expect), ("/dev/ttyUSB0", b"\x01", b"\x02"))

    def test_bad_active_entries_stop_the_load(self):
        bad = [
            "yes",
            1,
            [],
            {"sendHex": "01"},
            {"expectHex": "01"},
            {"sendHex": "", "expectHex": "01"},
            {"sendHex": "0", "expectHex": "01"},
            {"sendHex": "zz", "expectHex": "01"},
            {"sendHex": "01", "expectHex": "01", "extra": 1},
            {"sendHex": "00" * 65, "expectHex": "01"},
            {"sendHex": 1, "expectHex": 2},
        ]
        for value in bad:
            with self.assertRaises(ProbeProfileError, msg=repr(value)):
                self._load({"a": {"host": "127.0.0.1", "port": 9, "active": value}})

    def test_the_largest_exchange_is_accepted(self):
        place = self._load({"a": {"host": "127.0.0.1", "port": 9, "active": {"sendHex": "ab" * 64, "expectHex": "cd" * 64}}})["a"]
        self.assertEqual((len(place.send), len(place.expect)), (64, 64))


class MqttActiveTests(unittest.TestCase):
    def _run(self, server, *, active, asks=True):
        place = Place("127.0.0.1", server.port, active=asks)
        return run_health_check(_manifest("mqtt-ping"), place, active=active)

    def test_the_reach_check_sends_no_pingreq_when_the_switch_is_off(self):
        server = _Scripted([CONNACK_OK])
        self.addCleanup(server.close)
        result = self._run(server, active=False)
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "mqtt-connack")
        self.assertNotIn(b"\xc0\x00", server.received)
        self.assertIn("host switch is off", result.detail)
        self.assertNotIn("active", result.to_dict())

    def test_a_profile_that_does_not_ask_stays_passive_even_with_the_switch_on(self):
        server = _Scripted([CONNACK_OK])
        self.addCleanup(server.close)
        result = self._run(server, active=True, asks=False)
        self.assertEqual(result.checked, "mqtt-connack")
        self.assertNotIn(b"\xc0\x00", server.received)

    def test_the_active_check_wants_the_pingresp(self):
        server = _Scripted([CONNACK_OK, PINGRESP])
        self.addCleanup(server.close)
        result = self._run(server, active=True)
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "mqtt-pingresp")
        self.assertTrue(result.to_dict()["active"])
        self.assertIn(b"\xc0\x00", server.received)

    def test_a_broker_that_does_not_answer_the_ping_is_unhealthy(self):
        server = _Scripted([CONNACK_OK, None])
        self.addCleanup(server.close)
        result = self._run(server, active=True)
        self.assertFalse(result.healthy)
        self.assertIn("did not answer the PINGREQ", result.detail)

    def test_a_refused_connection_never_gets_a_ping(self):
        server = _Scripted([b"\x20\x02\x00\x05", PINGRESP])
        self.addCleanup(server.close)
        result = self._run(server, active=True)
        self.assertFalse(result.healthy)
        self.assertIn("refused", result.detail)
        self.assertNotIn(b"\xc0\x00", server.received)

    def test_a_wrong_pong_is_unhealthy(self):
        server = _Scripted([CONNACK_OK, b"\xd0\x01"])
        self.addCleanup(server.close)
        self.assertFalse(self._run(server, active=True).healthy)


class MavlinkActiveTests(unittest.TestCase):
    def test_the_gcs_heartbeat_is_a_valid_mavlink2_frame(self):
        frame = gcs_heartbeat_frame()
        self.assertEqual(frame[0], 0xFD)
        self.assertEqual(frame[1], 9)
        self.assertEqual(frame[5:7], bytes([255, 190]))  # system, component of a ground station
        self.assertEqual(frame[7:10], bytes(3))  # message id 0 = HEARTBEAT
        self.assertEqual(frame[10 + 4], 6)  # type = GCS
        self.assertEqual(frame[10 + 5], 8)  # autopilot = none
        self.assertEqual(struct.unpack("<H", frame[-2:])[0], _x25(frame[1:-2] + bytes([50])))
        self.assertTrue(find_mavlink_heartbeat(frame))

    def _vehicle_frame(self):
        body = bytes([9, 0, 0, 0, 1, 1, 0, 0, 0]) + bytes([0, 0, 0, 0, 2, 3, 81, 4, 3])
        return bytes([253]) + body + struct.pack("<H", _x25(body + bytes([50])))

    def test_the_active_check_says_hello_first_and_hears_the_vehicle(self):
        server = _Scripted([self._vehicle_frame()])  # the vehicle answers only after it heard the ground station
        self.addCleanup(server.close)
        result = run_health_check(_manifest("mavlink-heartbeat"), Place("127.0.0.1", server.port, active=True), active=True)
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "mavlink-gcs-heartbeat")
        self.assertEqual(server.received[0], gcs_heartbeat_frame())

    def test_the_passive_check_sends_nothing(self):
        server = _Scripted([], talk_first=self._vehicle_frame())
        self.addCleanup(server.close)
        result = run_health_check(_manifest("mavlink-heartbeat"), Place("127.0.0.1", server.port, active=True), active=False)
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "mavlink-heartbeat")
        self.assertEqual([item for item in server.received if item], [])

    def test_a_silent_vehicle_is_unhealthy_even_after_the_hello(self):
        server = _Scripted([None])
        self.addCleanup(server.close)
        result = run_health_check(_manifest("mavlink-heartbeat"), Place("127.0.0.1", server.port, active=True), active=True)
        self.assertFalse(result.healthy)
        self.assertTrue(result.active)


class TcpExchangeTests(unittest.TestCase):
    def _place(self, server, **values):
        defaults = dict(active=True, send=b"PING\n", expect=b"PONG")
        defaults.update(values)
        return Place("127.0.0.1", server.port, **defaults)

    def test_the_declared_bytes_are_sent_and_the_declared_answer_is_wanted(self):
        for kind in ("rpc-ping", "ros2-node-alive"):
            server = _Scripted([b"..PONG.."])
            self.addCleanup(server.close)
            result = run_health_check(_manifest(kind), self._place(server), active=True)
            self.assertTrue(result.healthy, kind)
            self.assertEqual(result.checked, "tcp-exchange")
            self.assertEqual(server.received[0], b"PING\n")

    def test_without_the_switch_nothing_is_sent(self):
        server = _Scripted([b"PONG"])
        self.addCleanup(server.close)
        result = run_health_check(_manifest("rpc-ping"), self._place(server), active=False)
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "tcp-reach")
        self.assertEqual([item for item in server.received if item], [])

    def test_a_place_that_declared_nothing_stays_a_reach_check(self):
        server = _Scripted([b"PONG"])
        self.addCleanup(server.close)
        result = run_health_check(_manifest("rpc-ping"), Place("127.0.0.1", server.port, active=True), active=True)
        self.assertEqual(result.checked, "tcp-reach")
        self.assertFalse(result.active)

    def test_a_wrong_answer_is_unhealthy(self):
        server = _Scripted([b"NOPE"])
        self.addCleanup(server.close)
        result = run_health_check(_manifest("rpc-ping"), self._place(server), active=True)
        self.assertFalse(result.healthy)
        self.assertIn("did not give the declared answer", result.detail)

    def test_nobody_listening_is_unhealthy_not_an_error(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.close()
        result = run_health_check(_manifest("rpc-ping"), Place("127.0.0.1", port, active=True, send=b"a", expect=b"b"), active=True)
        self.assertFalse(result.healthy)
        self.assertTrue(result.supported)

    def test_a_type_that_has_no_harmless_order_never_sends(self):
        server = _Scripted([b"PONG"])
        self.addCleanup(server.close)
        result = run_health_check(_manifest("tcp-connect"), self._place(server), active=True)
        self.assertEqual(result.checked, "tcp")
        self.assertFalse(result.active)
        self.assertEqual([item for item in server.received if item], [])


@unittest.skipUnless(hasattr(os, "openpty"), "needs a pseudo terminal")
class DeviceExchangeTests(unittest.TestCase):
    def _device(self):
        import tty

        master, slave = os.openpty()
        tty.setraw(slave)  # no echo and no line buffering: the bytes pass as they are
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        return master, os.ttyname(slave)

    def _skip_if_not_under_dev(self, name):
        if not name.startswith("/dev/"):
            self.skipTest("the pseudo terminal is not under /dev/")

    def test_the_device_gets_the_declared_bytes_and_answers(self):
        master, name = self._device()
        self._skip_if_not_under_dev(name)
        answer = threading.Thread(target=lambda: (os.read(master, 64), os.write(master, b"PONG")), daemon=True)
        answer.start()
        place = Place("", 0, device=name, active=True, send=b"PING\n", expect=b"PONG")
        result = run_health_check(_manifest("serial-probe"), place, active=True)
        answer.join(2)
        self.assertTrue(result.healthy, result.detail)
        self.assertEqual(result.checked, "device-exchange")

    def test_a_silent_device_is_unhealthy(self):
        _, name = self._device()
        self._skip_if_not_under_dev(name)
        place = Place("", 0, device=name, active=True, send=b"PING\n", expect=b"PONG")
        result = run_health_check(_manifest("serial-probe"), place, active=True)
        self.assertFalse(result.healthy)

    def test_without_the_switch_the_device_is_only_opened(self):
        master, name = self._device()
        self._skip_if_not_under_dev(name)
        place = Place("", 0, device=name, active=True, send=b"PING\n", expect=b"PONG")
        result = run_health_check(_manifest("serial-probe"), place, active=False)
        self.assertEqual(result.checked, "device-open")
        os.set_blocking(master, False)
        with self.assertRaises(BlockingIOError):
            os.read(master, 8)

    def test_gpio_read_never_writes(self):
        master, name = self._device()
        self._skip_if_not_under_dev(name)
        place = Place("", 0, device=name, active=True, send=b"PING\n", expect=b"PONG")
        result = run_health_check(_manifest("gpio-read"), place, active=True)
        self.assertEqual(result.checked, "device-open")
        os.set_blocking(master, False)
        with self.assertRaises(BlockingIOError):
            os.read(master, 8)


class DeviceGuardTests(unittest.TestCase):
    def test_a_missing_device_is_unhealthy_with_the_reason(self):
        place = Place("", 0, device="/dev/does-not-exist-hydra", active=True, send=b"a", expect=b"b")
        result = run_health_check(_manifest("serial-probe"), place, active=True)
        self.assertFalse(result.healthy)

    def test_a_profile_without_a_device_says_so(self):
        place = Place("127.0.0.1", 1, active=True, send=b"a", expect=b"b")
        result = run_health_check(_manifest("serial-probe"), place, active=True)
        self.assertFalse(result.healthy)


class RouteAndCliTests(unittest.TestCase):
    """The switch is read at the route and at the command, and the route reports what was exchanged."""

    FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

    def _get(self, server, path):
        import urllib.request

        thread = threading.Thread(target=server.handle_request)
        thread.start()
        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}", timeout=5)
            return json.loads(response.read().decode("utf-8"))
        finally:
            thread.join(timeout=5)

    def _serve(self, broker):
        from hydra_umc_connector_hub.catalog_server import serve_catalog

        server = serve_catalog(str(self.FIXTURES), port=0, places={"industrial-mqtt": Place("127.0.0.1", broker.port, active=True)})
        self.addCleanup(server.server_close)
        return server

    def _with_env(self, value):
        old = os.environ.pop(ACTIVE_ENV, None)
        if value is not None:
            os.environ[ACTIVE_ENV] = value

        def restore():
            os.environ.pop(ACTIVE_ENV, None)
            if old is not None:
                os.environ[ACTIVE_ENV] = old

        self.addCleanup(restore)

    def test_the_route_stays_passive_without_the_switch(self):
        self._with_env(None)
        broker = _Scripted([CONNACK_OK, PINGRESP])
        self.addCleanup(broker.close)
        payload = self._get(self._serve(broker), "/probe/industrial-mqtt")
        self.assertEqual(payload["checked"], "mqtt-connack")
        self.assertNotIn("active", payload)

    def test_the_route_is_active_with_the_switch(self):
        self._with_env("1")
        broker = _Scripted([CONNACK_OK, PINGRESP])
        self.addCleanup(broker.close)
        payload = self._get(self._serve(broker), "/probe/industrial-mqtt")
        self.assertEqual(payload["checked"], "mqtt-pingresp")
        self.assertTrue(payload["active"])

    def test_the_probe_command_follows_the_switch(self):
        import contextlib
        import io

        from hydra_umc_connector_hub.cli import main

        broker = _Scripted([CONNACK_OK, PINGRESP])
        self.addCleanup(broker.close)
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / "endpoints.json"
            profile.write_text(json.dumps({"industrial-mqtt": {"host": "127.0.0.1", "port": broker.port, "active": True}}), encoding="utf-8")
            self._with_env("1")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["probe", "--registry-dir", str(self.FIXTURES), "--endpoints-file", str(profile), "--adapter-id", "industrial-mqtt"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["results"][0]["checked"], "mqtt-pingresp")


if __name__ == "__main__":
    unittest.main()
