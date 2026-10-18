# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_robustness.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Hostile or odd input: a nested document, a record that is not an object,
a request dated in the future, a four-component SDK version, a literal secret
where an environment variable name belongs, an ETag list, a query string."""
import contextlib
import io
import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.catalog_server import serve_catalog
from hydra_umc_connector_hub.certification import load_certification_records
from hydra_umc_connector_hub.cli import main
from hydra_umc_connector_hub.registry import build_catalog
from hydra_umc_connector_hub.schema import (
    check_sdk_compatibility,
    load_and_validate,
    validate_adapter_manifest,
    validate_against_json_schema_subset,
)
from hydra_umc_connector_hub.sdk_gate import CapabilityCallRequest, evaluate_capability_call

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

try:
    import hydra_umc_sdk.bridge_contract  # noqa: F401

    SDK_INSTALLED = True
except ImportError:
    SDK_INSTALLED = False


def _fixture(name: str) -> dict:
    data, errors = load_and_validate(str(FIXTURES_DIR / name))
    assert not errors, errors
    return data


class NestedDocumentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.registry = Path(self._tmp.name)
        shutil.copy(FIXTURES_DIR / "cnc-grbl.json", self.registry / "good.json")
        # well under the size cap, far deeper than the interpreter allows
        (self.registry / "deep.json").write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")

    def test_a_deeply_nested_file_is_listed_as_invalid_not_a_crash(self):
        data, errors = load_and_validate(str(self.registry / "deep.json"))
        self.assertIsNone(data)
        self.assertIn("nested too deeply", errors[0])

    def test_one_such_file_does_not_take_the_catalog_down(self):
        entries, invalid = build_catalog(str(self.registry))
        self.assertEqual([entry.adapter_id for entry in entries], ["cnc-grbl"])
        self.assertIn("deep.json", invalid)

    def test_the_server_keeps_answering(self):
        server = serve_catalog(str(self.registry), port=0)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.handle_request)
        thread.start()
        try:
            body = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/health", timeout=5).read())
        finally:
            thread.join(timeout=5)
        self.assertEqual(body["adapterCount"], 1)
        self.assertEqual(body["invalidFileCount"], 1)


class CertificationFilesTests(unittest.TestCase):
    def test_a_file_that_is_not_a_record_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "list.json").write_text("[1, 2]", encoding="utf-8")
            (Path(tmp) / "number.json").write_text("7", encoding="utf-8")
            (Path(tmp) / "nested.json").write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
            self.assertEqual(load_certification_records(tmp), [])


class VersionTests(unittest.TestCase):
    def test_four_component_versions_are_understood(self):
        self.assertIsNone(check_sdk_compatibility(">=0.3.2", "0.8.0.0"))
        self.assertIsNone(check_sdk_compatibility(">=0.8.0", "0.8.0.0"))
        self.assertIsNone(check_sdk_compatibility(">=0.8.0.1", "0.8.0.1"))
        self.assertIsNone(check_sdk_compatibility(">=0.8.0.1", "0.8.1.0"))
        self.assertIn("requires", check_sdk_compatibility(">=0.8.0.1", "0.8.0.0"))
        self.assertIn("requires", check_sdk_compatibility(">=0.8.1", "0.8.0.9"))

    def test_three_component_versions_still_work(self):
        self.assertIsNone(check_sdk_compatibility(">=0.1.0", "0.3.2"))
        self.assertIn("requires", check_sdk_compatibility(">=0.4.0", "0.3.2"))

    def test_a_malformed_version_is_a_reason_not_a_crash(self):
        self.assertIn("not a real", check_sdk_compatibility(">=0.1.0", "0.3"))
        self.assertIn("not a real", check_sdk_compatibility(">=0.1.0", "0.3.2.1.5"))


class AuthenticationRefTests(unittest.TestCase):
    def _errors(self, ref: str) -> list[str]:
        manifest = dict(_fixture("cnc-grbl.json"))
        manifest["authenticationRef"] = ref
        return [error for error in validate_adapter_manifest(manifest) if "authenticationRef" in error]

    def test_an_environment_variable_name_is_accepted(self):
        self.assertEqual(self._errors("env:OPENPNP_RPC_TOKEN"), [])

    def test_a_literal_secret_after_env_is_refused(self):
        self.assertTrue(self._errors("env:ghp_abcdef0123456789"))
        self.assertTrue(self._errors("env:my token"))

    def test_a_store_path_is_accepted_and_a_value_with_spaces_is_not(self):
        self.assertEqual(self._errors("secret-store:mqtt/client-credentials"), [])
        self.assertTrue(self._errors("vault:sk live secret=abc"))


class IntegerTests(unittest.TestCase):
    def test_one_point_zero_is_an_integer(self):
        self.assertEqual(validate_against_json_schema_subset({"type": "integer"}, 1.0), [])
        self.assertTrue(validate_against_json_schema_subset({"type": "integer"}, 1.5))
        self.assertTrue(validate_against_json_schema_subset({"type": "integer"}, True))


class CatalogEntryTests(unittest.TestCase):
    def test_the_catalog_publishes_a_file_name_not_a_path(self):
        entries, _ = build_catalog(str(FIXTURES_DIR))
        for entry in entries:
            source = entry.to_dict()["sourcePath"]
            self.assertNotIn("/", source)
            self.assertNotIn("\\", source)
            self.assertTrue(source.endswith(".json"))


class CatalogRouteTests(unittest.TestCase):
    def setUp(self):
        self.server = serve_catalog(str(FIXTURES_DIR), port=0)
        self.addCleanup(self.server.server_close)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def _fetch(self, path: str, headers: dict | None = None):
        thread = threading.Thread(target=self.server.handle_request)
        thread.start()
        try:
            request = urllib.request.Request(self.base + path, headers=headers or {})
            try:
                response = urllib.request.urlopen(request, timeout=5)
                return response.status, dict(response.headers), response.read()
            except urllib.error.HTTPError as error:
                return error.code, dict(error.headers), error.read()
        finally:
            thread.join(timeout=5)

    def test_a_query_string_and_a_trailing_slash_do_not_change_the_route(self):
        self.assertEqual(self._fetch("/catalog?verbose=1")[0], 200)
        self.assertEqual(self._fetch("/catalog/")[0], 200)
        self.assertEqual(self._fetch("/catalog/cnc-grbl/")[0], 200)
        self.assertEqual(self._fetch("/health?x=y")[0], 200)

    def test_an_etag_list_and_a_weak_etag_give_a_304(self):
        status, headers, _ = self._fetch("/catalog")
        etag = headers["ETag"]
        self.assertEqual(self._fetch("/catalog", {"If-None-Match": f'"other", {etag}'})[0], 304)
        self.assertEqual(self._fetch("/catalog", {"If-None-Match": f"W/{etag}"})[0], 304)
        self.assertEqual(self._fetch("/catalog", {"If-None-Match": '"other"'})[0], 200)

    def test_the_server_does_not_announce_a_version_it_does_not_have(self):
        _, headers, _ = self._fetch("/health")
        self.assertNotIn("/0.1", headers.get("Server", ""))


class OwnerVerificationTests(unittest.TestCase):
    def test_only_confirmed_owners_are_listed_when_an_ecosystem_root_is_given(self):
        with tempfile.TemporaryDirectory() as root:
            # only one of the owners exists under the root
            owner = Path(root) / "HYDRA-UMC-BRIDGE-CNC"
            owner.mkdir()
            (owner / "hydra-umc.project.json").write_text(json.dumps({"name": "HYDRA-UMC-BRIDGE-CNC"}), encoding="utf-8")
            server = serve_catalog(str(FIXTURES_DIR), port=0, ecosystem_root=root)
            self.addCleanup(server.server_close)
            thread = threading.Thread(target=server.handle_request)
            thread.start()
            try:
                body = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/catalog", timeout=5).read())
            finally:
                thread.join(timeout=5)
            self.assertEqual([entry["adapterId"] for entry in body["adapters"]], ["cnc-grbl"])
            self.assertIn("industrial-opcua", body["unverifiedOwners"])


class CliErrorTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = main(argv)
        return code, stderr.getvalue()

    def test_a_missing_evidence_file_is_an_error_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, err = self._run([
                "certify", str(FIXTURES_DIR / "cnc-grbl.json"), "--machine-model", "A", "--certified-by", "J",
                "--evidence-file", str(Path(tmp) / "missing.json"), "--out-dir", tmp,
            ])
        self.assertEqual(code, 1)
        self.assertIn("could not read", err)

    def test_an_evidence_file_that_is_not_json_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            code, err = self._run([
                "gate", str(FIXTURES_DIR / "cnc-grbl.json"), "--capability", "grblStatus", "--job-id", "j", "--idempotency-key", "k",
                "--source", "s", "--cell-state", "READY", "--machine-state", "IDLE", "--evidence-file", str(bad),
            ])
        self.assertEqual(code, 1)
        self.assertIn("could not read", err)


class FutureRequestTests(unittest.TestCase):
    def _write_request(self, **overrides) -> CapabilityCallRequest:
        defaults = dict(
            job_id="job-1", idempotency_key="idem-1", source="test", capability_name="sendControlByte",
            cell_state="READY", machine_state="IDLE",
            granted_permissions=frozenset({"cnc.control.send"}), cell_mode="supervised", human_confirmed=True,
            satisfied_safety_gates=frozenset({"cell.estop.clear", "cell.enclosure.closed"}),
        )
        defaults.update(overrides)
        return CapabilityCallRequest(**defaults)

    def test_a_request_dated_in_the_future_is_denied_without_the_sdk(self):
        manifest = _fixture("cnc-grbl.json")
        now = 1_000_000.0
        result = evaluate_capability_call(manifest, self._write_request(requested_at=now + 1e9), now=now)
        self.assertFalse(result.allowed)
        self.assertIn("in the future", result.reason)

    @unittest.skipUnless(SDK_INSTALLED, "needs the optional hydra-umc-sdk")
    def test_a_little_clock_skew_is_not_a_denial(self):
        manifest = _fixture("cnc-grbl.json")
        now = 1_000_000.0
        result = evaluate_capability_call(manifest, self._write_request(requested_at=now + 2.0), now=now)
        self.assertNotIn("in the future", result.reason)

    @unittest.skipUnless(SDK_INSTALLED, "needs the optional hydra-umc-sdk")
    def test_an_observed_machine_state_overrides_the_claim(self):
        manifest = _fixture("cnc-grbl.json")
        claimed_idle = self._write_request()
        self.assertTrue(evaluate_capability_call(manifest, claimed_idle).allowed)
        machine_is_running = self._write_request(observed_machine_state="RUNNING")
        result = evaluate_capability_call(manifest, machine_is_running)
        self.assertFalse(result.allowed)

    @unittest.skipUnless(SDK_INSTALLED, "needs the optional hydra-umc-sdk")
    def test_an_unknown_observed_state_is_refused(self):
        from hydra_umc_connector_hub.sdk_gate import CapabilityGateError

        with self.assertRaises(CapabilityGateError):
            evaluate_capability_call(_fixture("cnc-grbl.json"), self._write_request(observed_machine_state="WHATEVER"))


if __name__ == "__main__":
    unittest.main()
