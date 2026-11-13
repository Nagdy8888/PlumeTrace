# Phase 8 · Aerial survey model, site mass balance, OGMP Level 5 reconciliation

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §11.1 stretch: quarterly aerial survey, mass balance and OGMP Level 5 reconciliation (the MVP shows Level 4 honestly).

## What the full plan must cover
- engineering: aerial survey detection model (detection limit, measurement uncertainty) and a site-level mass balance — pure, test-first, cited (engineering-core skill)
- reconciliation of bottom-up (source level) and top-down (site level) estimates with uncertainty
- UI: the OGMP level badge changes only when a reconciliation exists; still labelled a simplification

## Risks to resolve while planning
- every parameter needs a cited source; an owner review of the physics assumptions like Gate 2

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
