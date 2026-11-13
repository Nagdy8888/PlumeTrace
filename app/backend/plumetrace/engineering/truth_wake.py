"""Building wakes for the truth model: the obstacle type and the receptor-in-wake rule.

Pure geometry, no I/O. ``WakeObstacle`` is also importable from ``truth_model``.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.plume import downwind_crosswind_m

# Task 12 value: the wake reaches this many obstacle heights downwind of the obstacle centre.
WAKE_LENGTH_HEIGHTS: Final = 3.0


@dataclass(frozen=True)
class WakeObstacle:
    """A building or shelter that dilutes the plume in its wake.

    Attributes:
        center_xy: Obstacle centre (x, y) in metres.
        half_width_m: Half the crosswind extent in metres (> 0).
        height_m: Height in metres (> 0); the wake reaches three heights downwind.
    """

    center_xy: tuple[float, float]
    half_width_m: float
    height_m: float

    def __post_init__(self) -> None:
        """Reject a non-finite centre or a size that is not positive.

        Raises:
            ValueError: If the centre or a size is not finite, or the half width or the height
                is not above zero.
        """
        values = (*self.center_xy, self.half_width_m, self.height_m)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("WakeObstacle values must be finite")
        if self.half_width_m <= 0.0 or self.height_m <= 0.0:
            raise ValueError("half_width_m and height_m must be > 0")


def wake_mask(
    obstacles: Sequence[WakeObstacle], receptors_xy: npt.NDArray[np.float64], from_deg: float
) -> npt.NDArray[np.bool_]:
    """Which receptors are in the wake of any obstacle for this wind direction.

    A receptor is in a wake when ``0 < along <= 3 * height_m`` and ``|cross| <= half_width_m``,
    measured from the obstacle centre in the wind frame (``downwind_crosswind_m``).

    Args:
        obstacles: The obstacles to test.
        receptors_xy: Receptor positions, shape ``(N, 2)``, columns x and y in m.
        from_deg: Direction the wind blows from, degrees clockwise from north.

    Returns:
        Boolean array of shape ``(N,)``, true where the receptor is in at least one wake.
    """
    mask = np.zeros(len(receptors_xy), dtype=np.bool_)
    for obstacle in obstacles:
        centre = Point3(obstacle.center_xy[0], obstacle.center_xy[1], 0.0)
        along, cross = downwind_crosswind_m(centre, receptors_xy, from_deg)
        in_wake = (along > 0.0) & (along <= WAKE_LENGTH_HEIGHTS * obstacle.height_m)
        mask |= in_wake & (np.abs(cross) <= obstacle.half_width_m)
    return mask
