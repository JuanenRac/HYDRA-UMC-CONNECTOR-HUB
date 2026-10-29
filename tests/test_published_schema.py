# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - published JSON Schema stays in step with the validator
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""`schemas/adapter-manifest.v1.schema.json` is documentation a tool can read;
`schema.py` decides. These tests fail when the two drift apart."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from hydra_umc_connector_hub import schema as reference

import _schema_subset

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = json.loads((ROOT / "schemas" / "adapter-manifest.v1.schema.json").read_text(encoding="utf-8"))


class PublishedSchemaTests(unittest.TestCase):
    def test_required_top_level_fields_match_the_validator(self):
        code_required = set(reference.REQUIRED_TOP_LEVEL_STRING_FIELDS) | {
            "targetKinds", "endpointSchema", "healthCheck", "evidenceSchema",
            "requiredSafetyGates", "timeoutMs", "capabilities",
        }
        self.assertEqual(set(PUBLISHED["required"]), code_required)

    def test_enumerations_match_the_validator(self):
        self.assertEqual(tuple(PUBLISHED["properties"]["idempotency"]["enum"]), reference.IDEMPOTENCY_VALUES)
        capability = PUBLISHED["$defs"]["capability"]
        self.assertEqual(tuple(capability["properties"]["mode"]["enum"]), reference.CAPABILITY_MODES)

    def test_patterns_accept_and_reject_the_same_examples_as_the_validator(self):
        adapter = re.compile(PUBLISHED["properties"]["adapterId"]["pattern"])
        owner = re.compile(PUBLISHED["properties"]["ownerProject"]["pattern"])
        auth = re.compile(PUBLISHED["properties"]["authenticationRef"]["pattern"])
        for good in ("cnc-grbl", "A_1"):
            self.assertTrue(adapter.match(good), good)
        for bad in ("../escaped", "sub/dir", "-lead", ""):
            self.assertFalse(adapter.match(bad), bad)
        self.assertTrue(owner.fullmatch("HYDRA-UMC-BRIDGE-CNC"))
        self.assertFalse(owner.fullmatch("me"))
        self.assertTrue(auth.match("env:TOKEN"))
        self.assertFalse(auth.match("env:"))
        self.assertFalse(auth.match("literal-secret"))

    def test_write_capability_requirements_match_the_validator(self):
        then = PUBLISHED["$defs"]["capability"]["then"]["required"]
        self.assertEqual(set(then), set(reference._WRITE_CAPABILITY_REQUIRED_FIELDS))

    def test_every_valid_fixture_carries_every_required_field_of_the_schema(self):
        for path in sorted((ROOT / "fixtures").glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(reference.validate_adapter_manifest(manifest), [], path.name)
            missing = set(PUBLISHED["required"]) - set(manifest)
            self.assertFalse(missing, f"{path.name} lacks {sorted(missing)}")

    def test_every_invalid_fixture_is_rejected_by_the_validator(self):
        for path in sorted((ROOT / "fixtures" / "invalid").glob("*.json")):
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue  # malformed.json: not even JSON
            self.assertTrue(reference.validate_adapter_manifest(manifest), path.name)

class PublishedSchemaAgainstFixturesTests(unittest.TestCase):
    """The published schema and the validator are run on the same files and must agree."""

    def test_the_published_schema_accepts_every_valid_fixture(self):
        for path in sorted((ROOT / "fixtures").glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(_schema_subset.errors(manifest, PUBLISHED), [], path.name)

    def test_the_published_schema_rejects_every_invalid_fixture_the_validator_rejects(self):
        for path in sorted((ROOT / "fixtures" / "invalid").glob("*.json")):
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            self.assertTrue(reference.validate_adapter_manifest(manifest), path.name)
            self.assertTrue(_schema_subset.errors(manifest, PUBLISHED), f"{path.name}: the schema accepts what the validator refuses")

    def test_the_subset_evaluator_itself_refuses_a_keyword_it_does_not_know(self):
        with self.assertRaises(ValueError):
            _schema_subset.errors({}, {"type": "object", "oneOf": []})

    def test_the_subset_evaluator_checks_conditional_requirements(self):
        schema = {"type": "object", "if": {"properties": {"m": {"enum": ["w"]}}, "required": ["m"]}, "then": {"required": ["x"]}}
        self.assertTrue(_schema_subset.errors({"m": "w"}, schema))
        self.assertEqual(_schema_subset.errors({"m": "r"}, schema), [])


if __name__ == "__main__":
    unittest.main()
