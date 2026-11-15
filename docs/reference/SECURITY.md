# Security

Reference for security controls as they exist in the code. The process (quick gate, full gate,
hardening phase, release gate) is described in the `security-checks` project skill; this page
records what the code does today and is extended by later tasks. It states only what is implemented.
Status date of this revision: 2026-11-15 (Phases 1 to 4 Task 4).

Related pages: [CONFIGURATION.md](CONFIGURATION.md) (settings and `.env` in depth),
[DATABASE.md](DATABASE.md) (schema and RLS), [API.md](API.md), [DATA_LAYER.md](DATA_LAYER.md),
[CHECKS.md](CHECKS.md) (the local check stages), [DEPLOYMENT.md](DEPLOYMENT.md) (headers recorded for
a later phase).

## Scope and posture

PlumeTrace runs entirely on the developer's machine: a FastAPI process, a local Supabase Postgres in
Docker, and a Vite dev server or a static replay build. Nothing is deployed (rule 27). The station is
fictional and every station value is simulated, so there is no operational data to protect. What
needs protection is the owner's API keys (OpenAI, LangSmith), the integrity of the repo, and the
habits that keep a later deployment safe. No call to OpenAI or LangSmith exists in the code yet (only
their setting names are in `config.py`); when they are added, they get a row in the outbound table in
the same change.

## Trust boundaries

```mermaid
flowchart TB
    subgraph Host["Developer machine"]
        Env[".env at repo root<br/>git-ignored, secrets"]
        Cfg["plumetrace.config<br/>only reader of .env"]
        Pool["db.pool<br/>connection pool"]
        API["FastAPI<br/>127.0.0.1:8000"]
        DB[("Local Supabase Postgres<br/>:54322, RLS on")]
        Vite["Vite dev server :5173"]
        Browser["Browser: React app<br/>no secret, relative URLs"]
        Replay["app/replay/ JSON<br/>simulated data only"]
        Script["scripts/fetch_weather.py<br/>run by hand"]
    end
    Meteo["archive-api.open-meteo.com<br/>HTTPS, public, no key"]
    Env --> Cfg
    Cfg --> Pool
    Pool --> DB
    Browser -->|"/api via proxy, CORS allow-list"| Vite
    Vite --> API
    API -.->|"not wired yet: no route touches the DB"| DB
    Browser -->|"/replay/ static"| Replay
    Script -->|"timeout 20 s, TLS verified"| Meteo
```

Zones and flows. The only outbound call is the manual weather refresh. The browser never talks to
Postgres, OpenAI or Open-Meteo. No module under `plumetrace/api/` reads the settings, and no route
calls the database (`run_store.py` is unrouted); the dotted edge is the future path. Repository code
in `plumetrace/db/` passes parameterised SQL through the pool.

| Boundary | Crossing | Control in code | Evidence |
|---|---|---|---|
| Repo to disk | secrets in `.env` | one root `.env`, git-ignored; `.env.example` names only; `env_set.py` is the only agent writer; `check_env.py` and `secret_scan.py` | `app/backend/tests/test_secret_scan.py`; `ci_local.py` stages `env`, `secrets` |
| Process to process | backend to Postgres | direct URL from settings, parameterised queries, RLS on every table | `tests/db/test_schema.py`, `tests/test_config.py` |
| Network inbound | browser to API | bind `127.0.0.1`, CORS allow-list, generic errors | `tests/api/test_api.py` |
| Network outbound | script to Open-Meteo | fixed host, timeout, TLS, no secret, no network in tests | `tests/data_sources/`, `tests/test_fetch_weather.py` |
| Build output | static bundle to a public host (later) | live-API code excluded, bundle check, no env file read, no secret in frontend | `src/app/checkReplayBundle.test.ts` |

## Outbound network

Status on 2026-11-14, unchanged: the repository makes exactly **one** kind of outbound call, to the
free public Open-Meteo archive API.

| Call | Host | Where in the code | When it runs | Data sent | Data received |
|---|---|---|---|---|---|
| Historical weather | `archive-api.open-meteo.com` (HTTPS) | `plumetrace/data_sources/open_meteo.py`, started by `scripts/fetch_weather.py` | Only when a developer runs the script by hand to refresh the snapshot. The backend and the tests never call it | Latitude and longitude of the fictional KS-07 site, a date range, the five weather variable names, `wind_speed_unit=ms`, `timezone=UTC` | Hourly ERA5 weather (public data, CC BY 4.0) |

```mermaid
sequenceDiagram
    participant D as Developer
    participant S as fetch_weather.py
    participant O as open_meteo.py
    participant M as archive-api.open-meteo.com
    participant F as weather snapshot file
    D->>S: run by hand
    S->>O: fetch hourly weather
    O->>M: GET over HTTPS, timeout 20 s, no key
    alt answer valid
        M-->>O: hourly ERA5 data
        O-->>S: validated series
        S->>F: write snapshot
    else timeout, bad status or invalid data
        M-->>O: error or bad body
        O-->>S: exception
        S-->>D: reason on stderr, exit 1, nothing written
    end
```

The manual refresh. A failed refresh never leaves a partial or altered snapshot.

Controls in `data_sources/open_meteo.py`:

- **Fixed host.** The URL is the constant `ARCHIVE_URL`. No part of it comes from user input, a
  request, a database row or a file, so there is no server-side request forgery path.
- **Timeout.** Every request passes `timeout=TIMEOUT_S` (20 s). A timeout is raised to the caller
  (`httpx.TimeoutException`), never swallowed or retried silently.
- **TLS is verified.** The module and the script use the httpx default (certificate verification on)
  and never pass a `verify` argument. A test fails if the word appears in either file.
- **No secret and no user data in the request.** The API needs no key. The query holds only the
  parameters in the table above (a test asserts the exact set of query names and that no
  `Authorization` header is sent). The `User-Agent` is the httpx default (`python-httpx/<version>`);
  no name, email or machine identifier is added. The server that answers sees the IP address of the
  machine that runs the script, as with any HTTP request.
- **Errors are visible.** A non-2xx status raises `httpx.HTTPStatusError`. A `null` value, a missing
  field, a gap or shift in the time axis, an unphysical value or a wind unit other than m/s raises
  `OpenMeteoError`. `fetch_weather.py` then prints the reason to stderr, exits 1 and writes nothing, so
  a failed refresh never leaves a partial or altered snapshot.
- **No network in tests.** The Open-Meteo tests and the script tests use `httpx.MockTransport`.

The committed snapshot is generated output. It is read by `plumetrace/simulator/weather.py`, which
rejects a file with gaps, so a bad snapshot cannot reach a scenario.

Licence and terms (checked against the Open-Meteo licence and terms pages on 2026-11-14): the API data
is offered under CC BY 4.0, free of charge for non-commercial use within the published rate limits,
which the single manual fetch of one week is far below. The attribution text is stored in the
snapshot and must be shown, with a link to <https://open-meteo.com/>, wherever the weather data is
displayed.

## Settings and secrets

Full explanation: [CONFIGURATION.md](CONFIGURATION.md). Controls:

- **One file.** `.env` at the repo root holds every secret and setting. `.gitignore` ignores `.env`
  and `.env.*` and keeps `!.env.example`. No other env file may exist anywhere;
  `check_env.py` reports a stray one by path and fails.
- **One reader.** `plumetrace/config.py` (`pydantic-settings`, `env_file` pointing at the repo-root
  `.env`) is the only Python module that reads configuration. Agents will get values injected.
- **Secrets are not printable.** `openai_api_key`, `langsmith_api_key` and `supabase_db_url` are
  `SecretStr`: hidden in `repr` and `str`; `get_secret_value()` is called only where the value is used
  (`require_db_url`). Tests build `Settings(_env_file=None)` so they never read the real `.env`.
- **Missing value is a named error.** `require_db_url` raises `ConfigurationError` naming
  `SUPABASE_DB_URL` (the name, never a value) before any connection is tried.
- **Agents write `.env` only through `env_set.py`** (names only in output; random secrets are never
  printed; every write also adds the name to `.env.example`; the spend cap is owner-only). Reading
  `.env` with a read tool, `cat` or `grep` is forbidden by rule 9.
- **Scanner.** `secret_scan.py` searches every repo file outside a small skip list (`.git`,
  `node_modules`, `.venv`, caches, `app/supabase/.temp`, `.env` itself) with two detectors: every value
  in `.env` that is at least 12 characters long is searched for literally (a hit means a real key
  leaked), and key patterns (OpenAI, LangSmith, AWS, private-key blocks,
  `*_API_KEY`/`SECRET`/`TOKEN` assignments). It prints `no secrets found`, or the file path, line
  number and detector or variable name; never the matched text. `app/replay/`, `app/frontend/public/replay/`
  and a built `dist/` are not on the skip list, so they are scanned when present.
- **Commands (repo root):** `python -I .claude/skills/security-checks/scripts/check_env.py .` must
  print `env OK`; `python -I .claude/skills/security-checks/scripts/secret_scan.py .` must print
  `no secrets found`. Both run in `python scripts/ci_local.py`.

## Local database

Details: [DATABASE.md](DATABASE.md#row-level-security).

- **Local only.** The URL in `SUPABASE_DB_URL` is the public local Supabase default
  (`postgresql://postgres:postgres@127.0.0.1:54322/postgres`); the check scripts treat exactly that
  value as non-secret and any other value as secret.
- **RLS on, no policies.** RLS is enabled on every table in schema `plumetrace` (`scenarios`, `runs`,
  `events`, `sensor_readings`) and no policy exists for `anon` or `authenticated`. Only the backend
  connects, as the database owner, which bypasses RLS. If Supabase's REST API were reachable, the
  tables would expose no rows. `tests/db/test_schema.py` checks RLS on every table and that no policy
  exists. The local Supabase config (`app/supabase/config.toml`) lists the exposed API schemas as
  `public` and `graphql_public`; schema `plumetrace` is not in that list.
- **Parameterised SQL.** The repository modules (`plumetrace/db/runs.py`, `events.py`, `readings.py`)
  pass values as `%s` parameters. Ruff's `S` rules (bandit) run in the lint stage.
- **Migrations only.** Schema changes happen only through new files in `app/supabase/migrations/`.
- **No DB access from the API routes yet.** `plumetrace/api/run_store.py` can write a run, its events
  and its readings; no route calls it.
- **Not yet in place:** a least-privilege application role (Phase 6 Task 5), stored LLM calls and
  logs (later phases).

## API

Status on 2026-11-15 (Phase 4 Task 1): the FastAPI app serves health, the scenario list and the
scenario replay. Details: [API.md](API.md).

- **Localhost bind.** The server runs with `--host 127.0.0.1`; it is not reachable from the network.
- **CORS allow-list.** `ALLOWED_ORIGINS` holds only `http://localhost:5173` and
  `http://127.0.0.1:5173`; methods `GET` and `POST`, header `Content-Type` (Starlette also always
  allows `Accept`, `Accept-Language`, `Content-Language`), no credentials. A test checks that another
  origin gets no `Access-Control-Allow-Origin` header. CORS restricts browsers only; it is not
  authentication, and a local non-browser client can still call the API.
- **No echo.** An unknown scenario id gives `404` with the fixed body `{"detail": "unknown
  scenario"}`; the id is never reflected (a test sends `<script>`). The id is only a key into a fixed
  registry; it never reaches a file path, SQL or a command.
- **Generic errors.** No stack trace or internal detail is returned by these endpoints.
- **No secrets, no inversion.** The responses hold the simulated station only: no key, no database
  value, no inversion rate and no AI output. `keyframes[].sources[].rate_kg_h` is simulation input for
  drawing the plume only.
- **Work is bounded.** Only three scenario ids exist and results are cached (8 entries). An unknown
  id is not cached and costs about 40 ms per request (it re-reads the facility spec and the weather
  snapshot before the `KeyError`); no rate limit exists until Phase 6.

## Frontend

Code: `app/frontend/src`. Details: [DATA_LAYER.md](DATA_LAYER.md), [UI_PANELS.md](UI_PANELS.md).

- **No secret, no env file.** The frontend reads no env file and holds no secret. The only
  `import.meta.env` use is `MODE` in `getDataSource.ts`. `check_env.py` fails on any `app/frontend/.env*`.
- **Relative URLs only.** The one `fetch` call (`shared/data/fetchJson.ts`) takes a relative path built
  by `LiveSource` (`/api/...`) or `ReplaySource` (`/replay/...`). No `http://` or `https://` URL is
  written in the app code (searched 2026-11-15, test files and generated types excluded).
- **Ids are validated before a URL is built.** `isScenarioId` accepts `^s[0-9]+_[a-z0-9_]+$`; `../x`,
  `s1/../x`, `s1_a/b`, `S1_Rod_Packing` and an empty id give `not_found` and `fetch` is never called
  (`LiveSource.guard.test.ts`). `?scenario=` from the address bar is used only if it is in the loaded
  list.
- **Data is validated.** Replay bodies must have `schema_version` 1, `simulated: true`, the requested
  id and consistent lengths, or the load fails as `invalid`.
- **Error text comes from a fixed table.** The UI chooses its message from the error `kind`; the
  developer message (which may contain a URL or a status) is never rendered.
- **No injection sinks.** The app code has no `dangerouslySetInnerHTML`, `innerHTML`, `eval`, or
  `localStorage` / `sessionStorage` use (searched 2026-11-15). Replay text (log entries) is rendered
  as React text.
- **Fonts are local.** IBM Plex comes from npm packages bundled by Vite; no font host is contacted.
- **No Supabase or OpenAI in the browser.** The frontend never connects to either.
- **Simulation truth is not shown.** `keyframes[].sources` is never rendered; tests
  `viewGuards.test.ts` and `simulationTruth.test.tsx` pin it.

### The replay bundle check

The diagram is small on purpose: the check has one input and two outcomes.

```mermaid
flowchart LR
    Build["vite build --mode replay"] --> Chunks["dist/assets/*.js"]
    Chunks --> Check["check-replay-bundle.mjs"]
    Check -->|"no /api/ AND /replay/scenarios present"| Pass["replay bundle OK"]
    Check -->|"/api/ found, or /replay/scenarios missing, or both"| Fail["prints each problem, exit 1"]
```

`npm run check:replay-bundle` fails when any bundled script contains the live API path `/api/`, so the
public build cannot call a backend, and fails when no script contains `/replay/scenarios`, so the
check cannot pass vacuously. The negative control (a normal build) fails; it was observed on
2026-11-15. Full explanation with the build sizes: [DATA_LAYER.md](DATA_LAYER.md#replay-only-build-and-live-build).
The check does not scan for secrets; `secret_scan.py` does that for the files the build copies.

### Headers (recorded, not active)

`app/frontend/vercel.json` holds the CSP (`default-src 'self'`, `connect-src 'self'`,
`frame-ancestors 'none'`, ...), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` and
HSTS. They apply only to a deployment, which is not planned; `src/app/vercelConfig.test.ts` pins them.
The Vite dev server and `vite preview` do not send them. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Threats and where they stand

| Threat | Control | Status |
|---|---|---|
| Secret committed | git-ignore, `secret_scan.py`, `check_env.py`, pre-commit hook | in place |
| Secret printed in a log or chat | `SecretStr`, names-only tools, rule 9 | in place for settings; app logs arrive later |
| SSRF through the weather call | fixed `ARCHIVE_URL` | in place |
| Reflected content in an error | fixed 404 body, no echo | in place |
| Path traversal through a scenario id | id regex in the UI, registry lookup in the API | in place |
| Other website reading the API from a browser | CORS allow-list | in place |
| Other machine reaching the API | bind `127.0.0.1` | in place |
| Live API code in the public bundle | `check:replay-bundle` with negative control | in place |
| SQL injection | parameterised queries, Ruff `S` | in place |
| Direct table access through Supabase REST | RLS with no policy, schema not exposed | in place |
| Cross-site scripting | React text rendering, no HTML sinks, CSP (later deployment) | partly: CSP not active |

## Known gaps (not yet in place)

- Phase 6: rate limits, request body limit, host-header check (a local process or DNS rebinding can
  still reach `127.0.0.1:8000`), security headers on API responses, API fuzzing, least-privilege
  database role, dependency audit gate.
- The API docs page `/api/docs` loads Swagger UI from `cdn.jsdelivr.net` (`swagger-ui-dist@5`, not
  pinned to a patch version) in the **browser** of whoever opens it. The backend itself makes no such
  call. Decide in Phase 6 whether to serve it locally or disable it.
- No dedicated test scans a built `dist/` for keys; coverage comes from `secret_scan.py` over the
  working tree, which includes `dist/` when it exists. Rule 9 asks for such a test; it is not written.
- OpenAI, LangSmith and the agent runs do not exist yet, so their controls (spend cap, tracing
  requirement, prompt-injection handling) are not in this page.

## Testing and evidence

```bash
cd app && uv run pytest backend/tests/api backend/tests/db backend/tests/data_sources backend/tests/test_config.py backend/tests/test_secret_scan.py -q
cd app/frontend && npm run test
python -I .claude/skills/security-checks/scripts/check_env.py .
python -I .claude/skills/security-checks/scripts/secret_scan.py .
```

Phase check results are in `docs/evidence/` (Phase 1 and 2 files; the Phase 4 UI evidence is
collected at Gate 4). The `docs/evidence/<date>-security.md` reports are written by the security
phases.

## How to extend

- A new outbound call gets a row in the outbound table in the same change: host, file, when it runs,
  data sent, data received, timeout, TLS, and a no-network test. The host must be a constant.
- A new secret goes into the root `.env` through `env_set.py` and its name into `.env.example`.
- A new endpoint follows the invariants in [API.md](API.md#how-to-extend): generic errors, no echo,
  no bare rate.
- A new frontend `fetch` goes through `fetchJson.ts`, with an id check; never read `.env` from the
  frontend; never render the simulation source rates.
- A table gets RLS in the same migration; never add a policy for `anon` without the owner's approval.

## Changelog

- 2026-11-14: outbound network section (Open-Meteo).
- 2026-11-15: Phase 4 Task 1 API section.
- 2026-11-15: whole-project revision: trust-boundary diagram, settings and secrets, local database,
  frontend, replay-bundle check, threat table and known gaps.
