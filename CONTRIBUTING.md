# Contributing to HYDRA-UMC-CONNECTOR-HUB 🔌

We welcome contributions to the adapter-manifest registry and validator
of the HYDRA-UMC platform.

## Technology Stack

- **Language**: Python 3.11+.
- **Dependencies**: stdlib only, deliberately - `schema.py` is a
  hand-written structural validator, not a wrapper over the third-party
  `jsonschema` package, so every real error message can name the exact
  adapter/field/capability at fault. A dependency is added only once a
  specific later delivery's own code genuinely needs it, never
  speculatively.

## Guidelines

1. **A `write`/`abort` capability is never valid without its full real
   safety context.** `_WRITE_CAPABILITY_REQUIRED_FIELDS` in `schema.py`
   is an explicit, non-negotiable rule
   ("las acciones write nunca son seleccionables si falta una de esas
   condiciones") made real and tested. Do not relax this check, and do
   not add a new capability mode without deciding - explicitly, in this
   same file - whether it needs the same treatment.
2. **`authenticationRef` is a reference, never a secret.** Adding a new
   real reference scheme belongs in `AUTHENTICATION_REF_PREFIXES` - never
   loosen the check to accept an arbitrary string, which would silently
   let a literal credential back into a tracked manifest file.
3. **Every new fixture under `fixtures/` must name a REAL owner
   project** (`ownerProject` pointing at an actual HYDRA-UMC/URTC
   repository that already exists) - never an invented or aspirational
   one. A fixture for a protocol this ecosystem doesn't have a real
   bridge for yet belongs in a draft/PR discussion first, not committed
   as if it already existed.
4. **`validate_adapter_manifest()` collects every real error, it never
   stops at the first one.** A new check should `errors.append(...)` and
   continue, matching the existing pattern - a contributor fixing a
   manifest should see every real problem in one run, not one at a time.
5. **This delivery never contacts a real machine.** Do not add a socket,
   HTTP client, or serial-port open to `schema.py` or `cli.py` - Delivery
   1's own scope is structural validation of a file already on disk;
   real connectivity is explicitly later, separate work (see the
   README's own Roadmap section).
