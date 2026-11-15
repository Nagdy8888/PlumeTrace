"""Scenario list and replay endpoints."""

from fastapi import APIRouter, HTTPException

from plumetrace.api.scenario_cache import replay_for
from plumetrace.api.schemas import ScenarioSummary
from plumetrace.simulator.replay_schema import ReplayScenario
from plumetrace.simulator.scenarios import SCENARIOS

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios() -> list[ScenarioSummary]:
    """List the registered scenarios, sorted by id.

    Returns:
        One summary per scenario; all are MVP scenarios.
    """
    return [
        ScenarioSummary(id=d.id, title=d.title, duration_h=d.duration_h, is_mvp=True)
        for d in sorted(SCENARIOS.values(), key=lambda d: d.id)
    ]


@router.get("/{scenario_id}/replay", responses={404: {"description": "Unknown scenario"}})
def scenario_replay(scenario_id: str) -> ReplayScenario:
    """Return the full time series of one scenario, computed with the truth model.

    Args:
        scenario_id: Scenario id from the list endpoint.

    Returns:
        The replay document (simulated station; no inversion result, no AI output).

    Raises:
        HTTPException: 404 with a generic message if the id is unknown (never echoed).
    """
    try:
        return replay_for(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown scenario") from None
