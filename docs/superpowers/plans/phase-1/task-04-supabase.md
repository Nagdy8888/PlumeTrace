# Phase 1 · Task 4 — Local Supabase, first migration and DB pool

**Read first:** design §10.1, `CLAUDE.md` rule 19. **Skills:** `plan-execution`, `supabase:supabase`, `supabase:supabase-postgres-best-practices`, `security-checks`, `project-documentation`.

**Goal:** a local Supabase Postgres (Docker) with schema `plumetrace`, the `scenarios` table with
RLS, the three MVP scenario rows, a connection-pool factory, and tests that prove RLS is on.

**Precondition:** Docker Desktop is running (`docker info` succeeds). If not, STOP and ask the owner.

## Files
| Action | Path |
|---|---|
| Create (CLI) | `app/supabase/config.toml`, `app/supabase/.gitignore` (both from `supabase init`) |
| Create | `app/supabase/migrations/20261113090000_create_plumetrace_schema.sql`, `app/supabase/seed.sql` |
| Create | `app/backend/plumetrace/db/__init__.py`, `app/backend/plumetrace/db/pool.py` |
| Create | `app/backend/tests/test_db_pool.py`, `app/backend/tests/db/conftest.py`, `app/backend/tests/db/test_schema.py` |
| Create | `docs/reference/DATABASE.md`; modify `docs/LOCAL_DEVELOPMENT.md` → `## Database`, `docs/README.md` (add DATABASE.md row) |

## Exact file contents

`app/supabase/migrations/20261113090000_create_plumetrace_schema.sql`:
```sql
-- Migration: create the plumetrace schema and the scenarios catalogue.
-- Date: 2026-11-13. Design: docs/superpowers/specs/2026-11-12-plumetrace-design.md section 10.1.
-- Rules: RLS on every table, no anon/authenticated policies (only the backend, as the database
-- owner, reads and writes). Never edit this file after it has been applied; add a new migration.

create schema if not exists plumetrace;

create table plumetrace.scenarios (
    id          text        primary key check (id ~ '^s[0-9]+_[a-z0-9_]+$'),
    title       text        not null,
    seed        bigint      not null,
    version     integer     not null default 1,
    is_mvp      boolean     not null,
    created_at  timestamptz not null default now()
);

comment on table plumetrace.scenarios is 'Scenario catalogue (S1-S6). Seeded; read by the backend.';

alter table plumetrace.scenarios enable row level security;
```

`app/supabase/seed.sql`:
```sql
-- Seed data: reference rows only (no secrets, no personal data).
insert into plumetrace.scenarios (id, title, seed, version, is_mvp) values
    ('s1_rod_packing',      'Rod packing failure, K-202',         101, 1, true),
    ('s4_planned_blowdown', 'Planned blowdown, compressor K-201', 104, 1, true),
    ('s5_sensor_drift',     'Sensor drift, AT-106',               105, 1, true)
on conflict (id) do nothing;
```

`app/backend/plumetrace/db/__init__.py`:
```python
"""Database access for PlumeTrace (local Supabase Postgres).

Only this package and the injected LangGraph checkpointer touch the database. Queries are
parameterised; schema changes happen only through migrations in ``app/supabase/migrations``.
"""
```

`app/backend/plumetrace/db/pool.py` — interface (write Google docstrings):
- `def create_pool(settings: Settings, *, min_size: int = 1, max_size: int = 5) -> ConnectionPool`
  - gets the URL with `require_db_url(settings)` (so a missing URL raises `ConfigurationError` before any connection attempt);
  - returns `psycopg_pool.ConnectionPool(conninfo=url, min_size=min_size, max_size=max_size, open=True)`;
  - imports: `from psycopg_pool import ConnectionPool`, `from plumetrace.config import Settings, require_db_url`.

## Tests (full code)

`app/backend/tests/test_db_pool.py`:
```python
"""Tests for plumetrace.db.pool that need no database."""

import pytest

from plumetrace.config import ConfigurationError, Settings
from plumetrace.db.pool import create_pool


def test_create_pool_without_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """No SUPABASE_DB_URL -> actionable ConfigurationError, no connection attempt."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(ConfigurationError, match="SUPABASE_DB_URL"):
        create_pool(Settings(_env_file=None))
```

`app/backend/tests/db/conftest.py`:
```python
"""Fixtures for tests that need the local Supabase Postgres.

Locally, the tests skip with a hint when the database is not running. In `python scripts/ci_local.py --full` the stage sets
PLUMETRACE_REQUIRE_DB=1, which turns the same condition into a failure.
"""

import os
from collections.abc import Iterator

import psycopg
import pytest

from plumetrace.config import ConfigurationError, get_settings, require_db_url

START_HINT = "Supabase not running: run `npx --yes supabase@3.1.0 start` in app/"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test in this folder with the `db` marker."""
    for item in items:
        if "tests/db/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.db)


@pytest.fixture
def db_conn() -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    """Yield a connection to the local database, or skip/fail when it is unavailable."""
    try:
        url = require_db_url(get_settings())
        conn = psycopg.connect(url, connect_timeout=3)
    except (ConfigurationError, psycopg.OperationalError) as exc:
        if os.environ.get("PLUMETRACE_REQUIRE_DB") == "1":
            pytest.fail(f"database required but unavailable: {exc}")
        pytest.skip(START_HINT)
    try:
        yield conn
    finally:
        conn.close()
```

`app/backend/tests/db/test_schema.py`:
```python
"""Schema tests against the local Supabase Postgres (design section 10.1)."""

import psycopg


def test_every_plumetrace_table_has_rls(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """RLS is enabled on every table in schema plumetrace."""
    rows = db_conn.execute(
        "select c.relname, c.relrowsecurity from pg_class c "
        "join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'plumetrace' and c.relkind = 'r'"
    ).fetchall()
    assert rows, "schema plumetrace has no tables"
    assert all(rls for _, rls in rows), rows


def test_no_client_policies_exist(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """No RLS policies are defined: only the backend (owner) accesses the tables."""
    count = db_conn.execute(
        "select count(*) from pg_policies where schemaname = 'plumetrace'"
    ).fetchone()
    assert count == (0,)


def test_mvp_scenarios_are_seeded(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The three MVP scenarios exist after migrations + seed."""
    ids = {r[0] for r in db_conn.execute("select id from plumetrace.scenarios").fetchall()}
    assert ids == {"s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"}
```

## Steps
- [ ] **1. Init Supabase** (from `app/`): `printf 'n\nn\n' | npx --yes supabase@3.1.0 init` (answers "no" to editor-settings prompts). Confirm `app/supabase/config.toml` exists. Do not edit `config.toml`.
- [ ] **2. Start it:** `npx --yes supabase@3.1.0 start`. It prints a "DB URL". Check it is `postgresql://postgres:postgres@127.0.0.1:54322/postgres` (the public local default, which is already the value of `SUPABASE_DB_URL` in the root `.env`). If the printed URL differs, STOP and ask the owner. Never open `.env`; any `.env` change goes through `python -I .claude/skills/security-checks/scripts/env_set.py` (CLAUDE.md rule 9).
- [ ] **3. Write the tests** above. Run `uv run pytest -q` → `test_db_pool.py` fails (module missing); DB tests fail (no table).
- [ ] **4. Write the migration, seed and `db` package** exactly as above. Apply: `npx --yes supabase@3.1.0 db reset` (rebuilds the local DB from migrations + seed; the local DB has no other data).
- [ ] **5. Run** `uv run pytest -q` → all pass (13 total). `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean.
- [ ] **6. Prove the skip/fail behaviour:** `npx --yes supabase@3.1.0 stop` → `uv run pytest -q` shows 3 skipped DB tests; then (bash) `PLUMETRACE_REQUIRE_DB=1 uv run pytest -q backend/tests/db` → fails with "database required but unavailable". Start again: `npx --yes supabase@3.1.0 start`. Paste the three outputs.
- [ ] **7. Repo checks** pass.
- [ ] **8. Docs.**
  - `docs/reference/DATABASE.md`: purpose; connection (backend only, direct Postgres URL from `.env`); schema `plumetrace`; table `scenarios` with every column, type and meaning; RLS stance (enabled, no policies, why); migrations list (file + purpose); how to reset (`db reset`), start, stop; checkpoint tables note ("created by LangGraph PostgresSaver in Phase 5").
  - `docs/LOCAL_DEVELOPMENT.md` → `## Database`: start/stop/reset commands, the local URL, "Docker must be running", how DB tests skip/fail.
  - `docs/README.md`: add the DATABASE.md row. Work-log row; `STATUS.md` (last 1.4, next 1.5).
- [ ] **9. Commit** `feat(db): add local Supabase with plumetrace schema and scenarios table` (include `app/supabase/` except anything its own `.gitignore` excludes).
