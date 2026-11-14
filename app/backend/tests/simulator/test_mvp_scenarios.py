"""The three MVP scenarios behave as their stories require (truth physics, real weather)."""

import pytest

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import SCENARIOS, get_scenario
from plumetrace.simulator.scenarios.s4_planned_blowdown import S4_VENTED_CH4_KG
from plumetrace.simulator.selection import s1_passes, s4_passes, s5_passes
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def test_registry() -> None:
    """Exactly the three MVP scenarios are registered."""
    assert set(SCENARIOS) == {"s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"}
    with pytest.raises(KeyError, match="s9"):
        get_scenario("s9_unknown")


def test_s1_story() -> None:
    """S1: detected after the leak starts; inversion points at VS-250.tip."""
    assert s1_passes(run_scenario(get_scenario("s1_rod_packing"), SPEC, SNAP), SPEC)


def test_s4_story() -> None:
    """S4: the blowdown is detected during its window and nothing before it."""
    assert s4_passes(run_scenario(get_scenario("s4_planned_blowdown"), SPEC, SNAP))


def test_s5_story() -> None:
    """S5: only the drifting sensor raises events."""
    assert s5_passes(run_scenario(get_scenario("s5_sensor_drift"), SPEC, SNAP))


def test_s4_vented_mass_comes_from_the_blowdown_tool() -> None:
    """8 m3 from 4.5 MPa to ambient at 300 K vents a plausible CH4 mass (tens to hundreds kg)."""
    assert 50.0 < S4_VENTED_CH4_KG < 500.0
    s4 = get_scenario("s4_planned_blowdown")
    assert s4.sources[0].rate_kg_h == pytest.approx(S4_VENTED_CH4_KG / 0.25)
