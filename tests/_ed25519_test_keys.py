# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/_ed25519_test_keys.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Ephemeral Ed25519 test keys and a signer (RFC 8032), only to build tokens and key sets in the tests. Every key is generated at random for the run."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time

from hydra_umc_connector_hub import jwks as J


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class TestKey:
    __test__ = False   # not a test class for pytest

    def __init__(self, seed: bytes | None = None) -> None:
        self.seed = seed if seed is not None else os.urandom(32)
        h = hashlib.sha512(self.seed).digest()
        a = bytearray(h[:32])
        a[0] &= 248
        a[31] &= 127
        a[31] |= 64
        self._a = int.from_bytes(a, "little")
        self._prefix = h[32:]
        self.public = J._compress(J._mul(self._a, J._G))
        self.kid = J.thumbprint(self.public)

    def sign(self, message: bytes) -> bytes:
        r = J._h512(self._prefix + message)
        big_r = J._compress(J._mul(r, J._G))
        k = J._h512(big_r + self.public + message)
        return big_r + int.to_bytes((r + k * self._a) % J._Q, 32, "little")

    def jwk(self, **extra) -> dict:
        return {"kty": "OKP", "crv": "Ed25519", "x": b64(self.public), "kid": self.kid, "use": "sig", "alg": "EdDSA", **extra}

    def token(self, role="operator", *, exp_in=300, kid="default", header_extra=None, username="ana", alg="EdDSA", **claims_extra) -> str:
        header = {"alg": alg, "typ": "JWT", "kid": self.kid if kid == "default" else kid}
        header.update(header_extra or {})
        header = {k: v for k, v in header.items() if v is not None}
        now = int(time.time())
        claims = {"username": username, "role": role, "id": "u1", "tokenVersion": 1, "iat": now, "nbf": now, "exp": now + exp_in}
        claims.update(claims_extra)
        claims = {k: v for k, v in claims.items() if v is not None}
        signing = f"{b64(json.dumps(header).encode())}.{b64(json.dumps(claims).encode())}"
        return f"{signing}.{b64(self.sign(signing.encode()))}"
