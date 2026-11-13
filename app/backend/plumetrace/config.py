"""Application settings, loaded only from the single repo-root ``.env`` or the process environment.

CLAUDE.md rule 9: one ``.env`` at the repository root holds every secret and setting, and this
module is the only place Python reads it. Secret values are ``SecretStr``, so they never appear
in ``repr``/``str`` (logs, tracebacks); call ``get_secret_value()`` only where the value is used.

Tests construct ``Settings(_env_file=None)`` so they never read the real ``.env``.
"""

import functools
from pathlib import Path
from typing import Final

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
ENV_FILE: Final[Path] = REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Environment settings; each field is read from the upper-case variable of the same name.

    Attributes:
        openai_api_key: OpenAI API key (secret).
        langsmith_api_key: LangSmith API key (secret).
        langsmith_tracing: Whether LangSmith tracing is on.
        langsmith_project: LangSmith project name for traced runs.
        supabase_db_url: Postgres connection string of the local Supabase (secret).
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    openai_api_key: SecretStr | None = None
    langsmith_api_key: SecretStr | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "plumetrace-dev"
    supabase_db_url: SecretStr | None = None


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing."""


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them on first use.

    Returns:
        The cached ``Settings`` instance.
    """
    return Settings()


def require_db_url(settings: Settings) -> str:
    """Return the database URL as a plain string for the DB driver.

    Args:
        settings: The settings to read ``supabase_db_url`` from.

    Returns:
        The connection string.

    Raises:
        ConfigurationError: If ``SUPABASE_DB_URL`` is not set.
    """
    if settings.supabase_db_url is None:
        raise ConfigurationError(
            "SUPABASE_DB_URL is not set: run npx --yes supabase@3.1.0 start in app/ "
            "and add it to the root .env"
        )
    return settings.supabase_db_url.get_secret_value()
