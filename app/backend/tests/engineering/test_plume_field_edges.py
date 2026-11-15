"""Edge-case tests of the plume grid and its byte codec (Task 7 own behaviour)."""

import math

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.plume_field import (
    DECADES,
    PPM_MIN,
    GridSpec,
    decode_log_u8,
    encode_log_u8,
    ground_grid_ppm,
)
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource
from plumetrace.engineering.units import kg_h_to_kg_s

POS = Point3(85.0, 115.0, 12.0)
SRC = TrueSource(POS, 15.0, 0.0, 1e9)
DEFAULT_GRID = GridSpec()
WIND = (4.0, 250.0, StabilityClass.D, CoefficientSet.PG_MARTIN, 300.0, 98900.0)


def _grid(
    sources: list[TrueSource], t_s: float = 10.0, grid: GridSpec = DEFAULT_GRID
) -> np.ndarray:
    """Ground grid for the fixed wind above."""
    return ground_grid_ppm(sources, t_s, *WIND, grid=grid)


def test_constants_match_the_plan() -> None:
    """The encoding range is 0.1 to 1000 ppm, four decades."""
    assert PPM_MIN == 0.1 and DECADES == 4.0
    g = GridSpec()
    assert (g.x0_m, g.y0_m, g.dx_m, g.dy_m, g.nx, g.ny, g.z_m) == (0, 0, 5, 5, 40, 30, 1.5)


@pytest.mark.parametrize(
    "bad",
    [
        {"nx": 0},
        {"ny": -1},
        {"dx_m": 0.0},
        {"dy_m": -5.0},
        {"dx_m": math.nan},
        {"x0_m": math.inf},
        {"z_m": math.nan},
        {"z_m": -1.0},
    ],
)
def test_grid_spec_rejects_bad_values(bad: dict[str, float]) -> None:
    """A grid needs positive sizes and finite coordinates."""
    with pytest.raises(ValueError, match="GridSpec"):
        GridSpec(**bad)


def test_cell_centres_are_half_a_cell_in() -> None:
    """Cell (j, i) holds the concentration at (x0 + (i + 0.5) dx, y0 + (j + 0.5) dy, z)."""
    grid = GridSpec(x0_m=10.0, y0_m=20.0, dx_m=7.0, dy_m=3.0, nx=6, ny=4, z_m=2.0)
    g = _grid([SRC], grid=grid)
    assert g.shape == (4, 6)
    i, j = 5, 1
    receptor = np.array([[10.0 + 5.5 * 7.0, 20.0 + 1.5 * 3.0, 2.0]])
    want = concentration_ppm(kg_h_to_kg_s(15.0), *WIND[:2], POS, receptor, *WIND[2:])
    assert g[j, i] == pytest.approx(float(want[0]), rel=1e-12)


def test_grid_is_linear_in_rate_and_additive_over_sources() -> None:
    """Doubling the rate doubles the grid; two sources add."""
    other = TrueSource(Point3(60.0, 80.0, 1.5), 5.0, 0.0, 1e9)
    double = TrueSource(POS, 30.0, 0.0, 1e9)
    np.testing.assert_allclose(_grid([double]), 2.0 * _grid([SRC]), rtol=1e-12, atol=1e-290)
    np.testing.assert_allclose(
        _grid([SRC, other]), _grid([SRC]) + _grid([other]), rtol=1e-12, atol=1e-290
    )


def test_source_end_is_exclusive_and_no_sources_is_zero() -> None:
    """A source is active for start_s <= t < end_s; an empty list gives zeros."""
    ending = TrueSource(POS, 15.0, 0.0, 10.0)
    assert _grid([ending], t_s=9.999).max() > 0.0
    assert _grid([ending], t_s=10.0).max() == 0.0
    assert _grid([]).max() == 0.0


def test_grid_is_deterministic_and_finite() -> None:
    """The same inputs give the same bytes, and no cell is NaN or infinite."""
    a, b = _grid([SRC]), _grid([SRC])
    assert a.tobytes() == b.tobytes()
    assert np.isfinite(a).all() and (a >= 0.0).all()


@pytest.mark.parametrize("t_s", [math.nan, math.inf])
def test_non_finite_time_is_rejected(t_s: float) -> None:
    """A time that is not finite cannot decide which sources are active."""
    with pytest.raises(ValueError, match="t_s"):
        _grid([SRC], t_s=t_s)


@pytest.mark.parametrize("speed", [0.0, -1.0, math.nan])
def test_bad_wind_speed_is_rejected_even_without_active_sources(speed: float) -> None:
    """The wind must be positive and finite whether or not a source is active."""
    with pytest.raises(ValueError, match="wind_speed_m_s"):
        ground_grid_ppm([], 0.0, speed, 250.0, *WIND[2:])


def test_encode_range_ends_and_clamps() -> None:
    """0.1 ppm is byte 1, 1000 ppm is 255, more is clamped, less than 0.1 or negative is 0."""
    ppm = np.array([[0.1, 1000.0, 1e7, 0.0999999, -5.0, 1.0]])
    assert list(encode_log_u8(ppm)) == [1, 255, 255, 0, 0, 64]


def test_encode_is_row_major_and_accepts_views() -> None:
    """Rows (y) are written one after another; a transposed view encodes by its logical order."""
    ppm = np.array([[0.0, 1000.0], [0.1, 10.0]])
    assert list(encode_log_u8(ppm)) == [0, 255, 1, 128]
    assert encode_log_u8(ppm.T) == bytes([0, 1, 255, 128])
    assert isinstance(encode_log_u8(ppm), bytes)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_encode_rejects_non_finite(bad: float) -> None:
    """NaN and infinity have no byte: encoding them is an error, not a silent zero."""
    with pytest.raises(ValueError, match="finite"):
        encode_log_u8(np.array([[1.0, bad]]))


def test_every_byte_round_trips_exactly() -> None:
    """Decoding then encoding any byte gives the same byte (the code is a bijection on 1..255)."""
    data = bytes(range(256))
    out = decode_log_u8(data, 16, 16)
    assert encode_log_u8(out) == data
    assert out[0, 0] == 0.0 and out[0, 1] == PPM_MIN
    assert out[15, 15] == pytest.approx(1000.0, rel=1e-12)
    assert (np.diff(out.ravel()) > 0).all()


@pytest.mark.parametrize(("ny", "nx"), [(0, 4), (4, 0), (-1, 4), (2, 5), (3, 3)])
def test_decode_rejects_wrong_shape(ny: int, nx: int) -> None:
    """The shape must be positive and match the data length (8 bytes here)."""
    with pytest.raises(ValueError, match="decode_log_u8"):
        decode_log_u8(bytes(8), ny, nx)
