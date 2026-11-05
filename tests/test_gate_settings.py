# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_gate_settings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The switch for a caller with no identity can be read and changed while the gate runs: only an administrator with a signed token may, turning it on asks for a
confirmation, the change is written to the settings file and recorded in the audit chain, and the caller with no identity cannot use it."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.gate_audit import GateAudit, verify_records
from hydra_umc_connector_hub.gate_server import GateServiceConfig, serve_gate
from test_collect_and_gate_service import KEY, make_token


class GateSettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        (self.dir / "registry").mkdir()
        self.audit_path = self.dir / "audit.jsonl"
        self.audit = GateAudit(str(self.audit_path), b"k" * 20)
        self.settings = self.dir / "settings.json"
        self.settings.write_text(json.dumps({"identityKeyFile": "key.txt", "allowLoopbackNoIdentity": False}), encoding="utf-8")

    def _serve(self, *, host="127.0.0.1", **kwargs):
        config = GateServiceConfig(str(self.dir / "registry"), self.audit, **{"identity_key": KEY, "settings_file": str(self.settings), **kwargs})
        server = serve_gate(config, host=host, port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return config, f"http://127.0.0.1:{server.server_port}"

    def _call(self, base, method, path, body=None, token=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_the_switch_is_off_and_anyone_signed_in_can_read_it(self):
        _, base = self._serve()
        self.assertEqual(self._call(base, "GET", "/gate/settings")[0], 401)
        status, view = self._call(base, "GET", "/gate/settings", token=make_token("viewer"))
        self.assertEqual(status, 200)
        self.assertEqual(view, {"allowLoopbackNoIdentity": False, "loopbackSwitchAllowed": True, "verifiesTokens": True, "persisted": True})

    def test_only_an_administrator_changes_it(self):
        config, base = self._serve()
        body = {"allowLoopbackNoIdentity": True, "confirm": True}
        self.assertEqual(self._call(base, "POST", "/gate/settings", body)[0], 401)
        self.assertEqual(self._call(base, "POST", "/gate/settings", body, token=make_token("viewer"))[0], 403)
        self.assertEqual(self._call(base, "POST", "/gate/settings", body, token=make_token("operator"))[0], 403)
        self.assertFalse(config.allow_loopback_no_identity)
        self.assertIsNone(self.audit.head())  # a refused change leaves no trace in the chain

    def test_turning_it_on_asks_for_a_confirmation_and_is_audited_and_saved(self):
        config, base = self._serve()
        admin = make_token("admin", username="root")
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": True}, token=admin)
        self.assertEqual((status, answer["code"]), (400, "CONFIRMATION_REQUIRED"))
        self.assertFalse(config.allow_loopback_no_identity)
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": True, "confirm": True}, token=admin)
        self.assertEqual(status, 200)
        self.assertTrue(answer["allowLoopbackNoIdentity"] and answer["changed"])
        self.assertTrue(config.allow_loopback_no_identity)
        self.assertTrue(json.loads(self.settings.read_text(encoding="utf-8"))["allowLoopbackNoIdentity"])
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8"))["identityKeyFile"], "key.txt")  # the rest of the file is kept
        record = self.audit.recent(1)[0]
        self.assertEqual((record["kind"], record["setting"], record["from"], record["to"]), ("settings_change", "allowLoopbackNoIdentity", False, True))
        self.assertEqual(record["caller"]["username"], "root")
        lines = [json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines()]
        verify_records(lines, b"k" * 20)  # the chain still verifies with a settings record in it
        # asking for the state it already has changes nothing and records nothing
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": True, "confirm": True}, token=admin)
        self.assertEqual((status, answer["changed"]), (200, False))
        self.assertEqual(self.audit.head()["seq"], 1)

    def test_turning_it_off_needs_no_confirmation_and_the_caller_with_no_identity_cannot_use_the_route(self):
        config, base = self._serve(allow_loopback_no_identity=True)
        self.assertEqual(self._call(base, "GET", "/gate/settings")[0], 200)  # on: a caller on this machine reads without a token
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": False})
        self.assertEqual((status, answer["code"]), (403, "TOKEN_REQUIRED"))  # ... but cannot change it
        self.assertTrue(config.allow_loopback_no_identity)
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": False}, token=make_token("admin"))
        self.assertEqual((status, answer["changed"]), (200, True))
        self.assertFalse(config.allow_loopback_no_identity)
        self.assertEqual(self._call(base, "GET", "/gate/settings")[0], 401)  # off: the same caller is refused again

    def test_a_wrong_body_or_a_refused_state_is_not_applied(self):
        config, base = self._serve()
        admin = make_token("admin")
        for body in ({}, {"allowLoopbackNoIdentity": "yes"}, {"allowLoopbackNoIdentity": True, "confirm": True, "other": 1}):
            self.assertEqual(self._call(base, "POST", "/gate/settings", body, token=admin)[0], 400)
        self.assertFalse(config.allow_loopback_no_identity)
        # a settings file that cannot be written leaves the switch where it was
        self.settings.unlink()
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": True, "confirm": True}, token=admin)
        self.assertEqual((status, answer["code"]), (409, "SETTING_REFUSED"))
        self.assertFalse(config.allow_loopback_no_identity)

    def test_without_a_key_the_switch_cannot_be_turned_off(self):
        config = GateServiceConfig(str(self.dir / "registry"), self.audit, allow_loopback_no_identity=True)
        config.listens_on_loopback = True
        with self.assertRaises(ValueError):
            config.set_allow_loopback_no_identity(False)
        self.assertTrue(config.allow_loopback_no_identity)

    def test_a_service_that_is_not_on_loopback_cannot_turn_it_on(self):
        config = GateServiceConfig(str(self.dir / "registry"), self.audit, identity_key=KEY)
        self.assertFalse(config.listens_on_loopback)
        with self.assertRaises(ValueError):
            config.set_allow_loopback_no_identity(True)

    def test_memory_only_without_a_settings_file(self):
        config, base = self._serve(settings_file=None)
        status, answer = self._call(base, "POST", "/gate/settings", {"allowLoopbackNoIdentity": True, "confirm": True}, token=make_token("admin"))
        self.assertEqual((status, answer["persisted"]), (200, False))
        self.assertTrue(config.allow_loopback_no_identity)


if __name__ == "__main__":
    unittest.main()
