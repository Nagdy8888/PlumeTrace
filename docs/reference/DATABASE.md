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

## Row-level security

RLS is enabled on every table in schema `plumetrace`, and no policy exists for `anon` or
`authenticated`. Only the backend connects, as the database owner, which bypasses RLS. The result:
if Supabase's REST API were ever reachable, the tables would expose no rows. Tests
(`app/backend/tests/db/test_schema.py`) check that RLS is on for every table and that no policy exists.

## Migrations

Schema changes happen only through new files in `app/supabase/migrations/`. Never edit an applied
migration and never change the database by hand.

| File | Purpose |
|---|---|
| `20261113090000_create_plumetrace_schema.sql` | Creates schema `plumetrace` and the `scenarios` table with RLS enabled. |

## Operate (run from `app/`)

```bash
npx --yes supabase@3.1.0 start      # start the local stack (Docker must be running)
npx --yes supabase@3.1.0 db reset   # rebuild the database from migrations + seed.sql
npx --yes supabase@3.1.0 stop       # stop the stack
```

## Checkpoint tables

The LangGraph checkpoint tables (schema `langgraph`) are created by the LangGraph `PostgresSaver`
in Phase 5. They are not part of the migrations in this task.
