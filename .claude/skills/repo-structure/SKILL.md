---
name: repo-structure
description: The one allowed layout of the PlumeTrace repository - app/backend (FastAPI + engineering), app/agents (LangGraph), app/frontend (React/Vite, built and previewed locally; deployment is a later phase), app/supabase (local Supabase Postgres), where every file goes, naming conventions, dependency direction between the three apps, the "no god files" size limits, and the structure checker. Use before creating, moving or renaming any file or folder, before adding a module or feature, and when reviewing a diff for misplaced code.
---

# Repo structure (PlumeTrace)

Every agent places work **only** where this skill says. If something does not fit, stop and ask
the owner; do not invent a new top-level folder, a second place for the same kind of file, or a
"utils"/"misc"/"helpers" dumping ground.

Run the checker after any file is created, moved or renamed, and before every commit:

```bash
python -I .claude/skills/repo-structure/scripts/check_structure.py .
```

It must print `structure OK`. It checks allowed folders at each level, file placement, banned
names, the dependency direction between backend, agents and their packages, and the
"no god files" limits. Its rules are data in `scripts/structure_config.py`.

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
    ├── frontend/                  React + TS + Vite + R3F, built and previewed locally (deployment is a later phase)
    │   ├── package.json  lockfile  vite.config.ts  tsconfig*.json  index.html  components.json
    │   ├── vercel.json            build settings + security headers (CSP etc.), recorded for a later phase; nothing is deployed
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
    └── replay/                    generated data for the static replay build (previewed locally) — never hand-edited
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
- The frontend talks only to the backend API (live mode) or to replay files (local build). It never
  connects to Supabase or OpenAI.

## Naming

| Kind | Convention | Example |
|---|---|---|
| Python module / package | `snake_case` | `mass_balance.py` |
| Python test | `test_<module>.py`, mirrored path | `app/backend/tests/engineering/test_plume.py` |
| Agent node module | node name | `nodes/locate_quantify.py` |
| Prompt file | node name `.md` | `prompts/locate_quantify.md` |
| Quantity variables | unit suffix | `rate_kg_h`, `u_m_s`, `conc_ppm` |
| React component / hook / store | `PascalCase.tsx` / `useX.ts` / `store.ts` | `AlarmList.tsx` |
| SQL migration | `YYYYMMDDHHMMSS_<snake_name>.sql` | `20261113090000_create_runs.sql` |
| DB tables | `plumetrace.<plural_snake>` | `plumetrace.agent_steps` |
| Scenario / trace | `s<n>_<slug>` / `<scenario>/<branch>.json` | `s1_rod_packing/approve.json` |
| Docs | `UPPER_SNAKE.md` | `docs/reference/AGENTS.md` |
| Plans / specs | `YYYY-MM-DD-<topic>.md` | `2026-11-12-plumetrace-design.md` |

## Rules

1. One home per kind of file. Before creating a file, find its home in the tree above.
2. No new top-level folders, no new `app/*` sub-apps, no new packages under `plumetrace/` or
   `plumetrace_agents/`, and no new frontend `features/*` without the owner's approval **and** an
   update to this skill, the checker's allowlists and `docs/reference/STRUCTURE.md` in one change.
3. No `utils.py`, `helpers.py`, `misc/`, `common/` or `temp/`. Name modules by what they do.
4. Generated files (`app/replay/`, `app/frontend/src/shared/types/generated/`,
   `app/frontend/public/models/`, rendered SVGs) come from a script in `scripts/` and are never
   hand-edited.
5. Schema changes happen only through a new migration in `app/supabase/migrations/`; never edit an
   applied migration; never change the database by hand.
6. Tests mirror source paths. Every new source module gets its test module in the same change.
7. **No god files** — see the next section. The checker enforces the limits.
8. Moving or renaming a file updates every import, doc link and `docs/reference/STRUCTURE.md` in the
   same change, then re-run the checker.

## No god files

A "god file" is a module, component or class that does many jobs: it is long, imports half the
project, and every change touches it. PlumeTrace does not allow them. Build small modules with one
responsibility each, grouped in packages/folders, with a small public entry (`__init__.py` /
`index.ts`) that re-exports what callers need.

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

### How to split (by responsibility, never arbitrarily)
- **Python:** one concept per module (`plume.py`, `dispersion_coefficients.py`, `inversion.py`,
  `inversion_likelihood.py`); one node per file in `nodes/`; one router per resource in
  `api/routes/`; one repository per table group in `db/`. A long function becomes a few named
  steps (helpers in the same module, or a sibling module when they grow).
- **React:** one component per file; a component that renders several regions becomes a parent
  composing child components; state logic moves to a hook (`useX.ts`) or the feature's
  `store.ts`; constants and pure mapping functions move to their own module in the feature.
- **3D:** one component per equipment type or effect; parts in `parts/`; shaders split per
  material (see `frontend-3d`).
- **No catch-alls disguised as names:** no `manager.py`, `service.py`, `core.py`, `handlers.py`,
  `index.tsx` holding logic, or `Main.tsx` doing everything. Name modules by what they do.
- A barrel (`__init__.py`, `index.ts`) only re-exports; it contains no logic.

### When a limit blocks you
Split the file in the same change. Never raise a limit, add an exemption, or squeeze code onto
fewer lines to pass the check. If you believe a file genuinely needs more, stop and ask the
owner; a granted exception goes in `SIZE_EXCEPTIONS` in `scripts/structure_config.py` with the
reason and date.
