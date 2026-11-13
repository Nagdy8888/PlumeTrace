# Phase 8 · Carbon Mapper regional satellite context panel

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §8: a panel showing real detected methane plumes in the region, labelled as real regional context. The first step is a licence check.

## What the full plan must cover
- read Carbon Mapper's current data licence and attribution terms; record them in ASSETS.md; the owner decides (design fallback: store only plume ids and coordinates and link to the portal, or drop the panel)
- `app/backend/plumetrace/data_sources/carbon_mapper.py` fetch and snapshot script (like the Open-Meteo snapshot in Phase 3) — no runtime fetching on the public site
- placement in `features/` needs the owner's approval (the feature list is fixed in `repo-structure`)

## Risks to resolve while planning
- the public site's CSP forbids third-party requests: everything must be a local snapshot file
- simulated station data never appears next to real data without labels

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
