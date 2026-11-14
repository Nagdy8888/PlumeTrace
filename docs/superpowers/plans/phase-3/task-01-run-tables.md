# Phase 3 · Task 1 — Run tables and repositories

**Skills:** `plan-execution`, `supabase:supabase-postgres-best-practices`, `security-checks`, `project-documentation`.

## Files
| Action | Path |
|---|---|
| Create | `app/supabase/migrations/20261120090000_create_run_tables.sql` |
| Create | `app/backend/plumetrace/db/runs.py`, `app/backend/plumetrace/db/events.py`, `app/backend/plumetrace/db/readings.py` |
| Create | `app/backend/tests/db/test_run_tables.py` |
| Modify | `docs/reference/DATABASE.md` |

## Migration (exact content)
```sql
-- Migration: run storage (runs, detection events, downsampled readings).
-- Date: 2026-11-20. Design section 10.1. RLS on, no policies.

create table plumetrace.runs (
    run_id            uuid        primary key default gen_random_uuid(),
    scenario_id       text        not null references plumetrace.scenarios (id),
    variant_seed      bigint,
    mode              text        not null check (mode in ('live', 'record', 'eval')),
    status            text        not null check (status in
                          ('running', 'awaiting_approval', 'completed', 'aborted_budget', 'failed')),
    branch            text        check (branch in ('approve', 'reject_redraft')),
    sim_start_utc     timestamptz not null,
    started_at        timestamptz not null default now(),
    finished_at       timestamptz,
    model_fast        text,
    model_reasoning   text,
    prompt_tokens     integer     not null default 0 check (prompt_tokens >= 0),
    completion_tokens integer     not null default 0 check (completion_tokens >= 0),
    cost_usd          numeric(10, 4) not null default 0 check (cost_usd >= 0),
    langsmith_run_url text
);

create table plumetrace.events (
    event_id          bigint      generated always as identity primary key,
    run_id            uuid        not null references plumetrace.runs (run_id) on delete cascade,
    sensor_id         text        not null,
    window_index      integer     not null check (window_index >= 0),
    window_start_s    double precision not null,
    mean_ppm          double precision not null,
    baseline_ppm      double precision not null,
    cusum             double precision not null,
    downwind_of_site  boolean     not null,
    status            text        not null default 'new'
                          check (status in ('new', 'queued', 'investigating', 'closed')),
    created_at        timestamptz not null default now(),
    unique (run_id, sensor_id, window_index)
);
create index events_run_id_idx on plumetrace.events (run_id);

create table plumetrace.sensor_readings (
    run_id  uuid             not null references plumetrace.runs (run_id) on delete cascade,
    tag     text             not null,
    t_s     double precision not null,
    value   double precision,
    unit    text             not null,
    primary key (run_id, tag, t_s)
);

comment on table plumetrace.runs is 'One row per simulation/agent run; run_id = LangGraph thread_id.';
comment on table plumetrace.events is 'CUSUM detection events raised during a run.';
comment on table plumetrace.sensor_readings is '60 s mean readings per tag (methane and instruments).';

alter table plumetrace.runs enable row level security;
alter table plumetrace.events enable row level security;
alter table plumetrace.sensor_readings enable row level security;
```

## Interface (all functions take an open `psycopg.Connection` and do not commit; the caller owns the transaction)
`db/runs.py`:
- `RunMode = Literal["live", "record", "eval"]`; `RunStatus = Literal["running", "awaiting_approval", "completed", "aborted_budget", "failed"]`; `Branch = Literal["approve", "reject_redraft"]`
- `def create_run(conn, *, scenario_id: str, mode: RunMode, sim_start_utc: datetime, variant_seed: int | None = None, branch: Branch | None = None) -> UUID` — inserts with status `'running'`, returns `run_id`.
- `def set_run_status(conn, run_id: UUID, status: RunStatus) -> None` — sets `finished_at = now()` when status is `completed`, `aborted_budget` or `failed`.
- `def add_usage(conn, run_id: UUID, *, prompt_tokens: int, completion_tokens: int, cost_usd: Decimal) -> None` — increments.
- `class RunRow(BaseModel)` with every column; `def get_run(conn, run_id: UUID) -> RunRow` (raises `KeyError(str(run_id))` if missing).

`db/events.py`:
- `def insert_events(conn, run_id: UUID, events: Sequence[DetectionEvent]) -> int` — `insert … on conflict (run_id, sensor_id, window_index) do nothing`; returns rows inserted.
- `def list_events(conn, run_id: UUID) -> list[DetectionEvent]` — ordered by `window_index, sensor_id`.

`db/readings.py`:
- `class Reading(NamedTuple): tag: str; t_s: float; value: float | None; unit: str`
- `def insert_readings(conn, run_id: UUID, readings: Iterable[Reading]) -> None` — `executemany` with `on conflict do nothing`.
- `def get_series(conn, run_id: UUID, tag: str) -> list[tuple[float, float | None]]` — ordered by `t_s`.

All SQL uses `%s` placeholders (never f-strings). `NaN` values are stored as SQL `NULL`.

## Tests (full code) — `app/backend/tests/db/test_run_tables.py`
```python
"""Tests for the run tables and repositories (needs the local Supabase Postgres)."""

from datetime import UTC, datetime
from decimal import Decimal

import psycopg

from plumetrace.db.events import insert_events, list_events
from plumetrace.db.readings import Reading, get_series, insert_readings
from plumetrace.db.runs import add_usage, create_run, get_run, set_run_status
from plumetrace.engineering.detection import DetectionEvent

START = datetime(2025, 7, 14, 6, 0, tzinfo=UTC)


def _event(window: int) -> DetectionEvent:
    return DetectionEvent(sensor_id="AT-104", window_index=window, window_start_s=window * 600.0,
                          mean_ppm=4.0, baseline_ppm=1.95, cusum=6.0, downwind_of_site=True)


def test_run_lifecycle(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """A run is created running, accumulates usage and finishes with a timestamp."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(db_conn, scenario_id="s1_rod_packing", mode="record",
                            sim_start_utc=START, branch="approve")
        add_usage(db_conn, run_id, prompt_tokens=100, completion_tokens=20,
                  cost_usd=Decimal("0.0100"))
        add_usage(db_conn, run_id, prompt_tokens=50, completion_tokens=5,
                  cost_usd=Decimal("0.0050"))
        set_run_status(db_conn, run_id, "completed")
        row = get_run(db_conn, run_id)
        assert row.status == "completed" and row.finished_at is not None
        assert (row.prompt_tokens, row.completion_tokens) == (150, 25)
        assert row.cost_usd == Decimal("0.0150")


def test_events_are_idempotent(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Saving the same events twice stores them once."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(db_conn, scenario_id="s1_rod_packing", mode="record",
                            sim_start_utc=START)
        assert insert_events(db_conn, run_id, [_event(12), _event(30)]) == 2
        assert insert_events(db_conn, run_id, [_event(12)]) == 0
        assert [e.window_index for e in list_events(db_conn, run_id)] == [12, 30]


def test_readings_store_nan_as_null(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Readings round-trip in time order; NaN becomes NULL."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(db_conn, scenario_id="s5_sensor_drift", mode="eval",
                            sim_start_utc=START, variant_seed=7)
        insert_readings(db_conn, run_id, [Reading("AT-106", 60.0, float("nan"), "ppm"),
                                          Reading("AT-106", 0.0, 1.95, "ppm")])
        assert get_series(db_conn, run_id, "AT-106") == [(0.0, 1.95), (60.0, None)]


def test_unknown_scenario_is_rejected(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The scenario foreign key protects run integrity."""
    with db_conn.transaction(force_rollback=True):
        try:
            create_run(db_conn, scenario_id="s9_missing", mode="live", sim_start_utc=START)
        except psycopg.errors.ForeignKeyViolation:
            return
    raise AssertionError("expected a foreign key violation")
```
(The existing `test_every_plumetrace_table_has_rls` and `test_no_client_policies_exist` now also cover the three new tables.)

## Steps
- [x] Write the test; with Supabase running: `uv run pytest backend/tests/db -q` → fails.
- [x] Write the migration; `npx --yes supabase@3.1.0 db reset`; implement the three modules (Google docstrings; typed with `psycopg.Connection[tuple[object, ...]]`).
- [x] Full checks green: `python scripts/ci_local.py --full` after `npx --yes supabase@3.1.0 db reset`.
- [x] **Docs.** DATABASE.md: the three tables (every column, type, meaning, constraints), indexes, cascade rules, NaN→NULL, transaction ownership. Work-log; `STATUS.md` (last 3.1, next 3.2).
- [ ] **Commit** `feat(db): add run, event and reading tables with repositories`.
