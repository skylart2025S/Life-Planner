"""Verify signed access tokens against a trusted, local public-key set."""

from hashlib import sha256
import json
from pathlib import Path

import jwt

from apps.api.config import Settings


class InvalidToken(ValueError):
    """Authentication failed; deliberately carries no untrusted token details."""


def derive_owner(issuer: str, subject: str) -> str:
    identity = json.dumps([issuer, subject], ensure_ascii=True, separators=(",", ":"))
    return "oidc:" + sha256(identity.encode("utf-8")).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class TokenVerifier:
    """RS256-only user-access-token profile; keys reload only on restart."""

    def __init__(self, settings: Settings):
        self._issuer = settings.issuer
        self._audience = settings.audience
        self._keys = {}
        try:
            with Path(settings.jwks_path).open("rb") as source:
                content = source.read(1024 * 1024 + 1)
            if len(content) > 1024 * 1024:
                raise ValueError("JWKS too large")
            jwks = json.loads(content, object_pairs_hook=_unique_object)
            if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list) or not jwks["keys"]:
                raise ValueError("Keys are required")
            for value in jwks["keys"]:
                if not isinstance(value, dict):
                    raise ValueError("Invalid key")
                kid = value.get("kid")
                if not isinstance(kid, str) or not kid or len(kid) > 128 or kid in self._keys:
                    raise ValueError("Invalid key ID")
                if value.get("kty") != "RSA" or value.get("alg", "RS256") != "RS256":
                    raise ValueError("Unsupported key")
                if value.get("use", "sig") != "sig" or value.get("key_ops", ["verify"]) != ["verify"]:
                    raise ValueError("Key cannot verify signatures")
                if any(field in value for field in ("d", "p", "q", "dp", "dq", "qi", "oth")):
                    raise ValueError("Public keys only")
                key = jwt.PyJWK.from_dict(value, algorithm="RS256").key
                if key.key_size < 2048:
                    raise ValueError("RSA key is too small")
                self._keys[kid] = key
        except (OSError, ValueError, TypeError, KeyError, jwt.PyJWTError):
            raise ValueError("Invalid trusted JWKS configuration") from None

    def verify(self, token: str) -> str:
        try:
            if not isinstance(token, str) or not token or len(token) > 8192:
                raise ValueError("Invalid token size")
            # Reject duplicate JSON members rather than choosing one interpretation.
            segments = token.split(".")
            if len(segments) != 3:
                raise ValueError("Invalid token")
            header = json.loads(jwt.utils.base64url_decode(segments[0]), object_pairs_hook=_unique_object)
            json.loads(jwt.utils.base64url_decode(segments[1]), object_pairs_hook=_unique_object)
            if (not isinstance(header, dict) or header.get("alg") != "RS256"
                    or header.get("typ") not in ("at+jwt", "application/at+jwt")):
                raise ValueError("Invalid token profile")
            if any(name in header for name in ("jku", "x5u", "jwk", "x5c", "crit", "b64")):
                raise ValueError("Unsupported token header")
            kid = header.get("kid")
            if not isinstance(kid, str) or kid not in self._keys:
                raise ValueError("Unknown key")
            claims = jwt.decode(token, self._keys[kid], algorithms=["RS256"], issuer=self._issuer,
                                audience=self._audience, leeway=0,
                                options={"require": ["iss", "sub", "aud", "exp", "iat", "client_id", "jti"]})
            for name in ("iss", "sub", "client_id", "jti"):
                if not isinstance(claims[name], str) or not claims[name].strip():
                    raise ValueError("Invalid claim")
            for name in ("iat", "exp", "nbf"):
                if name in claims and (type(claims[name]) is not int or claims[name] < 0):
                    raise ValueError("Invalid numeric date")
            if claims["exp"] <= claims["iat"]:
                raise ValueError("Invalid lifetime")
            audience = claims["aud"]
            if not (isinstance(audience, str) and audience or
                    isinstance(audience, list) and audience and
                    all(isinstance(value, str) and value for value in audience)):
                raise ValueError("Invalid audience")
            return derive_owner(claims["iss"], claims["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
            raise InvalidToken("Invalid access token") from None
