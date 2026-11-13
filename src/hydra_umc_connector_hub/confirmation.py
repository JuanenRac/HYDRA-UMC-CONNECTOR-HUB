# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/confirmation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The human confirmation of a call, as a short signed token of HYDRA-UMC-SERVER that can be used once.

A capability that declares `requiresHumanConfirmation` used to be satisfied by the caller writing `humanConfirmed: true`: the caller vouched for itself.
Now the hub believes a confirmation only when it comes with `confirmationToken`, a token that the SERVER signs (the same key or key set that verifies the
identity of the caller, see `identity.py`) when an operator confirms in person. The token is a JWT with the claims

    username, role      the person who confirmed (`admin` or `operator`)
    purpose             exactly "human-confirmation" (an ordinary login token is not a confirmation)
    jti                 a unique id; the hub accepts each one ONCE
    jobId, adapterId, capability
                        the one call it confirms: a token for another job, adapter or capability is refused
    iat, exp            at most 120 seconds apart, and not expired

so a confirmation cannot be replayed, moved to another call or kept for later. The hub only VERIFIES such a token; the SERVER issues it. This module is
the same shape that the other services of the family use for the confirmation of a flight or a move (one piece for the whole ecosystem).

The switch `allowUnsignedHumanConfirmation` (command line `--allow-unsigned-human-confirmation`, or the settings file) is OFF by default; turned on, the
boolean `humanConfirmed` of the request is believed again, as before, and every decision says so (`confirmation.source`).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from .identity import DECIDE_ROLES, IdentityError, TokenVerifier

PURPOSE = "human-confirmation"
MAX_LIFETIME_S = 120.0
MAX_LEDGER_ENTRIES = 10_000
MAX_JTI_CHARS = 128


class ConfirmationError(Exception):
    """The confirmation is not valid; `str()` is the reason that is recorded."""


@dataclass(frozen=True)
class Confirmation:
    username: str
    role: str
    jti: str
    expires_at: float

    def as_audit(self, source: str = "token") -> dict[str, Any]:
        return {"source": source, "by": self.username, "role": self.role, "jti": self.jti}


class ConfirmationLedger:
    """The `jti` already used, until their expiry. Bounded: when it is full of tokens that have not expired, nothing more is accepted (fail-closed)."""

    def __init__(self, max_entries: int = MAX_LEDGER_ENTRIES) -> None:
        self._max = max_entries
        self._used: dict[str, float] = {}
        self._lock = threading.Lock()

    def claim(self, jti: str, expires_at: float, *, now: float) -> bool:
        with self._lock:
            if len(self._used) >= self._max:
                for key in [key for key, until in self._used.items() if until <= now]:
                    del self._used[key]
            if jti in self._used and self._used[jti] > now:
                return False
            if len(self._used) >= self._max:
                raise ConfirmationError("too many confirmations are waiting to expire; none is accepted for now")
            self._used[jti] = expires_at
            return True

    def release(self, jti: str) -> None:
        """Give a claim back (the call was denied for another reason, so nothing was confirmed in effect)."""
        with self._lock:
            self._used.pop(jti, None)


def verify_confirmation(
    token: object,
    verifier: TokenVerifier,
    *,
    job_id: str,
    adapter_id: str,
    capability: str,
    ledger: ConfirmationLedger,
    now: float | None = None,
) -> Confirmation:
    """The confirmation in `token` for exactly this call, claimed in the ledger, or ConfirmationError saying why there is none."""
    moment = time.time() if now is None else now
    if not isinstance(token, str) or not token:
        raise ConfirmationError("a signed confirmation of HYDRA-UMC-SERVER is required (confirmationToken)")
    try:
        identity, claims = verifier.verify_claims(token, now=moment)
    except IdentityError as exc:
        raise ConfirmationError(f"the confirmation is not valid: {exc}") from exc
    if claims.get("purpose") != PURPOSE:
        raise ConfirmationError("the token is not a human confirmation (purpose)")
    if identity.role not in DECIDE_ROLES:
        raise ConfirmationError(f"the role {identity.role!r} may not confirm")
    jti = claims.get("jti")
    if not isinstance(jti, str) or not jti or len(jti) > MAX_JTI_CHARS:
        raise ConfirmationError("the confirmation has no unique id (jti)")
    iat = claims.get("iat")
    exp = claims.get("exp")
    if isinstance(iat, bool) or not isinstance(iat, (int, float)):
        raise ConfirmationError("the confirmation says when it was issued (iat) in no readable way")
    if exp - iat > MAX_LIFETIME_S:  # exp was checked as a finite number by the identity checks
        raise ConfirmationError(f"the confirmation lives longer than {MAX_LIFETIME_S:g} seconds")
    for name, wanted in (("jobId", job_id), ("adapterId", adapter_id), ("capability", capability)):
        if not wanted or claims.get(name) != wanted:
            raise ConfirmationError(f"the confirmation is not for this call ({name})")
    if not ledger.claim(jti, float(exp), now=moment):
        raise ConfirmationError("the confirmation was already used")
    return Confirmation(identity.username or "", identity.role, jti, float(exp))
