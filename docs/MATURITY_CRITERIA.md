<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Maturity exit criteria
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Exit Criteria: Scaffolding to Functional (met)

This project is labelled `functional`: it moved up from `scaffolding` when every item below became true. The label moves to `functional` only
when every item below is true and verifiable in the repository (a test, a
CI check or a reproducible command) - not when the code merely exists.

- [x] A versioned connector schema is published (connectors, pins, power, capabilities) and validated by a test (`tests/test_published_schema.py`: the published schema and the validator accept and reject the same examples).
- [x] A validator rejects incompatible configurations before they reach a board or a design tool, with one test per rejection reason (`tests/test_schema.py`, `tests/test_hardening.py`, `tests/test_robustness.py`).
- [x] The registry keeps its deterministic snapshot behaviour and owner verification, covered by tests (`tests/test_registry.py`: `catalog_snapshot_version`, `verify_catalog_owners`).

Verified on real hardware or services is a separate, later step: a passing
software check does not certify physical behaviour.
