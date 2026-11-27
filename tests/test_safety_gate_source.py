# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_safety_gate_source.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Where the clear emergency stop comes from, and a confirmation that must be signed with the key set."""
import unittest
from types import SimpleNamespace

from hydra_umc_connector_hub.confirmation import ConfirmationError, ConfirmationLedger, token_algorithm, verify_confirmation
from hydra_umc_connector_hub.gate_server import ESTOP_CLEAR_GATE, _safety_gates
from hydra_umc_connector_hub.identity import TokenVerifier

from test_collect_and_gate_service import KEY
from test_confirmation import CALL, confirmation_token


def gates(derive, observed, claimed):
    decision = {}
    found = _safety_gates(SimpleNamespace(derive_safety_gates=derive), claimed, observed, decision)
    return ESTOP_CLEAR_GATE in found, decision["safetyGatesSource"][ESTOP_CLEAR_GATE]


class SafetyGateSourceTests(unittest.TestCase):
    def test_a_stopped_or_faulted_cell_is_never_clear(self):
        for derive in (False, True):
            for state in ("SAFE_STOP", "FAULT"):
                self.assertEqual(gates(derive, state, [ESTOP_CLEAR_GATE]), (False, "observed"))

    def test_by_default_the_claim_stands_when_nothing_says_stopped(self):
        self.assertEqual(gates(False, "READY", [ESTOP_CLEAR_GATE]), (True, "attested"))
        self.assertEqual(gates(False, None, [ESTOP_CLEAR_GATE]), (True, "attested"))
        self.assertEqual(gates(False, "READY", []), (False, "attested"))

    def test_derived_gates_ignore_the_caller(self):
        self.assertEqual(gates(True, "READY", []), (True, "observed"))
        self.assertEqual(gates(True, None, [ESTOP_CLEAR_GATE]), (False, "observed"))


class EdDsaOnlyTests(unittest.TestCase):
    def test_an_hs256_confirmation_is_refused_when_the_key_set_is_required(self):
        token = confirmation_token(jti="hs-1")
        self.assertEqual(token_algorithm(token), "HS256")
        with self.assertRaisesRegex(ConfirmationError, "EdDSA"):
            verify_confirmation(token, TokenVerifier(hs256_key=KEY), ledger=ConfirmationLedger(), require_eddsa=True, **CALL)
        self.assertIsNone(token_algorithm("!!!.x.y"))


if __name__ == "__main__":
    unittest.main()
