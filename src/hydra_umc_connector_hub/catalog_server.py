# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/catalog_server.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 2's own real read-only catalog endpoint - `http.server` only,
deliberately no web framework: three GET routes, nothing else. There is
no `do_POST`/`do_PUT`/`do_DELETE` anywhere in this module, so any write
attempt gets `BaseHTTPRequestHandler`'s own honest 501, never a route
this project forgot to protect. A real client (Server/Studio/Suite/
Updater, per the audit proposal's own item 5) is meant to poll `/catalog`
to discover which adapters exist and what they can do, then fetch
`/catalog/<adapterId>` once it knows which one it wants - it never gets a
way to invoke a capability from this module (that is Delivery 3's own,
separate, explicitly-gated `sdk_gate.py`)."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .registry import build_catalog, load_full_manifest


def _make_handler(registry_dir: str) -> type[BaseHTTPRequestHandler]:
    class CatalogRequestHandler(BaseHTTPRequestHandler):
        server_version = "HydraUmcConnectorHubCatalog/0.1"

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's own naming
            if self.path == "/health":
                entries, invalid_files = build_catalog(registry_dir)
                self._send_json(200, {"status": "ok", "adapterCount": len(entries), "invalidFileCount": len(invalid_files)})
                return
            if self.path == "/catalog":
                entries, invalid_files = build_catalog(registry_dir)
                self._send_json(200, {"adapters": [entry.to_dict() for entry in entries], "invalidFiles": invalid_files})
                return
            if self.path.startswith("/catalog/"):
                adapter_id = self.path[len("/catalog/"):]
                manifest = load_full_manifest(registry_dir, adapter_id)
                if manifest is None:
                    self._send_json(404, {"error": f"no registered adapter with adapterId {adapter_id!r}"})
                    return
                self._send_json(200, manifest)
                return
            self._send_json(404, {"error": f"unknown route {self.path!r} - see docs/CLI_REFERENCE.md"})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - matches base signature
            # Real requests still get logged, just to stderr via the
            # standard logging module rather than BaseHTTPRequestHandler's
            # default raw stdout write, so `serve-catalog`'s own stdout
            # stays reserved for the one real startup line the CLI prints.
            import sys

            print(f"{self.address_string()} - {format % args}", file=sys.stderr)

    return CatalogRequestHandler


def serve_catalog(registry_dir: str, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Builds and returns a real, already-bound `ThreadingHTTPServer` -
    the caller decides whether to call `.serve_forever()` (the real CLI
    path) or drive it manually with `.handle_request()` (what this
    project's own tests do, against a real ephemeral port, never a
    mocked socket). `port=0` (the default) lets the OS assign a free
    real port, read back afterwards via `server.server_port` - the same
    pattern this project's own test suite already needs to avoid ever
    colliding with a port some other real process on this machine owns."""
    handler_cls = _make_handler(registry_dir)
    return ThreadingHTTPServer((host, port), handler_cls)
