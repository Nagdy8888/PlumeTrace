# Phase 5 · Task 8 — Migration: agent steps, drafts, decisions, work orders, reports, LLM-call ledger, app logs, eval results; checkpoint schema

**Skills:** `plan-execution`, `supabase:supabase-postgres-best-practices`, `backend-design:migration-safety`, `security-checks`, `project-documentation`.
**Rules:** CLAUDE.md rule 19 (new migration only, schema `plumetrace`, RLS on every table, only `plumetrace.db` touches the DB). The repositories take and return plain JSON (`dict`) for drafts and decisions — `plumetrace.db` does not import `plumetrace_agents`.

## Files
| Action | Path |
|---|---|
| Create | `app/supabase/migrations/20261127090000_create_agent_tables.sql` |
| Create | `app/backend/plumetrace/db/agent_steps.py`, `db/drafts.py`, `db/decisions.py`, `db/outputs.py`, `db/llm_calls.py`, `db/app_logs.py`, `db/eval_results.py` |
| Modify | `app/backend/plumetrace/db/runs.py` → `set_outcome(conn, run_id, outcome)` |
| Create (tests) | `app/backend/tests/db/test_agent_tables.py`, `app/backend/tests/db/test_ledger_logs.py` |
| Modify | `docs/reference/DATABASE.md` (every new table and column) |

## Migration (exact)
```sql
-- Migration: agent run records (steps, drafts, decisions, outputs), the LLM-call ledger, app logs,
-- eval results, and the LangGraph checkpoint schema.
-- Date: 2026-11-27. Design sections 6 and 10.1. RLS on, no policies (backend is the only client).

alter table plumetrace.runs
    add column outcome text check (outcome in ('approved', 'edited', 'escalated', 'logged', 'failed'));

create table plumetrace.agent_steps (
    step_id    bigint generated always as identity primary key,
    run_id     uuid   not null references plumetrace.runs (run_id) on delete cascade,
    seq        integer not null check (seq >= 0),
    node       text   not null,
    kind       text   not null check (kind in ('event', 'tool_call', 'tool_result', 'submit_rejected',
                                                'submitted', 'approval', 'decision', 'final', 'error')),
    call_id    text,
    tool       text,
    summary    text   not null,
    payload    jsonb,
    created_at timestamptz not null default now(),
    unique (run_id, seq)
);

create table plumetrace.drafts (
    draft_id   bigint generated always as identity primary key,
    run_id     uuid    not null references plumetrace.runs (run_id) on delete cascade,
    revision   integer not null check (revision in (0, 1)),
    bundle     jsonb   not null,
    created_at timestamptz not null default now(),
    unique (run_id, revision)
);

create table plumetrace.decisions (
    decision_id  bigint generated always as identity primary key,
    run_id       uuid    not null references plumetrace.runs (run_id) on delete cascade,
    interrupt_id text    not null,
    revision     integer not null check (revision in (0, 1)),
    action       text    not null check (action in ('approve', 'edit', 'reject')),
    reason       text,
    edits        jsonb,
    decided_at   timestamptz not null default now(),
    unique (run_id, interrupt_id),
    check (action <> 'reject' or (reason is not null and length(btrim(reason)) >= 3))
);

create table plumetrace.work_orders (
    work_order_id bigint generated always as identity primary key,
    run_id        uuid not null unique references plumetrace.runs (run_id) on delete cascade,
    equipment_tag text not null,
    priority      text not null check (priority in ('P1', 'P2', 'P3')),
    title         text not null,
    body          jsonb not null,
    status        text not null default 'issued' check (status = 'issued'),
    issued_at     timestamptz not null default now()
);

create table plumetrace.reports (
    report_id       bigint generated always as identity primary key,
    run_id          uuid not null unique references plumetrace.runs (run_id) on delete cascade,
    source_category text not null,
    body            jsonb not null,
    status          text not null default 'filed' check (status = 'filed'),
    filed_at        timestamptz not null default now()
);

-- One row per billed OpenAI call. The sum of cost_usd is the project's total spend, checked
-- against PLUMETRACE_SPEND_CAP_USD before every call. Rows survive run deletion (set null).
create table plumetrace.llm_calls (
    llm_call_id       bigint  generated always as identity primary key,
    run_id            uuid    references plumetrace.runs (run_id) on delete set null,
    purpose           text    not null check (purpose in ('smoke', 'live', 'eval', 'record')),
    node              text    not null,
    role              text    not null check (role in ('fast', 'reasoning')),
    model             text    not null,
    reasoning_effort  text    not null,
    prompt_tokens     integer not null check (prompt_tokens >= 0),
    cached_tokens     integer not null check (cached_tokens >= 0 and cached_tokens <= prompt_tokens),
    completion_tokens integer not null check (completion_tokens >= 0),
    reasoning_tokens  integer not null check (reasoning_tokens >= 0 and reasoning_tokens <= completion_tokens),
    cost_usd          numeric(12, 6) not null check (cost_usd >= 0),
    latency_ms        integer not null check (latency_ms >= 0),
    created_at        timestamptz not null default now()
);

-- Backend log records (written by the logging handler of Task 9b). No foreign key on run_id:
-- logs outlive runs and may name a run that failed before its row existed.
create table plumetrace.app_logs (
    log_id     bigint generated always as identity primary key,
    level      text   not null check (level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    logger     text   not null,
    message    text   not null check (length(message) <= 4000),
    run_id     uuid,
    context    jsonb,
    created_at timestamptz not null default now()
);

-- One row per evaluation case and repetition (Task 11).
create table plumetrace.eval_results (
    eval_result_id  bigint  generated always as identity primary key,
    experiment      text    not null,
    case_id         text    not null,
    family          text    not null,
    repetition      integer not null check (repetition >= 0),
    run_id          uuid    references plumetrace.runs (run_id) on delete set null,
    scores          jsonb   not null,
    baseline_triage text,
    cost_usd        numeric(12, 6) not null check (cost_usd >= 0),
    latency_s       double precision not null check (latency_s >= 0),
    created_at      timestamptz not null default now(),
    unique (experiment, case_id, repetition)
);

create index agent_steps_run_idx on plumetrace.agent_steps (run_id, seq);
create index llm_calls_run_idx on plumetrace.llm_calls (run_id);
create index app_logs_created_idx on plumetrace.app_logs (created_at desc);
create index app_logs_run_idx on plumetrace.app_logs (run_id) where run_id is not null;
create index eval_results_run_idx on plumetrace.eval_results (run_id);

comment on table plumetrace.agent_steps is 'Ordered agent timeline per run (tool calls with inputs/outputs in payload).';
comment on table plumetrace.drafts is 'Draft bundles (work order, shift log, report line) by revision.';
comment on table plumetrace.decisions is 'Operator decisions: the authoritative approval record (not the checkpoint).';
comment on table plumetrace.work_orders is 'Approved work orders (status issued - simulated).';
comment on table plumetrace.reports is 'Approved OGMP report lines (status filed - simulated).';
comment on table plumetrace.llm_calls is 'Every billed OpenAI call: tokens, cost, latency. Sum = total spend vs the cap.';
comment on table plumetrace.app_logs is 'Backend log records (redacted; never secrets).';
comment on table plumetrace.eval_results is 'Evaluation scores per case and repetition.';

alter table plumetrace.agent_steps enable row level security;
alter table plumetrace.drafts enable row level security;
alter table plumetrace.decisions enable row level security;
alter table plumetrace.work_orders enable row level security;
alter table plumetrace.reports enable row level security;
alter table plumetrace.llm_calls enable row level security;
alter table plumetrace.app_logs enable row level security;
alter table plumetrace.eval_results enable row level security;

-- LangGraph checkpoint tables live in their own schema, created by PostgresSaver.setup() at start-up.
create schema if not exists langgraph;
do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        revoke all on schema langgraph from anon, authenticated;
    end if;
end
$$;
comment on schema langgraph is 'LangGraph checkpoints (graph state for pause/resume). Not exposed to the API roles.';
```
(The `do` block keeps the migration valid on a plain Postgres 17 database without the Supabase roles, for example a scratch database used to test migrations.)

## Repository functions (parameterised SQL only; each with a Google docstring)
`db/agent_steps.py`: `def append_step(conn, run_id, *, node, kind, summary, call_id=None, tool=None, payload=None) -> int` — `seq` = `coalesce(max(seq), -1) + 1` for the run inside the same statement (`insert … select`); returns `seq`. `def list_steps(conn, run_id, after_seq: int = -1) -> list[dict]` ordered by `seq`.
`db/drafts.py`: `def save_draft(conn, run_id, revision, bundle: dict) -> None` (`on conflict (run_id, revision) do nothing`); `def get_drafts(conn, run_id) -> list[dict]`.
`db/decisions.py`: `def record_decision(conn, run_id, *, interrupt_id, revision, action, reason, edits) -> bool` — returns `False` when the `(run_id, interrupt_id)` row already exists (`on conflict do nothing`), so a double submit is harmless; `def list_decisions(conn, run_id) -> list[dict]`.
`db/outputs.py`: `def issue_work_order(conn, run_id, *, equipment_tag, priority, title, body) -> None`; `def file_report(conn, run_id, *, source_category, body) -> None` (both idempotent on `run_id`).
`db/runs.py`: `def set_outcome(conn, run_id, outcome: str) -> None`.
`db/llm_calls.py`: `def record_llm_call(conn, *, run_id: UUID | None, purpose: str, node: str, role: str, model: str, reasoning_effort: str, prompt_tokens: int, cached_tokens: int, completion_tokens: int, reasoning_tokens: int, cost_usd: Decimal, latency_ms: int) -> None`; `def total_spend_usd(conn) -> Decimal` (`select coalesce(sum(cost_usd), 0)` over **all** rows — never filtered); `def run_spend_usd(conn, run_id) -> Decimal`; `def list_llm_calls(conn, run_id) -> list[dict]` ordered by `llm_call_id`.
`db/app_logs.py`: `def insert_log(conn, *, level: str, logger: str, message: str, run_id: UUID | None, context: dict | None) -> None` (the caller truncates `message` to 4000 chars); `def list_logs(conn, *, run_id: UUID | None = None, min_level: str = "INFO", limit: int = 200) -> list[dict]` newest first (level order DEBUG < INFO < WARNING < ERROR < CRITICAL, compared in SQL with `array_position`).
`db/eval_results.py`: `def save_eval_result(conn, *, experiment, case_id, family, repetition, run_id, scores: dict, baseline_triage, cost_usd: Decimal, latency_s: float) -> bool` (`on conflict do nothing`, returns whether a row was written); `def list_eval_results(conn, experiment: str) -> list[dict]` ordered by `case_id, repetition`.

## Tests — `app/backend/tests/db/test_agent_tables.py` (use the Phase 1 `db_conn` fixture; skipped without a DB unless `PLUMETRACE_REQUIRE_DB=1`)
Full code for the key cases:
```python
"""Agent tables: ordering, idempotency, constraints, RLS."""

import psycopg
import pytest

from plumetrace.db import agent_steps, decisions, drafts
from plumetrace.db.runs import create_run


def _run(conn: psycopg.Connection[tuple[object, ...]]) -> object:
    from datetime import UTC, datetime
    return create_run(conn, scenario_id="s1_rod_packing", mode="live",
                      sim_start_utc=datetime(2025, 7, 15, 6, tzinfo=UTC))


def test_steps_are_numbered_in_order(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """seq starts at 0 and increases per run."""
    run_id = _run(db_conn)
    assert agent_steps.append_step(db_conn, run_id, node="detect_event", kind="event", summary="a") == 0
    assert agent_steps.append_step(db_conn, run_id, node="triage", kind="tool_call", summary="b",
                                   call_id="call_001", tool="get_weather") == 1
    assert [s["seq"] for s in agent_steps.list_steps(db_conn, run_id)] == [0, 1]
    assert [s["seq"] for s in agent_steps.list_steps(db_conn, run_id, after_seq=0)] == [1]


def test_decision_is_recorded_once(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """A repeated decision for the same interrupt is ignored."""
    run_id = _run(db_conn)
    kw = {"interrupt_id": "x:r0", "revision": 0, "action": "approve", "reason": None, "edits": None}
    assert decisions.record_decision(db_conn, run_id, **kw) is True
    assert decisions.record_decision(db_conn, run_id, **kw) is False


def test_reject_needs_a_reason(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The database refuses a rejection without a reason."""
    run_id = _run(db_conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        decisions.record_decision(db_conn, run_id, interrupt_id="x:r0", revision=0, action="reject",
                                  reason=" ", edits=None)


def test_draft_revision_range(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Only revisions 0 and 1 exist (one redraft)."""
    run_id = _run(db_conn)
    drafts.save_draft(db_conn, run_id, 0, {"revision": 0})
    with pytest.raises(psycopg.errors.CheckViolation):
        drafts.save_draft(db_conn, run_id, 2, {"revision": 2})


def test_rls_is_enabled_on_new_tables(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Every plumetrace table has RLS enabled."""
    rows = db_conn.execute(
        "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'plumetrace' and c.relkind = 'r' and not c.relrowsecurity").fetchall()
    assert rows == []
```

`app/backend/tests/db/test_ledger_logs.py` (same fixture rules), full code:
```python
"""LLM-call ledger, app logs and eval results."""

from datetime import UTC, datetime
from decimal import Decimal

import psycopg
import pytest

from plumetrace.db import app_logs, eval_results, llm_calls
from plumetrace.db.runs import create_run

CALL = {"purpose": "live", "node": "triage", "role": "fast", "model": "gpt-6-luna",
        "reasoning_effort": "low", "prompt_tokens": 1000, "cached_tokens": 200,
        "completion_tokens": 300, "reasoning_tokens": 120, "latency_ms": 850}


def _run(conn: psycopg.Connection[tuple[object, ...]]) -> object:
    return create_run(conn, scenario_id="s1_rod_packing", mode="live",
                      sim_start_utc=datetime(2025, 7, 15, 6, tzinfo=UTC))


def test_total_spend_adds_every_call(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Spend is the sum over all calls, with and without a run."""
    before = llm_calls.total_spend_usd(db_conn)
    run_id = _run(db_conn)
    llm_calls.record_llm_call(db_conn, run_id=run_id, cost_usd=Decimal("0.000250"), **CALL)
    llm_calls.record_llm_call(db_conn, run_id=None, cost_usd=Decimal("0.000100"),
                              **{**CALL, "purpose": "smoke"})
    assert llm_calls.total_spend_usd(db_conn) - before == Decimal("0.000350")
    assert llm_calls.run_spend_usd(db_conn, run_id) == Decimal("0.000250")


def test_spend_survives_run_deletion(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Deleting a run keeps its ledger rows (run_id set to null)."""
    run_id = _run(db_conn)
    llm_calls.record_llm_call(db_conn, run_id=run_id, cost_usd=Decimal("0.001000"), **CALL)
    before = llm_calls.total_spend_usd(db_conn)
    db_conn.execute("delete from plumetrace.runs where run_id = %s", (run_id,))
    assert llm_calls.total_spend_usd(db_conn) == before


def test_impossible_token_counts_are_refused(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Cached > prompt or reasoning > completion violates a check."""
    with pytest.raises(psycopg.errors.CheckViolation):
        llm_calls.record_llm_call(db_conn, run_id=None, cost_usd=Decimal(0),
                                  **{**CALL, "cached_tokens": 2000})


def test_logs_filter_by_level_and_run(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """min_level hides lower levels; run_id filters."""
    run_id = _run(db_conn)
    app_logs.insert_log(db_conn, level="DEBUG", logger="t", message="d", run_id=run_id, context=None)
    app_logs.insert_log(db_conn, level="ERROR", logger="t", message="e", run_id=run_id,
                        context={"exc_type": "ValueError"})
    rows = app_logs.list_logs(db_conn, run_id=run_id, min_level="INFO")
    assert [r["message"] for r in rows] == ["e"]


def test_eval_result_written_once(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The same case and repetition in one experiment is stored once."""
    kw = {"experiment": "exp-test", "case_id": "s1_v0", "family": "s1", "repetition": 0,
          "run_id": None, "scores": {"triage_correct": 1}, "baseline_triage": "leak",
          "cost_usd": Decimal("0.012"), "latency_s": 40.0}
    assert eval_results.save_eval_result(db_conn, **kw) is True
    assert eval_results.save_eval_result(db_conn, **kw) is False
```

## Steps
- [ ] Write the migration; `cd app && npx --yes supabase@3.1.0 db reset` → applies cleanly. Never edit an applied migration.
- [ ] Tests → FAIL → implement → `PLUMETRACE_REQUIRE_DB=1 uv run pytest app/backend/tests/db -q` green (local Supabase running).
- [ ] `backend-design:schema-reviewer` pass over the migration; record findings.
- [ ] Repo checks (migration ≤ 300 lines).
- [ ] **Docs.** DATABASE.md (tables, columns, constraints, the `langgraph` schema and why it is separate, decisions = approval record, `llm_calls` = the spend ledger and why rows survive run deletion, `app_logs`, `eval_results`, the diagram of what is stored where for a live / eval / record run). Work-log; `STATUS.md` (last 5.8, next 5.9).
- [ ] **Commit** `feat(db): add agent run, LLM ledger, log and eval tables`.
