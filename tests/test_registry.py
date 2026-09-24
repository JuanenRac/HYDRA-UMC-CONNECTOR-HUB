# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 2 tests - real filesystem fixtures, no mocking of schema.py or
the filesystem: `fixtures/` on disk IS the real registry directory under
test, exactly as a real caller would point `--registry-dir` at it."""
import json
import tempfile
import unittest
from pathlib import Path

from hydra_umc_connector_hub.registry import (
    CatalogEntry,
    build_catalog,
    catalog_snapshot_version,
    load_full_manifest,
    verify_catalog_owners,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class BuildCatalogTests(unittest.TestCase):
    def test_the_real_fixtures_directory_yields_exactly_ten_entries_and_no_invalid_files(self):
        entries, invalid_files = build_catalog(str(FIXTURES_DIR))
        self.assertEqual(len(entries), 10)
        self.assertEqual(invalid_files, {})

    def test_entries_are_sorted_by_adapter_id(self):
        entries, _ = build_catalog(str(FIXTURES_DIR))
        ids = [entry.adapter_id for entry in entries]
        self.assertEqual(ids, sorted(ids))

    def test_the_nested_invalid_directory_is_never_scanned(self):
        entries, invalid_files = build_catalog(str(FIXTURES_DIR))
        for entry in entries:
            self.assertNotIn("invalid", entry.source_path.replace("\\", "/"))
        self.assertEqual(invalid_files, {})

    def test_a_catalog_entry_never_leaks_the_full_endpoint_or_evidence_schema(self):
        entries, _ = build_catalog(str(FIXTURES_DIR))
        for entry in entries:
            as_dict = entry.to_dict()
            self.assertNotIn("endpointSchema", as_dict)
            self.assertNotIn("evidenceSchema", as_dict)
            self.assertIn("capabilities", as_dict)

    def test_a_directory_with_one_invalid_manifest_reports_it_without_dropping_the_valid_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "good.json").write_text((FIXTURES_DIR / "industrial-mqtt.json").read_text(encoding="utf-8"), encoding="utf-8")
            (Path(tmp) / "broken.json").write_text(json.dumps({"adapterId": "broken-one"}), encoding="utf-8")
            entries, invalid_files = build_catalog(tmp)
            self.assertEqual(len(entries), 1)
            self.assertIn("broken.json", invalid_files)
            self.assertTrue(len(invalid_files["broken.json"]) > 0)

    def test_two_files_declaring_the_same_adapter_id_reject_the_second_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = json.loads((FIXTURES_DIR / "industrial-mqtt.json").read_text(encoding="utf-8"))
            (Path(tmp) / "a-first.json").write_text(json.dumps(original), encoding="utf-8")
            (Path(tmp) / "b-second.json").write_text(json.dumps(original), encoding="utf-8")
            entries, invalid_files = build_catalog(tmp)
            self.assertEqual(len(entries), 1)
            self.assertIn("b-second.json", invalid_files)
            self.assertIn("already registered", invalid_files["b-second.json"][0])

    def test_a_non_existent_directory_raises_a_real_error(self):
        with self.assertRaises(NotADirectoryError):
            build_catalog(str(FIXTURES_DIR / "does-not-exist"))


class LoadFullManifestTests(unittest.TestCase):
    def test_a_registered_adapter_returns_its_full_real_manifest(self):
        manifest = load_full_manifest(str(FIXTURES_DIR), "industrial-opcua")
        self.assertIsNotNone(manifest)
        self.assertIn("endpointSchema", manifest)
        self.assertEqual(manifest["ownerProject"], "HYDRA-UMC-OPCUA-SERVER")

    def test_an_unregistered_adapter_id_returns_none(self):
        self.assertIsNone(load_full_manifest(str(FIXTURES_DIR), "not-a-real-adapter"))


class CatalogSnapshotVersionTests(unittest.TestCase):
    def test_the_same_real_registry_yields_the_same_version_every_time(self):
        entries_a, invalid_a = build_catalog(str(FIXTURES_DIR))
        entries_b, invalid_b = build_catalog(str(FIXTURES_DIR))
        self.assertEqual(
            catalog_snapshot_version(entries_a, invalid_a),
            catalog_snapshot_version(entries_b, invalid_b),
        )

    def test_adding_a_real_adapter_changes_the_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = json.loads((FIXTURES_DIR / "industrial-mqtt.json").read_text(encoding="utf-8"))
            (Path(tmp) / "one.json").write_text(json.dumps(original), encoding="utf-8")
            entries_a, invalid_a = build_catalog(tmp)
            version_a = catalog_snapshot_version(entries_a, invalid_a)

            second = dict(original)
            second["adapterId"] = "a-second-real-adapter"
            (Path(tmp) / "two.json").write_text(json.dumps(second), encoding="utf-8")
            entries_b, invalid_b = build_catalog(tmp)
            version_b = catalog_snapshot_version(entries_b, invalid_b)

            self.assertNotEqual(version_a, version_b)

    def test_an_invalid_file_appearing_changes_the_version_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            entries_a, invalid_a = build_catalog(tmp)
            version_a = catalog_snapshot_version(entries_a, invalid_a)

            (Path(tmp) / "broken.json").write_text(json.dumps({"adapterId": "broken"}), encoding="utf-8")
            entries_b, invalid_b = build_catalog(tmp)
            version_b = catalog_snapshot_version(entries_b, invalid_b)

            self.assertNotEqual(version_a, version_b)


def _fake_entry(adapter_id: str, owner_project: str) -> CatalogEntry:
    return CatalogEntry(
        adapter_id=adapter_id, protocol="mqtt", target_kinds=["sensor"], owner_project=owner_project,
        sdk_compatibility=">=0.1.0", idempotency="none", capabilities=[], source_path="fake.json",
    )


class VerifyCatalogOwnersTests(unittest.TestCase):
    """`ownerProject` is real project-name-shaped by the
    time it reaches here (schema.py's own PROJECT_NAME_PATTERN check),
    but this is the actual "does that project exist and self-identify
    with this name" verification - a real filesystem check, never
    trusted from the manifest's own say-so alone."""

    def test_a_real_self_consistent_owner_manifest_verifies_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-MQTT-BROKER").mkdir()
            (root / "HYDRA-UMC-MQTT-BROKER" / "hydra-umc.project.json").write_text(
                json.dumps({"name": "HYDRA-UMC-MQTT-BROKER", "version": "0.1.0"}), encoding="utf-8",
            )
            entry = _fake_entry("mqtt-adapter", "HYDRA-UMC-MQTT-BROKER")

            failures = verify_catalog_owners([entry], str(root))

            self.assertEqual(failures, {})

    def test_a_missing_owner_manifest_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = _fake_entry("mqtt-adapter", "HYDRA-UMC-MQTT-BROKER")

            failures = verify_catalog_owners([entry], tmp)

            self.assertIn("mqtt-adapter", failures)
            self.assertIn("no real hydra-umc.project.json", failures["mqtt-adapter"])

    def test_an_owner_manifest_that_self_identifies_differently_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "HYDRA-UMC-MQTT-BROKER").mkdir()
            (root / "HYDRA-UMC-MQTT-BROKER" / "hydra-umc.project.json").write_text(
                json.dumps({"name": "HYDRA-UMC-SOMETHING-ELSE", "version": "0.1.0"}), encoding="utf-8",
            )
            entry = _fake_entry("mqtt-adapter", "HYDRA-UMC-MQTT-BROKER")

            failures = verify_catalog_owners([entry], str(root))

            self.assertIn("does not self-identify", failures["mqtt-adapter"])

    def test_real_fixtures_all_have_real_project_name_shaped_owners(self):
        # Real, end-to-end: the 10 real fixtures this repo ships all
        # declare a genuinely well-formed ownerProject (they simply
        # don't have real sibling checkouts under this temp root, so
        # this only exercises the PROJECT_NAME_PATTERN defense-in-depth
        # branch, not full existence - a real ecosystem_root pointed at
        # this workspace's own parent directory would verify them fully).
        with tempfile.TemporaryDirectory() as tmp:
            entries, _ = build_catalog(str(FIXTURES_DIR))
            failures = verify_catalog_owners(entries, tmp)
            for adapter_id, reason in failures.items():
                self.assertIn("no real hydra-umc.project.json", reason, f"{adapter_id}: {reason}")


if __name__ == "__main__":
    unittest.main()
