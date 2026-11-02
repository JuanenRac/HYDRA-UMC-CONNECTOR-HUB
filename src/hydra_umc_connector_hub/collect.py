# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/collect.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Collects the manifests that the bridges publish in their own repositories into the registry directory.

A bridge describes itself: it keeps `docs/adapter-manifest.json` (one adapter) or `docs/adapter-manifests/*.json` (several) in its own checkout. The hub
does not write those descriptions for it; it only gathers them. A manifest is collected only when ALL of this holds:

  * it is a valid adapter manifest (`schema.validate_adapter_manifest`);
  * its `ownerProject` is the name of the checkout it was found in, and that checkout's own `hydra-umc.project.json` says the same `name`, so a
    repository cannot publish an adapter in the name of another one;
  * its `adapterId` is not already taken by a manifest of another project.

The registry directory is only written with `apply=True` (the CLI asks for `--apply`); a plain run reports what it would do. A file that is already
there with the same content is left alone; one with other content from the same owner is replaced; one from another owner is never touched.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schema import PROJECT_NAME_PATTERN, validate_adapter_manifest

MANIFEST_LOCATIONS = ("docs/adapter-manifest.json", "docs/adapter-manifests/*.json")
MAX_MANIFEST_BYTES = 256 * 1024


@dataclass
class CollectReport:
    collected: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"collected": sorted(self.collected), "unchanged": sorted(self.unchanged), "skipped": {k: self.skipped[k] for k in sorted(self.skipped)}}


def _find_manifests(project_dir: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in MANIFEST_LOCATIONS:
        found.extend(sorted(project_dir.glob(pattern)))
    return [path for path in found if path.is_file()]


def _owner_confirmed(project_dir: Path) -> str | None:
    """None when the checkout's own manifest says it is who its directory says; otherwise why not."""
    try:
        data = json.loads((project_dir / "hydra-umc.project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return f"{project_dir.name} has no readable hydra-umc.project.json"
    if not isinstance(data, dict) or data.get("name") != project_dir.name:
        return f"the hydra-umc.project.json of {project_dir.name} does not say it is {project_dir.name}"
    return None


def collect_manifests(ecosystem_root: str, registry_dir: str, *, apply: bool = False) -> CollectReport:
    root = Path(ecosystem_root)
    registry = Path(registry_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"{ecosystem_root!r} is not a directory")
    report = CollectReport()
    owners: dict[str, str] = {}  # adapterId -> ownerProject, over what this run accepted
    # what is already in the registry belongs to its owner; another project cannot take its adapterId
    if registry.is_dir():
        for existing in sorted(registry.glob("*.json")):
            try:
                data = json.loads(existing.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and isinstance(data.get("adapterId"), str) and isinstance(data.get("ownerProject"), str):
                owners.setdefault(data["adapterId"], data["ownerProject"])
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir() and PROJECT_NAME_PATTERN.fullmatch(p.name)):
        for path in _find_manifests(project_dir):
            label = f"{project_dir.name}/{path.relative_to(project_dir).as_posix()}"
            try:
                if path.stat().st_size > MAX_MANIFEST_BYTES:
                    report.skipped[label] = [f"the manifest is larger than {MAX_MANIFEST_BYTES} bytes"]
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                report.skipped[label] = [f"it cannot be read as JSON: {exc}"]
                continue
            errors = validate_adapter_manifest(data)
            if errors:
                report.skipped[label] = errors
                continue
            if data["ownerProject"] != project_dir.name:
                report.skipped[label] = [f"ownerProject {data['ownerProject']!r} is not the checkout it was found in ({project_dir.name!r})"]
                continue
            problem = _owner_confirmed(project_dir)
            if problem:
                report.skipped[label] = [problem]
                continue
            adapter_id = data["adapterId"]
            if owners.get(adapter_id, project_dir.name) != project_dir.name:
                report.skipped[label] = [f"adapterId {adapter_id!r} already belongs to {owners[adapter_id]!r}"]
                continue
            owners[adapter_id] = project_dir.name
            text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            target = registry / f"{adapter_id}.json"
            if target.is_file() and target.read_text(encoding="utf-8") == text:
                report.unchanged.append(adapter_id)
                continue
            if apply:
                registry.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            report.collected.append(adapter_id)
    return report
