"""Trusted startup configuration; no request may override these values."""

from dataclasses import dataclass
import os

from psycopg.conninfo import conninfo_to_dict, make_conninfo


@dataclass(frozen=True)
class Settings:
    database_url: str
    issuer: str
    audience: str
    jwks_path: str

    def __post_init__(self):
        for name in ("database_url", "issuer", "audience", "jwks_path"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"Missing or invalid configuration: {name}")
        # Validate syntax without connecting or including secrets in errors.
        try:
            conninfo_to_dict(self.database_url)
        except Exception:
            raise ValueError("Invalid database configuration") from None

    def service_dsn(self) -> str:
        options = conninfo_to_dict(self.database_url).get("options", "")
        return make_conninfo(self.database_url, connect_timeout=5,
                             options=f"{options} -c lock_timeout=2000 -c statement_timeout=5000".strip())

    @classmethod
    def from_env(cls):
        return cls(database_url=os.environ.get("DATABASE_URL", ""),
                   issuer=os.environ.get("AUTH_ISSUER", ""),
                   audience=os.environ.get("AUTH_AUDIENCE", ""),
                   jwks_path=os.environ.get("AUTH_JWKS_PATH", ""))
