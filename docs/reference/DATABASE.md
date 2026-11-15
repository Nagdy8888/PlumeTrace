# Database

## Purpose

PlumeTrace keeps its state in a local Supabase Postgres (Docker). Later phases store runs, events,
agent steps, drafts, operator decisions, work orders, reports, LLM calls, logs and the LangGraph
checkpoints there. Phase 1 Task 4 created the schema, the first table and the connection pool.
Phase 3 added the run storage: `runs`, `events` and `sensor_readings`, three repositories and
`save_scenario_run`. Design reference: section 10.1; rule: `CLAUDE.md` rule 19 (local Supabase only,
schema changes only through new migrations, RLS on every table).

What this page covers today: the `plumetrace` schema as it exists after the two migrations below,
the repositories, how a simulated scenario run is saved, the constraints and failure modes the tests
pin, and the RLS stance. Tables for agent steps, drafts, decisions, LLM calls, logs and evaluations
arrive in Phase 5 and are not documented as implemented here.

## Connection

- Only the backend connects, with the direct Postgres URL from `SUPABASE_DB_URL` in the root `.env`
  (the usual local value, listed in `.env.example`, is
  `postgresql://postgres:postgres@127.0.0.1:54322/postgres`, the public local Supabase credentials;
  it is not a default in the code, a missing variable is an error).
- `plumetrace.db.pool.create_pool(settings, *, min_size=1, max_size=5)` returns an open
  `psycopg_pool.ConnectionPool`. It calls `require_db_url`, so a missing URL raises
  `ConfigurationError` naming `SUPABASE_DB_URL` before any connection is tried. The caller closes
  the pool.
- The frontend never connects to the database.

## Schema `plumetrace`

```mermaid
erDiagram
    SCENARIOS ||--o{ RUNS : "runs.scenario_id foreign key"
    RUNS ||--o{ EVENTS : "events.run_id on delete cascade"
    RUNS ||--o{ SENSOR_READINGS : "sensor_readings.run_id on delete cascade"

    SCENARIOS {
        text id PK "check id matches s digits underscore name"
        text title
        bigint seed
        integer version "default 1"
        boolean is_mvp
        timestamptz created_at
    }
    RUNS {
        uuid run_id PK "default gen_random_uuid, also the LangGraph thread_id"
        text scenario_id FK
        bigint variant_seed "null for the base scenario"
        text mode "live, record or eval"
        text status "running, awaiting_approval, completed, aborted_budget or failed"
        text branch "null, approve or reject_redraft"
        timestamptz sim_start_utc
        timestamptz started_at "default now"
        timestamptz finished_at "null until a final status"
        text model_fast
        text model_reasoning
        integer prompt_tokens "default 0, check 0 or more"
        integer completion_tokens "default 0, check 0 or more"
        numeric cost_usd "numeric 10 4, default 0, check 0 or more"
        text langsmith_run_url
    }
    EVENTS {
        bigint event_id PK "generated always as identity"
        uuid run_id FK
        text sensor_id
        integer window_index "check 0 or more"
        double_precision window_start_s
        double_precision mean_ppm
        double_precision baseline_ppm
        double_precision cusum
        boolean downwind_of_site
        text status "default new, check new, queued, investigating or closed"
        timestamptz created_at "default now"
    }
    SENSOR_READINGS {
        uuid run_id PK, FK
        text tag PK
        double_precision t_s PK
        double_precision value "null when there is no value"
        text unit
    }
```

*Entity-relationship view of the four tables. `events` also has `unique (run_id, sensor_id, window_index)` and an index on `run_id`. Row-level security is on for all four, with no policies.*

### Table `scenarios`

Scenario catalogue (S1-S6). Seeded by `app/supabase/seed.sql`. Today nothing reads it except the
foreign key `runs.scenario_id` (the migration comment says "read by the backend", which is the
intent, not the current code).

| Column | Type | Meaning |
|---|---|---|
| `id` | `text`, primary key | Scenario id, must match `^s[0-9]+_[a-z0-9_]+$` (for example `s1_rod_packing`). |
| `title` | `text`, not null | Human-readable scenario title. |
| `seed` | `bigint`, not null | Random seed that makes the simulation reproducible. |
| `version` | `integer`, not null, default 1 | Scenario definition version. |
| `is_mvp` | `boolean`, not null | True for the scenarios in the MVP (S1, S4, S5). |
| `created_at` | `timestamptz`, not null, default `now()` | Row creation time. |

Seeded rows (`seed.sql`, `on conflict (id) do nothing`):

| `id` | `title` | `seed` | `version` | `is_mvp` |
|---|---|---|---|---|
| `s1_rod_packing` | Rod packing failure, K-202 | 101 | 1 | true |
| `s4_planned_blowdown` | Planned blowdown, compressor K-201 | 104 | 1 | true |
| `s5_sensor_drift` | Sensor drift, AT-106 | 105 | 1 | true |

The ids and seeds match `plumetrace.simulator.scenarios`. The titles do **not** match the
`ScenarioDefinition.title` of the same scenarios (for example "K-202 rod-packing leak via vent stack
VS-250"). Nothing reads the database title today; the replay and the API use the definition title.
See the limits below.

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
| `window_index` | `integer`, not null, check `>= 0` | Detection window index (10-minute windows). |
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

### Constraint summary

| Rule | Where | Enforced by |
|---|---|---|
| A run names a known scenario | `runs.scenario_id` | foreign key (`ForeignKeyViolation`) |
| `mode`, `status`, `branch`, event `status` take only the listed values | `runs`, `events` | check constraints |
| Token and cost totals are never negative | `runs` | check `>= 0` on three columns |
| Window index is never negative | `events.window_index` | check `>= 0` |
| One event per sensor and window and run | `events` | `unique (run_id, sensor_id, window_index)` |
| One reading per tag and time and run | `sensor_readings` | primary key `(run_id, tag, t_s)` |
| Children disappear with their run | `events`, `sensor_readings` | `on delete cascade` |
| A NaN cost never reaches the database | `add_usage` | `ValueError` before the query (Postgres would accept NaN past `>= 0`) |
| A NaN or infinite event number never reaches the database | `insert_events` | `ValueError` before any row is written |
| A NaN reading becomes `NULL` | `insert_readings` | converted in Python |

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

## Saving scenario runs

`plumetrace.api.run_store` (in `api/`, because it combines the simulator and `db`) stores one
simulated scenario run. It does not commit: the caller owns the transaction. It has **no production
caller yet** (tests only): no API route, script or agent calls it, so today the tables are filled only
by the tests. The API and the agent graph are planned to call it in later phases.

```mermaid
sequenceDiagram
    participant C as Caller with open transaction
    participant RS as run_store.save_scenario_run
    participant R as db.runs.create_run
    participant E as db.events.insert_events
    participant D as db.readings.insert_readings
    participant PG as Postgres
    C->>RS: save_scenario_run(conn, run, mode, branch)
    RS->>R: create_run(scenario_id, mode, sim_start_utc, variant_seed, branch)
    R->>PG: insert into plumetrace.runs, status running
    alt scenario id not in plumetrace.scenarios
        PG-->>R: ForeignKeyViolation
        R-->>C: error, caller rolls back
    else scenario known
        PG-->>R: new run_id
        R-->>RS: run_id
    end
    RS->>E: insert_events(conn, run_id, run.events)
    E->>E: refuse NaN or infinity before any row
    loop each event
        E->>PG: insert on conflict run_id, sensor_id, window_index do nothing
    end
    RS->>RS: readings_from_run, 60 s means for 8 sensors and 9 instruments
    RS->>D: insert_readings(conn, run_id, readings)
    D->>PG: executemany insert on conflict do nothing, NaN stored as NULL
    RS-->>C: run_id, nothing committed yet
    C->>PG: commit or rollback
```

*Save sequence: every write happens inside the caller's transaction, so a failure rolls back the run row, the events and the readings together.*

- `save_scenario_run(conn, run, *, mode, branch=None) -> UUID` calls `create_run` (status `running`,
  `scenario_id` and `sim_start_utc` of the run, `variant_seed` = the definition seed only when
  `variant_index` is set, else `NULL`), then `insert_events` and `insert_readings`. The scenario must
  exist in `plumetrace.scenarios` (foreign key), otherwise `ForeignKeyViolation`.
- `readings_from_run(run) -> list[Reading]` makes 60 s means (`READINGS_STEP_S = 60.0`, the same
  `window_means` as the replay export) for the 8 methane sensors (unit `ppm`) and the 9 instruments
  (unit from `BASELINES`); `t_s` is the window start. A minute with too few samples is NaN and is
  stored as `NULL`.
- No duplicates: every call to `save_scenario_run` makes a new run id with its own rows (re-saving a
  scenario run creates a new run). A saved run stays `status = 'running'` with `finished_at` null: known
  and accepted at Gate 3; Phase 5 Task 10 ends every run in a terminal status. Inserting
  the same events or readings again into the same run adds nothing (`on conflict do nothing` on the
  primary keys `(run_id, sensor_id, window_index)` and `(run_id, tag, t_s)`).
- No inversion result is stored. Any inversion result stored later must follow the rate display rule
  (interval p05/p50/p95 plus flags, suppressed when inconclusive, top `NONE` or at the grid edge,
  "model estimate" and "model probability" wording).

### Worked example: row counts of the three MVP scenarios

Readings are 17 tags (8 methane sensors and 9 instruments) times one reading per minute. Events are
the detection events of the committed run.

| Scenario | Duration | Readings per tag | Readings in all | Events |
|---|---|---|---|---|
| `s1_rod_packing` | 6 h | 360 | 6 120 | 3 |
| `s4_planned_blowdown` | 4 h | 240 | 4 080 | 2 |
| `s5_sensor_drift` | 6 h | 360 | 6 120 | 2 |

### What re-saving does

| Action | Result | Test |
|---|---|---|
| `save_scenario_run` twice with the same `ScenarioRun` | two run ids, each with its own rows | `test_run_store_idempotent.py::test_saving_twice_makes_two_separate_runs` |
| `insert_events` or `insert_readings` again into the **same** run | no rows added (first value wins) | `test_resaving_into_the_same_run_adds_no_rows`, `test_run_tables.py::test_events_are_idempotent` |
| A NaN minute | stored as `NULL` | `test_run_tables.py::test_readings_store_nan_as_null`, `test_run_store.py::test_readings_are_one_minute_means` |
| A scenario id that is not seeded | `ForeignKeyViolation` | `test_run_tables.py::test_unknown_scenario_is_rejected` |
| Rolling back the caller's transaction | nothing is stored | `test_run_tables_edges.py::test_repositories_do_not_commit` |
| Deleting a run | its events and readings go too | `test_deleting_a_run_cascades` |

Tests: `app/backend/tests/db/test_run_store.py` (60 s readings, run, events and series stored) and
`test_run_store_idempotent.py` (re-saving adds no rows; two saves are two separate runs).

### Example queries

Read-only, run in the Supabase SQL console or `psql` against the local database. Replace the run id.

```sql
-- runs of a scenario, newest first
select run_id, mode, status, started_at from plumetrace.runs
where scenario_id = 's1_rod_packing' order by started_at desc;

-- how many readings per tag a run has (expect 360 for a 6 h scenario)
select tag, count(*) from plumetrace.sensor_readings
where run_id = '00000000-0000-0000-0000-000000000000' group by tag order by tag;
```

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
| `20261120090000_create_run_tables.sql` | Creates `runs`, `events` and `sensor_readings` with constraints, one index (`events_run_id_idx`), table comments and RLS enabled (no policies). |

## Limits and known gaps

- **Runs stay `running`.** `save_scenario_run` does not end the run; `finished_at` stays null.
  Accepted at Gate 3. Phase 5 Task 10 must set a terminal status on every run row it creates.
- **No production caller.** `save_scenario_run` and the run repositories are used by the tests only.
- **Catalogue titles differ.** `scenarios.title` (seed) and `ScenarioDefinition.title` (code) are
  two sources for the same text and they differ. Likewise `seed` and `version` are not synchronised
  with the code. Nothing reads the database copy yet; align them before a UI or an agent does.
- **Variant index is not stored.** A variant is identified in code by `(id, variant_index)`. The
  database keeps only `variant_seed`.
- **No retention rule.** Each `save_scenario_run` adds about 4 000 to 6 000 reading rows. There is no
  cleanup; use `db reset` locally.
- **Replay does not read the database.** The static replay build reads the committed JSON files
  ([REPLAY.md](REPLAY.md)); the database is local and private.

## Operate (run from `app/`)

```bash
npx --yes supabase@3.1.0 start      # start the local stack (Docker must be running)
npx --yes supabase@3.1.0 db reset   # rebuild the database from migrations + seed.sql
npx --yes supabase@3.1.0 stop       # stop the stack
```

The database tests skip with a hint when Supabase is not running. With
`PLUMETRACE_REQUIRE_DB=1` (set by `python scripts/ci_local.py --full`) the same condition fails
instead. Run them with `cd app && PLUMETRACE_REQUIRE_DB=1 uv run pytest backend/tests/db -q`.

## Checkpoint tables

The LangGraph checkpoint tables (schema `langgraph`) are created by the LangGraph `PostgresSaver`
in Phase 5. They are not part of the migrations in this task.

## How to extend

- A new column or table is a **new** migration file with the next timestamp. Enable RLS on every new
  table, add no client policy, add the repository function and its tests, and update the ER diagram
  and the tables above in the same change.
- Repository functions never commit and never open a connection themselves.
- Keep idempotency at the row level (primary key or unique constraint plus `on conflict do nothing`)
  for anything a script may run twice.
