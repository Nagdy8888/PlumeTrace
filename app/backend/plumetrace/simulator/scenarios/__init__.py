"""Registry of the MVP scenarios (S1, S4, S5)."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from plumetrace.simulator.scenario import ScenarioDefinition
from plumetrace.simulator.scenarios.s1_rod_packing import S1_ROD_PACKING
from plumetrace.simulator.scenarios.s4_planned_blowdown import S4_PLANNED_BLOWDOWN
from plumetrace.simulator.scenarios.s5_sensor_drift import S5_SENSOR_DRIFT

SCENARIOS: Final[Mapping[str, ScenarioDefinition]] = MappingProxyType(
    {d.id: d for d in (S1_ROD_PACKING, S4_PLANNED_BLOWDOWN, S5_SENSOR_DRIFT)}
)


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    """Return the registered scenario with this id.

    Args:
        scenario_id: For example ``s1_rod_packing``.

    Returns:
        The scenario definition.

    Raises:
        KeyError: If no scenario has this id.
    """
    if scenario_id not in SCENARIOS:
        raise KeyError(f"unknown scenario {scenario_id}")
    return SCENARIOS[scenario_id]
