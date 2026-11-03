# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Who is asking: the identity of the caller of the gate service, taken from the signed token that HYDRA-UMC-SERVER issues at login.

The format is the one the SERVER already uses and nothing else: a JWT (RFC 7519) signed with HS256, whose key is the SERVER's `JWT_SECRET`, with the claims
`username` (text), `role` (`admin`, `operator` or `viewer`) and `exp` (seconds since the epoch, required). The hub only VERIFIES such a token; it never
issues one. The key is read from a file the operator names (never from the command line), at least 32 characters, the same minimum as the SERVER.

What the hub checks: the algorithm is exactly HS256 (`none` and any other are refused), the signature (constant time), a present and future `exp`, an `nbf`
that has passed, a non-empty `username` and a known `role`. What it cannot check is a revocation the SERVER keeps on its side (a changed password or a
deleted account): keep `JWT_EXPIRES_IN` short for the account that calls the hub, as the SERVER documents.

Fail-closed: a request without a valid token is refused with a reason and the connector does not execute. The only way to answer a caller with no identity
is the explicit switch `allowLoopbackNoIdentity` (command line `--allow-loopback-no-identity`, or the configuration file), which is OFF by default and is
accepted only when the service listens on a loopback address and the caller connects from one.
"""
from __future__ import annotations

import base64
import binascii
import hmac
import json
import time
from dataclasses import dataclass
from hashlib import sha256

MIN_KEY_LENGTH = 32
ROLES = ("admin", "operator", "viewer")
# The roles that may ask the gate for a decision about a write or an abort: a read-only account may read the audit, nothing else.
DECIDE_ROLES = frozenset({"admin", "operator"})
LOOPBACK_ROLE = "loopback"
LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1", "localhost"})
MAX_TOKEN_CHARS = 4096


class IdentityError(Exception):
    """The caller has no valid identity; `str()` is the reason that is answered and recorded."""


@dataclass(frozen=True)
class Identity:
    username: str | None
    role: str
    source: str  # "token" or "loopback"

    def as_audit(self) -> dict[str, str | None]:
        return {"username": self.username, "role": self.role, "identitySource": self.source}


def load_identity_key(path: str) -> bytes:
    """Read the verification key from a file. Raises ValueError (never prints the key)."""
    with open(path, encoding="utf-8") as handle:
        key = handle.read().strip()
    if len(key) < MIN_KEY_LENGTH:
        raise ValueError(f"the identity key must have at least {MIN_KEY_LENGTH} characters")
    return key.encode("utf-8")


def _b64(segment: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as exc:
        raise IdentityError("the token is malformed") from exc


def _json_part(segment: str) -> dict:
    try:
        value = json.loads(_b64(segment).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise IdentityError("the token is malformed") from exc
    if not isinstance(value, dict):
        raise IdentityError("the token is malformed")
    return value


def verify_token(token: str | None, key: bytes, *, now: float | None = None) -> Identity:
    """The identity in a signed token, or IdentityError saying why there is none."""
    if not token:
        raise IdentityError("a signed token of HYDRA-UMC-SERVER is required")
    if len(token) > MAX_TOKEN_CHARS:
        raise IdentityError("the token is malformed")
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise IdentityError("the token is malformed")
    header = _json_part(parts[0])
    if header.get("alg") != "HS256":
        raise IdentityError("the token algorithm is not accepted (only HS256)")
    expected = hmac.new(key, f"{parts[0]}.{parts[1]}".encode("ascii", "replace"), sha256).digest()
    if not hmac.compare_digest(expected, _b64(parts[2])):
        raise IdentityError("the token signature is not valid")
    claims = _json_part(parts[1])
    moment = time.time() if now is None else now
    exp = claims.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        raise IdentityError("the token has no expiry")
    if exp <= moment:
        raise IdentityError("the token has expired")
    nbf = claims.get("nbf")
    if nbf is not None and (isinstance(nbf, bool) or not isinstance(nbf, (int, float)) or nbf > moment):
        raise IdentityError("the token is not valid yet")
    username, role = claims.get("username"), claims.get("role")
    if not isinstance(username, str) or not username:
        raise IdentityError("the token names no user")
    if role not in ROLES:
        raise IdentityError("the token carries no known role")
    return Identity(username, role, "token")


def require_role(identity: Identity, allowed: frozenset[str]) -> None:
    if identity.role not in allowed:
        raise IdentityError(f"the role {identity.role!r} may not do this (needs one of {', '.join(sorted(allowed))})")


def is_loopback(address: str) -> bool:
    return address in LOOPBACK_ADDRESSES or address.startswith("127.") or address == "::ffff:127.0.0.1"
