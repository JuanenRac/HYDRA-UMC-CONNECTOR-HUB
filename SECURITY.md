# Security Policy 🔒 (HYDRA-UMC-CONNECTOR-HUB)

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x.x   | ✅ Yes    |

## Reporting a Vulnerability

**CRITICAL: Do not report vulnerabilities through public GitHub issues.**

This project is designed, from its very first delivery, around a
non-negotiable limit: an adapter manifest must never be able to smuggle a
literal secret past this validator, and a `write`/`abort` capability must
never validate as safe when it is missing a real safety condition. If you
discover a vulnerability affecting:

- **What `validate_adapter_manifest()` accepts as a valid
  `authenticationRef`** - a way to make a literal token, password, or
  other secret-shaped value pass the reference-prefix check (currently
  `env:`/`secret-store:`/`vault:`/`none:`), or a way to make the
  write/abort safety-field check (`risk`/`requiredPermission`/
  `requiredCellState`/`requiresHumanConfirmation`/`timeoutMs`) pass while
  one of those fields is actually missing, empty, or the wrong type.
- **What `load_and_validate()` does with a hostile file path or file
  content** - this version reads exactly the path(s) given on the
  command line; a way to make it read outside an expected fixtures/
  manifests directory, or a way to make a malformed file crash the
  process instead of producing a real, reported validation error.

**Not yet applicable** - later deliveries this repository will
eventually implement (a read-only catalog endpoint over the network in
Delivery 2, real per-adapter hardware certification in Delivery 4) carry
their own, larger real attack surface once they exist. This version has
no network-facing service, executes no adapter, and never contacts a
real machine - there is nothing there yet to have a vulnerability in on
that front.

Please report responsibly:

1. **Email**: Send a detailed report to `electrohobby3d@gmail.com`.
2. **Impact**: Describe the attack surface affected and a realistic
   scenario (this delivery is a local CLI validator with no
   network-facing service of its own - the most realistic scenario is a
   hostile or malformed adapter-manifest file being validated).
3. **Response**: Initial acknowledgment within 48 hours.

We follow a coordinated disclosure policy.
