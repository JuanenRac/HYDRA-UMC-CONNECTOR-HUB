# The Adapter-Manifest Contract

This is the real, current shape `schema.py` validates - field-for-field,
the ecosystem-wide software-improvements audit's own "CONTRATO MINIMO DE
ADAPTADOR" proposal, made concrete and enforced.

## Top-level fields

| Field | Type | Notes |
|---|---|---|
| `adapterId` | string | A stable, unique identifier for this adapter, e.g. `industrial-opcua`. |
| `schemaVersion` | string | This manifest's own version, independent of `sdkCompatibility`. |
| `protocol` | string | The real wire protocol, e.g. `opc-ua`, `mqtt`, `mavlink`. |
| `targetKinds` | array of string | What kind(s) of machine this adapter targets, e.g. `["cnc-controller"]`. Non-empty. |
| `endpointSchema` | object | A structural description of the connection config this adapter needs (host, port, credentials reference, ...). Non-empty. |
| `authenticationRef` | string | A REFERENCE to where a real credential lives - must start with `env:`, `secret-store:`, `vault:`, or `none:`. Never a literal secret - see [Why `authenticationRef` is a reference](#why-authenticationref-is-a-reference) below. |
| `capabilities` | array of object | See [Capabilities](#capabilities) below. Non-empty. |
| `requiredSafetyGates` | array of string | Ecosystem-wide safety gates this adapter's own capabilities depend on (e.g. `cell.estop.clear`). An empty list is valid - not every adapter needs one. |
| `healthCheck` | object | A structural description of how to check this adapter is reachable, e.g. `{"type": "mqtt-ping", "topic": "..."}`. Non-empty. |
| `timeoutMs` | integer > 0 | The adapter's own default timeout. |
| `idempotency` | string | One of `none`, `idempotent`, `at-least-once`, `exactly-once` - a closed, real vocabulary, not an open string. |
| `evidenceSchema` | object | A structural description of what a capability call returns as evidence. Non-empty. |
| `sdkCompatibility` | string | A version-range string against this ecosystem's own SDK contract, e.g. `">=0.1.0"`. |
| `ownerProject` | string | The real HYDRA-UMC/URTC repository that implements this adapter, e.g. `HYDRA-UMC-OPCUA-SERVER`. Never an invented or aspirational project name. |

## Capabilities

Each entry in `capabilities` describes one real, discrete action:

| Field | Required for `read` | Required for `write`/`abort` | Notes |
|---|---|---|---|
| `name` | yes | yes | A stable identifier, e.g. `readNodeValue`. |
| `mode` | yes | yes | One of `read`, `write`, `abort`. |
| `risk` | recommended | **yes** | A free-form risk label (`low`/`medium`/`high` in this repo's own fixtures). |
| `requiredPermission` | no | **yes** | The permission a caller must hold to invoke this capability. |
| `requiredCellState` | no | **yes** | The cell state this capability requires (e.g. `operational`, `supervised`, `any`). |
| `requiresHumanConfirmation` | no | **yes** (a real boolean) | Whether a human must explicitly confirm before this capability runs. |
| `timeoutMs` | no | **yes** (a positive integer) | This capability's own timeout, if different from the adapter's default. |

### The one rule this validator will never relax

> "Las acciones write nunca son seleccionables si falta una de esas
> condiciones." - the audit proposal's own words.

A `write` or `abort` capability that is missing `risk`,
`requiredPermission`, `requiredCellState`, `requiresHumanConfirmation`,
or `timeoutMs` is REJECTED by `validate_adapter_manifest()` - not
accepted with a warning, not silently defaulted. See
`fixtures/invalid/write-capability-missing-gates.json` for a real,
concrete example this project's own test suite proves gets rejected.

## Why `authenticationRef` is a reference

A tracked adapter-manifest file is meant to be committed to a real
repository, reviewed in a real pull request, and read by a real catalog
service in a later delivery. None of that is safe if the file can also
carry a literal password or token. `authenticationRef` must instead name
WHERE a real credential lives (an environment variable, a secret store
path, a Vault path, or `none:` for a genuinely unauthenticated
read-only endpoint) - never the credential's own value. See
`fixtures/invalid/literal-secret-in-auth-ref.json` for a real rejected
example.

## What this contract deliberately does not cover yet

There is no field for a live health status, a discovered runtime
version, or a certification result - those belong to Delivery 2 (a
read-only catalog endpoint) and Delivery 4 (per-adapter hardware
certification), and adding a field for them before that code exists
would be a promise this version can't keep.
