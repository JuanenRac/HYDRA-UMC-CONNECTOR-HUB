# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_ledger.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The sealed, hash-chained certification folder: what it records, and every way of changing it that verify_chain
must see. Real files in a real temporary folder."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from hydra_umc_connector_hub import ledger
from hydra_umc_connector_hub.certification import (
    CertificationError,
    CertificationRecord,
    load_certification_records,
    save_certification_record,
)
from hydra_umc_connector_hub.cli import main

KEY = b"a-secret-of-the-operator"


def record(number: int, adapter: str = "cnc-grbl") -> CertificationRecord:
    return CertificationRecord(
        certification_id=f"cert{number:04d}",
        adapter_id=adapter,
        machine_model="3018",
        certified_by="ana",
        certified_at=f"2026-01-{number:02d}T00:00:00+00:00",
        evidence={"homed": True, "n": number},
        notes="",
    )


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def seal(self, count: int) -> list[Path]:
        return [Path(save_certification_record(record(n), str(self.dir), key=KEY)) for n in range(1, count + 1)]

    def verify(self, **kwargs):
        return ledger.verify_chain(str(self.dir), KEY, **kwargs)

    def rewrite(self, path: Path, change) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_a_fresh_chain_verifies_and_records_still_load_as_before(self):
        paths = self.seal(4)
        report = self.verify()
        self.assertTrue(report.ok, report.problems)
        self.assertEqual((report.sealed, report.unsealed), (4, []))
        chain = json.loads(paths[2].read_text(encoding="utf-8"))["chain"]
        self.assertEqual(chain["sequence"], 3)
        self.assertEqual(chain["previousHash"], ledger.file_hash(json.loads(paths[1].read_text(encoding="utf-8"))))
        loaded = load_certification_records(str(self.dir))
        self.assertEqual([r.certification_id for r in loaded], [f"cert{n:04d}" for n in range(1, 5)])

    def test_an_empty_or_missing_folder(self):
        self.assertTrue(self.verify().ok)
        self.assertFalse(ledger.verify_chain(str(self.dir / "nope"), KEY).ok)

    def test_editing_a_record_breaks_its_seal(self):
        paths = self.seal(3)
        self.rewrite(paths[1], lambda d: d["evidence"].update(homed=False))
        problems = self.verify().problems
        self.assertTrue(any("cert0002" in p and "seal" in p for p in problems), problems)
        self.assertTrue(any("cert0003" in p and "does not follow" in p for p in problems), problems)

    def test_removing_a_record_from_the_middle_is_a_gap_and_a_broken_link(self):
        paths = self.seal(4)
        paths[1].unlink()
        problems = self.verify().problems
        self.assertTrue(any("jumps from 1 to 3" in p for p in problems), problems)
        self.assertTrue(any("does not follow" in p for p in problems), problems)

    def test_removing_the_newest_records_is_seen_through_the_head(self):
        paths = self.seal(3)
        paths[2].unlink()
        problems = self.verify().problems
        self.assertTrue(any(ledger.HEAD_FILE in p and "removed" in p for p in problems), problems)

    def test_removing_the_first_record_is_seen(self):
        paths = self.seal(3)
        paths[0].unlink()
        self.assertTrue(any("starts at sequence 2" in p for p in self.verify().problems))

    def test_a_record_made_without_the_key_cannot_be_slipped_into_the_chain(self):
        self.seal(2)
        forged = ledger._sealed_document(record(3).to_dict(), 3, "0" * 64, b"some other key entirely")
        (self.dir / "cnc-grbl__forged.json").write_text(json.dumps(forged), encoding="utf-8")
        self.assertFalse(self.verify().ok)

    def test_a_rewritten_head_without_the_key_is_refused(self):
        self.seal(2)
        head = self.dir / ledger.HEAD_FILE
        head.write_text(json.dumps({"sequence": 1, "hash": "0" * 64, "seal": "0" * 64}), encoding="utf-8")
        self.assertTrue(any("seal does not match" in p for p in self.verify().problems))

    def test_a_missing_head_is_a_problem_when_there_are_records(self):
        self.seal(2)
        (self.dir / ledger.HEAD_FILE).unlink()
        self.assertTrue(any("missing" in p for p in self.verify().problems))

    def test_a_wrong_key_verifies_nothing(self):
        self.seal(2)
        report = ledger.verify_chain(str(self.dir), b"another-secret-xxxxx")
        self.assertFalse(report.ok)
        self.assertGreaterEqual(len([p for p in report.problems if "seal does not match" in p]), 2)

    def test_a_record_outside_the_chain_is_listed_and_strict_fails_on_it(self):
        self.seal(2)
        (self.dir / "cnc-grbl__hand.json").write_text(json.dumps(record(9).to_dict()), encoding="utf-8")
        report = self.verify()
        self.assertTrue(report.ok)
        self.assertEqual(report.unsealed, ["cnc-grbl__hand.json"])
        self.assertFalse(self.verify(strict=True).ok)

    def test_two_records_with_one_sequence_are_a_fork(self):
        paths = self.seal(2)
        twin = ledger._sealed_document(record(7).to_dict(), 2, json.loads(paths[0].read_text(encoding="utf-8")) and ledger.file_hash(json.loads(paths[0].read_text(encoding="utf-8"))), KEY)
        (self.dir / "cnc-grbl__twin.json").write_text(json.dumps(twin), encoding="utf-8")
        self.assertTrue(any("used twice" in p for p in self.verify().problems))

    def test_saving_the_same_record_again_is_a_no_op_and_another_under_the_same_id_is_refused(self):
        first = save_certification_record(record(1), str(self.dir), key=KEY)
        again = save_certification_record(record(1), str(self.dir), key=KEY)
        self.assertEqual(first, again)
        self.assertEqual(self.verify().sealed, 1)
        different = CertificationRecord(**{**record(1).__dict__, "notes": "changed"})
        with self.assertRaises(CertificationError):
            save_certification_record(different, str(self.dir), key=KEY)

    def test_without_a_key_nothing_changes(self):
        path = Path(save_certification_record(record(1), str(self.dir)))
        self.assertNotIn("chain", json.loads(path.read_text(encoding="utf-8")))
        self.assertFalse((self.dir / ledger.HEAD_FILE).exists())

    def test_a_stale_lock_of_a_dead_process_does_not_block_the_chain(self):
        import os
        import time

        lock = self.dir / ledger.LOCK_FILE
        lock.write_text("", encoding="utf-8")
        old = time.time() - ledger._LOCK_STALE_SECONDS - 5
        os.utime(lock, (old, old))
        self.seal(1)
        self.assertTrue(self.verify().ok)
        self.assertFalse(lock.exists())

    def test_the_key_must_be_long_enough_and_readable(self):
        short = self.dir / "short.key"
        short.write_text("tiny", encoding="utf-8")
        with self.assertRaises(ledger.LedgerError):
            ledger.load_key(str(short))
        with self.assertRaises(ledger.LedgerError):
            ledger.load_key(str(self.dir / "missing.key"))


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.key_file = self.dir / "chain.key"
        self.key_file.write_text("a-secret-of-the-operator\n", encoding="utf-8")
        self.fixtures = Path(__file__).resolve().parent.parent / "fixtures"

    def run_cli(self, *argv: str):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_certify_with_a_key_then_verify_then_tamper(self):
        evidence = self.dir / "evidence.json"
        manifest = self.fixtures / "cnc-grbl.json"
        # the evidence has to match the adapter's own schema: take what the existing CLI tests use
        schema = json.loads(manifest.read_text(encoding="utf-8")).get("evidenceSchema", {})
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        sample = {}
        for name in required:
            kind = properties.get(name, {}).get("type")
            sample[name] = {"boolean": True, "number": 1, "integer": 1, "string": "ok", "array": [], "object": {}}.get(kind, "ok")
        evidence.write_text(json.dumps(sample), encoding="utf-8")
        out_dir = self.dir / "records"
        for _ in range(2):
            code, out, err = self.run_cli(
                "certify", str(manifest), "--machine-model", "3018", "--certified-by", "ana",
                "--evidence-file", str(evidence), "--out-dir", str(out_dir), "--key-file", str(self.key_file),
            )
            self.assertEqual(code, 0, err + out)
            self.assertIn("sealed in the chain", out)
        code, out, _ = self.run_cli("verify-certifications", "--dir", str(out_dir), "--key-file", str(self.key_file))
        self.assertEqual(code, 0, out)
        self.assertIn("CHAIN=PASS 2 sealed", out)
        victim = sorted(out_dir.glob("cnc-grbl__*.json"))[0]
        data = json.loads(victim.read_text(encoding="utf-8"))
        data["certifiedBy"] = "someone else"
        victim.write_text(json.dumps(data), encoding="utf-8")
        code, out, _ = self.run_cli("verify-certifications", "--dir", str(out_dir), "--key-file", str(self.key_file))
        self.assertEqual(code, 1)
        self.assertIn("CHAIN=FAIL", out)

    def test_a_missing_or_short_key_file_is_a_clean_error(self):
        code, _, err = self.run_cli("verify-certifications", "--dir", str(self.dir), "--key-file", str(self.dir / "nope"))
        self.assertEqual(code, 1)
        self.assertIn("ERROR", err)


if __name__ == "__main__":
    unittest.main()
