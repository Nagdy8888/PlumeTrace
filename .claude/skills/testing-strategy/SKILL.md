---
name: testing-strategy
description: PlumeTrace test layers and when each is required - unit, property-based/metamorphic (Hypothesis), integration with local Supabase, API (TestClient), contract drift, API fuzzing (Schemathesis), security/abuse, component (Vitest + Testing Library), graph branch tests with the scripted LLM, end-to-end (Playwright replay, no-WebGL, full-stack live with the scripted LLM), visual, accessibility (axe), performance (fps), LLM evaluations. Use when writing or reviewing any test, choosing which tests a change needs, or running the local checks (scripts/ci_local.py).
---

# Testing strategy (PlumeTrace)

Owner decision (2026-11-13): not only unit tests. Every change gets the **test layers that fit
it** (table below), written test-first. Everything runs **locally** with `python scripts/ci_local.py`
(quick, also the pre-commit hook) and `python scripts/ci_local.py --full` (before every phase gate).
There is no GitHub Actions CI. The human-readable copy of this page is `docs/reference/TESTING.md`.

## Layers

| Layer | Tool | Where | Proves | Stage |
|---|---|---|---|---|
| Unit | pytest | `app/backend/tests/**`, `app/agents/tests/**` | one function or class against hand-checked values (cite references in physics tests) | quick + full |
| Property-based / metamorphic | Hypothesis 6.170.14 | `tests/engineering/test_properties.py`, `test_plume_field_properties.py`, more beside the module they test | laws that hold for **every** valid input (linearity, symmetry, invariance, round trips, probability rules) | quick + full |
| Integration (database) | pytest + local Supabase, `db` marker | `app/backend/tests/db/**` and DB-using API tests | SQL, constraints, RLS, grants, idempotency on the real Postgres | quick (skips without DB) / full (`PLUMETRACE_REQUIRE_DB=1`) |
| API | FastAPI `TestClient` (`base_url="http://127.0.0.1"`) | `app/backend/tests/api/**` | status codes, error bodies, WebSocket protocol, persistence before publish | quick + full |
| Graph branches | `ScriptedLLM` + `FakeToolProvider` + `memory_checkpointer()` | `app/agents/tests/graph/**` | every edge and branch of the LangGraph graph, resume behaviour, no LLM before `interrupt()` | quick + full |
| Contract | `scripts/export_contract.py` + `npm run gen:types` + `git diff --exit-code` | stage `contract-drift` | backend models and frontend types never drift | full |
| API fuzzing | Schemathesis 4.32.6, `fuzz` marker | `app/backend/tests/security/test_api_fuzz.py` | no `500`, responses match the declared schema, for generated inputs | full |
| Security / abuse | pytest | `app/backend/tests/security/**`, `app/agents/tests/graph/test_injection_routing.py` | rate limits, body limit, hosts, headers, hostile ids, replayed decisions, injected text cannot route or approve | quick + full |
| Component | Vitest 5.1.0 + Testing Library | `app/frontend/src/**/*.test.tsx` | a component's rendering and interaction, text rendered literally, limits shown | quick + full |
| Frontend coverage | `@vitest/coverage-v8` 5.1.0 | `npm run test:coverage` | lines/functions/statements ≥ 80 %, branches ≥ 70 % (3D scene excluded — covered by WebGL e2e) | full |
| Python coverage | pytest-cov 7.1.0 | stage `python-tests-full` | total ≥ 85 % (branch coverage on) | full |
| End-to-end, replay | Playwright 1.65.0, project `no-webgl` | `app/frontend/e2e/**` | the replay build works without WebGL, approval flows on recorded traces, no foreign requests | full |
| End-to-end, full-stack live | Playwright `live-fake` + `scripts/e2e_live_server.py` | `app/frontend/e2e-live/**` | browser → proxy → API → graph → Postgres → WebSocket → approval, with the scripted model (no cost) | full |
| Visual, 3D, fps | Playwright project `webgl` | owner's machine only | baseline screenshots, 3D interactions, ≥ 58 fps average | manual at Phase 4 / 7 gates |
| Accessibility | `@axe-core/playwright` 4.14.0 | e2e specs | no serious/critical axe violations | full |
| LLM evaluation | `scripts/run_evals.py` + LangSmith | `app/agents/evals/**` | AI vs baseline, provenance 100 %, cost/latency — **paid**, inside the spend cap, owner's yes | manual (Phase 5 Task 11) |

## Which layers a change needs

| Change | Required layers |
|---|---|
| Physics or any pure calculation (`engineering/`) | unit (cited values) + property/metamorphic law for every new formula with a law (linearity, symmetry, monotonicity, conservation, round trip) |
| Simulator / replay format | unit + determinism (same seed → same bytes) + property tests for codecs |
| Database (migration, repository) | integration with the real DB; constraint violations tested; RLS and grants checked |
| API endpoint or WebSocket | API test for every status code it can return + security tests (limits, hostile input) + it is covered by fuzzing automatically |
| Graph, node, routing, prompt | graph branch test with the scripted model for every branch it touches; prompt change → evaluation cases (paid, owner's yes) |
| Frontend component | component test (render, interaction, accessibility role names); data shown from props/stores, never hard-coded |
| A user flow | Playwright e2e (replay); live-only flows also `e2e-live` |
| 3D scene | WebGL e2e + fps on the owner's machine |
| Security control | a test that fails when the control is removed (write it first, watch it fail) |

## Rules
- Test-first (`superpowers:test-driven-development`): write the test, run it, see it fail for the right reason, then implement.
- Deterministic: seeded `numpy.random.Generator`; Hypothesis with `derandomize=True, database=None`; fake clocks for time; no sleeps for waiting (poll with timeouts in e2e only).
- **No paid calls in any automated test.** `ScriptedLLM` everywhere; `build_agent_llm` is blocked in backend tests (Phase 5 Task 10 guard); `LANGSMITH_TRACING=false` in tests.
- No network in tests except the local database and the local servers e2e starts.
- Test folders have **no** `__init__.py` (`--import-mode=importlib`); share helpers through `conftest.py` fixtures only.
- Never edit a planned test to make it pass; never lower a threshold, add a skip or an exemption to get green. Report instead.
- Markers: `db` (needs Supabase), `slow` (> ~5 s, full only), `fuzz` (Schemathesis, full only).

## Not used (and why)
- Mutation testing (`mutmut`): needs `fork`, unsupported on Windows (the owner's machine). Property tests and cited point tests are the strength check instead.
- Load testing: one local operator; rate limits and connection limits are tested directly (Phase 6).
- Remote CI: GitHub Actions off (owner decision, billing).

## `docs/reference/TESTING.md` sections
`# Testing` · `## How to run` (quick, full, `--only`, `--list`, the hook) · `## Layers` (the table above) · `## Which layers a change needs` · `## Property-based tests` (one row per file: laws) · `## Full-stack live e2e` · `## API fuzzing` · `## Abuse tests` · `## Coverage` (thresholds, exclusions and why) · `## Manual runs` (WebGL, fps, evaluations — and the spend cap).
