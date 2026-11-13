# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - src/hydra_umc_connector_hub/pattern_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A guard for the regular expressions that an adapter author writes in a `pattern` of a schema.

A JSON Schema `pattern` is written for ECMA-262 regular expressions, and this hub runs it with Python's `re`, which has no time limit. Two
things can go wrong with a pattern that someone else wrote:

* it uses a construct that exists in only one of the two dialects (named groups `(?P<n>...)`, inline flags `(?i)`, the anchors `\\A` and
  `\\Z`, back references, conditionals), so the same manifest would be valid in one tool and not in another;
* it can take exponential time on a short input ("catastrophic backtracking": an unbounded repeat inside an unbounded repeat, or an unbounded
  repeat of alternatives, such as `(a+)+$` or `(a|aa)*$`).

`check_pattern()` refuses both before a manifest is accepted, and `MAX_SUBJECT_CHARS` bounds how long a value may be when it is matched. The
limits are in `PatternLimits`, so a deployment can change them; the defaults are conservative.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

try:  # Python 3.11+ keeps the parser in a private module of re
    from re import _constants as _sre_constants  # type: ignore[attr-defined]
    from re import _parser as _sre_parse  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - older interpreters
    import sre_constants as _sre_constants  # type: ignore[no-redef]
    import sre_parse as _sre_parse  # type: ignore[no-redef]


@dataclass(frozen=True)
class PatternLimits:
    """Bounds for a pattern an author wrote and for the value it is matched against."""

    max_pattern_chars: int = 256
    max_subject_chars: int = 4096
    # a repeat whose upper bound is above this counts as unbounded for the check of nested repeats
    unbounded_from: int = 1000


DEFAULT_LIMITS = PatternLimits()

# Constructs of Python's `re` that ECMA-262 does not have, found in the text of the pattern.
_PYTHON_ONLY_TEXT = (
    (re.compile(r"\(\?P[<=>]"), "named groups written (?P<name>...)"),
    (re.compile(r"\(\?[aiLmsux-]+[:)]"), "inline flags"),
    (re.compile(r"\\[AZ]"), "the anchors \\A and \\Z"),
    (re.compile(r"\(\?\("), "conditionals"),
)

_REPEATS = {_sre_constants.MAX_REPEAT, _sre_constants.MIN_REPEAT}
_GROUP_REFERENCES = {_sre_constants.GROUPREF, getattr(_sre_constants, "GROUPREF_EXISTS", _sre_constants.GROUPREF)}


def _is_unbounded(maximum: int, limits: PatternLimits) -> bool:
    return maximum >= limits.unbounded_from or maximum == _sre_constants.MAXREPEAT


def _walk(items, limits: PatternLimits, inside_unbounded: bool, problems: list[str]) -> None:
    for opcode, argument in items:
        if opcode in _GROUP_REFERENCES:
            problems.append("back references are not part of the JSON Schema dialect")
        elif opcode == getattr(_sre_constants, "POSSESSIVE_REPEAT", None) or opcode == getattr(_sre_constants, "ATOMIC_GROUP", None):
            problems.append("uses possessive quantifiers or atomic groups, which the JSON Schema dialect does not have")
        elif opcode in _REPEATS:
            _low, high, body = argument
            unbounded = _is_unbounded(high, limits)
            if unbounded and inside_unbounded:
                problems.append("an unbounded repeat inside another unbounded repeat can take exponential time")
            _walk(body, limits, inside_unbounded or unbounded, problems)
        elif opcode == _sre_constants.BRANCH:
            if inside_unbounded:
                problems.append("alternatives inside an unbounded repeat can take exponential time")
            for branch in argument[1]:
                _walk(branch, limits, inside_unbounded, problems)
        elif opcode == _sre_constants.SUBPATTERN:
            _walk(argument[-1], limits, inside_unbounded, problems)
        elif opcode in (_sre_constants.ASSERT, _sre_constants.ASSERT_NOT):
            _walk(argument[1], limits, inside_unbounded, problems)


def check_pattern(pattern: str, limits: PatternLimits = DEFAULT_LIMITS) -> list[str]:
    """The reasons why `pattern` is not accepted from an adapter author; an empty list means it is. Never raises."""
    if not isinstance(pattern, str):
        return ["the pattern must be a string"]
    if len(pattern) > limits.max_pattern_chars:
        return [f"the pattern is longer than {limits.max_pattern_chars} characters"]
    problems: list[str] = []
    for found, what in _PYTHON_ONLY_TEXT:
        if found.search(pattern):
            problems.append(f"uses {what}, which the JSON Schema dialect does not have")
    try:
        parsed = _sre_parse.parse(pattern)
    except (re.error, RecursionError, OverflowError) as exc:
        return [f"is not a valid regular expression: {exc}"]
    _walk(parsed, limits, False, problems)
    seen: set[str] = set()
    return [p for p in problems if not (p in seen or seen.add(p))]  # type: ignore[func-returns-value]
