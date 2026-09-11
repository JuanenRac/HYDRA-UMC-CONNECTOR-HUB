# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/schema.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The real "adapter-manifest" contract defined while auditing the code
("CONTRATO MINIMO DE ADAPTADOR"), plus a
real, hand-written structural validator for it - deliberately not the
third-party `jsonschema` package, since this project's own Delivery 1 is
small enough (14 top-level fields, one nested capability shape) that a
plain, dependency-free Python validator is both simpler AND lets every
real error message name the exact adapter/field/capability at fault, which
generic JSON-Schema validator output rarely does as clearly.

This module never touches a network or a real machine - it only ever
validates the STRUCTURE and internal consistency of a manifest already
read from disk. Whether the endpoint/protocol it describes is actually
reachable is real, separate, later work (Delivery 4 - hardware
certification), not this module's job.
"""
from __future__ import annotations

import re
from typing import Any

# The real capability modes the contract names explicitly.
CAPABILITY_MODES = ("read", "write", "abort")

# V07-007 (P1): `adapterId`
# becomes part of a real filename in certification.py's own
# save_certification_record() (`{adapterId}__{certificationId}.json`
# under an operator-chosen certs directory). Every one of this repo's own
# 10 real fixtures already uses only lowercase letters, digits and `-` -
# this charset is deliberately closed to exactly that (plus `_` and
# uppercase, for a real adapter author's own convention) so a value like
# `../escaped` or `sub/dir` can never even reach a path join. See
# certification.py's own independent, resolved-path containment check
# for the second, belt-and-suspenders layer - this validator alone is
# not trusted to be the only thing standing between an adapterId and the
# filesystem.
_SAFE_ADAPTER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

# The real idempotency vocabulary this contract uses - deliberately a
# fixed, closed set (like `redaction_level` in HYDRA-UMC-OPS-AGENT's own
# incident.py) rather than an open string, so a typo becomes a real
# validation error instead of a silently-accepted new value.
IDEMPOTENCY_VALUES = ("none", "idempotent", "at-least-once", "exactly-once")

# `authenticationRef` must be a REFERENCE to where a real credential
# lives, never the credential itself - an explicit rule of the contract
# ("Perfil de despliegue por celda, sin secretos: referencias a
# secret stores o variables de entorno, nunca tokens dentro del
# manifiesto"). A closed set of real, known reference schemes, checked as
# a literal prefix - deliberately not a "looks secret-shaped" heuristic
# (see HYDRA-UMC-OPS-AGENT's own log_redaction.py for why a heuristic is
# the wrong tool here too: false positives and false negatives are both
# real risks a fixed, explicit list avoids).
AUTHENTICATION_REF_PREFIXES = ("env:", "secret-store:", "vault:", "none:")

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# Every one of this repo's own 12 real fixtures declares `sdkCompatibility`
# as exactly ">=X.Y.Z" - the one real operator this ecosystem's own
# manifests actually use, so it is the one real operator this parser
# supports (no `==`/`<`/`~=` - adding support for an operator no real
# fixture uses would be speculative, not real work).
_SDK_COMPATIBILITY_RE = re.compile(r"^>=(\d+)\.(\d+)\.(\d+)$")


def check_sdk_compatibility(constraint: str, installed_version: str) -> str | None:
    """F07 ('version incompatible' scenario):
    `sdkCompatibility` (REQUIRED_TOP_LEVEL_STRING_FIELDS above) was only
    ever checked for being a non-empty string - its own real meaning (a
    real minimum-version constraint against the SDK actually installed)
    was never evaluated anywhere in this codebase, a real gap found
    2026-09-08. Pure logic, no `hydra_umc_sdk` import needed here - the
    one real caller that needs this (sdk_gate.py, which already owns the
    lazy-import boundary for that optional package) passes the real
    installed `hydra_umc_sdk.__version__` in.

    Returns None when compatible, or a real, human-readable reason when
    not - never raises for a malformed but well-typed string input,
    matching every other check in this module (a malformed constraint or
    an unparseable installed version is itself a real reason to refuse,
    not a crash).
    """
    match = _SDK_COMPATIBILITY_RE.match(constraint)
    if match is None:
        return (
            f"'sdkCompatibility' {constraint!r} is not a real, supported constraint - "
            "only '>=MAJOR.MINOR.PATCH' is understood"
        )
    required = tuple(int(part) for part in match.groups())

    installed_match = _VERSION_RE.match(installed_version)
    if installed_match is None:
        return f"the installed hydra-umc-sdk version {installed_version!r} is not a real 'MAJOR.MINOR.PATCH' string"
    installed = tuple(int(part) for part in installed_match.groups())

    if installed < required:
        return (
            f"this adapter requires hydra-umc-sdk {constraint} but the installed version is "
            f"{installed_version} - refusing before any capability call, not just a failed one"
        )
    return None

# Fields a "write" or "abort" capability must ALL declare, per an
# explicit rule: "Las acciones write nunca son
# seleccionables si falta una de esas condiciones."
_WRITE_CAPABILITY_REQUIRED_FIELDS = (
    "risk",
    "requiredPermission",
    "requiredCellState",
    "requiresHumanConfirmation",
    "timeoutMs",
)

# The three of the fields above that must carry a real, meaningful string -
# checked separately from mere presence (below), since presence alone
# (`"risk": []` or `"requiredPermission": " "`) does not give a future
# consumer a usable policy value, only the appearance of one.
_WRITE_CAPABILITY_STRING_FIELDS = ("risk", "requiredPermission", "requiredCellState")

REQUIRED_TOP_LEVEL_STRING_FIELDS = (
    "adapterId",
    "schemaVersion",
    "protocol",
    "authenticationRef",
    "sdkCompatibility",
    "ownerProject",
    "idempotency",
)


class AdapterManifestError(ValueError):
    """Raised with EVERY real reason a manifest failed validation, never
    just the first one found - a person fixing a manifest should not have
    to run this validator N times to discover N separate problems."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _require_non_empty_string(data: dict[str, Any], field: str, errors: list[str]) -> None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field!r} must be a non-empty string")


def _validate_capability(capability: Any, index: int) -> list[str]:
    errors: list[str] = []
    prefix = f"capabilities[{index}]"
    if not isinstance(capability, dict):
        return [f"{prefix} must be an object"]

    name = capability.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{prefix}.name must be a non-empty string")

    mode = capability.get("mode")
    if mode not in CAPABILITY_MODES:
        errors.append(f"{prefix}.mode must be one of {CAPABILITY_MODES}, got {mode!r}")

    # An explicit non-negotiable rule: a write/abort
    # capability is never selectable unless it ALSO declares every one
    # of these - checked here as a real, enforced structural rule, not
    # left as documentation someone could forget to implement later.
    if mode in ("write", "abort"):
        for required_field in _WRITE_CAPABILITY_REQUIRED_FIELDS:
            if required_field not in capability or capability.get(required_field) in (None, ""):
                errors.append(
                    f"{prefix} has mode {mode!r} but is missing required field {required_field!r} "
                    "(a write/abort capability must declare risk, requiredPermission, "
                    "requiredCellState, requiresHumanConfirmation and timeoutMs)"
                )
        # Presence alone is not enough: `"risk": []`/`{}`/`" "` all pass the
        # loop above (none of them equal `None`/`""`) while still giving a
        # future consumer no real, usable policy value - checked as its own
        # real, tested rule rather than trusted to "just be a string" by
        # convention.
        for string_field in _WRITE_CAPABILITY_STRING_FIELDS:
            if string_field not in capability:
                continue  # already reported as missing above
            value = capability[string_field]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{string_field} must be a real, non-empty string, got {value!r}")
        if "requiresHumanConfirmation" in capability and not isinstance(capability["requiresHumanConfirmation"], bool):
            errors.append(f"{prefix}.requiresHumanConfirmation must be a real boolean, not {capability['requiresHumanConfirmation']!r}")
        timeout = capability.get("timeoutMs")
        if timeout is not None and (not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0):
            errors.append(f"{prefix}.timeoutMs must be a positive integer, got {timeout!r}")

    return errors


def validate_adapter_manifest(data: Any) -> list[str]:
    """Returns a list of every real validation error found - an empty
    list means the manifest is structurally valid. Never raises for a
    malformed but well-typed input; the caller decides what to do with a
    non-empty error list (the CLI prints each and exits non-zero)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["the manifest must be a JSON object"]

    for field in REQUIRED_TOP_LEVEL_STRING_FIELDS:
        _require_non_empty_string(data, field, errors)

    adapter_id = data.get("adapterId")
    if isinstance(adapter_id, str) and adapter_id.strip() and not _SAFE_ADAPTER_ID_RE.match(adapter_id):
        errors.append(
            f"'adapterId' must contain only letters, digits, '-' and '_' (no path separators or '.') "
            f"so it can never escape the directory a certification record is stored under - got {adapter_id!r}"
        )

    idempotency = data.get("idempotency")
    if isinstance(idempotency, str) and idempotency not in IDEMPOTENCY_VALUES:
        errors.append(f"'idempotency' must be one of {IDEMPOTENCY_VALUES}, got {idempotency!r}")

    auth_ref = data.get("authenticationRef")
    if isinstance(auth_ref, str) and auth_ref.strip():
        matched_prefix = next((prefix for prefix in AUTHENTICATION_REF_PREFIXES if auth_ref.startswith(prefix)), None)
        if matched_prefix is None:
            errors.append(
                f"'authenticationRef' must start with one of {AUTHENTICATION_REF_PREFIXES} "
                f"(a reference to where a credential lives, never the credential itself) - got {auth_ref!r}"
            )
        elif not auth_ref[len(matched_prefix):].strip():
            # `env:` alone (nothing after the real prefix) cannot be
            # resolved to any real credential location - accepting it would
            # let a future catalog silently treat "no reference at all" as
            # a valid one.
            errors.append(f"'authenticationRef' {auth_ref!r} has prefix {matched_prefix!r} but no real identifier after it")

    target_kinds = data.get("targetKinds")
    if not isinstance(target_kinds, list) or not target_kinds or not all(isinstance(k, str) and k.strip() for k in target_kinds):
        errors.append("'targetKinds' must be a non-empty list of non-empty strings")

    for field in ("endpointSchema", "healthCheck", "evidenceSchema"):
        value = data.get(field)
        if not isinstance(value, dict) or not value:
            errors.append(f"{field!r} must be a non-empty object")
        elif field != "healthCheck":
            # V07-009: `healthCheck`'s own shape is protocol-specific
            # (`{"expect": ...}`, `{"topic": ...}`, ...) and is never run
            # through validate_against_json_schema_subset anywhere in
            # this codebase, so it is deliberately not shape-checked
            # here - only endpointSchema/evidenceSchema, which ARE later
            # used as a real JSON-Schema-subset by sdk_gate.py and
            # certification.py, get this check.
            errors.extend(_validate_schema_shape(value, field))

    # F07 ("gate caducado" scenario) - optional (no existing fixture needs
    # to declare it; a real, conservative ecosystem default applies when
    # absent, see sdk_gate.py's own DEFAULT_MAX_REQUEST_AGE_SECONDS), but
    # if an adapter author DOES declare one it must be a real positive
    # number, not a value that would silently accept every request
    # (0/negative) or reject every one (a non-number).
    max_request_age = data.get("maxRequestAgeSeconds")
    if max_request_age is not None:
        if isinstance(max_request_age, bool) or not isinstance(max_request_age, (int, float)) or max_request_age <= 0:
            errors.append(f"'maxRequestAgeSeconds' must be a positive number when present, got {max_request_age!r}")

    required_safety_gates = data.get("requiredSafetyGates")
    if not isinstance(required_safety_gates, list) or not all(isinstance(g, str) for g in required_safety_gates):
        errors.append("'requiredSafetyGates' must be a list of strings (an empty list is allowed)")

    timeout_ms = data.get("timeoutMs")
    if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool) or timeout_ms <= 0:
        errors.append(f"'timeoutMs' must be a positive integer, got {timeout_ms!r}")

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("'capabilities' must be a non-empty list")
    else:
        seen_names: dict[str, int] = {}
        for index, capability in enumerate(capabilities):
            errors.extend(_validate_capability(capability, index))
            if isinstance(capability, dict):
                name = capability.get("name")
                if isinstance(name, str) and name.strip():
                    if name in seen_names:
                        # Two capabilities with the same name cannot be
                        # unambiguously selected by a future catalog/gate
                        # caller (which one runs?) - rejected here rather
                        # than left to whichever one a naive lookup happens
                        # to find first.
                        errors.append(
                            f"capabilities[{index}].name {name!r} duplicates capabilities[{seen_names[name]}].name "
                            "- capability names must be unique within one manifest"
                        )
                    else:
                        seen_names[name] = index

    return errors


# The real, deliberately small subset of JSON Schema this project's own
# fixtures ever actually use for `endpointSchema`/`evidenceSchema` -
# "type", "properties", "required" and "pattern". Delivery 3 needs a real
# way to check a submitted evidence payload against the shape an
# adapter's own manifest declares for it (and Delivery 4's certification
# record needs the same for a config payload) - written here as a second
# small, dependency-free, hand-rolled validator rather than reaching for
# `jsonschema` now, for the exact same reason `validate_adapter_manifest`
# above does not: this project's real usage never needs the rest of the
# spec, and a generic library's error messages name a JSON Pointer, not
# the adapter/field at fault.
_JSON_SCHEMA_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}


def _validate_schema_shape(schema: Any, path: str) -> list[str]:
    """V07-009 (P2): checks
    that `schema` (an endpointSchema/evidenceSchema value) is ITSELF
    well-formed, recursively - before validate_adapter_manifest ever
    accepts the manifest carrying it. A malformed schema used to pass
    that validator (which only checked "non-empty object") and only
    blow up later, inside validate_against_json_schema_subset, when a
    real evidence/endpoint payload was finally checked against it: an
    invalid regex `pattern` raised `re.error`, a non-string `required`
    entry raised `TypeError` (`key not in instance` on an unhashable
    key). Never raises itself - always returns the list of real
    problems found, same contract as validate_against_json_schema_subset
    below."""
    errors: list[str] = []
    if not isinstance(schema, dict):
        return [f"{path}: schema itself must be an object, got {schema!r}"]

    schema_type = schema.get("type")
    if schema_type is not None and schema_type not in _JSON_SCHEMA_TYPE_CHECKS:
        errors.append(f"{path}.type: unknown schema type {schema_type!r}, expected one of {tuple(_JSON_SCHEMA_TYPE_CHECKS)}")

    pattern = schema.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            errors.append(f"{path}.pattern must be a string, got {pattern!r}")
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{path}.pattern {pattern!r} is not a valid regular expression: {exc}")

    required = schema.get("required")
    if required is not None and (not isinstance(required, list) or not all(isinstance(k, str) for k in required)):
        errors.append(f"{path}.required must be a list of strings, got {required!r}")

    properties = schema.get("properties")
    if properties is not None:
        if not isinstance(properties, dict):
            errors.append(f"{path}.properties must be an object, got {properties!r}")
        else:
            for key, sub_schema in properties.items():
                errors.extend(_validate_schema_shape(sub_schema, f"{path}.properties.{key}"))

    items = schema.get("items")
    if items is not None:
        errors.extend(_validate_schema_shape(items, f"{path}.items"))

    return errors


def validate_against_json_schema_subset(schema: Any, instance: Any, *, path: str = "$") -> list[str]:
    """Checks `instance` against `schema` using only the subset of JSON
    Schema this project's own fixtures ever declare. An empty/missing
    schema (falsy `schema`) matches anything - the manifest author simply
    did not constrain that shape further, which is not itself an error.
    Never raises; always returns the list of real mismatches found."""
    errors: list[str] = []
    if not schema:
        return errors
    if not isinstance(schema, dict):
        return [f"{path}: schema itself must be an object, got {schema!r}"]

    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        python_type = _JSON_SCHEMA_TYPE_CHECKS.get(expected_type)
        if python_type is None:
            errors.append(f"{path}: schema names unknown type {expected_type!r}")
        # V07-009: `bool` is a subclass of `int` in Python, so
        # `isinstance(True, int)` (and therefore the "number" tuple check
        # below, which includes `int`) is True - without this explicit
        # exclusion a real boolean silently passed as both an "integer"
        # AND a "number", which the fixed "integer" branch already
        # guarded against but "number" never did.
        elif expected_type in ("integer", "number") and isinstance(instance, bool):
            errors.append(f"{path}: expected {expected_type}, got a boolean")
        elif expected_type == "boolean" and not isinstance(instance, bool):
            errors.append(f"{path}: expected boolean, got {type(instance).__name__}")
        elif expected_type != "boolean" and not isinstance(instance, python_type):
            errors.append(f"{path}: expected {expected_type}, got {type(instance).__name__}")
            return errors  # further object/string checks below would be meaningless on a type mismatch

    if isinstance(instance, str) and isinstance(schema.get("pattern"), str):
        # V07-009: an adapter manifest's own evidenceSchema/endpointSchema
        # is real, adapter-author-supplied data, not a value this project
        # controls - a malformed regex here used to raise `re.error`
        # straight out of this "never raises" function. `_validate_schema_shape`
        # now refuses a schema this bad before it is ever accepted onto a
        # manifest, but this stays defence-in-depth for whatever reaches
        # here anyway (a schema saved to disk before that gate existed).
        try:
            matched = re.search(schema["pattern"], instance) is not None
        except re.error as exc:
            errors.append(f"{path}: schema 'pattern' {schema['pattern']!r} is not a valid regular expression: {exc}")
        else:
            if not matched:
                errors.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")

    if isinstance(instance, dict):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, sub_schema in properties.items():
                if key in instance:
                    errors.extend(validate_against_json_schema_subset(sub_schema, instance[key], path=f"{path}.{key}"))
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                # V07-009: a non-string `required` entry (e.g. `[[]]`)
                # used to raise `TypeError: unhashable type` on `key not
                # in instance` - a schema's own `required` list is
                # exactly as untrusted as `pattern` above.
                if not isinstance(key, str):
                    errors.append(f"{path}: schema 'required' entries must be strings, got {key!r}")
                elif key not in instance:
                    errors.append(f"{path}: missing required property {key!r}")

    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(instance):
            errors.extend(validate_against_json_schema_subset(schema["items"], item, path=f"{path}[{index}]"))

    return errors


def load_and_validate(path: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Reads and validates one manifest file. Returns (data, errors) -
    `data` is None only when the file itself could not be read/parsed as
    JSON (a distinct real failure from a well-formed-but-invalid
    manifest, which returns the parsed `data` alongside its own real
    errors so a caller can still report which adapterId failed)."""
    import json

    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        return None, [f"could not read {path}: {exc}"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"{path} is not valid JSON: {exc}"]
    return data, validate_adapter_manifest(data)
