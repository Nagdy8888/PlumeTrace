"""Sensor drift faults for the truth model.

Pure functions, no I/O. ``SensorFault`` is also importable from ``truth_model``.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.geometry import Sensor


@dataclass(frozen=True)
class SensorFault:
    """A linear drift on one sensor.

    Attributes:
        sensor_id: Id of the faulty sensor.
        drift_ppm_per_h: Drift rate in ppm per hour (may be negative).
        start_s: Time in seconds when the drift starts.
    """

    sensor_id: str
    drift_ppm_per_h: float
    start_s: float

    def __post_init__(self) -> None:
        """Reject a non-finite drift or start time.

        Raises:
            ValueError: If ``drift_ppm_per_h`` or ``start_s`` is not finite.
        """
        if not (math.isfinite(self.drift_ppm_per_h) and math.isfinite(self.start_s)):
            raise ValueError("SensorFault drift_ppm_per_h and start_s must be finite")


def apply_faults(
    ppm: npt.NDArray[np.float64],
    times_s: npt.NDArray[np.float64],
    sensors: Sequence[Sensor],
    faults: Sequence[SensorFault],
) -> None:
    """Add each fault's drift ``rate * max(0, t - start) / 3600`` to its sensor column.

    Args:
        ppm: Readings, shape ``(T, S)``, changed in place.
        times_s: Step times in seconds, shape ``(T,)``.
        sensors: The sensors, in column order.
        faults: Drift faults; several on one sensor add up.

    Raises:
        KeyError: If a fault names a sensor that is not in ``sensors``.
    """
    index = {s.id: j for j, s in enumerate(sensors)}
    for fault in faults:
        drift = fault.drift_ppm_per_h * (np.maximum(0.0, times_s - fault.start_s) / 3600.0)
        ppm[:, index[fault.sensor_id]] += drift
