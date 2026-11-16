# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_probe_redirects.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The http-get health probe opens a connection only to the host and port it was given: a redirect is an unhealthy answer and is never followed."""
from __future__ import annotations

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from hydra_umc_connector_hub.health_probe import Place, run_health_check


def _serve(handler: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class ProbeRedirectTests(unittest.TestCase):
    def test_a_redirect_is_not_followed_and_is_not_healthy(self):
        reached: list[str] = []

        class Inside(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                reached.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):  # noqa: D401
                pass

        inside = _serve(Inside)
        self.addCleanup(lambda: (inside.shutdown(), inside.server_close()))

        class Listed(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(self.server.status_code)  # type: ignore[attr-defined]
                self.send_header("Location", f"http://127.0.0.1:{inside.server_port}/internal")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):  # noqa: D401
                pass

        listed = _serve(Listed)
        self.addCleanup(lambda: (listed.shutdown(), listed.server_close()))
        place = Place("127.0.0.1", listed.server_port)
        for status in (301, 302, 303, 307, 308):
            listed.status_code = status  # type: ignore[attr-defined]
            result = run_health_check({"adapterId": "x", "timeoutMs": 800, "healthCheck": {"type": "http-get", "path": "/probe"}}, place)
            self.assertFalse(result.healthy, status)
            self.assertIn(str(status), result.detail)
        self.assertEqual(reached, [], "the host behind the redirect received a request")


if __name__ == "__main__":
    unittest.main()
