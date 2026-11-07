# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_health_probe.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The healthCheck of a manifest, run for real against stand-ins on real sockets: HTTP, a bare TCP port, an MQTT broker, an OPC UA server."""
import json
import os
import socket
import stat
import struct
import tempfile
import threading
import unittest
import urllib.request
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hydra_umc_connector_hub.catalog_server import serve_catalog
from hydra_umc_connector_hub.health_probe import Place, ProbeCache, ProbeProfileError, _x25, find_mavlink_heartbeat, load_profile, run_health_check

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _manifest(check: dict) -> dict:
    return {"adapterId": "x", "timeoutMs": 1000, "healthCheck": check}


def _mavlink_v1_heartbeat(msgid: int = 0) -> bytes:
    body = bytes([9, 1, 1, 1, msgid]) + bytes(9)  # len, seq, system, component, message id, payload
    return bytes([254]) + body + struct.pack("<H", _x25(body + bytes([50])))


def _mavlink_v2_heartbeat() -> bytes:
    body = bytes([9, 0, 0, 1, 1, 1, 0, 0, 0]) + bytes([2, 3, 4, 5, 0, 0, 3, 3, 3])  # len, flags, seq, system, component, id(3), payload
    return bytes([253]) + body + struct.pack("<H", _x25(body + bytes([50])))


class _Http(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        status = 200 if self.path == "/probe" else 503
        self.send_response(status)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # noqa: D401
        pass


def _serve_http():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Http)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _serve_tcp(answer):
    """A TCP listener that reads what the client sends and answers `answer(data)` (bytes, or None to close without a word)."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)

    def run():
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(2)
                try:
                    data = conn.recv(1024)
                    reply = answer(data)
                    if reply:
                        conn.sendall(reply)
                except OSError:
                    pass

    threading.Thread(target=run, daemon=True).start()
    return listener


def _serve_talker(message):
    """A TCP listener that sends `message` as soon as a client connects (a vehicle streams its heartbeat without being asked)."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)

    def run():
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            with conn:
                try:
                    conn.sendall(message)
                    conn.settimeout(1)
                    conn.recv(16)
                except OSError:
                    pass

    threading.Thread(target=run, daemon=True).start()
    return listener


class HealthProbeTests(unittest.TestCase):
    def test_http_get_is_healthy_on_a_2xx_and_not_on_another_status(self):
        server = _serve_http()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        place = Place("127.0.0.1", server.server_port)
        ok = run_health_check(_manifest({"type": "http-get", "path": "/probe"}), place)
        self.assertTrue(ok.healthy and ok.supported)
        self.assertEqual(ok.checked, "http")
        self.assertIn("answered 200", ok.detail)
        bad = run_health_check(_manifest({"type": "http-get", "path": "/other"}), place)
        self.assertFalse(bad.healthy)
        self.assertIn("503", bad.detail)
        with self.assertRaises(ProbeProfileError):
            run_health_check(_manifest({"type": "http-get", "path": "/../etc"}), place)

    def test_tcp_connect_and_a_port_nobody_listens_on(self):
        listener = _serve_tcp(lambda data: None)
        self.addCleanup(listener.close)
        up = run_health_check(_manifest({"type": "tcp-connect"}), Place("127.0.0.1", listener.getsockname()[1]))
        self.assertTrue(up.healthy)
        closed = socket.socket()
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
        closed.close()
        down = run_health_check(_manifest({"type": "tcp-connect"}), Place("127.0.0.1", port), timeout=0.5)
        self.assertFalse(down.healthy)
        self.assertTrue(down.supported)
        self.assertIn("the check failed", down.detail)

    def test_mqtt_ping_needs_a_connack_that_accepts(self):
        accepting = _serve_tcp(lambda data: b"\x20\x02\x00\x00" if data[:1] == b"\x10" else None)
        self.addCleanup(accepting.close)
        result = run_health_check(_manifest({"type": "mqtt-ping", "topic": "$SYS/x"}), Place("127.0.0.1", accepting.getsockname()[1]))
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "mqtt-connack")
        refusing = _serve_tcp(lambda data: b"\x20\x02\x00\x05")
        self.addCleanup(refusing.close)
        refused = run_health_check(_manifest({"type": "mqtt-ping"}), Place("127.0.0.1", refusing.getsockname()[1]))
        self.assertFalse(refused.healthy)
        self.assertIn("return code 5", refused.detail)
        mute = _serve_tcp(lambda data: b"HTTP/1.1 200 OK\r\n\r\n")
        self.addCleanup(mute.close)
        not_mqtt = run_health_check(_manifest({"type": "mqtt-ping"}), Place("127.0.0.1", mute.getsockname()[1]))
        self.assertFalse(not_mqtt.healthy)

    def test_opcua_read_proves_only_the_hello_and_says_so(self):
        acking = _serve_tcp(lambda data: b"ACKF" + (28).to_bytes(4, "little") + b"\x00" * 20 if data[:4] == b"HELF" else None)
        self.addCleanup(acking.close)
        result = run_health_check(_manifest({"type": "opcua-read", "node": "ns=0;i=2259"}), Place("127.0.0.1", acking.getsockname()[1]))
        self.assertTrue(result.healthy)
        self.assertEqual(result.checked, "opcua-hello")
        self.assertIn("was not read", result.detail)
        erroring = _serve_tcp(lambda data: b"ERRF" + (16).to_bytes(4, "little") + b"\x00" * 8)
        self.addCleanup(erroring.close)
        self.assertFalse(run_health_check(_manifest({"type": "opcua-read"}), Place("127.0.0.1", erroring.getsockname()[1])).healthy)

    def test_a_check_the_hub_cannot_run_is_unsupported_and_never_healthy(self):
        for check_type in ("mqtt-topic-recent", "something-new"):
            result = run_health_check(_manifest({"type": check_type}), Place("127.0.0.1", 1))
            self.assertFalse(result.supported, check_type)
            self.assertFalse(result.healthy, check_type)
        self.assertFalse(run_health_check({"adapterId": "x"}, Place("127.0.0.1", 1)).supported)

    def test_every_fixture_check_type_is_either_run_or_declared_unsupported(self):
        for path in sorted(FIXTURES.glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            result = run_health_check(manifest, Place("127.0.0.1", 1), timeout=0.3)
            self.assertEqual(result.check_type, manifest["healthCheck"]["type"], path.name)
            if not result.supported:
                self.assertIn("cannot run", result.detail)

    def test_rpc_and_ros2_checks_prove_only_that_the_port_accepts(self):
        listener = _serve_tcp(lambda data: None)
        self.addCleanup(listener.close)
        place = Place("127.0.0.1", listener.getsockname()[1])
        for check_type in ("rpc-ping", "ros2-node-alive"):
            result = run_health_check(_manifest({"type": check_type}), place)
            self.assertTrue(result.supported and result.healthy, check_type)
            self.assertEqual(result.checked, "tcp-reach")
            self.assertIn("was not asked", result.detail)
        closed = socket.socket()
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
        closed.close()
        self.assertFalse(run_health_check(_manifest({"type": "rpc-ping"}), Place("127.0.0.1", port)).healthy)

    def test_mavlink_heartbeat_needs_a_frame_with_a_valid_checksum(self):
        v1 = _mavlink_v1_heartbeat()
        v2 = _mavlink_v2_heartbeat()
        self.assertTrue(find_mavlink_heartbeat(v1) and find_mavlink_heartbeat(v2))
        self.assertTrue(find_mavlink_heartbeat(b"\x00\x01noise" + v2 + b"tail"))
        broken = bytearray(v2)
        broken[-1] ^= 0xFF
        for bad in (bytes(broken), v1[:-1], v2[:5], b"", b"\xfe" * 30, b"\xfd" * 30, _mavlink_v1_heartbeat(msgid=1)):
            self.assertFalse(find_mavlink_heartbeat(bad))
        for frame, label in ((v1, "v1"), (v2, "v2")):
            server = _serve_talker(frame)
            self.addCleanup(server.close)
            result = run_health_check(_manifest({"type": "mavlink-heartbeat"}), Place("127.0.0.1", server.getsockname()[1]))
            self.assertTrue(result.healthy, label)
            self.assertEqual(result.checked, "mavlink-heartbeat")
        silent = _serve_talker(b"hello there")
        self.addCleanup(silent.close)
        result = run_health_check({"adapterId": "x", "timeoutMs": 300, "healthCheck": {"type": "mavlink-heartbeat"}}, Place("127.0.0.1", silent.getsockname()[1]))
        self.assertTrue(result.supported)
        self.assertFalse(result.healthy)

    def test_device_checks_prove_only_that_the_device_file_opens(self):
        for check_type in ("serial-probe", "gpio-read"):
            manifest = _manifest({"type": check_type})
            with mock.patch("os.stat", return_value=mock.Mock(st_mode=stat.S_IFCHR | 0o660)), mock.patch("os.open", return_value=99) as opener, mock.patch("os.close") as closer:
                result = run_health_check(manifest, Place("", 0, device="/dev/ttyUSB0"))
            self.assertTrue(result.healthy, check_type)
            self.assertEqual(result.checked, "device-open")
            self.assertIn("nothing was read", result.detail)
            closer.assert_called_once_with(99)
            self.assertTrue(opener.call_args[0][1] & os.O_RDONLY == os.O_RDONLY)
            with mock.patch("os.stat", return_value=mock.Mock(st_mode=stat.S_IFREG | 0o644)):
                self.assertIn("not a character device", run_health_check(manifest, Place("", 0, device="/dev/x")).detail)
            with mock.patch("os.stat", side_effect=FileNotFoundError):
                self.assertIn("does not exist", run_health_check(manifest, Place("", 0, device="/dev/x")).detail)
            with mock.patch("os.stat", return_value=mock.Mock(st_mode=stat.S_IFCHR)), mock.patch("os.open", side_effect=PermissionError):
                result = run_health_check(manifest, Place("", 0, device="/dev/x"))
            self.assertFalse(result.healthy)
            self.assertIn("may not open", result.detail)
        self.assertFalse(run_health_check(_manifest({"type": "serial-probe"}), Place("127.0.0.1", 1)).healthy)

    @unittest.skipUnless(os.path.exists("/dev/null"), "needs a Linux device file")
    def test_a_real_character_device_opens(self):
        result = run_health_check(_manifest({"type": "gpio-read"}), Place("", 0, device="/dev/null"))
        self.assertTrue(result.healthy)
        self.assertFalse(run_health_check(_manifest({"type": "gpio-read"}), Place("", 0, device="/dev/hydra-no-such-device")).healthy)

    def test_the_profile_takes_a_device_and_refuses_a_path_outside_dev(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_text(json.dumps({"a": {"device": "/dev/ttyUSB0"}, "b": {"host": "h", "port": 5, "device": "/dev/gpiochip0"}}))
            places = load_profile(str(path))
            self.assertEqual(places["a"], Place("", 0, "http", "/dev/ttyUSB0"))
            self.assertEqual(places["b"].device, "/dev/gpiochip0")
            for bad in ("/etc/passwd", "/dev/../etc/passwd", "dev/tty", "/dev/", 5, "/dev/a b"):
                path.write_text(json.dumps({"a": {"device": bad}}))
                with self.assertRaises(ProbeProfileError, msg=str(bad)):
                    load_profile(str(path))

    def test_the_profile_lists_places_and_refuses_what_is_not_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.json"
            good.write_text(json.dumps({"a": {"host": "plc.local", "port": 502}, "b": {"host": "[::1]", "port": 443, "scheme": "https"}}))
            places = load_profile(str(good))
            self.assertEqual(places["a"], Place("plc.local", 502, "http"))
            self.assertEqual(places["b"].scheme, "https")
            for bad in (
                [],
                {},
                {"a": {"host": "x y", "port": 1}},
                {"a": {"host": "x/../y", "port": 1}},
                {"a": {"host": "h", "port": 0}},
                {"a": {"host": "h", "port": True}},
                {"a": {"host": "h", "port": 1, "scheme": "file"}},
                {"a": "h:1"},
            ):
                path = Path(tmp) / "bad.json"
                path.write_text(json.dumps(bad))
                with self.assertRaises(ProbeProfileError, msg=str(bad)):
                    load_profile(str(path))
            with self.assertRaises(ProbeProfileError):
                load_profile(str(Path(tmp) / "missing.json"))

    def test_the_cache_runs_a_check_once_inside_its_window(self):
        now = [100.0]
        cache = ProbeCache(5.0, clock=lambda: now[0])
        calls = []
        run = lambda: calls.append(1) or "result"  # noqa: E731
        self.assertEqual(cache.get_or_run("a", run), "result")
        self.assertEqual(cache.get_or_run("a", run), "result")
        self.assertEqual(len(calls), 1)
        now[0] += 6
        cache.get_or_run("a", run)
        self.assertEqual(len(calls), 2)


class ProbeRouteTests(unittest.TestCase):
    def _get(self, server, path):
        thread = threading.Thread(target=server.handle_request)
        thread.start()
        try:
            try:
                response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}", timeout=5)
                return response.status, json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))
        finally:
            thread.join(timeout=5)

    def test_the_route_is_off_without_a_profile_and_probes_only_what_the_profile_lists(self):
        import urllib.error  # noqa: F401

        off = serve_catalog(str(FIXTURES), port=0)
        self.addCleanup(off.server_close)
        status, payload = self._get(off, "/probe/industrial-mqtt")
        self.assertEqual(status, 404)
        self.assertIn("--endpoints-file", payload["error"])

        broker = _serve_tcp(lambda data: b"\x20\x02\x00\x00" if data[:1] == b"\x10" else None)
        self.addCleanup(broker.close)
        on = serve_catalog(str(FIXTURES), port=0, places={"industrial-mqtt": Place("127.0.0.1", broker.getsockname()[1])})
        self.addCleanup(on.server_close)
        status, payload = self._get(on, "/probe/industrial-mqtt")
        self.assertEqual(status, 200)
        self.assertTrue(payload["healthy"])
        self.assertEqual(payload["checked"], "mqtt-connack")
        status, payload = self._get(on, "/probe/industrial-opcua")
        self.assertEqual(status, 404)
        status, _ = self._get(on, "/probe/not-an-adapter")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
