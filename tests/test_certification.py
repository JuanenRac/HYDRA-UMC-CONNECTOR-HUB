# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_certification.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Delivery 4 tests - real filesystem writes/reads under a real temp
directory, no mocking. These tests prove the one real, honest guarantee
this module makes: a certification is refused unless its evidence
actually matches the adapter's own declared evidenceSchema, and every
accepted record survives a real save/load round trip byte-for-byte."""
import json
import tempfile
import unittest
from pathlib import Path

from dataclasses import replace as _replace

from hydra_umc_connector_hub.certification import (
    CertificationError,
    CertificationRecord,
    certify_adapter,
    load_certification_records,
    save_certification_record,
)
from hydra_umc_connector_hub.schema import load_and_validate

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> dict:
    data, errors = load_and_validate(str(FIXTURES_DIR / name))
    assert not errors, errors
    return data


class CertifyAdapterTests(unittest.TestCase):
    def test_a_valid_manifest_and_matching_evidence_produces_a_real_record(self):
        manifest = _load("cnc-grbl.json")
        record = certify_adapter(
            manifest,
            machine_model="Genmitsu 3018-PROVer",
            certified_by="Juan Enrique",
            evidence={"status": "Idle", "machinePosition": [0.0, 0.0, 0.0]},
        )
        self.assertEqual(record.adapter_id, "cnc-grbl")
        self.assertTrue(record.certification_id)
        self.assertTrue(record.certified_at)

    def test_evidence_not_matching_evidenceschema_is_refused(self):
        manifest = _load("cnc-grbl.json")
        with self.assertRaises(CertificationError) as ctx:
            certify_adapter(
                manifest,
                machine_model="Genmitsu 3018-PROVer",
                certified_by="Juan Enrique",
                evidence={"status": 12345},  # wrong type, per the fixture's own evidenceSchema
            )
        self.assertIn("expected string", str(ctx.exception))

    def test_an_empty_certified_by_is_refused(self):
        manifest = _load("cnc-grbl.json")
        with self.assertRaises(CertificationError):
            certify_adapter(manifest, machine_model="X", certified_by="   ", evidence={"status": "Idle"})

    def test_an_invalid_manifest_is_refused_before_evidence_is_even_checked(self):
        with self.assertRaises(CertificationError) as ctx:
            certify_adapter({"adapterId": "broken"}, machine_model="X", certified_by="Y", evidence={})
        self.assertIn("targetKinds", str(ctx.exception))


class SaveAndLoadCertificationRecordsTests(unittest.TestCase):
    def test_a_saved_record_round_trips_exactly(self):
        manifest = _load("industrial-mqtt.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = certify_adapter(
                manifest, machine_model="Mosquitto on a real gateway PC", certified_by="Juan Enrique", evidence={}
            )
            path = save_certification_record(record, tmp)
            self.assertTrue(Path(path).is_file())
            loaded = load_certification_records(tmp, adapter_id=record.adapter_id)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].to_dict(), record.to_dict())

    def test_multiple_certifications_of_the_same_adapter_all_survive_side_by_side(self):
        manifest = _load("industrial-mqtt.json")
        with tempfile.TemporaryDirectory() as tmp:
            first = certify_adapter(manifest, machine_model="Gateway A", certified_by="Juan", evidence={})
            second = certify_adapter(manifest, machine_model="Gateway B", certified_by="Juan", evidence={})
            save_certification_record(first, tmp)
            save_certification_record(second, tmp)
            loaded = load_certification_records(tmp, adapter_id="industrial-mqtt")
            self.assertEqual(len(loaded), 2)
            self.assertEqual({r.certification_id for r in loaded}, {first.certification_id, second.certification_id})

    def test_filtering_by_adapter_id_excludes_other_adapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            mqtt_record = certify_adapter(_load("industrial-mqtt.json"), machine_model="A", certified_by="J", evidence={})
            opcua_record = certify_adapter(_load("industrial-opcua.json"), machine_model="B", certified_by="J", evidence={})
            save_certification_record(mqtt_record, tmp)
            save_certification_record(opcua_record, tmp)
            loaded = load_certification_records(tmp, adapter_id="industrial-mqtt")
            self.assertEqual([r.adapter_id for r in loaded], ["industrial-mqtt"])

    def test_a_directory_that_does_not_exist_yet_returns_an_empty_list(self):
        self.assertEqual(load_certification_records("/does/not/exist/at/all"), [])

    def test_a_malformed_record_file_on_disk_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "broken.json").write_text("{not valid json", encoding="utf-8")
            self.assertEqual(load_certification_records(tmp), [])

    # V07-007 (P1): a
    # CertificationRecord built directly (e.g. via from_dict() on
    # untrusted JSON) never goes through validate_adapter_manifest at
    # all - save_certification_record() must refuse a path-traversal
    # adapter_id/certification_id on its OWN, independent of whatever a
    # manifest validator may or may not have already checked.
    def test_a_path_traversal_adapter_id_is_refused_not_written_outside_the_directory(self):
        record = CertificationRecord(
            certification_id="real-id",
            adapter_id="../escaped",
            machine_model="X",
            certified_by="Y",
            certified_at="2026-01-01T00:00:00+00:00",
            evidence={},
            notes="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            certs_dir = Path(tmp) / "certs"
            with self.assertRaises(CertificationError):
                save_certification_record(record, str(certs_dir))
            # nothing must have been written anywhere outside (or even
            # inside) the intended certs directory
            self.assertFalse((Path(tmp) / "escaped__real-id.json").exists())

    def test_a_path_traversal_certification_id_is_also_refused(self):
        record = CertificationRecord(
            certification_id="../../escaped",
            adapter_id="cnc-grbl",
            machine_model="X",
            certified_by="Y",
            certified_at="2026-01-01T00:00:00+00:00",
            evidence={},
            notes="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CertificationError):
                save_certification_record(record, str(Path(tmp) / "certs"))

    def test_a_normal_certification_id_and_adapter_id_still_save_fine(self):
        manifest = _load("cnc-grbl.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = certify_adapter(manifest, machine_model="X", certified_by="Y", evidence={"status": "Idle"})
            path = save_certification_record(record, tmp)
            self.assertTrue(Path(path).is_file())
            self.assertTrue(Path(path).resolve().is_relative_to(Path(tmp).resolve()))


class AppendOnlyCertificationStoreTests(unittest.TestCase):
    """V07-008 (P2):
    docs/CERTIFICATION.md and this module's own docstring promise a
    certification record is "never overwritten" once saved - but nothing
    actually enforced that."""

    def test_saving_the_same_record_twice_with_different_content_is_refused(self):
        manifest = _load("industrial-mqtt.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = certify_adapter(manifest, machine_model="Gateway A", certified_by="Juan", evidence={})
            path = save_certification_record(record, tmp)
            original_bytes = Path(path).read_text(encoding="utf-8")
            tampered = _replace(record, notes="a completely different note, added after the fact")
            with self.assertRaises(CertificationError):
                save_certification_record(tampered, tmp)
            # the original record on disk must be untouched, byte for byte
            self.assertEqual(Path(path).read_text(encoding="utf-8"), original_bytes)

    def test_saving_the_exact_same_record_twice_is_a_harmless_idempotent_no_op(self):
        manifest = _load("industrial-mqtt.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = certify_adapter(manifest, machine_model="Gateway A", certified_by="Juan", evidence={})
            first_path = save_certification_record(record, tmp)
            second_path = save_certification_record(record, tmp)  # identical content - must not raise
            self.assertEqual(first_path, second_path)
            loaded = load_certification_records(tmp, adapter_id=record.adapter_id)
            self.assertEqual(len(loaded), 1)


if __name__ == "__main__":
    unittest.main()
