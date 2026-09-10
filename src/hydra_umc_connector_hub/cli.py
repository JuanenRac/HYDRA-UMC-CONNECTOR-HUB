# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real CLI entry point for every delivery this project ships so far:
`validate` (Delivery 1), `catalog`/`serve-catalog` (Delivery 2), `gate`
(Delivery 3), `certify`/`certifications` (Delivery 4). See
docs/CLI_REFERENCE.md for the exact, versioned command surface."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .certification import CertificationError, certify_adapter, load_certification_records, save_certification_record
from .registry import build_catalog, load_full_manifest
from .schema import load_and_validate
from .sdk_gate import CapabilityCallRequest, CapabilityGateError, SdkUnavailableError, evaluate_capability_call


def _cmd_validate(args: argparse.Namespace) -> int:
    overall_ok = True
    for path in args.manifest_file:
        data, errors = load_and_validate(path)
        if data is None:
            # errors[0] is the real read/parse failure message.
            print(f"ERROR: {path}: {errors[0]}", file=sys.stderr)
            overall_ok = False
            continue
        if errors:
            # `data` is real (JSON parsed) but not necessarily a dict - a
            # review found a bare `[]`/`"..."`/`123` top-level document
            # reaching `data.get(...)` here and crashing with a bare
            # AttributeError, aborting the whole batch instead of reporting
            # every file's own real errors.
            adapter_id = data.get("adapterId") if isinstance(data, dict) else None
            print(f"INVALID {path} (adapterId={adapter_id!r}):", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            overall_ok = False
            continue
        print(f"VALID {path} adapterId={data['adapterId']!r} ownerProject={data['ownerProject']!r}")
    return 0 if overall_ok else 1


def _cmd_catalog(args: argparse.Namespace) -> int:
    entries, invalid_files = build_catalog(args.registry_dir)
    payload = {"adapters": [entry.to_dict() for entry in entries], "invalidFiles": invalid_files}
    print(json.dumps(payload, indent=2))
    return 0 if not invalid_files else 1


def _cmd_serve_catalog(args: argparse.Namespace) -> int:
    from .catalog_server import serve_catalog

    server = serve_catalog(args.registry_dir, host=args.host, port=args.port)
    print(f"serving read-only catalog for {args.registry_dir!r} on http://{server.server_address[0]}:{server.server_port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _cmd_gate(args: argparse.Namespace) -> int:
    manifest, errors = load_and_validate(args.manifest_file)
    if manifest is None or errors:
        print(f"ERROR: {args.manifest_file} is not a valid adapter manifest: {errors}", file=sys.stderr)
        return 1

    parameters: dict[str, str] = {}
    for raw in args.param or []:
        if "=" not in raw:
            print(f"ERROR: --param {raw!r} must look like key=value", file=sys.stderr)
            return 1
        key, _, value = raw.partition("=")
        parameters[key] = value

    evidence = _load_json_file(args.evidence_file) if args.evidence_file else None

    try:
        request = CapabilityCallRequest(
            job_id=args.job_id,
            idempotency_key=args.idempotency_key,
            source=args.source,
            capability_name=args.capability,
            cell_state=args.cell_state,
            machine_state=args.machine_state,
            parameters=parameters,
            evidence=evidence,
            # V07-006: a write/abort capability's own declared
            # requiredPermission/requiredCellState/requiresHumanConfirmation/
            # requiredSafetyGates are now real, enforced checks - a CLI
            # caller must attest to them explicitly, the same way it
            # already attests to --cell-state/--machine-state.
            granted_permissions=frozenset(args.permission or []),
            cell_mode=args.cell_mode,
            human_confirmed=args.human_confirmed,
            satisfied_safety_gates=frozenset(args.safety_gate or []),
        )
        result = evaluate_capability_call(manifest, request)
    except (CapabilityGateError, SdkUnavailableError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.allowed else 1


def _cmd_certify(args: argparse.Namespace) -> int:
    manifest, errors = load_and_validate(args.manifest_file)
    if manifest is None or errors:
        print(f"ERROR: {args.manifest_file} is not a valid adapter manifest: {errors}", file=sys.stderr)
        return 1
    evidence = _load_json_file(args.evidence_file)
    try:
        record = certify_adapter(
            manifest,
            machine_model=args.machine_model,
            certified_by=args.certified_by,
            evidence=evidence,
            notes=args.notes or "",
        )
    except CertificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    path = save_certification_record(record, args.out_dir)
    print(f"CERTIFIED adapterId={record.adapter_id!r} certificationId={record.certification_id!r} -> {path}")
    return 0


def _cmd_certifications(args: argparse.Namespace) -> int:
    records = load_certification_records(args.dir, adapter_id=args.adapter_id)
    print(json.dumps([record.to_dict() for record in records], indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydra-umc-connector-hub",
        description="Adapter-manifest registry, catalog, safety gate and certification records for the HYDRA-UMC/URTC ecosystem.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate one or more adapter-manifest JSON files.")
    validate.add_argument("manifest_file", nargs="+", help="Path(s) to adapter-manifest JSON file(s).")
    validate.set_defaults(func=_cmd_validate)

    catalog = subparsers.add_parser("catalog", help="Print the real read-only catalog built from a directory of manifest files.")
    catalog.add_argument("--registry-dir", required=True, help="Directory scanned (non-recursive) for *.json adapter manifests.")
    catalog.set_defaults(func=_cmd_catalog)

    serve_catalog_cmd = subparsers.add_parser("serve-catalog", help="Serve the real read-only catalog over HTTP (GET-only).")
    serve_catalog_cmd.add_argument("--registry-dir", required=True, help="Directory scanned (non-recursive) for *.json adapter manifests.")
    serve_catalog_cmd.add_argument("--host", default="127.0.0.1")
    serve_catalog_cmd.add_argument("--port", type=int, default=8801)
    serve_catalog_cmd.set_defaults(func=_cmd_serve_catalog)

    gate = subparsers.add_parser("gate", help="Evaluate one capability call against HYDRA-UMC-SDK's own real safety gate.")
    gate.add_argument("manifest_file")
    gate.add_argument("--capability", required=True)
    gate.add_argument("--job-id", required=True)
    gate.add_argument("--idempotency-key", required=True)
    gate.add_argument("--source", required=True)
    gate.add_argument("--cell-state", required=True, help="One of READY/INHIBITED/FAULT/SAFE_STOP.")
    gate.add_argument("--machine-state", required=True, help="One of OFFLINE/IDLE/RUNNING/HOLDING/FAULT/SAFE_STOP.")
    gate.add_argument("--param", action="append", help="key=value, repeatable.")
    gate.add_argument("--evidence-file", help="Optional path to a JSON evidence payload checked against evidenceSchema.")
    gate.add_argument(
        "--permission", action="append",
        help="A permission the caller attests to holding, repeatable - checked against the capability's own requiredPermission (V07-006).",
    )
    gate.add_argument(
        "--cell-mode",
        help="The cell's current real supervision mode (e.g. operational/supervised/ready) - checked against the capability's own requiredCellState (V07-006). Distinct from --cell-state, which is HYDRA-UMC-SDK's own generic motion-gate state.",
    )
    gate.add_argument(
        "--human-confirmed", action="store_true",
        help="Pass this if a human has explicitly confirmed this specific call - checked against the capability's own requiresHumanConfirmation (V07-006).",
    )
    gate.add_argument(
        "--safety-gate", action="append",
        help="A real safety gate currently satisfied, repeatable - checked against the manifest's own requiredSafetyGates (V07-006).",
    )
    gate.set_defaults(func=_cmd_gate)

    certify = subparsers.add_parser("certify", help="Record a real, human-attested hardware certification for one adapter.")
    certify.add_argument("manifest_file")
    certify.add_argument("--machine-model", required=True)
    certify.add_argument("--certified-by", required=True)
    certify.add_argument("--evidence-file", required=True, help="Path to a JSON evidence payload matching this adapter's own evidenceSchema.")
    certify.add_argument("--notes", default="")
    certify.add_argument("--out-dir", required=True, help="Directory certification records are saved into, one JSON file per record.")
    certify.set_defaults(func=_cmd_certify)

    certifications = subparsers.add_parser("certifications", help="List real, previously saved certification records.")
    certifications.add_argument("--dir", required=True)
    certifications.add_argument("--adapter-id", help="Filter to one adapterId; omit to list every record.")
    certifications.set_defaults(func=_cmd_certifications)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
