"""Edge cases of methane intensity: zero emission, bad input, scaling, overflow, no cap at 100 %."""

import math

import pytest

from plumetrace.engineering.intensity import methane_intensity_percent

NAN = float("nan")
INF = float("inf")


def test_zero_emission_is_zero_percent() -> None:
    """No methane emitted is exactly 0 % (valid, not an error)."""
    assert methane_intensity_percent(0.0, 1000.0) == 0.0


def test_linear_in_emission_and_inverse_in_throughput() -> None:
    """Twice the emission doubles the intensity; twice the throughput halves it."""
    base = methane_intensity_percent(3.0, 500.0)
    assert methane_intensity_percent(6.0, 500.0) == pytest.approx(2.0 * base, rel=1e-12)
    assert methane_intensity_percent(3.0, 1000.0) == pytest.approx(0.5 * base, rel=1e-12)


def test_value_matches_density_of_pure_methane_at_standard_conditions() -> None:
    """0.6785 kg/Sm3 (ideal gas, 288.15 K, 101325 Pa): 0.6785 kg/h over 100 Sm3/h is 1 %."""
    assert methane_intensity_percent(0.6785, 100.0) == pytest.approx(1.0, rel=1e-3)


def test_intensity_above_100_percent_is_not_capped() -> None:
    """67.85 kg/h CH4 = 100 Sm3/h; over 10 Sm3/h of gas that is 1000 %, not a clipped value."""
    assert methane_intensity_percent(67.85, 10.0) == pytest.approx(1000.0, rel=1e-3)


def test_tiny_throughput_stays_finite() -> None:
    """A very small positive throughput gives a large but finite percentage."""
    out = methane_intensity_percent(1.0, 1e-9)
    assert math.isfinite(out)
    assert out > 1e9


@pytest.mark.parametrize("throughput", [0.0, -0.0, -1.0, -1e-12, NAN, INF, -INF])
def test_bad_throughput_is_value_error(throughput: float) -> None:
    """Zero, negative, NaN or infinite throughput is rejected, naming the argument."""
    with pytest.raises(ValueError, match="throughput_sm3_h"):
        methane_intensity_percent(1.0, throughput)


@pytest.mark.parametrize("emitted", [-1.0, -1e-12, NAN, INF, -INF])
def test_bad_emission_is_value_error(emitted: float) -> None:
    """Negative, NaN or infinite emitted methane is rejected, naming the argument."""
    with pytest.raises(ValueError, match="ch4_emitted_kg_h"):
        methane_intensity_percent(emitted, 1000.0)


def test_overflowing_ratio_is_value_error() -> None:
    """A ratio that overflows to infinity is an error, never inf or NaN."""
    with pytest.raises(ValueError, match="finite"):
        methane_intensity_percent(1e308, 1e-300)
