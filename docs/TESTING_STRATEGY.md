# Testing strategy: property-based tests and mutation checks of the identity check

The gate service answers only to a caller that carries a signed token of HYDRA-UMC-SERVER. The check of that token (`identity.py`) is the gate in front of every decision of the connector, so it is tested with property-based tests besides the hand-written cases.

## Property-based tests

`tests/test_property_identity.py` states rules that must hold for every input and checks them on generated cases. The cases come from a small generator with a fixed seed (`random.Random`), so a run is the same on every machine, nothing extra is installed to run it, and the whole file takes about one second. The rules:

| Area | Rule checked on generated inputs |
| --- | --- |
| Expiry | a token is valid only while `exp` is in the future, to the instant; a missing, non-numeric, boolean or non-finite `exp` (NaN, infinity) is refused |
| Not before | an `nbf` in the future, non-numeric or non-finite is refused |
| Claims | a role outside `admin`, `operator`, `viewer` and a missing or non-text user are refused; a viewer can never decide |
| Algorithm | only `HS256`: `none` in any spelling, other algorithms, a missing algorithm, and unsigned tokens are refused |
| Signature | any change of one character of the signed part or of the signature, a token signed with another key and a token of the wrong shape are refused |
| Limits | the length limit of a token is exact; the key must have at least 32 characters |
| Robustness | any text, damaged valid token or fuzzed segment gives an `IdentityError`, never another error |
| Loopback | only real loopback addresses (including `::ffff:127.x`) are loopback; names such as `127.example.com` and white-space variants are not |

## Mutation checks (local only)

Mutation testing changes the code of a module in small ways (a `<` for a `<=`, a constant, a condition) and runs the tests: a change the tests do not notice is a behaviour nobody checks. It is a measure of the tests, not a part of the build: it is **not** run in the CI, and a run takes several minutes. To repeat it, in a throwaway virtual environment (mutmut 2 counts only the exit code 1 of the test command as a kill, so use a runner that maps every failing exit code to 1):

```
python -m pip install "mutmut<3" pytest
mutmut run --paths-to-mutate src/hydra_umc_connector_hub/identity.py --runner "python runner.py tests/test_property_identity.py tests/test_identity.py"
mutmut results
```

The whole module was mutated.

| Target | Mutants | Killed by the first run | Killed after the added tests | Left |
| --- | --- | --- | --- | --- |
| `identity.py` | 106 | 100 (94.3 %) | 103 (97.2 %) | 3, equivalent |

The tests added after the first run check the exact length limits, the texts of the refusals and the minimum length of the key. The three left are equivalent changes: the two spellings of the loopback address that the address parser accepts anyway, and the sign of the padding of a base64 text, which the decoder tolerates.
