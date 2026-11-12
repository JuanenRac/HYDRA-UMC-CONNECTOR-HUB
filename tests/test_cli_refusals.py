# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_cli_refusals.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Refusal paths of the probe, collect and gate commands: one line on stderr, exit 1, nothing written, no traceback."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hydra_umc_connector_hub import cli
from hydra_umc_connector_hub.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class ProbeRefusals(unittest.TestCase):
    def test_a_missing_endpoints_file_is_one_error_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run(["probe", "--registry-dir", tmp, "--endpoints-file", str(Path(tmp) / "none.json")])
            self.assertEqual(code, 1)
            self.assertTrue(err.startswith("ERROR:"))
            self.assertNotIn("Traceback", err)
            self.assertEqual(out, "")

    def test_an_endpoints_file_that_is_not_json_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "e.json"
            bad.write_text("{broken", encoding="utf-8")
            code, out, err = run(["probe", "--registry-dir", tmp, "--endpoints-file", str(bad)])
            self.assertEqual(code, 1)
            self.assertTrue(err.startswith("ERROR:"))

    def test_an_adapter_that_is_not_in_the_registry_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            endpoints = Path(tmp) / "e.json"
            endpoints.write_text(json.dumps({"ghost": {"host": "127.0.0.1", "port": 9, "scheme": "http"}}), encoding="utf-8")
            code, out, err = run(["probe", "--registry-dir", tmp, "--endpoints-file", str(endpoints), "--adapter-id", "ghost"])
            self.assertEqual(code, 1)
            self.assertIn("'ghost'", err)
            self.assertIn("registry", err)


class CollectRefusals(unittest.TestCase):
    def test_an_ecosystem_root_that_is_not_a_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run(["collect", "--ecosystem-root", str(Path(tmp) / "absent"), "--registry-dir", str(Path(tmp) / "reg")])
            self.assertEqual(code, 1)
            self.assertTrue(err.startswith("ERROR:"))
            self.assertFalse((Path(tmp) / "reg").exists())

    def test_an_empty_ecosystem_collects_nothing_and_without_apply_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "eco"
            root.mkdir()
            registry = Path(tmp) / "reg"
            code, out, err = run(["collect", "--ecosystem-root", str(root), "--registry-dir", str(registry)])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out)["applied"])
            self.assertFalse(registry.exists())


class GateSettingsTests(unittest.TestCase):
    def test_no_file_means_no_settings(self):
        self.assertEqual(cli._gate_settings(None), {})
        self.assertEqual(cli._gate_settings(""), {})

    def test_a_json_object_is_returned_as_it_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps({"allowLoopbackNoIdentity": False}), encoding="utf-8")
            self.assertEqual(cli._gate_settings(str(path)), {"allowLoopbackNoIdentity": False})

    def test_a_missing_or_damaged_file_is_a_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                cli._gate_settings(str(Path(tmp) / "none.json"))
            path = Path(tmp) / "s.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                cli._gate_settings(str(path))

    def test_a_json_list_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text("[1, 2]", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                cli._gate_settings(str(path))
            self.assertIn("JSON object", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
