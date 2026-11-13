# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_confirmation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signed, single-use human confirmation of a call (confirmation.py) and its place in the gate service."""
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from hydra_umc_connector_hub.confirmation import MAX_LIFETIME_S, PURPOSE, ConfirmationError, ConfirmationLedger, verify_confirmation
from hydra_umc_connector_hub.gate_audit import GateAudit
from hydra_umc_connector_hub.gate_server import GateServiceConfig, serve_gate
from hydra_umc_connector_hub.identity import TokenVerifier

from test_collect_and_gate_service import FIXTURES, KEY, TOKEN, make_token

CALL = {"job_id": "job-7", "adapter_id": "printer-moonraker", "capability": "startPrintJob"}


def confirmation_token(role="operator", **overrides) -> str:
    now = int(time.time())
    claims = {"purpose": PURPOSE, "jti": "c-1", "iat": now, "exp": now + 60, "jobId": "job-7", "adapterId": "printer-moonraker", "capability": "startPrintJob"}
    claims.update(overrides)
    return make_token(role, exp_in=60, **claims)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.verifier = TokenVerifier(hs256_key=KEY)
        self.ledger = ConfirmationLedger()

    def check(self, token, **changes):
        return verify_confirmation(token, self.verifier, ledger=self.ledger, **dict(CALL, **changes))

    def test_a_good_confirmation_is_accepted_once(self):
        confirmation = self.check(confirmation_token())
        self.assertEqual((confirmation.username, confirmation.role, confirmation.jti), ("ana", "operator", "c-1"))
        with self.assertRaisesRegex(ConfirmationError, "already used"):
            self.check(confirmation_token())

    def test_it_is_for_one_call_only(self):
        for name, value in (("job_id", "job-8"), ("adapter_id", "other"), ("capability", "cancelPrintJob")):
            with self.assertRaisesRegex(ConfirmationError, "not for this call"):
                self.check(confirmation_token(jti=f"x-{name}"), **{name: value})

    def test_an_ordinary_login_token_is_not_a_confirmation(self):
        with self.assertRaisesRegex(ConfirmationError, "purpose"):
            self.check(TOKEN)
        with self.assertRaisesRegex(ConfirmationError, "purpose"):
            self.check(confirmation_token(purpose="login"))

    def test_the_role_the_lifetime_and_the_signature_are_checked(self):
        with self.assertRaisesRegex(ConfirmationError, "may not confirm"):
            self.check(confirmation_token("viewer"))
        now = int(time.time())
        with self.assertRaisesRegex(ConfirmationError, "longer than"):
            self.check(confirmation_token(jti="long", iat=now, exp=now + int(MAX_LIFETIME_S) + 60), )
        with self.assertRaisesRegex(ConfirmationError, "not valid"):
            self.check(confirmation_token(iat=now - 400, exp=now - 100, jti="old"))
        with self.assertRaisesRegex(ConfirmationError, "not valid"):
            self.check(confirmation_token(jti="forged").rsplit(".", 1)[0] + ".AAAA")
        with self.assertRaisesRegex(ConfirmationError, "required"):
            self.check(None)

    def test_it_needs_a_unique_id_and_an_issue_time(self):
        with self.assertRaisesRegex(ConfirmationError, "unique id"):
            self.check(confirmation_token(jti=None))
        with self.assertRaisesRegex(ConfirmationError, "unique id"):
            self.check(confirmation_token(jti="j" * 200))
        with self.assertRaisesRegex(ConfirmationError, "issued"):
            self.check(confirmation_token(jti="no-iat", iat=None))

    def test_the_ledger_is_bounded_and_a_claim_can_be_given_back(self):
        ledger = ConfirmationLedger(max_entries=2)
        now = time.time()
        self.assertTrue(ledger.claim("a", now + 60, now=now))
        self.assertTrue(ledger.claim("b", now + 60, now=now))
        with self.assertRaises(ConfirmationError):
            ledger.claim("c", now + 60, now=now)
        ledger.release("a")
        self.assertTrue(ledger.claim("c", now + 60, now=now))
        # an entry that has expired makes room and may be used again
        self.assertTrue(ledger.claim("a", now + 200, now=now + 120))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        directory = Path(self._tmp.name)
        registry = directory / "registry"
        registry.mkdir()
        (registry / "printer-moonraker.json").write_text((FIXTURES / "printer-moonraker.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.registry = str(registry)
        self.audit = GateAudit(str(directory / "audit.jsonl"), b"k" * 20)

    def serve(self, **kwargs):
        config = GateServiceConfig(self.registry, self.audit, identity_key=KEY, **kwargs)
        server = serve_gate(config, port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return config, f"http://127.0.0.1:{server.server_port}"

    def evaluate(self, base, **extra):
        body = {
            "adapterId": "printer-moonraker",
            "capability": "startPrintJob",
            "jobId": "job-7",
            "source": "test",
            "cellState": "READY",
            "machineState": "IDLE",
            "observedMachineState": "IDLE",
            "grantedPermissions": ["printer3d.job.start"],
            "cellMode": "idle",
        }
        body.update(extra)
        request = urllib.request.Request(base + "/gate/evaluate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            return json.loads(exc.read().decode())

    def test_the_boolean_of_the_caller_is_not_believed_by_default(self):
        config, base = self.serve()
        self.assertFalse(config.allow_unsigned_human_confirmation)
        answer = self.evaluate(base, humanConfirmed=True)
        self.assertFalse(answer["allowed"])
        self.assertIn("requires explicit human confirmation", answer["reason"])
        self.assertEqual(answer["confirmation"]["source"], "ignored")

    def test_a_signed_confirmation_satisfies_the_requirement_once_and_is_recorded(self):
        _, base = self.serve()
        answer = self.evaluate(base, confirmationToken=confirmation_token())
        self.assertNotIn("requires explicit human confirmation", answer["reason"], answer)
        self.assertEqual((answer["confirmation"]["source"], answer["confirmation"]["by"]), ("token", "ana"))
        # a denial for another reason gave the confirmation back: the same token works again
        if not answer["allowed"]:
            again = self.evaluate(base, confirmationToken=confirmation_token())
            self.assertEqual(again["confirmation"]["source"], "token", again)
        else:
            replay = self.evaluate(base, confirmationToken=confirmation_token())
            self.assertFalse(replay["allowed"])
            self.assertIn("already used", replay["reason"])
        record = self.audit.recent(10)[0]
        self.assertEqual(record["confirmation"]["jti"], "c-1")
        self.assertNotIn("confirmationToken", json.dumps(record))

    def test_a_confirmation_that_is_given_must_be_good_even_with_the_switch_on(self):
        _, base = self.serve(allow_unsigned_human_confirmation=True)
        answer = self.evaluate(base, humanConfirmed=True, confirmationToken=confirmation_token(jobId="another-job"))
        self.assertFalse(answer["allowed"])
        self.assertIn("not for this call", answer["reason"])
        self.assertEqual(answer["confirmation"]["source"], "rejected")

    def test_the_switch_restores_the_boolean(self):
        _, base = self.serve(allow_unsigned_human_confirmation=True)
        answer = self.evaluate(base, humanConfirmed=True)
        self.assertNotIn("requires explicit human confirmation", answer["reason"], answer)
        self.assertEqual(answer["confirmation"]["source"], "unsigned")


if __name__ == "__main__":
    unittest.main()
