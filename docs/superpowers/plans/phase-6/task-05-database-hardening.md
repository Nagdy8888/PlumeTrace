# Phase 6 · Task 5 — Database hardening: least-privilege role, append-only records, timeouts

**Skills:** `plan-execution`, `supabase:supabase-postgres-best-practices`, `backend-design:migration-safety`, `security-checks` (§H), `project-documentation`.
**Docs to check first:** PostgreSQL 17 `CREATE ROLE`, `GRANT`, `ALTER DEFAULT PRIVILEGES`, `ALTER ROLE … SET`; Supabase CLI 3.1.0 `db lint`; langgraph-checkpoint-postgres 3.2.0 `setup()` (which statements it runs when the tables already exist).

## Fixed decisions
- The backend stops connecting as the superuser `postgres`. A new role **`plumetrace_app`** gets only: `usage` on schemas `plumetrace` and `langgraph`; `create` on `langgraph` (the checkpointer creates its tables); table rights below; nothing on `auth`, `storage`, `public`, `extensions` or any Supabase schema.
- **Append-only tables** (tamper resistance for the approval record, the spend ledger and the logs): `decisions`, `llm_calls`, `app_logs`, `eval_results` → `select, insert` only. Every other `plumetrace` table → `select, insert, update, delete`.
- Role settings: `statement_timeout = '5s'`, `lock_timeout = '2s'`, `idle_in_transaction_session_timeout = '30s'`, `connection limit 20`.
- The migration creates the role **`nologin` without a password**. The **executor** then runs `scripts/set_app_role_password.py`: it generates a random password, gives the role a login with it, and writes the new `SUPABASE_DB_URL` into the root `.env` through `env_set.write_value` (owner decision 2026-11-13: the executor may change `.env`, only through `env_set.py`). Nobody sees or types the password; it is never printed. Migrations keep running as `postgres` through the Supabase CLI.
- Default privileges make tables created by later migrations follow the same rule (owner `postgres` grants `select, insert, update, delete` to `plumetrace_app`); a later append-only table must revoke `update, delete` in its own migration.

## Files
| Action | Path |
|---|---|
| Create | `app/supabase/migrations/20261210090000_create_app_role.sql` |
| Create | `scripts/set_app_role_password.py` (full code below) |
| Create (tests) | `app/backend/tests/db/test_app_role.py`, `app/backend/tests/test_set_app_role_password.py` (full code below) |
| Modify | `docs/SETUP.md` ("After `db reset`: run `scripts/set_app_role_password.py`"), `docs/reference/DATABASE.md` ("Roles and grants"), `docs/reference/SECURITY.md` |
| Check | `grep -rn "delete from plumetrace\.\(decisions\|llm_calls\|app_logs\|eval_results\)" app/backend/tests app/agents/tests` → no hits (tests never delete from append-only tables) |

## Migration (exact)
```sql
-- Migration: least-privilege role for the backend; append-only audit tables; timeouts.
-- Date: 2026-12-10. Phase 6 Task 5. The owner sets the login password outside migrations.

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'plumetrace_app') then
        create role plumetrace_app nologin noinherit nocreatedb nocreaterole noreplication nobypassrls;
    end if;
end
$$;

alter role plumetrace_app connection limit 20;
alter role plumetrace_app set statement_timeout = '5s';
alter role plumetrace_app set lock_timeout = '2s';
alter role plumetrace_app set idle_in_transaction_session_timeout = '30s';
alter role plumetrace_app set search_path = plumetrace, langgraph;

grant usage on schema plumetrace to plumetrace_app;
grant usage, create on schema langgraph to plumetrace_app;

grant select, insert, update, delete on all tables in schema plumetrace to plumetrace_app;
revoke update, delete on plumetrace.decisions, plumetrace.llm_calls, plumetrace.app_logs,
    plumetrace.eval_results from plumetrace_app;
grant usage, select on all sequences in schema plumetrace to plumetrace_app;

grant select, insert, update, delete on all tables in schema langgraph to plumetrace_app;
grant usage, select on all sequences in schema langgraph to plumetrace_app;

alter default privileges for role postgres in schema plumetrace
    grant select, insert, update, delete on tables to plumetrace_app;
alter default privileges for role postgres in schema plumetrace
    grant usage, select on sequences to plumetrace_app;
alter default privileges for role postgres in schema langgraph
    grant select, insert, update, delete on tables to plumetrace_app;

-- RLS stays enabled with no policies: plumetrace_app needs a policy to see rows.
-- One permissive policy per table for this role only (anon/authenticated still get nothing).
do $$
declare t record;
begin
    for t in select tablename from pg_tables where schemaname = 'plumetrace' loop
        execute format('create policy %I on plumetrace.%I for all to plumetrace_app using (true) with check (true)',
                       'app_all_' || t.tablename, t.tablename);
    end loop;
end
$$;

comment on role plumetrace_app is 'PlumeTrace backend: table rights only; append-only audit tables; 5 s statements.';
```
(Why the policies: RLS is enabled on every table and the earlier design relied on the superuser bypassing it. A non-superuser without `bypassrls` sees no rows unless a policy allows it. The policies are scoped `to plumetrace_app` only. Phase 1's test `test_no_client_policies_exist` checks policies for `anon`/`authenticated` — it must keep passing; if it counts **all** policies, change it to count only policies whose roles include `anon` or `authenticated`, and say so in the work log.)

## Switching the backend to the app role (executor steps, no owner action)
1. `cd app && npx --yes supabase@3.1.0 db reset` (applies the migration).
2. `cd app && uv run python ../scripts/set_app_role_password.py` → prints
   `plumetrace_app has a new password; SUPABASE_DB_URL updated in .env (value not shown)`.
   `refused: ...` → local Supabase is not running or the migration is missing; fix and rerun.
3. `python -I .claude/skills/security-checks/scripts/check_env.py .` → `env OK`.
4. After **any** later `db reset`, if the backend reports
   `password authentication failed for user "plumetrace_app"`, rerun step 2 (it rotates the
   password and rewrites the URL). Write this in `docs/SETUP.md`.

Never read `.env`, never print the URL, never pass the password on a command line.

## Script (full code) — `scripts/set_app_role_password.py`
```python
"""Give the backend database role a new random password and point SUPABASE_DB_URL at it.

Run with local Supabase running, after the role migration is applied and after every
``supabase db reset``:

    cd app && uv run python ../scripts/set_app_role_password.py

It connects as ``postgres`` through the public Supabase CLI local default URL, runs
``alter role plumetrace_app login password ...`` with a fresh ``secrets.token_urlsafe(32)``
value, and writes ``SUPABASE_DB_URL`` for ``plumetrace_app`` into the root ``.env`` through
``env_set.write_value``. The password and the URL are never printed, logged or passed on a
command line; nobody needs to know them.
"""

from __future__ import annotations

import importlib.util
import secrets
import sys
from pathlib import Path
from types import ModuleType

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
ENV_SET = ROOT / ".claude" / "skills" / "security-checks" / "scripts" / "env_set.py"
ADMIN_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"  # public local default
APP_ROLE = "plumetrace_app"
APP_HOST = "127.0.0.1:54322/postgres"


def load_env_set() -> ModuleType:
    """Load the ``env_set`` script as a module.

    Returns:
        ModuleType: The loaded ``env_set`` module.
    """
    spec = importlib.util.spec_from_file_location("env_set", ENV_SET)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ENV_SET}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["env_set"] = module
    spec.loader.exec_module(module)
    return module


def app_url(password: str) -> str:
    """Build the backend connection URL for the app role.

    Args:
        password: URL-safe password (``secrets.token_urlsafe`` output needs no escaping).

    Returns:
        str: ``postgresql://plumetrace_app:<password>@127.0.0.1:54322/postgres``.
    """
    return f"postgresql://{APP_ROLE}:{password}@{APP_HOST}"


def role_password_statement(password: str) -> sql.Composed:
    """Build ``alter role plumetrace_app login password '<password>'`` safely quoted.

    Args:
        password: New password, sent as a quoted SQL literal.

    Returns:
        sql.Composed: The statement (role as an identifier, password as a literal).
    """
    return sql.SQL("alter role {} login password {}").format(
        sql.Identifier(APP_ROLE), sql.Literal(password)
    )


def set_role_password(admin_url: str, password: str) -> None:
    """Enable login for the app role with the given password.

    Args:
        admin_url: Superuser URL of the local database.
        password: New password.
    """
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(role_password_statement(password))


def main(root: Path = ROOT) -> int:
    """Rotate the app role password and store the new URL in ``root/.env``.

    Args:
        root: Repository root holding ``.env`` and ``.env.example``.

    Returns:
        int: 0 on success, 1 when the database refused (``.env`` is then unchanged).
    """
    password = secrets.token_urlsafe(32)
    try:
        set_role_password(ADMIN_URL, password)
    except psycopg.Error as error:
        print(
            f"refused: could not set the {APP_ROLE} password ({type(error).__name__}); "
            "is local Supabase running and the role migration applied?"
        )
        return 1
    load_env_set().write_value(root, "SUPABASE_DB_URL", app_url(password))
    print(f"{APP_ROLE} has a new password; SUPABASE_DB_URL updated in .env (value not shown)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Script test (full code) — `app/backend/tests/test_set_app_role_password.py` (no DB)
```python
"""The role-password script writes the new URL to .env and never prints the password."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import psycopg
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "set_app_role_password.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("set_app_role_password", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["set_app_role_password"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A fake repo root with a superuser URL in .env and the name in .env.example."""
    (tmp_path / ".env").write_text(
        "LANGSMITH_PROJECT=plumetrace-test\nSUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("LANGSMITH_PROJECT=\nSUPABASE_DB_URL=\n", encoding="utf-8")
    return tmp_path


def test_new_url_is_written_and_password_is_not_printed(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The role gets the password that ends up in SUPABASE_DB_URL; stdout holds neither."""
    script = _load()
    seen: list[str] = []
    monkeypatch.setattr(script, "set_role_password", lambda _url, password: seen.append(password))
    assert script.main(repo) == 0
    env = (repo / ".env").read_text(encoding="utf-8")
    assert len(seen) == 1 and len(seen[0]) >= 43
    assert (
        f"SUPABASE_DB_URL=postgresql://plumetrace_app:{seen[0]}@127.0.0.1:54322/postgres\n" in env
    )
    assert "LANGSMITH_PROJECT=plumetrace-test\n" in env and env.count("SUPABASE_DB_URL=") == 1
    out = capsys.readouterr().out
    assert seen[0] not in out and "postgresql://" not in out


def test_database_error_leaves_env_unchanged(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refused ALTER ROLE exits 1 and keeps the old URL."""
    script = _load()
    before = (repo / ".env").read_bytes()

    def refuse(_url: str, _password: str) -> None:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(script, "set_role_password", refuse)
    assert script.main(repo) == 1
    assert (repo / ".env").read_bytes() == before
    assert "OperationalError" in capsys.readouterr().out


def test_password_is_sent_as_a_quoted_literal() -> None:
    """The statement quotes the role as an identifier and the password as a literal."""
    statement = _load().role_password_statement("a'b")
    assert statement.as_string() == "alter role \"plumetrace_app\" login password 'a''b'"
```
(`parents[3]` = repo root, as in `test_ci_local.py`. The DB side is proven by `test_app_role.py`: the whole suite then runs as `plumetrace_app`.)

## Tests (full code) — `app/backend/tests/db/test_app_role.py`
```python
"""The backend's database role has table rights only, append-only audit tables and timeouts."""

import psycopg
import pytest

APPEND_ONLY = ("decisions", "llm_calls", "app_logs", "eval_results")


def test_backend_is_not_a_superuser(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """SUPABASE_DB_URL uses plumetrace_app, not postgres."""
    user, superuser = db_conn.execute(
        "select current_user, rolsuper from pg_roles where rolname = current_user").fetchone()
    if user != "plumetrace_app":
        pytest.fail("SUPABASE_DB_URL still uses a superuser; run scripts/set_app_role_password.py")
    assert superuser is False


def test_schema_changes_are_refused(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """No DDL on the plumetrace schema."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db_conn.execute("create table plumetrace.evil (x int)")
    db_conn.rollback()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db_conn.execute("drop table plumetrace.runs")


def test_supabase_internals_are_not_readable(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """auth.users is out of reach."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db_conn.execute("select count(*) from auth.users")


@pytest.mark.parametrize("table", APPEND_ONLY)
def test_audit_tables_are_append_only(db_conn: psycopg.Connection[tuple[object, ...]], table: str) -> None:
    """update and delete are refused on the audit tables."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db_conn.execute(f"delete from plumetrace.{table}")  # noqa: S608 - fixed table names


def test_statements_are_time_limited(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """A statement over 5 s is cancelled."""
    assert db_conn.execute("show statement_timeout").fetchone() == ("5s",)
    with pytest.raises(psycopg.errors.QueryCanceled):
        db_conn.execute("select pg_sleep(6)")
```

## Steps
- [ ] Script test → FAIL → write the script → green. Tests → FAIL (still the superuser) → write the migration → executor steps 1–3 → `PLUMETRACE_REQUIRE_DB=1 uv run pytest app/backend app/agents -q` green **as `plumetrace_app`**. A test that now fails because it updates or deletes an append-only table, or runs DDL: that test is wrong for the product's rules — report it to the owner with the test name; do not grant more.
- [ ] Start the backend; one fake-LLM run through `tests/api/test_runs_api.py` passes; the checkpointer's `setup()` succeeds as the app role (if it needs a right not granted, STOP and report the exact error).
- [ ] `cd app && npx --yes supabase@3.1.0 db lint --level warning` → record the output; every finding fixed in a new migration or accepted in SECURITY.md with the owner.
- [ ] `backend-design:schema-reviewer` on the migration; record findings.
- [ ] Repo checks.
- [ ] **Docs.** DATABASE.md → "Roles and grants" (table of rights per table, append-only list, policies, timeouts, why); SETUP.md (step 4 above); SECURITY.md → "Database"; THREAT_MODEL.md T11 confirmed. Work-log; `STATUS.md` (last 6.5, next 6.6).
- [ ] **Commit** `feat(db): add a least-privilege backend role with append-only audit tables`.
