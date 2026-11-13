# Phase 8 · PDF export of approved outputs

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §11 (phase 6 item in the design): export an approved work order and report line as a PDF.

## What the full plan must cover
- `app/backend/plumetrace/reports/` PDF builder (a new dependency → pin it; the owner approves it)
- endpoint `GET /api/runs/{id}/report.pdf` (live only) and a pre-rendered PDF per recorded trace for the replay
- the PDF carries the simulated label, the source of every number and the rule citations

## Risks to resolve while planning
- the new dependency and its licence; PDF size; fonts must be local (IBM Plex, OFL)

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
