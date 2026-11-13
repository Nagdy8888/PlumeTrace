# Phase 8 · Scenario S2 — tank thief hatch left open after gauging

**Status: outline** — the planner expands this file before execution (see the Phase 8 README). STOP if asked to implement it as it is.

## Why
Design §7 S2: after a gauging entry at TK-402 the thief hatch is left open; intermittent ~30–50 kg/h from `TK-402.thief_hatch`; the AI must tie it to the gauging log entry and check VRU status.

## What the full plan must cover
- `app/backend/plumetrace/simulator/scenarios/s2_thief_hatch.py` (seeded definition: intermittent source schedule, gauging log entry, PT-402 pressure effect, expected outcome)
- `InstrumentEffect`s for PT-402 (tank pressure drops while the hatch is open) — check that Phase 3 `instruments.py` supports it
- window selection criteria (`selection.py`), variant family (Phase 3 Task 6 rules), replay export
- eval cases and recorded traces (approve, reject_redraft) — paid runs, owner's yes
- a VRU status signal if the scenario needs it (today `vru_online` is always true — the full plan decides whether to add an instrument tag)

## Risks to resolve while planning
- intermittent-source inversion behaviour (the inversion assumes a steady source over a window range) — benchmark it before writing the scenario
- how the agents relate a gauging entry to a hatch (prompt change → new eval cases)

## Done means (same as every phase)
Tests first, docs updated (rule 17), structure / secrets / env / slop checks clean, owner review where a gate applies, `STATUS.md` updated.
