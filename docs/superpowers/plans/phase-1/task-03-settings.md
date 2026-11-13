# Phase 1 · Task 3 — Settings from the single root `.env`

**Read first:** `CLAUDE.md` rule 9, `phase-1/README.md`. **Skills:** `plan-execution`, `security-checks`, `project-documentation`.

**Goal:** one settings object, loaded only from the repo-root `.env` or the process environment,
that never reveals secret values, and a helper that fails clearly when the database URL is missing.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/config.py` |
| Create | `app/backend/tests/test_config.py` |
| Modify | `docs/LOCAL_DEVELOPMENT.md` → `## Configuration` |

## Interface (exact names)
`plumetrace/config.py` must define:
- `REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]` (config.py → plumetrace → backend → app → repo root)
- `ENV_FILE: Final[Path] = REPO_ROOT / ".env"`
- `class Settings(BaseSettings)`:
  - `model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")`
  - fields (env var name = upper-case field name): `openai_api_key: SecretStr | None = None`, `langsmith_api_key: SecretStr | None = None`, `langsmith_tracing: bool = False`, `langsmith_project: str = "plumetrace-dev"`, `supabase_db_url: SecretStr | None = None`
- `class ConfigurationError(RuntimeError)` — docstring: raised when required configuration is missing.
- `def get_settings() -> Settings` decorated with `@functools.lru_cache(maxsize=1)`.
- `def require_db_url(settings: Settings) -> str` — returns `settings.supabase_db_url.get_secret_value()`; if it is `None` raises `ConfigurationError("SUPABASE_DB_URL is not set: run npx --yes supabase@3.1.0 start in app/ and add it to the root .env")`.

Module docstring: explain the single-`.env` rule (CLAUDE.md rule 9), that values are `SecretStr`,
and that tests construct `Settings(_env_file=None)` so they never read the real `.env`.

## Tests (full code) — `app/backend/tests/test_config.py`
```python
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
    """Environment variables override defaults (a shell or the check runner can provide them without a .env)."""
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
```

## Steps
- [ ] **1.** Write the test file. **2.** `uv run pytest backend/tests/test_config.py -q` → fails with `ModuleNotFoundError: No module named 'plumetrace.config'`.
- [ ] **3.** Implement `config.py` exactly per the Interface (Google docstrings on every object).
- [ ] **4.** `uv run pytest -q` → all pass (9 total); `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean.
- [ ] **5.** Repo checks pass (`structure OK`, `env OK`, `no secrets found`).
- [ ] **6. Docs.** `docs/LOCAL_DEVELOPMENT.md` → `## Configuration`: list the five variable **names** with one-line meaning each, state "only the root `.env` is read; never create other `.env` files; values are never printed". Work-log row; `STATUS.md` (last 1.3, next 1.4).
- [ ] **7. Commit** `feat(config): load settings from the single root .env`.
