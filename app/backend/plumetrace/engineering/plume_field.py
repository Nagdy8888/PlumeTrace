"""Ground-level methane grid and its one-byte logarithmic encoding.

The replay build draws the plume from key frames: a regular grid of concentrations above
background at a fixed height, summed over the sources active at that time. Pure numpy, no I/O.
Site coordinates are metres (x east, y north, z up). ``PPM_MIN`` and ``DECADES`` (0.1 to
1000 ppm) are Task 7 values, a display range chosen for the replay, not a published constant.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource
from plumetrace.engineering.units import kg_h_to_kg_s

PPM_MIN: Final = 0.1
DECADES: Final = 4.0
_LEVELS: Final = 254.0  # byte 1 is PPM_MIN and byte 255 is PPM_MIN * 10**DECADES


@dataclass(frozen=True)
class GridSpec:
    """A regular grid of cell centres at one height.

    Cell centres are at ``x0_m + (i + 0.5) * dx_m`` and ``y0_m + (j + 0.5) * dy_m``.

    Attributes:
        x0_m: West edge of the grid in m.
        y0_m: South edge of the grid in m.
        dx_m: Cell width in m (> 0).
        dy_m: Cell height in m (> 0).
        nx: Number of cells in x (>= 1).
        ny: Number of cells in y (>= 1).
        z_m: Height of the grid above ground in m (>= 0).
    """

    x0_m: float = 0.0
    y0_m: float = 0.0
    dx_m: float = 5.0
    dy_m: float = 5.0
    nx: int = 40
    ny: int = 30
    z_m: float = 1.5

    def __post_init__(self) -> None:
        """Reject non-finite coordinates, non-positive cell sizes or counts, or a negative height.

        Raises:
            ValueError: If a value is out of range; the message starts with ``GridSpec``.
        """
        floats = (self.x0_m, self.y0_m, self.dx_m, self.dy_m, self.z_m)
        if not all(math.isfinite(v) for v in floats):
            raise ValueError("GridSpec values must be finite")
        if self.dx_m <= 0.0 or self.dy_m <= 0.0 or self.nx < 1 or self.ny < 1 or self.z_m < 0.0:
            raise ValueError("GridSpec needs dx_m, dy_m > 0, nx, ny >= 1 and z_m >= 0")


def _cell_centres(grid: GridSpec) -> npt.NDArray[np.float64]:
    """Return the cell centres as receptors, shape ``(ny * nx, 3)``, in row-major order."""
    xs = grid.x0_m + (np.arange(grid.nx) + 0.5) * grid.dx_m
    ys = grid.y0_m + (np.arange(grid.ny) + 0.5) * grid.dy_m
    gx, gy = np.meshgrid(xs, ys)
    return np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, grid.z_m)])


def _check_time_and_wind(t_s: float, wind_speed_m_s: float) -> None:
    """Require a finite time and a finite, positive wind speed.

    Raises:
        ValueError: If not; the message names ``t_s`` or ``wind_speed_m_s``.
    """
    if not math.isfinite(t_s):
        raise ValueError("t_s must be finite")
    if not (math.isfinite(wind_speed_m_s) and wind_speed_m_s > 0.0):
        raise ValueError("wind_speed_m_s must be finite and > 0")


def ground_grid_ppm(
    sources: Sequence[TrueSource],
    t_s: float,
    wind_speed_m_s: float,
    wind_from_deg: float,
    stability: StabilityClass,
    coeff: CoefficientSet,
    temp_k: float,
    pressure_pa: float,
    grid: GridSpec = GridSpec(),
) -> npt.NDArray[np.float64]:
    """Concentration above background on the grid, summed over the sources active at ``t_s``.

    A source is active for ``start_s <= t_s < end_s``; there is no building wake.

    Args:
        sources: Emissions; only those active at ``t_s`` contribute.
        t_s: Time in scenario seconds (finite).
        wind_speed_m_s: Wind speed in m/s (finite, > 0).
        wind_from_deg: Direction the wind blows from, degrees clockwise from north.
        stability: Pasquill stability class.
        coeff: Dispersion coefficient set.
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        grid: The grid; defaults to 40 x 30 cells of 5 m (the 200 m x 150 m site).

    Returns:
        Concentrations in ppm, shape ``(ny, nx)``, south row and west column first.

    Raises:
        ValueError: If ``t_s`` is not finite or ``wind_speed_m_s`` is not finite and positive.
    """
    _check_time_and_wind(t_s, wind_speed_m_s)
    receptors = _cell_centres(grid)
    total = np.zeros(len(receptors), dtype=np.float64)
    for src in sources:
        if src.start_s <= t_s < src.end_s:
            total += concentration_ppm(
                kg_h_to_kg_s(src.rate_kg_h),
                wind_speed_m_s,
                wind_from_deg,
                src.position,
                receptors,
                stability,
                coeff,
                temp_k,
                pressure_pa,
            )
    return total.reshape(grid.ny, grid.nx)


def encode_log_u8(ppm: npt.NDArray[np.float64]) -> bytes:
    """Encode concentrations as one byte per cell on a logarithmic scale.

    Byte ``0`` is a cell below ``PPM_MIN``; otherwise the byte is
    ``clip(round(1 + 254 * log10(ppm / PPM_MIN) / DECADES), 1, 255)``, so 0.1 ppm is 1 and
    1000 ppm or more is 255. Cells are written row-major (``y`` then ``x``).

    Args:
        ppm: Concentrations in ppm, any shape; negative values count as below ``PPM_MIN``.

    Returns:
        One byte per cell.

    Raises:
        ValueError: If a value is NaN or infinite.
    """
    values = np.asarray(ppm, dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("ppm values must be finite")
    flat = values.ravel()
    positive = np.maximum(flat, PPM_MIN)
    level = np.rint(1.0 + _LEVELS * np.log10(positive / PPM_MIN) / DECADES)
    coded = np.where(flat < PPM_MIN, 0.0, np.clip(level, 1.0, 255.0))
    return coded.astype(np.uint8).tobytes()


def decode_log_u8(data: bytes, ny: int, nx: int) -> npt.NDArray[np.float64]:
    """Decode bytes made by ``encode_log_u8`` back to ppm.

    ``0`` gives 0.0 and byte ``b`` gives ``PPM_MIN * 10 ** ((b - 1) * DECADES / 254)``. A value
    inside the range comes back within half a step (a factor of 1.018) of the original.

    Args:
        data: One byte per cell, row-major.
        ny: Number of rows (>= 1).
        nx: Number of columns (>= 1).

    Returns:
        Concentrations in ppm, shape ``(ny, nx)``.

    Raises:
        ValueError: If ``ny`` or ``nx`` is below 1 or ``len(data)`` is not ``ny * nx``.
    """
    if ny < 1 or nx < 1 or len(data) != ny * nx:
        raise ValueError(f"decode_log_u8: {len(data)} bytes do not fill a {ny} x {nx} grid")
    b = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
    ppm = np.where(b == 0.0, 0.0, PPM_MIN * 10.0 ** ((b - 1.0) * DECADES / _LEVELS))
    return ppm.reshape(ny, nx)
