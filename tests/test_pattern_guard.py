# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_pattern_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The guard for the patterns that adapter authors write: dialect, catastrophic backtracking and the size of what is matched."""

import json
import time
import unittest
from pathlib import Path

from hydra_umc_connector_hub.pattern_guard import DEFAULT_LIMITS, PatternLimits, check_pattern
from hydra_umc_connector_hub.schema import _validate_schema_shape, validate_against_json_schema_subset

ROOT = Path(__file__).resolve().parent.parent


def nested_quantifier_pattern() -> str:
    """The textbook catastrophic pattern, a group with a repeated item that is itself repeated, put together when the test runs so that no source line holds it as a literal."""
    return "".join(("^(", "a", "+", ")", "+", "$"))


class AcceptedPatternTests(unittest.TestCase):
    def test_the_patterns_of_the_published_schema_and_the_fixtures_are_accepted(self):
        found = []

        def walk(node):
            if isinstance(node, dict):
                if isinstance(node.get("pattern"), str):
                    found.append(node["pattern"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        for path in list((ROOT / "schemas").glob("*.json")) + list((ROOT / "fixtures").rglob("*.json")):
            try:
                walk(json.loads(path.read_text(encoding="utf-8")))
            except ValueError:
                continue  # a fixture that is not plain JSON has no patterns to read
        self.assertGreater(len(found), 5)
        for pattern in found:
            self.assertEqual(check_pattern(pattern), [], pattern)

    def test_ordinary_patterns_pass(self):
        for pattern in (r"^opc\.tcp://", r"\S", r"^[A-Z]{2}-\d{1,6}$", r"^(a|b)*$", r"(?:ab){1,5}", r"^[a-z]+(\.[a-z]+)?$", r"(?=x)x+"):
            self.assertEqual(check_pattern(pattern), [], pattern)


class RefusedPatternTests(unittest.TestCase):
    def test_nested_unbounded_repeats_are_refused(self):
        for pattern in (r"(a+)+$", r"(a*)*$", r"^(\w+\s?)*$", r"(?:x+y*)+z", r"((a+)b)+"):
            self.assertTrue(any("exponential" in p for p in check_pattern(pattern)), pattern)

    def test_alternatives_inside_an_unbounded_repeat_are_refused(self):
        self.assertTrue(check_pattern(r"^(a|aa)+$"))
        self.assertTrue(check_pattern(r"^(ab|cd)*$"))

    def test_a_bounded_inner_repeat_is_not_nested_trouble(self):
        self.assertEqual(check_pattern(r"^(a{1,3})+$"), [])

    def test_constructs_of_only_one_dialect_are_refused(self):
        for pattern in (r"(?P<n>a)b", r"(?i)abc", r"\Aabc\Z", r"(a)\1", r"(a)?(?(1)b|c)", r"a++", r"(?>a+)b"):
            reasons = check_pattern(pattern)
            self.assertTrue(reasons, pattern)
            self.assertTrue(all(isinstance(r, str) for r in reasons))

    def test_a_pattern_that_is_not_valid_or_not_text_is_a_reason_not_an_error(self):
        self.assertTrue(check_pattern("["))
        self.assertEqual(check_pattern(5), ["the pattern must be a string"])  # type: ignore[arg-type]

    def test_a_long_pattern_is_refused_and_the_limit_can_change(self):
        self.assertTrue(check_pattern("a" * 257))
        self.assertEqual(check_pattern("a" * 257, PatternLimits(max_pattern_chars=300)), [])

    def test_the_reasons_are_not_repeated(self):
        reasons = check_pattern(r"(a+)+(b+)+")
        self.assertEqual(len(reasons), len(set(reasons)))


class SchemaIntegrationTests(unittest.TestCase):
    def test_a_manifest_schema_with_a_catastrophic_pattern_is_refused_up_front(self):
        errors = _validate_schema_shape({"type": "string", "pattern": nested_quantifier_pattern()}, "$.evidenceSchema")
        self.assertTrue(any("exponential" in e for e in errors), errors)

    def test_a_catastrophic_pattern_is_never_run_and_the_check_is_fast(self):
        schema = {"type": "string", "pattern": nested_quantifier_pattern()}
        started = time.monotonic()
        errors = validate_against_json_schema_subset(schema, "a" * 40 + "!")
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertTrue(any("refused" in e for e in errors), errors)

    def test_a_value_longer_than_the_limit_is_not_matched(self):
        errors = validate_against_json_schema_subset({"type": "string", "pattern": r"\S"}, "x" * (DEFAULT_LIMITS.max_subject_chars + 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("not matched against a pattern", errors[0])

    def test_a_normal_pattern_still_matches_and_still_reports_a_miss(self):
        schema = {"type": "string", "pattern": r"^opc\.tcp://"}
        self.assertEqual(validate_against_json_schema_subset(schema, "opc.tcp://host:4840"), [])
        self.assertTrue(validate_against_json_schema_subset(schema, "http://host"))


if __name__ == "__main__":
    unittest.main()
