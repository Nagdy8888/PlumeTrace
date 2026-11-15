"""In-process cache of computed scenario replays."""

import functools

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.export import build_replay
from plumetrace.simulator.replay_schema import ReplayScenario
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.weather import load_snapshot


@functools.lru_cache(maxsize=8)
def replay_for(scenario_id: str) -> ReplayScenario:
    """Compute the replay of one scenario with the truth model (cached per id).

    Args:
        scenario_id: For example ``s5_sensor_drift``.

    Returns:
        The replay document. Callers must not mutate it; it is shared between requests.

    Raises:
        KeyError: If no scenario has this id.
    """
    spec = load_facility()
    snapshot = load_snapshot()
    run = run_scenario(get_scenario(scenario_id), spec, snapshot)
    return build_replay(run, spec, snapshot.attribution)
