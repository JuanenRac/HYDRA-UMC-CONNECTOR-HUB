# Changelog: HYDRA-UMC-CONNECTOR-HUB 🔌

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## Unreleased

(nothing yet)

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

## [0.0.4] - Real regressions found by a second, independent revalidation audit

A second independent ecosystem-wide revalidation audit found 4 more real
issues, each reproduced first against a real fixture/fixture-derived
request (no network/hardware), then fixed with new regression tests:

- **V07-006 (P1): the capability gate ignored every permission/
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
- **V07-007 (P1): `adapterId` could escape the certification directory.**
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
- **V07-008 (P2): the certification store was not actually append-only.**
  Saving a second, DIFFERENT `CertificationRecord` under the same
  `certification_id` silently overwrote the first, despite
  `docs/CERTIFICATION.md` and this module's own docstring promising
  "never overwritten". Records are now created with real, atomic
  `O_CREAT|O_EXCL` semantics (`open(path, "x")`); a second write of the
  byte-for-byte SAME record is a harmless idempotent no-op, a different
  one under the same id is refused outright.
- **V07-009 (P2): the evidence-schema validator accepted wrong types and
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

An independent ecosystem-wide revalidation audit reproduced 4 real
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
- 7 new regression tests (65 total), each reproducing the audit's own
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
the ecosystem-wide software-improvements audit's own recommended-new-
project proposal ("Esquema JSON, CLI validate y diez fixtures (sin red,
sin hardware)"). This version touches no network, no hardware, and no
real machine - it only validates the structure of an adapter-manifest
file already on disk.

- **`schema.py`** - a real, hand-written structural validator (no
  `jsonschema` dependency) for the audit proposal's own "CONTRATO MINIMO
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
