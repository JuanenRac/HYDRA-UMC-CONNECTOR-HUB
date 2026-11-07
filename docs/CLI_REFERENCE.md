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
`HYDRA-UMC-*`/`URTC-*` project name) - the real second half is
`--ecosystem-root`, an optional path to a real directory of sibling
project checkouts. When given, every entry's own `ownerProject` is
verified for real against that project's own `hydra-umc.project.json`
(must exist, and its own `name` must equal `ownerProject`) via
`registry.verify_catalog_owners()`; any failure is reported under a new
`unverifiedOwners` key (adapter id -> real reason) and fails the exit
code. Omitted, `unverifiedOwners` never appears in the output at all -
there is nothing honest to verify without a real ecosystem root, so this
never silently claims every owner is verified when none were checked.

The output also always carries `snapshotVersion` - a real,
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
  registry genuinely has not changed since - the same
  "transactional reload" guarantee: a client always gets either the honest
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

`--ecosystem-root DIR` (optional) lists only the adapters whose `ownerProject`
is confirmed by that project's own `hydra-umc.project.json` under `DIR`; the
others are reported under `unverifiedOwners`. `sourcePath` in the answer is the
manifest's file name, never a path on the server. A query string or a trailing
slash does not change the route, and `If-None-Match` may carry a list of tags
and weak tags.

A manifest file that is not valid UTF-8, larger than 1 MB, or nested thousands of
levels deep is listed under `invalidFiles` like any other broken file instead of
stopping the catalog; if the registry directory disappears while the server runs,
requests get a `503` with a JSON error; and a connection that sends
nothing for 15 seconds is closed.

## `gate <manifest-file> --capability NAME --job-id ID --idempotency-key KEY --source SRC --cell-state STATE --machine-state STATE [--param k=v ...] [--evidence-file FILE] [--permission PERM ...] [--cell-mode MODE] [--human-confirmed] [--safety-gate GATE ...] [--observed-machine-state STATE] [--allow-unobserved]`

Evaluates one real capability call against
[docs/CAPABILITY_GATE.md](CAPABILITY_GATE.md)'s own contract - a `read`
capability is always allowed without needing HYDRA-UMC-SDK installed at
all; a `write`/`abort` capability must first satisfy its own declared
policy (`--permission`/`--cell-mode`/`--human-confirmed`/`--safety-gate`
- see CAPABILITY_GATE.md) and is THEN gated by HYDRA-UMC-SDK's
own real `evaluate_job()` (requires the optional `[sdk]` extra - see
`pip install -e ".[sdk]"`). `--cell-state` is one of
`READY`/`INHIBITED`/`FAULT`/`SAFE_STOP`; `--machine-state` is one of
`OFFLINE`/`IDLE`/`RUNNING`/`HOLDING`/`FAULT`/`SAFE_STOP` (HYDRA-UMC-SDK's
own real enums - an unrecognised value is a real `ERROR`, not a
best-effort guess). `--cell-mode` is a DIFFERENT, adapter-defined axis
(e.g. `operational`/`supervised`/`ready`/`any`) checked against the
capability's own `requiredCellState` - never confuse it with
`--cell-state` above. `--permission` and `--safety-gate` are each
repeatable. Every one of these is attested by the caller, so a decision is
advisory (see [CAPABILITY_GATE.md](CAPABILITY_GATE.md)); `--observed-machine-state`
(same values as `--machine-state`) is the state the caller itself observed and,
when given, replaces the claimed one in the SDK gate. Without it a write is
refused (the claim is not a reading); `--allow-unobserved` is the explicit
opt-in of a caller that cannot read the machine, and the answer then says
`"observed": false`. A `--evidence-file` that
cannot be read as JSON is an `ERROR` (exit `1`).

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

## `probe`

`hydra-umc-connector-hub probe --registry-dir DIR --endpoints-file FILE [--adapter-id ID] [--timeout SECONDS]` runs the `healthCheck` declared by the manifests against the places of the endpoints file, a JSON object `{"<adapterId>": {"host": "...", "port": 1234, "scheme": "http"}}` (`scheme` is `http` or `https`, only used by `http-get`; an entry for `serial-probe` or `gpio-read` may instead be `{"device": "/dev/ttyUSB0"}`, a path under `/dev/`). Exit code 1 when any result is not healthy. The result of each adapter has `type`, `supported`, `healthy`, `detail`, `latencyMs` and `checked` (`http`, `tcp`, `mqtt-connack`, `opcua-hello`, `device-open`, `tcp-reach` or `mavlink-heartbeat`: what the check proved and nothing more). See [`health_probe.py`](../src/hydra_umc_connector_hub/health_probe.py) for what each type does.

`serve-catalog --endpoints-file FILE` adds `GET /probe/<adapterId>` for the adapters of that file (answers cached for five seconds, 404 for any other adapter); without the file the catalog stays read-only and the route answers 404.

## `collect`

`hydra-umc-connector-hub collect --ecosystem-root DIR --registry-dir DIR [--apply]` gathers the manifests that the projects publish in `docs/adapter-manifest.json` or `docs/adapter-manifests/*.json` of their own checkouts. Without `--apply` it reports what it would write. The report lists `collected`, `unchanged` and `skipped` (with the reasons); exit code 1 when anything was skipped.

## `serve-gate`

`hydra-umc-connector-hub serve-gate --registry-dir DIR (--identity-key-file FILE | --allow-loopback-no-identity) --audit-file FILE [--config-file FILE] [--audit-key-file FILE] [--cell-state-url URL --cell-state-token-file FILE --cell-state-max-age-s 5] [--datalake-url URL --datalake-token-file FILE] [--host 127.0.0.1] [--port 8802]`

- **Who may ask (fail-closed).** Every route but `GET /health` needs `Authorization: Bearer <token>`, where the token is the one HYDRA-UMC-SERVER issues at login: a JWT signed with HS256 whose key is the SERVER's `JWT_SECRET`, with the claims `username`, `role` (`admin`, `operator` or `viewer`) and `exp` (required). `--identity-key-file` names the file with that key (at least 32 characters; the key is never taken from the command line and never printed). A request with no token, an expired, tampered or foreign one, or any algorithm other than HS256 is answered `401` with the reason (`code: IDENTITY_REQUIRED`) and is not evaluated; a `viewer` may read `/gate/audit` and `/metrics` but a decision at `/gate/evaluate` needs `operator` or `admin` (`403`, `code: ROLE_FORBIDDEN`). Each recorded decision carries `caller` (`username`, `role`, `identitySource`). The hub only verifies; it does not see the revocations the SERVER keeps (changed password, deleted account), so give the account that calls the hub a short `JWT_EXPIRES_IN`. Without a key and without the switch below, the service does not start.
- **The key file also comes from the environment.** `HYDRA_UMC_CONNECTOR_HUB_IDENTITY_KEY_FILE` names the file with the key when `--identity-key-file` is not given (the settings file `identityKeyFile` comes last), which is how the identity command of HYDRA-UMC-OS hands the key to this service as it does to the others. The short token that HYDRA-UMC-SERVER signs for its own calls (HS256, `username`, `role`, `exp`) is a token like any other here; this service keeps its own verifier and its key set of EdDSA.
- **Tokens signed with a key pair (EdDSA), verified with the public keys of the SERVER.** When the SERVER is set to sign with Ed25519 it publishes its public keys at `GET /.well-known/jwks.json`, and the hub can verify those tokens without holding any secret that could forge one. In the settings file of `--config-file` add the block `identity`: `jwks_url` (the address of that key set; only `https`, or `http` to a loopback address; no credentials in it), `accept_hs256` (default `true`: HS256 tokens signed with the `--identity-key-file` key are still accepted, so nobody is signed out while the SERVER changes over; set it to `false` when the transition is over and the hub then accepts only EdDSA), `jwks_ttl_s` (how long the key set is kept, default 300), `jwks_min_refetch_s` (the least time between two reads of the key set, default 30) and `jwks_timeout_s` (default 5). The algorithm is fixed by this configuration and never by the token: `alg: none`, HS384, RS*, ES* and an HS256 token signed with a public key are refused, and so is an EdDSA token without a `kid`, with a `kid` the SERVER does not publish, without `exp`, expired, or with an `nbf` or an `iat` in the future (5 seconds of clock difference are tolerated for `iat`). A key is used only if its `kid` is the RFC 7638 thumbprint of the key itself. A token with an unknown `kid` makes the hub read the key set again (a rotation), but never more often than `jwks_min_refetch_s`, failed reads included, so invented `kid`s cannot overload the SERVER; during a rotation both keys are published and both work. If the key set is not in the cache and the SERVER does not answer, nobody is identified and the request is refused (`401`); the cache is not served past its time to live. Redirects are not followed and the TLS certificate is verified. The claims are the same as with HS256 (`username`, `role`, `exp`; `id` and `tokenVersion` are not used by the hub). Without the block `identity`, nothing changes.
- **Switch for a caller with no identity (OFF by default).** `--allow-loopback-no-identity`, or `"allowLoopbackNoIdentity": true` in the file of `--config-file` (a JSON object with `identityKeyFile`, `allowLoopbackNoIdentity` and the block `identity`; the command line wins), answers a caller that connects from this machine without a token (role `loopback`, recorded as such). It is accepted only with a loopback `--host`; any other address stops the start. A token that is sent is still verified when a key is also given.
- **Reading and changing that switch while the gate runs.** `GET /gate/settings` (any signed-in role) answers `allowLoopbackNoIdentity`, `loopbackSwitchAllowed` (the service listens on a loopback address), `verifiesTokens` and `persisted` (a `--config-file` is in use). `POST /gate/settings` with `{"allowLoopbackNoIdentity": true|false, "confirm": true}` needs an administrator with a **signed token** (`403` for another role, and `403` with `code: TOKEN_REQUIRED` for the caller with no identity, which can therefore never switch itself on or off); turning the switch on needs `confirm: true` (`400`, `code: CONFIRMATION_REQUIRED`) and a loopback address, turning it off needs a key that verifies tokens (`409`, `code: SETTING_REFUSED`, otherwise). The change is written to the `--config-file` first (only that key; if the file cannot be written nothing changes) and then recorded in the audit chain (`kind: settings_change`, `from`, `to`, `caller`); a change that cannot be recorded is undone (`503`). The command line still wins at the next start: a gate started with `--allow-loopback-no-identity` is on again after a restart whatever the file says. HYDRA-UMC-SERVER relays this route (`GET` and `POST /api/connector-hub/gate/settings`) so that STUDIO can show and change it.
- `POST /gate/evaluate` takes `adapterId`, `capability`, `jobId`, `source`, and optionally `idempotencyKey`, `machineState`, `observedMachineState`, `allowUnobserved`, `cellState` (used only without a cell-state provider), `grantedPermissions`, `cellMode`, `humanConfirmed`, `satisfiedSafetyGates`, `parameters` and `evidence`. It answers `200` with `allowed`, `reason`, `evidenceErrors`, `observed`, `cellStateSource` (`observed` or `attested`) and `auditSeq`; a denial is also a `200`. A decision that could not be recorded is a `503` with `allowed: false`.
- `GET /gate/audit` gives the head of the chain (keep it elsewhere to notice a cut tail), the counts and the newest decisions. `GET /health` is open.
- Every line of the audit file has `seq`, `at`, the decision, `prevHash` and `hash`, and `seal` with a key. Opening a file that does not verify stops the start.
