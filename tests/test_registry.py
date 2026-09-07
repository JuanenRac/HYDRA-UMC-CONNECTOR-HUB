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

from hydra_umc_connector_hub.registry import build_catalog, load_full_manifest

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


if __name__ == "__main__":
    unittest.main()
