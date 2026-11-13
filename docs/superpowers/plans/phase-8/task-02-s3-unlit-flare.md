# Phase 8 · Scenario S3 — unlit flare and super-emitter

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §7 S3: the flare pilot goes out; more than 100 kg/h of methane slips; a public satellite would likely detect it; the AI flags a super-emitter event with top urgency and drafts the notification the operator policy requires.

## What the full plan must cover
- scenario definition: flare flow, TE-601 drop (pilot out), source at `FL-601.tip` with `flare_ch4_slip_kg_h(..., pilot_lit=False)`
- the super-emitter rule from a transcribed text (Phase 5 Task 4 found or did not find a threshold — if none exists, the expected outcome must not claim one; the owner decides)
- flare flame effect off while the pilot is out (Phase 4 `FlareFlame`)
- a notification draft type in `DraftBundle` (schema change → contract, frontend dialog section, evaluation)

## Risks to resolve while planning
- elevated release at 30 m: check the dispersion model's validity range for fence-line sensors (ENGINEERING.md limits)
- a draft schema change touches Phase 5 Tasks 2, 6, 13 and 14 — plan it as one change

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
