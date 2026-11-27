# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_cut_answers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A cell state answer cut in the middle. urlopen is replaced, so nothing leaves the machine."""
from __future__ import annotations

import http.client
import io
import unittest
import urllib.request
from unittest.mock import patch

from hydra_umc_connector_hub.gate_server import CellStateError, http_cell_state_provider


class CutAnswer(io.BytesIO):
    """An answer that stops in the middle of its body."""

    status = 200

    def read(self, *args):
        raise http.client.IncompleteRead(b"{", 100)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class CutCellStateTests(unittest.TestCase):
    def test_a_cut_answer_is_an_unreadable_cell_state(self) -> None:
        read = http_cell_state_provider("http://127.0.0.1:1/state")
        with patch.object(urllib.request, "urlopen", lambda *a, **k: CutAnswer()):
            with self.assertRaises(CellStateError):
                read()
