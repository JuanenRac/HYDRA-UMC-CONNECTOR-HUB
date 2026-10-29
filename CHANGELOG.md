# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- **README in the universal layout:** the README and its seven translations follow the layout that the four families share (22 sections in a fixed order), with an architecture picture and a repository-structure picture drawn from `docs/architecture.json` and `docs/structure.json`; the CI validator checks both pictures and the file tree. Where the repository has a service or an MQTT transport, the README now says how to start it and which environment variables it reads.

- **The layout of the README is checked in the CI:** the validator runs `tools/universal_readme_check.py` and lists, as a warning, what differs from the universal layout of the README.
- The README in the eight languages says that the four planned deliveries are shipped in six parts, as the list that follows shows.

## [0.1.5] - Building no longer changes the version; raising it is the explicit `bu

- Building no longer changes the version; raising it is the explicit `bump` command (`python tools/hydra_project_tool.py bump`). The build scripts only report the version they built, and CI fails if a build script runs a bump.
- The build and run scripts use the Python of the `.venv` directly instead of an activate script, and create the venv with the `py` launcher when there is one; CI fails if a script activates a venv.
- `docs/MATURITY_CRITERIA.md` now agrees with the manifest and the READMEs: the three exit criteria are marked as met, each pointing to the tests that verify it, and the project is labelled `functional` (the document still called it `scaffolding`).
- **Sealed, hash-chained certification records** (`ledger.py`, opt-in): `certify --key-file FILE` writes each record with its sequence, the sha256 of the previous file and an HMAC-SHA256 seal under the operator's key, plus a sealed `.chain-head.json`; the new `verify-certifications --dir D --key-file FILE [--strict]` fails on an edited record, a record removed from the middle or the start or the end, a forked chain, a rewritten head, a wrong key, and, with `--strict`, a record outside the chain. One writer at a time (a lock file that goes stale). Without a key nothing changes and the sealed files still load with `certifications`. It is an HMAC, not a signature: whoever holds the key can rewrite the chain. 18 new tests (188 in all). Not used against a real certification folder yet.
- The banner follows the animated style of the ecosystem banners, with the name, the kind and the technologies of the project.
- Added `tools/hydra_project_tool.py`: the same `validate`, `test`, `version`, `status` and `bump` commands in every repository. The checks run with `HYDRA_UMC_CI=1` and fail if the version changes; only `bump` changes it.
- The SDK is now fetched at a release tag instead of the main branch, so a change of the SDK cannot break this repository by itself.
- The SDK is pinned to 0.3.6, whose gate refuses a write when the caller did not read the state of the machine. A write capability now needs `observed_machine_state` (`--observed-machine-state` on the CLI); the claimed `machine_state` alone is refused. A caller that really cannot read the machine opts in explicitly with `allow_unobserved` (`--allow-unobserved`), and every answer now carries `observed` (false for that opt-in). The documentation and the tests cover the refusal, the opt-in and the observed case.

## [0.1.4]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.
- The licence is written as GPL-3.0-or-later in every header and in the package metadata.

## [0.1.3] - A gate that says what it is worth, robust against hostile files, four-component SDK versions

- **The capability gate is documented as advisory, and can use an observation.** Every fact it evaluates (permissions, human confirmation, safety gates, cell mode, cell and machine state) is attested by the caller, so a decision is only as good as the caller. The README example that showed a write capability being allowed with no attestation at all is replaced by one that is true, `docs/CAPABILITY_GATE.md` says what a decision is worth, and a caller that can read the machine passes `observed_machine_state` (`--observed-machine-state`), which the SDK gate uses instead of the claim.
- A capability call dated more than 5 seconds in the future is denied: its negative age passed every freshness check.
- **SDK versions of four components** (`0.8.0.0`) are understood in `sdkCompatibility` and in the installed version; before this a write or abort capability would have been denied for every adapter once the SDK moved to them. The optional SDK is installed from its `v0.3.2` tag instead of from `main`.
- **One bad file no longer breaks the catalog:** a document nested thousands of levels deep raised `RecursionError` inside the scan and made the catalog server drop the connection of `/health`, `/catalog` and `/catalog/<id>`; it is listed under `invalidFiles` now, and any other unexpected failure on one file is reported for that file only. A certification record that is not an object, or has no valid `certifiedAt`, is skipped instead of making `certifications` crash.
- The catalog publishes the manifest's file name as `sourcePath` instead of an absolute path on the server; a query string or a trailing slash no longer makes `/catalog` a `404`; `If-None-Match` accepts a list of tags and weak tags; `serve-catalog --ecosystem-root` lists only the adapters whose `ownerProject` is confirmed (the others appear under `unverifiedOwners`), as `catalog --ecosystem-root` already did.
- `authenticationRef` is stricter: after `env:` only the name of an environment variable (upper case, digits, `_`) is accepted, so a literal secret pasted after the prefix is refused, and the other prefixes accept only identifier or store-path characters. JSON Schema `integer` accepts `1.0`. The published schema carries the same patterns.
- **The `industrial-opcua` fixture describes the OPC-UA server** (anonymous read of the address space, health check on the `ServerStatus` node by NodeId) instead of an OPC-UA client that project does not implement.
- The CLI reports an unreadable evidence file or an unwritable certification directory as an `ERROR` instead of a traceback; unused imports were removed; the CI step that runs the tests has its own name. 165 tests (34 are skipped when the optional SDK is not installed).

## [0.1.2] - Broken registry files and idle connections

- A manifest file in the registry that is not valid UTF-8 no longer takes the whole catalog down: it is listed under `invalidFiles` (the `UnicodeDecodeError` was not caught, so one such file made every scan, `/health` and `/catalog` fail), and a file over 1 MB is listed as invalid without being read.
- The catalog server drops a connection that stays idle for 15 seconds instead of holding a thread forever, and answers `503` with a JSON error (instead of dropping the connection with a traceback) when the registry directory disappears under it.
- Added 4 tests for all of the above (143 in total, 31 of them skipped when the optional SDK is not installed); corrected the README test count and sample version line in every language and documented the behaviour.

## [0.1.1] - SDK-gate tests run in CI, Portuguese README

- **CI now runs the SDK-gate tests:** the workflow installed only `.[dev]`, so the 31 tests of the safety-gate integration (`tests/test_sdk_gate.py`, which call the real `HYDRA-UMC-SDK` `evaluate_job()`) were skipped on every CI run and the gate was never exercised there. It now installs `.[dev,sdk]` and prints the skip reasons; with the SDK present the whole suite passes (139 tests, 108 without the optional extra).
- **Docs:** the test count in the README was out of date (113) and now states 139 with the `[sdk]` extra and how many skip without it, and a README in Portuguese (`README_por.md`) joins the other translations.

## [0.1.0] - Published JSON Schema for the adapter manifest

- **`schemas/adapter-manifest.v1.schema.json`:** the adapter manifest contract as a JSON
  Schema document (required fields, enumerations, patterns, the write/abort capability
  requirements). `schema.py` remains the reference validator; six new tests compare the
  published file against it and against every valid and invalid fixture, so the two cannot
  drift apart unnoticed. Documented in `docs/ADAPTER_MANIFEST.md`.

## [0.0.9] - the catalog gained a real, deterministic snapshot version and a real conditional-GET

`build_catalog()` itself stays a fresh per-call directory scan (Delivery
2's own deliberate design - a registry directory is real, live
filesystem state, never cached), but nothing let a caller cheaply tell
"has this catalog changed since I last saw it" without diffing the
whole body itself. New `registry.catalog_snapshot_version()`: a real
SHA-256 over the catalog's own canonical content - deterministic (two
scans of an unchanged registry always agree), changes if and only if a
real adapter is added/removed/edited or a file starts/stops failing
validation.

- `catalog` (CLI) now always includes `snapshotVersion` in its output.
- `GET /catalog` (`serve-catalog`) now sends it as a real `ETag` header
  and honors `If-None-Match`: a matching value gets a real, honest `304
  Not Modified` (empty body) instead of the full catalog - the real
  "transactional reload" half, since every response is still one
  complete, freshly-rescanned comparison, never a partial/torn one.

7 new tests (133 passed).

## [0.0.8] - ownerProject was only ever checked as a non-empty string, never verified against a real project

Two real, independent layers, neither one alone sufficient:

- **Shape check (`schema.py`).** New `PROJECT_NAME_PATTERN` (mirrors
  HYDRA-UMC-SDK's own) rejects an `ownerProject` that does not even look
  like a real `HYDRA-UMC-*`/`URTC-*` project name - a typo or a made-up
  value used to pass `validate_adapter_manifest()` just as cleanly as a
  real one.
- **Existence check (`registry.py`'s new `verify_catalog_owners()`).**
  For a real batch of catalog entries against a real ecosystem root,
  confirms the claimed owner project's own `hydra-umc.project.json`
  actually exists AND self-identifies with that same name - the same
  self-consistency check HYDRA-UMC-LOCAL-TECHNICIAN's own
  `resolve_project_manifest_path()` already applies, ported here. Wired
  into the real CLI as a new, optional `catalog --ecosystem-root <dir>`
  flag - omitted, nothing changes (only the shape check runs, same as
  before); given, every failure is reported under a new
  `unverifiedOwners` key and fails the command's own exit code.

7 new tests (126 passed).

## [0.0.7] - textual booleans, unhashable schema types, non-finite freshness

- `CapabilityCallRequest.human_confirmed` was a plain `bool`
  type hint with no runtime check. The literal string `"false"` is
  truthy in Python, so a caller wiring this dataclass up from
  loosely-typed input (a future HTTP/JSON layer, a query string) that
  passed textual `"false"` instead of a real bool would have it treated
  as an actual human confirmation. Fixed: `__post_init__` now rejects any
  `human_confirmed` that is not a real `bool`.
- `_validate_schema_shape()`'s own `schema_type not in
  _JSON_SCHEMA_TYPE_CHECKS` hashes `schema_type` to look it up - a
  malformed `"type"` that is itself unhashable (a list or object) raised
  `TypeError`, taking down this validator instead of returning it as a
  real problem found, contradicting this function's own "never raises"
  docstring. Fixed: guarded with `isinstance(schema_type, str)` first,
  same pattern `validate_against_json_schema_subset()` already used for
  the identical lookup.
- `_policy_denials()`'s request-freshness check compared
  `age > max_age` directly. NaN compares `False` against everything, so
  a non-finite `requested_at` (or `now`) silently passed as "not stale"
  instead of being rejected - defeating the fail-closed guarantee the
  "expired gate" scenario below exists for. Fixed: a non-finite age is now
  rejected explicitly before the threshold comparison runs.

## [0.0.6] - Real "version incompatible" and "expired gate" checks

2 of the 5 real scenarios this project's own certification flow names
(malicious ID, incompatible version, duplicate certificate, missing
confirmation, and an expired gate) were found not implemented at
all - not merely untested:

- **Version incompatible**: `sdkCompatibility` (required since Delivery
  1, a real `>=X.Y.Z` constraint every fixture already declares) was
  only ever checked for being a non-empty string - its actual meaning
  against the REAL installed `hydra_umc_sdk.__version__` was never
  evaluated anywhere. New `schema.check_sdk_compatibility()` (pure
  logic, no SDK import needed) is now checked in
  `evaluate_capability_call()` right where the optional dependency
  already becomes available, before any `BridgeJob` is ever constructed.
- **Expired gate**: a write/abort request built long before
  it is actually evaluated is now denied - the cell/machine state it
  attests to may no longer hold by then. New `CapabilityCallRequest.
  requested_at` (defaults to "now", so every existing caller keeps
  behaving exactly as before) checked against a real, optional
  per-manifest `maxRequestAgeSeconds` (a conservative 30s ecosystem
  default applies when a manifest doesn't declare one).

Both checks are read-exempt, same as every other policy check this
module already enforces - a read capability still never
touches the optional SDK dependency at all. `evaluate_capability_call()`
gains an optional `now=` parameter for real, deterministic freshness
tests instead of a flaky `sleep()`.

Verified: full pytest suite (113/113, 21 new), `tools/ci_validate.py`
PASS (incl. a 7-language README version-string fix this surfaced).

## [0.0.5] - Docs only: real client integration has started

No code changed here - HYDRA-UMC-SERVER is now a real consumer of this
project's own `serve-catalog` (`GET /api/adapters`,
`GET /api/adapters/:adapterId`), proven end to end against a real spawned
`serve-catalog` process, this project's own real `fixtures/`, and a real
Server instance (see HYDRA-UMC-SERVER's own
`tools/verify_connector_hub_relay_contract.mjs`) - never a mock on either
side. Also built as a real wheel and installed into a venv outside this
project's own checkout, then driven from there (`catalog`/`serve-catalog`
against the real `fixtures/`), confirming the packaging itself works, not
just an editable install. README's own ROADMAP (and its 6 translations)
updated to drop the stale "No real client integration yet" line -
Studio/Suite/Updater calling `gate` themselves is still real, separate,
future work.

## [0.0.4] - Real regressions found by a second review pass

A second review pass found 4 more real
issues, each reproduced first against a real fixture/fixture-derived
request (no network/hardware), then fixed with new regression tests:

- **The capability gate ignored every permission/
  confirmation/gate a write or abort capability itself declared.**
  `evaluate_capability_call()` forwarded straight to HYDRA-UMC-SDK's own
  generic READY/IDLE motion gate - `cnc-grbl.json`'s own `sendControlByte`
  (`requiredPermission=cnc.control.send`, `requiredCellState=supervised`,
  `requiresHumanConfirmation=true`, plus the manifest's own
  `requiredSafetyGates`) came back `allowed=true` with a READY/IDLE cell
  and ZERO evidence any of those four requirements were actually met.
  `CapabilityCallRequest` now carries the caller's own real attestation
  (`granted_permissions`/`cell_mode`/`human_confirmed`/
  `satisfied_safety_gates`); every one of the four is checked, fail-closed,
  BEFORE the optional SDK dependency is even imported - dropping any
  single one denies the call. See `docs/CAPABILITY_GATE.md` and the new
  `gate` CLI flags (`--permission`/`--cell-mode`/`--human-confirmed`/
  `--safety-gate`).
- **`adapterId` could escape the certification directory.**
  `validate_adapter_manifest()` accepted `adapterId: "../escaped"`, and
  `save_certification_record()` joined it straight into a real file path
  with no containment check - a real file could land outside the
  operator-chosen certs directory. `adapterId` is now restricted to a
  safe charset (letters/digits/`-`/`_`, matching every one of this
  repo's own 10 real fixtures), and `save_certification_record()` ALSO
  independently verifies the resolved path stays inside the target
  directory - belt-and-suspenders, since a `CertificationRecord` built
  directly (`from_dict()` on untrusted JSON) never goes through the
  manifest validator at all.
- **The certification store was not actually append-only.**
  Saving a second, DIFFERENT `CertificationRecord` under the same
  `certification_id` silently overwrote the first, despite
  `docs/CERTIFICATION.md` and this module's own docstring promising
  "never overwritten". Records are now created with real, atomic
  `O_CREAT|O_EXCL` semantics (`open(path, "x")`); a second write of the
  byte-for-byte SAME record is a harmless idempotent no-op, a different
  one under the same id is refused outright.
- **The evidence-schema validator accepted wrong types and
  could raise.** `{"type": "number"}` accepted a real Python `bool`
  (`isinstance(True, int)` is true); a `pattern` that is not a valid
  regex raised `re.error`; a non-string `required` entry raised
  `TypeError` (`key not in instance` on an unhashable key) - despite the
  function's own docstring promising "never raises". Both are now
  handled as real, reported errors, never an exception; a manifest whose
  own `endpointSchema`/`evidenceSchema` is malformed in one of these
  ways is now rejected by `validate_adapter_manifest()` itself, before
  it can ever reach a real evidence check.

## [0.0.3] - Real regressions found by independent revalidation

A review pass reproduced 4 real
issues against this project's own v0.0.1/v0.0.2 code (each with a real
fixture/probe, no network/hardware involved). All 4 are fixed here,
each with a new regression test:

- **A `write`/`abort` capability's `risk`/`requiredPermission`/
  `requiredCellState` only checked presence, not real content.**
  `"risk": []`, `"requiredPermission": {}` or `"requiredCellState": "
  "` all used to pass with `errors=[]` - none of them equal `None`/`""`,
  the only two values the old check rejected. Each of the three must
  now be a real, non-empty string.
- **`validate`'s CLI crashed on a well-formed JSON document that is not
  an object.** A bare `[]`/`123`/`"text"` top-level document produces a
  real, non-empty `errors` list from `validate_adapter_manifest()`, but
  the CLI then called `data.get('adapterId')` unconditionally - a real
  `AttributeError` on anything that isn't a dict. Now only accesses
  `.get()` when `data` actually is one.
- **`authenticationRef` accepted a real prefix with nothing after it,
  and two capabilities could share the same name.** `"env:"` alone
  cannot be resolved to any real credential location; two capabilities
  named the same thing cannot be unambiguously selected by a future
  catalog/gate caller. Both are now real, rejected errors.
- **Documentation accuracy:** the adapter-manifest contract has 14
  top-level fields, not 13 (fixed in `schema.py`'s own docstring and
  all 7 README languages); the `build-test.sh` claim of "runs the same
  checks as `build.sh`... the command this project's own CI actually
  runs" was true for the compile step but false for the test suite -
  `build-test.sh` only ever compiles, it never runs `pytest`; CI runs
  `pytest` as its own, separate, later step. Wording corrected in all 7
  languages. The `ownerProject` test now checks each fixture's own
  exact, fixed real owner (not merely a `HYDRA-UMC-` prefix).
- 7 new regression tests (65 total), each reproducing an explicit
  exact scenario before the fix and passing after it.

## [0.0.2] - Deliveries 2-4: catalog, SDK safety gate, certification records

- **`registry.py` + `catalog` / `serve-catalog` (Delivery 2)** - scans a
  real directory of adapter manifests (non-recursive, so a nested
  `fixtures/invalid/` never joins a real catalog), keeps only the ones
  that pass `schema.py`'s own structural validator, and builds a stable,
  `adapterId`-sorted summary catalog. `serve-catalog` exposes it over a
  real, GET-only `http.server` (`/catalog`, `/catalog/<adapterId>`,
  `/health`) - there is no `do_POST`/`do_PUT` anywhere in the module, so
  any write attempt gets a real, honest 501, not a silently-unprotected
  route. Two duplicate files declaring the same `adapterId` reject the
  second one rather than letting either shadow the other.
- **`sdk_gate.py` + `gate` (Delivery 3, [P0])** - real integration with
  HYDRA-UMC-SDK's own `bridge_contract.evaluate_job()`, never a second,
  competing safety-gate implementation. A `read` capability is always
  allowed without touching the SDK at all; a `write`/`abort` capability
  builds a real `BridgeJob` (abort maps to `JobPhase.ABORT`, write to a
  documented single `JobPhase.PROCESS` stand-in) and is gated by the
  SDK's own real `evaluate_job()` - denied whenever the cell is not
  READY or the machine is not IDLE, except abort, which is always
  forwarded. An optional evidence payload is checked against the
  adapter's own `evidenceSchema` via a new small, dependency-free JSON
  Schema subset validator (`validate_against_json_schema_subset()` in
  `schema.py`) and folds into the final decision. `hydra-umc-sdk` ships
  as a new, optional `[sdk]` extra (git dependency, same pattern every
  bridge project already uses) - the core stays dependency-free.
- **`certification.py` + `certify` / `certifications` (Delivery 4,
  [P1][HARDWARE])** - the real, honest software half of "certify
  adapters one at a time; no universal global label, every profile keeps
  its own evidence": a real, append-only, one-file-per-record
  certification log, refusing to record a certification unless the
  manifest is structurally valid AND the supplied evidence actually
  matches that adapter's own `evidenceSchema`. This module explicitly
  does NOT talk to a real serial port/OPC-UA endpoint/MQTT broker to
  independently confirm the evidence came from the named machine - that
  automated hardware verification genuinely needs the real hardware this
  delivery is tagged `[HARDWARE]` for, which this development machine
  does not have; producing honest evidence stays the human certifier's
  own responsibility.
- 36 new tests (58 total) - `registry.py`/`catalog_server.py` against
  real fixture files and a real `http.server` on a real ephemeral port;
  `sdk_gate.py` against the real, installed `hydra-umc-sdk` package
  (skipped, never faked, if it is not installed); `certification.py`
  against a real temp directory.

## [0.0.1] - Delivery 1: schema + CLI validate + fixtures

First real scaffolding version - Delivery 1 of the 4-delivery plan from
a recommended-new-project proposal made on code review
("Esquema JSON, CLI validate y diez fixtures (sin red,
sin hardware)"). This version touches no network, no hardware, and no
real machine - it only validates the structure of an adapter-manifest
file already on disk.

- **`schema.py`** - a real, hand-written structural validator (no
  `jsonschema` dependency) for an explicit "CONTRATO MINIMO
  DE ADAPTADOR" - all 13 top-level fields, plus the capability shape
  (`name`/`mode`/`risk`/`requiredPermission`/`requiredCellState`/
  `requiresHumanConfirmation`/`timeoutMs`). Enforces the proposal's own
  non-negotiable rule as a real, tested check: a `write`/`abort`
  capability is rejected unless it ALSO declares risk, requiredPermission,
  requiredCellState, requiresHumanConfirmation and timeoutMs.
  `authenticationRef` must be a reference (`env:`/`secret-store:`/
  `vault:`/`none:`) - a literal secret value is rejected, never accepted
  and silently trusted.
- **`cli.py`** - `hydra-umc-connector-hub validate <file> [<file> ...]`.
  Reports every real error for every file given, not just the first one
  found; a distinct message for "file could not be parsed as JSON" vs.
  "file parsed but is structurally invalid".
- **Ten real fixtures** under `fixtures/`, one per already-existing real
  bridge/protocol project in this ecosystem (`industrial-opcua` ->
  HYDRA-UMC-OPCUA-SERVER, `industrial-mqtt` -> HYDRA-UMC-MQTT-BROKER,
  `manufacturing-mtconnect` -> HYDRA-UMC-MTCONNECT-ADAPTER, `cnc-grbl` ->
  HYDRA-UMC-BRIDGE-CNC, `laser-safety` -> HYDRA-UMC-BRIDGE-LASER,
  `pnp-openpnp` -> HYDRA-UMC-BRIDGE-OPENPNP, `printer-moonraker` ->
  HYDRA-UMC-BRIDGE-PRINTER3D, `robotics-ros2` -> HYDRA-UMC-BRIDGE-ROS2,
  `mobile-vda5050` -> HYDRA-UMC-BRIDGE-AMR, `uav-mavlink` ->
  HYDRA-UMC-BRIDGE-UAV) plus five real invalid fixtures under
  `fixtures/invalid/`, each constructed to demonstrate one specific real
  rejection reason.
- 22 real tests across `schema.py` and `cli.py` - every real fixture
  (valid and invalid) is exercised against the actual validator and the
  actual CLI, never a synthetic stand-in.
