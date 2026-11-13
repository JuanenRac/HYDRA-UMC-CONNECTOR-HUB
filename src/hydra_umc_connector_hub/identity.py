# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Who is asking: the identity of the caller of the gate service, taken from the signed token that HYDRA-UMC-SERVER issues at login.

Two algorithms, chosen by the configuration and never by the token: HS256 with the shared key (`TokenVerifier`, `--identity-key-file`; while `identity.accept_hs256`
is on) and EdDSA verified with the public keys of the SERVER's key set (`jwks.py`, `identity.jwks_url`). The HS256 format is: a JWT (RFC 7519) signed with HS256, whose key is the SERVER's `JWT_SECRET`, with the claims
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
import ipaddress
import json
import math
import time
from dataclasses import dataclass
from hashlib import sha256

from .jwks import JwksClient, JwksError, ed25519_verify

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


IAT_SKEW_S = 5   # clock difference tolerated for an `iat` in the future, as the SERVER does


def _claims_identity(claims: dict, moment: float) -> Identity:
    """The checks on the claims that every accepted algorithm shares."""
    exp = claims.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, (int, float)) or not math.isfinite(exp):   # NaN compares false with everything: it would never expire
        raise IdentityError("the token has no expiry")
    if exp <= moment:
        raise IdentityError("the token has expired")
    nbf = claims.get("nbf")
    if nbf is not None and (isinstance(nbf, bool) or not isinstance(nbf, (int, float)) or not math.isfinite(nbf) or nbf > moment):
        raise IdentityError("the token is not valid yet")
    iat = claims.get("iat")
    if iat is not None and (isinstance(iat, bool) or not isinstance(iat, (int, float)) or not math.isfinite(iat) or iat > moment + IAT_SKEW_S):
        raise IdentityError("the token was issued in the future")
    username, role = claims.get("username"), claims.get("role")
    if not isinstance(username, str) or not username:
        raise IdentityError("the token names no user")
    if role not in ROLES:
        raise IdentityError("the token carries no known role")
    return Identity(username, role, "token")


def _split(token: str | None) -> tuple[list[str], dict]:
    if not token:
        raise IdentityError("a signed token of HYDRA-UMC-SERVER is required")
    if len(token) > MAX_TOKEN_CHARS:
        raise IdentityError("the token is malformed")
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise IdentityError("the token is malformed")
    return parts, _json_part(parts[0])


def verify_token_claims(token: str | None, key: bytes, *, now: float | None = None) -> "tuple[Identity, dict]":
    """Like `verify_token`, and the claims of the token as well (for the callers that read more than the identity, such as the confirmation)."""
    parts, header = _split(token)
    if header.get("alg") != "HS256":
        raise IdentityError("the token algorithm is not accepted (only HS256)")
    expected = hmac.new(key, f"{parts[0]}.{parts[1]}".encode("ascii", "replace"), sha256).digest()
    if not hmac.compare_digest(expected, _b64(parts[2])):
        raise IdentityError("the token signature is not valid")
    claims = _json_part(parts[1])
    return _claims_identity(claims, time.time() if now is None else now), claims


def verify_token(token: str | None, key: bytes, *, now: float | None = None) -> Identity:
    """The identity in an HS256 token signed with `key`, or IdentityError saying why there is none."""
    return verify_token_claims(token, key, now=now)[0]


class TokenVerifier:
    """Which tokens of the SERVER are accepted, decided by the configuration and never by the token.

    * `jwks`: a `JwksClient` -> EdDSA tokens are verified with the public key published under their `kid`.
    * `hs256_key` and `accept_hs256` -> HS256 tokens are verified with that key (the transition: `accept_hs256` is on by default, as in the SERVER).
    The header `alg` only selects among what the configuration allows; `none`, HS384, RS/ES and the rest are refused, and an HS256 token is never checked
    against a public key (no key confusion). An unreadable key set is a refusal (fail-closed)."""

    def __init__(self, *, hs256_key: bytes | None = None, jwks: "JwksClient | None" = None, accept_hs256: bool = True) -> None:
        if hs256_key is not None and len(hs256_key) < MIN_KEY_LENGTH:
            raise ValueError(f"the identity key must have at least {MIN_KEY_LENGTH} characters")
        self.jwks = jwks
        self.hs256_key = hs256_key if accept_hs256 else None
        if self.jwks is None and self.hs256_key is None:
            raise ValueError("a token verifier needs a key set address (identity.jwks_url) or, with identity.accept_hs256 on, an identity key file")

    def verify(self, token: str | None, *, now: float | None = None) -> Identity:
        return self.verify_claims(token, now=now)[0]

    def verify_claims(self, token: str | None, *, now: float | None = None) -> "tuple[Identity, dict]":
        """The identity and the claims of a token that passes the same checks as `verify`."""
        parts, header = _split(token)
        alg = header.get("alg")
        moment = time.time() if now is None else now
        if alg == "HS256" and self.hs256_key is not None:
            return verify_token_claims(token, self.hs256_key, now=moment)
        if alg == "EdDSA" and self.jwks is not None:
            kid = header.get("kid")
            if not isinstance(kid, str) or not kid or len(kid) > 128:
                raise IdentityError("the token names no key")
            try:
                public = self.jwks.public_key(kid)
            except JwksError as exc:
                raise IdentityError(str(exc)) from exc
            if not ed25519_verify(public, f"{parts[0]}.{parts[1]}".encode("ascii", "replace"), _b64(parts[2])):
                raise IdentityError("the token signature is not valid")
            claims = _json_part(parts[1])
            return _claims_identity(claims, moment), claims
        allowed = [name for name, on in (("EdDSA", self.jwks is not None), ("HS256", self.hs256_key is not None)) if on]
        raise IdentityError(f"the token algorithm is not accepted (only {' or '.join(allowed)})")


def require_role(identity: Identity, allowed: frozenset[str]) -> None:
    if identity.role not in allowed:
        raise IdentityError(f"the role {identity.role!r} may not do this (needs one of {', '.join(sorted(allowed))})")


def is_loopback(address: str) -> bool:
    if address in LOOPBACK_ADDRESSES:
        return True
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False   # a name such as "127.example.com" is not an address: only a real loopback address counts
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return parsed.is_loopback
