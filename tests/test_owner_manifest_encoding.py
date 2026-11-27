# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_owner_manifest_encoding.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""An owner manifest saved in another encoding."""
from __future__ import annotations

from types import SimpleNamespace

from hydra_umc_connector_hub.registry import verify_catalog_owners


def test_an_owner_manifest_in_another_encoding_is_one_failure(tmp_path):
    for name, raw in (("HYDRA-UMC-LATIN", b'{"name": "se\xf1al"}'), ("HYDRA-UMC-GOOD", b'{"name": "HYDRA-UMC-GOOD"}')):
        (tmp_path / name).mkdir()
        (tmp_path / name / "hydra-umc.project.json").write_bytes(raw)
    entries = [SimpleNamespace(adapter_id="a", owner_project="HYDRA-UMC-LATIN"),
               SimpleNamespace(adapter_id="b", owner_project="HYDRA-UMC-GOOD")]
    failures = verify_catalog_owners(entries, str(tmp_path))
    assert list(failures) == ["a"]
    assert "could not be read" in failures["a"]
