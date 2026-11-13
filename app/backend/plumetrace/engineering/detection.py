"""Event detection on 10-minute window means: rolling robust baseline plus one-sided CUSUM.

A sensor event is a sustained rise above its own recent background. Pure numpy, no I/O. It does
not decide whether an event is a leak or a sensor fault; that is triage's job.
"""

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

from plumetrace.engineering.geometry import Sensor

# 1.4826 scales the median absolute deviation to a normal sigma.
_MAD_TO_SIGMA = 1.4826


@dataclass(frozen=True)
class DetectionConfig:
    """Tuning of the detector; defaults are the Phase 2 Task 7 values.

    Attributes:
        baseline_windows: Number of previous windows the rolling baseline uses.
        k_sigma: CUSUM allowance, in sigmas, subtracted every window.
        h_sigma: CUSUM decision threshold, in sigmas.
        sigma_floor_ppm: Lower bound of the robust sigma, in ppm.
        refractory_windows: Windows after an event during which the sensor is held at zero.
        downwind_half_angle_deg: Half width of the "downwind of the site" sector, in degrees.
    """

    baseline_windows: int = 12
    k_sigma: float = 0.5
    h_sigma: float = 5.0
    sigma_floor_ppm: float = 0.1
    refractory_windows: int = 6
    downwind_half_angle_deg: float = 60.0


class DetectionEvent(BaseModel):
    """One CUSUM alarm on one sensor.

    Attributes:
        sensor_id: Instrument tag.
        window_index: Index of the window in which the CUSUM crossed the threshold.
        window_start_s: Start time of that window in s.
        mean_ppm: Window mean in ppm.
        baseline_ppm: Rolling median baseline used for that window, in ppm.
        cusum: CUSUM value that crossed the threshold, in sigmas.
        downwind_of_site: Whether the sensor lies downwind of the site centre in that window.
    """

    model_config = ConfigDict(frozen=True)

    sensor_id: str
    window_index: int
    window_start_s: float
    mean_ppm: float
    baseline_ppm: float
    cusum: float
    downwind_of_site: bool


def _cusum_column(
    means_ppm: npt.NDArray[np.float64], config: DetectionConfig
) -> list[tuple[int, float, float, float]]:
    """Run the CUSUM over one sensor column.

    Args:
        means_ppm: Window means of one sensor, shape ``(W,)``, NaN allowed.
        config: Detector tuning.

    Returns:
        ``(window_index, mean_ppm, baseline_ppm, cusum)`` per alarm, in window order.
    """
    found: list[tuple[int, float, float, float]] = []
    s = 0.0
    suppressed_until = -1
    for t in range(config.baseline_windows, len(means_ppm)):
        if t <= suppressed_until:
            s = 0.0
            continue
        x = float(means_ppm[t])
        if math.isnan(x):
            continue
        hist = means_ppm[t - config.baseline_windows : t]
        hist = hist[~np.isnan(hist)]
        if hist.size == 0:
            continue
        baseline = float(np.median(hist))
        sigma = max(
            _MAD_TO_SIGMA * float(np.median(np.abs(hist - baseline))), config.sigma_floor_ppm
        )
        s = max(0.0, s + (x - baseline) / sigma - config.k_sigma)
        if s > config.h_sigma:
            found.append((t, x, baseline, s))
            s = 0.0
            suppressed_until = t + config.refractory_windows
    return found


def _is_downwind(
    sensor: Sensor, site_center_xy: tuple[float, float], wind_from_deg: float, half_angle_deg: float
) -> bool:
    """Whether the sensor lies within the downwind sector of the site centre.

    A NaN wind direction or a sensor exactly at the site centre has no bearing: returns False.
    """
    dx = sensor.position.x_m - site_center_xy[0]
    dy = sensor.position.y_m - site_center_xy[1]
    if math.isnan(wind_from_deg) or (dx == 0.0 and dy == 0.0):
        return False
    bearing_deg = math.degrees(math.atan2(dx, dy)) % 360.0
    diff = abs(bearing_deg - (wind_from_deg + 180.0) % 360.0) % 360.0
    return min(diff, 360.0 - diff) <= half_angle_deg


def _validate(
    window_start_s: npt.NDArray[np.float64],
    means_ppm: npt.NDArray[np.float64],
    sensors: list[Sensor],
    wind_from_deg: npt.NDArray[np.float64],
    config: DetectionConfig,
) -> None:
    """Check shapes and config.

    Raises:
        ValueError: If a shape does not match, ``baseline_windows`` is below 1, or
            ``sigma_floor_ppm`` is not positive.
    """
    if means_ppm.ndim != 2 or means_ppm.shape[1] != len(sensors):
        raise ValueError(f"means_ppm shape {means_ppm.shape} does not match {len(sensors)} sensors")
    if len(window_start_s) != means_ppm.shape[0] or len(wind_from_deg) != means_ppm.shape[0]:
        raise ValueError("window_start_s and wind_from_deg must have one entry per window")
    if config.baseline_windows < 1:
        raise ValueError("baseline_windows must be at least 1")
    if not config.sigma_floor_ppm > 0.0:
        raise ValueError("sigma_floor_ppm must be positive")


def detect_events(
    window_start_s: npt.NDArray[np.float64],
    means_ppm: npt.NDArray[np.float64],
    sensors: list[Sensor],
    site_center_xy: tuple[float, float],
    wind_from_deg: npt.NDArray[np.float64],
    config: DetectionConfig = DetectionConfig(),
) -> list[DetectionEvent]:
    """Find sustained rises above each sensor's rolling background.

    Per sensor the baseline is the median of the previous ``baseline_windows`` non-NaN windows and
    sigma is 1.4826 x their median absolute deviation (at least ``sigma_floor_ppm``). The CUSUM
    ``S = max(0, S + (x - baseline) / sigma - k_sigma)`` raises an event when it exceeds
    ``h_sigma``, then restarts from zero and the sensor is held for ``refractory_windows``. A NaN
    window leaves the CUSUM unchanged. Series with no more than ``baseline_windows`` windows give
    no events.

    Args:
        window_start_s: Window start times in s, shape ``(W,)``.
        means_ppm: Absolute window means in ppm, shape ``(W, S)``, NaN allowed.
        sensors: The S sensors, in column order.
        site_center_xy: Site centre ``(x_m, y_m)`` for the downwind test.
        wind_from_deg: Direction the wind blows from per window, shape ``(W,)``.
        config: Detector tuning.

    Returns:
        Events sorted by ``(window_index, sensor_id)``.

    Raises:
        ValueError: If shapes disagree, ``baseline_windows`` is below 1 or ``sigma_floor_ppm`` is
            not positive.
    """
    _validate(window_start_s, means_ppm, sensors, wind_from_deg, config)
    events = [
        DetectionEvent(
            sensor_id=sensor.id,
            window_index=t,
            window_start_s=float(window_start_s[t]),
            mean_ppm=x,
            baseline_ppm=baseline,
            cusum=s,
            downwind_of_site=_is_downwind(
                sensor, site_center_xy, float(wind_from_deg[t]), config.downwind_half_angle_deg
            ),
        )
        for column, sensor in enumerate(sensors)
        for t, x, baseline, s in _cusum_column(means_ppm[:, column], config)
    ]
    return sorted(events, key=lambda event: (event.window_index, event.sensor_id))
