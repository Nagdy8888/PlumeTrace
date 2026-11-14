"""Tests for the run tables and repositories (needs the local Supabase Postgres)."""

from datetime import UTC, datetime
from decimal import Decimal

import psycopg

from plumetrace.db.events import insert_events, list_events
from plumetrace.db.readings import Reading, get_series, insert_readings
from plumetrace.db.runs import add_usage, create_run, get_run, set_run_status
from plumetrace.engineering.detection import DetectionEvent

START = datetime(2025, 7, 14, 6, 0, tzinfo=UTC)


def _event(window: int) -> DetectionEvent:
    return DetectionEvent(
        sensor_id="AT-104",
        window_index=window,
        window_start_s=window * 600.0,
        mean_ppm=4.0,
        baseline_ppm=1.95,
        cusum=6.0,
        downwind_of_site=True,
    )


def test_run_lifecycle(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """A run is created running, accumulates usage and finishes with a timestamp."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(
            db_conn,
            scenario_id="s1_rod_packing",
            mode="record",
            sim_start_utc=START,
            branch="approve",
        )
        add_usage(
            db_conn, run_id, prompt_tokens=100, completion_tokens=20, cost_usd=Decimal("0.0100")
        )
        add_usage(
            db_conn, run_id, prompt_tokens=50, completion_tokens=5, cost_usd=Decimal("0.0050")
        )
        set_run_status(db_conn, run_id, "completed")
        row = get_run(db_conn, run_id)
        assert row.status == "completed" and row.finished_at is not None
        assert (row.prompt_tokens, row.completion_tokens) == (150, 25)
        assert row.cost_usd == Decimal("0.0150")


def test_events_are_idempotent(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Saving the same events twice stores them once."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(
            db_conn, scenario_id="s1_rod_packing", mode="record", sim_start_utc=START
        )
        assert insert_events(db_conn, run_id, [_event(12), _event(30)]) == 2
        assert insert_events(db_conn, run_id, [_event(12)]) == 0
        assert [e.window_index for e in list_events(db_conn, run_id)] == [12, 30]


def test_readings_store_nan_as_null(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """Readings round-trip in time order; NaN becomes NULL."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(
            db_conn, scenario_id="s5_sensor_drift", mode="eval", sim_start_utc=START, variant_seed=7
        )
        insert_readings(
            db_conn,
            run_id,
            [Reading("AT-106", 60.0, float("nan"), "ppm"), Reading("AT-106", 0.0, 1.95, "ppm")],
        )
        assert get_series(db_conn, run_id, "AT-106") == [(0.0, 1.95), (60.0, None)]


def test_unknown_scenario_is_rejected(db_conn: psycopg.Connection[tuple[object, ...]]) -> None:
    """The scenario foreign key protects run integrity."""
    with db_conn.transaction(force_rollback=True):
        try:
            create_run(db_conn, scenario_id="s9_missing", mode="live", sim_start_utc=START)
        except psycopg.errors.ForeignKeyViolation:
            return
    raise AssertionError("expected a foreign key violation")
