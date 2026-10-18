# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/catalog_server.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Delivery 2's own real read-only catalog endpoint - `http.server` only,
deliberately no web framework: three GET routes, nothing else. There is
no `do_POST`/`do_PUT`/`do_DELETE` anywhere in this module, so any write
attempt gets `BaseHTTPRequestHandler`'s own honest 501, never a route
this project forgot to protect. A real client (Server/Studio/Suite/
Updater) is meant to poll `/catalog`
to discover which adapters exist and what they can do, then fetch
`/catalog/<adapterId>` once it knows which one it wants - it never gets a
way to invoke a capability from this module (that is Delivery 3's own,
separate, explicitly-gated `sdk_gate.py`)."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from .registry import build_catalog, catalog_snapshot_version, load_full_manifest, verify_catalog_owners


def _etag_matches(header: str, version: str) -> bool:
    """True when an `If-None-Match` header (a list of entity tags, each possibly weak, or `*`) names this version."""
    for candidate in header.split(","):
        candidate = candidate.strip()
        if candidate == "*":
            return True
        if candidate.startswith("W/"):
            candidate = candidate[2:]
        if candidate.strip('"') == version:
            return True
    return False


def _make_handler(registry_dir: str, ecosystem_root: str | None = None) -> type[BaseHTTPRequestHandler]:
    class CatalogRequestHandler(BaseHTTPRequestHandler):
        server_version = "HydraUmcConnectorHubCatalog"
        # A client that connects and then goes quiet must not hold a thread forever.
        timeout = 15.0

        def _send_json(self, status: int, payload: Any, *, etag: str | None = None) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if etag is not None:
                self.send_header("ETag", f'"{etag}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's own naming
            try:
                self._route()
            except (NotADirectoryError, FileNotFoundError, PermissionError) as exc:
                # The registry directory vanished (or became unreadable) after
                # the server started: answer that, instead of dropping the
                # connection with a traceback and no response at all.
                self._send_json(503, {"error": f"the registry directory is not readable: {exc}"})

        def _scan(self):
            """The catalog scan, with the entries whose owner project cannot be confirmed moved out when an ecosystem root was given."""
            entries, invalid_files = build_catalog(registry_dir)
            unverified: dict[str, str] = {}
            if ecosystem_root:
                unverified = verify_catalog_owners(entries, ecosystem_root)
                entries = [entry for entry in entries if entry.adapter_id not in unverified]
            return entries, invalid_files, unverified

        def _route(self) -> None:
            # the query string and a trailing slash do not make a different route
            route = urlsplit(self.path).path
            if len(route) > 1 and route.endswith("/"):
                route = route.rstrip("/")
            if route == "/health":
                entries, invalid_files, _unverified = self._scan()
                self._send_json(200, {"status": "ok", "adapterCount": len(entries), "invalidFileCount": len(invalid_files)})
                return
            if route == "/catalog":
                # a real, deterministic snapshot version
                # (never random, never a timestamp) computed fresh from
                # THIS scan - a real ETag, not a stale cached one. A
                # client sending back the same If-None-Match it was
                # given gets a real, honest 304 the instant the
                # underlying registry genuinely has not changed, never a
                # partial/torn body.
                entries, invalid_files, unverified = self._scan()
                version = catalog_snapshot_version(entries, invalid_files)
                if _etag_matches(self.headers.get("If-None-Match", ""), version):
                    self.send_response(304)
                    self.send_header("ETag", f'"{version}"')
                    self.end_headers()
                    return
                payload = {
                    "adapters": [entry.to_dict() for entry in entries],
                    "invalidFiles": invalid_files,
                    "snapshotVersion": version,
                }
                if ecosystem_root:
                    payload["unverifiedOwners"] = unverified
                self._send_json(200, payload, etag=version)
                return
            if route.startswith("/catalog/"):
                adapter_id = route[len("/catalog/"):]
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


def serve_catalog(registry_dir: str, host: str = "127.0.0.1", port: int = 0, ecosystem_root: str | None = None) -> ThreadingHTTPServer:
    """Builds and returns a real, already-bound `ThreadingHTTPServer` -
    the caller decides whether to call `.serve_forever()` (the real CLI
    path) or drive it manually with `.handle_request()` (what this
    project's own tests do, against a real ephemeral port, never a
    mocked socket). `port=0` (the default) lets the OS assign a free
    real port, read back afterwards via `server.server_port` - the same
    pattern this project's own test suite already needs to avoid ever
    colliding with a port some other real process on this machine owns.

    `ecosystem_root`, when given, makes the catalog list only the adapters whose
    `ownerProject` is confirmed by that project's own manifest under that
    directory; the others are reported under `unverifiedOwners`."""
    handler_cls = _make_handler(registry_dir, ecosystem_root)
    return ThreadingHTTPServer((host, port), handler_cls)
