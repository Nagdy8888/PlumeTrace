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
