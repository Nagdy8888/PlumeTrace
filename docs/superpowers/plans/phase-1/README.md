# Phase 1 — Foundations

> **For agentic workers:** load the `plan-execution` skill first. Execute the task files in this
> folder **in numeric order, one per session/subagent**, exactly as written. Each task file is
> self-contained: it lists every file, every file's content or exact interface, every test (full
> code), every command and its expected output. If anything in a task file is impossible as
> written, STOP and report (see `plan-execution`). Do not improvise.

**Goal:** a checked repository skeleton — git, uv workspace (`plumetrace`, `plumetrace_agents`),
settings from the single root `.env`, local Supabase with the first migration, the Vite/React
shell (its security headers recorded in `vercel.json` for a later deployment phase), the KS-07 facility spec, the Python→TypeScript contract, and local checks (no GitHub Actions).

**Spec:** `docs/superpowers/specs/2026-11-12-plumetrace-design.md` · **Rules:** `CLAUDE.md`

## Task order
| # | File | Delivers |
|---|---|---|
| 1 | `task-01-repo-bootstrap.md` | git, LICENSE, .gitattributes, docs skeleton |
| 2 | `task-02-python-workspace.md` | uv workspace, two packages, lint/type/test config |
| 3 | `task-03-settings.md` | `plumetrace.config` (single root `.env`) |
| 4 | `task-04-supabase.md` | local Supabase, first migration + seed, DB pool, RLS tests |
| 5 | `task-05-frontend-scaffold.md` | Vite + React + TS + Tailwind shell, Vercel headers |
| 6 | `task-06-facility-spec.md` | KS-07 facility spec, loader, candidates, components |
| 7 | `task-07-type-contract.md` | JSON Schema + TS types + facility JSON for the frontend |
| 8 | `task-08-ci.md` | local check runner `scripts/ci_local.py` + git pre-commit hook (no GitHub Actions) |

## Pinned versions (use exactly these; checked 2026-11-12)
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
| actions/checkout | v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1` | Task 8 |
| actions/setup-python | v7.1.0 `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | Task 8 |
| actions/setup-node | v7.1.0 `949feb2413d6458794dcd2491c4babbbce0c15c1` | Task 8 |
| astral-sh/setup-uv | v10.3.3 `68559e99cc807c1eb7e9238fd43a15bba460eec2` | Task 8 |

If `npm install` / `uv sync` reports a peer or resolution conflict with these pins, STOP and
report the exact error. Do not change a version on your own.

## Global constraints (apply to every task)
- All Python commands run from `app/` as `uv run …`. Frontend commands run from `app/frontend/`.
- Ruff: `line-length = 100`, rules `E,F,W,I,B,UP,D,S,ANN,N`, Google docstrings; tests ignore only `S101`, `ANN`. mypy strict.
- Google docstrings on every Python module/class/function; TSDoc on every exported TS function/component.
- File-size limits and banned names: `.claude/skills/repo-structure/SKILL.md` ("No god files").
- Settings only via `plumetrace.config`, only from the repo-root `.env` or the environment.
- Coordinates: metres, x = east, y = north, z = up, origin = south-west fence corner; site 200 × 150 m.
- Frontend: anti-slop rules (`.ux-profile.md`), no `VITE_*` secrets.
- Database: schema `plumetrace`, RLS on every table, no `anon`/`authenticated` policies, changes only via migrations.

## Review focus (edge cases the tests in this phase pin down)
1. Fresh clone without `.env` → settings load with defaults; DB code raises an error naming `SUPABASE_DB_URL` (Task 3).
2. Supabase not running → DB tests skip with a start hint; with `PLUMETRACE_REQUIRE_DB=1` they fail (Task 4).
3. Broken facility spec (duplicate tag, bad anchor, out-of-bounds point, unknown `vents_to`, composition ≠ 1) → error naming the item (Task 6).
4. Windows vs Linux → generated files byte-identical (LF, sorted keys, UTF-8) (Tasks 1 and 7).
5. Non-ASCII YAML text (°, ≈, –) → loads on Windows (Task 6).

## Phase exit — Owner Gate 1
After Task 8: write `docs/evidence/2026-11-phase-1-checks.md` with the output of every check
command, set `STATUS.md` to "Phase 1 complete — waiting for Gate 1 (ks07.yaml, gas composition,
component_counts.yaml, emission sources)", and STOP.
