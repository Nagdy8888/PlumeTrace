"""Select the weather window of each MVP scenario from the committed weather snapshot.

For every scenario and every candidate offset (``CANDIDATE_OFFSETS_H``) that fits the snapshot,
the scenario is run with that offset and its criterion from ``plumetrace.simulator.selection``
is applied. The first passing offset per scenario is the one written into the scenario file
(``WEATHER_OFFSET_H``), by hand from this output, never guessed. No network is used.

Run it from the repo root::

    cd app && uv run python ../scripts/select_scenario_windows.py

The exit code is 1 when a scenario has no passing offset.
"""

from collections.abc import Callable

from plumetrace.facility.loader import load_facility
from plumetrace.facility.spec import FacilitySpec
from plumetrace.simulator.runner import ScenarioRun, run_scenario
from plumetrace.simulator.scenarios import SCENARIOS
from plumetrace.simulator.selection import (
    CANDIDATE_OFFSETS_H,
    s1_passes,
    s4_passes,
    s5_passes,
)
from plumetrace.simulator.weather import WeatherSnapshot, load_snapshot


def _criteria(spec: FacilitySpec) -> dict[str, Callable[[ScenarioRun], bool]]:
    """Map each scenario id to its pass/fail criterion."""
    return {
        "s1_rod_packing": lambda run: s1_passes(run, spec),
        "s4_planned_blowdown": s4_passes,
        "s5_sensor_drift": s5_passes,
    }


def select_windows(spec: FacilitySpec, snapshot: WeatherSnapshot) -> dict[str, int | None]:
    """Evaluate every candidate offset of every scenario and print one line per candidate.

    Args:
        spec: The facility spec.
        snapshot: The weather snapshot.

    Returns:
        Scenario id to its first passing offset in hours, or None when no offset passes.
    """
    first: dict[str, int | None] = {}
    for scenario_id, passes in _criteria(spec).items():
        definition = SCENARIOS[scenario_id]
        first[scenario_id] = None
        for offset_h in CANDIDATE_OFFSETS_H:
            if offset_h + definition.duration_h + 1 > len(snapshot.hours):
                continue
            run = run_scenario(
                definition.model_copy(update={"weather_offset_h": offset_h}), spec, snapshot
            )
            ok = passes(run)
            print(f"{scenario_id}: offset {offset_h} h {'PASS' if ok else 'FAIL'}")
            if ok and first[scenario_id] is None:
                first[scenario_id] = offset_h
    return first


def main() -> int:
    """Run the selection and print the first passing offset of each scenario.

    Returns:
        0 when every scenario has a passing offset, otherwise 1.
    """
    spec, snapshot = load_facility(), load_snapshot()
    first = select_windows(spec, snapshot)
    for scenario_id, offset_h in first.items():
        print(
            f"{scenario_id}: first passing offset {offset_h if offset_h is not None else 'NONE'} h"
        )
    return 0 if all(o is not None for o in first.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
