"""Cryptographic verification contracts using generated RSA keys, never real tokens."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


ISSUER = "https://identity.example.test"
AUDIENCE = "life-planner-api"


class SignedIdentityFixture:
    """Shared test fixture only; this does not issue production credentials."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix="lp-api-keys-")
        self.addCleanup(self.temporary.cleanup)
        self.jwks_path = Path(self.temporary.name) / "jwks.json"
        key = json.loads(RSAAlgorithm.to_jwk(self.signing_key.public_key()))
        key.update({"kid": "test-key", "use": "sig", "alg": "RS256"})
        self.public_jwk = key
        self.jwks_path.write_text(json.dumps({"keys": [key]}))

    def token(self, subject="alice", *, changes=None, omit=(), headers=None, key=None):
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": subject,
                  "iat": now - 5, "exp": now + 300, "client_id": "test-web-client", "jti": "test-token-id"}
        claims.update(changes or {})
        for field in omit:
            claims.pop(field, None)
        return jwt.encode(claims, key or self.signing_key, algorithm="RS256",
                          headers={"kid": "test-key", "typ": "at+jwt", **(headers or {})})

    def settings(self, database_url="postgresql://unused.invalid/test", **changes):
        from apps.api.config import Settings
        return Settings(database_url=database_url, issuer=ISSUER, audience=AUDIENCE,
                        jwks_path=str(self.jwks_path), **changes)


class TokenVerificationTests(SignedIdentityFixture, unittest.TestCase):
    def verifier(self):
        from apps.api.auth import TokenVerifier
        return TokenVerifier(self.settings())

    def test_valid_signature_returns_stable_owner_and_other_subject_differs(self):
        verifier = self.verifier()
        alice = verifier.verify(self.token())
        self.assertTrue(alice)
        self.assertEqual(alice, verifier.verify(self.token()))
        self.assertNotEqual(alice, verifier.verify(self.token("bob")))

    def test_same_subject_at_different_issuer_maps_to_different_owner(self):
        from apps.api.auth import TokenVerifier, derive_owner
        first = self.verifier().verify(self.token())
        alternate = "https://second-identity.example.test"
        second_verifier = TokenVerifier(replace(self.settings(), issuer=alternate))
        second = second_verifier.verify(self.token(changes={"iss": alternate}))
        self.assertEqual(derive_owner(ISSUER, "alice"), first)
        self.assertNotEqual(first, second)

    def test_equivalent_access_token_type_and_audience_list_are_supported(self):
        owner = self.verifier().verify(self.token())
        self.assertEqual(owner, self.verifier().verify(self.token(headers={"typ": "application/at+jwt"})))
        self.assertEqual(owner, self.verifier().verify(self.token(changes={"aud": ["other-api", AUDIENCE]})))

    def test_signature_claim_and_token_type_failures_are_rejected(self):
        now = int(time.time())
        invalid_tokens = {
            "wrong_signature": self.token(key=self.wrong_key),
            "wrong_issuer": self.token(changes={"iss": "https://attacker.example.test"}),
            "wrong_audience": self.token(changes={"aud": "another-api"}),
            "expired": self.token(changes={"exp": now - 300}),
            "future_not_before": self.token(changes={"nbf": now + 300}),
            "future_issued_at": self.token(changes={"iat": now + 300}),
            "empty_subject": self.token(subject=""),
            "integer_subject": self.token(changes={"sub": 123}),
            "invalid_expiry": self.token(changes={"exp": "not-a-time"}),
            "boolean_expiry": self.token(changes={"exp": True}),
            "string_expiry": self.token(changes={"exp": str(now + 300)}),
            "boolean_issued_at": self.token(changes={"iat": False}),
            "empty_client": self.token(changes={"client_id": ""}),
            "empty_token_id": self.token(changes={"jti": ""}),
            "unknown_key": self.token(headers={"kid": "untrusted-key"}),
            "id_token": self.token(headers={"typ": "JWT"}),
            "token_key_url": self.token(headers={"jku": "https://attacker.example.test/keys"}),
            "unknown_critical_header": self.token(headers={"crit": ["unsupported"], "unsupported": True}),
            "malformed": "not-a-jwt",
            "unsigned": jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "alice", "exp": now + 300}, key="", algorithm="none"),
            "symmetric_algorithm": jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "alice", "exp": now + 300}, key="a-test-secret-that-is-at-least-32-bytes", algorithm="HS256"),
        }
        for name, token in invalid_tokens.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                self.verifier().verify(token)

    def test_required_claims_cannot_be_missing(self):
        for claim in ("iss", "aud", "sub", "exp", "iat", "client_id", "jti"):
            with self.subTest(claim=claim), self.assertRaises(ValueError):
                self.verifier().verify(self.token(omit=(claim,)))

    def test_missing_invalid_or_duplicate_trusted_keys_fail_closed(self):
        documents = ({"keys": []}, {"keys": [self.public_jwk, self.public_jwk]},
                     {"keys": [{"kid": "test-key", "kty": "RSA", "n": "invalid", "e": "AQAB"}]})
        for document in documents:
            self.jwks_path.write_text(json.dumps(document))
            with self.subTest(document=document), self.assertRaises(ValueError):
                self.verifier()
        self.jwks_path.unlink()
        with self.assertRaises(ValueError):
            self.verifier()

    def test_required_settings_cannot_be_empty(self):
        from apps.api.app import create_app
        settings = self.settings()
        for field in ("database_url", "issuer", "audience", "jwks_path"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                create_app(replace(settings, **{field: ""}))


if __name__ == "__main__":
    unittest.main()
