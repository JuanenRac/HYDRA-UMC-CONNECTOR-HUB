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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import load_and_validate


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
