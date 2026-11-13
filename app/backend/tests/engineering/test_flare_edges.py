"""Edge cases of flare slip: zero and non-finite input, efficiency bounds, unlit, huge flow."""

import math

import pytest

from plumetrace.engineering.flare import DEFAULT_DESTRUCTION_EFFICIENCY, flare_ch4_slip_kg_h

NAN = float("nan")
INF = float("inf")


def test_default_destruction_efficiency_is_98_percent() -> None:
    """The default is the 0.98 of the plan: lit slip is 2 % of the methane sent to the flare."""
    assert DEFAULT_DESTRUCTION_EFFICIENCY == 0.98
    assert flare_ch4_slip_kg_h(50.0, 1.0, pilot_lit=True) == pytest.approx(1.0)


@pytest.mark.parametrize("pilot_lit", [True, False])
def test_zero_flow_or_zero_methane_gives_zero(pilot_lit: bool) -> None:
    """No gas, or gas without methane, slips nothing."""
    assert flare_ch4_slip_kg_h(0.0, 0.8, pilot_lit=pilot_lit) == 0.0
    assert flare_ch4_slip_kg_h(10.0, 0.0, pilot_lit=pilot_lit) == 0.0


def test_destruction_efficiency_bounds_are_inclusive() -> None:
    """DE = 1 destroys everything; DE = 0 on a lit flare equals an unlit flare."""
    assert flare_ch4_slip_kg_h(100.0, 0.8, pilot_lit=True, destruction_efficiency=1.0) == 0.0
    lit_de0 = flare_ch4_slip_kg_h(100.0, 0.8, pilot_lit=True, destruction_efficiency=0.0)
    assert lit_de0 == flare_ch4_slip_kg_h(100.0, 0.8, pilot_lit=False)


def test_unlit_flare_ignores_destruction_efficiency() -> None:
    """With the pilot out nothing is destroyed, whatever the stated efficiency."""
    slip = flare_ch4_slip_kg_h(100.0, 0.8, pilot_lit=False, destruction_efficiency=0.5)
    assert slip == pytest.approx(80.0)


def test_lower_efficiency_gives_more_slip() -> None:
    """Slip rises as efficiency falls and never exceeds the unlit value."""
    unlit = flare_ch4_slip_kg_h(100.0, 0.8, pilot_lit=False)
    prev = 0.0
    for de in (1.0, 0.99, 0.98, 0.9, 0.5, 0.0):
        slip = flare_ch4_slip_kg_h(100.0, 0.8, pilot_lit=True, destruction_efficiency=de)
        assert prev <= slip <= unlit
        prev = slip


def test_huge_flow_stays_finite() -> None:
    """A huge but finite flow cannot overflow: the result is at most flow * w."""
    out = flare_ch4_slip_kg_h(1.0e308, 1.0, pilot_lit=False)
    assert math.isfinite(out)
    assert out == 1.0e308


@pytest.mark.parametrize("flow", [-1.0, -1e-12, NAN, INF, -INF])
def test_bad_flow_is_value_error(flow: float) -> None:
    """Negative, NaN or infinite flow is rejected for lit and unlit flares."""
    for lit in (True, False):
        with pytest.raises(ValueError, match="flared_gas_kg_h"):
            flare_ch4_slip_kg_h(flow, 0.8, pilot_lit=lit)


@pytest.mark.parametrize("w", [-0.1, 1.0000001, NAN, INF, -INF])
def test_bad_methane_fraction_is_value_error(w: float) -> None:
    """A methane mass fraction outside [0, 1] (or NaN) is rejected."""
    with pytest.raises(ValueError, match="ch4_mass_fraction"):
        flare_ch4_slip_kg_h(10.0, w, pilot_lit=True)


@pytest.mark.parametrize("de", [-0.01, 1.01, NAN, INF, -INF])
@pytest.mark.parametrize("pilot_lit", [True, False])
def test_bad_destruction_efficiency_is_value_error(de: float, pilot_lit: bool) -> None:
    """Efficiency outside [0, 1] (or NaN) is rejected, also when the pilot is out."""
    with pytest.raises(ValueError, match="destruction_efficiency"):
        flare_ch4_slip_kg_h(10.0, 0.8, pilot_lit=pilot_lit, destruction_efficiency=de)
