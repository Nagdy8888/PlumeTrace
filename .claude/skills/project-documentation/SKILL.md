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
2. **Reference:** the matching `docs/reference/*.md` page is updated or created with the
   [deep documentation page template](#deep-documentation-page-template) below — what it does, why,
   inputs/outputs with units, assumptions, limits, failure behaviour, how to run and extend it — and
   its examples still run. A new page also gets a row in `docs/README.md`.
3. **Diagrams:** the page's inline Mermaid diagram is updated whenever behaviour, data flow or
   structure changed, and every block parses (see [Diagram standard](#diagram-standard)).
4. **Setup/API:** `docs/LOCAL_DEVELOPMENT.md` and `docs/reference/API.md` reflect new commands,
   env vars, endpoints or message formats; `.env.example` lists any new variable (names only).
5. **Work log:** `docs/WORK_LOG.md` gets an entry: date, plan task, changed paths, purpose,
   docs updated, verification commands with results, open gaps.
6. **Checks pass:** `uv run ruff check` (pydocstyle Google convention) and the frontend doc lint
   pass with zero docstring findings.

If a change truly needs no reference update (e.g. a typo fix), the work-log entry says why. A
reviewer FAILs a task with a missing or stale deep-doc section or diagram for a changed behaviour.

### Per-change docs checklist
- [ ] Docstrings/TSDoc on every new or changed definition; stale comments removed.
- [ ] Reference page section updated from the code (not from memory or the plan); worked example uses real values you ran.
- [ ] Diagram updated or added, matches the code, parses locally, has a one-line caption.
- [ ] Edge cases listed with the test that pins each (file and test name).
- [ ] Built versus planned stated; no planned part described as working.
- [ ] `docs/README.md` index row (new page) and relative links resolve.
- [ ] `docs/WORK_LOG.md` entry with the real verification output and gaps.
- [ ] Doc-versus-code inconsistencies you find are recorded in the page ("Known inconsistencies") and the work-log Gaps cell, not silently fixed in code.

### Honest labelling in docs
- Simulated station data, real public data (Open-Meteo, Carbon Mapper, emission factors) and synthetic benchmark results are labelled as what they are; the station is fictional.
- Inversion rates follow the binding display rule R1 to R4 (interval `p05-p95 (median p50)` at 2 significant figures, never the median alone; suppressed with a reason when inconclusive, top `NONE` or at the grid edge; always labelled "model estimate" or "model probability", never "confidence" or "calibrated"; public benchmark numbers only from the generated evidence JSON); see `docs/reference/INVERSION.md` section 6.
- Numbers in docs come from evidence (a command you ran, a generated report, a cited source), never invented or rounded into a better story. Do not write "validated", "accurate" or "production ready".
- Regulatory statements come only from the curated rules table and are framed as OGMP 2.0 plus an operator LDAR policy modelled on EU 2024/1787 (EU-import readiness).

## Required working loop

- Read the affected implementation reference through `docs/README.md`; verify its claims against actual source, schemas and configuration.
- Include meaningful adjacent contracts and the relevant focused `docs/reference/` explanation with each coherent change. A log, generated schema or one-line purpose label cannot replace them.
- Update affected setup/API/runbook/test guidance and append the actual step, changed paths, purpose, verification and gaps to `docs/WORK_LOG.md` before the next step. The entry covers its documentation changes too; do not log recursively.
- Before reporting completion or a phase commit, review all affected new/changed/renamed/deleted paths for documentation coverage and validate links, examples and applicable inline/architecture contracts. A passing presence check does not prove the prose is accurate or sufficiently deep.
- Keep prior runtime evidence dated. For prose/comment-only changes, use appropriate static/contract checks; do not invent a runtime rerun or invoke paid OpenAI/LangSmith calls solely for documentation validation.

## PlumeTrace documentation homes
The index with one row per page is `docs/README.md`; keep it current. Focused pages exist beyond
the list below (for example `DISPERSION`, `DETECTION`, `INVERSION`, `QUANTIFICATION`, `TRUTH_MODEL`,
`BENCHMARK`, `PHYSICS_PIPELINE`, `FACILITY`, `SCENARIOS`, `VARIANTS`, `WEATHER`, `DATA_LAYER`,
`UI_PANELS`, `DESIGN_SYSTEM`, `ACCESSIBILITY`, `WORKSPACE`, `CONFIGURATION`, `CHECKS`, `CONTRACT`):
extend the page that owns the responsibility; add a page only for a distinct reader or job, and add its index row.
- `docs/reference/ENGINEERING.md` — every physics model: equations, assumptions, validity limits, constants and their citations, units.
- `docs/reference/SIMULATOR.md` — facility spec, instruments, scenarios S1–S6, seeds.
- `docs/reference/AGENTS.md` — LangGraph graph, state, nodes, tools, approval/redraft, prompts, LangSmith tags and evaluators.
- `docs/reference/RULES.md` — the curated rules table and how each rule was verified against the regulation text.
- `docs/reference/FRONTEND.md` — features, data sources (live/replay), 3D scene, performance budget.
- `docs/reference/REPLAY.md` — trace format, branches, export and the static build.
- `docs/benchmark.md` — inversion benchmark results exactly as produced, with seed, revision and date.
- `docs/reference/API.md` — REST endpoints and WebSocket message formats.
- `docs/reference/DATABASE.md` — Supabase schema `plumetrace`: every table and column (type, unit, meaning), RLS stance, migrations list, checkpoint tables, ER diagram.
- `docs/reference/DEPLOYMENT.md` — Vercel settings recorded for a later phase; nothing is deployed (rule 27).
- `docs/reference/SECURITY.md` — threat model, controls and the latest security-checks report.
- `docs/reference/STRUCTURE.md` — repo layout (mirrors the repo-structure skill).
- `docs/LOCAL_DEVELOPMENT.md` — setup and commands. `docs/WORK_LOG.md` — step log.

## Deep documentation page template
Every `docs/reference/*.md` page is written so another developer can explain, operate and extend the
feature from the page and the source. Existing pages (for example `CONFIGURATION.md`, `FACILITY.md`,
`CHECKS.md`) are the models. Sections, in this order (rename to fit; skip one only when it truly does
not apply, and say so):
1. **Purpose and scope** — what this part does and does not do; owner module; what is built versus planned.
2. **How it works** — at least one inline Mermaid diagram of the right kind, a one-line caption under it, and the prose that walks it.
3. **Module-by-module reference** — each module/endpoint/component: public interface, inputs and outputs with units, the invariant it keeps.
4. **Worked example** — real values from a command you ran (seed, scenario, numbers), not invented ones.
5. **Edge cases and failure modes** — each with the test that pins it (file and test name) and what the user sees.
6. **Design decisions and assumptions** — and the design-doc section or owner ruling they come from; limits and known inconsistencies.
7. **Configuration** — env vars and settings with defaults (names only for secrets).
8. **How to run** — exact commands that match the current shell, with expected output.
9. **How to extend** — the invariants a future change must keep, and the steps to add the next item.
10. **Testing and evidence** — which tests prove it, latest results, evidence label.
11. **Related** — links to code, adjacent pages and the work-log entry. Changelog: dated one-liners for material changes.

## Diagram standard
- **Inline is the project standard.** Put each diagram in a fenced `mermaid` block inside the
  reference page it explains; GitHub renders it. Keep `.mmd` sources under `docs/diagrams/` with a
  rendered SVG only for a diagram reused in several pages, the README or the video, and then link
  it from the index. There is no repository diagram toolchain and none is added.
- **6 to 15 nodes per diagram**; split anything larger into focused views. A one-line caption (italic or `Caption:`) goes under each, saying what it shows.
- **Choose the type by the question:** flowchart for process and data flow; `sequenceDiagram` for interactions over time; `erDiagram` for tables; `classDiagram` for types; `stateDiagram-v2` for lifecycles; a C4-style container flowchart for architecture.
- **Label built versus planned.** Draw planned parts dotted and named PLANNED; never as running. Show the human-approval boundary and the live-versus-replay boundary where they matter.
- **Match the code.** Read the code before drawing; a diagram that disagrees with the code is a defect.
- **Validate locally, never upload.** Parse every block with the real parser in a throwaway folder
  outside the repo (see below). Never paste project diagrams into mermaid.live, Mermaid Chart or any
  public renderer. Add no dependency to the repository.

### Local syntax validation (throwaway, outside the repo)
```powershell
# in the session scratchpad (never inside the repo)
mkdir mermaid-check; cd mermaid-check; npm init -y; npm i mermaid jsdom
```
Write a small Node script that sets up `jsdom` globals, calls `mermaid.parse(block)` for each
```` ```mermaid ```` block extracted from the changed pages (regex on the fenced blocks) and prints the
file, block number and error. Every block must parse before the task is reported done. Nothing from the
scratch folder enters the repo. Parsing proves syntax only: also read the diagram
against the code, and where a render is practical inspect it for clipped labels and misleading edges.

## Professional visual documentation

For architecture, relationships, nontrivial workflows and states (the agent graph, data flow, replay), apply [mermaid-diagrams](references/mermaid-diagrams/GUIDE.md) and read [the visual documentation standard](references/visual-documentation.md). A syntactically valid diagram can still be misleading or unreadable: compare it with the code.

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
