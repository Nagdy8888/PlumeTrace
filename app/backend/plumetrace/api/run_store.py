"""Persist a scenario run: the run row, its detection events and its 60 s readings.

This builds no inversion input and stores no inversion result: only simulator output is saved.
"""

from typing import Final
from uuid import UUID

import psycopg

from plumetrace.db.events import insert_events
from plumetrace.db.readings import Reading, insert_readings
from plumetrace.db.runs import Branch, RunMode, create_run
from plumetrace.engineering.averaging import window_means
from plumetrace.simulator.instruments import BASELINES
from plumetrace.simulator.runner import ScenarioRun

READINGS_STEP_S: Final = 60.0


def readings_from_run(run: ScenarioRun) -> list[Reading]:
    """Turn a run into 60 s mean readings for every methane sensor and every instrument.

    A minute without enough valid samples gives NaN, which the repository stores as ``NULL``.

    Args:
        run: The simulated scenario run.

    Returns:
        One reading per tag and minute; ``t_s`` is the window start, the unit is ``ppm`` for
        methane sensors and the ``BASELINES`` unit for instruments.
    """
    times_s = run.series.times_s
    starts, means = window_means(times_s, run.series.ppm, window_s=READINGS_STEP_S)
    out = [
        Reading(sensor.id, float(t), float(means[k, i]), "ppm")
        for i, sensor in enumerate(run.sensors)
        for k, t in enumerate(starts)
    ]
    for tag, values in run.instruments.items():
        _, inst = window_means(times_s, values.reshape(-1, 1), window_s=READINGS_STEP_S)
        unit = BASELINES[tag].unit
        out.extend(Reading(tag, float(t), float(inst[k, 0]), unit) for k, t in enumerate(starts))
    return out


def save_scenario_run(
    conn: psycopg.Connection[tuple[object, ...]],
    run: ScenarioRun,
    *,
    mode: RunMode,
    branch: Branch | None = None,
) -> UUID:
    """Store a scenario run, its events and its readings. Does not commit.

    Args:
        conn: Open connection; the caller commits.
        run: The simulated scenario run.
        mode: ``live``, ``record`` or ``eval``.
        branch: Approval branch the run takes, if scripted.

    Returns:
        The new run id.

    Raises:
        psycopg.errors.ForeignKeyViolation: If the scenario is not in ``plumetrace.scenarios``.
    """
    definition = run.definition
    run_id = create_run(
        conn,
        scenario_id=definition.id,
        mode=mode,
        sim_start_utc=run.sim_start_utc,
        variant_seed=definition.seed if definition.variant_index is not None else None,
        branch=branch,
    )
    insert_events(conn, run_id, run.events)
    insert_readings(conn, run_id, readings_from_run(run))
    return run_id
