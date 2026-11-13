# Phase 6 — Security hardening of the whole project

> **For agentic workers:** load `plan-execution`, `security-checks`, `fastapi`, `testing-strategy`
> first. **Start only after the owner's Phase 5 review** is signed off in STATUS.md. Task 1 ends
> with **Owner Gate 6a** (threat model); Task 8 ends with **Owner Gate 6** (security evidence). STOP at each.
> No new dependency except the two test tools pinned below (owner-approved 2026-11-13).

**Goal:** every boundary of PlumeTrace is defended and every defence has an automated test:
rate limits and concurrency limits, request size and input limits, host and origin checks,
security headers, generic errors, least-privilege database access, LLM and spend limits,
frontend output safety, secrets and supply chain, plus an API fuzz suite and an abuse test suite.
Everything runs locally (no GitHub Actions, no deployment).

**Why a separate phase:** Phases 1–5 built each control where it was first needed (single `.env`,
Origin check before WebSocket accept, RLS, provenance guard, spend cap, redacted logs). This phase
looks at the **whole system** from an attacker's side, closes the gaps, and proves each control with
a test that fails if the control is removed.

**Spec:** design §10 (live mode is local), §10.1 (database), §6 (agents, budgets); `CLAUDE.md` rules 9, 18, 19, 23, 24; `security-checks` skill and `references/checklist.md` A–H; OWASP API Security Top 10 (2023) and OWASP Top 10 for LLM Applications (2025) as named in the checklist.

## Task order
| # | File | Delivers |
|---|---|---|
| 1 | `task-01-threat-model.md` | `docs/reference/THREAT_MODEL.md`: assets, trust boundaries, STRIDE table, control ↔ test map → **Owner Gate 6a** |
| 2 | `task-02-rate-limiting.md` | in-process token-bucket rate limits per client and route class, WebSocket connection limits, `429` + `Retry-After` |
| 3 | `task-03-request-hardening.md` | body size limit, trusted hosts (DNS rebinding), API security headers, generic 500 handler, strict input schemas and length limits |
| 4 | `task-04-frontend-static-hardening.md` | `check_frontend_safety.py`, LLM text rendered as text, `check_headers.py` against the local preview, replay bundle scan |
| 5 | `task-05-database-hardening.md` | least-privilege role `plumetrace_app`, statement timeouts, grants test, `db lint` |
| 6 | `task-06-supply-chain-secrets.md` | secret scan stdin mode + history scan, dependency audit and licence inventory stages in `ci_local.py`, lockfile checks |
| 7 | `task-07-security-tests-fuzz.md` | Schemathesis API fuzzing, abuse test suite (`app/backend/tests/security/`), offline prompt-injection routing tests |
| 8 | `task-08-security-gate.md` | full security gate, reviews, evidence → **Owner Gate 6** |

## Pinned additions (checked 2026-11-13 on PyPI; resolved together with every Phase 1–5 pin by `uv pip compile` for Python 3.12 — no conflicts; adds werkzeug 3.1.9, coverage 7.17.3)
| Package | Version | Where | Why |
|---|---|---|---|
| hypothesis | 6.170.14 | `app/pyproject.toml` dev group (added in Phase 1 Task 2 — see the testing strategy) | property-based tests |
| schemathesis | 4.32.6 | `app/pyproject.toml` dev group (added here, Task 7) | API fuzzing from the OpenAPI schema (requires hypothesis < 7, pytest < 10 — both satisfied) |

## Global constraints
- Everything is local: the API binds `127.0.0.1`; there is no deployment and no GitHub Actions. Checks run with `python scripts/ci_local.py`.
- Every control gets a test that fails when the control is removed (write the test first, see it fail, then add the control).
- Responses never echo user input, never contain tracebacks, settings, SQL or file paths.
- Security events are logged at `WARNING` on logger `plumetrace.security` (stored in `app_logs`, Phase 5 Task 9b) with the client host, route class and reason — never request bodies.
- The executor never weakens an existing control to make a test pass, never adds an exemption to `check_structure.py`, `secret_scan.py` or `check_slop.py`; ask the owner.
- Numbers in this phase (limits, sizes, timeouts) are fixed in the task files; changing one needs the owner.

## Review focus
1. Rate limits hold per client and per route class, also for WebSocket connects; a burst gets `429` with `Retry-After`, never a `500`.
2. A browser page on another origin or a DNS-rebinding host name cannot drive the local API (Origin + Host checks).
3. The backend's database role cannot change the schema, cannot read Supabase's own schemas, and every query is time-limited.
4. Fuzzing the API from its OpenAPI schema produces no `500` and no response that breaks its declared schema.
5. LLM text is never interpreted as HTML in the UI; injected log text never changes routing or approval.

## Phase exit — Owner Gate 6
`docs/evidence/2026-11-phase-6-security.md` (Task 8). `STATUS.md`: "Phase 6 complete — waiting for Gate 6 (security evidence)". STOP.
