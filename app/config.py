"""Environment configuration. Values are read from os.environ only.

Keys are referenced by name and never read into logs. `redacted_summary()`
exists so startup can prove wiring without exposing secret values (spec §2).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _require(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(f"{name} is not set. See .env.example.")
    return val


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    kv_url: str
    you_search_base_url: str
    you_research_base_url: str
    crew_model: str
    youcom_cache_ttl_seconds: int

    # Secret env var *names* — the values are read lazily by the clients that
    # need them and are never stored on this object.
    you_search_key_env: str = "YOU_SEARCH_API_KEY"
    you_research_key_env: str = "YOU_RESEARCH_API_KEY"
    anthropic_key_env: str = "ANTHROPIC_API_KEY"

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


def load_settings() -> Settings:
    return Settings(
        app_env=os.environ.get("APP_ENV", "development"),
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://csr:csr@localhost:5432/causes"
        ),
        kv_url=os.environ.get("KV_URL", "redis://localhost:6379/0"),
        you_search_base_url=os.environ.get(
            "YOU_SEARCH_BASE_URL", "https://ydc-index.io"
        ),
        you_research_base_url=os.environ.get(
            "YOU_RESEARCH_BASE_URL", "https://api.you.com"
        ),
        crew_model=os.environ.get("CREW_MODEL", "anthropic/claude-opus-4-8"),
        youcom_cache_ttl_seconds=int(os.environ.get("YOUCOM_CACHE_TTL_SECONDS", "21600")),
    )


settings = load_settings()
