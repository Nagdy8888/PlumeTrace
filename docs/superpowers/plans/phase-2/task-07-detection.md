# Phase 2 · Task 7 — Event detection (rolling baseline + CUSUM)

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

The algorithm and the test thresholds below were validated by the planner with a prototype
(0 false alarms over 20 seeds × 2 days × 8 sensors; step caught at window 100; drift caught at window 63).

## Files
Create `app/backend/plumetrace/engineering/detection.py`, `app/backend/tests/engineering/test_detection.py`.

## Interface
```python
@dataclass(frozen=True)
class DetectionConfig:
    baseline_windows: int = 12
    k_sigma: float = 0.5
    h_sigma: float = 5.0
    sigma_floor_ppm: float = 0.1
    refractory_windows: int = 6
    downwind_half_angle_deg: float = 60.0

class DetectionEvent(BaseModel):  # frozen
    sensor_id: str
    window_index: int
    window_start_s: float
    mean_ppm: float
    baseline_ppm: float
    cusum: float
    downwind_of_site: bool

def detect_events(
    window_start_s: npt.NDArray[np.float64],   # (W,)
    means_ppm: npt.NDArray[np.float64],        # (W, S), absolute ppm, NaN allowed
    sensors: list[Sensor],                     # length S, same order as columns
    site_center_xy: tuple[float, float],
    wind_from_deg: npt.NDArray[np.float64],    # (W,)
    config: DetectionConfig = DetectionConfig(),
) -> list[DetectionEvent]:                     # sorted by (window_index, sensor_id)
```

Algorithm, per sensor column (write it in a helper `_cusum_column(...)`, ≤ 50 lines):
```text
S = 0.0; suppressed_until = -1
for t in range(baseline_windows, W):
    if t <= suppressed_until: S = 0.0; continue          # refractory: hold at zero
    x = means[t]; if isnan(x): continue                 # NaN leaves S unchanged
    hist = non-NaN values of means[t-baseline_windows : t]; if empty: continue
    baseline = median(hist)
    sigma = max(1.4826 * median(|hist - baseline|), sigma_floor_ppm)
    S = max(0.0, S + (x - baseline) / sigma - k_sigma)
    if S > h_sigma:
        emit event(t, x, baseline, S); S = 0.0; suppressed_until = t + refractory_windows
```
`downwind_of_site` for an event in window t: bearing from `site_center_xy` to the sensor,
`degrees(atan2(dx, dy)) mod 360`, is within `downwind_half_angle_deg` (inclusive) of
`(wind_from_deg[t] + 180) mod 360`, using the smallest angular difference.

## Tests (full code) — `app/backend/tests/engineering/test_detection.py`
```python
"""Tests for CUSUM event detection on 10-minute window means (KS-07 sensors)."""

import numpy as np

from plumetrace.engineering.detection import detect_events
from plumetrace.facility.candidates import methane_sensors
from plumetrace.facility.loader import load_facility

SENSORS = methane_sensors(load_facility())  # AT-101 .. AT-108, columns 0..7
CENTER = (100.0, 75.0)
W = 288  # two days of 10-minute windows


def _noise(seed: int = 7) -> np.ndarray:
    return 1.95 + np.random.default_rng(seed).normal(0.0, 0.05, (W, len(SENSORS)))


def _run(means: np.ndarray, wind_from: float = 250.0) -> list:
    return detect_events(np.arange(W) * 600.0, means, SENSORS, CENTER, np.full(W, wind_from))


def test_no_false_alarms_on_pure_noise() -> None:
    """Two days of background noise produce no events."""
    assert _run(_noise()) == []


def test_step_is_detected_once_and_promptly() -> None:
    """A +2 ppm step on AT-104 from window 100 gives exactly one event, within 2 windows."""
    means = _noise()
    means[100:, 3] += 2.0
    events = _run(means)
    assert [e.sensor_id for e in events] == ["AT-104"]
    assert 100 <= events[0].window_index <= 102
    assert events[0].window_start_s == events[0].window_index * 600.0
    assert events[0].mean_ppm > events[0].baseline_ppm + 1.5


def test_slow_drift_is_detected() -> None:
    """A +0.02 ppm/window drift on AT-106 from window 50 is flagged by window 80."""
    means = _noise()
    means[50:, 5] += 0.02 * np.arange(W - 50)
    first = [e for e in _run(means) if e.sensor_id == "AT-106"][0]
    assert first.window_index <= 80


def test_missing_windows_are_ignored() -> None:
    """30 % NaN windows on one sensor raise no error and no event."""
    means = _noise()
    rng = np.random.default_rng(11)
    means[rng.random(W) < 0.3, 2] = np.nan
    assert _run(means) == []


def test_downwind_flag() -> None:
    """With wind from 250 deg, AT-104 (east) is downwind; AT-107 (north-west) is not."""
    means = _noise()
    means[100:, 3] += 2.0  # AT-104
    means[150:, 6] += 2.0  # AT-107
    flags = {e.sensor_id: e.downwind_of_site for e in _run(means)}
    assert flags == {"AT-104": True, "AT-107": False}
```

## Steps
- [ ] Test → FAIL → implement → full checks green.
- [ ] **Docs.** ENGINEERING.md → "Event detection": algorithm, parameters with their meaning and default values, why CUSUM (catches steps and slow drifts), the measured false-alarm behaviour, what it does not decide (leak vs fault is triage's job). Work-log; `STATUS.md` (last 2.7, next 2.8).
- [ ] **Commit** `feat(engineering): add CUSUM event detection`.
