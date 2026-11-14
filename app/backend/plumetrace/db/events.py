"""Repository for the ``plumetrace.events`` table (CUSUM detection events).

Every function takes an open connection and does not commit: the caller owns the transaction.
"""

import math
from collections.abc import Sequence
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from plumetrace.engineering.detection import DetectionEvent


def insert_events(
    conn: psycopg.Connection[tuple[object, ...]], run_id: UUID, events: Sequence[DetectionEvent]
) -> int:
    """Store detection events; events already stored for the run are skipped.

    Args:
        conn: Open connection; the caller commits.
        run_id: Run the events belong to.
        events: Events to store. The key is ``(run_id, sensor_id, window_index)``.

    Returns:
        The number of rows actually inserted (duplicates are not counted).

    Raises:
        ValueError: If an event holds a NaN or infinite number.
        psycopg.errors.ForeignKeyViolation: If the run does not exist.
        psycopg.errors.CheckViolation: If a ``window_index`` is negative.
    """
    for event in events:
        numbers = (event.window_start_s, event.mean_ppm, event.baseline_ppm, event.cusum)
        if not all(math.isfinite(x) for x in numbers):
            raise ValueError(f"event {event.sensor_id}/{event.window_index} has a non-finite value")
    rows = [
        (
            run_id,
            e.sensor_id,
            e.window_index,
            e.window_start_s,
            e.mean_ppm,
            e.baseline_ppm,
            e.cusum,
            e.downwind_of_site,
        )
        for e in events
    ]
    inserted = 0
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                "insert into plumetrace.events (run_id, sensor_id, window_index, window_start_s, "
                "mean_ppm, baseline_ppm, cusum, downwind_of_site) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s) "
                "on conflict (run_id, sensor_id, window_index) do nothing",
                row,
            )
            inserted += cur.rowcount
    return inserted


def list_events(conn: psycopg.Connection[tuple[object, ...]], run_id: UUID) -> list[DetectionEvent]:
    """Read the detection events of a run.

    Args:
        conn: Open connection.
        run_id: Run to read.

    Returns:
        Events ordered by ``window_index`` then ``sensor_id``; empty for an unknown run.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "select sensor_id, window_index, window_start_s, mean_ppm, baseline_ppm, cusum, "
            "downwind_of_site from plumetrace.events where run_id = %s "
            "order by window_index, sensor_id",
            (run_id,),
        )
        return [DetectionEvent(**row) for row in cur.fetchall()]
