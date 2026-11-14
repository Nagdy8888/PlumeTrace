"""Repository for the ``plumetrace.sensor_readings`` table (60 s mean readings).

Every function takes an open connection and does not commit: the caller owns the transaction.
"""

import math
from collections.abc import Iterable
from typing import NamedTuple
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


class Reading(NamedTuple):
    """One stored reading.

    Attributes:
        tag: Instrument tag, for example ``AT-106``.
        t_s: Scenario time in seconds.
        value: Reading value; ``None`` (SQL ``NULL``) when the instrument gave no value.
        unit: Unit of ``value``, for example ``ppm``.
    """

    tag: str
    t_s: float
    value: float | None
    unit: str


def insert_readings(
    conn: psycopg.Connection[tuple[object, ...]], run_id: UUID, readings: Iterable[Reading]
) -> None:
    """Store readings; a reading whose ``(run_id, tag, t_s)`` already exists is skipped.

    A NaN value is stored as SQL ``NULL``.

    Args:
        conn: Open connection; the caller commits.
        run_id: Run the readings belong to.
        readings: Readings to store.

    Raises:
        psycopg.errors.ForeignKeyViolation: If the run does not exist.
    """
    rows = [
        (
            run_id,
            r.tag,
            r.t_s,
            None if r.value is not None and math.isnan(r.value) else r.value,
            r.unit,
        )
        for r in readings
    ]
    with conn.cursor() as cur:
        cur.executemany(
            "insert into plumetrace.sensor_readings (run_id, tag, t_s, value, unit) "
            "values (%s, %s, %s, %s, %s) on conflict do nothing",
            rows,
        )


def get_series(
    conn: psycopg.Connection[tuple[object, ...]], run_id: UUID, tag: str
) -> list[tuple[float, float | None]]:
    """Read one tag's series.

    Args:
        conn: Open connection.
        run_id: Run to read.
        tag: Instrument tag.

    Returns:
        ``(t_s, value)`` pairs ordered by ``t_s``; empty when the tag has no readings.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "select t_s, value from plumetrace.sensor_readings "
            "where run_id = %s and tag = %s order by t_s",
            (run_id, tag),
        )
        return [(row["t_s"], row["value"]) for row in cur.fetchall()]
