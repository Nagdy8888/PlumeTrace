# Database

## Purpose

PlumeTrace keeps its state in a local Supabase Postgres (Docker). Later phases store runs, events,
agent steps, drafts, operator decisions, work orders, reports, LLM calls, logs and the LangGraph
checkpoints there. Phase 1 Task 4 creates the schema, the first table and the connection pool.
Design reference: section 10.1; rule: `CLAUDE.md` rule 19.

## Connection

- Only the backend connects, with the direct Postgres URL from `SUPABASE_DB_URL` in the root `.env`
  (local default `postgresql://postgres:postgres@127.0.0.1:54322/postgres`, the public local
  Supabase credentials).
- `plumetrace.db.pool.create_pool(settings, *, min_size=1, max_size=5)` returns an open
  `psycopg_pool.ConnectionPool`. It calls `require_db_url`, so a missing URL raises
  `ConfigurationError` naming `SUPABASE_DB_URL` before any connection is tried. The caller closes
  the pool.
- The frontend never connects to the database.

## Schema `plumetrace`

### Table `scenarios`

Scenario catalogue (S1-S6). Seeded by `app/supabase/seed.sql`; read by the backend.

| Column | Type | Meaning |
|---|---|---|
| `id` | `text`, primary key | Scenario id, must match `^s[0-9]+_[a-z0-9_]+$` (for example `s1_rod_packing`). |
| `title` | `text`, not null | Human-readable scenario title. |
| `seed` | `bigint`, not null | Random seed that makes the simulation reproducible. |
| `version` | `integer`, not null, default 1 | Scenario definition version. |
| `is_mvp` | `boolean`, not null | True for the scenarios in the MVP (S1, S4, S5). |
| `created_at` | `timestamptz`, not null, default `now()` | Row creation time. |

Seeded rows: `s1_rod_packing`, `s4_planned_blowdown`, `s5_sensor_drift`.

### Table `runs`

One row per simulation or agent run. `run_id` is also the LangGraph `thread_id`. Migration
`20261120090000_create_run_tables.sql`.

| Column | Type | Meaning |
|---|---|---|
| `run_id` | `uuid`, primary key, default `gen_random_uuid()` | Run id (the LangGraph `thread_id`). |
| `scenario_id` | `text`, not null, foreign key to `scenarios.id` | Scenario the run simulates. An unknown id raises `ForeignKeyViolation`. |
| `variant_seed` | `bigint`, nullable | Seed of the randomised scenario variant; `NULL` for the base scenario. |
| `mode` | `text`, not null, check | `live`, `record` or `eval`. |
| `status` | `text`, not null, check | `running`, `awaiting_approval`, `completed`, `aborted_budget` or `failed`. |
| `branch` | `text`, nullable, check | `approve` or `reject_redraft`: the approval branch of a scripted run. |
| `sim_start_utc` | `timestamptz`, not null | UTC time that scenario second 0 maps to (anchors the run to real weather). |
| `started_at` | `timestamptz`, not null, default `now()` | Row creation time. |
| `finished_at` | `timestamptz`, nullable | Set when the status becomes `completed`, `aborted_budget` or `failed`. |
| `model_fast`, `model_reasoning` | `text`, nullable | Model names used by the run. |
| `prompt_tokens`, `completion_tokens` | `integer`, not null, default 0, check `>= 0` | Token totals, incremented by `add_usage`. |
| `cost_usd` | `numeric(10, 4)`, not null, default 0, check `>= 0` | Cost total in USD, incremented by `add_usage`. |
| `langsmith_run_url` | `text`, nullable | LangSmith trace URL. |

### Table `events`

CUSUM detection events raised during a run (one row per `DetectionEvent`).

| Column | Type | Meaning |
|---|---|---|
| `event_id` | `bigint`, `generated always as identity`, primary key | Row id. |
| `run_id` | `uuid`, not null, foreign key to `runs.run_id`, `on delete cascade` | Owning run. |
| `sensor_id` | `text`, not null | Instrument tag. |
| `window_index` | `integer`, not null, check `>= 0` | Detection window index. |
| `window_start_s` | `double precision`, not null | Window start in s. |
| `mean_ppm` | `double precision`, not null | Window mean in ppm. |
| `baseline_ppm` | `double precision`, not null | Rolling median baseline in ppm. |
| `cusum` | `double precision`, not null | CUSUM value that crossed the threshold, in sigmas. |
| `downwind_of_site` | `boolean`, not null | Whether the sensor is downwind of the site centre. |
| `status` | `text`, not null, default `new`, check | `new`, `queued`, `investigating` or `closed`. |
| `created_at` | `timestamptz`, not null, default `now()` | Row creation time. |

Constraint `unique (run_id, sensor_id, window_index)` makes saving idempotent. Index
`events_run_id_idx` on `run_id` serves `list_events`.

### Table `sensor_readings`

60 s mean readings per tag (methane and the other instruments), not raw 10 s samples.

| Column | Type | Meaning |
|---|---|---|
| `run_id` | `uuid`, not null, foreign key to `runs.run_id`, `on delete cascade` | Owning run. |
| `tag` | `text`, not null | Instrument tag. |
| `t_s` | `double precision`, not null | Scenario time in s. |
| `value` | `double precision`, nullable | Reading; `NULL` when there is no value (a NaN is stored as `NULL`). |
| `unit` | `text`, not null | Unit of `value`. |

Primary key `(run_id, tag, t_s)`; the key index also serves `get_series`.

Deleting a run deletes its events and readings (`on delete cascade`).

## Repositories (`plumetrace.db`)

All functions take an open `psycopg.Connection[tuple[object, ...]]` and **never commit**: the caller
owns the transaction (a test wraps it in `transaction(force_rollback=True)`). All SQL uses `%s`
placeholders. Looking up or changing a run that does not exist raises `KeyError(str(run_id))`.

| Module | Functions | Notes |
|---|---|---|
| `runs.py` | `create_run`, `set_run_status`, `add_usage`, `get_run`, `RunRow` | `create_run` inserts status `running`. `set_run_status` sets `finished_at = now()` for `completed`, `aborted_budget`, `failed`. `add_usage` increments the totals and raises `ValueError` for a NaN or infinite cost (Postgres would accept NaN past the `>= 0` check). |
| `events.py` | `insert_events`, `list_events` | `insert_events` uses `on conflict (run_id, sensor_id, window_index) do nothing` and returns the rows inserted; it raises `ValueError` for a NaN or infinite number in an event, before any row is written. `list_events` orders by `window_index, sensor_id`. |
| `readings.py` | `Reading`, `insert_readings`, `get_series` | `insert_readings` stores NaN as `NULL` and skips an existing `(run_id, tag, t_s)` (the first value wins). `get_series` orders by `t_s`. |

Tests: `app/backend/tests/db/test_run_tables.py` (lifecycle, idempotency, NaN, foreign key) and
`test_run_tables_edges.py` (final and non-final statuses, unknown runs, non-finite values, check
constraints, duplicates, ordering, cascade, no commit, RLS, index).

## Row-level security

RLS is enabled on every table in schema `plumetrace`, and no policy exists for `anon` or
`authenticated`. Only the backend connects, as the database owner, which bypasses RLS. The result:
if Supabase's REST API were ever reachable, the tables would expose no rows. Tests
(`app/backend/tests/db/test_schema.py`) check that RLS is on for every table (the three run tables included) and that no policy exists.

## Migrations

Schema changes happen only through new files in `app/supabase/migrations/`. Never edit an applied
migration and never change the database by hand.

| File | Purpose |
|---|---|
| `20261113090000_create_plumetrace_schema.sql` | Creates schema `plumetrace` and the `scenarios` table with RLS enabled. |
| `20261120090000_create_run_tables.sql` | Creates `runs`, `events` and `sensor_readings` with constraints, one index and RLS enabled (no policies). |

## Operate (run from `app/`)

```bash
npx --yes supabase@3.1.0 start      # start the local stack (Docker must be running)
npx --yes supabase@3.1.0 db reset   # rebuild the database from migrations + seed.sql
npx --yes supabase@3.1.0 stop       # stop the stack
```

## Checkpoint tables

The LangGraph checkpoint tables (schema `langgraph`) are created by the LangGraph `PostgresSaver`
in Phase 5. They are not part of the migrations in this task.
