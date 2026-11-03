# =============================================================================
# HYDRA-UMC-CONNECTOR-HUB - tests/test_jwks.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Verification of the EdDSA tokens of the SERVER by its key set: a fake local key set with ephemeral keys, rotation, unknown keys, forged tokens, the cache
and the limit on how often the set is read, fail-closed, and the settings of `serve-gate`."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hydra_umc_connector_hub import jwks as J
from hydra_umc_connector_hub.cli import _build_token_verifier
from hydra_umc_connector_hub.gate_audit import GateAudit
from hydra_umc_connector_hub.gate_server import GateServiceConfig, serve_gate
from hydra_umc_connector_hub.identity import IdentityError, TokenVerifier

from _ed25519_test_keys import TestKey, b64
from test_collect_and_gate_service import FIXTURES, KEY, make_token

BODY = {"adapterId": "industrial-mqtt", "capability": "publishCommandTopic", "jobId": "job-1", "source": "test-suite"}


class FakeServer:
    """A key set on a loopback port; `keys` and `status` can be changed while it runs; `hits` counts the reads."""

    def __init__(self, keys):
        self.keys, self.status, self.raw, self.hits = list(keys), 200, None, 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                outer.hits += 1
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/.well-known/jwks.json")
                    self.end_headers()
                    return
                body = outer.raw if outer.raw is not None else json.dumps({"keys": [k.jwk() for k in outer.keys]}).encode()
                self.send_response(outer.status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/.well-known/jwks.json"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Ed25519Tests(unittest.TestCase):
    def test_rfc8032_vector_1_and_tampering(self):
        seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        key = TestKey(seed)
        self.assertEqual(key.public.hex(), "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        signature = key.sign(b"")
        self.assertEqual(signature.hex(), "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertTrue(J.ed25519_verify(key.public, b"", signature))
        self.assertFalse(J.ed25519_verify(key.public, b"x", signature))
        self.assertFalse(J.ed25519_verify(TestKey().public, b"", signature))
        self.assertFalse(J.ed25519_verify(key.public, b"", signature[:-1] + bytes([signature[-1] ^ 1])))
        malleable = signature[:32] + int.to_bytes(int.from_bytes(signature[32:], "little") + J._Q, 32, "little")
        self.assertFalse(J.ed25519_verify(key.public, b"", malleable))
        self.assertFalse(J.ed25519_verify(key.public, b"", b"\x00" * 64))
        self.assertFalse(J.ed25519_verify(b"\x00" * 31, b"", signature))


class KeySetParsingTests(unittest.TestCase):
    def test_only_well_formed_keys_with_their_own_thumbprint_are_kept(self):
        good, other = TestKey(), TestKey()
        document = {"keys": [
            good.jwk(),
            {**other.jwk(), "kid": "spoofed"},                 # the name is not the thumbprint of the key
            {**other.jwk(), "kty": "RSA"},
            {**other.jwk(), "alg": "RS256"},
            {**other.jwk(), "use": "enc"},
            {**other.jwk(), "x": b64(other.public[:31])},
            {**other.jwk(), "x": "!!!"},
            "junk",
        ]}
        self.assertEqual(J.parse_jwks(document), {good.kid: good.public})
        for bad in ({}, {"keys": "x"}, {"keys": []}, [], {"keys": [{**other.jwk(), "kid": "spoofed"}]}):
            with self.assertRaises(J.JwksError):
                J.parse_jwks(bad)

    def test_the_address_must_be_https_or_loopback_without_credentials(self):
        for ok in ("https://server.example/.well-known/jwks.json", "http://127.0.0.1:3000/x", "http://localhost/x", "http://[::1]:3000/x"):
            self.assertEqual(J.check_jwks_url(ok), ok)
        for bad in ("http://server.example/x", "http://10.0.0.5/x", "http://127.example.com/x", "ftp://127.0.0.1/x", "https://user:pw@server.example/x",
                    "https://server.example/x#f", "https://", "", None, "https://server.example:99999/x", "file:///etc/passwd"):
            with self.assertRaises(ValueError, msg=str(bad)):
                J.check_jwks_url(bad)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.key = TestKey()
        self.server = FakeServer([self.key])
        self.addCleanup(self.server.close)
        self.clock = Clock()
        self.client = J.JwksClient(self.server.url, ttl_s=300, min_refetch_s=30, clock=self.clock)
        self.verifier = TokenVerifier(jwks=self.client, hs256_key=KEY)

    def test_a_good_token_gives_the_claims_of_today(self):
        who = self.verifier.verify(self.key.token("admin"))
        self.assertEqual((who.username, who.role, who.source), ("ana", "admin", "token"))

    def test_forged_and_malformed_tokens_are_refused(self):
        stranger = TestKey()
        good = self.key.token("operator")
        head, body, sig = good.split(".")
        other_body = self.key.token("admin").split(".")[1]
        cases = {
            "signed by a stranger with the real kid": stranger.token(kid=self.key.kid),
            "tampered role": f"{head}.{other_body}.{sig}",
            "unknown kid": self.key.token(kid="nobody"),
            "no kid": self.key.token(kid=None),
            "alg none": self.key.token(alg="none"),
            "alg ES256": self.key.token(alg="ES256"),
            "alg RS256": self.key.token(alg="RS256"),
            "alg HS384": self.key.token(alg="HS384"),
            "expired": self.key.token(exp_in=-5),
            "no exp": self.key.token(exp=None),
            "nbf in the future": self.key.token(nbf=2**33),
            "iat in the future": self.key.token(iat=2**33),
            "no username": self.key.token(username=None),
            "unknown role": self.key.token(role="root"),
            "empty signature": f"{head}.{body}.",
            "short signature": f"{head}.{body}.{b64(b'x' * 10)}",
        }
        for name, token in cases.items():
            with self.assertRaises(IdentityError, msg=name):
                self.verifier.verify(token)

    def test_hs256_confusion_with_the_public_key_is_refused(self):
        # an attacker signs HS256 using the PUBLIC key (published) as if it were the shared secret
        for verifier in (TokenVerifier(jwks=self.client), TokenVerifier(jwks=self.client, hs256_key=KEY)):
            for secret in (b64(self.key.public).encode() + b"x" * 32, self.key.public + b"x" * 32):
                with self.assertRaises(IdentityError):
                    verifier.verify(make_token("admin", key=secret))
        with self.assertRaises(IdentityError):
            TokenVerifier(jwks=self.client, hs256_key=KEY).verify(make_token("admin", key=b"another-key-of-more-than-32-characters"))

    def test_hs256_only_while_the_configuration_allows_it(self):
        token = make_token("operator")
        self.assertEqual(self.verifier.verify(token).role, "operator")
        with self.assertRaises(IdentityError) as ctx:
            TokenVerifier(jwks=self.client, hs256_key=KEY, accept_hs256=False).verify(token)
        self.assertIn("only EdDSA", str(ctx.exception))
        with self.assertRaises(IdentityError):
            TokenVerifier(jwks=self.client).verify(token)            # no HS256 key given
        with self.assertRaises(ValueError):
            TokenVerifier(hs256_key=KEY, accept_hs256=False)         # nothing would verify
        with self.assertRaises(ValueError):
            TokenVerifier()
        with self.assertRaises(IdentityError):
            TokenVerifier(hs256_key=KEY).verify(self.key.token())    # EdDSA is not allowed without an address

    def test_cache_ttl_and_unknown_kid_rate_limit(self):
        self.verifier.verify(self.key.token())
        self.verifier.verify(self.key.token())
        self.assertEqual(self.server.hits, 1)                         # cached
        newer = TestKey()
        self.server.keys.append(newer)
        with self.assertRaises(IdentityError):                        # unknown kid, but read less than 30 s ago: no new read
            self.verifier.verify(newer.token())
        self.assertEqual(self.server.hits, 1)
        self.clock.now += 31                                          # the limit has passed: the rotation is seen
        self.assertEqual(self.verifier.verify(newer.token()).role, "operator")
        self.assertEqual(self.server.hits, 2)
        for _ in range(50):                                           # a flood of invented kids
            with self.assertRaises(IdentityError):
                self.verifier.verify(self.key.token(kid="x"))
        self.assertEqual(self.server.hits, 2)
        self.clock.now += 31
        with self.assertRaises(IdentityError):
            self.verifier.verify(self.key.token(kid="x"))
        self.assertEqual(self.server.hits, 3)                         # at most one read per window
        self.clock.now += 301                                         # time to live over: refreshed
        self.verifier.verify(self.key.token())
        self.assertEqual(self.server.hits, 4)

    def test_rotation_with_overlap_and_retirement(self):
        old, new = self.key, TestKey()
        self.verifier.verify(old.token())
        self.server.keys = [new, old]                                 # overlap: both published
        self.clock.now += 31
        self.assertEqual(self.verifier.verify(new.token()).role, "operator")
        self.assertEqual(self.verifier.verify(old.token()).role, "operator")
        self.server.keys = [new]                                      # the old one is retired
        self.clock.now += 301
        self.assertEqual(self.verifier.verify(new.token()).role, "operator")
        with self.assertRaises(IdentityError):
            self.verifier.verify(old.token())

    def test_fail_closed_when_the_server_does_not_answer(self):
        self.verifier.verify(self.key.token())
        self.server.status = 503
        self.clock.now += 301                                         # cache expired and the server is down
        with self.assertRaises(IdentityError) as ctx:
            self.verifier.verify(self.key.token())
        self.assertNotIn("127.0.0.1", str(ctx.exception))             # the reason holds no address
        hits = self.server.hits
        self.clock.now += 1
        with self.assertRaises(IdentityError):
            self.verifier.verify(self.key.token())
        self.assertEqual(self.server.hits, hits)                      # failures are rate limited too
        self.server.status = 200
        self.clock.now += 31
        self.assertEqual(self.verifier.verify(self.key.token()).role, "operator")   # recovers

    def test_a_server_that_cannot_be_reached_or_answers_junk_gives_no_identity(self):
        self.server.close()
        with self.assertRaises(IdentityError):
            self.verifier.verify(self.key.token())
        for raw in (b"not json", b"[]", b'{"keys": []}', b"x" * (J.MAX_JWKS_BYTES + 10)):
            server = FakeServer([self.key])
            server.raw = raw
            try:
                client = J.JwksClient(server.url, clock=Clock())
                with self.assertRaises(IdentityError, msg=raw[:20]):
                    TokenVerifier(jwks=client).verify(self.key.token())
            finally:
                server.close()

    def test_redirects_are_not_followed(self):
        client = J.JwksClient(self.server.url.replace("/.well-known/jwks.json", "/redirect"), clock=Clock())
        with self.assertRaises(IdentityError):
            TokenVerifier(jwks=client).verify(self.key.token())

    def test_settings_of_the_client_are_checked(self):
        for kwargs in ({"ttl_s": 0}, {"ttl_s": -1}, {"min_refetch_s": True}, {"timeout_s": 10**6}, {"ttl_s": "5"}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                J.JwksClient(self.server.url, **kwargs)


class ServeGateSettingsTests(unittest.TestCase):
    def test_identity_block_builds_the_verifier(self):
        self.assertIsNone(_build_token_verifier({}, KEY))
        plain = _build_token_verifier({"identity": {}}, KEY)    # no address: HS256 with the key, as before
        self.assertIsNone(plain.jwks)
        self.assertIsNotNone(plain.hs256_key)
        verifier = _build_token_verifier({"identity": {"jwks_url": "https://server.example/.well-known/jwks.json", "jwks_ttl_s": 60}}, KEY)
        self.assertIsNotNone(verifier.jwks)
        self.assertIsNotNone(verifier.hs256_key)
        verifier = _build_token_verifier({"identity": {"jwks_url": "https://server.example/j", "accept_hs256": False}}, KEY)
        self.assertIsNone(verifier.hs256_key)
        for bad in (
            {"identity": []}, {"identity": {"jwks_url": "http://server.example/j"}}, {"identity": {"accept_hs256": "yes", "jwks_url": "https://s.example/j"}},
            {"identity": {"accept_hs256": False}}, {"identity": {"jwks_ttl_s": 5}}, {"identity": {"jwks_url": "https://s.example/j", "other": 1}},
            {"identity": {"jwks_url": "https://s.example/j", "jwks_ttl_s": 0}},
        ):
            with self.assertRaises(ValueError, msg=str(bad)):
                _build_token_verifier(bad, KEY)

    def _serve(self, verifier):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        registry = Path(tmp.name) / "registry"
        registry.mkdir()
        (registry / "industrial-mqtt.json").write_text((FIXTURES / "industrial-mqtt.json").read_text(encoding="utf-8"), encoding="utf-8")
        audit = GateAudit(str(Path(tmp.name) / "audit.jsonl"), None)
        server = serve_gate(GateServiceConfig(str(registry), audit, token_verifier=verifier), host="127.0.0.1", port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return f"http://127.0.0.1:{server.server_port}"

    @staticmethod
    def _post(base, token):
        request = urllib.request.Request(f"{base}/gate/evaluate", data=json.dumps(BODY).encode(), method="POST",
                                         headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_the_gate_service_accepts_an_eddsa_token_and_refuses_the_rest(self):
        key = TestKey()
        fake = FakeServer([key])
        self.addCleanup(fake.close)
        base = self._serve(TokenVerifier(jwks=J.JwksClient(fake.url), hs256_key=KEY))
        self.assertNotEqual(self._post(base, key.token("operator")), 401)
        self.assertEqual(self._post(base, key.token("viewer")), 403)
        self.assertEqual(self._post(base, TestKey().token(kid=key.kid)), 401)
        self.assertEqual(self._post(base, key.token(alg="none")), 401)
        self.assertNotEqual(self._post(base, make_token("operator")), 401)    # HS256 still allowed by the configuration
        fake.close()
        self.assertEqual(self._post(base, TestKey().token()), 401)


if __name__ == "__main__":
    unittest.main()
