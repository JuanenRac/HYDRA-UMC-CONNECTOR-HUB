# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_catalog_server.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 2 tests against a REAL `http.server` bound to a real ephemeral
local port (127.0.0.1:0, read back via `server.server_port`) - never a
mocked socket or a mocked `BaseHTTPRequestHandler`. Every request in this
file is a real `urllib.request.urlopen()` round trip over a real loopback
TCP connection, driven one request at a time via the server's own
`handle_request()` (no background thread needed for a handful of
sequential real requests)."""
import json
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.catalog_server import serve_catalog

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class CatalogServerTests(unittest.TestCase):
    def setUp(self):
        self.server = serve_catalog(str(FIXTURES_DIR), port=0)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.server_close()

    def _get(self, path: str):
        import threading

        thread = threading.Thread(target=self.server.handle_request)
        thread.start()
        try:
            response = urllib.request.urlopen(f"{self.base_url}{path}", timeout=5)
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            thread.join(timeout=5)

    def test_health_reports_the_real_ten_fixture_adapter_count(self):
        status, payload = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["adapterCount"], 10)
        self.assertEqual(payload["invalidFileCount"], 0)

    def test_catalog_lists_all_ten_real_adapters(self):
        status, payload = self._get("/catalog")
        self.assertEqual(status, 200)
        ids = [entry["adapterId"] for entry in payload["adapters"]]
        self.assertEqual(len(ids), 10)
        self.assertIn("industrial-opcua", ids)

    def test_catalog_detail_returns_the_full_real_manifest_for_one_adapter(self):
        status, payload = self._get("/catalog/cnc-grbl")
        self.assertEqual(status, 200)
        self.assertEqual(payload["ownerProject"], "HYDRA-UMC-BRIDGE-CNC")
        self.assertIn("endpointSchema", payload)

    def test_catalog_detail_for_an_unknown_adapter_is_a_real_404(self):
        import threading

        thread = threading.Thread(target=self.server.handle_request)
        thread.start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"{self.base_url}/catalog/not-real", timeout=5)
            self.assertEqual(ctx.exception.code, 404)
        finally:
            thread.join(timeout=5)

    def test_an_unknown_route_is_a_real_404(self):
        import threading

        thread = threading.Thread(target=self.server.handle_request)
        thread.start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"{self.base_url}/not-a-route", timeout=5)
            self.assertEqual(ctx.exception.code, 404)
        finally:
            thread.join(timeout=5)

    def test_a_write_attempt_gets_a_real_501_never_a_silently_accepted_write(self):
        import threading

        thread = threading.Thread(target=self.server.handle_request)
        thread.start()
        try:
            request = urllib.request.Request(f"{self.base_url}/catalog", method="POST", data=b"{}")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(ctx.exception.code, 501)
        finally:
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
