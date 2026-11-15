# Phase 3 · Task 8 — Persist scenario runs to Supabase

**Skills:** `plan-execution`, `repo-structure` (orchestration lives in `api/`), `project-documentation`.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/api/__init__.py` (docstring: "FastAPI application and orchestration that combines simulator, agents and database."), `app/backend/plumetrace/api/run_store.py` |
| Create | `app/backend/tests/db/test_run_store.py` |

## Interface — `api/run_store.py`
- `READINGS_STEP_S: Final = 60.0`
- `def readings_from_run(run: ScenarioRun) -> list[Reading]` — 60 s means (`window_means(..., window_s=READINGS_STEP_S)`) for every methane sensor (unit `"ppm"`) and every instrument (unit from `BASELINES`), `t_s` = window start; NaN stays NaN (the repository stores NULL).
- `def save_scenario_run(conn: psycopg.Connection[tuple[object, ...]], run: ScenarioRun, *, mode: RunMode, branch: Branch | None = None) -> UUID` — `create_run(...)` with `scenario_id=run.definition.id`, `sim_start_utc=run.sim_start_utc`, `variant_seed=run.definition.seed if run.definition.variant_index is not None else None`; `insert_events`; `insert_readings(readings_from_run(run))`; returns the run id. Does not commit.

## Tests (full code) — `app/backend/tests/db/test_run_store.py`
```python
"""Saving a scenario run stores the run, its events and 60 s readings."""

import psycopg

from plumetrace.api.run_store import readings_from_run, save_scenario_run
from plumetrace.db.events import list_events
from plumetrace.db.readings import get_series
from plumetrace.db.runs import get_run
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.weather import load_snapshot

RUN = run_scenario(get_scenario("s5_sensor_drift"), load_facility(), load_snapshot())


def test_readings_are_one_minute_means() -> None:
    """6 h -> 360 readings per tag, 8 methane sensors + 9 instruments."""
    readings = readings_from_run(RUN)
    assert len(readings) == 360 * 17
    assert {r.unit for r in readings if r.tag.startswith("AT-")} == {"ppm"}


def test_save_scenario_run(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The run row, the AT-106 events and the readings are stored."""
    with db_conn.transaction(force_rollback=True):
        run_id = save_scenario_run(db_conn, RUN, mode="record")
        row = get_run(db_conn, run_id)
        assert row.scenario_id == "s5_sensor_drift" and row.status == "running"
        assert {e.sensor_id for e in list_events(db_conn, run_id)} == {"AT-106"}
        assert len(get_series(db_conn, run_id, "AT-106")) == 360
```

## Steps
- [x] Tests → FAIL → implement → full checks green (`check_structure.py`: `api` may import anything).
- [x] **Phase evidence.** Write `docs/evidence/2026-11-phase-3-scenarios.md`: for each MVP scenario — selected offset and UTC start, detection events (sensor, window, mean, baseline), the inversion result on the S1 event windows (top id, probability, rate and interval), replay file size. Generate the numbers with a short throwaway snippet you paste into the file together with its output (do not commit the snippet).
- [ ] **Docs.** DATABASE.md → "Saving scenario runs"; SIMULATOR.md complete. Work-log; `STATUS.md` (last 3.8, next 3.9).
- [ ] **Commit** `feat(runs): persist scenario runs to Supabase` and `docs(evidence): record phase 3 scenarios`. STOP.
