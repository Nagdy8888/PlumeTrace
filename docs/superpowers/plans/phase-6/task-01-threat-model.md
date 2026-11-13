# Phase 6 · Task 1 — Threat model and control map → OWNER GATE 6a

**Skills:** `plan-execution`, `security-checks` (+ `references/checklist.md`), `agentic-council:skeptic-threat-model`, `project-documentation` (+ `references/mermaid-diagrams/GUIDE.md`).

**Why:** the later tasks of this phase are fixed, but the owner must see the whole picture first:
what is worth protecting, who could attack it, where, and which control and test answers each threat.

## File
| Action | Path |
|---|---|
| Create | `docs/reference/THREAT_MODEL.md`; link it from `docs/README.md` and `docs/reference/SECURITY.md` |

## Content (exact sections, in this order)
1. **Scope** — one paragraph: local live mode (FastAPI on `127.0.0.1:8000`, Vite dev server on `127.0.0.1:5173`, local Supabase), the static replay build (built and previewed locally; deployment is a later, unplanned phase), the paid OpenAI and LangSmith calls, the repository itself.
2. **Assets** — table `Asset | Where | Why it matters`: `OPENAI_API_KEY` and `LANGSMITH_API_KEY` (root `.env`; money and account access); `SUPABASE_DB_URL` (root `.env`; full DB access); the spend budget ($4 cap, `llm_calls`); the approval record (`decisions`); work orders and reports (`work_orders`, `reports`); LangGraph checkpoints (`langgraph` schema); logs (`app_logs`); the replay files and traces (`app/replay/`, public later); the owner's machine (local services).
3. **Actors** — a malicious web page open in the owner's browser (cross-origin requests, WebSocket, DNS rebinding); text inside scenario data, permit-log notes and operator reasons (prompt injection); a compromised or typosquatted dependency; a future reader of the public repository (secrets in history); the executor agent itself making a mistake (spend, deleting data).
4. **Trust boundaries diagram** — Mermaid `flowchart LR`: Browser (other origin) ⇢ Browser (PlumeTrace UI) → Vite proxy → FastAPI → {LangGraph agents → OpenAI (internet), LangSmith (internet)}, FastAPI → Supabase (Postgres); replay build → static files. Mark each boundary with a dashed subgraph and its id `B1`…`B6`.
5. **Threats** — table `Id | Boundary | STRIDE | Threat | Control (where) | Test (file::name)`. At least these rows (ids fixed; later tasks name them):
   | Id | Threat | Control | Test |
   |---|---|---|---|
   | T01 | Cross-origin page calls `POST /api/runs` repeatedly (spend, DoS) | CORS allowlist; rate limit `start_run` 5/min; one active run; spend cap | `tests/security/test_rate_limits.py::test_start_run_burst_gets_429` |
   | T02 | Cross-origin page opens the run WebSocket | Origin check before accept (Phase 5 Task 10); WS connect rate limit; ≤ 3 sockets per client | `tests/api/test_run_ws.py`, `tests/security/test_rate_limits.py::test_ws_connect_limit` |
   | T03 | DNS rebinding (attacker host name resolving to 127.0.0.1) | `TrustedHostMiddleware` (`localhost`, `127.0.0.1`) | `tests/security/test_request_hardening.py::test_foreign_host_header_is_rejected` |
   | T04 | Oversized or deeply nested JSON body | 64 KiB body limit (ASGI), Pydantic length limits | `test_request_hardening.py::test_body_over_limit_gets_413` |
   | T05 | Forged or replayed approval decision | interrupt id must match the pending one; one decision per interrupt (Phase 5) | `tests/api/test_runs_api.py` + `tests/security/test_abuse.py::test_decision_replay_is_refused` |
   | T06 | SQL injection through ids or text | parameterised SQL only; ids validated (UUID, scenario enum) | `test_abuse.py::test_sql_payloads_never_reach_sql` + `check_sql_safety` grep stage |
   | T07 | Error responses leak internals | generic 500 handler; no echo | `test_request_hardening.py::test_unhandled_error_is_generic` |
   | T08 | Prompt injection in log text changes routing or approval | code-defined edges; approval only by a human; provenance guard | `app/agents/tests/graph/test_injection_routing.py` + eval case `s1_injection` |
   | T09 | LLM output rendered as HTML (XSS) | React text rendering; `check_frontend_safety.py` | `src/features/agentPanel/AgentTimeline.test.tsx::renders model text literally` |
   | T10 | Unbounded LLM spend | per-run $0.10 / 180 s; total cap (`PLUMETRACE_SPEND_CAP_USD`) from `llm_calls` | `tests/api/test_budget.py` |
   | T11 | Backend DB role can alter schema or read Supabase internals | role `plumetrace_app` with table-level grants only; `statement_timeout` | `tests/db/test_app_role.py` |
   | T12 | Secret committed to git or written to a log, trace or build | `secret_scan.py` (files, staged, history, build, replay), log redaction, trace secret guard | `scripts` tests + `ci_local.py` stages |
   | T13 | Vulnerable or malicious dependency | exact pins, lockfiles, `pip-audit`, `npm audit`, licence inventory | `ci_local.py --full` stages `audit`, `licences` |
   | T14 | The replay build talks to a backend or third party | `check:replay-bundle`, CSP in `vercel.json` / `preview.headers` | `check_headers.py` on the local preview; Playwright network log |
   | T15 | Log flooding fills the database | request log is one line per request; rate limits bound requests | `test_rate_limits.py::test_rejected_requests_are_logged_once_per_window` |
6. **Accepted risks** — table `Risk | Why accepted | Owner decision date`: the backend connects over plain TCP to local Postgres (local only); FastAPI `/api/docs` stays enabled on `127.0.0.1`; LangSmith receives tool inputs/outputs of simulated data. The owner may add or remove rows at Gate 6a.
7. **Out of scope now** — hosted deployment (later phase), authentication (single local operator; design §10).

## Steps
- [ ] Read every Phase 1–5 control in the code (grep for each control name in the table) and confirm its location; a control that is missing becomes a later-task item — note it, do not add it here.
- [ ] Write `THREAT_MODEL.md`; render the Mermaid diagram (project-documentation render check) and inspect it.
- [ ] `agentic-council:skeptic-threat-model` pass: list any threat it finds that has no row; add rows for those (control column "to decide at Gate 6a").
- [ ] Repo checks (structure, secrets, env).
- [ ] **Docs.** SECURITY.md links the threat model; Work-log; `STATUS.md` (last 6.1, "waiting for Gate 6a").
- [ ] **Commit** `docs(security): add the threat model and control map`.
- [ ] **Owner Gate 6a (STOP):** show the threats table and the accepted risks; record the owner's answer in STATUS.md (decisions log); new rows the owner wants become extra steps in the task that owns the boundary (the planner writes them — do not invent them).
