<!-- =============================================================================
HYDRA-UMC-CONNECTOR-HUB - Maturity exit criteria
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0 - see LICENSE
============================================================================= -->

# Exit Criteria: Scaffolding to Functional

This project is labelled `scaffolding`. The label moves to `functional` only
when every item below is true and verifiable in the repository (a test, a
CI check or a reproducible command) - not when the code merely exists.

- [ ] A versioned connector schema is published (connectors, pins, power, capabilities) and validated by a test.
- [ ] A validator rejects incompatible configurations before they reach a board or a design tool, with one test per rejection reason.
- [ ] The registry keeps its deterministic snapshot behaviour and owner verification, covered by tests.

Verified on real hardware or services is a separate, later step: a passing
software check does not certify physical behaviour.
