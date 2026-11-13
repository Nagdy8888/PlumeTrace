# Phase 8 — Stretch (only after Phase 7 is complete)

> **For agentic workers: these files are OUTLINES, not executable plans.** Before any stretch task
> starts, the planner expands its outline to the Phase 1–7 level of detail (exact files,
> interfaces, values, full test code) and the owner approves it. If `STATUS.md` names a Phase 8
> task whose file still says `Status: outline`, **STOP and ask** — do not fill gaps yourself.

**Goal:** the stretch items from design §11.1, each shippable on its own, in the owner's order.

| # | File | Delivers | Depends on |
|---|---|---|---|
| 1 | `task-01-s2-thief-hatch.md` | Scenario S2: tank thief hatch left open after gauging | Phase 7 |
| 2 | `task-02-s3-unlit-flare.md` | Scenario S3: unlit flare, super-emitter handling | Phase 7; a super-emitter rule in the rules table (Phase 5 Task 4) |
| 3 | `task-03-s6-ogi-flange.md` | Scenario S6: small flange leak found only by the quarterly OGI survey | Phase 7 |
| 4 | `task-04-carbon-mapper-panel.md` | Regional satellite context panel (real Carbon Mapper data) | licence check first |
| 5 | `task-05-pdf-export.md` | PDF export of approved work orders and report lines | Phase 7 |
| 6 | `task-06-aerial-mass-balance.md` | Quarterly aerial survey model, site mass balance, OGMP Level 5 reconciliation | Phase 2 engineering core |
| 7 | `task-07-night-mode.md` | Night lighting mode for the 3D station | Phase 4 3D |

## Constraints that already apply (from earlier phases)
All CLAUDE.md rules; new scenarios follow Phase 3 (seeded definitions, `expected` outcomes, variant families, replay export) and Phase 5 (eval cases, recorded traces for both branches); new UI passes the anti-slop gate and screenshot critique; new data sources are labelled and attributed; new rules come only from transcribed texts with citations; every paid OpenAI call counts against the $4 total spend cap (CLAUDE.md rule 23) — a stretch task that needs paid runs states its cost against what is left and the owner decides whether to raise the cap.
