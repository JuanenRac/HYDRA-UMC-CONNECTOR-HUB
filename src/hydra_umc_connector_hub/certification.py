# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/certification.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 4 [P1][HARDWARE] - the real, honest software half of "certify
adapters one at a time against their own machine; no universal global
label, every profile keeps its own real evidence" (the audit proposal's
own wording).

What this module IS: a real attestation record - who certified which
adapter, against which real machine model, with which real evidence
payload (checked to actually match that adapter's own declared
`evidenceSchema`, never accepted un-checked) - stored as one real JSON
file per record, append-only, never overwritten.

What this module is deliberately NOT, and never claims to be: an
automated hardware test. There is no code path here that talks to a
real serial port, OPC-UA endpoint or MQTT broker to independently
confirm the supplied evidence actually came from the named machine model
- that would require the real hardware this delivery is explicitly
tagged [HARDWARE] for, which this development machine does not have.
Producing the evidence honestly is the human certifier's own
responsibility, the same way `docs/CERTIFICATION.md` says out loud;
this module's real, verifiable job is to refuse to record a certification
whose evidence does not even match the adapter's own self-declared
shape, and to keep every record it does accept exactly as given, forever
- never silently "improving" or reconciling one later.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schema import validate_adapter_manifest, validate_against_json_schema_subset


class CertificationError(ValueError):
    """Raised for any real reason a certification cannot be honestly
    recorded - an invalid manifest, evidence that does not match the
    adapter's own evidenceSchema, or a missing required field."""


@dataclass(frozen=True)
class CertificationRecord:
    certification_id: str
    adapter_id: str
    machine_model: str
    certified_by: str
    certified_at: str
    evidence: dict[str, Any]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificationId": self.certification_id,
            "adapterId": self.adapter_id,
            "machineModel": self.machine_model,
            "certifiedBy": self.certified_by,
            "certifiedAt": self.certified_at,
            "evidence": dict(self.evidence),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CertificationRecord":
        return cls(
            certification_id=data["certificationId"],
            adapter_id=data["adapterId"],
            machine_model=data["machineModel"],
            certified_by=data["certifiedBy"],
            certified_at=data["certifiedAt"],
            evidence=dict(data.get("evidence", {})),
            notes=data.get("notes", ""),
        )


def _require_non_empty(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CertificationError(f"{field_name!r} must be a non-empty string")


def _require_safe_path_segment(value: Any, field_name: str) -> None:
    """V07-007 (found in an independent revalidation audit, P1):
    `adapter_id`/`certification_id` become part of a real filename under
    a directory the caller controls - checked here independently of
    whatever `validate_adapter_manifest` may or may not have already
    checked, since a `CertificationRecord` can also be built directly
    (e.g. `from_dict()` on untrusted JSON) without ever going through
    that validator at all. `save_certification_record()` also verifies
    the final RESOLVED path stays inside the target directory as a
    second, independent layer - this repo's own established
    belt-and-suspenders style (see canary_deploy.py in HYDRA-UMC-OPS-AGENT
    for the same pattern applied to a different real path-safety risk)."""
    if not isinstance(value, str) or not value.strip():
        raise CertificationError(f"{field_name!r} must be a non-empty string")
    if value in (".", ".."):
        raise CertificationError(f"{field_name} {value!r} is not a safe path segment")
    if "/" in value or "\\" in value:
        raise CertificationError(f"{field_name} {value!r} must not contain a path separator")


def certify_adapter(
    manifest: dict[str, Any],
    *,
    machine_model: str,
    certified_by: str,
    evidence: dict[str, Any],
    notes: str = "",
) -> CertificationRecord:
    """Builds (but does not save) one real `CertificationRecord`. Refuses
    - raising `CertificationError` with every real reason, never just the
    first - unless the manifest is itself structurally valid AND the
    supplied evidence actually matches that manifest's own
    `evidenceSchema`. A human certifier who cannot produce evidence in
    the adapter's own declared shape has not actually certified it."""
    errors = list(validate_adapter_manifest(manifest))
    if not isinstance(evidence, dict):
        errors.append("'evidence' must be a JSON object")
    else:
        errors.extend(validate_against_json_schema_subset(manifest.get("evidenceSchema"), evidence))
    if not isinstance(machine_model, str) or not machine_model.strip():
        errors.append("'machine_model' must be a non-empty string")
    if not isinstance(certified_by, str) or not certified_by.strip():
        errors.append("'certified_by' must be a non-empty string")
    if errors:
        raise CertificationError("; ".join(errors))

    return CertificationRecord(
        certification_id=uuid.uuid4().hex,
        adapter_id=manifest["adapterId"],
        machine_model=machine_model,
        certified_by=certified_by,
        certified_at=datetime.now(timezone.utc).isoformat(),
        evidence=evidence,
        notes=notes,
    )


def save_certification_record(record: CertificationRecord, directory: str) -> str:
    """Writes one real, never-overwritten JSON file for `record` under
    `directory` (created if missing) and returns its real path. The file
    name embeds both the adapterId and the record's own unique id, so two
    real certifications of the same adapter (a re-certification after a
    firmware update, say) both stay on disk side by side - this is an
    append-only log, never a single-slot "latest status" file.

    Two real, independent safety checks make that honest, not just
    documented:

    - V07-007: `adapter_id`/`certification_id` are checked as safe path
      segments (see `_require_safe_path_segment`), AND the final
      resolved path is verified to still be inside `directory` - a
      belt-and-suspenders pair, since either one alone trusts a single
      layer that a future change could weaken.
    - V07-008: the file is created EXCLUSIVELY (`open(..., "x")` -
      real `O_CREAT|O_EXCL` semantics, atomic against a second, real
      concurrent writer). If a file already exists under this exact
      certification_id, saving the byte-for-byte SAME record again is a
      harmless, idempotent no-op (a retried request after a network
      blip, say); saving a DIFFERENT record under the same id is
      refused outright - this store is append-only, never mutated in
      place.
    """
    _require_safe_path_segment(record.adapter_id, "adapter_id")
    _require_safe_path_segment(record.certification_id, "certification_id")

    target_dir = Path(directory).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = (target_dir / f"{record.adapter_id}__{record.certification_id}.json").resolve()
    if not path.is_relative_to(target_dir):
        raise CertificationError(
            f"refusing to write a certification record outside {target_dir} "
            f"(adapterId {record.adapter_id!r} / certification_id {record.certification_id!r} resolved to {path})"
        )

    payload = json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n"
    try:
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(payload)
    except FileExistsError:
        if path.read_text(encoding="utf-8") == payload:
            return str(path)  # V07-008: identical content re-saved - a real, harmless no-op
        raise CertificationError(
            f"refusing to overwrite {path.name} - a DIFFERENT certification record already exists on disk "
            "under this certification_id; this store is append-only and is never mutated in place"
        )
    return str(path)


def load_certification_records(directory: str, adapter_id: str | None = None) -> list[CertificationRecord]:
    """Loads every real certification record under `directory`
    (non-recursive), optionally filtered to one `adapter_id`, sorted by
    `certified_at` so the most recent real certification for an adapter
    is always last - never reordered by file-system listing order, which
    is not a real timestamp."""
    target_dir = Path(directory)
    if not target_dir.is_dir():
        return []
    records: list[CertificationRecord] = []
    for path in sorted(target_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            record = CertificationRecord.from_dict(data)
        except (OSError, ValueError, KeyError):
            continue
        if adapter_id is not None and record.adapter_id != adapter_id:
            continue
        records.append(record)
    records.sort(key=lambda record: record.certified_at)
    return records
