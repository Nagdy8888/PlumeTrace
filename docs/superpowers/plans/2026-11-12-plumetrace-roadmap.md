# PlumeTrace Roadmap (master plan)

> **For agentic workers:** this file is the index. Each phase is a folder (`phase-N/`) with a
> `README.md` (pinned versions, constraints, task order) and one self-contained file per task.
> Execute only the **task file** named in
> `docs/superpowers/plans/STATUS.md` as "current". Load the `plan-execution` skill first; it
> defines how to execute, when to stop, and how to report. Phases 1–7 are fully planned. Phase 8
> files are **outlines**: the planner expands one before it can be executed (STOP otherwise).
> At each owner gate the planner may revise the next phase's files if the gate changes anything.

**Goal:** Build PlumeTrace, the AI methane leak hunter for the simulated gas compressor station
"KS-07", as specified in the design.

**Spec:** `docs/superpowers/specs/2026-11-12-plumetrace-design.md` (read sections 1–15 before any phase).
**Rules:** `CLAUDE.md` (authoritative), project skills in `.claude/skills/`, `.ux-profile.md`.

## Phases

| # | Phase | Plan file | Depends on | Owner gate at end |
|---|---|---|---|---|
| 1 | Foundations: repo, uv workspace, config, local Supabase, frontend scaffold, type contract, facility spec, local check runner + pre-commit hook (no GitHub Actions) | `phase-1/` (README + 8 task files) | — | **Gate 1:** facility spec, gas composition, component-count table |
| 2 | Engineering core: units, gas properties, stability, dispersion, plume, averaging, detection, inversion, fusion, flare, blowdown, inventory, truth model, honest benchmark, property-based tests of the physics laws | `phase-2/` (README + 14 task files) | 1 | **Gate 2:** physics assumptions in `ENGINEERING.md` + benchmark results |
| 3 | Simulator + scenarios S1/S4/S5 + scenario-variant generator + Open-Meteo weather + DB tables for runs/events/readings + replay export + codec property tests | `phase-3/` (README + 9 task files) | 2 | **Gate 3:** scenario scripts reviewed |
| 4 | FastAPI app + control-room UI + 3D: design system, data layer, panels, Blender spike (owner go / no-go) → bpy pipeline (or fallback A) → R3F station, plume, accessibility, e2e + fps | `phase-4/` (README + 12 task files incl. 5b) | 1 (spec), 3 (data) | Spike review (Task 5), then **Gate 4:** UI review |
| 5 | Agents: schemas + provenance guard, tool protocol, rules table, AgentLLM + bounded loop, nodes, graph, agent tables, backend tools, runner + WebSocket, LangSmith + evals + baseline, backend logs in Supabase, trace export, agent panel, approval dialog, full-stack live e2e | `phase-5/` (README + 16 task files incl. 9b) | 2, 3, 4 | **Gate 5a:** rules table vs regulation text; **Gate 5b:** evaluation results |
| 6 | **Security hardening of the whole project:** threat model, rate limits and connection limits, request hardening (body limit, trusted hosts, headers, strict inputs), frontend output safety, least-privilege DB role, supply chain and history secret scan, API fuzzing + abuse tests | `phase-6/` (README + 8 task files) | 5 | **Gate 6a:** threat model; **Gate 6:** security evidence |
| 7 | Replay polish, performance pass, demo video, README + launch drafts, local release-readiness gate — **no deployment** | `phase-7/` (README + 5 task files) | 6 | Release-readiness review |
| 8 | Stretch (only after 7 is complete): S2, S3, S6, Carbon Mapper panel, PDF export, aerial survey + mass balance + Level 5, night mode | `phase-8/` (README + 7 **outline** files) | 7 | per task |
| — | Deployment of the replay site | **not planned yet** (owner decision 2026-11-13: a later phase after development) | 7 | — |

## Working rules that span every phase (owner decisions 2026-11-13)
- Checks are **local only**: `python scripts/ci_local.py` (quick; also the git pre-commit hook) and `--full` before every gate. No GitHub Actions, no `.github/`.
- Tests are **layered** (`testing-strategy` skill): unit, property-based, DB integration, API, graph branches, component, contract, fuzz, security, e2e (replay and full-stack live with the scripted model), accessibility, performance; LLM evaluations are paid and manual.
- OpenAI model `gpt-6-luna`; total spend cap **$4.00** (`PLUMETRACE_SPEND_CAP_USD`), enforced from `plumetrace.llm_calls`; every paid run traced in LangSmith; everything the app runs stored in local Supabase.

## Cross-phase contracts (do not change without the planner)
- Python packages: backend `plumetrace` (app/backend), agents `plumetrace_agents` (app/agents);
  agents never import backend (enforced by `check_structure.py`).
- Facility ids: equipment tags (e.g. `K-202`), anchors `<tag>.<anchor>` (e.g. `VS-250.tip`),
  sensors `AT-101`…`AT-108`, met mast `MET-01` — defined in Phase 1 Task 6, used by every later phase.
- Units in code: SI internally; names carry units (`rate_kg_h`, `u_m_s`, `conc_ppm`).
- Coordinates: site metres, x = east, y = north, z = up, origin = south-west fence corner.
- Wind direction: meteorological "from" degrees, clockwise from north.

## How progress is tracked
`docs/superpowers/plans/STATUS.md` holds the current phase, the last completed task, open
blockers and owner decisions. The executor updates it after every task (see `plan-execution`).
