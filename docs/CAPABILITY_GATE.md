# Capability Gate (Delivery 3, [P0])

`sdk_gate.py`'s `evaluate_capability_call()` answers one real question:
**is this specific capability call, on this specific registered adapter,
allowed to proceed right now?** - and it answers it by calling straight
into HYDRA-UMC-SDK's own real `bridge_contract.evaluate_job()`, never a
second, competing implementation of that gate that could silently drift
from the one every physical-motion bridge (CNC/LASER/OPENPNP/PRINTER3D/
ROS2) already depends on.

## The real decision path

1. **The manifest is re-validated first.** `evaluate_capability_call()`
   runs `validate_adapter_manifest()` before anything else and raises
   `CapabilityGateError` if it finds any real error - a call is never
   gated against a contract that has already drifted invalid.
2. **The named capability must exist.** An unknown `capability_name`
   returns `allowed=False` with a real reason, never a crash.
3. **`read` never touches HYDRA-UMC-SDK at all.** `evaluate_job()` is a
   motion/write safety gate - it was never designed to protect a read,
   and a read capability's own manifest fields already are the whole
   real safety story for it.
4. **`write`/`abort` must first satisfy their own declared policy.**
   Before HYDRA-UMC-SDK is ever consulted, `evaluate_capability_call()`
   checks the capability's own `requiredPermission`/`requiredCellState`/
   `requiresHumanConfirmation`, and the manifest's own top-level
   `requiredSafetyGates`, against what the CALLER's request actually
   attests to (`granted_permissions`/`cell_mode`/`human_confirmed`/
   `satisfied_safety_gates`). Any one of these missing denies the call
   outright, with every real reason named, before the optional SDK
   dependency is even imported - a call denied on policy grounds does
   not need `hydra-umc-sdk` installed to already know the answer. Note
   `requiredCellState` (a real, adapter-defined vocabulary - e.g.
   `operational`/`supervised`/`ready`/`any`) is a DIFFERENT axis from
   `--cell-state` below (HYDRA-UMC-SDK's own generic `READY`/`INHIBITED`/
   `FAULT`/`SAFE_STOP` motion-gate state) - a capability can require
   both a specific cell mode AND a READY cell at the same time. This
   check is deliberately uniform across `write` AND `abort` - a real
   adapter that wants its own abort capability exempt from confirmation
   or cell-mode restrictions declares `requiresHumanConfirmation: false`/
   `requiredCellState: "any"` for it (every real fixture in this repo
   already does exactly that); the code itself never assumes "abort is
   exempt". (V07-006, found in an independent revalidation audit.)
5. **Only then does `write`/`abort` go through the real SDK gate.** A
   real `BridgeJob` is built from the request and passed to
   HYDRA-UMC-SDK's own `evaluate_job(job, cell_state)`:
   - `abort` maps to `JobPhase.ABORT` - always forwarded to the
     authorised safety path, exactly like a real bridge's own abort
     request.
   - `write` maps to a single stand-in `JobPhase.PROCESS`. HYDRA-UMC-SDK's
     own `JobPhase` enum (PREPARE/LOAD/PROCESS/UNLOAD/COMPLETE/ABORT)
     models a physical-motion bridge's own job lifecycle, which an
     arbitrary adapter capability (a PLC write, a print-job start) does
     not naturally have - finer job-phase granularity stays each real
     bridge's own concern, not this shared boundary's. This is a
     deliberate, named simplification, not a full job-lifecycle tracker.
   - Either way, the actual allow/deny rule is HYDRA-UMC-SDK's own,
     unmodified: the cell must be `READY` and (for anything but abort)
     the external machine must be `IDLE`.
6. **Evidence, if supplied, is checked against `evidenceSchema`.** An
   optional `evidence` payload on the request is validated with
   `schema.py`'s own `validate_against_json_schema_subset()` and folds
   into the final decision - a call can be gate-allowed and still come
   back with real `evidenceErrors` if the evidence does not match what
   the adapter itself promised to return.

## What this module does not do

- It does not track a real job's lifecycle across multiple phases -
  each `evaluate_capability_call()` is a single, stateless decision.
- It does not talk to a real machine - the `cell_state`/`machine_state`
  a caller supplies are assumed to already be a real, current
  observation from elsewhere in the ecosystem (HYDRA-UMC-SERVER, the
  cell's own safety-zone logic), never fetched by this module itself.
- Installing the optional `hydra-umc-sdk` package (`pip install -e
  ".[sdk]"`) is required only for a `write`/`abort` capability call - a
  `read` capability call, `validate`, `catalog`, `serve-catalog` and
  `certify` all work with zero extra dependencies.

## Real example

Missing every piece of the capability's own declared policy (the
default, safest state - nothing was attested to):

```
$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json \
    --capability sendControlByte --job-id j1 --idempotency-key i1 \
    --source studio --cell-state READY --machine-state IDLE
{
  "allowed": false,
  "reason": "caller lacks required permission 'cnc.control.send'; cell is not in the required mode 'supervised' for this capability (current cell mode: None); this capability requires explicit human confirmation, which was not given; required safety gate(s) not satisfied: cell.estop.clear, cell.enclosure.closed",
  "evidenceErrors": []
}
```

Fully authorised, but the cell itself is not ready - now the real SDK
motion gate is what denies it:

```
$ hydra-umc-connector-hub gate fixtures/cnc-grbl.json \
    --capability sendControlByte --job-id j1 --idempotency-key i1 \
    --source studio --cell-state INHIBITED --machine-state IDLE \
    --permission cnc.control.send --cell-mode supervised --human-confirmed \
    --safety-gate cell.estop.clear --safety-gate cell.enclosure.closed
{
  "allowed": false,
  "reason": "cell is INHIBITED, not READY",
  "evidenceErrors": []
}
```

See [docs/CLI_REFERENCE.md](CLI_REFERENCE.md) for the full `gate`
command surface, and HYDRA-UMC-SDK's own `clients/python/src/
hydra_umc_sdk/bridge_contract.py` for the real gate this module calls.
