# Testing

Every change gets the test layers that fit it, written test-first. All checks run locally; there is
no GitHub Actions CI (owner decision 2026-11-13). This page is the readable copy of the
`testing-strategy` project skill. Layers that do not exist yet are marked "planned" with the phase
that adds them.

## How to run

From the repository root:

```bash
python scripts/install_git_hooks.py        # once per clone: installs .git/hooks/pre-commit
python scripts/ci_local.py                 # quick: the pre-commit hook runs this
python scripts/ci_local.py --full          # every stage; local Supabase must be running
python scripts/ci_local.py --only ruff,mypy
python scripts/ci_local.py --list
```

- `scripts/ci_local.py` runs the stages in a fixed order, stops a stage at its first failing command,
  prints a summary table and exits 1 if any stage failed. Later tasks add stages to `STAGES`.
- Quick mode runs `python-tests` (marker filter `not slow and not fuzz`) and `frontend-test`.
  Full mode replaces them with `python-tests-full` (adds coverage, sets `PLUMETRACE_REQUIRE_DB=1`),
  `frontend-coverage`, `frontend-build` and `contract-drift`.
- The hook runs the quick mode before every commit. Never commit with `--no-verify`.
- On Windows the runner prefers the `.cmd` shim for `npm`, because `shutil.which("npm")` returns the
  extensionless script that `CreateProcess` cannot start.

## Layers

| Layer | Tool | Where | Proves | Stage |
|---|---|---|---|---|
| Unit | pytest | `app/backend/tests/**`, `app/agents/tests/**` | one function or class against hand-checked values | quick + full |
| Property-based / metamorphic | Hypothesis | beside the module tested (planned, Phase 2) | laws that hold for every valid input | quick + full |
| Integration (database) | pytest + local Supabase, `db` marker | `app/backend/tests/db/**` | SQL, constraints, RLS, grants | quick (skips without DB) / full (fails without DB) |
| API | FastAPI `TestClient` | `app/backend/tests/api/**` (planned) | status codes, error bodies, WebSocket protocol | quick + full |
| Graph branches | scripted LLM + fake tools (planned) | `app/agents/tests/graph/**` | every edge and branch of the graph | quick + full |
| Contract | `scripts/export_contract.py`, `npm run gen:types`, `git diff --exit-code` | stage `contract-drift` | backend models and frontend types never drift | full |
| API fuzzing | Schemathesis, `fuzz` marker (planned, Phase 6) | `app/backend/tests/security/` | no 500, responses match the schema | full |
| Security / abuse | pytest (planned) | `app/backend/tests/security/**` | limits, hostile input, replayed decisions | quick + full |
| Component | Vitest + Testing Library | `app/frontend/src/**/*.test.tsx` | rendering and interaction of one component | quick + full |
| Frontend coverage | `@vitest/coverage-v8` | `npm run test:coverage` | line and branch thresholds | full |
| Python coverage | pytest-cov | stage `python-tests-full` | total at least 85 % | full |
| End-to-end | Playwright (planned) | `app/frontend/e2e/**` | replay build and approval flows | full |
| Accessibility | axe with Playwright (planned) | e2e specs | no serious or critical violations | full |
| LLM evaluation | LangSmith (planned, Phase 5) | `app/agents/evals/**` | AI against baseline; paid | manual |

The check runner itself is covered by unit tests in `app/backend/tests/test_ci_local.py` (stage
selection by mode, unknown stage names, stop at the first failing command, failure summary, stage
environment).

## Which layers a change needs

| Change | Required layers |
|---|---|
| Physics or any pure calculation | unit with cited values, plus a property or metamorphic law for every formula with a law |
| Simulator or replay format | unit, determinism (same seed, same bytes), property tests for codecs |
| Database (migration, repository) | integration against the real DB; constraint violations; RLS and grants |
| API endpoint or WebSocket | API test for every status code, security tests, automatic fuzzing |
| Graph, node, routing, prompt | graph branch test with the scripted model for every touched branch; prompt change adds evaluation cases (paid, owner's yes) |
| Frontend component | component test (render, interaction, role names); data from props or stores |
| A user flow | Playwright e2e (replay); live-only flows also the live e2e |
| 3D scene | WebGL e2e and fps on the owner's machine |
| Security control | a test that fails when the control is removed |

## Property-based tests

None yet. The first ones arrive with the engineering core in Phase 2; this section gets one row per
file with the laws it checks.

## Full-stack live e2e

Not built yet (planned). It will run browser, proxy, API, graph, Postgres and WebSocket with the
scripted model, so it costs nothing.

## API fuzzing

Not built yet (planned, Phase 6), marker `fuzz`, full mode only.

## Abuse tests

Not built yet (planned, Phase 6): rate limits, body limit, hostile ids, replayed decisions.

## Coverage

| Scope | Threshold | Set in |
|---|---|---|
| Python (`plumetrace`, `plumetrace_agents`), branch coverage on | total at least 85 % | stage `python-tests-full` (`--cov-fail-under=85`) |
| Frontend | lines, functions, statements at least 80 %; branches at least 70 % (the 3D scene is excluded and covered by WebGL e2e) | `npm run test:coverage` |

Coverage runs in full mode only. Never lower a threshold or add an exclusion to get green.

## Manual runs

WebGL visual checks, fps measurement and LLM evaluations are run by hand at the phase gates. The
evaluations are paid: they stay inside the OpenAI spend cap ($4.00 in total) and need the owner's
yes in chat before each run. No automated test makes a paid call.
