# Configuration and the root `.env`

## Purpose and scope

PlumeTrace has one configuration source: the single `.env` file at the repository root, or the
process environment. This page explains how the backend loads it (`plumetrace.config`), how the
database connection pool uses it (`plumetrace.db.pool`), and how the three project scripts keep
`.env` safe (`env_set.py`, `check_env.py`, `secret_scan.py`).

It covers Phase 1 Task 3 (settings) and the configuration part of Task 4 (pool). It does not
cover the schema (see [DATABASE.md](DATABASE.md)) or the security threat model (see
[SECURITY.md](SECURITY.md)). Rule source: `CLAUDE.md` hard rule 9.

Rule 9 in one line: every secret and every environment setting lives in the root `.env`. No
other env file exists anywhere. Values are never printed, logged or committed.

## How it works

### Where a setting can come from

```mermaid
flowchart LR
    ENVVAR["Process environment variable"] --> S["Settings object"]
    DOTENV["Root .env file (REPO_ROOT/.env)"] --> S
    DEFAULT["Field default in config.py"] --> S
    S --> CACHE["get_settings (cached once per process)"]
    TEST["Tests build Settings with _env_file=None"] -. "skips the file" .-> DOTENV
    CACHE --> DB["require_db_url then create_pool"]
    EX[".env.example (names only, committed)"] -. "kept in sync by check_env.py" .-> DOTENV
```

Caption: a `Settings` object merges the process environment, the root `.env` and the field
defaults. Tests skip the file by passing `_env_file=None`.

`Settings` is a `pydantic_settings.BaseSettings`. Its `model_config` points `env_file` at
`ENV_FILE`, which is `REPO_ROOT / ".env"`. `REPO_ROOT` is computed as
`Path(__file__).resolve().parents[3]`, so it does not depend on the current working directory:
commands run from `app/` and from the repository root read the same file.

The merge order is the pydantic-settings default: an environment variable wins over the `.env`
file, and both win over a field default. The tests pin two parts of this
(`test_values_come_from_environment`: environment over default; `test_settings_defaults_without_env`:
defaults when nothing is set). They do not test the environment-over-`.env` order, because tests
never read the real `.env`.

`extra="ignore"` is set, so a variable in `.env` that has no field (for example
`OPENAI_MODEL_FAST`) is skipped silently, not rejected.

### Settings fields

All values below are the real code. Each field is read from the upper-case variable with the same
name.

| Field | Environment variable | Type | Default | Secret |
|---|---|---|---|---|
| `openai_api_key` | `OPENAI_API_KEY` | `SecretStr \| None` | `None` | yes |
| `langsmith_api_key` | `LANGSMITH_API_KEY` | `SecretStr \| None` | `None` | yes |
| `langsmith_tracing` | `LANGSMITH_TRACING` | `bool` | `False` | no |
| `langsmith_project` | `LANGSMITH_PROJECT` | `str` | `"plumetrace-dev"` | no |
| `supabase_db_url` | `SUPABASE_DB_URL` | `SecretStr \| None` | `None` | yes (see below) |

`SecretStr` hides the value in `repr()` and `str()`. Code that needs the real value calls
`get_secret_value()` at the point of use. `SUPABASE_DB_URL` is held as a secret even though the
local default (`postgresql://postgres:postgres@127.0.0.1:54322/postgres`) is public, because a
hosted URL would contain a real password.

### Names that `Settings` does not read yet

The root `.env` and `.env.example` list the first three names below. The fourth,
`PLUMETRACE_REQUIRE_DB`, is not in either file; it is an environment switch that the check runner
sets:

| Name | Kind | Who reads it today |
|---|---|---|
| `OPENAI_MODEL_FAST` | non-secret setting | no Python code (no `Settings` field yet) |
| `OPENAI_MODEL_REASONING` | non-secret setting | no Python code (no `Settings` field yet) |
| `PLUMETRACE_SPEND_CAP_USD` | owner-only setting | no Python code (no `Settings` field yet) |
| `PLUMETRACE_REQUIRE_DB` | test switch, set by `ci_local.py --full` (not in `.env`) | `app/backend/tests/db/conftest.py`, through `os.environ` |

A later phase adds `Settings` fields for the first three when the LLM wrapper needs them. The
spend cap is owner-only: `env_set.py` refuses to write it.

### Sequence: loading settings and creating the pool

```mermaid
sequenceDiagram
    participant Caller as Caller (API or test)
    participant Cfg as config.get_settings
    participant Set as Settings
    participant Req as config.require_db_url
    participant Pool as db.pool.create_pool
    participant PG as Local Postgres (Docker)

    Caller->>Cfg: get_settings()
    Cfg->>Set: Settings() on first call only
    Set-->>Cfg: values from env, .env, defaults
    Cfg-->>Caller: cached instance
    Caller->>Pool: create_pool(settings)
    Pool->>Req: require_db_url(settings)
    alt supabase_db_url is None
        Req-->>Pool: raise ConfigurationError naming SUPABASE_DB_URL
        Pool-->>Caller: error, no connection tried
    else URL present
        Req-->>Pool: plain URL string
        Pool->>PG: ConnectionPool(min_size=1, max_size=5, open=True)
        PG-->>Caller: open pool, caller closes it
    end
```

Caption: `get_settings` builds `Settings` once; `create_pool` fails before any network call when the
URL is missing.

Notes on this flow:

- `get_settings` uses `functools.lru_cache(maxsize=1)`. The first call reads `.env`; later calls
  return the same object. A change to `.env` needs a new process.
- `create_pool` takes a `Settings` argument. It never calls `get_settings` itself, so a test can
  hand it `Settings(_env_file=None)`.
- Today only `app/backend/tests/db/conftest.py` calls `get_settings()` and `psycopg.connect`
  directly. No application module calls `create_pool` yet; the API in
  `plumetrace.api` uses a connection passed in by its caller (`api/run_store.py`).

## Module reference

### `app/backend/plumetrace/config.py`

| Name | What it does | Why |
|---|---|---|
| `REPO_ROOT` | Repository root as an absolute `Path` | Makes the `.env` location independent of the working directory |
| `ENV_FILE` | `REPO_ROOT / ".env"` | The one allowed env file |
| `Settings` | Typed fields (table above), read from the environment and `.env` | One typed place for every setting |
| `ConfigurationError` | `RuntimeError` subclass | A named error callers can catch; the message names the variable |
| `get_settings()` | Cached `Settings()` | Parsing once per process |
| `require_db_url(settings)` | Returns the URL as a plain `str`, or raises `ConfigurationError` | The only place that calls `get_secret_value()` on the URL |

The error text is: `SUPABASE_DB_URL is not set: run npx --yes supabase@3.1.0 start in app/ and add
it to the root .env`. It names the variable and the fix and never prints a value.

### `app/backend/plumetrace/db/pool.py`

`create_pool(settings, *, min_size=1, max_size=5)` calls `require_db_url`, then builds a
`psycopg_pool.ConnectionPool(conninfo=url, min_size=..., max_size=..., open=True)`. The caller owns
the pool and closes it. The pool package is `psycopg_pool` 3.3.3 with `psycopg[binary,pool]` 3.3.9
(pins in `app/backend/pyproject.toml`).

## Worked example

A fresh clone has no `.env`. This is what the code does, using only values from the tests:

```python
from plumetrace.config import Settings, require_db_url

s = Settings(_env_file=None)       # what the tests do; get_settings() would read the root .env
s.openai_api_key                   # None
s.langsmith_tracing                # False
s.langsmith_project                # 'plumetrace-dev'
require_db_url(s)                  # raises ConfigurationError: SUPABASE_DB_URL is not set: ...
```

With `SUPABASE_DB_URL=postgresql://u:p@127.0.0.1:5432/db` in the environment, `require_db_url`
returns that exact string. `repr(Settings(...))` never contains an API key value, even when the
key is set: `test_secrets_are_not_revealed_in_repr` sets a fake key and asserts it is absent from
`repr` and `str`.

## Tooling that guards `.env`

All three scripts live in `.claude/skills/security-checks/scripts/` and run with `python -I`
(isolated mode: no user site-packages, no current directory on `sys.path`).

### `env_set.py`: the only way an agent writes `.env`

Agents never open `.env` with a read or edit tool, `cat`, `type`, `Get-Content` or `grep`; that
would load every secret into the conversation. They run `env_set.py` instead.

| Command | Effect | Prints a value? |
|---|---|---|
| `names` | Lists each name with `set` or `empty` | never |
| `get NAME` | Prints the value of a non-secret setting (`NAME` in `NON_SECRET_SETTINGS`) | only for non-secret names |
| `set NAME VALUE` | Writes a non-secret setting, or resets `SUPABASE_DB_URL` to its public local default | no |
| `add NAME [--comment TEXT]` | Adds `NAME` with an empty value for a key only the owner has; the owner pastes the value | no |
| `generate NAME [--bytes N]` | Writes a random secret (`secrets.token_urlsafe`, 16 to 64 bytes, default 32) | no |

Rules the script enforces (all in `env_set.py`):

- A name must match `^[A-Z][A-Z0-9_]{0,63}$`.
- `PLUMETRACE_SPEND_CAP_USD` is in `OWNER_ONLY`; every write command refuses it.
- `set` refuses any name that may hold a secret. `NON_SECRET_SETTINGS` is
  `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, `OPENAI_MODEL_FAST`, `OPENAI_MODEL_REASONING`.
- A value with a newline is refused.
- Writes are atomic: a temporary file in the same folder, then `os.replace`.
- Every write also adds the name, with an empty value, to `.env.example` if it is missing.

Example (names only, no values): `python -I .claude/skills/security-checks/scripts/env_set.py names`
prints one line per name, for example `SUPABASE_DB_URL set`.

### `check_env.py`: the single-`.env` rule

Prints `env OK` or one finding per problem. Findings name paths and variables, never values.

1. Stray env files: any `.env*` file other than the root `.env` and `.env.example` (for example
   `app/frontend/.env.local`) is a finding. Its own skip list is `.git`, `node_modules`, `.venv`,
   `__pycache__` and `skills`; env files inside those folders are not reported.
2. Names in sync: every name in `.env` is in `.env.example` and the reverse.
3. The example holds no secrets: values in `.env.example` must be empty, except
   `LANGSMITH_TRACING`, `LANGSMITH_PROJECT` and the public local `SUPABASE_DB_URL`.
4. Required values present: every name in `.env.example` has a non-empty value in `.env`.

When `.env` does not exist (a fresh clone, no local secrets yet), checks 2 and 4 are skipped and
the script can still print `env OK`.

### `secret_scan.py`: no secret leaves the machine

Two detectors run over every text file under the given paths (files larger than 5,000,000 bytes
found by walking a folder are skipped):

1. Known values: each value in `.env` that is at least 12 characters long is searched literally.
   Non-secret names and the public local database URL are excluded.
2. Key patterns: regular expressions for OpenAI keys, LangSmith keys, AWS access keys, private-key
   blocks and `*_API_KEY|SECRET|TOKEN = <16 or more characters>` assignments. A match that looks
   like a documentation placeholder (`your_`, `_here`, `example`, `<...>`) is ignored.

It prints `path:line: detector` and never the matched text. The only project path skipped is the
Supabase CLI cache `app/supabase/.temp` (pinned by `test_secret_scan.py`). Tool and cache folders
(`.git`, `node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`,
`.hypothesis`, `.coverage`) and the `.env` file itself are skipped as well; a `.temp` folder
anywhere else is scanned.

## Edge cases and failure modes

| Case | Behaviour | Pinned by |
|---|---|---|
| No `.env`, no variables | `Settings` loads defaults; secrets are `None` | `test_config.py::test_settings_defaults_without_env` |
| Environment variable set | It overrides the default | `test_config.py::test_values_come_from_environment` |
| Secret in `repr`/`str` | Never shown | `test_config.py::test_secrets_are_not_revealed_in_repr` |
| `SUPABASE_DB_URL` missing | `ConfigurationError` naming the variable | `test_config.py::test_require_db_url_names_the_variable` |
| `SUPABASE_DB_URL` set | Plain string returned | `test_config.py::test_require_db_url_returns_plain_value` |
| `.env` location | `REPO_ROOT / ".env"`, next to `CLAUDE.md` | `test_config.py::test_env_file_points_at_repo_root` |
| Pool without URL | `ConfigurationError` before any connection | `test_db_pool.py::test_create_pool_without_url_raises` |
| Key-like text in docs | Reported by detector name only | `test_secret_scan.py::test_key_is_reported_without_its_value` |
| `.temp` folders | `app/supabase/.temp` is the only project path skipped (tool and cache folders and `.env` itself too); other `.temp` folders are scanned | `test_secret_scan.py` (two tests) |

Not covered by an automated test: `env_set.py` and `check_env.py` have no unit tests. Run
`check_env.py` after any `.env` change.

## How to run

From the repository root. On Windows PowerShell the commands are the same; only the quoting of
environment variables differs.

```powershell
python -I .claude/skills/security-checks/scripts/check_env.py .      # expect: env OK
python -I .claude/skills/security-checks/scripts/secret_scan.py .    # expect: no secrets found
python -I .claude/skills/security-checks/scripts/env_set.py names    # names only
cd app; uv run pytest -q backend/tests/test_config.py backend/tests/test_db_pool.py
```

To override one setting for a single shell (PowerShell): `$env:LANGSMITH_TRACING = "false"`. In
Git Bash: `LANGSMITH_TRACING=false uv run pytest -q`.

## How to extend

Add a setting in these steps, in one change:

1. Add the field to `Settings` with a type, a default, and a line in the `Attributes:` docstring.
   Use `SecretStr` for a secret.
2. Add the name to `.env.example` and `.env` through `env_set.py` (`set` for a non-secret
   setting, `add` for an owner-supplied key, `generate` for a secret the project creates). Never
   edit the files by hand and never create another env file.
3. For a non-secret setting, add the name to `NON_SECRET_SETTINGS` in `env_set.py` and to
   `NON_SECRET_NAMES` in `secret_scan.py`, as `CLAUDE.md` rule 9 requires. If `.env.example` should
   hold a default value for it, also add it to `NON_SECRET_EXAMPLE_VALUES` in `check_env.py`.
4. Add a test in `app/backend/tests/test_config.py` (default and override) and add the name to its
   `ENV_NAMES` list so the test clears it.
5. Update the table on this page, the table in [LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md), and
   `docs/WORK_LOG.md`.
6. Run `python -I .claude/skills/security-checks/scripts/check_env.py .` and
   `python -I .claude/skills/security-checks/scripts/secret_scan.py .`.

Invariants to keep: only `config.py` reads configuration (the test switch
`PLUMETRACE_REQUIRE_DB` in `tests/db/conftest.py` is the one documented exception and is test-only);
no secret is ever printed, logged or sent to the frontend; the frontend reads no env file.

## Known inconsistencies

These came up while documenting; they are recorded, not fixed here.

- `secret_scan.py` `NON_SECRET_NAMES` lists only `LANGSMITH_TRACING` and `LANGSMITH_PROJECT`, while
  `env_set.py` `NON_SECRET_SETTINGS` also lists `OPENAI_MODEL_FAST` and `OPENAI_MODEL_REASONING`.
  `CLAUDE.md` rule 9 says the two lists change together. There is no practical effect today
  because the model-name values are shorter than the 12-character threshold of the known-value
  detector.
- The `env_set.py` module docstring mentions `scripts/set_app_role_password.py`, which does not
  exist in the repository.
- `.env.example` sets `LANGSMITH_TRACING=true`, while the `Settings` default is `False`. A fresh
  clone without `.env` therefore has tracing off, and copying `.env.example` turns it on.

## Related

- Code: `app/backend/plumetrace/config.py`, `app/backend/plumetrace/db/pool.py`
- Scripts: `.claude/skills/security-checks/scripts/`
- Pages: [DATABASE.md](DATABASE.md), [SECURITY.md](SECURITY.md), [CHECKS.md](CHECKS.md),
  [WORKSPACE.md](WORKSPACE.md), [../LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md)
