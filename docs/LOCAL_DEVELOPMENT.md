# Local development

Everything runs locally. There is no GitHub Actions CI and no deployment.

## Prerequisites

- Python 3.12
- uv 0.10.3
- Node >= 22.13
- Docker Desktop
- git

## Pinned versions

| Tool / package | Version | Notes |
|---|---|---|
| Python | 3.12 (`>=3.12,<3.13`) | local 3.12.0 |
| uv | 0.10.3 | local |
| Node.js | `>=22.13.0` | local 22.19.0 |
| pydantic | 2.14.3 | |
| pydantic-settings | 2.16.2 | |
| pyyaml | 6.0.3 | |
| psycopg[binary,pool] | 3.3.9 | |
| psycopg-pool | 3.3.3 | |
| numpy | 2.5.4 | added in Phase 2 |
| hatchling | 1.33.0 | build backend |
| pytest | 9.2.0 | dev |
| ruff | 0.17.5 | dev |
| mypy | 2.4.1 | dev |
| types-PyYAML | 6.0.12.20261111 | dev |
| pip-audit | 2.10.1 | dev |
| hypothesis | 6.170.14 | dev — property-based tests (released 2026-10-30; resolves with every pin) |
| pytest-cov | 7.1.0 | dev — coverage (brings coverage 7.17.3) |
| Supabase CLI | 3.1.0 | always `npx --yes supabase@3.1.0 …` |
| react, react-dom | 19.3.1 | |
| @types/react, @types/react-dom | 19.3.0 | |
| @types/node | 26.6.6 | |
| typescript | **6.0.3** | NOT 7.x — typescript-eslint 8.72.2 requires `<6.1` |
| vite | 8.3.8 | |
| @vitejs/plugin-react | 6.3.0 | |
| tailwindcss, @tailwindcss/vite | 4.3.5 | |
| eslint | 10.14.0 | |
| @eslint/js | 10.0.1 | |
| typescript-eslint | 8.72.2 | |
| eslint-plugin-react-hooks | 7.1.1 | |
| eslint-plugin-react-refresh | 0.5.7 | |
| eslint-plugin-jsdoc | 65.4.5 | |
| globals | 17.14.0 | |
| vitest | 5.1.0 | |
| @vitest/coverage-v8 | 5.1.0 | dev — must equal the vitest version (exact peer dependency) |
| jsdom | **29.1.1** | NOT 30/31 — those need Node ≥ 22.22 |
| @testing-library/react | 16.3.3 | |
| @testing-library/dom | 10.4.2 | peer of RTL |
| @testing-library/jest-dom | 7.0.1 | |
| json-schema-to-typescript | 16.0.0 | Task 7 |

## Configuration

Settings come from `plumetrace.config` (`app/backend/plumetrace/config.py`), the only Python module that reads configuration.

| Variable | Meaning |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (secret; the owner pastes it). |
| `LANGSMITH_API_KEY` | LangSmith API key (secret). |
| `LANGSMITH_TRACING` | `true` turns LangSmith tracing on; default off. |
| `LANGSMITH_PROJECT` | LangSmith project name; default `plumetrace-dev`. |
| `SUPABASE_DB_URL` | Postgres connection string of the local Supabase (secret). |

Only the root `.env` is read; never create other `.env` files. Values are never printed: secrets are
held as `SecretStr` and hidden from `repr`/`str`. Without a `.env` the settings load with defaults,
and database code raises `ConfigurationError` naming `SUPABASE_DB_URL`. Tests build
`Settings(_env_file=None)` so they never read the real `.env`.

## Python

All Python commands run from `app/` (the uv workspace root; members `backend` and `agents`).

```bash
cd app
uv sync                  # create .venv and install both packages plus the dev tools
uv run pytest -q         # run the tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy              # type-check (strict)
```

Tests use `--import-mode=importlib`; test folders have no `__init__.py`.

## Database

Local Supabase Postgres, run in Docker. Docker Desktop must be running first (`docker info` works).
Run these from `app/`:

```bash
npx --yes supabase@3.1.0 start      # start (first run pulls images)
npx --yes supabase@3.1.0 db reset   # rebuild from migrations + seed
npx --yes supabase@3.1.0 stop       # stop
```

The local database URL is `postgresql://postgres:postgres@127.0.0.1:54322/postgres` (public local
default). It is the value of `SUPABASE_DB_URL` in the root `.env`.

Tests in `app/backend/tests/db/` need the database. When it is not running they skip with a start
hint. With `PLUMETRACE_REQUIRE_DB=1` (set by `python scripts/ci_local.py --full`) the same condition
fails the test. Details: [reference/DATABASE.md](reference/DATABASE.md).

## Frontend

Filled in by Phase 1 Task 5.

## Checks

Run from the repo root:

```bash
python -I .claude/skills/repo-structure/scripts/check_structure.py .
python -I .claude/skills/security-checks/scripts/check_env.py .
python -I .claude/skills/security-checks/scripts/secret_scan.py .
```

Expected output: `structure OK`, `env OK`, `no secrets found`.
