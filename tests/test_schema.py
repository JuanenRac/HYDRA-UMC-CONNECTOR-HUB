# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_schema.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real tests: every one of the ten real Delivery-1 fixtures must validate
cleanly, and every real invalid fixture must fail for the SPECIFIC reason
it was constructed to demonstrate - never just "some error occurred"."""
import json
import unittest
from pathlib import Path

from hydra_umc_connector_hub.schema import (
    check_sdk_compatibility,
    load_and_validate,
    validate_adapter_manifest,
    validate_against_json_schema_subset,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

REAL_ADAPTER_FIXTURES = (
    "industrial-opcua.json",
    "industrial-mqtt.json",
    "manufacturing-mtconnect.json",
    "cnc-grbl.json",
    "laser-safety.json",
    "pnp-openpnp.json",
    "printer-moonraker.json",
    "robotics-ros2.json",
    "mobile-vda5050.json",
    "uav-mavlink.json",
)


class RealFixturesValidateCleanlyTests(unittest.TestCase):
    def test_there_are_exactly_ten_real_delivery_1_fixtures(self):
        self.assertEqual(len(REAL_ADAPTER_FIXTURES), 10)

    def test_every_real_fixture_file_exists(self):
        for name in REAL_ADAPTER_FIXTURES:
            self.assertTrue((FIXTURES_DIR / name).is_file(), f"missing fixture: {name}")

    def test_every_real_fixture_validates_with_zero_errors(self):
        for name in REAL_ADAPTER_FIXTURES:
            data, errors = load_and_validate(str(FIXTURES_DIR / name))
            self.assertIsNotNone(data, f"{name} failed to parse")
            self.assertEqual(errors, [], f"{name} had real validation errors: {errors}")

    # The real, fixed adapterId -> ownerProject mapping this project's own
    # ten fixtures were written against (see the root README's own ROADMAP/
    # Related Projects sections) - checked against this exact catalog, not
    # merely "starts with HYDRA-UMC-", so an accidentally-swapped or
    # invented owner would actually fail this test rather than pass it by
    # coincidence of prefix alone.
    _REAL_OWNER_BY_ADAPTER_ID = {
        "industrial-opcua": "HYDRA-UMC-OPCUA-SERVER",
        "industrial-mqtt": "HYDRA-UMC-MQTT-BROKER",
        "manufacturing-mtconnect": "HYDRA-UMC-MTCONNECT-ADAPTER",
        "cnc-grbl": "HYDRA-UMC-BRIDGE-CNC",
        "laser-safety": "HYDRA-UMC-BRIDGE-LASER",
        "pnp-openpnp": "HYDRA-UMC-BRIDGE-OPENPNP",
        "printer-moonraker": "HYDRA-UMC-BRIDGE-PRINTER3D",
        "robotics-ros2": "HYDRA-UMC-BRIDGE-ROS2",
        "mobile-vda5050": "HYDRA-UMC-BRIDGE-AMR",
        "uav-mavlink": "HYDRA-UMC-BRIDGE-UAV",
    }

    def test_every_real_fixture_names_its_own_exact_real_owner_project(self):
        self.assertEqual(len(self._REAL_OWNER_BY_ADAPTER_ID), 10)
        for name in REAL_ADAPTER_FIXTURES:
            data, _ = load_and_validate(str(FIXTURES_DIR / name))
            expected_owner = self._REAL_OWNER_BY_ADAPTER_ID[data["adapterId"]]
            self.assertEqual(data["ownerProject"], expected_owner, f"{name} names the wrong ownerProject")


class InvalidFixturesFailForTheRightReasonTests(unittest.TestCase):
    def test_missing_fields_fixture_reports_every_missing_field(self):
        data, errors = load_and_validate(str(FIXTURES_DIR / "invalid" / "missing-fields.json"))
        self.assertIsNotNone(data)
        joined = " ".join(errors)
        self.assertIn("authenticationRef", joined)
        self.assertIn("targetKinds", joined)  # endpointSchema/timeoutMs etc. are also missing

    def test_literal_secret_in_auth_ref_is_rejected(self):
        data, errors = load_and_validate(str(FIXTURES_DIR / "invalid" / "literal-secret-in-auth-ref.json"))
        self.assertIsNotNone(data)
        self.assertTrue(any("authenticationRef" in e for e in errors))

    def test_write_capability_missing_gates_is_rejected(self):
        data, errors = load_and_validate(str(FIXTURES_DIR / "invalid" / "write-capability-missing-gates.json"))
        self.assertIsNotNone(data)
        joined = " ".join(errors)
        self.assertIn("requiredPermission", joined)
        self.assertIn("requiresHumanConfirmation", joined)
        self.assertIn("timeoutMs", joined)

    def test_bad_idempotency_value_is_rejected(self):
        data, errors = load_and_validate(str(FIXTURES_DIR / "invalid" / "bad-idempotency-value.json"))
        self.assertIsNotNone(data)
        self.assertTrue(any("idempotency" in e for e in errors))

    def test_malformed_json_returns_none_data_and_a_parse_error(self):
        data, errors = load_and_validate(str(FIXTURES_DIR / "invalid" / "malformed.json"))
        self.assertIsNone(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("not valid JSON", errors[0])

    def test_a_missing_file_returns_a_real_read_error(self):
        data, errors = load_and_validate(str(FIXTURES_DIR / "does-not-exist.json"))
        self.assertIsNone(data)
        self.assertIn("could not read", errors[0])


class ValidateAdapterManifestUnitTests(unittest.TestCase):
    def test_non_dict_input_is_rejected(self):
        self.assertEqual(validate_adapter_manifest(["not", "a", "dict"]), ["the manifest must be a JSON object"])

    def test_a_read_capability_never_needs_the_write_only_fields(self):
        errors = validate_adapter_manifest({
            "adapterId": "x", "schemaVersion": "1.0", "protocol": "http",
            "targetKinds": ["thing"], "endpointSchema": {"a": 1},
            "authenticationRef": "env:X", "capabilities": [{"name": "read", "mode": "read", "risk": "low"}],
            "requiredSafetyGates": [], "healthCheck": {"type": "http"}, "timeoutMs": 100,
            "idempotency": "none", "evidenceSchema": {"a": 1}, "sdkCompatibility": ">=0",
            "ownerProject": "HYDRA-UMC-X",
        })
        self.assertEqual(errors, [])

    def test_an_unknown_capability_mode_is_rejected(self):
        errors = validate_adapter_manifest({
            "adapterId": "x", "schemaVersion": "1.0", "protocol": "http",
            "targetKinds": ["thing"], "endpointSchema": {"a": 1},
            "authenticationRef": "env:X", "capabilities": [{"name": "y", "mode": "delete", "risk": "low"}],
            "requiredSafetyGates": [], "healthCheck": {"type": "http"}, "timeoutMs": 100,
            "idempotency": "none", "evidenceSchema": {"a": 1}, "sdkCompatibility": ">=0",
            "ownerProject": "HYDRA-UMC-X",
        })
        self.assertTrue(any("mode" in e for e in errors))

    def _write_capability(self, **overrides) -> dict:
        capability = {
            "name": "y", "mode": "write", "risk": "high", "requiredPermission": "x.y",
            "requiredCellState": "supervised", "requiresHumanConfirmation": True, "timeoutMs": 1000,
        }
        capability.update(overrides)
        return {
            "adapterId": "x", "schemaVersion": "1.0", "protocol": "http",
            "targetKinds": ["thing"], "endpointSchema": {"a": 1},
            "authenticationRef": "env:X", "capabilities": [capability],
            "requiredSafetyGates": [], "healthCheck": {"type": "http"}, "timeoutMs": 100,
            "idempotency": "none", "evidenceSchema": {"a": 1}, "sdkCompatibility": ">=0",
            "ownerProject": "HYDRA-UMC-X",
        }

    # REV-028 regression: a real audit found `risk`/`requiredPermission`/
    # `requiredCellState` accepting a list/dict/whitespace-only string -
    # every one of these must be a real, meaningful string.
    def test_a_write_capability_with_a_list_risk_is_rejected(self):
        errors = validate_adapter_manifest(self._write_capability(risk=[]))
        self.assertTrue(any("risk" in e for e in errors), errors)

    def test_a_write_capability_with_a_dict_required_permission_is_rejected(self):
        errors = validate_adapter_manifest(self._write_capability(requiredPermission={}))
        self.assertTrue(any("requiredPermission" in e for e in errors), errors)

    def test_a_write_capability_with_a_whitespace_only_required_cell_state_is_rejected(self):
        errors = validate_adapter_manifest(self._write_capability(requiredCellState="   "))
        self.assertTrue(any("requiredCellState" in e for e in errors), errors)

    def test_a_well_formed_write_capability_still_passes(self):
        self.assertEqual(validate_adapter_manifest(self._write_capability()), [])

    # REV-030 regression: `authenticationRef` with a real prefix but no
    # identifier after it, and two capabilities sharing the same name,
    # both used to pass with errors=[].
    def test_authentication_ref_with_prefix_but_no_identifier_is_rejected(self):
        manifest = self._write_capability()
        manifest["authenticationRef"] = "env:"
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("authenticationRef" in e for e in errors), errors)

    def test_duplicate_capability_names_are_rejected(self):
        manifest = self._write_capability()
        manifest["capabilities"] = [
            {"name": "same", "mode": "read", "risk": "low"},
            {"name": "same", "mode": "read", "risk": "low"},
        ]
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("duplicates" in e for e in errors), errors)

    # V07-007 (found in an independent revalidation audit, P1): adapterId
    # becomes part of a real filename in certification.py's
    # save_certification_record() - a manifest that slips a path-traversal
    # segment past this validator used to let a certification record be
    # written OUTSIDE the operator-chosen certs directory.
    def test_an_adapter_id_with_a_path_traversal_segment_is_rejected(self):
        manifest = self._write_capability()
        manifest["adapterId"] = "../escaped"
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("adapterId" in e for e in errors), errors)

    def test_an_adapter_id_with_a_backslash_is_rejected(self):
        manifest = self._write_capability()
        manifest["adapterId"] = "..\\escaped"
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("adapterId" in e for e in errors), errors)

    def test_an_adapter_id_with_a_forward_slash_is_rejected(self):
        manifest = self._write_capability()
        manifest["adapterId"] = "sub/dir"
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("adapterId" in e for e in errors), errors)

    def test_a_plain_dash_separated_adapter_id_still_passes(self):
        # every one of this repo's own 10 real fixtures uses exactly this
        # shape - the new charset check must never reject a real adapterId.
        manifest = self._write_capability()
        manifest["adapterId"] = "industrial-opcua-2"
        self.assertEqual(validate_adapter_manifest(manifest), [])

    # V07-009 (found in an independent revalidation audit, P2): a
    # malformed endpointSchema/evidenceSchema used to sail through this
    # validator (which only checked "non-empty object") and only blow up
    # later, inside validate_against_json_schema_subset, when a real
    # evidence/endpoint payload was finally checked against it.
    def test_a_manifest_with_an_invalid_regex_pattern_in_its_evidence_schema_is_rejected(self):
        manifest = self._write_capability()
        manifest["evidenceSchema"] = {"type": "object", "properties": {"x": {"type": "string", "pattern": "["}}}
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("pattern" in e for e in errors), errors)

    def test_a_manifest_with_a_non_string_required_entry_in_its_evidence_schema_is_rejected(self):
        manifest = self._write_capability()
        manifest["evidenceSchema"] = {"type": "object", "required": [[]]}
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("required" in e for e in errors), errors)

    def test_a_manifest_with_an_unknown_schema_type_in_its_endpoint_schema_is_rejected(self):
        manifest = self._write_capability()
        manifest["endpointSchema"] = {"type": "not-a-real-type"}
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("endpointSchema" in e for e in errors), errors)

    # F07 ("gate caducado") - maxRequestAgeSeconds is optional (no
    # existing fixture needs to change), but must be a real positive
    # number when an adapter author does declare one.
    def test_a_manifest_with_no_max_request_age_is_still_valid(self):
        manifest = self._write_capability()
        self.assertNotIn("maxRequestAgeSeconds", manifest)
        self.assertEqual(validate_adapter_manifest(manifest), [])

    def test_a_manifest_with_a_real_positive_max_request_age_is_valid(self):
        manifest = self._write_capability()
        manifest["maxRequestAgeSeconds"] = 15.0
        self.assertEqual(validate_adapter_manifest(manifest), [])

    def test_a_manifest_with_a_zero_max_request_age_is_rejected(self):
        manifest = self._write_capability()
        manifest["maxRequestAgeSeconds"] = 0
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("maxRequestAgeSeconds" in e for e in errors), errors)

    def test_a_manifest_with_a_negative_max_request_age_is_rejected(self):
        manifest = self._write_capability()
        manifest["maxRequestAgeSeconds"] = -5
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("maxRequestAgeSeconds" in e for e in errors), errors)

    def test_a_manifest_with_a_non_numeric_max_request_age_is_rejected(self):
        manifest = self._write_capability()
        manifest["maxRequestAgeSeconds"] = "soon"
        errors = validate_adapter_manifest(manifest)
        self.assertTrue(any("maxRequestAgeSeconds" in e for e in errors), errors)


class ValidateAgainstJsonSchemaSubsetRobustnessTests(unittest.TestCase):
    """V07-009: `validate_against_json_schema_subset()` itself must never
    raise, no matter how malformed the schema handed to it is - its own
    docstring promises exactly that. These exercise it directly (not
    through validate_adapter_manifest's new up-front gate above) since a
    schema could reach it some other way (a future caller, a schema that
    predates this gate on disk) and it must still fail closed on its own."""

    def test_type_number_does_not_accept_a_real_boolean(self):
        errors = validate_against_json_schema_subset({"type": "number"}, True)
        self.assertTrue(errors)

    def test_type_number_still_accepts_a_real_number(self):
        self.assertEqual(validate_against_json_schema_subset({"type": "number"}, 3.5), [])
        self.assertEqual(validate_against_json_schema_subset({"type": "number"}, 3), [])

    def test_an_invalid_regex_pattern_is_reported_as_an_error_not_raised(self):
        errors = validate_against_json_schema_subset({"type": "string", "pattern": "["}, "x")
        self.assertTrue(errors)

    def test_a_non_string_required_entry_is_reported_as_an_error_not_raised(self):
        errors = validate_against_json_schema_subset({"type": "object", "required": [[]]}, {})
        self.assertTrue(errors)


# F07 ("version incompatible") - check_sdk_compatibility() itself, pure
# logic, no hydra-umc-sdk install needed (see sdk_gate.py's own real
# caller for why the installed version is passed in rather than imported
# here).
class SdkCompatibilityCheckTests(unittest.TestCase):
    def test_installed_version_meeting_the_minimum_is_compatible(self):
        self.assertIsNone(check_sdk_compatibility(">=0.1.0", "0.1.0"))

    def test_installed_version_above_the_minimum_is_compatible(self):
        self.assertIsNone(check_sdk_compatibility(">=0.1.0", "0.2.5"))

    def test_installed_version_below_the_minimum_is_incompatible(self):
        error = check_sdk_compatibility(">=0.1.0", "0.0.9")
        self.assertIsNotNone(error)
        self.assertIn("0.1.0", error)
        self.assertIn("0.0.9", error)

    def test_a_major_version_bump_downward_is_incompatible(self):
        self.assertIsNotNone(check_sdk_compatibility(">=1.0.0", "0.9.9"))

    def test_a_malformed_constraint_is_a_real_reported_error_not_a_crash(self):
        error = check_sdk_compatibility("whatever-i-want", "0.1.0")
        self.assertIsNotNone(error)
        self.assertIn("not a real, supported constraint", error)

    def test_an_unsupported_operator_is_a_real_reported_error_not_silently_accepted(self):
        # This ecosystem's own real fixtures only ever use '>=' - '==' is
        # deliberately NOT understood, and must fail closed, not be
        # silently treated as compatible.
        error = check_sdk_compatibility("==0.1.0", "0.1.0")
        self.assertIsNotNone(error)

    def test_a_malformed_installed_version_is_a_real_reported_error_not_a_crash(self):
        error = check_sdk_compatibility(">=0.1.0", "not-a-version")
        self.assertIsNotNone(error)
        self.assertIn("not a real", error)


if __name__ == "__main__":
    unittest.main()
