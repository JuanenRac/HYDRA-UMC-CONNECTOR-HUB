# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_hardening.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A registry directory is files other people drop in: one that is not UTF-8,
one that is far too large, a directory that disappears under a running server,
a client that connects and says nothing. Real files, a real server on a real
ephemeral port."""
import json
import shutil
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.catalog_server import serve_catalog
from hydra_umc_connector_hub.registry import build_catalog
from hydra_umc_connector_hub.schema import MAX_MANIFEST_BYTES, load_and_validate

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _a_valid_fixture() -> Path:
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        data, errors = load_and_validate(str(path))
        if data is not None and not errors:
            return path
    raise AssertionError("no valid fixture manifest found")


class BrokenFilesInTheRegistryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.registry = Path(self._tmp.name)
        shutil.copy(_a_valid_fixture(), self.registry / "good.json")

    def test_a_file_that_is_not_utf8_is_listed_as_invalid_and_the_rest_still_load(self):
        (self.registry / "latin1.json").write_bytes('{"adapterId": "caf\xe9"}'.encode("latin-1"))
        entries, invalid = build_catalog(str(self.registry))
        self.assertEqual(len(entries), 1)
        self.assertIn("latin1.json", invalid)
        self.assertIn("UTF-8", invalid["latin1.json"][0])

    def test_a_file_over_the_size_cap_is_listed_as_invalid_without_being_read(self):
        (self.registry / "huge.json").write_bytes(b'{"adapterId": "' + b"a" * (MAX_MANIFEST_BYTES + 10) + b'"}')
        entries, invalid = build_catalog(str(self.registry))
        self.assertEqual(len(entries), 1)
        self.assertIn("larger than", invalid["huge.json"][0])


class _Running:
    def __init__(self, registry: str):
        self.server = serve_catalog(registry, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class ServerEdgeTests(unittest.TestCase):
    def test_a_registry_directory_that_disappears_is_a_503_not_a_dropped_connection(self):
        tmp = tempfile.TemporaryDirectory()
        registry = Path(tmp.name) / "registry"
        registry.mkdir()
        shutil.copy(_a_valid_fixture(), registry / "good.json")
        running = _Running(str(registry))
        try:
            shutil.rmtree(registry)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(f"{running.base}/health", timeout=5)
            self.assertEqual(caught.exception.code, 503)
            self.assertIn("registry", json.loads(caught.exception.read())["error"])
        finally:
            running.close()
            tmp.cleanup()

    def test_a_connection_that_never_sends_a_request_is_dropped_and_the_server_keeps_serving(self):
        running = _Running(str(FIXTURES_DIR))
        try:
            handler_cls = running.server.RequestHandlerClass
            self.assertGreater(handler_cls.timeout, 0)
            handler_cls.timeout = 0.3
            idle = socket.create_connection(("127.0.0.1", running.server.server_port), timeout=5)
            try:
                idle.settimeout(5)
                self.assertEqual(idle.recv(1024), b"", "the server must close an idle connection")
            finally:
                idle.close()
            with urllib.request.urlopen(f"{running.base}/health", timeout=5) as response:
                self.assertEqual(response.status, 200)
        finally:
            running.close()


if __name__ == "__main__":
    unittest.main()
