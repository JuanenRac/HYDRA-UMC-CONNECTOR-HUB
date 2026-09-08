<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-CONNECTOR-HUB banner" width="100%">
</p>

# 🔌 HYDRA-UMC-CONNECTOR-HUB

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🧩 A Declarative Registry and Validator for External-Machine Adapters

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only core">
  <img src="https://img.shields.io/badge/Deliveries-4%20of%204-367BF5.svg" alt="Deliveries 4 of 4">
</p>

> **Status: v0.0.6, scaffolding - Deliveries 1-4 of 4 (schema/CLI/
> fixtures, read-only catalog, SDK safety gate, certification records).**
> `catalog`/`serve-catalog` are real and GET-only (no network write path
> exists anywhere in this project); `gate` calls straight into
> HYDRA-UMC-SDK's own real `evaluate_job()`, never a second
> implementation of that gate (see
> [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)); `certify` records
> a real, human-attested evidence payload but explicitly does NOT
> independently verify it against real hardware - see
> [docs/CERTIFICATION.md](docs/CERTIFICATION.md) for exactly why that
> stays out of scope without a physical machine in hand. See
> [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for the exact command
> surface that exists today.

---

## 1. 🛠️ TECHNICAL OVERVIEW

Today, choosing and configuring which bridge a given cell/machine uses is
spread across READMEs, `.env` files and ad-hoc scripts across many real
bridge repositories. HYDRA-UMC-CONNECTOR-HUB is meant to become the
single place that answers, for any real external machine, three
questions: **what protocol does it speak, what can it actually do
(read/write/abort, at what risk), and which existing real project of
this ecosystem already implements that?**

This version ships all four deliveries of that plan:

1. **A real, fixed contract** ([docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)) -
   the ecosystem-wide software-improvements audit's own "CONTRATO MINIMO
   DE ADAPTADOR", with one non-negotiable rule enforced in code: a
   `write`/`abort` capability is rejected unless it also declares its
   own risk, required permission, required cell state, human-confirmation
   requirement, and timeout.
2. **A real CLI validator** (`hydra-umc-connector-hub validate`) - a
   hand-written structural check (no `jsonschema` dependency), so every
   real error names the exact adapter/field/capability at fault.
3. **Ten real fixtures**, one per already-existing real bridge/protocol
   project in this ecosystem - proof that the contract is not
   theoretical, and a starting template for a new adapter manifest.
4. **A real read-only catalog** (`catalog`/`serve-catalog`) -
   discovers every structurally-valid manifest in a directory and, for
   `serve-catalog`, exposes it over a real GET-only `http.server` (no
   write route exists anywhere in this project).
5. **A real HYDRA-UMC-SDK safety-gate integration** (`gate`) - a
   `write`/`abort` capability call is gated by the SDK's own real
   `evaluate_job()`, never a second implementation of that logic; see
   [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md).
6. **Real certification records** (`certify`/`certifications`) - a
   human-attested, append-only log checked against an adapter's own
   `evidenceSchema`; see [docs/CERTIFICATION.md](docs/CERTIFICATION.md)
   for why independently verifying evidence against real hardware stays
   explicitly out of scope here.

```
$ hydra-umc-connector-hub validate fixtures/industrial-opcua.json
VALID fixtures/industrial-opcua.json adapterId='industrial-opcua' ownerProject='HYDRA-UMC-OPCUA-SERVER'

$ hydra-umc-connector-hub catalog --registry-dir fixtures | head -c 200
{"adapters": [{"adapterId": "cnc-grbl", "protocol": "grbl-serial", ...

$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json --capability sendControlByte \
    --job-id j1 --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
{"allowed": true, "reason": "cell and external machine are ready", "evidenceErrors": []}

$ hydra-umc-connector-hub certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Juan Enrique" --evidence-file real-status.json --out-dir certifications/
CERTIFIED adapterId='cnc-grbl' certificationId='...' -> certifications/cnc-grbl__....json
```

There is no default/bare invocation and no GUI anywhere in this project
- see [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for the full, real
command surface.

## 2. 🧱 ARCHITECTURE & DESIGN DECISIONS

- **A hand-written validator, not `jsonschema`.** Delivery 1's own
  contract is small enough (14 top-level fields, one nested capability
  shape) that a plain Python function collecting real, specific error
  strings is both simpler than a generic JSON-Schema validator AND
  produces clearer output - every message names the exact field/index at
  fault, not a generic schema-path.
- **The write/abort safety rule is enforced in code, not documentation.**
  `_WRITE_CAPABILITY_REQUIRED_FIELDS` in `schema.py` is the audit
  proposal's own explicit sentence turned into a real, tested check - a
  manifest author cannot forget it, because the validator rejects a
  capability that does.
- **`authenticationRef` is checked as a reference, never trusted as
  free text.** A closed set of real prefixes (`env:`, `secret-store:`,
  `vault:`, `none:`) - deliberately not a "looks secret-shaped"
  heuristic (see HYDRA-UMC-OPS-AGENT's own `log_redaction.py` for why a
  heuristic is the wrong tool for this exact problem too).
- **Every error is collected, never just the first one.**
  `validate_adapter_manifest()` keeps checking after finding a problem -
  a person fixing a manifest sees every real issue in one run.
- **The catalog is real and read-only, on purpose.** `registry.py` scans
  a directory non-recursively (so a nested `fixtures/invalid/` never
  joins a real catalog), drops - but still reports - anything that fails
  `validate_adapter_manifest()`, and rejects two files that declare the
  same `adapterId`. `catalog_server.py` has no `do_POST`/`do_PUT`
  anywhere - a write attempt gets `BaseHTTPRequestHandler`'s own honest
  `501`, never a route this project forgot to protect.
- **The safety gate reuses HYDRA-UMC-SDK's own real logic, never a
  second implementation of it.** `sdk_gate.py`'s `evaluate_capability_call()`
  calls straight into `hydra_umc_sdk.bridge_contract.evaluate_job()` for
  every `write`/`abort` capability - a `read` capability never touches
  the SDK at all, since `evaluate_job()` is a motion/write gate, not a
  read gate. See [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md) for
  the one deliberate, named simplification this integration makes
  (a single stand-in `JobPhase` for any non-abort write).
- **A certification record is honest about what it can and cannot
  prove.** `certification.py` refuses to save a certification whose
  evidence does not match the adapter's own `evidenceSchema`, but it
  never claims to independently verify that evidence came from real
  hardware - there is no code path anywhere in this project that opens a
  real serial port/OPC-UA session/MQTT connection to check that. See
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **The ten fixtures name real owner projects, never invented ones.**
  Every `ownerProject` in `fixtures/*.json` is an actual repository in
  this ecosystem (see the Related Projects section) - this is a real
  registry template, not a speculative one.
- **stdlib only for the core.** `validate`/`catalog`/`serve-catalog`/
  `certify`/`certifications` need zero dependencies - `json`, plain
  Python structural checks, and `http.server`. Only `gate` on a
  `write`/`abort` capability needs the optional `[sdk]` extra.

## 📂 DIRECTORY STRUCTURE

```
HYDRA-UMC-CONNECTOR-HUB/
├── src/hydra_umc_connector_hub/
│   ├── schema.py            # The real adapter-manifest contract + structural validator + JSON-Schema-subset checker
│   ├── registry.py          # Delivery 2: scans a directory into a real, stable, sorted catalog
│   ├── catalog_server.py    # Delivery 2: real GET-only http.server exposing the catalog
│   ├── sdk_gate.py          # Delivery 3: real HYDRA-UMC-SDK evaluate_job() integration
│   ├── certification.py     # Delivery 4: real, append-only, human-attested certification log
│   └── cli.py               # validate/catalog/serve-catalog/gate/certify/certifications entry point
├── fixtures/                # Ten real, valid adapter manifests (one per existing bridge)
│   └── invalid/             # Five real invalid manifests, each demonstrating one rejection reason
├── tests/                   # Real tests: fixtures, a real http.server on an ephemeral port, the real installed hydra-umc-sdk, and a real temp-dir certification log
├── docs/
│   ├── ADAPTER_MANIFEST.md  # The full real contract, field by field
│   ├── CAPABILITY_GATE.md   # Delivery 3's own real gate contract and its one named simplification
│   ├── CERTIFICATION.md     # Delivery 4's own real contract and its honest hardware-verification gap
│   └── CLI_REFERENCE.md     # Every subcommand, its output shapes, exit codes
├── images/                  # Media and app icons
├── tools/
│   ├── build_test.py        # Non-versioning build/compile check
│   └── ci_validate.py       # Manifest/CHANGELOG/docs validation used by CI
├── build.sh / build.bat     # venv + editable install + compile-check + tests
├── build-test.sh / .bat     # Non-mutating build validation only
├── run.sh / run.bat         # Real demo: validates the ten fixtures (no arguments), or forwards a real CLI command
├── bump_version.py          # Ecosystem-wide odometer bump (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Syncs hydra-umc.project.json's version to the native one (--sync)
```

## ⚙️ BUILD & RUN GUIDE

```bash
chmod +x build.sh   # one-time
./build.sh          # creates .venv, pip install -e ".[dev]", compile-checks + tests
./run.sh                                   # real demo: validates the ten real fixtures
./run.sh validate fixtures/industrial-opcua.json
./run.sh validate fixtures/invalid/*.json  # every one of these should report INVALID
./run.sh catalog --registry-dir fixtures
./run.sh serve-catalog --registry-dir fixtures --port 8801   # Ctrl+C to stop
pip install -e ".[sdk]"                    # only needed for `gate` on a write/abort capability
./run.sh gate fixtures/cnc-grbl.json --capability sendControlByte --job-id j1 \
    --idempotency-key i1 --source studio --cell-state READY --machine-state IDLE
./run.sh certify fixtures/cnc-grbl.json --machine-model "Genmitsu 3018-PROVer" \
    --certified-by "Your Name" --evidence-file real-status.json --out-dir certifications/
```

On Windows: `build.bat`, then `run.bat` (same demo when called with no
arguments) / any of the subcommands above. `build-test.sh`/`.bat`
performs the same non-mutating Python-syntax compile check this
project's own CI workflow performs, without touching the project
version or CHANGELOG - it does NOT run the test suite itself; CI runs
`pytest` as its own separate, later step. Run `./build.sh`/`build.bat`
(or `pytest tests/` directly) for the full local test suite.

**Troubleshooting**

- `validate` reports `INVALID` for a manifest you believe is correct:
  read every listed reason - the validator reports all of them, not just
  the first. See [docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)
  for the exact field-by-field contract.
- `validate` reports `ERROR: ... is not valid JSON`: the file itself is
  malformed JSON, distinct from a well-formed-but-invalid manifest -
  check for a missing comma/quote before checking the contract itself.
- `catalog`/`serve-catalog` exits `1` or lists a file under
  `invalidFiles`: that file failed structural validation and was left
  out of the catalog on purpose - run `validate` on it directly for the
  full list of reasons.
- `gate` fails with `ERROR: the optional 'hydra-umc-sdk' package is not
  installed`: run `pip install -e ".[sdk]"` first - only needed for a
  `write`/`abort` capability.
- `gate`/`certify` fails with `ERROR: unknown cell_state ...` or
  `... does not match evidenceSchema`: see
  [docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)/
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md) for the exact real
  values/shapes expected.

## 🚀 ROADMAP

All four deliveries of the plan named in this project's own manifest and
CHANGELOG now ship real, tested code. What is left, stated honestly:

- **Delivery 4's own hardware-verification gap stays open on purpose.**
  `certify` records a human-attested evidence payload checked against an
  adapter's own `evidenceSchema`, but nothing in this project
  independently confirms that evidence came from the named real
  machine - that needs the physical hardware itself, in a real cell,
  which this development machine does not have. See
  [docs/CERTIFICATION.md](docs/CERTIFICATION.md).
- **Real client integration: started, not finished.** HYDRA-UMC-SERVER now
  polls `serve-catalog` for real - `GET /api/adapters` and
  `GET /api/adapters/:adapterId` proxy this project's own real catalog, end
  to end (see HYDRA-UMC-SERVER's own `tools/verify_connector_hub_relay_contract.mjs`,
  which spawns this project's real `serve-catalog` against its real
  `fixtures/` and a real Server instance, never a mock). This has also been
  installed as a real wheel into a venv outside this project's own
  checkout and driven from there, confirming the packaging itself (not
  just an editable install) works. Studio/Suite/Updater calling `gate`
  themselves is still real, separate, future work.
- **A real transport between a `gate`/`certify` caller and the actual
  cell/machine state.** Today, `--cell-state`/`--machine-state` are
  supplied by the caller as already-known values - there is no code path
  here that fetches them live from HYDRA-UMC-SERVER or a safety-zone
  service itself.

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Directly Related**
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract every bridge already validates its own commands against; this hub's `gate` command (Delivery 3) calls straight into its own real `bridge_contract.evaluate_job()` for a write/abort capability, never a second implementation of that gate.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — the audit proposal's other recommended new project: operates the maintenance-incident lifecycle of this ecosystem's OWN components, while this hub discovers and validates what an EXTERNAL machine/adapter can do.
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — explicitly NOT replaced by this project: GATEWAY-INDUSTRIAL is a real protocol relay with its own command allowlist; this hub is a declarative registry/validator that sits above it and every other bridge, never a second implementation of any one protocol.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the physical robot-arm motherboard: CM5 host + dual-core STM32H745, orchestrating up to 8 tool arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.

*Core Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the real headless backend (REST/WebSocket) every control client actually talks to.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a real VDA 5050 MQTT publisher; the real `ownerProject` behind this hub's own `mobile-vda5050` fixture.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with real GRBL status/control-byte access; behind this hub's own `cnc-grbl` fixture.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a real Boston Dynamics Spot command sender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell safety coordinator reading 3 real key/enclosure/interlock GPIO safeguards; behind this hub's own `laser-safety` fixture.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place; behind this hub's own `pnp-openpnp` fixture.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands; behind this hub's own `printer-moonraker` fixture.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — safety coordinator with a real, lazily-imported rclpy ROS 2 transport; behind this hub's own `robotics-ros2` fixture.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a real MAVLink command sender; behind this hub's own `uav-mavlink` fixture.

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — real Position-Based Visual Servoing correction law, safety-gated on upstream zone state.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — real zone-breach checking and E-STOP requesting, with calibration-freshness enforcement.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — real hardware-in-the-loop safety interlock routing commands between simulation and real hardware.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — real forward kinematics and joint-limit validation over a real URDF subset.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — real procedural 2D scene generator with YOLO/COCO annotation export.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session; the real `ownerProject` behind this hub's own `industrial-opcua` fixture.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs; behind this hub's own `industrial-mqtt` fixture.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output; behind this hub's own `manufacturing-mtconnect` fixture.

*Ecosystem Operations*
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — detects, installs and updates every ecosystem checkout.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — builds a fresh, fully current CM5 image.
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with real haptic alerts and a paired-phone voice relay.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.

---

## 📚 Documentation & Community

- **[docs/ADAPTER_MANIFEST.md](docs/ADAPTER_MANIFEST.md)** — the full real contract, field by field, and why `authenticationRef` is a reference.
- **[docs/CAPABILITY_GATE.md](docs/CAPABILITY_GATE.md)** — Delivery 3's own real HYDRA-UMC-SDK safety-gate integration and its one named simplification.
- **[docs/CERTIFICATION.md](docs/CERTIFICATION.md)** — Delivery 4's own real certification-record contract and its honest hardware-verification gap.
- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — every subcommand, its output shapes, and the exit-code contract.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this project's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

GPL-3.0 (software) / CC BY-SA 4.0 (documentation) - see [LICENSE.md](LICENSE.md).
