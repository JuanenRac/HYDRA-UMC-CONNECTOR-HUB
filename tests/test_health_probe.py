# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_health_probe.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The healthCheck of a manifest, run for real against stand-ins on real sockets: HTTP, a bare TCP port, an MQTT broker, an OPC UA server."""
import json
import socket
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hydra_umc_connector_hub.catalog_server import serve_catalog
from hydra_umc_connector_hub.health_probe import Place, ProbeCache, ProbeProfileError, load_profile, run_health_check

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _manifest(check: dict) -> dict:
    return {"adapterId": "x", "timeoutMs": 1000, "healthCheck": check}


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
        for check_type in ("serial-probe", "gpio-read", "rpc-ping", "ros2-node-alive", "mavlink-heartbeat", "mqtt-topic-recent", "something-new"):
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
