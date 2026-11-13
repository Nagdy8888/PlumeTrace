# Phase 3 — Simulator, scenarios, weather and run storage

> **For agentic workers:** load `plan-execution` first. **Start only after STATUS.md records Owner
> Gate 2 as signed off** (and, if the owner ordered a benchmark improvement round, after that
> round). Execute task files in numeric order, one per session/subagent, exactly as written.

**Goal:** turn the engineering core into a station that *runs*: real Open-Meteo weather for the
site, the non-methane instruments (vent header flow, packing temperatures, flare, tanks,
throughput), the permit/maintenance log, the three MVP scenarios (S1 rod packing via VS-250,
S4 planned blowdown, S5 sensor drift), randomised scenario variants for the agent evaluation,
replay files for the static replay build, and run storage in Supabase.

**Spec:** design §4, §7, §8, §9 (time model), §10 (replay budget), §10.1 (tables).

## Task order
| # | File | Delivers |
|---|---|---|
| 1 | `task-01-run-tables.md` | migration for runs/events/sensor_readings + `plumetrace.db` repositories |
| 2 | `task-02-open-meteo.md` | `data_sources/open_meteo.py`, `scripts/fetch_weather.py`, committed weather snapshot |
| 3 | `task-03-instruments.md` | `simulator/instruments.py` (FT-250, TT-20xP, flare, tanks, throughput) |
| 4 | `task-04-scenario-model.md` | `simulator/scenario.py` (definition, log entries, expected outcome) + `simulator/runner.py` |
| 5 | `task-05-mvp-scenarios.md` | S1, S4, S5 definitions + `scripts/select_scenario_windows.py` |
| 6 | `task-06-variants.md` | `simulator/variants.py` (scenario families for evaluation) |
| 7 | `task-07-replay-export.md` | `engineering/plume_field.py`, `simulator/replay_schema.py`, `simulator/export.py`, `scripts/export_scenarios.py` |
| 8 | `task-08-persist-runs.md` | `simulator/persist.py` (scenario run → Supabase) |
| 9 | `task-09-codec-property-tests.md` | Hypothesis property tests of the plume-grid codec |

## Pinned additions (checked 2026-11-13)
| Package | Version | Where |
|---|---|---|
| httpx | 0.28.1 | backend dependency (Task 2) |

## Global constraints
- All Phase 1 and Phase 2 constraints apply. `engineering/` stays pure; network I/O only in `data_sources/`; DB I/O only in `db/`.
- Simulator time: `t_s` seconds from the scenario start; `sim_start_utc` anchors it to real weather. Step `DT_S = 10.0`.
- Every scenario is deterministic for its seed. Scenario ids: `s1_rod_packing`, `s4_planned_blowdown`, `s5_sensor_drift`.
- Replay files ≤ 5 MB each (design §10). Generated files are never hand-edited.
- Stored readings are 60 s means (`READINGS_STEP_S = 60.0`), not raw 10 s samples.

## Review focus
1. Open-Meteo unreachable or returns gaps (`null` values) → the fetch script fails with a clear message; the loader rejects snapshots with gaps (Task 2).
2. Scenario longer than the weather snapshot → `ValueError` naming the scenario and hours needed (Task 4).
3. Two events for the same sensor inside the refractory period → only one (inherited from detection; asserted in Task 4).
4. Replay file over 5 MB → export fails (Task 7).
5. Re-saving the same scenario run → no duplicate rows (primary keys / `on conflict do nothing`, Task 8).

## Phase exit — Owner Gate 3
`docs/reference/SIMULATOR.md` complete; `app/replay/scenarios/*.json` generated; `docs/evidence/2026-11-phase-3-scenarios.md` lists, per MVP scenario, the detection events, the inversion result on the first event window (truth physics) and the replay file size. `STATUS.md`: "Phase 3 complete — waiting for Gate 3 (scenario scripts)". STOP.
