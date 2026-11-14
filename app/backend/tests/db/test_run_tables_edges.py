"""Edge-case tests for the run tables and repositories (needs the local Supabase Postgres)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

from plumetrace.db.events import insert_events, list_events
from plumetrace.db.readings import Reading, get_series, insert_readings
from plumetrace.db.runs import add_usage, create_run, get_run, set_run_status
from plumetrace.engineering.detection import DetectionEvent

START = datetime(2025, 7, 14, 6, 0, tzinfo=UTC)
Conn = psycopg.Connection[tuple[object, ...]]


def _event(window: int, sensor: str = "AT-104", mean_ppm: float = 4.0) -> DetectionEvent:
    return DetectionEvent(
        sensor_id=sensor,
        window_index=window,
        window_start_s=window * 600.0,
        mean_ppm=mean_ppm,
        baseline_ppm=1.95,
        cusum=6.0,
        downwind_of_site=True,
    )


def _run(conn: Conn) -> UUID:
    return create_run(conn, scenario_id="s1_rod_packing", mode="record", sim_start_utc=START)


def _count(conn: Conn, table: str, run_id: UUID) -> int:
    query = sql.SQL("select count(*) as n from plumetrace.{} where run_id = %s").format(
        sql.Identifier(table)
    )
    with conn.cursor(row_factory=dict_row) as cur:
        row = cur.execute(query, (run_id,)).fetchone()
    assert row is not None
    count: int = row["n"]
    return count


def test_new_run_defaults(db_conn: Conn) -> None:
    """A new run is running, unfinished, with zero usage and the given optional fields."""
    with db_conn.transaction(force_rollback=True):
        run_id = create_run(
            db_conn,
            scenario_id="s5_sensor_drift",
            mode="eval",
            sim_start_utc=START,
            variant_seed=7,
            branch="reject_redraft",
        )
        row = get_run(db_conn, run_id)
        assert (row.status, row.finished_at, row.variant_seed) == ("running", None, 7)
        assert row.branch == "reject_redraft" and row.sim_start_utc == START
        assert (row.prompt_tokens, row.completion_tokens, row.cost_usd) == (0, 0, Decimal(0))


@pytest.mark.parametrize("status", ["completed", "aborted_budget", "failed"])
def test_final_status_sets_finished_at(db_conn: Conn, status: Any) -> None:
    """Each final status stamps finished_at."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        set_run_status(db_conn, run_id, status)
        assert get_run(db_conn, run_id).finished_at is not None


def test_non_final_status_leaves_finished_at_empty(db_conn: Conn) -> None:
    """awaiting_approval is not final."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        set_run_status(db_conn, run_id, "awaiting_approval")
        row = get_run(db_conn, run_id)
        assert row.status == "awaiting_approval" and row.finished_at is None


def test_unknown_run_raises_key_error(db_conn: Conn) -> None:
    """Reading or changing a run that does not exist is an error, never a silent no-op."""
    missing = uuid4()
    with db_conn.transaction(force_rollback=True):
        with pytest.raises(KeyError, match=str(missing)):
            get_run(db_conn, missing)
        with pytest.raises(KeyError, match=str(missing)):
            set_run_status(db_conn, missing, "failed")
        with pytest.raises(KeyError, match=str(missing)):
            add_usage(db_conn, missing, prompt_tokens=1, completion_tokens=1, cost_usd=Decimal(1))


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
def test_add_usage_rejects_non_finite_cost(db_conn: Conn, bad: Decimal) -> None:
    """A NaN cost would pass the >= 0 check in Postgres, so it is refused before the query."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        with pytest.raises(ValueError, match="finite"):
            add_usage(db_conn, run_id, prompt_tokens=1, completion_tokens=1, cost_usd=bad)
        assert get_run(db_conn, run_id).cost_usd == Decimal(0)


def test_add_usage_cannot_make_totals_negative(db_conn: Conn) -> None:
    """The check constraints refuse a negative increment that would push a total below zero."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        with pytest.raises(psycopg.errors.CheckViolation), db_conn.transaction():
            add_usage(db_conn, run_id, prompt_tokens=-1, completion_tokens=0, cost_usd=Decimal(0))
        with pytest.raises(psycopg.errors.CheckViolation), db_conn.transaction():
            add_usage(db_conn, run_id, prompt_tokens=0, completion_tokens=0, cost_usd=Decimal(-1))


def test_bad_enum_values_are_rejected(db_conn: Conn) -> None:
    """mode, branch and status are limited by check constraints even if typing is bypassed."""
    bad: Any = "nonsense"
    with db_conn.transaction(force_rollback=True):
        with pytest.raises(psycopg.errors.CheckViolation), db_conn.transaction():
            create_run(db_conn, scenario_id="s1_rod_packing", mode=bad, sim_start_utc=START)
        with pytest.raises(psycopg.errors.CheckViolation), db_conn.transaction():
            create_run(
                db_conn,
                scenario_id="s1_rod_packing",
                mode="live",
                sim_start_utc=START,
                branch=bad,
            )
        run_id = _run(db_conn)
        with pytest.raises(psycopg.errors.CheckViolation), db_conn.transaction():
            set_run_status(db_conn, run_id, bad)


def test_repositories_do_not_commit(db_conn: Conn) -> None:
    """Rolling back the caller's transaction removes everything the repositories wrote."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        insert_events(db_conn, run_id, [_event(1)])
        insert_readings(db_conn, run_id, [Reading("AT-104", 0.0, 1.0, "ppm")])
    other = psycopg.connect(db_conn.info.dsn, password=db_conn.info.password)
    try:
        assert _count(other, "runs", run_id) == 0
    finally:
        other.close()


def test_insert_events_empty_and_duplicates_in_one_call(db_conn: Conn) -> None:
    """An empty list stores nothing; duplicates inside one call are stored once."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        assert insert_events(db_conn, run_id, []) == 0
        assert insert_events(db_conn, run_id, [_event(5), _event(5, mean_ppm=9.0)]) == 1
        stored = list_events(db_conn, run_id)
        assert [e.mean_ppm for e in stored] == [4.0], "the first event wins"


def test_events_are_ordered_and_scoped_to_the_run(db_conn: Conn) -> None:
    """Events come back by window_index then sensor_id, and only for the asked run."""
    with db_conn.transaction(force_rollback=True):
        run_id, other_id = _run(db_conn), _run(db_conn)
        insert_events(
            db_conn,
            run_id,
            [_event(30, "AT-106"), _event(12, "AT-106"), _event(12, "AT-104")],
        )
        insert_events(db_conn, other_id, [_event(99)])
        keys = [(e.window_index, e.sensor_id) for e in list_events(db_conn, run_id)]
        assert keys == [(12, "AT-104"), (12, "AT-106"), (30, "AT-106")]
        assert list_events(db_conn, uuid4()) == []


def test_events_round_trip_every_field(db_conn: Conn) -> None:
    """A stored event reads back equal to the original."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        original = _event(7)
        insert_events(db_conn, run_id, [original])
        assert list_events(db_conn, run_id) == [original]


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_insert_events_rejects_non_finite_numbers(db_conn: Conn, bad: float) -> None:
    """NaN or infinity in an event is refused, and nothing from that call is stored."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        with pytest.raises(ValueError, match="non-finite"):
            insert_events(db_conn, run_id, [_event(1), _event(2, mean_ppm=bad)])
        assert list_events(db_conn, run_id) == []


def test_insert_events_foreign_key_and_negative_window(db_conn: Conn) -> None:
    """An unknown run or a negative window index is refused by the database."""
    with db_conn.transaction(force_rollback=True):
        with pytest.raises(psycopg.errors.ForeignKeyViolation), db_conn.transaction():
            insert_events(db_conn, uuid4(), [_event(1)])
        run_id = _run(db_conn)
        with pytest.raises(psycopg.errors.CheckViolation), db_conn.transaction():
            insert_events(db_conn, run_id, [_event(-1)])


def test_readings_edge_cases(db_conn: Conn) -> None:
    """Empty input, None, duplicates (first wins), unknown tag and other runs."""
    with db_conn.transaction(force_rollback=True):
        run_id, other_id = _run(db_conn), _run(db_conn)
        insert_readings(db_conn, run_id, [])
        assert get_series(db_conn, run_id, "AT-106") == []
        insert_readings(db_conn, run_id, iter([Reading("AT-106", 0.0, 1.0, "ppm")]))
        insert_readings(
            db_conn,
            run_id,
            [Reading("AT-106", 0.0, 9.0, "ppm"), Reading("AT-106", 60.0, None, "ppm")],
        )
        insert_readings(db_conn, other_id, [Reading("AT-106", 0.0, 5.0, "ppm")])
        assert get_series(db_conn, run_id, "AT-106") == [(0.0, 1.0), (60.0, None)]
        assert get_series(db_conn, run_id, "AT-999") == []
        assert get_series(db_conn, other_id, "AT-106") == [(0.0, 5.0)]


def test_readings_unknown_run_is_rejected(db_conn: Conn) -> None:
    """The run foreign key protects reading integrity."""
    with db_conn.transaction(force_rollback=True):
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            insert_readings(db_conn, uuid4(), [Reading("AT-106", 0.0, 1.0, "ppm")])


def test_deleting_a_run_cascades(db_conn: Conn) -> None:
    """Events and readings are removed with their run."""
    with db_conn.transaction(force_rollback=True):
        run_id = _run(db_conn)
        insert_events(db_conn, run_id, [_event(1)])
        insert_readings(db_conn, run_id, [Reading("AT-104", 0.0, 1.0, "ppm")])
        db_conn.execute("delete from plumetrace.runs where run_id = %s", (run_id,))
        assert _count(db_conn, "events", run_id) == 0
        assert _count(db_conn, "sensor_readings", run_id) == 0


def test_new_tables_have_rls_and_no_policies(db_conn: Conn) -> None:
    """The three run tables are in schema plumetrace with RLS on and no policy."""
    names = ("runs", "events", "sensor_readings")
    rows = db_conn.execute(
        "select c.relname, c.relrowsecurity from pg_class c "
        "join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'plumetrace' and c.relname = any(%s)",
        (list(names),),
    ).fetchall()
    assert sorted(rows) == sorted((n, True) for n in names)
    policies = db_conn.execute(
        "select count(*) from pg_policies where schemaname = 'plumetrace' and tablename = any(%s)",
        (list(names),),
    ).fetchone()
    assert policies == (0,)


def test_events_run_id_index_exists(db_conn: Conn) -> None:
    """The index that serves list_events exists."""
    row = db_conn.execute(
        "select 1 from pg_indexes "
        "where schemaname = 'plumetrace' and indexname = 'events_run_id_idx'"
    ).fetchone()
    assert row == (1,)
