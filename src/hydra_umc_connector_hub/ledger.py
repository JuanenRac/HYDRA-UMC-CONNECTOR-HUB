# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/ledger.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A sealed, hash-chained certification record, so that "append-only" can be checked and not only promised.

`certification.py` writes one JSON file per certification and never overwrites one. That stops this program from
editing a record; it does not stop anybody with access to the folder from editing or deleting a file by hand, and
nothing would show it. With a key (a secret the operator holds, in a file with the permissions of a secret), each
record is written with a `chain` block:

  * `sequence`: 1, 2, 3 ... with no gap;
  * `previousHash`: the sha256 of the whole previous file (its `chain` block included), so editing a record, or
    removing one from the middle, breaks the link after it;
  * `seal`: an HMAC-SHA256 of the record and its chain fields under the key, so a record cannot be made, or changed
    and re-chained, by someone without the key.

A small `.chain-head.json`, sealed the same way, says how long the chain is and the hash of its last record, so removing
the newest records is seen too. `verify_chain` goes through all of it. Without a key nothing here is used and records are
written exactly as before. A record in the folder that has no `chain` block (written before sealing, or put there by hand)
is reported as unsealed: the chain does not cover it, and `strict` turns that into a failure.

What this is not: a signature. The HMAC key verifies and also seals, so whoever holds it can rewrite the whole chain.
It stops the people who can reach the folder and not the key.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HEAD_FILE = ".chain-head.json"
LOCK_FILE = ".chain.lock"
MIN_KEY_LENGTH = 16
_LOCK_WAIT_SECONDS = 5.0
_LOCK_STALE_SECONDS = 30.0


class LedgerError(ValueError):
    """The chain cannot be extended or the key cannot be used."""


def load_key(path: str) -> bytes:
    """The key from a file: its text, stripped, at least 16 characters."""
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise LedgerError(f"the key file cannot be read: {exc}") from exc
    if len(text) < MIN_KEY_LENGTH:
        raise LedgerError(f"the key must have at least {MIN_KEY_LENGTH} characters")
    return text.encode("utf-8")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _seal(key: bytes, body: dict[str, Any]) -> str:
    return hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()


def file_hash(document: dict[str, Any]) -> str:
    """sha256 of a record file as a whole: the record, its chain fields and its seal."""
    return hashlib.sha256(_canonical(document)).hexdigest()


def _sealed_document(record: dict[str, Any], sequence: int, previous_hash: str, key: bytes) -> dict[str, Any]:
    chain = {"sequence": sequence, "previousHash": previous_hash}
    seal = _seal(key, {**record, "chain": chain})
    return {**record, "chain": {**chain, "seal": seal}}


def _head_document(sequence: int, last_hash: str, key: bytes) -> dict[str, Any]:
    body = {"sequence": sequence, "hash": last_hash}
    return {**body, "seal": _seal(key, {"head": body})}


@dataclass
class ChainReport:
    ok: bool
    sealed: int = 0
    unsealed: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "sealed": self.sealed, "unsealed": list(self.unsealed), "problems": list(self.problems)}


def _read_documents(directory: Path) -> list[tuple[str, dict[str, Any]]]:
    documents: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name == HEAD_FILE:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and "certificationId" in data:
            documents.append((path.name, data))
    return documents


def _chain_of(document: dict[str, Any]) -> dict[str, Any] | None:
    chain = document.get("chain")
    if (
        isinstance(chain, dict)
        and isinstance(chain.get("sequence"), int) and not isinstance(chain.get("sequence"), bool)
        and isinstance(chain.get("previousHash"), str) and isinstance(chain.get("seal"), str)
    ):
        return chain
    return None


class _Lock:
    """One writer at a time for the chain: a lock file created exclusively; one left by a dead process goes stale."""

    def __init__(self, directory: Path) -> None:
        self._path = directory / LOCK_FILE

    def __enter__(self) -> "_Lock":
        deadline = time.monotonic() + _LOCK_WAIT_SECONDS
        while True:
            try:
                descriptor = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    if time.time() - self._path.stat().st_mtime > _LOCK_STALE_SECONDS:
                        self._path.unlink()
                        continue
                except OSError:
                    continue
                if time.monotonic() > deadline:
                    raise LedgerError("another process is writing to the certification chain")
                time.sleep(0.05)
                continue
            os.close(descriptor)
            return self

    def __exit__(self, *exc: object) -> None:
        try:
            self._path.unlink()
        except OSError:
            pass


def verify_chain(directory: str, key: bytes, *, strict: bool = False) -> ChainReport:
    """Every problem found in the certification folder `directory`; `ok` when there is none (and, with `strict`,
    nothing is unsealed)."""
    target = Path(directory)
    report = ChainReport(ok=True)
    if not target.is_dir():
        report.problems.append(f"{directory} is not a folder")
        report.ok = False
        return report
    sealed: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for name, document in _read_documents(target):
        chain = _chain_of(document)
        if chain is None:
            report.unsealed.append(name)
        else:
            sealed.append((name, document, chain))
    sealed.sort(key=lambda item: item[2]["sequence"])
    report.sealed = len(sealed)

    previous_hash = ""
    previous_sequence = 0
    last_hash = ""
    for name, document, chain in sealed:
        body = {k: v for k, v in document.items() if k != "chain"}
        expected_seal = _seal(key, {**body, "chain": {"sequence": chain["sequence"], "previousHash": chain["previousHash"]}})
        if not hmac.compare_digest(expected_seal, chain["seal"]):
            report.problems.append(f"{name}: the seal does not match (the record was changed, or it was not made with this key)")
        if chain["sequence"] == previous_sequence:
            report.problems.append(f"{name}: sequence {chain['sequence']} is used twice (the chain forked)")
        elif previous_sequence and chain["sequence"] != previous_sequence + 1:
            report.problems.append(f"{name}: sequence jumps from {previous_sequence} to {chain['sequence']} (a record is missing)")
        elif not previous_sequence and chain["sequence"] != 1:
            report.problems.append(f"{name}: the chain starts at sequence {chain['sequence']}, not 1 (the first records are missing)")
        if chain["previousHash"] != previous_hash:
            report.problems.append(f"{name}: it does not follow the record before it (that one was changed or removed)")
        previous_hash = file_hash(document)
        previous_sequence = chain["sequence"]
        last_hash = previous_hash

    head_path = target / HEAD_FILE
    if sealed or head_path.exists():
        try:
            head = json.loads(head_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            head = None
            report.problems.append(f"{HEAD_FILE} is missing or unreadable (records could have been removed from the end)")
        if isinstance(head, dict):
            body = {"sequence": head.get("sequence"), "hash": head.get("hash")}
            if not isinstance(head.get("seal"), str) or not hmac.compare_digest(_seal(key, {"head": body}), head["seal"]):
                report.problems.append(f"{HEAD_FILE}: the seal does not match")
            elif head.get("sequence") != previous_sequence or head.get("hash") != last_hash:
                report.problems.append(
                    f"{HEAD_FILE} says the chain has {head.get('sequence')} record(s) and the folder has {previous_sequence} "
                    "(the newest records were removed, or the head was replaced)"
                )
    if strict and report.unsealed:
        report.problems.append(f"{len(report.unsealed)} record(s) are outside the chain: {', '.join(report.unsealed)}")
    report.ok = not report.problems
    return report


def append_sealed(record_dict: dict[str, Any], directory: str, path_for: str, key: bytes) -> str:
    """Write `record_dict` as the next record of the chain in `directory`, in the file named `path_for`, and move the head.

    The same record saved again (the file exists with the same record) is a no-op that returns its path; another
    record under the same file name is refused, as before. Returns the path."""
    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)
    path = (target / path_for).resolve()
    if not path.is_relative_to(target):
        raise LedgerError(f"refusing to write a record outside {target}")
    with _Lock(target):
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if {k: v for k, v in existing.items() if k != "chain"} == record_dict:
                return str(path)
            raise LedgerError(f"refusing to overwrite {path.name}: a different record already exists under this id")
        sealed = sorted(
            ((chain["sequence"], document) for _, document in _read_documents(target) if (chain := _chain_of(document))),
            key=lambda item: item[0],
        )
        sequence = sealed[-1][0] + 1 if sealed else 1
        previous_hash = file_hash(sealed[-1][1]) if sealed else ""
        document = _sealed_document(record_dict, sequence, previous_hash, key)
        payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        head = _head_document(sequence, file_hash(document), key)
        temporary = target / (HEAD_FILE + ".tmp")
        temporary.write_text(json.dumps(head, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, target / HEAD_FILE)
    return str(path)
