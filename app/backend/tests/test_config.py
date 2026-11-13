"""Tests for plumetrace.config (single root .env, secrets never revealed)."""

import pytest

from plumetrace.config import (
    ENV_FILE,
    REPO_ROOT,
    ConfigurationError,
    Settings,
    require_db_url,
)

ENV_NAMES = [
    "OPENAI_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_PROJECT",
    "SUPABASE_DB_URL",
]


def test_settings_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fresh clone with no .env and no env vars loads safe defaults."""
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    s = Settings(_env_file=None)
    assert s.openai_api_key is None
    assert s.langsmith_api_key is None
    assert s.supabase_db_url is None
    assert s.langsmith_tracing is False
    assert s.langsmith_project == "plumetrace-dev"


def test_values_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables override defaults.

    A shell or the check runner can provide them without a .env.
    """
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_PROJECT", "plumetrace-ci")
    s = Settings(_env_file=None)
    assert s.langsmith_tracing is True
    assert s.langsmith_project == "plumetrace-ci"


def test_secrets_are_not_revealed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret values never appear in repr/str (logs, tracebacks)."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-value-for-tests")
    s = Settings(_env_file=None)
    assert "fake-openai-value-for-tests" not in repr(s)
    assert "fake-openai-value-for-tests" not in str(s)
    assert s.openai_api_key is not None
    assert s.openai_api_key.get_secret_value() == "fake-openai-value-for-tests"


def test_require_db_url_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing DB URL fails with an actionable message naming the variable."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(ConfigurationError, match="SUPABASE_DB_URL"):
        require_db_url(Settings(_env_file=None))


def test_require_db_url_returns_plain_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """When set, the URL is returned as a plain string for the DB driver."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@127.0.0.1:5432/db")
    assert require_db_url(Settings(_env_file=None)) == "postgresql://u:p@127.0.0.1:5432/db"


def test_env_file_points_at_repo_root() -> None:
    """The settings file is the single root .env, next to CLAUDE.md."""
    assert (REPO_ROOT / "CLAUDE.md").is_file()
    assert ENV_FILE == REPO_ROOT / ".env"
