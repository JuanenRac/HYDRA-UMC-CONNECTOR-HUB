# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_sdk_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 3 tests - against the REAL `hydra_umc_sdk.bridge_contract`
module (the optional `[sdk]` extra), never a fake/mocked stand-in for
HYDRA-UMC-SDK's own gate logic. If `hydra_umc_sdk` is not installed in
this environment, the write/abort tests are skipped rather than faked -
the whole point of Delivery 3 is proving this module calls the REAL
`evaluate_job()`, so a mock would test nothing real."""
import unittest

from hydra_umc_connector_hub.schema import load_and_validate
from hydra_umc_connector_hub.sdk_gate import (
    CapabilityCallRequest,
    CapabilityGateError,
    evaluate_capability_call,
)
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

try:
    import hydra_umc_sdk.bridge_contract  # noqa: F401

    SDK_INSTALLED = True
except ImportError:
    SDK_INSTALLED = False


def _load(name: str) -> dict:
    data, errors = load_and_validate(str(FIXTURES_DIR / name))
    assert not errors, errors
    return data


def _request(**overrides) -> CapabilityCallRequest:
    defaults = dict(
        job_id="job-1",
        idempotency_key="idem-1",
        source="test",
        capability_name="grblStatus",
        cell_state="READY",
        machine_state="IDLE",
    )
    defaults.update(overrides)
    return CapabilityCallRequest(**defaults)


def _authorized_request(**overrides) -> CapabilityCallRequest:
    """A request carrying every real bit of authorisation context
    `cnc-grbl.json`'s own `sendControlByte` capability actually declares
    (`requiredPermission=cnc.control.send`, `requiredCellState=supervised`,
    `requiresHumanConfirmation=true`, and the manifest's own
    `requiredSafetyGates` - `cell.estop.clear`/`cell.enclosure.closed`) -
    V07-006's fix means a write call is denied unless every one of these
    is actually satisfied, not just the generic READY/IDLE motion gate.
    Tests exercising ONE axis (the SDK's own motion gate, say) start from
    this fully-authorised baseline and vary only that one field, so a
    failure there is unambiguously about that one axis."""
    defaults = dict(
        job_id="job-1",
        idempotency_key="idem-1",
        source="test",
        capability_name="sendControlByte",
        cell_state="READY",
        machine_state="IDLE",
        granted_permissions=frozenset({"cnc.control.send"}),
        cell_mode="supervised",
        human_confirmed=True,
        satisfied_safety_gates=frozenset({"cell.estop.clear", "cell.enclosure.closed"}),
    )
    defaults.update(overrides)
    return CapabilityCallRequest(**defaults)


class ReadCapabilityNeverNeedsTheSdkTests(unittest.TestCase):
    def test_a_read_capability_is_always_allowed_without_the_sdk_installed(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _request(capability_name="grblStatus"))
        self.assertTrue(result.allowed)
        self.assertIn("not subject to the motion safety gate", result.reason)

    def test_an_unknown_capability_name_is_denied_without_touching_the_sdk(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _request(capability_name="doesNotExist"))
        self.assertFalse(result.allowed)
        self.assertIn("unknown capability", result.reason)

    def test_gating_against_a_structurally_invalid_manifest_fails_closed(self):
        with self.assertRaises(CapabilityGateError):
            evaluate_capability_call({"adapterId": "broken"}, _request())


@unittest.skipUnless(SDK_INSTALLED, "hydra-umc-sdk (optional [sdk] extra) is not installed")
class WriteAndAbortCapabilitiesUseTheRealSdkGateTests(unittest.TestCase):
    def test_a_write_capability_is_allowed_when_fully_authorised_and_cell_is_ready_and_machine_is_idle(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request())
        self.assertTrue(result.allowed)

    def test_a_write_capability_is_denied_when_the_cell_is_not_ready(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(cell_state="INHIBITED"))
        self.assertFalse(result.allowed)
        self.assertIn("not READY", result.reason)

    def test_a_write_capability_is_denied_when_the_machine_is_not_idle(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(machine_state="RUNNING"))
        self.assertFalse(result.allowed)
        self.assertIn("not IDLE", result.reason)

    def test_an_abort_style_capability_is_always_allowed_through_the_sdk_motion_gate_even_when_the_cell_is_not_ready(self):
        manifest = _load("printer-moonraker.json")
        abort_capability = next(c for c in manifest["capabilities"] if c["mode"] == "abort")
        result = evaluate_capability_call(
            manifest,
            _request(
                capability_name=abort_capability["name"],
                cell_state="FAULT",
                machine_state="FAULT",
                # printer-moonraker.json's own cancelPrintJob declares
                # requiredCellState="any" and requiresHumanConfirmation=false
                # - only its real requiredPermission still has to be held.
                granted_permissions=frozenset({abort_capability["requiredPermission"]}),
            ),
        )
        self.assertTrue(result.allowed)

    def test_an_unknown_cell_state_name_fails_closed_before_any_sdk_call(self):
        manifest = _load("cnc-grbl.json")
        with self.assertRaises(CapabilityGateError):
            evaluate_capability_call(manifest, _authorized_request(cell_state="NOT_A_REAL_STATE"))


@unittest.skipUnless(SDK_INSTALLED, "hydra-umc-sdk (optional [sdk] extra) is not installed")
class CapabilityGateEnforcesDeclaredPolicyTests(unittest.TestCase):
    """V07-006 (P1): a write/
    abort capability's own declared requiredPermission/requiredCellState/
    requiresHumanConfirmation, and the manifest's own top-level
    requiredSafetyGates, used to be pure documentation -
    evaluate_capability_call() forwarded straight to HYDRA-UMC-SDK's
    generic READY/IDLE motion gate and ignored all four. Each test below
    starts from a fully-authorised baseline (_authorized_request) and
    removes exactly ONE requirement, proving that ONE requirement alone
    is enough to deny the call - fixing "any one dropped -> denied" is
    the stated acceptance criterion."""

    def test_missing_the_required_permission_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(granted_permissions=frozenset()))
        self.assertFalse(result.allowed)
        self.assertIn("cnc.control.send", result.reason)

    def test_a_different_granted_permission_still_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(
            manifest, _authorized_request(granted_permissions=frozenset({"some.other.permission"}))
        )
        self.assertFalse(result.allowed)

    def test_wrong_cell_mode_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(cell_mode="autonomous"))
        self.assertFalse(result.allowed)
        self.assertIn("supervised", result.reason)

    def test_no_cell_mode_at_all_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(cell_mode=None))
        self.assertFalse(result.allowed)

    def test_missing_human_confirmation_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(human_confirmed=False))
        self.assertFalse(result.allowed)
        self.assertIn("confirmation", result.reason)

    def test_a_missing_safety_gate_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(
            manifest, _authorized_request(satisfied_safety_gates=frozenset({"cell.estop.clear"}))
        )
        self.assertFalse(result.allowed)
        self.assertIn("cell.enclosure.closed", result.reason)

    def test_no_safety_gates_satisfied_at_all_denies_the_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request(satisfied_safety_gates=frozenset()))
        self.assertFalse(result.allowed)

    def test_every_requirement_missing_at_once_still_denies_closed_not_raises(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(
            manifest,
            _authorized_request(
                granted_permissions=frozenset(),
                cell_mode=None,
                human_confirmed=False,
                satisfied_safety_gates=frozenset(),
            ),
        )
        self.assertFalse(result.allowed)

    def test_a_capability_declaring_required_cell_state_any_is_not_gated_on_cell_mode(self):
        manifest = _load("printer-moonraker.json")
        abort_capability = next(c for c in manifest["capabilities"] if c["mode"] == "abort")
        self.assertEqual(abort_capability["requiredCellState"], "any")
        result = evaluate_capability_call(
            manifest,
            _request(
                capability_name=abort_capability["name"],
                cell_state="FAULT",
                machine_state="FAULT",
                granted_permissions=frozenset({abort_capability["requiredPermission"]}),
                cell_mode=None,  # deliberately absent - "any" must still pass
            ),
        )
        self.assertTrue(result.allowed)

    def test_a_read_capability_is_never_subject_to_any_of_these_policy_checks(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _request(capability_name="grblStatus"))
        self.assertTrue(result.allowed)

    def test_evidence_matching_the_schema_does_not_block_an_allowed_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(
            manifest,
            _request(
                capability_name="grblStatus",
                evidence={"status": "Idle", "machinePosition": [0.0, 0.0, 0.0]},
            ),
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.evidence_errors, [])

    def test_evidence_not_matching_the_schema_blocks_an_otherwise_allowed_call(self):
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(
            manifest,
            _request(capability_name="grblStatus", evidence={"status": 123}),
        )
        self.assertFalse(result.allowed)
        self.assertTrue(result.evidence_errors)


# F07 ("ID malicioso, version incompatible, certificado duplicado,
# confirmacion ausente y gate caducado") - the last 2 of those
# scenarios were found not implemented at
# all (not just untested). "ID malicioso"/"confirmacion ausente" were
# already real above (unknown capability / requiresHumanConfirmation);
# "certificado duplicado" is Delivery 4's own certification.py, out of
# this module's scope.
@unittest.skipUnless(SDK_INSTALLED, "hydra-umc-sdk (optional [sdk] extra) is not installed")
class RequestFreshnessGateTests(unittest.TestCase):
    """'gate caducado' - a write/abort request built too long ago must be
    refused, since the cell/machine state it attests to may no longer
    hold. Uses `now=` injection throughout for a real, deterministic
    "time has passed" instead of a flaky sleep()."""

    def test_a_request_older_than_the_default_limit_is_denied(self):
        manifest = _load("cnc-grbl.json")
        now = 1_000_000.0
        stale = _authorized_request(requested_at=now - 31.0)  # DEFAULT_MAX_REQUEST_AGE_SECONDS is 30.0
        result = evaluate_capability_call(manifest, stale, now=now)
        self.assertFalse(result.allowed)
        self.assertIn("gate has expired", result.reason)

    def test_a_request_within_the_default_limit_is_not_denied_for_freshness(self):
        manifest = _load("cnc-grbl.json")
        now = 1_000_000.0
        fresh = _authorized_request(requested_at=now - 5.0)
        result = evaluate_capability_call(manifest, fresh, now=now)
        self.assertTrue(result.allowed)

    def test_a_manifest_declaring_its_own_max_request_age_is_honoured(self):
        manifest = dict(_load("cnc-grbl.json"))
        manifest["maxRequestAgeSeconds"] = 5.0
        now = 1_000_000.0
        # Would pass the 30s ecosystem default, but not this manifest's
        # own tighter, real 5s limit.
        result = evaluate_capability_call(manifest, _authorized_request(requested_at=now - 10.0), now=now)
        self.assertFalse(result.allowed)
        self.assertIn("gate has expired", result.reason)

    def test_a_freshly_constructed_request_defaults_to_now_and_is_never_stale(self):
        # No now= override at all - requested_at's own default_factory
        # (time.time) and evaluate_capability_call's own default (also
        # time.time()) must never disagree by more than this test's own
        # execution time.
        manifest = _load("cnc-grbl.json")
        result = evaluate_capability_call(manifest, _authorized_request())
        self.assertTrue(result.allowed)

    def test_a_read_capability_is_never_subject_to_the_freshness_check(self):
        manifest = _load("cnc-grbl.json")
        now = 1_000_000.0
        ancient = _request(capability_name="grblStatus", requested_at=now - 10_000.0)
        result = evaluate_capability_call(manifest, ancient, now=now)
        self.assertTrue(result.allowed)


@unittest.skipUnless(SDK_INSTALLED, "hydra-umc-sdk (optional [sdk] extra) is not installed")
class SdkVersionCompatibilityGateTests(unittest.TestCase):
    """'version incompatible' - an adapter manifest's own declared
    `sdkCompatibility` (a real `>=X.Y.Z` constraint, required by every
    real fixture already, see schema.py's own REQUIRED_TOP_LEVEL_STRING_
    FIELDS) was only ever checked for being a non-empty string - its real
    meaning against the actually-installed hydra-umc-sdk was never
    evaluated anywhere until this pass."""

    def test_a_manifest_requiring_an_unreleased_future_sdk_version_is_denied(self):
        manifest = dict(_load("cnc-grbl.json"))
        manifest["sdkCompatibility"] = ">=99.0.0"  # always incompatible, regardless of what's installed
        result = evaluate_capability_call(manifest, _authorized_request())
        self.assertFalse(result.allowed)
        self.assertIn("requires hydra-umc-sdk >=99.0.0", result.reason)

    def test_a_manifest_compatible_with_the_installed_sdk_is_not_denied_for_version(self):
        manifest = dict(_load("cnc-grbl.json"))
        manifest["sdkCompatibility"] = ">=0.0.1"  # every real installed version satisfies this
        result = evaluate_capability_call(manifest, _authorized_request())
        self.assertTrue(result.allowed)

    def test_a_read_capability_is_never_subject_to_the_version_check(self):
        # Same real design as the freshness check above: a read never
        # touches the optional SDK dependency at all, so it cannot be
        # gated on that dependency's own installed version either.
        manifest = dict(_load("cnc-grbl.json"))
        manifest["sdkCompatibility"] = ">=99.0.0"
        result = evaluate_capability_call(manifest, _request(capability_name="grblStatus"))
        self.assertTrue(result.allowed)

    def test_version_incompatibility_is_checked_before_the_motion_gate_not_after(self):
        # Cell not-ready would ALSO deny this call (see
        # WriteAndAbortCapabilitiesUseTheRealSdkGateTests above) - the
        # reason returned must be the version one, proving this check
        # runs first, not that it merely happens to agree with a
        # different real denial.
        manifest = dict(_load("cnc-grbl.json"))
        manifest["sdkCompatibility"] = ">=99.0.0"
        result = evaluate_capability_call(manifest, _authorized_request(cell_state="INHIBITED"))
        self.assertFalse(result.allowed)
        self.assertIn("requires hydra-umc-sdk", result.reason)


if __name__ == "__main__":
    unittest.main()
