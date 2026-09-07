# Support Information 🔌 (HYDRA-UMC-CONNECTOR-HUB)

Thank you for using HYDRA-UMC-CONNECTOR-HUB! Here is how you can get help:

## 📺 Video Tutorials & Demos

The best way to see how this project's own adapter-manifest contract
works is through our official YouTube channel:
[youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## ✉️ Direct Technical Inquiries

For questions about writing a new adapter manifest, the validator's own
rules, or anything not covered by the README:
Email: `electrohobby3d@gmail.com`

## 🐛 Bug Reports

If `hydra-umc-connector-hub validate` accepts a manifest it should
reject (especially a literal secret in `authenticationRef`, or a
`write`/`abort` capability missing a real safety field - see
`SECURITY.md` for that specifically), or rejects one of the ten real
fixtures in `fixtures/` that should validate cleanly, please open a
**GitHub Issue** in this repository - include the exact manifest file
(with any real credential replaced by a placeholder reference) and the
full, real CLI output.
*Please search existing issues before opening a new one.*

## ❌ What is NOT support?

- This is Delivery 1 (schema + CLI validate + fixtures) of a 4-delivery
  plan - it has no network endpoint, no runtime catalog, and does not
  yet register the real existing bridges anywhere queryable. Please do
  not open an Issue asking it to do something a later delivery has not
  shipped yet; see the README's own Roadmap section for what is planned
  and when.
- This project validates a manifest's own DECLARED shape - it never
  contacts a real machine to confirm the manifest is accurate. A bridge
  project's own real protocol behavior (HYDRA-UMC-BRIDGE-CNC,
  HYDRA-UMC-OPCUA-SERVER, etc.) belongs on THAT project's own issue
  tracker, not this one's.
