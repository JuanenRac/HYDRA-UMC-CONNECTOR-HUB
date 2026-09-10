# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/sdk_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 3 [P0] - real integration with HYDRA-UMC-SDK's own safety-gate
contract (`hydra_umc_sdk.bridge_contract`), never a second, competing
implementation of that gate. This module answers one question honestly:
"is this specific capability call, on this specific adapter, allowed to
proceed right now?" - and it answers it by re-using the exact same
`evaluate_job()`/`GateDecision` every physical-motion bridge (CNC/LASER/
OPENPNP/PRINTER3D/ROS2) already goes through, not by inventing a parallel
rule set that could silently drift from it.

Honest scope, stated up front rather than hidden in a docstring nobody
reads:

- A `read` capability is never sent through the SDK gate at all.
  `evaluate_job()` is a motion/write safety gate - it was never designed
  to protect a read, and forcing one through it would not make a read
  any safer, only slower and more confusing to debug.
- HYDRA-UMC-SDK's own `JobPhase` enum (PREPARE/LOAD/PROCESS/UNLOAD/
  COMPLETE/ABORT) models a physical-motion bridge's own job lifecycle,
  which an arbitrary adapter capability (a PLC write, a print-job start)
  does not naturally have. This module maps a manifest capability's own
  `mode` onto only two of those phases: `abort` -> `JobPhase.ABORT`
  (always forwarded to the authorised safety path, exactly like a real
  bridge's own abort request), and `write` -> a single stand-in
  `JobPhase.PROCESS` (any non-abort action still needs a READY cell and
  an IDLE machine before it proceeds; finer job-phase granularity is
  bridge-specific and stays each bridge's own concern, not this shared
  boundary's). This simplification is named here explicitly so nobody
  mistakes this module for a full job-lifecycle tracker - it is not one.
- Evidence-shape checking (`evidenceSchema`) is a real, separate,
  composable step - `evaluate_capability_call()` only folds it into the
  final decision when the caller actually supplies an `evidence` payload
  to check; it never invents evidence a real machine did not produce.

V07-006 (P1): a write/abort
capability's own declared `requiredPermission`/`requiredCellState`/
`requiresHumanConfirmation`, and the manifest's own top-level
`requiredSafetyGates`, used to be pure documentation - this module
forwarded straight to HYDRA-UMC-SDK's generic READY/IDLE motion gate
and never checked any of them. `evaluate_job()` stays exactly what its
own docstring says it is (a motion/state gate), never turned into a
full authorisation engine; instead, `evaluate_capability_call()` now
also checks, for every write/abort capability, that the CALLER'S OWN
request actually attests to holding the declared permission, having the
cell in the declared supervision mode (a real, adapter-defined
vocabulary - "supervised"/"operational"/"any" - deliberately distinct
from the SDK's own `CellState` enum, which this module already forwards
separately), a human having explicitly confirmed, and every one of the
manifest's own required safety gates being currently satisfied. Every
one of these is fail-closed and independent: dropping any single one
denies the call, matching the stated acceptance criterion.
This is deliberately NOT a special case for `mode == "abort"` - a real
adapter that wants its own abort capability to skip confirmation/cell-
mode restrictions simply declares `requiresHumanConfirmation: false`/
`requiredCellState: "any"` for it (every real fixture in this repo
already does exactly that), which this uniform check honours without
the code itself ever assuming "abort is exempt".

F07 (private plan's own flow, 2 of its 5 named scenarios found NOT
implemented at all as of 2026-09-08 - not merely untested): a
write/abort call is now ALSO denied when the caller's own request has
gone stale (`requested_at` older than `maxRequestAgeSeconds`/
`DEFAULT_MAX_REQUEST_AGE_SECONDS` - "gate caducado", the cell/machine
state a request attests to may no longer hold by the time it is
evaluated) or when the adapter manifest's own declared
`sdkCompatibility` constraint does not match the REAL installed
`hydra_umc_sdk.__version__` ("version incompatible" - `sdkCompatibility`
was required to be a non-empty string since Delivery 1, but its actual
semantic meaning was never once evaluated). Both are checked fail-closed
and independent of the other policy checks above, same standard.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .schema import check_sdk_compatibility, validate_adapter_manifest, validate_against_json_schema_subset

# F07 ("gate caducado" scenario, found and closed 2026-09-08): a write/
# abort request that was constructed a long time ago must not be trusted
# as if it were made right now - the cell/machine state it was built
# against may no longer hold. No existing manifest declares its own
# `maxRequestAgeSeconds` (added as an optional field in schema.py), so
# every real fixture gets this same conservative default rather than
# silently trusting a request of any age - matching this ecosystem's own
# general "short, bounded window" convention (e.g. HYDRA-UMC-SERVER's own
# DEFAULT_RESERVATION_TTL_MS for command ownership).
DEFAULT_MAX_REQUEST_AGE_SECONDS = 30.0


class CapabilityGateError(ValueError):
    """Raised BEFORE any SDK call for a request this module can never
    honestly evaluate - a structurally invalid manifest, an unknown
    cell/machine state name. Fails closed: no decision is better than a
    decision made against a broken contract."""


class SdkUnavailableError(RuntimeError):
    """Raised the first time `evaluate_capability_call()` actually needs
    HYDRA-UMC-SDK's own `bridge_contract` module (a write/abort
    capability) and the optional `hydra-umc-sdk` package - a real git
    dependency, not on PyPI - is not installed. A `read` capability never
    reaches this check at all, matching `diagnosis.py`'s own lazy-import,
    named-error pattern in HYDRA-UMC-OPS-AGENT for an optional real
    dependency."""


@dataclass(frozen=True)
class CapabilityCallRequest:
    """One real, correlated request to invoke a named capability on one
    registered adapter - deliberately shaped close to HYDRA-UMC-SDK's own
    `BridgeJob` (job_id/idempotency_key/source), since a write/abort
    capability call becomes a real `BridgeJob` internally."""

    job_id: str
    idempotency_key: str
    source: str
    capability_name: str
    cell_state: str
    machine_state: str
    parameters: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, Any] | None = None
    # V07-006: the real authorisation context a caller must actually
    # attest to for a write/abort capability - see this module's own
    # docstring for why these are checked here, separately from
    # evaluate_job()'s own generic motion gate.
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    cell_mode: str | None = None
    human_confirmed: bool = False
    satisfied_safety_gates: frozenset[str] = field(default_factory=frozenset)
    # F07 ("gate caducado") - when this request was actually built, real
    # wall-clock seconds (`time.time()`). Defaults to "right now" so
    # every existing caller/test that never set this explicitly keeps
    # behaving exactly as before (a freshly-built request is never
    # stale); a caller that wants to exercise real expiry sets this to a
    # real past timestamp instead.
    requested_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        for attr in ("job_id", "idempotency_key", "source", "capability_name", "cell_state", "machine_state"):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise CapabilityGateError(f"{attr!r} must be a non-empty string")


@dataclass(frozen=True)
class CapabilityGateResult:
    allowed: bool
    reason: str
    evidence_errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "evidenceErrors": list(self.evidence_errors)}


def _find_capability(manifest: dict[str, Any], capability_name: str) -> dict[str, Any] | None:
    for capability in manifest.get("capabilities", []):
        if isinstance(capability, dict) and capability.get("name") == capability_name:
            return capability
    return None


def _policy_denials(manifest: dict[str, Any], capability: dict[str, Any], request: CapabilityCallRequest, now: float) -> list[str]:
    """V07-006: every real, separate reason a write/abort capability's
    own declared policy can refuse this specific call - independent of,
    and checked BEFORE, HYDRA-UMC-SDK's own generic motion gate (so a
    call missing a permission is denied without even needing the
    optional `hydra-umc-sdk` package installed). Returns every real
    reason found, never just the first - same style as
    `validate_adapter_manifest`'s own error list."""
    denials: list[str] = []

    required_permission = capability.get("requiredPermission")
    if required_permission and required_permission not in request.granted_permissions:
        denials.append(f"caller lacks required permission {required_permission!r}")

    required_cell_state = capability.get("requiredCellState")
    if required_cell_state and required_cell_state != "any" and request.cell_mode != required_cell_state:
        denials.append(
            f"cell is not in the required mode {required_cell_state!r} for this capability "
            f"(current cell mode: {request.cell_mode!r})"
        )

    if capability.get("requiresHumanConfirmation") is True and not request.human_confirmed:
        denials.append("this capability requires explicit human confirmation, which was not given")

    missing_gates = [gate for gate in manifest.get("requiredSafetyGates", []) if gate not in request.satisfied_safety_gates]
    if missing_gates:
        denials.append(f"required safety gate(s) not satisfied: {', '.join(missing_gates)}")

    # F07 ("gate caducado"): the request's own age, not the SDK's motion
    # gate, is what expires here - checked with a plain wall-clock
    # subtraction so it needs neither the optional SDK dependency nor a
    # real machine, matching every other check in this function.
    max_age = manifest.get("maxRequestAgeSeconds", DEFAULT_MAX_REQUEST_AGE_SECONDS)
    age = now - request.requested_at
    if age > max_age:
        denials.append(
            f"this request's own gate has expired: it was made {age:.1f}s ago, "
            f"exceeding the {max_age}s limit - the cell/machine state it was built against can no longer be trusted"
        )

    return denials


def evaluate_capability_call(manifest: dict[str, Any], request: CapabilityCallRequest, *, now: float | None = None) -> CapabilityGateResult:
    """The one real entry point Delivery 3 adds. Order of checks, each
    one a real, separate reason a call can fail closed:

    1. The manifest itself must still be structurally valid - never gate
       a call against a contract that has already drifted invalid.
    2. The named capability must actually exist on this adapter.
    3. `read` is always allowed (see module docstring); `write`/`abort`
       must satisfy every real policy the capability/manifest declares
       (`requiredPermission`/`requiredCellState`/`requiresHumanConfirmation`/
       `requiredSafetyGates`/request freshness - see `_policy_denials()`,
       V07-006 and F07's own "gate caducado" scenario) BEFORE going
       through HYDRA-UMC-SDK's own real `evaluate_job()` motion gate -
       every one of these, the SDK's own version compatibility (F07's
       own "version incompatible" scenario) included, must pass.
    4. If `request.evidence` was supplied, it is checked against the
       manifest's own `evidenceSchema` - a call can be gate-allowed and
       still come back with real `evidence_errors` if the evidence
       payload does not match what the adapter itself promised to
       return.

    `now`: real wall-clock seconds this call is evaluated at, for the
    request-freshness check above - defaults to `time.time()`, override
    only from a test that needs a real, reproducible "time has passed"
    scenario rather than a flaky sleep().
    """
    effective_now = now if now is not None else time.time()

    manifest_errors = validate_adapter_manifest(manifest)
    if manifest_errors:
        raise CapabilityGateError(f"refusing to gate a call against an invalid manifest: {'; '.join(manifest_errors)}")

    capability = _find_capability(manifest, request.capability_name)
    if capability is None:
        return CapabilityGateResult(False, f"unknown capability {request.capability_name!r} on this adapter", [])

    mode = capability.get("mode")
    if mode == "read":
        allowed, reason = True, "read capabilities are not subject to the motion safety gate"
    else:
        policy_denials = _policy_denials(manifest, capability, request, effective_now)
        if policy_denials:
            # V07-006: denied on the capability's own declared policy
            # BEFORE ever touching the optional SDK dependency - a call
            # missing a permission does not need `hydra-umc-sdk`
            # installed to already know the answer is "no". Still falls
            # through to the shared evidence check below like any other
            # decision.
            allowed, reason = False, "; ".join(policy_denials)
        else:
            try:
                import hydra_umc_sdk  # type: ignore[import-not-found]
                from hydra_umc_sdk.bridge_contract import (  # type: ignore[import-not-found]
                    BridgeError,
                    BridgeJob,
                    CellState,
                    JobPhase,
                    MachineState,
                    evaluate_job,
                )
            except ImportError as exc:
                raise SdkUnavailableError(
                    "the optional 'hydra-umc-sdk' package is not installed - run "
                    "`pip install -e \".[sdk]\"` to gate a write/abort capability call"
                ) from exc

            # F07 ("version incompatible"): checked here, right where the
            # optional dependency becomes available - same real installed
            # __version__ every other consumer of this package would see,
            # never a value this module invents or caches stale. Denied
            # exactly like a policy denial above (falls through to the
            # shared evidence check below, never an early return) rather
            # than ever constructing a BridgeJob against an SDK contract
            # this manifest does not actually claim to support.
            incompatibility_reason = check_sdk_compatibility(manifest["sdkCompatibility"], hydra_umc_sdk.__version__)
            if incompatibility_reason is not None:
                allowed, reason = False, incompatibility_reason
            else:
                try:
                    cell_state = CellState(request.cell_state)
                except ValueError as exc:
                    raise CapabilityGateError(f"unknown cell_state {request.cell_state!r} - expected one of {[s.value for s in CellState]}") from exc
                try:
                    machine_state = MachineState(request.machine_state)
                except ValueError as exc:
                    raise CapabilityGateError(f"unknown machine_state {request.machine_state!r} - expected one of {[s.value for s in MachineState]}") from exc

                phase = JobPhase.ABORT if mode == "abort" else JobPhase.PROCESS
                try:
                    job = BridgeJob(
                        job_id=request.job_id,
                        idempotency_key=request.idempotency_key,
                        source=request.source,
                        phase=phase,
                        machine_state=machine_state,
                        parameters=dict(request.parameters),
                    )
                except BridgeError as exc:
                    raise CapabilityGateError(f"HYDRA-UMC-SDK rejected this request before any gate ran: {exc}") from exc

                decision = evaluate_job(job, cell_state)
                allowed, reason = decision.allowed, decision.reason

    evidence_errors: list[str] = []
    if request.evidence is not None:
        evidence_errors = validate_against_json_schema_subset(manifest.get("evidenceSchema"), request.evidence)
        if evidence_errors:
            allowed = False
            reason = f"{reason}; evidence does not match this adapter's own evidenceSchema"

    return CapabilityGateResult(allowed, reason, evidence_errors)
