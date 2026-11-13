# Phase 2 · Task 6 — Window averaging, wind statistics, calm detection

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

## Files
Create `app/backend/plumetrace/engineering/averaging.py`, `app/backend/tests/engineering/test_averaging.py`.

## Interface
- `WINDOW_S: Final = 600.0`; `CALM_WIND_M_S: Final = 1.0`; `MIN_COVERAGE: Final = 0.5`
- `def window_means(times_s: npt.NDArray[np.float64], values: npt.NDArray[np.float64], window_s: float = WINDOW_S) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]`
  - `times_s` shape `(T,)` ascending with a constant step `dt = times_s[1] − times_s[0]`; `values` shape `(T, S)`.
  - Window k covers `[t0 + k·window_s, t0 + (k+1)·window_s)` where `t0 = times_s[0]`. Only complete windows are returned (a trailing partial window is dropped).
  - Per window and sensor: mean of non-NaN samples; if non-NaN samples `< MIN_COVERAGE × (window_s / dt)`, the result is `NaN`.
  - Returns `(window_start_s (W,), means (W, S))`.
- `def circular_mean_deg(directions_deg: npt.NDArray[np.float64]) -> float` — vector mean of unit vectors, result normalised to `[0, 360)`; values within `1e-9` of 360 return `0.0`.
- `def window_wind(times_s, speed_m_s, from_deg, window_s: float = WINDOW_S) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]` — per complete window: arithmetic mean speed and `circular_mean_deg` of directions; returns `(mean_speed (W,), mean_from_deg (W,))`.
- `def is_calm(speed_m_s: float) -> bool` — `speed_m_s < CALM_WIND_M_S`.

## Tests (full code) — `app/backend/tests/engineering/test_averaging.py`
```python
"""Tests for window averaging and wind statistics."""

import numpy as np
import pytest

from plumetrace.engineering.averaging import circular_mean_deg, is_calm, window_means, window_wind


def test_two_complete_windows_and_partial_dropped() -> None:
    """25 min of 10 s samples -> 2 complete 10-min windows; the 5-min tail is dropped."""
    t = np.arange(0.0, 1500.0, 10.0)
    v = np.column_stack([np.where(t < 600.0, 1.0, 3.0), np.full(t.shape, 2.0)])
    starts, means = window_means(t, v)
    assert starts.tolist() == [0.0, 600.0]
    assert means.shape == (2, 2)
    assert means[:, 0].tolist() == [1.0, 3.0]
    assert means[:, 1].tolist() == [2.0, 2.0]


def test_low_coverage_window_is_nan() -> None:
    """A sensor with 70 % NaN samples in a window gives NaN for that window."""
    t = np.arange(0.0, 600.0, 10.0)
    v = np.ones((60, 1))
    v[:42, 0] = np.nan
    _, means = window_means(t, v)
    assert np.isnan(means[0, 0])


def test_half_coverage_window_is_kept() -> None:
    """Exactly 50 % valid samples is enough."""
    t = np.arange(0.0, 600.0, 10.0)
    v = np.ones((60, 1))
    v[:30, 0] = np.nan
    _, means = window_means(t, v)
    assert means[0, 0] == 1.0


def test_circular_mean_wraps_around_north() -> None:
    """359 and 1 degrees average to 0, not 180."""
    assert circular_mean_deg(np.array([359.0, 1.0])) == pytest.approx(0.0, abs=1e-9)
    assert circular_mean_deg(np.array([350.0, 20.0])) == pytest.approx(5.0, abs=1e-9)
    assert circular_mean_deg(np.array([90.0, 90.0, 270.0])) == pytest.approx(90.0, abs=1e-9)


def test_window_wind() -> None:
    """Mean speed is arithmetic; mean direction is circular."""
    t = np.arange(0.0, 600.0, 10.0)
    speed = np.where(np.arange(60) % 2 == 0, 3.0, 5.0)
    direction = np.where(np.arange(60) % 2 == 0, 355.0, 5.0)
    s, d = window_wind(t, speed, direction)
    assert s.tolist() == [4.0]
    assert d[0] == pytest.approx(0.0, abs=1e-9)


def test_calm_threshold() -> None:
    """Below 1 m/s is calm; 1 m/s is not."""
    assert is_calm(0.99) is True
    assert is_calm(1.0) is False
```

## Steps
- [ ] Test → FAIL → implement → full checks green.
- [ ] **Docs.** ENGINEERING.md → "Averaging": why sensor data is averaged (the plume model predicts ~10-min means), window rule, coverage rule, circular mean, calm threshold. Work-log; `STATUS.md` (last 2.6, next 2.7).
- [ ] **Commit** `feat(engineering): add window averaging and wind statistics`.
