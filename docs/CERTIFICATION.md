# Certification Records (Delivery 4, [P1][HARDWARE])

The proposal's own wording for this delivery is explicit: *"no hay
etiqueta universal global, cada perfil conserva su propia evidencia"* -
certify adapters one at a time against their own real target machine;
there is no single "certified" checkbox for an adapter in the abstract.

`certification.py` is the real, honest **software half** of that: a
real, append-only, human-attested record of who certified which adapter
against which real machine model, with which real evidence.

## What `certify_adapter()` actually checks

A certification is refused (`CertificationError`, every real reason
collected, never just the first) unless **all** of the following hold:

1. The adapter's own manifest is still structurally valid
   (`validate_adapter_manifest()`).
2. The supplied `evidence` is a JSON object that matches that adapter's
   own declared `evidenceSchema` (`validate_against_json_schema_subset()`
   - the same small, dependency-free JSON-Schema-subset checker
   `sdk_gate.py`'s evidence check uses).
3. `machine_model` and `certified_by` are both real, non-empty strings.

A record that passes all three gets a real `certificationId` (a fresh
UUID4), a real `certifiedAt` timestamp (UTC, ISO 8601), and is saved as
its own never-overwritten JSON file under the target directory - a
second certification of the same adapter (after a firmware update, a
different unit of the same model) is a second file, side by side with
the first, never a silent overwrite.

## What this module deliberately does NOT do

There is no code path anywhere in `certification.py` that opens a real
serial port, OPC-UA session or MQTT connection to independently confirm
the supplied evidence actually came from the named machine. That kind of
automated hardware verification genuinely needs the real, physical
machine this delivery is tagged `[HARDWARE]` for - which this
development machine does not have. Producing honest evidence (a real
status read, a real position report, a real health-check response
copied from the actual target machine) stays the human certifier's own
responsibility; this module's real, verifiable job stops at refusing to
record a certification whose evidence does not even match the adapter's
own self-declared shape, and at never losing or silently altering a
record it did accept.

This gap is named here on purpose, the same way HYDRA-UMC-OPS-AGENT's
own Delivery 6 names why voice/notification integration is genuinely
blocked rather than pretending a stub proves something it does not.

## Real example

```
$ hydra-umc-connector-hub certify fixtures/cnc-grbl.json \
    --machine-model "Genmitsu 3018-PROVer" --certified-by "Juan Enrique" \
    --evidence-file real-grbl-status.json --out-dir certifications/
CERTIFIED adapterId='cnc-grbl' certificationId='a1b2c3d4e5f6...' -> certifications/cnc-grbl__a1b2c3d4e5f6....json

$ hydra-umc-connector-hub certifications --dir certifications/ --adapter-id cnc-grbl
[
  {
    "certificationId": "a1b2c3d4e5f6...",
    "adapterId": "cnc-grbl",
    "machineModel": "Genmitsu 3018-PROVer",
    "certifiedBy": "Juan Enrique",
    "certifiedAt": "2026-...T...+00:00",
    "evidence": { "status": "Idle", "machinePosition": [0.0, 0.0, 0.0] },
    "notes": ""
  }
]
```

## Sealing the records: making "append-only" checkable

Writing a file only once stops this program from editing a record; it does not stop anybody with access to the folder
from editing or deleting a file by hand. With `certify --key-file FILE` (a secret of 16 or more characters, held by the
operator) every record is written with a `chain` block - its `sequence` (1, 2, 3, no gap), the `previousHash` (sha256 of
the whole previous file) and a `seal` (HMAC-SHA256 of the record and those two fields under the key) - and a sealed
`.chain-head.json` says how long the chain is. `verify-certifications --dir D --key-file FILE` goes through it and fails
on an edited record (its seal, and the link of the one after it), a record removed from the middle (a gap), the first
ones removed (it does not start at 1), the newest ones removed (the head), two records with one sequence (a fork), a
head rewritten without the key, and a wrong key. A record in the folder with no `chain` block (written before sealing,
or put there by hand) is listed as unsealed and `--strict` makes it a failure. Without `--key-file` records are
written as before.

This is an HMAC, not a signature: the key verifies and also seals, so whoever holds it can rewrite the whole chain. It
stops people who can reach the folder and not the key. A chain with asymmetric signatures would need a decision on key
management that is not made.

See [docs/CLI_REFERENCE.md](CLI_REFERENCE.md) for the full `certify`/
`certifications` command surface.
