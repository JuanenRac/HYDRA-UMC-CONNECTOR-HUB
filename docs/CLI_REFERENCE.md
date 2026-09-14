# CLI Reference

`hydra-umc-connector-hub` (or `python -m hydra_umc_connector_hub.cli`)
has one real subcommand per delivery this project ships so far. There is
no default/bare invocation - a command is always required.

## `validate <file> [<file> ...]`

Validates one or more adapter-manifest JSON files against the real
contract in [docs/ADAPTER_MANIFEST.md](ADAPTER_MANIFEST.md). Touches no
network, no hardware, no real machine - only reads the file(s) given.

```
hydra-umc-connector-hub validate fixtures/industrial-opcua.json
hydra-umc-connector-hub validate fixtures/*.json
```

For each file, one of three real outcomes:

- **`VALID <path> adapterId=... ownerProject=...`** on stdout - the file
  parsed as JSON and passed every structural check.
- **`INVALID <path> (adapterId=...): ...`** on stderr, followed by every
  real reason (not just the first one) indented on its own line - the
  file parsed as JSON but failed one or more structural checks.
- **`ERROR: <path>: ...`** on stderr - the file could not be read, or
  was not valid JSON at all (distinct from a structurally invalid but
  well-formed manifest).

Exit code `0` only if every file given was `VALID`; `1` if any file was
`INVALID` or produced an `ERROR`. Validating multiple files always
reports every one of them, even after the first failure - a caller
checking a whole `fixtures/` directory sees every real problem in one
run.

## `catalog --registry-dir <dir> [--ecosystem-root <dir>]`

Prints, as JSON on stdout, the real read-only catalog built from every
`*.json` file directly inside `<dir>` (non-recursive - a nested
`invalid/` subdirectory is never scanned). Each catalog entry is a
summary (`adapterId`, `protocol`, `targetKinds`, `ownerProject`,
`sdkCompatibility`, `idempotency`, `capabilities: [{name, mode}]`), never
the full `endpointSchema`/`evidenceSchema` bodies - fetch
`catalog/<adapterId>` (via `serve-catalog`, below) once a caller already
knows which adapter it wants.

```
hydra-umc-connector-hub catalog --registry-dir fixtures
```

Output also includes `invalidFiles` (a map of file name to its real
validation errors) for anything in `<dir>` that failed
`validate_adapter_manifest()` - it is left out of `adapters` but never
silently dropped. Exit code `0` only if `invalidFiles` is empty (and, when
`--ecosystem-root` is given, `unverifiedOwners` too).

`ownerProject` is only ever shape-checked by
`validate_adapter_manifest()` itself (does it look like a real
`HYDRA-UMC-*`/`URTC-*` project name) - PROM-HUB-F02's real second half is
`--ecosystem-root`, an optional path to a real directory of sibling
project checkouts. When given, every entry's own `ownerProject` is
verified for real against that project's own `hydra-umc.project.json`
(must exist, and its own `name` must equal `ownerProject`) via
`registry.verify_catalog_owners()`; any failure is reported under a new
`unverifiedOwners` key (adapter id -> real reason) and fails the exit
code. Omitted, `unverifiedOwners` never appears in the output at all -
there is nothing honest to verify without a real ecosystem root, so this
never silently claims every owner is verified when none were checked.

PROM-HUB-E01: the output also always carries `snapshotVersion` - a real,
deterministic SHA-256 over the catalog's own canonical content
(`registry.catalog_snapshot_version()`), never a random id or a
timestamp. Unchanged real registry contents always yield the exact same
version across separate calls; any real addition/removal/edit changes
it. See `serve-catalog` below for the real HTTP `ETag`/conditional-GET
use of this same value.

## `serve-catalog --registry-dir <dir> [--host HOST] [--port PORT]`

Serves the same real catalog over a real, GET-only `http.server`
(default `127.0.0.1:8801`). Three routes, nothing else:

- **`GET /catalog`** — the same JSON `catalog` prints (including
  `snapshotVersion`), live-rebuilt from `<dir>` on every request (so a
  manifest edited on disk shows up on the very next poll, no restart
  needed). The response also carries a real `ETag` header equal to
  `"<snapshotVersion>"`; send it back as `If-None-Match` on a later
  request and get a real `304 Not Modified` (empty body) the instant the
  registry genuinely has not changed since - PROM-HUB-E01's own
  "transactional reload" half: a client always gets either the honest
  "nothing changed" answer or one complete, freshly-rescanned body,
  never a partial/torn one.
- **`GET /catalog/<adapterId>`** — the full real manifest for one
  registered, structurally-valid adapter, or a real `404` if no such
  adapter is registered.
- **`GET /health`** — `{"status": "ok", "adapterCount": N,
  "invalidFileCount": M}`.

There is no `POST`/`PUT`/`DELETE` route anywhere in this server - any
write attempt gets a real `501 Unsupported method` from
`BaseHTTPRequestHandler` itself, never a route this project forgot to
protect. Runs until `Ctrl+C`.

## `gate <manifest-file> --capability NAME --job-id ID --idempotency-key KEY --source SRC --cell-state STATE --machine-state STATE [--param k=v ...] [--evidence-file FILE] [--permission PERM ...] [--cell-mode MODE] [--human-confirmed] [--safety-gate GATE ...]`

Evaluates one real capability call against
[docs/CAPABILITY_GATE.md](CAPABILITY_GATE.md)'s own contract - a `read`
capability is always allowed without needing HYDRA-UMC-SDK installed at
all; a `write`/`abort` capability must first satisfy its own declared
policy (`--permission`/`--cell-mode`/`--human-confirmed`/`--safety-gate`
- see CAPABILITY_GATE.md, V07-006) and is THEN gated by HYDRA-UMC-SDK's
own real `evaluate_job()` (requires the optional `[sdk]` extra - see
`pip install -e ".[sdk]"`). `--cell-state` is one of
`READY`/`INHIBITED`/`FAULT`/`SAFE_STOP`; `--machine-state` is one of
`OFFLINE`/`IDLE`/`RUNNING`/`HOLDING`/`FAULT`/`SAFE_STOP` (HYDRA-UMC-SDK's
own real enums - an unrecognised value is a real `ERROR`, not a
best-effort guess). `--cell-mode` is a DIFFERENT, adapter-defined axis
(e.g. `operational`/`supervised`/`ready`/`any`) checked against the
capability's own `requiredCellState` - never confuse it with
`--cell-state` above. `--permission` and `--safety-gate` are each
repeatable.

```
hydra-umc-connector-hub gate fixtures/cnc-grbl.json \
    --capability sendControlByte --job-id j1 --idempotency-key i1 \
    --source studio --cell-state READY --machine-state IDLE \
    --permission cnc.control.send --cell-mode supervised --human-confirmed \
    --safety-gate cell.estop.clear --safety-gate cell.enclosure.closed
```

Prints the real `{"allowed": bool, "reason": str, "evidenceErrors":
[...]}` decision as JSON. Exit code `0` only if `allowed` is `true`.
Omitting `--permission`/`--cell-mode`/`--human-confirmed`/`--safety-gate`
for a `write`/`abort` capability that declares them denies the call on
policy grounds - this is the safe default, not an oversight to work
around. `--evidence-file` is optional; when given, its JSON content is
checked against the manifest's own `evidenceSchema` and folds into
`allowed`/`evidenceErrors` even when the safety gate itself would have
said yes.

## `certify <manifest-file> --machine-model NAME --certified-by NAME --evidence-file FILE [--notes TEXT] --out-dir DIR`

Records one real, human-attested certification - see
[docs/CERTIFICATION.md](CERTIFICATION.md) for the full contract and its
honest limits. Refused (`ERROR`, exit `1`) unless the manifest is
structurally valid AND the evidence file's own JSON content matches that
adapter's `evidenceSchema`. On success, writes one new JSON file under
`--out-dir` (never overwriting a previous certification of the same
adapter) and prints `CERTIFIED adapterId=... certificationId=... -> <path>`.

## `certifications --dir DIR [--adapter-id ID]`

Prints every real certification record saved under `--dir` (optionally
filtered to one `adapterId`) as a JSON array, sorted by `certifiedAt`
(oldest first). An empty or missing directory prints `[]`, not an error.

## `--version`

Prints the installed `hydra_umc_connector_hub.__version__` and exits `0`.

## What does not exist yet

There is no command that independently probes a real machine (serial
port, OPC-UA endpoint, MQTT broker) to confirm a certification's own
evidence is genuine - `certify` records a human's own attestation, it
does not verify it against real hardware. See
[docs/CERTIFICATION.md](CERTIFICATION.md) for exactly why that stays out
of this project's real, honest scope without the physical machine in
hand.
