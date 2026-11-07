# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Real CLI entry point for every delivery this project ships so far:
`validate` (Delivery 1), `catalog`/`serve-catalog` (Delivery 2), `gate`
(Delivery 3), `certify`/`certifications` (Delivery 4). See
docs/CLI_REFERENCE.md for the exact, versioned command surface."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from . import __version__
from . import ledger
from .certification import CertificationError, certify_adapter, load_certification_records, save_certification_record
from .registry import build_catalog, catalog_snapshot_version, verify_catalog_owners
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
    payload: dict[str, Any] = {
        "adapters": [entry.to_dict() for entry in entries],
        "invalidFiles": invalid_files,
        "snapshotVersion": catalog_snapshot_version(entries, invalid_files),
    }
    unverified_owners: dict[str, str] = {}
    if args.ecosystem_root:
        # only run when the caller has a real ecosystem
        # root to verify against - there is nothing honest to check
        # without one, and `--ecosystem-root` stays optional so a
        # caller with no sibling checkouts available (a CI job testing
        # only this repo's own fixtures, say) is never forced to fail
        # every entry for a reason unrelated to the manifest itself.
        unverified_owners = verify_catalog_owners(entries, args.ecosystem_root)
        payload["unverifiedOwners"] = unverified_owners
    print(json.dumps(payload, indent=2))
    return 0 if not invalid_files and not unverified_owners else 1


def _cmd_serve_catalog(args: argparse.Namespace) -> int:
    from .catalog_server import serve_catalog

    places = None
    if args.endpoints_file:
        from .health_probe import ProbeProfileError, load_profile

        try:
            places = load_profile(args.endpoints_file)
        except ProbeProfileError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    server = serve_catalog(args.registry_dir, host=args.host, port=args.port, ecosystem_root=args.ecosystem_root, places=places)
    print(f"serving read-only catalog for {args.registry_dir!r} on http://{server.server_address[0]}:{server.server_port} (Ctrl+C to stop)")  # type: ignore[str-bytes-safe]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _cmd_probe(args: argparse.Namespace) -> int:
    from .health_probe import ProbeProfileError, active_probes_enabled, load_profile, run_health_check
    from .registry import load_full_manifest

    try:
        places = load_profile(args.endpoints_file)
    except ProbeProfileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    wanted = [args.adapter_id] if args.adapter_id else sorted(places)
    results = []
    for adapter_id in wanted:
        manifest = load_full_manifest(args.registry_dir, adapter_id)
        place = places.get(adapter_id)
        if manifest is None or place is None:
            print(f"ERROR: {adapter_id!r} is not both in the registry and in the endpoints file", file=sys.stderr)
            return 1
        try:
            results.append(run_health_check(manifest, place, timeout=args.timeout, active=active_probes_enabled()).to_dict())
        except ProbeProfileError as exc:
            print(f"ERROR: {adapter_id}: {exc}", file=sys.stderr)
            return 1
    print(json.dumps({"results": results}, indent=2))
    return 0 if all(item["healthy"] for item in results) else 1


def _cmd_collect(args: argparse.Namespace) -> int:
    from .collect import collect_manifests

    try:
        report = collect_manifests(args.ecosystem_root, args.registry_dir, apply=args.apply)
    except NotADirectoryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    payload = report.to_dict()
    payload["applied"] = bool(args.apply)
    print(json.dumps(payload, indent=2))
    return 0 if not report.skipped else 1


def _gate_settings(path: str | None) -> dict:
    """The settings file of `serve-gate` (JSON object: `identityKeyFile`, `allowLoopbackNoIdentity` and the block `identity`: `jwks_url`, `accept_hs256`,
    `jwks_ttl_s`, `jwks_min_refetch_s`, `jwks_timeout_s`); the command line wins over it."""
    if not path:
        return {}
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"the settings file cannot be read: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("the settings file must hold a JSON object")
    return data


def _build_token_verifier(settings: dict, identity_key: bytes | None):
    """The verifier from the `identity` block of the settings: None when no key set address is given (the plain HS256 key is used as always)."""
    from .identity import TokenVerifier
    from .jwks import JwksClient

    block = settings.get("identity")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ValueError("the `identity` block of the settings must be a JSON object")
    unknown = set(block) - {"jwks_url", "accept_hs256", "jwks_ttl_s", "jwks_min_refetch_s", "jwks_timeout_s"}
    if unknown:
        raise ValueError(f"unknown settings in `identity`: {', '.join(sorted(unknown))}")
    accept = block.get("accept_hs256", True)
    if not isinstance(accept, bool):
        raise ValueError("identity.accept_hs256 must be true or false")
    url = block.get("jwks_url")
    jwks = None
    if url is not None:
        options = {name[len("jwks_"):]: block[name] for name in ("jwks_ttl_s", "jwks_min_refetch_s", "jwks_timeout_s") if name in block}
        jwks = JwksClient(url, **options)
    elif any(name in block for name in ("jwks_ttl_s", "jwks_min_refetch_s", "jwks_timeout_s")):
        raise ValueError("identity.jwks_ttl_s and the other key set options need identity.jwks_url")
    if jwks is None and not accept and identity_key is not None:
        raise ValueError("identity.accept_hs256 is off and no identity.jwks_url is given: nothing would verify a token")
    if jwks is None and identity_key is None:
        return None   # nothing to build: the loopback switch or the missing key is decided by GateServiceConfig as before
    return TokenVerifier(hs256_key=identity_key, jwks=jwks, accept_hs256=accept)


IDENTITY_KEY_FILE_VARIABLE = "HYDRA_UMC_CONNECTOR_HUB_IDENTITY_KEY_FILE"


def _cmd_serve_gate(args: argparse.Namespace) -> int:
    from pathlib import Path

    from .gate_audit import GateAudit, GateAuditError, load_key
    from .gate_server import GateServiceConfig, http_cell_state_provider, serve_gate
    from .identity import load_identity_key

    try:
        settings = _gate_settings(args.config_file)
        # the command line first, then the variable that the identity command of HYDRA-UMC-OS sets for every service of the family, then the settings file
        key_file = args.identity_key_file or os.environ.get(IDENTITY_KEY_FILE_VARIABLE, "").strip() or settings.get("identityKeyFile")
        allow_loopback = bool(args.allow_loopback_no_identity or settings.get("allowLoopbackNoIdentity") is True)
        identity_key = load_identity_key(key_file) if key_file else None
        verifier = _build_token_verifier(settings, identity_key)
        key = load_key(args.audit_key_file) if args.audit_key_file else None
        audit = GateAudit(args.audit_file, key)
        lake_token = Path(args.datalake_token_file).read_text(encoding="utf-8").strip() if args.datalake_token_file else None
        cell_token = Path(args.cell_state_token_file).read_text(encoding="utf-8").strip() if args.cell_state_token_file else None
        cell_state = (
            http_cell_state_provider(args.cell_state_url, cell_token, max_age_s=args.cell_state_max_age_s) if args.cell_state_url else None
        )
        config = GateServiceConfig(
            args.registry_dir, audit, identity_key=identity_key, token_verifier=verifier, allow_loopback_no_identity=allow_loopback,
            cell_state=cell_state, datalake_url=args.datalake_url, datalake_token=lake_token, settings_file=args.config_file,
        )
    except (OSError, ValueError, GateAuditError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if allow_loopback:
        print("WARNING: allowLoopbackNoIdentity is ON: a caller on this machine is answered without a signed token", file=sys.stderr)
    if key is None:
        print("WARNING: no --audit-key-file: the audit chain is tamper-evident but not sealed", file=sys.stderr)
    if cell_state is None:
        print("WARNING: no --cell-state-url: the cell state is whatever the caller says it is (attested)", file=sys.stderr)
    try:
        server = serve_gate(config, host=args.host, port=args.port)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"serving the capability gate for {args.registry_dir!r} on http://{server.server_address[0]}:{server.server_port} (Ctrl+C to stop)")  # type: ignore[str-bytes-safe]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


class _EvidenceFileError(Exception):
    """The evidence file could not be read as JSON."""


def _load_json_file(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, RecursionError) as exc:
        raise _EvidenceFileError(f"could not read {path} as JSON: {exc}") from exc


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

    try:
        evidence = _load_json_file(args.evidence_file) if args.evidence_file else None
    except _EvidenceFileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

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
            # a write/abort capability's own declared
            # requiredPermission/requiredCellState/requiresHumanConfirmation/
            # requiredSafetyGates are now real, enforced checks - a CLI
            # caller must attest to them explicitly, the same way it
            # already attests to --cell-state/--machine-state.
            granted_permissions=frozenset(args.permission or []),
            cell_mode=args.cell_mode,
            human_confirmed=args.human_confirmed,
            satisfied_safety_gates=frozenset(args.safety_gate or []),
            observed_machine_state=args.observed_machine_state,
            allow_unobserved=args.allow_unobserved,
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
    try:
        evidence = _load_json_file(args.evidence_file)
    except _EvidenceFileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
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
    key = None
    if args.key_file:
        try:
            key = ledger.load_key(args.key_file)
        except ledger.LedgerError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    try:
        path = save_certification_record(record, args.out_dir, key=key)
    except (CertificationError, OSError) as exc:
        print(f"ERROR: could not save the certification record: {exc}", file=sys.stderr)
        return 1
    print(f"CERTIFIED adapterId={record.adapter_id!r} certificationId={record.certification_id!r} -> {path}" + (" (sealed in the chain)" if key else ""))
    return 0


def _cmd_verify_certifications(args: argparse.Namespace) -> int:
    try:
        key = ledger.load_key(args.key_file)
    except ledger.LedgerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    report = ledger.verify_chain(args.dir, key, strict=args.strict)
    print(json.dumps(report.to_dict(), indent=2))
    print(("CHAIN=PASS" if report.ok else "CHAIN=FAIL") + f" {report.sealed} sealed record(s), {len(report.unsealed)} outside the chain")
    return 0 if report.ok else 1


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
    catalog.add_argument(
        "--ecosystem-root",
        help="Optional: a real directory of sibling HYDRA-UMC-*/URTC-* checkouts. When given, every entry's "
        "own ownerProject is verified for real against that project's own hydra-umc.project.json "
        "and any failure is reported under 'unverifiedOwners'. Omitted, ownerProject stays only shape-checked.",
    )
    catalog.set_defaults(func=_cmd_catalog)

    serve_catalog_cmd = subparsers.add_parser("serve-catalog", help="Serve the real read-only catalog over HTTP (GET-only).")
    serve_catalog_cmd.add_argument("--registry-dir", required=True, help="Directory scanned (non-recursive) for *.json adapter manifests.")
    serve_catalog_cmd.add_argument("--host", default="127.0.0.1")
    serve_catalog_cmd.add_argument("--port", type=int, default=8801)
    serve_catalog_cmd.add_argument(
        "--ecosystem-root",
        help="Optional: a directory of sibling HYDRA-UMC-*/URTC-* checkouts. When given, only adapters whose ownerProject is "
        "confirmed by that project's own hydra-umc.project.json are listed; the others appear under 'unverifiedOwners'.",
    )
    serve_catalog_cmd.add_argument(
        "--endpoints-file",
        help="Optional: a JSON file {adapterId: {host, port, scheme}} with the places of the adapters. With it GET /probe/<adapterId> runs the healthCheck of the manifest "
        "against that place (cached for 5 seconds). Without it the route answers 404 and the catalog stays read-only.",
    )
    serve_catalog_cmd.set_defaults(func=_cmd_serve_catalog)

    probe = subparsers.add_parser("probe", help="Run the healthCheck declared by the adapters against the places listed in an endpoints file. Exit 1 if any is unhealthy.")
    probe.add_argument("--registry-dir", required=True)
    probe.add_argument("--endpoints-file", required=True, help="JSON {adapterId: {host, port, scheme}}.")
    probe.add_argument("--adapter-id", help="Only this adapter; omit to probe every entry of the endpoints file.")
    probe.add_argument("--timeout", type=float, help="Seconds to wait (default: the timeoutMs of the manifest).")
    probe.set_defaults(func=_cmd_probe)

    collect = subparsers.add_parser("collect", help="Gather the manifests the bridges publish in their own checkouts (docs/adapter-manifest.json) into the registry directory.")
    collect.add_argument("--ecosystem-root", required=True, help="Directory of sibling HYDRA-UMC-*/URTC-* checkouts.")
    collect.add_argument("--registry-dir", required=True)
    collect.add_argument("--apply", action="store_true", help="Write the registry; without it only report what would be collected.")
    collect.set_defaults(func=_cmd_collect)

    serve_gate_cmd = subparsers.add_parser("serve-gate", help="Serve the capability gate over HTTP (POST /gate/evaluate), every decision recorded.")
    serve_gate_cmd.add_argument("--registry-dir", required=True)
    serve_gate_cmd.add_argument("--identity-key-file", help="File with the key that verifies the signed tokens of HYDRA-UMC-SERVER (its JWT_SECRET, 32+ characters). Required unless the loopback switch is on.")
    serve_gate_cmd.add_argument("--allow-loopback-no-identity", action="store_true", help="OFF by default. Answer a caller on this machine that has no token; only with a loopback --host.")
    serve_gate_cmd.add_argument("--config-file", help="JSON settings: identityKeyFile, allowLoopbackNoIdentity (the command line wins).")
    serve_gate_cmd.add_argument("--audit-file", required=True, help="JSON-lines file of the decisions (hash chain).")
    serve_gate_cmd.add_argument("--audit-key-file", help="Optional: a secret (16+ characters) that seals each line of the audit chain.")
    serve_gate_cmd.add_argument("--cell-state-url", help="Optional: GET URL that answers the safety state of the cell; the service then reads it itself and ignores the caller's claim.")
    serve_gate_cmd.add_argument("--cell-state-token-file")
    serve_gate_cmd.add_argument("--cell-state-max-age-s", type=float, default=5.0)
    serve_gate_cmd.add_argument("--datalake-url", help="Optional: send each decision to this HYDRA-UMC-DATALAKE (http://host:port).")
    serve_gate_cmd.add_argument("--datalake-token-file")
    serve_gate_cmd.add_argument("--host", default="127.0.0.1")
    serve_gate_cmd.add_argument("--port", type=int, default=8802)
    serve_gate_cmd.set_defaults(func=_cmd_serve_gate)

    gate = subparsers.add_parser("gate", help="Evaluate one capability call against HYDRA-UMC-SDK's own real safety gate.")
    gate.add_argument("manifest_file")
    gate.add_argument("--capability", required=True)
    gate.add_argument("--job-id", required=True)
    gate.add_argument("--idempotency-key", required=True)
    gate.add_argument("--source", required=True)
    gate.add_argument("--cell-state", required=True, help="One of READY/INHIBITED/FAULT/SAFE_STOP.")
    gate.add_argument("--machine-state", required=True, help="One of OFFLINE/IDLE/RUNNING/HOLDING/FAULT/SAFE_STOP.")
    gate.add_argument(
        "--observed-machine-state",
        help="The machine state as the CALLER observed it (same values as --machine-state). When given, the gate uses it instead of the --machine-state claim.",
    )
    gate.add_argument(
        "--allow-unobserved", action="store_true",
        help="Explicit opt-in for a caller that cannot read the machine: the gate then trusts the --machine-state claim and the answer says observed=false. Without --observed-machine-state or this flag a write is refused.",
    )
    gate.add_argument("--param", action="append", help="key=value, repeatable.")
    gate.add_argument("--evidence-file", help="Optional path to a JSON evidence payload checked against evidenceSchema.")
    gate.add_argument(
        "--permission", action="append",
        help="A permission the caller attests to holding, repeatable - checked against the capability's own requiredPermission.",
    )
    gate.add_argument(
        "--cell-mode",
        help="The cell's current real supervision mode (e.g. operational/supervised/ready) - checked against the capability's own requiredCellState. Distinct from --cell-state, which is HYDRA-UMC-SDK's own generic motion-gate state.",
    )
    gate.add_argument(
        "--human-confirmed", action="store_true",
        help="Pass this if a human has explicitly confirmed this specific call - checked against the capability's own requiresHumanConfirmation.",
    )
    gate.add_argument(
        "--safety-gate", action="append",
        help="A real safety gate currently satisfied, repeatable - checked against the manifest's own requiredSafetyGates.",
    )
    gate.set_defaults(func=_cmd_gate)

    certify = subparsers.add_parser("certify", help="Record a real, human-attested hardware certification for one adapter.")
    certify.add_argument("manifest_file")
    certify.add_argument("--machine-model", required=True)
    certify.add_argument("--certified-by", required=True)
    certify.add_argument("--evidence-file", required=True, help="Path to a JSON evidence payload matching this adapter's own evidenceSchema.")
    certify.add_argument("--notes", default="")
    certify.add_argument("--out-dir", required=True, help="Directory certification records are saved into, one JSON file per record.")
    certify.add_argument(
        "--key-file",
        help="Optional: a file holding a secret (16+ characters). The record is then sealed with an HMAC and chained to the one before it, "
        "so editing or removing a record can be detected with verify-certifications. Without it records are written as before.",
    )
    certify.set_defaults(func=_cmd_certify)

    certifications = subparsers.add_parser("certifications", help="List real, previously saved certification records.")
    certifications.add_argument("--dir", required=True)
    certifications.add_argument("--adapter-id", help="Filter to one adapterId; omit to list every record.")
    certifications.set_defaults(func=_cmd_certifications)

    verify = subparsers.add_parser(
        "verify-certifications", help="Check the sealed chain of a certification folder: seals, links, gaps, the head. Exit 1 on any problem."
    )
    verify.add_argument("--dir", required=True)
    verify.add_argument("--key-file", required=True, help="The same secret the records were sealed with.")
    verify.add_argument("--strict", action="store_true", help="Also fail when a record in the folder is outside the chain (unsealed).")
    verify.set_defaults(func=_cmd_verify_certifications)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
