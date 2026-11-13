# PlumeTrace — rules for every agent working in this repo

PlumeTrace is an AI methane leak hunter for a simulated gas compressor station: a 3D control-room
web app (a static public replay build; deploying it is a later phase, not planned yet) backed by FastAPI and local Supabase, where LangGraph
agents (OpenAI models, traced in LangSmith) triage methane events, locate
and quantify leaks with real physics, check rules, and draft work orders and reports that a human
operator approves. It is a LinkedIn portfolio project that must look and behave like a real
industrial product.

**Source of truth:** `docs/superpowers/specs/2026-11-12-plumetrace-design.md`. If a task conflicts
with the design, stop and ask the owner; do not silently change the design.

## If you are implementing a plan
Load the `plan-execution` skill first. Work only on the "Next task" in
`docs/superpowers/plans/STATUS.md`, follow the plan's exact interfaces and values, stop and ask
instead of guessing, and update `STATUS.md` after every task. Plans live in
`docs/superpowers/plans/` (start with the roadmap).

## Repo layout (summary — the full, binding tree is in the `repo-structure` skill)

All application code lives under `app/`, one sub-folder per app:

- `app/backend/` — Python 3.12, FastAPI. Package `plumetrace`: `engineering/` (pure physics),
  `facility/`, `simulator/` (scenarios S1–S6), `rules/` (cited rules table), `data_sources/`,
  `db/` (Supabase Postgres access), `agent_tools/` (implements the agents' ToolProvider),
  `reports/`, `api/` (REST + WebSocket, runs the graph). Tests in `app/backend/tests/`.
- `app/agents/` — LangGraph agents. Package `plumetrace_agents`: `graph.py`, `state.py`,
  `routing.py`, `llm.py`, `checkpoint.py`, `tracing.py`, `export_trace.py`, `nodes/`, `tools/`,
  `schemas/`, `prompts/`. Evaluations in `app/agents/evals/`, tests in `app/agents/tests/`.
  **Never imports the backend**; tools, LLM and checkpointer are injected.
- `app/frontend/` — React + TypeScript + Vite, React Three Fiber, Tailwind, shadcn/ui, Zustand.
  The public replay build is built and previewed **locally**; deployment (Vercel) is a later phase, not planned yet.
- `app/supabase/` — **local Supabase** (Postgres): migrations, seed, config. Holds runs, events,
  agent steps, drafts, operator decisions, work orders, reports and the LangGraph checkpoints.
- `app/replay/` — generated scenario data and recorded traces for the replay build.
- `app/pyproject.toml` — uv workspace root (members: backend, agents).
- `docs/` — design, plans, references, benchmark, work log. `scripts/` — repo tooling.
- `.claude/skills/` — project skills (below). The root `skills/` folder holds the original,
  unadapted source copies (some still carry another project's rules). **Ignore it**; always use
  `.claude/skills/`.

## Hard rules

1. **Check current docs before writing library code.** Use the Context7 docs tool (or official
   docs) before code that uses LangGraph, LangChain, langchain-openai, LangSmith, FastAPI,
   Pydantic, psycopg, Supabase, Vercel, React Three Fiber, drei, postprocessing, Tailwind or shadcn. Never rely on memory for
   these APIs; they change often (e.g. LangGraph's newer event-streaming API, LangSmith's newer
   agent-addressing variables).
2. **Pin versions.** Exact versions in `app/backend/pyproject.toml`, `app/agents/pyproject.toml`
   and `app/uv.lock`; in `app/frontend/package.json` and its lockfile; and the Supabase CLI version. Note the version you checked docs against in the task.
3. **Engineering core is pure and test-first.** No LLM, no I/O, no global state. TDD. SI units
   inside; unit suffixes in names (`rate_kg_h`, `u_m_s`, `conc_ppm`). Cite reference values in test
   docstrings. See the `engineering-core` skill.
4. **The LLM never produces an engineering number.** Every number in agent output comes from a tool
   result in the same run. The "numbers-from-tools" evaluator enforces it in tests and LangSmith.
5. **Structured outputs only.** Every agent node returns a Pydantic-validated model. Invalid →
   retry once → fail visibly. Never silently fill defaults.
6. **LangGraph:** `interrupt()` only in the `approval` node, with nothing before it except building
   the payload (the node re-runs on resume). Always compile with a checkpointer, always pass
   `thread_id`, resume with `Command(resume=...)`. Edges are code-defined; conditional edges only
   after `triage` and `approval`. Every graph change has a fake-LLM test covering every branch.
   See the `langgraph` skill.
7. **LangSmith:** every paid run (smoke, live, eval, record) is traced — the backend refuses a paid
   run when tracing is off (`require_tracing`). Tracing only through env vars; tag runs with scenario id, run id and branch;
   no secrets or bulk data in metadata; unit tests run with `LANGSMITH_TRACING=false`. LangSmith is
   not the public replay source. See the `langsmith-trace` skill.
8. **Regulatory content only from the curated rules table** (`app/backend/plumetrace/rules/`), each
   rule with article/section and link. The site is outside the EU and exports to the EU: frame
   compliance as OGMP 2.0 + an operator LDAR policy modelled on EU 2024/1787 ("EU-import
   readiness"). Never claim EU articles bind the site directly. Never write regulatory statements
   from memory into prompts or UI copy.
9. **Secrets: one `.env`, at the repo root, holds every secret and setting.**
   - **Every** secret and environment setting goes in the root `.env` (non-secret settings too: `OPENAI_MODEL_FAST`,
     `OPENAI_MODEL_REASONING`, `PLUMETRACE_SPEND_CAP_USD`; secrets currently `OPENAI_API_KEY`,
     `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, `SUPABASE_DB_URL`). A new secret
     is added there **and** its name to the root `.env.example` (names only, no values) in the same change.
   - **No other env files anywhere**: no `app/backend/.env`, `app/agents/.env`, `app/frontend/.env*`,
     `app/supabase/.env`, `.env.local`, `.env.production`. Never run `vercel env pull`.
   - Python reads it only in `app/backend/plumetrace/config.py` (pydantic-settings with
     `env_file` pointing at the repo-root `.env`); agents get values injected. Supabase CLI and
     scripts get variables from the same root `.env`. The frontend reads no env file and holds no secret.
   - Never hard-code a secret, never read `.env` values into chat, logs, commits, traces, LangSmith
     metadata, docs or the frontend, never print keys, never pass them as command-line arguments.
     Report problems by variable **name** only.
   - **Agents may add and update `.env` entries — only through `python -I .claude/skills/security-checks/scripts/env_set.py`**
     (owner decision 2026-11-13). Never open `.env` with a read or edit tool, `cat`, `type`,
     `Get-Content` or `grep` (that loads every secret into the conversation). Commands: `names`
     (names only), `get`/`set` for non-secret settings, `add NAME` (empty, for a key only the owner
     has: the owner pastes it), `generate NAME` (random secret, never printed). Every write also adds
     the name to `.env.example`. `PLUMETRACE_SPEND_CAP_USD` is owner-only (the script refuses it).
     A new non-secret setting goes into `NON_SECRET_SETTINGS` (env_set.py) and `NON_SECRET_NAMES`
     (secret_scan.py) in the same change.
   - Check: `python -I .claude/skills/security-checks/scripts/check_env.py .` must print `env OK`.
   - Vercel holds no secrets; the frontend never connects to Supabase or OpenAI. A test scans the
     static build and `app/replay/` for keys.
10. **Honest labelling.** The station is fictional and labelled simulated; real data (Open-Meteo,
    Carbon Mapper, emission factors) is labelled real and attributed. No real operator names or logos.
11. **Human approves.** The AI never issues a work order or files a report on its own. Approve /
    edit / reject; one redraft after the first rejection; a second rejection escalates.
12. **Verify before claiming done.** Run tests, lint and type-check and show the output. For UI
    work, open it in a browser and check it (Playwright). "Should work" is not done.
13. **3D performance budget:** 60 fps at 1080p on integrated graphics. Instance repeated parts;
    check the budget for each new scene feature.
14. **Skill install gate.** Any new skill or plugin goes through the SkillSpector scan in the
    owner's global `CLAUDE.md` before install.
15. **Scope discipline.** Do the task in the plan, nothing more. No new dependencies, features or
    refactors outside the task without asking.
16. **Repo structure is fixed.** Every file goes where the `repo-structure` skill says. No new
    top-level folders, packages or features without the owner's approval. After creating, moving
    or renaming files, run
    `python -I .claude/skills/repo-structure/scripts/check_structure.py .` — it must print `structure OK`.
17. **Docs move with the code.** Every code change updates, in the same change: Google-style
    docstrings (Python) / TSDoc (TypeScript), the matching detailed `docs/reference/*.md` page,
    affected diagrams, setup/API docs, and a `docs/WORK_LOG.md` entry. A task without its docs is
    not done. See the `project-documentation` skill and its `references/code-comments.md`.
18. **Security gates.** Quick gate before every commit, full gate at the end of every phase,
    a dedicated security-hardening phase (Phase 6), release gate before the project is called complete
    (Phase 7, local) — see the `security-checks` skill. High/critical findings block.
19. **Database.** Local Supabase only. Schema changes only through new migrations in
    `app/supabase/migrations/` (never edit an applied one, never change the DB by hand). Schema
    `plumetrace`, RLS enabled on every table. Only `plumetrace.db` and the injected LangGraph
    checkpointer touch the database. The checkpoint is graph state; the operator's decision is
    recorded in `plumetrace.decisions`.
20. **No god files.** Small modules with one responsibility each; split files, components and
    functions instead of growing them. Limits (enforced by `check_structure.py`): Python module
    ≤ 300 lines, function ≤ 50, class ≤ 200, ≤ 12 top-level definitions; TS/TSX file ≤ 250 lines;
    tests ≤ 500 (Python) / 400 (TS); SQL migration ≤ 300; prompt ≤ 200. No `manager.py`,
    `service.py`, `core.py`, `handlers.py`, `utils.*`, `helpers.*`, `Main.tsx`. Never raise a limit,
    add an exemption or compress code to pass — split it, or ask the owner. See `repo-structure`.
21. **3D work follows `frontend-3d` (approach B: Blender-baked).** The station is generated by the
    bpy script in `scripts/blender/` from `ks07.yaml`, lighting baked, exported to
    `app/frontend/public/models/ks07.glb` (≤ 15 MB) — never modelled or edited by hand. Plume,
    highlights, labels and camera are real-time R3F. No `setState` or allocation in `useFrame`,
    local assets only, quality tiers, 60 fps measured and recorded. A 2-day spike validates B
    first; fallback is approach A. Free tools only: Blender, glTF-Transform,
    Poly Haven CC0.
22. **No AI slop in the frontend.** Follow `.ux-profile.md` and
    `frontend-design/references/anti-slop.md`: no gradients/gradient text, glassmorphism, neon
    glows, purple "AI" accents, emoji or sparkle icons, filler marketing copy, placeholder text,
    decorative infinite animations, identical rounded cards, or hard-coded demo numbers. Every UI
    task passes `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src`
    (`no slop found`) and a screenshot critique (`impeccable` or `design-skills:design-critique`)
    recorded in `docs/WORK_LOG.md`.

23. **OpenAI spend cap: $4.00 in total** (owner decision 2026-11-13). Model `gpt-6-luna` only.
    Every billed call is written to `plumetrace.llm_calls` and checked against
    `PLUMETRACE_SPEND_CAP_USD` before the next call. Never raise the cap, never bypass the
    ledger, never call OpenAI outside `BudgetedLLM`. Before any paid step, state runs, estimated
    cost, spend so far and the cap, and wait for the owner's yes.
24. **Everything is stored in local Supabase:** runs, agent steps with tool inputs/outputs,
    drafts, decisions, outputs, LLM calls, backend logs (`app_logs`, redacted), eval results and
    the LangGraph checkpoints (schema `langgraph`) — for live, eval and record runs alike.

25. **Checks are local only.** GitHub Actions are not used (owner decision 2026-11-13, billing): no
    `.github/` folder (`check_structure.py` refuses one). Run `python scripts/ci_local.py` (quick; the
    git pre-commit hook runs it) and `python scripts/ci_local.py --full` before every phase gate.
    Never commit with `--no-verify`.
26. **Test layers, not only unit tests.** Every change gets the layers the `testing-strategy` skill
    requires (unit, property-based, integration with the DB, API, graph branches, component,
    contract, fuzz, security, e2e, accessibility, performance). No paid call in any automated test.
27. **No deployment now.** No Vercel project, no `vercel` command, no live URL in any file —
    deployment is a later phase that is not planned yet (owner decision 2026-11-13).

## Definition of done (every task)
1. Code + tests written test-first with the layers `testing-strategy` requires; `python scripts/ci_local.py` passes (lint incl. pydocstyle Google + Ruff `S`, types, tests) — output shown. Phase gates: `--full`.
2. Docs updated per rule 17.
3. `check_structure.py` prints `structure OK` (layout, imports and no-god-file limits).
4. `secret_scan.py` prints `no secrets found` and `check_env.py` prints `env OK`.
5. Reviewed against the design (`verify-and-review`) for phase-end tasks.
6. UI tasks: `check_slop.py` prints `no slop found` and the screenshot critique is done (rule 22).

## Skills to use

| When | Skill |
|---|---|
| Implementing any plan task (load first) | `plan-execution` (project) |
| Planning from the design | `superpowers:writing-plans` |
| Executing the plan | `plan-execution` → "Orchestrator mode" with `.claude/agents/plumetrace-implementer.md` + `plumetrace-reviewer.md` (one task at a time, no parallel implementers); single-session fallback: `superpowers:executing-plans` |
| Every code task | `superpowers:test-driven-development`, `testing-strategy` (project) |
| Before saying done | `superpowers:verification-before-completion`, `verify-and-review` (project) |
| Code review | `verify-and-review` (project) → review-plumetrace-code |
| Where a file goes, new modules/features, moves | `repo-structure` (project) |
| Docs, docstrings, work log, diagrams (after every code change) | `project-documentation` (project) |
| Security gates, secrets, LLM/agent risks, API hardening | `security-checks` (project) |
| Git, commits, PRs | `contribution-workflow` (project) |
| Bugs / failing tests | `superpowers:systematic-debugging` |
| End of each phase | `superpowers:requesting-code-review` |
| Physics and calculations | `engineering-core` (project) |
| LangGraph graph, nodes, approval | `langgraph` (project) |
| LangSmith tracing and evals | `langsmith-trace` (project) |
| Agent prompts and evaluators | `agentic-council:oracle-prompt-engineering`, `agentic-council:oracle-ai-evaluation` |
| FastAPI endpoints, WebSocket, Pydantic | `fastapi` (project) |
| Visual direction | `frontend-design` (project) |
| Frontend code structure, state, data sources | `frontend-structure` (project) |
| 3D station: R3F, equipment, plume, camera, 3D performance and tests | `frontend-3d` (project) |
| UI components | `shadcn` (project) |
| UI polish and critique | `impeccable` (project), `design-skills:design-critique` |
| Avoiding AI-slop UI | `vectorlab-ux-skills:anti-slop` + `.ux-profile.md` + `frontend-design/references/anti-slop.md` |
| Charts and KPI tiles | `dataviz` |
| Browser checks | `playwright-cli` |
| Security hardening phase (Phase 6) and the release gate (Phase 7) | `security-checks`, `security-review`, `backend-design:security-reviewer` |
| Database schema, migrations, RLS, SQL | `supabase:supabase`, `supabase:supabase-postgres-best-practices` |
| Deploying the replay site | later phase, not planned yet — do not use `deploy-to-vercel` / `vercel-cli-with-tokens` now |

## Commands (once scaffolded)

- Database (from `app/`): `npx supabase@<pinned> start`, `npx supabase@<pinned> db reset` (re-applies migrations + seed), `npx supabase@<pinned> stop`
- Python (from `app/`): `uv sync --frozen`, `uv run pytest app/backend app/agents -q`, `uv run ruff check`,
  `uv run fastapi dev backend/plumetrace/api/main.py`
- Frontend (from `app/frontend/`): `npm ci`, `npm run dev`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`
- Checks (repo root): `python scripts/ci_local.py` (quick) · `python scripts/ci_local.py --full` · `python scripts/install_git_hooks.py` (once per clone)
- Replay build (from `app/frontend/`): `npm run build:replay` · `npm run preview:replay` (local only; no deployment)
