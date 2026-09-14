# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 2: registers the real, already-existing bridges as a real
read-only catalog - never a second protocol implementation, never a live
connection to any machine. A registry entry IS the adapter-manifest file
already validated by `schema.py`; this module only discovers a directory
of them, keeps the ones that are structurally valid, and builds the small
summary shape a catalog client (Server/Studio/Suite/Updater) actually
needs - it never invents a field
the manifest itself does not declare.

A manifest that fails `validate_adapter_manifest()` is never silently
dropped: it is kept out of the catalog itself (a broken contract must
never look selectable) but its own real errors are still reported back
to the caller/CLI, the same "report every reason, do not swallow one"
standard `schema.py` already holds itself to.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import PROJECT_NAME_PATTERN, load_and_validate


@dataclass(frozen=True)
class CatalogEntry:
    """The real, read-only summary of one registered adapter - deliberately
    smaller than the full manifest (no `endpointSchema`/`evidenceSchema`
    bodies, which can be verbose and are only needed by a real caller
    once it already knows which adapter it wants)."""

    adapter_id: str
    protocol: str
    target_kinds: list[str]
    owner_project: str
    sdk_compatibility: str
    idempotency: str
    capabilities: list[dict[str, Any]]
    source_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "protocol": self.protocol,
            "targetKinds": list(self.target_kinds),
            "ownerProject": self.owner_project,
            "sdkCompatibility": self.sdk_compatibility,
            "idempotency": self.idempotency,
            "capabilities": [dict(capability) for capability in self.capabilities],
            "sourcePath": self.source_path,
        }


def _entry_from_manifest(data: dict[str, Any], source_path: str) -> CatalogEntry:
    capabilities = [
        {"name": capability.get("name"), "mode": capability.get("mode")}
        for capability in data.get("capabilities", [])
        if isinstance(capability, dict)
    ]
    return CatalogEntry(
        adapter_id=data["adapterId"],
        protocol=data["protocol"],
        target_kinds=list(data.get("targetKinds", [])),
        owner_project=data["ownerProject"],
        sdk_compatibility=data["sdkCompatibility"],
        idempotency=data["idempotency"],
        capabilities=capabilities,
        source_path=source_path,
    )


def build_catalog(registry_dir: str) -> tuple[list[CatalogEntry], dict[str, list[str]]]:
    """Scans every real `*.json` file directly inside `registry_dir`
    (non-recursive - a nested `invalid/` fixtures directory is exactly
    the kind of thing that must NOT silently join a real catalog) and
    returns `(entries, invalid_files)`. `entries` is sorted by
    `adapter_id` so a catalog's own output is stable across runs on the
    same registry contents - a real client should never see adapters
    reorder themselves for no reason. `invalid_files` maps a relative
    file name to its real validation errors, for a caller that wants to
    report why a file did not make it into the catalog."""
    directory = Path(registry_dir)
    if not directory.is_dir():
        raise NotADirectoryError(f"{registry_dir!r} is not a real directory")

    entries: list[CatalogEntry] = []
    invalid_files: dict[str, list[str]] = {}
    seen_adapter_ids: dict[str, str] = {}

    for path in sorted(directory.glob("*.json")):
        data, errors = load_and_validate(str(path))
        if data is None:
            invalid_files[path.name] = errors
            continue
        if errors:
            invalid_files[path.name] = errors
            continue
        adapter_id = data["adapterId"]
        if adapter_id in seen_adapter_ids:
            invalid_files[path.name] = [
                f"adapterId {adapter_id!r} is already registered by {seen_adapter_ids[adapter_id]!r} - "
                "adapterId must be unique across the whole registry"
            ]
            continue
        seen_adapter_ids[adapter_id] = path.name
        entries.append(_entry_from_manifest(data, str(path)))

    entries.sort(key=lambda entry: entry.adapter_id)
    return entries, invalid_files


def catalog_snapshot_version(entries: list[CatalogEntry], invalid_files: dict[str, list[str]]) -> str:
    """PROM-HUB-E01's own real "versioned snapshot" half: a deterministic
    SHA-256 over `entries`' + `invalid_files`' own real, canonical
    content - never a random id, never a timestamp (two back-to-back
    calls against an unchanged real registry directory must return the
    exact same version). Changes if and only if a real adapter is
    added/removed/edited, or a file starts/stops failing validation -
    `build_catalog()` itself stays a fresh per-call scan (Delivery 2's
    own design, see this module's header comment on why: a registry
    directory is real, live filesystem state, never cached across
    calls), so this is computed fresh every time too, from whatever that
    scan just found - never a stale cached hash going out of sync with
    what a caller's own `entries` actually says right now.

    A real HTTP caller (`catalog_server.py`) turns this into a real
    `ETag` - the "transactional reload" half: a client sends
    `If-None-Match` back and gets a real, fresh, honest `304 Not Modified`
    exactly when nothing changed, or a real, freshly-and-fully-rescanned
    body when it did - never a torn read mixing an old and a new scan,
    since each response is one complete scan compared as a whole, not a
    partial diff applied to cached state."""
    canonical = json.dumps(
        {
            "adapters": [entry.to_dict() for entry in entries],
            "invalidFiles": invalid_files,
        },
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_catalog_owners(entries: list[CatalogEntry], ecosystem_root: str) -> dict[str, str]:
    """PROM-HUB-F02's own real second half: `schema.py`'s own
    `PROJECT_NAME_PATTERN` check on `ownerProject` only confirms a value
    LOOKS like a real project name - it never confirms the claimed owner
    actually exists. This function does that for real: for every entry,
    resolves `ecosystem_root / ownerProject / hydra-umc.project.json`
    and requires it to (a) exist and (b) itself declare `name` equal to
    that same `ownerProject` - the same self-consistency check
    HYDRA-UMC-LOCAL-TECHNICIAN's own `resolve_project_manifest_path()`
    already applies, ported here rather than imported (this project
    stays independent, same real property every other shared-but-not-
    centralized piece of this ecosystem already follows).

    Returns a real reason string per adapter_id that FAILS verification
    - an adapter whose owner cannot be confirmed is never silently kept
    in an already-trusted-looking catalog, but this function itself
    never mutates `entries`; a caller (catalog_server.py, cli.py)
    decides what to do with a failing entry (typically: keep it out of
    what is presented as a verified catalog, same as an invalid_files
    entry). A caller with no real `ecosystem_root` available at all
    should not call this - there is nothing honest to verify against."""
    root = Path(ecosystem_root)
    failures: dict[str, str] = {}
    for entry in entries:
        owner = entry.owner_project
        if not PROJECT_NAME_PATTERN.fullmatch(owner):
            # Already caught by schema.py at manifest-validation time for
            # every real caller that runs it first - this is real
            # defense in depth, not the primary check.
            failures[entry.adapter_id] = f"ownerProject {owner!r} does not look like a real project name"
            continue
        manifest_path = (root / owner / "hydra-umc.project.json").resolve()
        if root.resolve() not in manifest_path.parents:
            failures[entry.adapter_id] = f"ownerProject {owner!r} does not resolve under {root}"
            continue
        if not manifest_path.is_file():
            failures[entry.adapter_id] = f"no real hydra-umc.project.json found for ownerProject {owner!r} under {root}"
            continue
        try:
            owner_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures[entry.adapter_id] = f"ownerProject {owner!r}'s own manifest at {manifest_path} could not be read: {exc}"
            continue
        if not isinstance(owner_manifest, dict) or owner_manifest.get("name") != owner:
            failures[entry.adapter_id] = (
                f"ownerProject {owner!r}'s own manifest at {manifest_path} does not self-identify as {owner!r}"
            )
    return failures


def load_full_manifest(registry_dir: str, adapter_id: str) -> dict[str, Any] | None:
    """Returns the full, real manifest dict for one adapter already known
    to the catalog, or None if no registered (structurally valid) file in
    `registry_dir` declares that `adapterId`. Used by the catalog server's
    own per-adapter detail endpoint - a summary `CatalogEntry` is not
    enough once a real caller needs the full `capabilities`/
    `endpointSchema`/`evidenceSchema` bodies for one specific adapter."""
    entries, _ = build_catalog(registry_dir)
    for entry in entries:
        if entry.adapter_id == adapter_id:
            data, errors = load_and_validate(entry.source_path)
            if data is not None and not errors:
                return data
    return None
