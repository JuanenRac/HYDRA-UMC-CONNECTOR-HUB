# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/gate_audit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The record of every decision of the gate service: one JSON line each, chained by hash and, with a key, sealed.

Each line carries `seq` (1, 2, 3 ... with no gap), `at` (UTC), the decision, `prevHash` (the hash of the line before; 64 zeros for the first) and
`hash` (SHA-256 over the line without `hash` and `seal`). With a key every line also carries `seal`, an HMAC-SHA256 of its hash: without the key a
line cannot be made, or changed and re-chained. Opening the file again verifies all of it first and refuses a file that does not verify, so a
service never goes on writing after a file that was edited or cut in the middle. (Removing the newest lines cannot be seen from the file alone;
`head()` is what an operator keeps elsewhere to notice that.)

A line that cannot be written is an error for the caller: the gate service turns the decision into a denial, because a decision nobody can see
afterwards is not one that may let a machine move.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
MIN_KEY_LENGTH = 16
_KEPT = 200


class GateAuditError(ValueError):
    """The audit file cannot be verified or written."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _hash_of(record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k not in ("hash", "seal")}
    return hashlib.sha256(_canonical(body)).hexdigest()


def _seal_of(key: bytes, digest: str) -> str:
    return hmac.new(key, digest.encode("ascii"), hashlib.sha256).hexdigest()


def load_key(path: str) -> bytes:
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise GateAuditError(f"the audit key file cannot be read: {exc}") from exc
    if len(text) < MIN_KEY_LENGTH:
        raise GateAuditError(f"the audit key must have at least {MIN_KEY_LENGTH} characters")
    return text.encode("utf-8")


def verify_records(records: list[dict[str, Any]], key: bytes | None) -> None:
    """Raises GateAuditError at the first line that does not verify."""
    previous = GENESIS
    for index, record in enumerate(records, start=1):
        if record.get("seq") != index:
            raise GateAuditError(f"line {index}: the sequence number is {record.get('seq')!r}, expected {index}")
        if record.get("prevHash") != previous:
            raise GateAuditError(f"line {index}: it does not follow the line before it")
        digest = _hash_of(record)
        if record.get("hash") != digest:
            raise GateAuditError(f"line {index}: its content does not match its hash")
        if key is not None and not hmac.compare_digest(str(record.get("seal", "")), _seal_of(key, digest)):
            raise GateAuditError(f"line {index}: the seal is missing or was made with another key")
        previous = digest


class GateAudit:
    def __init__(self, path: str, key: bytes | None = None) -> None:
        self._path = Path(path)
        self._key = key
        self._lock = threading.Lock()
        self._recent: list[dict[str, Any]] = []
        self._seq = 0
        self._last = GENESIS
        if self._path.exists():
            records: list[dict[str, Any]] = []
            for number, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except ValueError as exc:
                    raise GateAuditError(f"line {number}: it is not JSON") from exc
                if not isinstance(item, dict):
                    raise GateAuditError(f"line {number}: it is not an object")
                records.append(item)
            verify_records(records, key)
            if records:
                self._seq = records[-1]["seq"]
                self._last = records[-1]["hash"]
                self._recent = records[-_KEPT:]
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def signed(self) -> bool:
        return self._key is not None

    def head(self) -> dict[str, Any] | None:
        with self._lock:
            return {"seq": self._seq, "hash": self._last} if self._seq else None

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._recent[-max(1, limit):])

    def append(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Writes one line and flushes it to disk before returning. Raises GateAuditError when it cannot."""
        with self._lock:
            record = dict(decision)
            record["seq"] = self._seq + 1
            record["at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            record["prevHash"] = self._last
            record["hash"] = _hash_of(record)
            if self._key is not None:
                record["seal"] = _seal_of(self._key, record["hash"])
            line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
            try:
                with open(self._path, "a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise GateAuditError(f"the audit line cannot be written: {exc}") from exc
            self._seq = record["seq"]
            self._last = record["hash"]
            self._recent.append(record)
            del self._recent[:-_KEPT]
            return record
