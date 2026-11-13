# Repository structure

The authoritative rules are in `.claude/skills/repo-structure/SKILL.md`; this page mirrors them for human readers.

## The tree

```text
PlumeTrace/
├── CLAUDE.md                      rules for all agents (authoritative)
├── README.md                      public entry point: problem, video, benchmark, setup link (no live link until the later deployment phase)
├── .gitignore   .env.example      (.env is local only, never committed)
├── .claude/skills/                project skills
│                                  (no .github/: GitHub Actions are not used — checks run locally
│                                   with scripts/ci_local.py and the git pre-commit hook)
├── .ux-profile.md                 visual profile + slop ban list read by UI skills
├── build/                         git-ignored scratch output (raw glb, bake caches)
├── scripts/                       repo-level tooling only (record traces, export schemas, render diagrams)
│   └── blender/                   bpy package that generates + bakes the 3D station (frontend-3d skill)
├── docs/                          all documentation (see project-documentation skill)
├── skills/                        LEGACY source copies from another project — ignored, never edited
└── app/
    ├── pyproject.toml  uv.lock    uv workspace root; members: backend, agents (one shared .venv)
    │
    ├── backend/                   FastAPI service + engineering + simulator   (package `plumetrace`)
    │   ├── pyproject.toml         depends on: plumetrace-agents (workspace), fastapi, psycopg, numpy …
    │   ├── plumetrace/
    │   │   ├── __init__.py
    │   │   ├── config.py          settings from env (pydantic-settings) — the ONLY place env is read
    │   │   ├── engineering/       PURE physics: units, constants, plume, inversion, flare, inventory,
    │   │   │                      mass_balance, reconciliation, aerial_survey
    │   │   ├── facility/          Station KS-07 spec (ks07.yaml) + typed loader
    │   │   ├── simulator/         instruments, weather, runner, scenarios/ (s1_*.py … s6_*.py)
    │   │   ├── rules/             rules_table.yaml (cited) + lookup
    │   │   ├── data_sources/      open_meteo.py, carbon_mapper.py (outbound HTTP lives only here)
    │   │   ├── db/                Supabase Postgres access: pool.py, repositories (runs, events,
    │   │   │                      agent_steps, drafts, decisions, work_orders, reports)
    │   │   ├── agent_tools/       implements plumetrace_agents' ToolProvider by calling engineering,
    │   │   │                      simulator, rules and db — the ONLY bridge from backend to agents' tools
    │   │   ├── reports/           work order / OGMP report / PDF rendering
    │   │   └── api/               main.py (FastAPI app), routes/, ws.py, schemas.py, graph_runner.py
    │   ├── benchmark/             inversion benchmark (model-mismatch generators, runner, report)
    │   └── tests/                 mirrors plumetrace/: tests/engineering/test_plume.py …
    │
    ├── agents/                    LangGraph agents   (package `plumetrace_agents`)
    │   ├── pyproject.toml         depends on: langgraph, langgraph-checkpoint, langchain-core,
    │   │                          langsmith, pydantic — NOT on the backend (the backend owns
    │   │                          langchain-openai and langgraph-checkpoint-postgres and injects them)
    │   ├── plumetrace_agents/
    │   │   ├── __init__.py        exports build_graph()
    │   │   ├── graph.py           build_graph(tools, llm, checkpointer) -> compiled StateGraph
    │   │   ├── state.py           PlumeTraceState (typed graph state)
    │   │   ├── routing.py         conditional-edge functions (after triage, after approval)
    │   │   ├── llm.py             AgentLLM protocol, message/turn models, ScriptedLLM fake
    │   │   ├── checkpoint.py      memory_checkpointer() for tests, CHECKPOINT_SCHEMA (backend builds PostgresSaver)
    │   │   ├── tracing.py         LangSmith run config: tags + metadata per run
    │   │   ├── export_trace.py    graph event stream -> replay JSON
    │   │   ├── nodes/             one module per node: detect_event, triage, locate_quantify,
    │   │   │                      compliance, draft_outputs, approval, redraft, escalate,
    │   │   │                      log_vented_volume, finalize
    │   │   ├── tools/             protocol.py (ToolProvider), recorder.py, registry.py (ToolSpec per
    │   │   │                      node), descriptions.py, fakes.py + fake_profiles.py (test provider)
    │   │   ├── schemas/           common.py, tool_call.py, tool_io_*.py (tool inputs/results),
    │   │   │                      outputs.py, drafts.py, decisions.py, provenance.py (number guard),
    │   │   │                      trace.py (replay trace format)
    │   │   └── prompts/           one .md prompt per LLM node (triage.md, compliance.md …)
    │   ├── evals/                 LangSmith dataset builder + evaluators
    │   └── tests/                 fake-LLM + fake-tools graph tests, every branch
    │
    ├── frontend/                  React + TS + Vite + R3F, deployed to Vercel (static replay build)
    │   ├── package.json  lockfile  vite.config.ts  tsconfig*.json  index.html  components.json
    │   ├── vercel.json            build settings + security headers (CSP etc.)
    │   ├── public/                static assets; replay data copied in at build time
    │   │   ├── models/            ks07.glb — GENERATED by scripts/blender + glTF-Transform
    │   │   ├── textures/          Poly Haven CC0 textures (local), env/ HDRI, fonts/
    │   ├── e2e/                   Playwright specs
    │   └── src/
    │       ├── main.tsx
    │       ├── app/               shell, layout, providers
    │       ├── features/          station3d/ alarms/ agentPanel/ trends/ kpis/ approval/ scenarios/ reports/
    │       │   └── <feature>/     index.ts, components/, hooks/, store.ts, *.test.tsx
    │       │                      (station3d has its own sub-layout: see the frontend-3d skill)
    │       ├── shared/            ui/ (shadcn), lib/, data/ (LiveSource, ReplaySource),
    │       │                      types/generated/, facility/
    │       └── styles/
    │
    ├── supabase/                  local Supabase (created by `supabase init` in app/)
    │   ├── config.toml
    │   ├── migrations/            YYYYMMDDHHMMSS_<name>.sql — schema `plumetrace`, RLS on every table
    │   └── seed.sql               facility + scenario reference rows only (no secrets)
    │
    └── replay/                    generated data for the static Vercel build — never hand-edited
        ├── scenarios/<scenario>.json
        └── traces/<scenario>/<branch>.json
```

## Dependency direction

```text
app/frontend ──HTTP/WS──▶ app/backend/plumetrace.api ──▶ plumetrace_agents (graph)
                                   │                         ▲
                                   ▼                         │ implements ToolProvider
              engineering ◀ facility ◀ simulator ◀ agent_tools ─┘
                    ▲            ▲         ▲            │
                 rules, data_sources, reports           ▼
                                                        db ──▶ Supabase Postgres (local)
```

- **`plumetrace_agents` never imports `plumetrace`.** Agents get tools, the LLM and the
  checkpointer injected through `build_graph(...)`. This keeps the graph testable with fakes and
  keeps a single direction: backend → agents.
- Inside `plumetrace` (backend):
  - `engineering` imports nothing else from the project.
  - `facility` → engineering only. `simulator` → engineering, facility.
  - `rules`, `data_sources`, `reports` → engineering, facility only.
  - `db` → `config` and pure `engineering` data types only (no api, agent_tools, simulator).
  - Orchestration that combines simulator + db (e.g. saving a scenario run) lives in `api/`
    (`api/run_store.py`), which may import anything.
  - `agent_tools` → engineering, facility, simulator, rules, db, and `plumetrace_agents.tools/schemas`.
  - `api` → anything. Only `api` and `agent_tools` may import `plumetrace_agents`.
- Inside `plumetrace_agents`: `schemas` imports nothing internal except `schemas`; `llm` imports only
  `schemas`; `nodes` may import `schemas`, `state`, `tools`, `llm`, `prompts`; only `graph.py` wires
  nodes, routing, llm and checkpointer.
- Only `config.py` reads environment variables. Outbound network: `data_sources/` (public data)
  and `api/openai_llm.py` (OpenAI, via langchain-openai). Database access: only `db/` and the
  checkpointer built in `api/checkpointer.py`.
- The frontend talks only to the backend API (live mode) or to replay files (Vercel). It never
  connects to Supabase or OpenAI.

## No god files

### Hard limits (enforced by `check_structure.py`)

| What | Limit |
|---|---|
| Python source module (`.py`, not a test) | ≤ 300 lines |
| Python function / method | ≤ 50 lines |
| Python class | ≤ 200 lines |
| Top-level functions + classes in one Python module | ≤ 12 |
| Python test module | ≤ 500 lines |
| TypeScript / TSX source file | ≤ 250 lines |
| TypeScript / TSX test file | ≤ 400 lines |
| SQL migration | ≤ 300 lines |
| Agent prompt (`prompts/*.md`) | ≤ 200 lines |

Lines are physical lines including docstrings and comments, so full Google docstrings count —
that is intended: if docs push a file over the limit, the file does too much. Exempt: generated
files (`app/frontend/src/shared/types/generated/`, `app/replay/`), lockfiles, JSON/YAML data.
