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


class CatalogSnapshotVersionTests(unittest.TestCase):
    """a real, deterministic snapshot version + ETag, and a
    real conditional-GET 304 when the registry genuinely has not
    changed."""

    def setUp(self):
        self.server = serve_catalog(str(FIXTURES_DIR), port=0)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.server_close()

    def _get_with_headers(self, path: str, headers: dict | None = None):
        import threading

        thread = threading.Thread(target=self.server.handle_request)
        thread.start()
        try:
            request = urllib.request.Request(f"{self.base_url}{path}", headers=headers or {})
            try:
                response = urllib.request.urlopen(request, timeout=5)
                return response.status, dict(response.headers), response.read()
            except urllib.error.HTTPError as exc:
                return exc.code, dict(exc.headers), exc.read()
        finally:
            thread.join(timeout=5)

    def test_catalog_response_carries_a_real_etag_matching_its_own_snapshot_version(self):
        status, headers, body = self._get_with_headers("/catalog")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIn("snapshotVersion", payload)
        self.assertEqual(headers["ETag"], f'"{payload["snapshotVersion"]}"')

    def test_two_back_to_back_scans_of_an_unchanged_registry_yield_the_same_version(self):
        _, _, body_a = self._get_with_headers("/catalog")
        _, _, body_b = self._get_with_headers("/catalog")
        self.assertEqual(json.loads(body_a)["snapshotVersion"], json.loads(body_b)["snapshotVersion"])

    def test_matching_if_none_match_gets_a_real_304_not_a_full_body(self):
        _, headers, body = self._get_with_headers("/catalog")
        version = json.loads(body)["snapshotVersion"]

        status, headers_304, body_304 = self._get_with_headers("/catalog", {"If-None-Match": f'"{version}"'})

        self.assertEqual(status, 304)
        self.assertEqual(headers_304["ETag"], f'"{version}"')
        self.assertEqual(body_304, b"")

    def test_a_stale_if_none_match_still_gets_the_real_full_body(self):
        status, headers, body = self._get_with_headers("/catalog", {"If-None-Match": '"not-a-real-version"'})
        self.assertEqual(status, 200)
        self.assertIn("adapters", json.loads(body))


if __name__ == "__main__":
    unittest.main()
