"""Tests for methane intensity (volume basis)."""

import pytest

from plumetrace.engineering.intensity import methane_intensity_percent


def test_one_percent() -> None:
    """6.785 kg/h CH4 = 10.000 Sm3/h (rho 0.6785 kg/Sm3); / 1000 Sm3/h throughput = 1.000 %."""
    assert methane_intensity_percent(6.785, 1000.0) == pytest.approx(1.0, rel=1e-3)


def test_zero_throughput_rejected() -> None:
    """Intensity is undefined without throughput."""
    with pytest.raises(ValueError):
        methane_intensity_percent(1.0, 0.0)
