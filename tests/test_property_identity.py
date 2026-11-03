# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_property_identity.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Property-based tests of the identity check: no manipulated, expired or foreign token gives an identity, and no text is taken for a loopback address by mistake.

The cases come from a small generator with a FIXED seed (``random.Random``), so a run is the same everywhere and no test dependency is needed; the number of cases per
property is bounded to keep the file in a few seconds.
"""
import base64
import hashlib
import hmac
import json
import random
import tempfile
import unittest
from pathlib import Path

from hydra_umc_connector_hub.identity import DECIDE_ROLES, MIN_KEY_LENGTH, ROLES, Identity, IdentityError, MAX_TOKEN_CHARS, is_loopback, load_identity_key, require_role, verify_token

SEED = 7001
CASES = 600
KEY = b"k" * 40
NOW = 1_900_000_000.0


def rng(name):
    return random.Random(f"{SEED}:{name}")


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make(claims=None, header=None, key=KEY, sign=True):
    head = b64(json.dumps(header if header is not None else {"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps(claims if claims is not None else {"username": "ana", "role": "operator", "exp": NOW + 60}).encode())
    sig = hmac.new(key, f"{head}.{body}".encode(), hashlib.sha256).digest() if sign else b""
    return f"{head}.{body}.{b64(sig) if sign else 'AAAA'}"


class TokenProperties(unittest.TestCase):
    def refused(self, token, key=KEY, now=NOW):
        with self.assertRaises(IdentityError):
            verify_token(token, key, now=now)

    def test_the_good_token_is_accepted_for_every_role(self):
        for role in ROLES:
            who = verify_token(make({"username": "ana", "role": role, "exp": NOW + 1}), KEY, now=NOW)
            self.assertEqual((who.username, who.role, who.source), ("ana", role, "token"))

    def test_the_expiry_is_exact_and_a_non_finite_one_is_refused(self):
        r = rng("exp")
        for _ in range(CASES):
            delta = r.choice([-1e9, -1, -0.001, 0, 0.001, 1, 1e9, r.uniform(-100, 100)])
            token = make({"username": "ana", "role": "viewer", "exp": NOW + delta})
            if delta > 0:
                verify_token(token, KEY, now=NOW)
            else:
                self.refused(token)
        for odd in (float("nan"), float("inf"), -float("inf"), True, False, None, "9999999999", [], {}):
            claims = {"username": "ana", "role": "viewer", "exp": odd}
            self.refused(make(claims))            # json.dumps writes NaN and Infinity, which json.loads reads back
        self.refused(make({"username": "ana", "role": "viewer"}))

    def test_not_before_in_the_future_or_unreadable_is_refused(self):
        r = rng("nbf")
        for _ in range(CASES):
            delta = r.choice([-5, 0, 1, 5, 3600, r.uniform(-50, 50)])
            token = make({"username": "ana", "role": "viewer", "exp": NOW + 100, "nbf": NOW + delta})
            if delta <= 0:
                verify_token(token, KEY, now=NOW)
            else:
                self.refused(token)
        for odd in (float("nan"), float("inf"), True, "0", [], {}):
            self.refused(make({"username": "ana", "role": "viewer", "exp": NOW + 100, "nbf": odd}))

    def test_a_token_with_a_wrong_role_or_user_is_refused(self):
        r = rng("claims")
        for _ in range(CASES):
            role = r.choice(["admin", "operator", "viewer", "root", "Admin", "", None, 5, ["admin"], "admin ", "loopback", "superuser"])
            user = r.choice(["ana", "", None, 5, ["a"], {}, True])
            token = make({"username": user, "role": role, "exp": NOW + 10})
            if role in ROLES and isinstance(user, str) and user:
                self.assertEqual(verify_token(token, KEY, now=NOW).role, role)
            else:
                self.refused(token)

    def test_only_hs256_is_accepted_as_algorithm(self):
        r = rng("alg")
        for alg in ["none", "None", "NONE", "HS384", "HS512", "RS256", "ES256", "hs256", "HS256 ", "", None, 5, ["HS256"]]:
            self.refused(make(header={"alg": alg}))
            self.refused(make(header={"alg": alg}, sign=False))
        self.refused(make(header={"typ": "JWT"}))
        for _ in range(100):   # the classic confusion: the algorithm none with an empty signature, or a signature of any bytes
            head = b64(json.dumps({"alg": r.choice(["none", "None"])}).encode())
            body = b64(json.dumps({"username": "ana", "role": "admin", "exp": NOW + 99}).encode())
            for tail in ("", b64(bytes(r.randrange(256) for _ in range(32))), "AAAA"):
                self.refused(f"{head}.{body}.{tail}")

    def test_any_change_to_the_signed_part_or_the_signature_is_refused(self):
        token = make()
        r = rng("flip")
        for _ in range(CASES):
            chars = list(token)
            i = r.randrange(len(chars))
            replacement = r.choice("ABCxyz019-_")
            if chars[i] == replacement or chars[i] == ".":
                continue
            chars[i] = replacement
            changed = "".join(chars)
            try:
                who = verify_token(changed, KEY, now=NOW)
            except IdentityError:
                continue
            # the one tolerated change is the unused trailing bits of the last base64 character: the very same signature bytes, so the very same identity
            self.assertEqual(i, len(token) - 1)
            self.assertEqual((who.username, who.role), ("ana", "operator"))

    def test_a_token_of_another_key_or_of_the_wrong_shape_is_refused(self):
        r = rng("shape")
        for _ in range(100):
            other = bytes(r.randrange(256) for _ in range(40))
            if other != KEY:
                self.refused(make(key=other))
        junk = ["", ".", "..", "a.b", "a.b.c.d", "a..c", ".b.c", "a.b.", "é.é.é", "x" * (MAX_TOKEN_CHARS + 1), "..." + "." * 10, None, "a.b.c"]
        for item in junk:
            self.refused(item)
        good = make()
        for _ in range(CASES):
            parts = good.split(".")
            parts = [p for p in r.sample(parts, r.randrange(0, 4))] if r.random() < 0.5 else parts[: r.randrange(0, 3)]
            if ".".join(parts) != good:
                self.refused(".".join(parts))
        self.refused(make(), key=b"")

    def test_never_an_exception_other_than_identity_error(self):
        r = rng("fuzz")
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-_=.é\u0000 "
        base = make()
        for _ in range(CASES * 3):
            if r.random() < 0.5:
                token = "".join(r.choice(alphabet) for _ in range(r.randrange(0, 120)))
            else:
                parts = base.split(".")
                parts[r.randrange(3)] = "".join(r.choice(alphabet) for _ in range(r.randrange(0, 60)))
                token = ".".join(parts)
            try:
                verify_token(token, KEY, now=NOW)
            except IdentityError:
                pass


class RoleAndLoopback(unittest.TestCase):
    def test_a_viewer_or_unknown_role_may_never_decide(self):
        r = rng("roles")
        for _ in range(CASES):
            role = r.choice(list(ROLES) + ["loopback", "root", "", "ADMIN"])
            if role in DECIDE_ROLES:
                require_role(Identity("ana", role, "token"), DECIDE_ROLES)
            else:
                with self.assertRaises(IdentityError):
                    require_role(Identity("ana", role, "token"), DECIDE_ROLES)

    def test_only_real_loopback_addresses_are_loopback(self):
        for good in ("127.0.0.1", "127.0.0.2", "127.255.255.254", "::1", "localhost", "::ffff:127.0.0.1", "::ffff:127.9.9.9"):
            self.assertTrue(is_loopback(good), good)
        for bad in ("", "0.0.0.0", "10.0.0.1", "192.168.0.180", "128.0.0.1", "::", "::2", "::ffff:10.0.0.1", "127.example.com", "127.0.0.1.evil.test", "127", "127.",
                    "localhost.evil.test", "LOCALHOST", " 127.0.0.1", "127.0.0.1 ", "8.8.8.8", "fe80::1"):
            self.assertFalse(is_loopback(bad), bad)
        r = rng("loop")
        for _ in range(CASES):
            text = "".join(r.choice("0123456789.:abcf") for _ in range(r.randrange(0, 16)))
            if is_loopback(text):
                self.assertTrue(text in ("::1",) or text.startswith(("127.", "::ffff:127.", "0:0:0:0:0:0:0:1")) or text.count(":") >= 2, text)


class LimitsAndReasons(unittest.TestCase):
    """Added after a mutation run: the exact limits and the reasons that are answered and recorded."""

    def reason(self, token, key=KEY):
        with self.assertRaises(IdentityError) as caught:
            verify_token(token, key, now=NOW)
        return str(caught.exception)

    def test_the_reasons_are_the_documented_ones(self):
        self.assertEqual(self.reason(None), "a signed token of HYDRA-UMC-SERVER is required")
        self.assertEqual(self.reason(""), "a signed token of HYDRA-UMC-SERVER is required")
        self.assertEqual(self.reason("a.b"), "the token is malformed")
        self.assertEqual(self.reason("x" * (MAX_TOKEN_CHARS + 1)), "the token is malformed")
        self.assertEqual(self.reason(make(header={"alg": "none"})), "the token algorithm is not accepted (only HS256)")
        self.assertEqual(self.reason(make(key=b"z" * 40)), "the token signature is not valid")
        head = b64(b"[1]")
        self.assertEqual(self.reason(f"{head}.{head}.{head}"), "the token is malformed")
        self.assertEqual(self.reason(f"!!!.{head}.{head}"), "the token is malformed")
        self.assertEqual(self.reason(make({"username": "ana", "role": "viewer"})), "the token has no expiry")
        self.assertEqual(self.reason(make({"username": "ana", "role": "viewer", "exp": NOW - 1})), "the token has expired")
        self.assertEqual(self.reason(make({"username": "ana", "role": "viewer", "exp": NOW + 9, "nbf": NOW + 5})), "the token is not valid yet")
        self.assertEqual(self.reason(make({"role": "viewer", "exp": NOW + 9})), "the token names no user")
        self.assertEqual(self.reason(make({"username": "ana", "role": "root", "exp": NOW + 9})), "the token carries no known role")
        with self.assertRaises(IdentityError) as caught:
            require_role(Identity("ana", "viewer", "token"), DECIDE_ROLES)
        self.assertEqual(str(caught.exception), "the role 'viewer' may not do this (needs one of admin, operator)")
        self.assertEqual(self.reason("A.B.C"), "the token is malformed")      # a base64 text of one character more than a multiple of four cannot be decoded
        self.assertEqual(self.reason(make().rsplit(".", 1)[0] + ".A"), "the token is malformed")

    def token_of_length(self, length):
        claims = {"username": "ana", "role": "viewer", "exp": NOW + 9, "pad": ""}
        for pad in range(0, 6000):
            claims["pad"] = "p" * pad
            token = make(claims)
            if len(token) >= length:
                return token   # the first one that long (the base64 text grows in steps)
        self.fail("could not build a token of the length %d" % length)

    def test_the_token_length_limit_is_exact(self):
        exact = self.token_of_length(MAX_TOKEN_CHARS)
        self.assertEqual(len(exact), MAX_TOKEN_CHARS)
        self.assertEqual(verify_token(exact, KEY, now=NOW).username, "ana")
        just_over = self.token_of_length(MAX_TOKEN_CHARS + 1)
        self.assertEqual(len(just_over), MAX_TOKEN_CHARS + 1)
        self.refused_malformed(just_over)

    def refused_malformed(self, token):
        self.assertEqual(self.reason(token), "the token is malformed")

    def test_the_key_must_have_at_least_the_minimum_length_exactly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "key.txt"
            for length in (0, 1, MIN_KEY_LENGTH - 1, MIN_KEY_LENGTH, MIN_KEY_LENGTH + 1, 200):
                path.write_text("k" * length + chr(10), encoding="utf-8")
                if length >= MIN_KEY_LENGTH:
                    self.assertEqual(load_identity_key(str(path)), b"k" * length)
                else:
                    with self.assertRaises(ValueError) as caught:
                        load_identity_key(str(path))
                    self.assertEqual(str(caught.exception), f"the identity key must have at least {MIN_KEY_LENGTH} characters")
        self.assertEqual(MIN_KEY_LENGTH, 32)

    def test_an_identity_cannot_be_changed_and_says_what_to_audit(self):
        who = Identity("ana", "admin", "token")
        with self.assertRaises(Exception) as caught:
            who.role = "viewer"
        self.assertEqual(type(caught.exception).__name__, "FrozenInstanceError")
        self.assertEqual(who.as_audit(), {"username": "ana", "role": "admin", "identitySource": "token"})


if __name__ == "__main__":
    unittest.main()
