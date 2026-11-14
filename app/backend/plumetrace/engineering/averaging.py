"""Window averaging and wind statistics for sensor and weather series.

The plume model predicts roughly 10-minute mean concentrations, so raw samples are averaged into
complete windows before they are compared with it. Pure numpy, no I/O.
"""

import math
from collections import Counter
from collections.abc import Sequence
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.stability import StabilityClass

# 10-minute window, the 1 m/s calm limit and the 50 % coverage rule: Phase 2 Task 6 values.
WINDOW_S: Final[float] = 600.0
CALM_WIND_M_S: Final[float] = 1.0
MIN_COVERAGE: Final[float] = 0.5


def _samples_per_window(
    times_s: npt.NDArray[np.float64], window_s: float, *series: npt.NDArray[np.float64]
) -> int:
    """Number of samples in one window; checks the series against ``times_s``.

    Raises:
        ValueError: If there are fewer than two samples or a series length differs from
            ``len(times_s)``.
    """
    if len(times_s) < 2:
        raise ValueError("need at least two samples to find the time step")
    for item in series:
        if len(item) != len(times_s):
            raise ValueError(
                f"series length {len(item)} differs from times_s length {len(times_s)}"
            )
    return round(window_s / float(times_s[1] - times_s[0]))


def _window_starts_s(
    times_s: npt.NDArray[np.float64], window_s: float, n: int
) -> npt.NDArray[np.float64]:
    """Start time of each complete window."""
    count = len(times_s) // n
    return float(times_s[0]) + window_s * np.arange(count, dtype=np.float64)


def window_means(
    times_s: npt.NDArray[np.float64],
    values: npt.NDArray[np.float64],
    window_s: float = WINDOW_S,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Average ``values`` over consecutive complete windows, ignoring NaN samples.

    Window k covers ``[t0 + k*window_s, t0 + (k+1)*window_s)``; a trailing partial window is
    dropped. A sensor with fewer than ``MIN_COVERAGE`` of the expected samples in a window gets
    NaN for that window.

    Args:
        times_s: Sample times, shape ``(T,)``, ascending with a constant step, in s.
        values: Samples, shape ``(T, S)``.
        window_s: Window length in s.

    Returns:
        ``(window_start_s, means)`` with shapes ``(W,)`` and ``(W, S)``; ``W`` is 0 when the
        series is shorter than one window.

    Raises:
        ValueError: If ``times_s`` has fewer than two samples or ``len(values)`` differs from
            ``len(times_s)`` (longer or shorter, no truncation).
    """
    n = _samples_per_window(times_s, window_s, values)
    starts = _window_starts_s(times_s, window_s, n)
    count = len(starts)
    blocks = np.asarray(values, dtype=np.float64)[: count * n].reshape(count, n, values.shape[1])
    valid = ~np.isnan(blocks)
    n_valid = valid.sum(axis=1)
    total = np.where(valid, blocks, 0.0).sum(axis=1)
    means = np.where(n_valid < MIN_COVERAGE * n, np.nan, total / np.maximum(n_valid, 1))
    return starts, means


def circular_mean_deg(directions_deg: npt.NDArray[np.float64]) -> float:
    """Vector mean of compass directions, in ``[0, 360)`` degrees.

    Args:
        directions_deg: Directions in degrees.

    Returns:
        Mean direction; values within 1e-9 of 360 are returned as 0.0.

    Raises:
        ValueError: If ``directions_deg`` is empty.
    """
    if len(directions_deg) == 0:
        raise ValueError("directions_deg is empty")
    rad = np.radians(directions_deg)
    mean = math.degrees(math.atan2(float(np.sin(rad).sum()), float(np.cos(rad).sum()))) % 360.0
    return 0.0 if mean > 360.0 - 1e-9 else mean


def window_wind(
    times_s: npt.NDArray[np.float64],
    speed_m_s: npt.NDArray[np.float64],
    from_deg: npt.NDArray[np.float64],
    window_s: float = WINDOW_S,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Mean wind speed and circular mean wind direction per complete window.

    Args:
        times_s: Sample times, shape ``(T,)``, constant step, in s.
        speed_m_s: Wind speed, shape ``(T,)``, in m/s.
        from_deg: Direction the wind blows from, shape ``(T,)``, degrees.
        window_s: Window length in s.

    Returns:
        ``(mean_speed_m_s, mean_from_deg)``, each of shape ``(W,)`` (empty when the series is
        shorter than one window).

    Raises:
        ValueError: If ``times_s`` has fewer than two samples or ``speed_m_s`` or ``from_deg``
            has a different length from ``times_s``.
    """
    n = _samples_per_window(times_s, window_s, speed_m_s, from_deg)
    count = len(times_s) // n
    speed = np.asarray(speed_m_s, dtype=np.float64)[: count * n].reshape(count, n)
    direction = np.asarray(from_deg, dtype=np.float64)[: count * n].reshape(count, n)
    return speed.mean(axis=1), np.array([circular_mean_deg(row) for row in direction])


def window_direction_sd_deg(
    times_s: npt.NDArray[np.float64],
    from_deg: npt.NDArray[np.float64],
    window_s: float = WINDOW_S,
) -> npt.NDArray[np.float64]:
    """Circular standard deviation of the wind direction per complete window, in degrees.

    ``sd = degrees(sqrt(-2 ln R))`` with ``R`` the mean resultant length of the unit vectors of
    the directions in the window (``R = 1`` for a constant direction, so ``sd = 0``). ``R`` is
    computed as the mean of ``cos(direction - circular mean)``, which equals the vector length and
    is exactly 1 for identical directions; it is clipped to ``[0, 1]`` so rounding cannot give a
    NaN. The windows are the same as in ``window_wind``, with the same NaN rule: a window with a
    missing direction is NaN, so a window under ``MIN_COVERAGE`` valid samples is NaN too.

    Args:
        times_s: Sample times, shape ``(T,)``, constant step, in s.
        from_deg: Direction the wind blows from, shape ``(T,)``, degrees.
        window_s: Window length in s.

    Returns:
        Circular standard deviation per complete window, shape ``(W,)`` (empty when the series is
        shorter than one window). A window whose directions cancel exactly (``R = 0``) gives inf.

    Raises:
        ValueError: If ``times_s`` has fewer than two samples or ``from_deg`` has a different
            length from ``times_s``.
    """
    n = _samples_per_window(times_s, window_s, from_deg)
    count = len(times_s) // n
    rad = np.radians(np.asarray(from_deg, dtype=np.float64)[: count * n].reshape(count, n))
    mean = np.arctan2(np.sin(rad).sum(axis=1), np.cos(rad).sum(axis=1))
    resultant = np.clip(np.cos(rad - mean[:, None]).mean(axis=1), 0.0, 1.0)
    with np.errstate(divide="ignore"):
        sd: npt.NDArray[np.float64] = np.degrees(np.sqrt(-2.0 * np.log(resultant)))
    return sd


def window_mode_class(
    classes: Sequence[StabilityClass], steps_per_window: int, n_windows: int
) -> list[StabilityClass]:
    """Most frequent stability class in each window.

    Window k covers ``classes[k * steps_per_window : (k + 1) * steps_per_window]``.

    Args:
        classes: One class per time step.
        steps_per_window: Time steps in one window (> 0).
        n_windows: Number of windows to return.

    Returns:
        One class per window; ties go to the alphabetically first class.

    Raises:
        ValueError: If a requested window holds no steps (``steps_per_window`` below 1 or
            ``classes`` too short for ``n_windows``).
    """
    n = steps_per_window
    modes: list[StabilityClass] = []
    for k in range(n_windows):
        counts = Counter(classes[k * n : (k + 1) * n])
        if not counts:
            raise ValueError(f"window {k} holds no steps")
        modes.append(min(counts, key=lambda c: (-counts[c], c.value)))
    return modes


def is_calm(speed_m_s: float) -> bool:
    """Return True when the wind is below ``CALM_WIND_M_S``."""
    return speed_m_s < CALM_WIND_M_S
