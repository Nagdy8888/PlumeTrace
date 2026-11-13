# Phase 5 · Task 9b — Backend logs into Supabase (`plumetrace.app_logs`), redaction, request log

**Skills:** `plan-execution`, `fastapi`, `security-checks` (no secrets in logs), `backend-design:observability-by-default`, `project-documentation`.
**Docs to check first (Context7 / Python docs):** FastAPI 0.162.5 lifespan (`@asynccontextmanager async def lifespan(app)`, `FastAPI(lifespan=...)`) and HTTP middleware (`@app.middleware("http")`); Python 3.12 `logging.handlers.QueueHandler` / `QueueListener` (`respect_handler_level`), `logging.Handler.handleError`.

**Why (owner decision 2026-11-13):** everything the app runs is stored in local Supabase. Agent
steps, LLM calls, eval results and checkpoints have their own tables; this task stores the
**backend log records** too, so a run can be investigated from the database alone.

## Fixed decisions
- Logs go to the database through a **queue**: the request or agent thread only puts the record on
  a `queue.SimpleQueue`; one `QueueListener` thread writes it. A slow or failing database never
  blocks or breaks a request or a run.
- Every message and every formatted traceback is **redacted** before it is stored or printed:
  secret-like substrings become `[redacted]`. The redaction runs inside the writer, so no caller can
  forget it.
- Stored level: `INFO` and above for loggers under `plumetrace` (the app) and `plumetrace.http`
  (request log). Third-party loggers are not stored (they still print to the console as before).
- The request log stores method, **path only** (never the query string, headers or bodies), status
  code and duration. `/api/health` is logged too (it is cheap and shows liveness).
- No DB URL in settings → no database logging (console only); one console line says
  `database logging disabled: SUPABASE_DB_URL is not set` (name only).
- A failure inside the writer goes to `logging.Handler.handleError` (stderr) — never back into the
  logger (no recursion).

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/api/redact.py` |
| Create | `app/backend/plumetrace/api/db_logging.py` |
| Create | `app/backend/plumetrace/api/request_log.py` |
| Modify | `app/backend/plumetrace/api/main.py` → add the lifespan (logs part) and the request-log middleware |
| Create (tests) | `app/backend/tests/api/test_redact.py`, `app/backend/tests/api/test_db_logging.py`, `app/backend/tests/api/test_request_log.py` |
| Modify | `docs/reference/DATABASE.md` (`app_logs` usage), `docs/reference/API.md` ("Logging"), `docs/reference/SECURITY.md` ("Logs and redaction") |

## Interfaces
`api/redact.py`:
- `SECRET_PATTERNS: Final[tuple[re.Pattern[str], ...]]` — `sk-[A-Za-z0-9_-]{16,}`, `lsv2_[A-Za-z0-9_]{16,}`, `postgres(?:ql)?://\S+`, `Bearer\s+[A-Za-z0-9._-]{16,}`, `(?i)(api[_-]?key|password|secret|token)\s*[=:]\s*\S+`.
- `REDACTED: Final = "[redacted]"`
- `def redact(text: str) -> str` — every match of every pattern → `REDACTED`.

`api/db_logging.py`:
- `STORED_LOGGERS: Final = ("plumetrace",)` (covers `plumetrace.http` and every `plumetrace.*` module logger).
- `MAX_MESSAGE_CHARS: Final = 4000`
- `class DbLogWriter(logging.Handler)` — `__init__(self, pool: ConnectionPool)`; `emit(record)`: `message = redact(record.getMessage())[:MAX_MESSAGE_CHARS]`; `context = {"module": record.module, "lineno": record.lineno}` plus, when `record.exc_info`, `"exc_type": <class name>` and `"traceback": redact(<formatted traceback>)[:MAX_MESSAGE_CHARS]`; `run_id = getattr(record, "run_id", None)` (callers pass `extra={"run_id": run_id}`; a value that is not a valid UUID is moved into `context["run_id_text"]` and stored as `None`); `with pool.connection() as conn: app_logs.insert_log(conn, level=record.levelname, logger=record.name, message=message, run_id=run_id, context=context)`; any exception → `self.handleError(record)`.
- `def install_db_logging(pool: ConnectionPool) -> QueueListener` — creates `queue.SimpleQueue()`, a `QueueHandler(q)` with level `INFO` added to `logging.getLogger("plumetrace")` (logger level set to `INFO`; `propagate` unchanged, so console output stays), and `QueueListener(q, DbLogWriter(pool), respect_handler_level=True)`; starts and returns the listener.
- `def uninstall_db_logging(listener: QueueListener) -> None` — `listener.stop()` (flushes the queue), removes the `QueueHandler` from the `plumetrace` logger.

`api/request_log.py`:
- `logger = logging.getLogger("plumetrace.http")`
- `async def log_requests(request: Request, call_next) -> Response` — `t0 = time.perf_counter()`; `response = await call_next(request)`; `logger.info("%s %s %d %.0f ms", request.method, request.url.path, response.status_code, ms)`; an exception from `call_next` → `logger.exception("%s %s failed", method, path)` then re-raise.

`api/main.py`:
- `@asynccontextmanager async def lifespan(app: FastAPI)` — `settings = get_settings()`; if `settings.supabase_db_url` is set: `app.state.log_pool = create_pool(settings, min_size=1, max_size=2)`, `app.state.log_listener = install_db_logging(app.state.log_pool)`; else both `None` and the one console line above. `yield`. On shutdown: `uninstall_db_logging` then `log_pool.close()` (each only when set). Task 10 extends this same function — keep it in `main.py`, ≤ 50 lines; if Task 10 would push it over, move the agent part into `api/agent_lifespan.py` there.
- `create_app()` passes `lifespan=lifespan` and registers `app.middleware("http")(log_requests)` **before** the CORS middleware is added (so CORS stays the outermost layer).

## Tests (full code)
`app/backend/tests/api/test_redact.py`:
```python
"""Secret-like values never reach a log line."""

from plumetrace.api.redact import REDACTED, redact


def test_keys_urls_and_assignments_are_redacted() -> None:
    """Each pattern is replaced; normal text is kept."""
    text = ("key sk-" + "a" * 24 + " url postgresql://u:p@127.0.0.1:54322/postgres "
            "auth Bearer " + "b" * 20 + " OPENAI_API_KEY=abc123 ok")
    out = redact(text)
    assert "sk-" not in out and "postgresql://" not in out and "abc123" not in out
    assert out.count(REDACTED) == 4 and out.endswith(" ok")


def test_plain_text_is_unchanged() -> None:
    """A normal log message passes through."""
    assert redact("run started for s1_rod_packing") == "run started for s1_rod_packing"
```

`app/backend/tests/api/test_db_logging.py` (DB fixture rules as in Phase 1: skipped without a DB unless `PLUMETRACE_REQUIRE_DB=1`):
```python
"""Log records reach plumetrace.app_logs through the queue, redacted."""

import logging
import uuid

import psycopg
from psycopg_pool import ConnectionPool

from plumetrace.api.db_logging import install_db_logging, uninstall_db_logging
from plumetrace.config import get_settings
from plumetrace.db import app_logs
from plumetrace.db.pool import create_pool


def test_record_is_stored_with_run_id_and_redaction(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """An app log line with extra run_id is written once, without the secret."""
    pool: ConnectionPool = create_pool(get_settings(), min_size=1, max_size=1)
    listener = install_db_logging(pool)
    run_id = uuid.uuid4()
    try:
        logging.getLogger("plumetrace.test").warning(
            "probe %s", "sk-" + "z" * 20, extra={"run_id": str(run_id)})
    finally:
        uninstall_db_logging(listener)
        pool.close()
    rows = app_logs.list_logs(db_conn, run_id=run_id, min_level="INFO")
    assert len(rows) == 1
    assert rows[0]["message"] == "probe [redacted]" and rows[0]["level"] == "WARNING"


def test_third_party_loggers_are_not_stored(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Only plumetrace.* loggers are written to the database."""
    pool: ConnectionPool = create_pool(get_settings(), min_size=1, max_size=1)
    listener = install_db_logging(pool)
    run_id = uuid.uuid4()
    try:
        logging.getLogger("httpx").warning("outside", extra={"run_id": str(run_id)})
    finally:
        uninstall_db_logging(listener)
        pool.close()
    assert app_logs.list_logs(db_conn, run_id=run_id) == []
```
(`db_conn` and the stored rows are on the same local database; the listener commits through the pool's own connection, so `db_conn` sees the rows. The rows stay in `app_logs` — **no clean-up delete**: logs are append-only (Phase 6 Task 5 revokes `delete` from the backend role). Each test filters by its own fresh `uuid4()` run id, so leftovers never collide.)

`app/backend/tests/api/test_request_log.py` (no DB; `caplog`):
```python
"""Every request produces one log line with path, status and duration, never the query."""

import logging

import pytest
from fastapi.testclient import TestClient

from plumetrace.api.main import create_app


def test_request_line_has_no_query_string(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/health?token=x logs the path only."""
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    caplog.set_level(logging.INFO, logger="plumetrace.http")
    with TestClient(create_app()) as client:
        assert client.get("/api/health?token=abc").status_code == 200
    lines = [r.getMessage() for r in caplog.records if r.name == "plumetrace.http"]
    assert len(lines) == 1 and lines[0].startswith("GET /api/health 200 ")
    assert "token" not in lines[0]
```
(If `get_settings()` is cached with `lru_cache` (Phase 1 Task 3), call `get_settings.cache_clear()` after the `delenv` and in teardown — check the Phase 1 code.)

## Steps
- [ ] Tests → FAIL → implement → `PLUMETRACE_REQUIRE_DB=1 uv run pytest app/backend -q` green (local Supabase running); ruff + mypy clean.
- [ ] Manual check: start the backend with the DB, `curl http://127.0.0.1:8000/api/scenarios`, then `select level, logger, message from plumetrace.app_logs order by log_id desc limit 5;` through `npx --yes supabase@3.1.0 db` tooling or `psql` from the local Supabase container — the request line is there. Record the output (no connection string) in the work log.
- [ ] `security-checks`: secret scan; confirm no log call in `plumetrace` formats a `SecretStr` value or `.env` value (`grep -rn "get_secret_value" app/backend/plumetrace` — every hit is outside a log call).
- [ ] Repo checks (structure, secrets, env).
- [ ] **Docs.** API.md → "Logging" (what is stored, levels, request line format, path only, queue, redaction, how to query `app_logs`); SECURITY.md → "Logs and redaction" (patterns, why in the writer); DATABASE.md → `app_logs` usage. Work-log; `STATUS.md` (last 5.9b, next 5.10).
- [ ] **Commit** `feat(api): store backend logs in Supabase with redaction and a request log`.
