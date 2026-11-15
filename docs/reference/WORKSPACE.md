# Workspace and local stack

## Purpose and scope

This page describes how the repository is put together so that it builds and runs on a fresh
clone: the repository bootstrap files, the uv workspace with its two Python packages, the tool
settings (Ruff, mypy, pytest, coverage), the local Supabase stack with the first migration and the
seed, and the shell of the Vite and React app. It covers Phase 1 Tasks 1, 2, 4 and 5.

It does not repeat what other pages own: the layout rules are in [STRUCTURE.md](STRUCTURE.md),
settings and `.env` in [CONFIGURATION.md](CONFIGURATION.md), every table and column in
[DATABASE.md](DATABASE.md), the frontend features and design tokens in [FRONTEND.md](FRONTEND.md),
the Vercel headers in [DEPLOYMENT.md](DEPLOYMENT.md), and the check runner in
[CHECKS.md](CHECKS.md). Nothing here is deployed: the public replay build is built and previewed
locally only.

## Architecture

### Containers and boundaries

```mermaid
flowchart LR
    subgraph REPO["Repository (one git repo, one root .env)"]
        subgraph UV["uv workspace: app/pyproject.toml, one shared .venv"]
            BE["backend: package plumetrace"]
            AG["agents: package plumetrace_agents"]
        end
        FE["frontend: React, TypeScript, Vite"]
        SB["supabase: config.toml, migrations, seed.sql"]
        SC["scripts: ci_local.py, export_contract.py"]
    end
    BE -->|"workspace dependency"| AG
    BE -->|"psycopg pool, SUPABASE_DB_URL"| PG[("Local Postgres 17 in Docker")]
    SB -->|"supabase start and db reset apply"| PG
    FE -->|"HTTP /api proxy in dev"| BE
    SC -->|"generates types and ks07.json"| FE
```

Caption: the two Python packages share one environment and depend in one direction (backend on
agents); only the backend talks to Postgres; the frontend never connects to the database.

The arrow from the backend to the agents is the only allowed direction; `check_structure.py`
rejects an import the other way (see [CHECKS.md](CHECKS.md)). At the end of Phase 1 the agents
package only held its version string; later phases fill it.

### Repository bootstrap (Phase 1 Task 1)

| File | Purpose |
|---|---|
| `LICENSE` | MIT licence, "Copyright (c) 2026 PlumeTrace contributors" |
| `.gitattributes` | `* text=auto eol=lf`; binary rules for `png jpg glb webp hdr exr pdf`. Makes generated files identical on Windows and Linux |
| `.gitignore` | Keeps `.env` and `.env.*` out (but not `.env.example`), Python and Node caches, `app/supabase/.temp/`, `build/`, `dist/`, `app/frontend/public/replay/` and coverage output |
| `README.md` | Public entry point: what PlumeTrace is, links to the design, local development and the docs index; states the station is fictional and simulated |
| `docs/` | `README.md` index, `WORK_LOG.md`, `OWNER_ACTIONS.md`, `LOCAL_DEVELOPMENT.md`, `reference/` |
| `app/.python-version` | `3.12` |

## The uv workspace (Phase 1 Task 2)

`app/pyproject.toml` is the workspace root and is not a package (`[tool.uv] package = false`). Its
members are `backend` and `agents`; both resolve from the workspace through
`[tool.uv.sources]`. One lock file (`app/uv.lock`) and one virtual environment (`app/.venv`)
serve both.

| Project | Name on PyPI-style metadata | Import package | Dependencies (exact pins) |
|---|---|---|---|
| `app/backend` | `plumetrace` 0.1.0 | `plumetrace` | `pydantic==2.14.3`, `pydantic-settings==2.16.2`, `pyyaml==6.0.3`, `numpy==2.5.4`, `psycopg[binary,pool]==3.3.9`, `psycopg-pool==3.3.3`, `httpx==0.28.1`, `fastapi==0.162.5`, `uvicorn[standard]==0.54.0`, `plumetrace-agents` (workspace) |
| `app/agents` | `plumetrace-agents` 0.1.0 | `plumetrace_agents` | `pydantic==2.14.3` |

Both use `hatchling==1.33.0` as the build backend and ship only their package folder
(`[tool.hatch.build.targets.wheel] packages`). `numpy` arrived in Phase 2 and `httpx`, `fastapi`
and `uvicorn` in a later phase; the rest is Phase 1. Python is `>=3.12,<3.13`.

Dev tools are in the root `[dependency-groups] dev`, all exact:
`pytest==9.2.0`, `ruff==0.17.5`, `mypy==2.4.1`, `types-PyYAML==6.0.12.20261111`,
`pip-audit==2.10.1`, `hypothesis==6.170.14`, `pytest-cov==7.1.0`.

### Tool settings in `app/pyproject.toml`

| Tool | Setting | Why |
|---|---|---|
| Ruff | `line-length = 100`, `target-version = "py312"` | One style |
| Ruff lint | `select = E,F,W,I,B,UP,D,S,ANN,N`; pydocstyle `convention = "google"` | Docstrings on everything, security rules (`S`), annotations, naming |
| Ruff isort | `known-first-party = plumetrace, plumetrace_agents, evals` | Stable import blocks |
| Ruff per-file | `**/tests/**` ignores `S101` and `ANN` | Tests use `assert` and need no annotations |
| mypy | `strict = true`, plugin `pydantic.mypy`, packages `plumetrace`, `plumetrace_agents` | Strict typing for both packages (not for `scripts/`) |
| pytest | `testpaths = backend/tests, agents/tests`; `--import-mode=importlib`; `pythonpath = ["backend"]` | Test folders have no `__init__.py`; `pythonpath` lets tests import the `benchmark` package that sits beside `plumetrace` |
| pytest markers | `db`, `slow`, `fuzz` | `db` needs local Supabase; `slow` is skipped in quick checks; `fuzz` is Phase 6 |
| coverage | `branch = true`, `source = plumetrace, plumetrace_agents` | Branch coverage for the 85 % threshold in full mode |

### Smoke tests

`app/backend/tests/test_package.py` asserts that `plumetrace.__version__ == "0.1.0"` and that
`plumetrace_agents` imports from the backend environment. `app/agents/tests/test_package.py`
asserts the agents version. They prove the workspace installs and that the dependency direction is
importable.

## Local Supabase (Phase 1 Task 4)

### Bootstrap sequence

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CLI as npx supabase 3.1.0
    participant Dock as Docker Desktop
    participant PG as Postgres 17 container
    participant Mig as app/supabase/migrations
    participant Seed as app/supabase/seed.sql

    Dev->>CLI: npx --yes supabase@3.1.0 start (in app/)
    CLI->>Dock: pull images on first run, start containers
    Dock->>PG: database on port 54322
    CLI->>Mig: apply files in filename order
    Mig->>PG: create schema plumetrace, tables, enable RLS
    CLI->>Seed: run seed.sql
    Seed->>PG: insert reference rows
    Dev->>CLI: npx --yes supabase@3.1.0 db reset
    CLI->>PG: rebuild from migrations and seed
```

Caption: `start` brings up the containers and applies the migrations and the seed; `db reset`
rebuilds the database from the same files.

`app/supabase/config.toml` (created by `supabase init`) sets `project_id = "app"`, the API on
54321, Postgres on 54322 (major version 17), Studio on 54323, migrations enabled, and
`[db.seed] sql_paths = ["./seed.sql"]`. Its `[api] schemas` lists only `public` and
`graphql_public`, so the `plumetrace` schema is not served by the Supabase REST API.
`app/supabase/.gitignore` keeps the CLI's `.branches` and `.temp` folders out of git.

### The first migration

File: `app/supabase/migrations/20261113090000_create_plumetrace_schema.sql`. It creates the schema
`plumetrace` and the table `plumetrace.scenarios`, then `alter table ... enable row level
security`. It defines no policy. The header states the intent: only the backend, as the database
owner, reads and writes; never edit an applied migration; add a new one.

```mermaid
erDiagram
    SCENARIOS {
        text id PK "format s, digits, underscore, slug"
        text title "not null"
        bigint seed "not null"
        integer version "default 1"
        boolean is_mvp "not null"
        timestamptz created_at "default now"
    }
    RUNS {
        uuid run_id PK
        text scenario_id FK
    }
    SCENARIOS ||--o{ RUNS : "scenario_id (later migration)"
```

Caption: Phase 1 creates only `scenarios`; the `runs` table (second migration,
`20261120090000_create_run_tables.sql`) points at it with a foreign key. All columns of `runs` are
in [DATABASE.md](DATABASE.md).

Seed rows (`app/supabase/seed.sql`, inserted with `on conflict (id) do nothing`, so reruns are
safe):

| id | title | seed | version | is_mvp |
|---|---|---|---|---|
| `s1_rod_packing` | Rod packing failure, K-202 | 101 | 1 | true |
| `s4_planned_blowdown` | Planned blowdown, compressor K-201 | 104 | 1 | true |
| `s5_sensor_drift` | Sensor drift, AT-106 | 105 | 1 | true |

### How database tests choose between skip and fail

```mermaid
flowchart TD
    A["db_conn fixture"] --> B{"SUPABASE_DB_URL set?"}
    B -->|"no"| E["ConfigurationError"]
    B -->|"yes"| C["psycopg.connect, connect_timeout 3 s"]
    C -->|"connected"| OK["yield connection, close afterwards"]
    C -->|"OperationalError"| E
    E --> D{"PLUMETRACE_REQUIRE_DB equals 1?"}
    D -->|"yes"| F["pytest.fail: database required but unavailable"]
    D -->|"no"| G["pytest.skip with the start hint"]
```

Caption: the same unavailable-database condition skips locally and fails in full mode, so a phase
gate can never pass without having run the database tests.

`app/backend/tests/db/conftest.py` marks every test in the folder with the `db` marker and holds
`START_HINT = "Supabase not running: run `npx --yes supabase@3.1.0 start` in app/"`.

### Schema tests (`app/backend/tests/db/test_schema.py`)

| Test | Proves |
|---|---|
| `test_every_plumetrace_table_has_rls` | Every table in schema `plumetrace` has `relrowsecurity` true and at least one table exists |
| `test_no_client_policies_exist` | `pg_policies` has zero rows for schema `plumetrace` |
| `test_mvp_scenarios_are_seeded` | The three MVP scenario ids exist after migrations and seed |

These tests describe the current database: later migrations add tables, and the first test checks
all of them.

## The frontend shell (Phase 1 Task 5)

The shell is `app/frontend/` with Vite 8.3.8, React 19.3.1, TypeScript 6.0.3 and Tailwind 4.3.5
(exact pins in `package.json`). The panels, data layer and design tokens that grew on top of it
are described in [FRONTEND.md](FRONTEND.md).

| File | What it does |
|---|---|
| `index.html` | One `div#root`, loads `/src/main.tsx` as a module; title `PlumeTrace` |
| `src/main.tsx` | Imports the local IBM Plex font files, mounts `AppShell` in `StrictMode`; throws `Root element #root not found in index.html` if the root is missing |
| `vite.config.ts` | Plugins `react()` and `tailwindcss()`; alias `@` to `src`; dev proxy `/api` to `http://127.0.0.1:8000`; Vitest block (jsdom, setup file, v8 coverage with thresholds lines 80, functions 80, branches 70, statements 80; excludes tests, `main.tsx`, generated types, test helpers and the 3D scene folder) |
| `tsconfig.json` | `strict`, `noUncheckedIndexedAccess`, `noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`, `moduleResolution: bundler`, `noEmit`; path alias `@/*` |
| `eslint.config.js` | `@eslint/js` and typescript-eslint recommended, `react-hooks` rules, `react-refresh/only-export-components` (warn), and `jsdoc/require-jsdoc` (error) for public functions, arrow functions and classes; ignores `dist`, `node_modules` and the generated types |
| `components.json` | shadcn settings (style `new-york`, aliases under `@/shared`) |
| `vercel.json` | Security headers and an SPA rewrite, recorded for a later phase and pinned by `src/app/vercelConfig.test.ts`; see [DEPLOYMENT.md](DEPLOYMENT.md) |

Facts worth knowing:

- The browser build holds no secret and reads no env file; there are no `VITE_*` variables.
- `connect-src 'self'` in `vercel.json` means the public build calls only its own origin.
- TypeScript is pinned to 6.0.3 because `typescript-eslint` 8.72.2 requires a version below 6.1;
  `jsdom` is pinned to 29.1.1 because newer versions need Node 22.22 or newer. Do not bump either
  without checking the peer ranges.

## Worked example: a fresh clone

1. `git clone`, then `python scripts/install_git_hooks.py`.
2. `cd app && uv sync --frozen` creates `app/.venv` from `uv.lock` with both packages and the dev
   tools.
3. `uv run pytest -q backend/tests/test_package.py agents/tests` passes (3 tests): the workspace is
   wired. No `.env` exists yet, and nothing needs it.
4. `uv run pytest -q backend/tests/test_config.py` passes: settings load their defaults.
5. `uv run pytest -q backend/tests/db` skips every database test with the start hint (Supabase is not
   running). With Docker Desktop running: `npx --yes supabase@3.1.0 start`, add `SUPABASE_DB_URL`
   to the root `.env` (the local default is
   `postgresql://postgres:postgres@127.0.0.1:54322/postgres`; use
   `python -I .claude/skills/security-checks/scripts/env_set.py set SUPABASE_DB_URL <that value>`),
   then the same command runs the tests for real.
6. `cd frontend && npm ci && npm run test` runs the Vitest suite.

## Edge cases and failure modes

| Case | Behaviour | Test or check |
|---|---|---|
| Fresh clone without `.env` | Settings load defaults; DB code raises an error naming `SUPABASE_DB_URL` | `test_config.py`, `test_db_pool.py` |
| Supabase not running | `db` tests skip with a start hint; fail with `PLUMETRACE_REQUIRE_DB=1` | `tests/db/conftest.py` |
| Table created without RLS | `test_every_plumetrace_table_has_rls` fails | `tests/db/test_schema.py` |
| Someone adds an `anon` or `authenticated` policy | `test_no_client_policies_exist` fails | `tests/db/test_schema.py` |
| Agents package imports the backend | `check_structure.py` reports `forbidden import` | stage `structure` |
| Windows vs Linux generated files | LF, sorted keys, UTF-8 | `.gitattributes`, `test_export_contract.py` |
| Vercel header value changed | Vitest fails | `src/app/vercelConfig.test.ts` |
| Peer or resolution conflict on `npm ci` or `uv sync` | Stop and report; do not change a pin (Rule 2) | plan Phase 1 README |

## How to run

```bash
cd app
uv sync --frozen                          # or: uv sync
uv run pytest -q                          # all Python tests (db tests skip without Supabase)
uv run ruff check .
uv run mypy
npx --yes supabase@3.1.0 start            # needs Docker Desktop
npx --yes supabase@3.1.0 db reset
npx --yes supabase@3.1.0 stop
cd frontend
npm ci
npm run dev                               # http://localhost:5173
```

PowerShell notes: use `;` instead of `&&` to chain commands in Windows PowerShell 5.1; Docker
Desktop must be running before `supabase start` (`docker info` works); quote paths that contain
spaces. All commands are the same as in Git Bash otherwise.

## How to extend

- Add a Python dependency: pin it exactly in the member's `pyproject.toml`, run `uv lock` (or
  `uv sync`), check the library's current docs first (rule 1), add it to the pinned table in
  [LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md), and update this page. The agents package must
  not depend on the backend.
- Add a database table: write a new migration file named `YYYYMMDDHHMMSS_<name>.sql` in
  `app/supabase/migrations/` (at most 300 lines), enable RLS in it, add no client policy, never
  edit an applied migration, then `db reset` and run `tests/db`. Document the table in
  [DATABASE.md](DATABASE.md) (rules 17 and 19).
- Add a frontend dependency: exact version in `package.json`, lockfile updated, docs checked, the
  pinned table updated.

Invariants to keep: one workspace, one `.venv`; backend depends on agents and never the reverse;
schema `plumetrace` with RLS on every table and no client policy; the frontend holds no secret and
never connects to Supabase or OpenAI.

## Related

- Code: `app/pyproject.toml`, `app/backend/pyproject.toml`, `app/agents/pyproject.toml`,
  `app/supabase/`, `app/frontend/`
- Pages: [STRUCTURE.md](STRUCTURE.md), [CONFIGURATION.md](CONFIGURATION.md),
  [DATABASE.md](DATABASE.md), [FRONTEND.md](FRONTEND.md), [CHECKS.md](CHECKS.md),
  [../LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md)
