# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_uav_fixture_authentication.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The MAVLink fixture says where its signing key lives, as a reference to an environment variable and never as a value."""
import json
import unittest
from pathlib import Path

from hydra_umc_connector_hub.schema import AUTHENTICATION_REF_PREFIXES, validate_adapter_manifest

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "uav-mavlink.json"


class UavFixtureAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_the_fixture_still_validates(self):
        self.assertEqual(validate_adapter_manifest(self.manifest), [])

    def test_the_reference_names_the_signing_key_file_variable_of_the_bridge(self):
        self.assertEqual(self.manifest["authenticationRef"], "env:HYDRA_UMC_BRIDGE_UAV_SIGNING_KEY_FILE")

    def test_the_reference_is_not_the_no_authentication_marker(self):
        self.assertFalse(self.manifest["authenticationRef"].startswith("none:"))
        self.assertTrue(self.manifest["authenticationRef"].startswith(AUTHENTICATION_REF_PREFIXES))

    def test_a_literal_key_in_its_place_is_refused(self):
        self.manifest["authenticationRef"] = "env:00112233445566778899aabbccddeeff"
        self.assertNotEqual(validate_adapter_manifest(self.manifest), [])


if __name__ == "__main__":
    unittest.main()
