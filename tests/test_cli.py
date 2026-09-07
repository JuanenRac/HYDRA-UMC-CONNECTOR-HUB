# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real end-to-end CLI tests against the real fixture files on disk - no
mocking of schema.py, since Delivery 1 is exactly the CLI + schema +
fixtures triad and this is the one thing all three need to prove
together."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hydra_umc_connector_hub.cli import main

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

try:
    import hydra_umc_sdk.bridge_contract  # noqa: F401

    SDK_INSTALLED = True
except ImportError:
    SDK_INSTALLED = False


class CliValidateTests(unittest.TestCase):
    def test_validate_a_single_real_valid_fixture_succeeds(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["validate", str(FIXTURES_DIR / "industrial-opcua.json")])
        self.assertEqual(exit_code, 0)
        self.assertIn("VALID", stdout.getvalue())
        self.assertIn("industrial-opcua", stdout.getvalue())

    def test_validate_all_ten_real_fixtures_at_once_succeeds(self):
        real_fixtures = sorted(str(p) for p in FIXTURES_DIR.glob("*.json"))
        self.assertEqual(len(real_fixtures), 10)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["validate", *real_fixtures])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().count("VALID"), 10)

    def test_validate_an_invalid_fixture_fails_with_a_nonzero_exit(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main(["validate", str(FIXTURES_DIR / "invalid" / "missing-fields.json")])
        self.assertEqual(exit_code, 1)
        self.assertIn("INVALID", stderr.getvalue())

    def test_validate_a_malformed_file_fails_with_a_real_parse_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main(["validate", str(FIXTURES_DIR / "invalid" / "malformed.json")])
        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR", stderr.getvalue())

    # REV-029 regression: a real audit found a well-formed JSON document
    # that is not an object (a bare `[]`) crashing this command with a raw
    # AttributeError (`data.get(...)` on a list) instead of reporting the
    # real "must be a JSON object" error like any other invalid manifest.
    def test_validate_a_valid_json_array_instead_of_object_reports_invalid_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "not-an-object.json"
            path.write_text("[]", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["validate", str(path)])
            self.assertEqual(exit_code, 1)
            self.assertIn("INVALID", stderr.getvalue())
            self.assertIn("must be a JSON object", stderr.getvalue())

    def test_mixing_a_valid_and_an_invalid_file_still_reports_both_and_fails(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main([
                "validate",
                str(FIXTURES_DIR / "industrial-opcua.json"),
                str(FIXTURES_DIR / "invalid" / "bad-idempotency-value.json"),
            ])
        self.assertEqual(exit_code, 1)
        self.assertIn("VALID", stdout.getvalue())
        self.assertIn("INVALID", stderr.getvalue())

    def test_version_flag_prints_the_real_package_version(self):
        from hydra_umc_connector_hub import __version__
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(stdout):
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(__version__, stdout.getvalue())


class CliCatalogTests(unittest.TestCase):
    def test_catalog_prints_all_ten_real_adapters_as_json(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["catalog", "--registry-dir", str(FIXTURES_DIR)])
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(len(payload["adapters"]), 10)
        self.assertEqual(payload["invalidFiles"], {})


class CliGateTests(unittest.TestCase):
    def test_gate_on_a_read_capability_is_allowed_without_the_sdk(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([
                "gate", str(FIXTURES_DIR / "cnc-grbl.json"),
                "--capability", "grblStatus", "--job-id", "j1", "--idempotency-key", "i1",
                "--source", "test", "--cell-state", "READY", "--machine-state", "IDLE",
            ])
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["allowed"])

    def test_gate_on_an_unknown_capability_fails_with_nonzero_exit(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([
                "gate", str(FIXTURES_DIR / "cnc-grbl.json"),
                "--capability", "doesNotExist", "--job-id", "j1", "--idempotency-key", "i1",
                "--source", "test", "--cell-state", "READY", "--machine-state", "IDLE",
            ])
        self.assertEqual(exit_code, 1)

    @unittest.skipUnless(SDK_INSTALLED, "hydra-umc-sdk (optional [sdk] extra) is not installed")
    def test_gate_on_a_write_capability_uses_the_real_sdk(self):
        # V07-006: exercising the SDK's own motion gate requires the
        # caller to ALSO attest to sendControlByte's own declared policy
        # (permission/cell-mode/confirmation/gates) - otherwise the call
        # is denied on policy grounds before the SDK is ever consulted.
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([
                "gate", str(FIXTURES_DIR / "cnc-grbl.json"),
                "--capability", "sendControlByte", "--job-id", "j1", "--idempotency-key", "i1",
                "--source", "test", "--cell-state", "INHIBITED", "--machine-state", "IDLE",
                "--permission", "cnc.control.send", "--cell-mode", "supervised", "--human-confirmed",
                "--safety-gate", "cell.estop.clear", "--safety-gate", "cell.enclosure.closed",
            ])
        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["allowed"])
        self.assertIn("not READY", payload["reason"])

    def test_gate_on_a_write_capability_with_no_policy_context_is_denied_on_policy_grounds(self):
        # V07-006's own reproduction: the exact command line the audit
        # itself ran (no --permission/--cell-mode/--human-confirmed/
        # --safety-gate at all) used to print allowed=true.
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main([
                "gate", str(FIXTURES_DIR / "cnc-grbl.json"),
                "--capability", "sendControlByte", "--job-id", "j1", "--idempotency-key", "i1",
                "--source", "test", "--cell-state", "READY", "--machine-state", "IDLE",
            ])
        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["allowed"])
        self.assertIn("cnc.control.send", payload["reason"])


class CliCertifyTests(unittest.TestCase):
    def test_certify_then_list_round_trips_through_the_real_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "evidence.json"
            evidence_path.write_text(json.dumps({"status": "Idle", "machinePosition": [0, 0, 0]}), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main([
                    "certify", str(FIXTURES_DIR / "cnc-grbl.json"),
                    "--machine-model", "Genmitsu 3018-PROVer", "--certified-by", "Juan Enrique",
                    "--evidence-file", str(evidence_path), "--out-dir", tmp,
                ])
            self.assertEqual(exit_code, 0)
            self.assertIn("CERTIFIED", stdout.getvalue())

            stdout2 = io.StringIO()
            with contextlib.redirect_stdout(stdout2):
                exit_code2 = main(["certifications", "--dir", tmp, "--adapter-id", "cnc-grbl"])
            self.assertEqual(exit_code2, 0)
            records = json.loads(stdout2.getvalue())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["machineModel"], "Genmitsu 3018-PROVer")


if __name__ == "__main__":
    unittest.main()
