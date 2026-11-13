---
name: project-documentation
description: Maintain deep implementation references, inline contracts, setup guides, runbooks, benchmark evidence and the work log for PlumeTrace. Required for every repository file-changing task and completed implementation, setup, or verification step, as well as explicit documentation requests.
license: Proprietary - original supplied notices retained in the source archive.
---

# Project Documentation (PlumeTrace)

Inspect the root `CLAUDE.md`, the design doc (`docs/superpowers/specs/2026-11-12-plumetrace-design.md`), the documentation index (`docs/README.md`, create it on first use) and affected source before editing. Preserve approved plans, evidence and unrelated changes. Documentation is part of the implementation step, not a later phase. Pure read-only answers without a completed operational step do not require a work-log entry.

Read [the deep documentation standard](references/deep-documentation.md) and [the code comments and Google docstring standard](references/code-comments.md) before the first file-changing or completed operational step in each turn. Read [document patterns](references/document-patterns.md) for the requested artifact. Apply depth to the affected contracts; a small change does not require new guides, an RFC or a fixed amount of prose.

## Non-negotiable: docs move with the code

**Every change to code updates its documentation in the same change.** There is no "docs later"
task. A code task is not done — and must not be reported done, committed or ticked in the plan —
until all of these are true:

1. **Inline:** every new or changed Python definition has a complete Google-style docstring
   (`Args`, `Returns`/`Yields`, `Raises`, units, valid ranges, side effects); every exported TS
   symbol has TSDoc. Removed code has its now-stale comments removed.
2. **Reference:** the matching `docs/reference/*.md` page describes the change in detail — what it
   does, why, inputs/outputs with units, assumptions, limits, failure behaviour, and how to extend
   it — and its examples still run.
3. **Diagrams:** affected `docs/diagrams/*.mmd` are updated and re-rendered when the flow, graph or
   architecture changed.
4. **Setup/API:** `docs/LOCAL_DEVELOPMENT.md` and `docs/reference/API.md` reflect new commands,
   env vars, endpoints or message formats; `.env.example` lists any new variable (names only).
5. **Work log:** `docs/WORK_LOG.md` gets an entry: date, plan task, changed paths, purpose,
   docs updated, verification commands with results, open gaps.
6. **Checks pass:** `uv run ruff check` (pydocstyle Google convention) and the frontend doc lint
   pass with zero docstring findings.

If a change truly needs no reference update (e.g. a typo fix), the work-log entry says why.

## Required working loop

- Read the affected implementation reference through `docs/README.md`; verify its claims against actual source, schemas and configuration.
- Include meaningful adjacent contracts and the relevant focused `docs/reference/` explanation with each coherent change. A log, generated schema or one-line purpose label cannot replace them.
- Update affected setup/API/runbook/test guidance and append the actual step, changed paths, purpose, verification and gaps to `docs/WORK_LOG.md` before the next step. The entry covers its documentation changes too; do not log recursively.
- Before reporting completion or a phase commit, review all affected new/changed/renamed/deleted paths for documentation coverage and validate links, examples and applicable inline/architecture contracts. A passing presence check does not prove the prose is accurate or sufficiently deep.
- Keep prior runtime evidence dated. For prose/comment-only changes, use appropriate static/contract checks; do not invent a runtime rerun or invoke paid OpenAI/LangSmith calls solely for documentation validation.

## PlumeTrace documentation homes
- `docs/reference/ENGINEERING.md` — every physics model: equations, assumptions, validity limits, constants and their citations, units.
- `docs/reference/SIMULATOR.md` — facility spec, instruments, scenarios S1–S6, seeds.
- `docs/reference/AGENTS.md` — LangGraph graph, state, nodes, tools, approval/redraft, prompts, LangSmith tags and evaluators.
- `docs/reference/RULES.md` — the curated rules table and how each rule was verified against the regulation text.
- `docs/reference/FRONTEND.md` — features, data sources (live/replay), 3D scene, performance budget.
- `docs/reference/REPLAY.md` — trace format, branches, export and the static build.
- `docs/benchmark.md` — inversion benchmark results exactly as produced, with seed, revision and date.
- `docs/reference/API.md` — REST endpoints and WebSocket message formats.
- `docs/reference/DATABASE.md` — Supabase schema `plumetrace`: every table and column (type, unit, meaning), RLS stance, migrations list, checkpoint tables, ER diagram.
- `docs/reference/DEPLOYMENT.md` — Vercel project settings, build command, headers, how replay data gets into the build.
- `docs/reference/SECURITY.md` — threat model, controls and the latest security-checks report.
- `docs/reference/STRUCTURE.md` — repo layout (mirrors the repo-structure skill).
- `docs/LOCAL_DEVELOPMENT.md` — setup and commands. `docs/WORK_LOG.md` — step log.

## Reference page template (each `docs/reference/*.md`)
1. Purpose and scope — what this part of PlumeTrace does and does not do.
2. How it works — the flow, with a diagram when there is more than one step.
3. Public interface — every public function/class/endpoint/message with inputs, outputs and units.
4. Design decisions and assumptions — and the design-doc section they come from.
5. Limits and failure behaviour — validity ranges, errors, what the user sees.
6. Configuration — env vars and settings, with defaults.
7. Testing and evidence — which tests prove it, how to run them, latest results.
8. How to extend — the invariants a future change must keep.
9. Changelog — dated one-liners for material changes.

## Professional visual documentation

For architecture, relationships, nontrivial workflows and states (the agent graph, data flow, replay), apply [mermaid-diagrams](references/mermaid-diagrams/GUIDE.md) and read [the visual documentation standard](references/visual-documentation.md). Run diagram render checks and inspect actual output; a syntactically valid diagram can still be misleading or unreadable.

## Ownership
- README is an entry point linking to setup, the actual workflow, the live link, the video and evidence.
- Setup/how-to explains a specific task; reference records contracts/configuration; explanation gives rationale; tutorials teach through a verified path.
- An ADR captures a material accepted decision. An RFC discusses an unresolved decision. An implementation plan sequences agreed work and preserves existing to-dos.
- Architecture views show actual actors, running processes, data stores, and external boundaries.
- Runbooks support diagnosis, remediation, and verification for actual operational conditions. [Runbook prompts](assets/runbook-prompts.md) and [decision prompts](assets/decision-prompts.md) are optional starting points.
- Release notes describe implemented user-visible changes.

## Evidence and scope
Use real commands, package versions, and observed results. Mark unavailable verification explicitly. Do not invent deployments, benchmark numbers, users or client results.
Do not copy secrets, populated environment files, or raw LangSmith traces. Clearly separate simulated station data, real public data, synthetic benchmark results, and local checks.
Update affected docs in the implementation task without automatically publishing, committing, or rewriting unrelated material. Validate relative links and meaningful command examples.
Use [contribution-workflow](../contribution-workflow/SKILL.md) for requested PR/release operations and [verify-engineering-coverage](../verify-and-review/references/engineering-coverage/GUIDE.md) for evidence-backed readiness.
