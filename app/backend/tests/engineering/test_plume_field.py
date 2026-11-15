"""Tests for the ground concentration grid and its byte encoding."""

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.plume_field import (
    GridSpec,
    decode_log_u8,
    encode_log_u8,
    ground_grid_ppm,
)
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource

SRC = TrueSource(Point3(85.0, 115.0, 12.0), 15.0, 0.0, 1e9)


def test_grid_shape_and_downwind_mass() -> None:
    """The 40 x 30 grid has signal downwind (wind from 250 -> east-north-east) and none upwind."""
    g = ground_grid_ppm(
        [SRC], 10.0, 4.0, 250.0, StabilityClass.D, CoefficientSet.PG_MARTIN, 300.0, 98900.0
    )
    assert g.shape == (30, 40)
    assert g[:, 30:].max() > 0.0
    assert g[:, :10].max() == 0.0


def test_inactive_source_gives_empty_grid() -> None:
    """Before the source starts the grid is all zero."""
    late = TrueSource(Point3(85.0, 115.0, 12.0), 15.0, 100.0, 1e9)
    assert (
        ground_grid_ppm(
            [late], 10.0, 4.0, 250.0, StabilityClass.D, CoefficientSet.PG_MARTIN, 300.0, 98900.0
        ).max()
        == 0.0
    )


def test_log_u8_round_trip() -> None:
    """Values round-trip within one quantisation step (4 decades / 254 steps = 3.7 %)."""
    ppm = np.array([[0.0, 0.05, 0.1, 1.0], [10.0, 123.0, 999.0, 5000.0]])
    out = decode_log_u8(encode_log_u8(ppm), 2, 4)
    assert out[0, 0] == 0.0 and out[0, 1] == 0.0
    for v, d in [(0.1, out[0, 2]), (1.0, out[0, 3]), (10.0, out[1, 0]), (123.0, out[1, 1])]:
        assert d == pytest.approx(v, rel=0.04)
    assert out[1, 3] == pytest.approx(1000.0, rel=0.04)
    assert len(encode_log_u8(np.zeros(GridSpec().ny * GridSpec().nx).reshape(30, 40))) == 1200
