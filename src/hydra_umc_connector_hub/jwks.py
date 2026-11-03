# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/jwks.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The public keys of HYDRA-UMC-SERVER, read from its key set (`GET /.well-known/jwks.json`, RFC 7517) to verify the EdDSA (Ed25519) tokens it signs.

The hub holds no secret for this path: it reads PUBLIC keys and can never forge a token. What is fixed here:

* The place is named in the settings file (`identity.jwks_url`), never by a token or a request. Only `https`, or `http` to a loopback address, and no
  credentials in the address. Redirects are not followed; TLS is verified; the answer is limited in size and in number of keys.
* A key is accepted only if it is `OKP`/`Ed25519`, its `x` is 32 bytes, it is not marked for another use or algorithm, and its `kid` is the RFC 7638
  thumbprint of the key itself (a key whose name does not match is ignored, so a `kid` cannot be spoofed).
* Cache with a time to live (`jwks_ttl_s`). A token with a `kid` that is not in the cache makes the client read the set again (a rotation), but at most once
  every `jwks_min_refetch_s`, failures included, so a flood of tokens with invented `kid`s cannot make the hub hammer the SERVER (nor itself be slow).
* Fail-closed: if the set is not in the cache and cannot be read, there is no key and the token is refused; the cache is not served past its time to live.

The Ed25519 check is the reference of RFC 8032 in pure Python (the core of the hub depends on no package). It only handles public data, so the lack of
constant-time arithmetic is not an issue for verification.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import ipaddress
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

MAX_JWKS_BYTES = 65536
MAX_JWKS_KEYS = 16
DEFAULT_TTL_S = 300.0
DEFAULT_MIN_REFETCH_S = 30.0
DEFAULT_TIMEOUT_S = 5.0
_LOOPBACK_NAMES = frozenset({"localhost"})

# --- Ed25519 (RFC 8032, section 6) ---------------------------------------------------------------------------------------------------------------------
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _recover_x(y: int, sign: int) -> int | None:
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)  # type: ignore[operator]


def _add(p1, p2):
    a = (p1[1] - p1[0]) * (p2[1] - p2[0]) % _P
    b = (p1[1] + p1[0]) * (p2[1] + p2[0]) % _P
    c = 2 * p1[3] * p2[3] * _D % _P
    d = 2 * p1[2] * p2[2] % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(scalar: int, point):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(p1, p2) -> bool:
    return (p1[0] * p2[2] - p2[0] * p1[2]) % _P == 0 and (p1[1] * p2[2] - p2[1] * p1[2]) % _P == 0


def _compress(point) -> bytes:
    zinv = pow(point[2], _P - 2, _P)
    x, y = point[0] * zinv % _P, point[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(data: bytes):
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % _P)


def _h512(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little") % _Q


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """True only for a valid Ed25519 signature (the scalar must be reduced: a malleable signature is refused)."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a_point = _decompress(public_key)
    r_point = _decompress(signature[:32])
    if a_point is None or r_point is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    h = _h512(signature[:32] + public_key + message)
    return _equal(_mul(s, _G), _add(r_point, _mul(h, a_point)))


# --- keys ------------------------------------------------------------------------------------------------------------------------------------------
class JwksError(Exception):
    """The key set cannot be used; `str()` is a reason that holds no address, no secret and no token."""


def b64url_decode(segment: str) -> bytes:
    if not isinstance(segment, str) or not segment or not all(c.isalnum() or c in "-_" for c in segment):
        raise JwksError("a key has a value that is not base64url")
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as exc:
        raise JwksError("a key has a value that is not base64url") from exc


def thumbprint(x: bytes) -> str:
    """RFC 7638 thumbprint of an Ed25519 public key: base64url (no padding) of SHA-256 of the canonical JSON of its required members."""
    canonical = '{"crv":"Ed25519","kty":"OKP","x":"%s"}' % base64.urlsafe_b64encode(x).rstrip(b"=").decode("ascii")
    return base64.urlsafe_b64encode(hashlib.sha256(canonical.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def parse_jwks(document: object) -> dict[str, bytes]:
    """`{kid: public key}` for the usable Ed25519 keys of a JWK Set. Anything unusable is skipped; a set with none is an error."""
    if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
        raise JwksError("the key set has no list of keys")
    keys: dict[str, bytes] = {}
    for entry in document["keys"][:MAX_JWKS_KEYS]:
        if not isinstance(entry, dict) or entry.get("kty") != "OKP" or entry.get("crv") != "Ed25519":
            continue
        if entry.get("use") not in (None, "sig") or entry.get("alg") not in (None, "EdDSA"):
            continue
        try:
            x = b64url_decode(entry.get("x"))  # type: ignore[arg-type]
        except JwksError:
            continue
        kid = entry.get("kid")
        if len(x) != 32 or not isinstance(kid, str) or kid != thumbprint(x) or _decompress(x) is None:
            continue
        keys[kid] = x
    if not keys:
        raise JwksError("the key set holds no usable Ed25519 key")
    return keys


def check_jwks_url(url: object) -> str:
    """The address of the key set if it is acceptable (https, or http to a loopback address; no credentials, no fragment), else ValueError."""
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise ValueError("identity.jwks_url must be an address")
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname
    if parsed.scheme not in ("https", "http") or not host:
        raise ValueError("identity.jwks_url must be an https address")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ValueError("identity.jwks_url must carry no credentials and no fragment")
    if parsed.scheme == "http":
        loopback = host in _LOOPBACK_NAMES
        if not loopback:
            try:
                loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = False
        if not loopback:
            raise ValueError("identity.jwks_url must be https (plain http is accepted only to a loopback address)")
    try:
        parsed.port  # noqa: B018 - raises ValueError for a bad port
    except ValueError as exc:
        raise ValueError("identity.jwks_url has an invalid port") from exc
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401
        return None


def fetch_jwks_document(url: str, timeout_s: float) -> object:
    """GET the key set with a size limit, no redirect and verified TLS. Raises JwksError."""
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"Accept": "application/jwk-set+json, application/json"}, method="GET")
    try:
        with opener.open(request, timeout=timeout_s) as response:
            if response.status != 200:
                raise JwksError("the server did not answer with its key set")
            body = response.read(MAX_JWKS_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise JwksError("the key set of the server cannot be read") from exc
    if len(body) > MAX_JWKS_BYTES:
        raise JwksError("the key set is too large")
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise JwksError("the key set is not JSON") from exc


class JwksClient:
    """Public keys of the SERVER with a cache and a limit on how often the set is read. Thread-safe; every failure is a JwksError (fail-closed)."""

    def __init__(
        self,
        url: str,
        *,
        ttl_s: float = DEFAULT_TTL_S,
        min_refetch_s: float = DEFAULT_MIN_REFETCH_S,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        clock: Callable[[], float] = time.monotonic,
        fetcher: Callable[[str, float], object] = fetch_jwks_document,
    ) -> None:
        self.url = check_jwks_url(url)
        for name, value in (("jwks_ttl_s", ttl_s), ("jwks_min_refetch_s", min_refetch_s), ("jwks_timeout_s", timeout_s)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 86400:
                raise ValueError(f"identity.{name} must be a number of seconds between 0 and 86400")
        self.ttl_s, self.min_refetch_s, self.timeout_s = float(ttl_s), float(min_refetch_s), float(timeout_s)
        self._clock, self._fetcher = clock, fetcher
        self._keys: dict[str, bytes] = {}
        self._loaded_at: float | None = None      # when the cached set was read
        self._attempted_at: float | None = None   # when the last read was tried, failed or not
        self._lock = threading.Lock()
        self.fetches = 0

    def _refresh(self, now: float) -> None:
        self._attempted_at = now
        self.fetches += 1
        keys = parse_jwks(self._fetcher(self.url, self.timeout_s))   # on failure the old cache stays but is never served past its time to live
        self._keys, self._loaded_at = keys, now

    def public_key(self, kid: str) -> bytes:
        """The public key published under `kid`, or JwksError."""
        with self._lock:
            now = self._clock()
            fresh = self._loaded_at is not None and now - self._loaded_at < self.ttl_s
            if fresh and kid in self._keys:
                return self._keys[kid]
            may_read = self._attempted_at is None or now - self._attempted_at >= self.min_refetch_s
            if may_read:
                self._refresh(now)
                fresh = True
            elif not fresh:
                raise JwksError("the key set of the server is not available")
            key = self._keys.get(kid) if fresh else None
            if key is None:
                raise JwksError("the token names a key that the server does not publish")
            return key
