"""Tests for flare methane slip."""

import pytest

from plumetrace.engineering.flare import flare_ch4_slip_kg_h


def test_unlit_flare_vents_all_methane() -> None:
    """Pilot out: every kg of methane sent to the flare is emitted (100 * 0.8624 = 86.24)."""
    assert flare_ch4_slip_kg_h(100.0, 0.8624, pilot_lit=False) == pytest.approx(86.24)


def test_lit_flare_slips_two_percent() -> None:
    """Lit flare at 98 % destruction: 2 % of 86.24 = 1.7248 kg/h."""
    assert flare_ch4_slip_kg_h(100.0, 0.8624, pilot_lit=True) == pytest.approx(1.7248)


def test_invalid_inputs() -> None:
    """Negative flow and impossible fractions are rejected."""
    with pytest.raises(ValueError):
        flare_ch4_slip_kg_h(-1.0, 0.8, pilot_lit=True)
    with pytest.raises(ValueError):
        flare_ch4_slip_kg_h(1.0, 1.2, pilot_lit=True)
