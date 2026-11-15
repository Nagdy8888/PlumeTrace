"""Re-saving a scenario run never duplicates rows (primary keys, ``on conflict do nothing``)."""

import psycopg

from plumetrace.api.run_store import readings_from_run, save_scenario_run
from plumetrace.db.events import insert_events, list_events
from plumetrace.db.readings import get_series, insert_readings
from plumetrace.db.runs import get_run
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.weather import load_snapshot

RUN = run_scenario(get_scenario("s5_sensor_drift"), load_facility(), load_snapshot())


_COUNT_SQL = {
    "events": "select count(*) from plumetrace.events where run_id = %s",
    "sensor_readings": "select count(*) from plumetrace.sensor_readings where run_id = %s",
}


def _count_rows(conn: psycopg.Connection[tuple[object, ...]], table: str, run_id: object) -> int:
    """Count the rows of one run in the events or sensor_readings table."""
    one = conn.execute(_COUNT_SQL[table], (run_id,)).fetchone()
    assert one is not None
    return int(str(one[0]))


def test_resaving_into_the_same_run_adds_no_rows(
    db_conn: psycopg.Connection[tuple[object, ...]],
) -> None:
    """Inserting the same events and readings again leaves the counts unchanged."""
    with db_conn.transaction(force_rollback=True):
        run_id = save_scenario_run(db_conn, RUN, mode="record")
        events, readings = (
            _count_rows(db_conn, "events", run_id),
            _count_rows(db_conn, "sensor_readings", run_id),
        )
        assert insert_events(db_conn, run_id, RUN.events) == 0
        insert_readings(db_conn, run_id, readings_from_run(RUN))
        assert _count_rows(db_conn, "events", run_id) == events == len(RUN.events)
        assert _count_rows(db_conn, "sensor_readings", run_id) == readings == 360 * 17


def test_saving_twice_makes_two_separate_runs(
    db_conn: psycopg.Connection[tuple[object, ...]],
) -> None:
    """Each save is its own run with its own full set of rows; nothing is shared or doubled."""
    with db_conn.transaction(force_rollback=True):
        first = save_scenario_run(db_conn, RUN, mode="record")
        second = save_scenario_run(db_conn, RUN, mode="record", branch="approve")
        assert first != second
        assert get_run(db_conn, second).branch == "approve"
        assert get_run(db_conn, first).variant_seed is None
        assert len(get_series(db_conn, first, "AT-106")) == 360
        assert len(get_series(db_conn, second, "AT-106")) == 360
        assert len(list_events(db_conn, first)) == len(list_events(db_conn, second))
