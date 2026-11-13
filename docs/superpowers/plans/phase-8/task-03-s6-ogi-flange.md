# Phase 8 · Scenario S6 — small flange leak found only by OGI

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §7 S6: a small flange leak below fence-line detection, found in the quarterly OGI survey; logged from the OGI evidence, rate estimated with leaker factors, repair deadline set.

## What the full plan must cover
- OGI survey data model and generator (survey date, findings with component ids from the facility component placement)
- `get_ogi_results` returns findings (today it is always empty) — backend tool change and tests
- event source = an OGI finding instead of a CUSUM event (`detect_event` input change; graph tests for the new entry path)
- `leaker_ch4_kg_h` (Phase 2 Task 11) as the rate tool for an OGI-found component

## Risks to resolve while planning
- a second detection path into the same graph — keep conditional edges only after triage and approval (CLAUDE.md rule 6)

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
