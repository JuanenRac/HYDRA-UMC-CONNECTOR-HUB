# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The caller of the gate service must carry a signed token of the SERVER; without a valid one the connector does not execute."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.cli import main
from hydra_umc_connector_hub.gate_audit import GateAudit
from hydra_umc_connector_hub.gate_server import GateServiceConfig, serve_gate
from hydra_umc_connector_hub.identity import IdentityError, load_identity_key, verify_token

from test_collect_and_gate_service import FIXTURES, KEY, make_token

BODY = {"adapterId": "industrial-mqtt", "capability": "publishCommandTopic", "jobId": "job-1", "source": "test-suite"}


class VerifyTokenTests(unittest.TestCase):
    def test_a_good_token_gives_the_user_and_the_role(self):
        who = verify_token(make_token("admin"), KEY)
        self.assertEqual((who.username, who.role, who.source), ("ana", "admin", "token"))

    def test_absent_expired_tampered_and_foreign_tokens_are_refused_with_a_reason(self):
        good = make_token("operator")
        head, body, sig = good.split(".")
        other = make_token("admin")
        cases = {
            "required": None,
            "malformed": "not-a-token",
            "expired": make_token(exp_in=-5),
            "no expiry": make_token(exp=None),
            "signature": make_token(key=b"another-key-of-more-than-32-characters"),
            "tampered role": f"{head}.{other.split('.')[1]}.{sig}",
            "tampered signature": f"{head}.{body}.{sig[:-3]}AAA",
            "algorithm": make_token(alg="none"),
            "other algorithm": make_token(alg="HS512"),
            "unknown role": make_token("root"),
            "no user": make_token(username=""),
            "not yet valid": make_token(nbf=4102444800),
        }
        for name, token in cases.items():
            with self.subTest(name), self.assertRaises(IdentityError):
                verify_token(token, KEY)

    def test_an_unsigned_token_with_an_empty_signature_is_refused(self):
        head, body, _ = make_token().split(".")
        with self.assertRaises(IdentityError):
            verify_token(f"{head}.{body}.", KEY)

    def test_the_key_must_be_long_and_comes_from_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            short, ok = Path(tmp) / "short", Path(tmp) / "ok"
            short.write_text("abc")
            ok.write_text(KEY.decode() + "\n")
            with self.assertRaises(ValueError):
                load_identity_key(str(short))
            self.assertEqual(load_identity_key(str(ok)), KEY)


class GateIdentityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.registry = self.dir / "registry"
        self.registry.mkdir()
        (self.registry / "industrial-mqtt.json").write_text((FIXTURES / "industrial-mqtt.json").read_text(encoding="utf-8"))
        self.audit = GateAudit(str(self.dir / "audit.jsonl"))

    def _serve(self, host="127.0.0.1", **kwargs):
        config = GateServiceConfig(str(self.registry), self.audit, **kwargs)
        server = serve_gate(config, host=host, port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return f"http://127.0.0.1:{server.server_port}"

    def _post(self, base, token=None, path="/gate/evaluate"):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(base + path, data=json.dumps(BODY).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_by_default_no_token_means_the_connector_does_not_execute(self):
        base = self._serve(identity_key=KEY)
        for token in (None, make_token(exp_in=-1), make_token(key=b"x" * 40), "garbage"):
            status, answer = self._post(base, token)
            self.assertEqual(status, 401, answer)
            self.assertEqual(answer["code"], "IDENTITY_REQUIRED")
            self.assertNotIn("allowed", answer)
        self.assertIsNone(self.audit.head())  # nothing was evaluated

    def test_a_viewer_may_not_ask_for_a_decision_but_an_operator_and_an_admin_may(self):
        base = self._serve(identity_key=KEY)
        status, answer = self._post(base, make_token("viewer"))
        self.assertEqual((status, answer["code"]), (403, "ROLE_FORBIDDEN"))
        self.assertIsNone(self.audit.head())
        for role in ("operator", "admin"):
            status, answer = self._post(base, make_token(role))
            self.assertEqual(status, 200)
            self.assertIn("allowed", answer)
        recent = self.audit.recent(5)
        self.assertEqual([r["caller"]["role"] for r in recent], ["operator", "admin"])
        self.assertEqual(recent[0]["caller"], {"username": "ana", "role": "operator", "identitySource": "token"})

    def test_a_viewer_may_read_the_audit(self):
        base = self._serve(identity_key=KEY)
        request = urllib.request.Request(base + "/gate/audit", headers={"Authorization": f"Bearer {make_token('viewer')}"})
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 200)

    def test_loopback_without_identity_only_with_the_explicit_switch(self):
        with self.assertRaises(ValueError):
            GateServiceConfig(str(self.registry), self.audit)  # off by default: no key, no switch, no service
        base = self._serve(allow_loopback_no_identity=True)
        status, answer = self._post(base)
        self.assertEqual(status, 200)
        self.assertIn("allowed", answer)
        self.assertEqual(self.audit.recent(1)[0]["caller"], {"username": None, "role": "loopback", "identitySource": "loopback"})
        # a bad token is still refused when a key is also configured
        base = self._serve(identity_key=KEY, allow_loopback_no_identity=True)
        self.assertEqual(self._post(base, make_token(exp_in=-1))[0], 401)

    def test_the_switch_is_refused_on_an_address_that_is_not_loopback(self):
        config = GateServiceConfig(str(self.registry), self.audit, allow_loopback_no_identity=True)
        with self.assertRaises(ValueError):
            serve_gate(config, host="0.0.0.0", port=0)

    def test_the_command_line_refuses_to_start_without_a_key_or_the_switch(self):
        argv = ["serve-gate", "--registry-dir", str(self.registry), "--audit-file", str(self.dir / "a.jsonl")]
        self.assertEqual(main(argv), 1)
        self.assertEqual(main(argv + ["--allow-loopback-no-identity", "--host", "0.0.0.0"]), 1)
        short = self.dir / "short.key"
        short.write_text("abc")
        self.assertEqual(main(argv + ["--identity-key-file", str(short)]), 1)


class CommonIdentityTests(unittest.TestCase):
    """The token the family shares (HS256, the claims username, role and exp, no iat, as the probe of the other services signs it) is accepted next to the
    verifier of the hub, which keeps refusing a caller without a token and still takes the EdDSA key set."""

    def common_token(self, role="viewer", key=KEY, exp_in=60):
        import base64
        import hmac
        import time
        from hashlib import sha256

        def part(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

        head = part(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = part(json.dumps({"username": "hydra-umc-server", "role": role, "exp": int(time.time()) + exp_in}).encode())
        return f"{head}.{body}.{part(hmac.new(key, f'{head}.{body}'.encode('ascii'), sha256).digest())}"

    def test_the_common_token_of_the_server_is_accepted(self):
        for role in ("viewer", "operator", "admin"):
            who = verify_token(self.common_token(role), KEY)
            self.assertEqual((who.username, who.role, who.source), ("hydra-umc-server", role, "token"))

    def test_the_common_token_is_refused_when_it_is_wrong(self):
        for name, token in {"foreign key": self.common_token(key=b"another-key-of-more-than-32-characters"), "expired": self.common_token(exp_in=-5), "unknown role": self.common_token("root")}.items():
            with self.subTest(name), self.assertRaises(IdentityError):
                verify_token(token, KEY)

    def test_the_key_file_of_the_family_variable_starts_the_service_and_no_token_is_still_refused(self):
        import os
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "connector-hub-identity.key"
            key_file.write_bytes(KEY)
            registry = Path(tmp) / "registry"
            registry.mkdir()
            argv = ["serve-gate", "--registry-dir", str(registry), "--audit-file", str(Path(tmp) / "a.jsonl"), "--host", "127.0.0.1", "--port", "0"]
            # without the variable and without a switch the service does not start; with the variable it gets as far as serving
            self.assertEqual(main(argv), 1)
            with mock.patch.dict(os.environ, {"HYDRA_UMC_CONNECTOR_HUB_IDENTITY_KEY_FILE": str(key_file)}), mock.patch("hydra_umc_connector_hub.gate_server.serve_gate", side_effect=RuntimeError("reached")) as served:
                with self.assertRaises(RuntimeError):
                    main(argv)
                config = served.call_args[0][0]
                self.assertEqual(config.identity_key, KEY)
                with self.assertRaises(IdentityError):
                    config.token_verifier.verify(None)


if __name__ == "__main__":
    unittest.main()
