"""Tests for the Pasquill-Gifford-Turner stability table (Turner 1994, Table 1-1)."""

import pytest

from plumetrace.engineering.stability import StabilityClass as S
from plumetrace.engineering.stability import pasquill_class

# (wind m/s, shortwave W/m2, cloud fraction) -> class; one case per table cell.
CELLS = [
    ((1.0, 700.0, 0.1), S.A),
    ((1.0, 400.0, 0.1), S.B),
    ((1.0, 100.0, 0.1), S.B),
    ((2.5, 700.0, 0.1), S.B),
    ((2.5, 400.0, 0.1), S.B),
    ((2.5, 100.0, 0.1), S.C),
    ((4.0, 700.0, 0.1), S.B),
    ((4.0, 400.0, 0.1), S.C),
    ((4.0, 100.0, 0.1), S.C),
    ((5.5, 700.0, 0.1), S.C),
    ((5.5, 400.0, 0.1), S.D),
    ((5.5, 100.0, 0.1), S.D),
    ((7.0, 700.0, 0.1), S.C),
    ((7.0, 400.0, 0.1), S.D),
    ((7.0, 100.0, 0.1), S.D),
    ((1.0, 0.0, 0.6), S.F),
    ((1.0, 0.0, 0.2), S.F),
    ((2.5, 0.0, 0.6), S.E),
    ((2.5, 0.0, 0.2), S.F),
    ((4.0, 0.0, 0.6), S.D),
    ((4.0, 0.0, 0.2), S.E),
    ((5.5, 0.0, 0.6), S.D),
    ((5.5, 0.0, 0.2), S.D),
]


@pytest.mark.parametrize(("inputs", "expected"), CELLS)
def test_every_table_cell(inputs: tuple[float, float, float], expected: S) -> None:
    """Each cell of the table maps to the documented class."""
    assert pasquill_class(*inputs) == expected


def test_overcast_is_neutral_day_and_night() -> None:
    """Overcast (>= 7/8 cloud) is class D regardless of sun and wind."""
    assert pasquill_class(1.0, 900.0, 0.9) == S.D
    assert pasquill_class(1.0, 0.0, 0.9) == S.D


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ((2.0, 700.0, 0.1), S.B),  # u = 2 belongs to the 2-<3 bin
        ((3.0, 700.0, 0.1), S.B),  # u = 3 belongs to the 3-<5 bin
        ((4.0, 600.0, 0.1), S.C),  # 600 W/m2 is moderate, not strong
        ((4.0, 300.0, 0.1), S.C),  # 300 W/m2 is moderate
        ((4.0, 10.0, 0.2), S.E),  # 10 W/m2 is night
        ((4.0, 0.0, 0.5), S.D),  # cloud 0.5 counts as cloudy at night
    ],
)
def test_bin_boundaries(inputs: tuple[float, float, float], expected: S) -> None:
    """Boundary values fall into the documented bins."""
    assert pasquill_class(*inputs) == expected
