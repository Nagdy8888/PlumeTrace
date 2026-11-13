# Phase 8 · Night mode for the 3D station

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §9 and the frontend-3d skill: night mode = global tint and exposure change plus emissive lights from the real-time layer; no second bake.

## What the full plan must cover
- `scene/NightMode.tsx`: exposure, sun off, lower HDRI intensity, emissive control-room windows (CR-901), equipment beacons; a toggle in the quality menu
- the 60 fps budget measured again; screenshot critique

## Risks to resolve while planning
- bloom budget with more emissive sources

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
