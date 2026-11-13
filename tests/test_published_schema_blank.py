# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - a blank string is refused by the published schema as by the validator
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The validator refuses a string that is only white space where a name is required; the published schema must say the same,
so a tool that reads only the schema does not accept what the hub rejects."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from hydra_umc_connector_hub import schema as reference

import _schema_subset

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = json.loads((ROOT / "schemas" / "adapter-manifest.v1.schema.json").read_text(encoding="utf-8"))
BASE = json.loads((ROOT / "fixtures" / "cnc-grbl.json").read_text(encoding="utf-8"))


def _blank_in(manifest: dict, where: str) -> dict:
    manifest = copy.deepcopy(manifest)
    if where == "targetKinds":
        manifest["targetKinds"] = ["   "]
    elif where == "capabilities.name":
        manifest["capabilities"][0]["name"] = "   "
    elif where.startswith("capabilities."):
        # risk, requiredPermission and requiredCellState are checked by the validator on write and abort capabilities only
        write = next(c for c in manifest["capabilities"] if c["mode"] in ("write", "abort"))
        write[where.split(".", 1)[1]] = "   "
    else:
        manifest[where] = "   "
    return manifest


class BlankStringTests(unittest.TestCase):
    def test_the_base_manifest_is_valid_for_both(self):
        self.assertEqual(reference.validate_adapter_manifest(BASE), [])
        self.assertEqual(_schema_subset.errors(BASE, PUBLISHED), [])

    def test_a_blank_name_is_refused_by_the_validator_and_by_the_schema(self):
        for where in ("schemaVersion", "protocol", "targetKinds", "capabilities.name", "capabilities.risk", "capabilities.requiredPermission", "capabilities.requiredCellState"):
            manifest = _blank_in(BASE, where)
            with self.subTest(where=where):
                self.assertTrue(reference.validate_adapter_manifest(manifest), "the validator accepts it")
                self.assertTrue(_schema_subset.errors(manifest, PUBLISHED), "the schema accepts it")

    def test_every_string_that_needs_one_character_also_needs_a_visible_one(self):
        def walk(node: object, path: str) -> None:
            if isinstance(node, dict):
                if node.get("type") == "string" and node.get("minLength") == 1:
                    self.assertIn("pattern", node, path)
                for key, value in node.items():
                    walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f"{path}[{index}]")

        walk(PUBLISHED, "$")


if __name__ == "__main__":
    unittest.main()
