"""Repository for the ``plumetrace.runs`` table.

Every function takes an open connection and does not commit: the caller owns the transaction.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel

RunMode = Literal["live", "record", "eval"]
RunStatus = Literal["running", "awaiting_approval", "completed", "aborted_budget", "failed"]
Branch = Literal["approve", "reject_redraft"]

_FINAL_STATUSES = ("completed", "aborted_budget", "failed")


class RunRow(BaseModel):
    """One row of ``plumetrace.runs``.

    Attributes:
        run_id: Run id, equal to the LangGraph ``thread_id``.
        scenario_id: Scenario the run simulates.
        variant_seed: Seed of the scenario variant, ``None`` for the base scenario.
        mode: ``live``, ``record`` or ``eval``.
        status: Run status.
        branch: Approval branch the run takes, ``None`` when not scripted.
        sim_start_utc: UTC time that scenario second 0 maps to.
        started_at: Row creation time.
        finished_at: Set when the status becomes final, else ``None``.
        model_fast: Fast model name, if any.
        model_reasoning: Reasoning model name, if any.
        prompt_tokens: Prompt tokens used so far.
        completion_tokens: Completion tokens used so far.
        cost_usd: Cost so far in USD.
        langsmith_run_url: LangSmith trace URL, if any.
    """

    run_id: UUID
    scenario_id: str
    variant_seed: int | None
    mode: RunMode
    status: RunStatus
    branch: Branch | None
    sim_start_utc: datetime
    started_at: datetime
    finished_at: datetime | None
    model_fast: str | None
    model_reasoning: str | None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal
    langsmith_run_url: str | None


def create_run(
    conn: psycopg.Connection[tuple[object, ...]],
    *,
    scenario_id: str,
    mode: RunMode,
    sim_start_utc: datetime,
    variant_seed: int | None = None,
    branch: Branch | None = None,
) -> UUID:
    """Insert a run with status ``running``.

    Args:
        conn: Open connection; the caller commits.
        scenario_id: Id of an existing scenario.
        mode: ``live``, ``record`` or ``eval``.
        sim_start_utc: Timezone-aware UTC time of scenario second 0.
        variant_seed: Seed of the scenario variant, if any.
        branch: Approval branch the run takes, if scripted.

    Returns:
        The new ``run_id``.

    Raises:
        psycopg.errors.ForeignKeyViolation: If the scenario does not exist.
        psycopg.errors.CheckViolation: If ``mode`` or ``branch`` is not allowed.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "insert into plumetrace.runs (scenario_id, variant_seed, mode, status, branch, "
            "sim_start_utc) values (%s, %s, %s, 'running', %s, %s) returning run_id",
            (scenario_id, variant_seed, mode, branch, sim_start_utc),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("insert into plumetrace.runs returned no row")
    run_id: UUID = row["run_id"]
    return run_id


def set_run_status(
    conn: psycopg.Connection[tuple[object, ...]], run_id: UUID, status: RunStatus
) -> None:
    """Set the run status; a final status also sets ``finished_at`` to now.

    Args:
        conn: Open connection; the caller commits.
        run_id: Run to update.
        status: New status. ``completed``, ``aborted_budget`` and ``failed`` are final.

    Raises:
        KeyError: If the run does not exist.
        psycopg.errors.CheckViolation: If ``status`` is not allowed.
    """
    cur = conn.execute(
        "update plumetrace.runs set status = %s, "
        "finished_at = case when %s then now() else finished_at end where run_id = %s",
        (status, status in _FINAL_STATUSES, run_id),
    )
    if cur.rowcount == 0:
        raise KeyError(str(run_id))


def add_usage(
    conn: psycopg.Connection[tuple[object, ...]],
    run_id: UUID,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: Decimal,
) -> None:
    """Add token counts and cost to the run totals.

    Args:
        conn: Open connection; the caller commits.
        run_id: Run to update.
        prompt_tokens: Prompt tokens to add, not negative.
        completion_tokens: Completion tokens to add, not negative.
        cost_usd: Cost in USD to add, finite and not negative.

    Raises:
        ValueError: If ``cost_usd`` is not finite.
        KeyError: If the run does not exist.
        psycopg.errors.CheckViolation: If a total would become negative.
    """
    if not cost_usd.is_finite():
        raise ValueError(f"cost_usd must be finite, got {cost_usd}")
    cur = conn.execute(
        "update plumetrace.runs set prompt_tokens = prompt_tokens + %s, "
        "completion_tokens = completion_tokens + %s, cost_usd = cost_usd + %s "
        "where run_id = %s",
        (prompt_tokens, completion_tokens, cost_usd, run_id),
    )
    if cur.rowcount == 0:
        raise KeyError(str(run_id))


def get_run(conn: psycopg.Connection[tuple[object, ...]], run_id: UUID) -> RunRow:
    """Read one run.

    Args:
        conn: Open connection.
        run_id: Run to read.

    Returns:
        The run row.

    Raises:
        KeyError: If the run does not exist.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from plumetrace.runs where run_id = %s", (run_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(str(run_id))
    return RunRow(**row)
