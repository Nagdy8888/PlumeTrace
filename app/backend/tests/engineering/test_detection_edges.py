"""Edge cases of CUSUM detection: short or empty input, bad shapes, NaN, bearings, ordering."""

import numpy as np
import pytest

from plumetrace.engineering.detection import DetectionConfig, detect_events
from plumetrace.engineering.geometry import Point3, Sensor

CENTER = (100.0, 75.0)
NORTH = Sensor(id="N", position=Point3(100.0, 175.0, 3.0), noise_ppm=0.05)
SENSORS = [
    Sensor(id="B", position=Point3(150.0, 75.0, 3.0), noise_ppm=0.05),
    Sensor(id="A", position=Point3(50.0, 75.0, 3.0), noise_ppm=0.05),
]


def _means(n_windows: int, n_sensors: int = 2, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return 1.95 + rng.normal(0.0, 0.05, (n_windows, n_sensors))


def _detect(means: np.ndarray, sensors: list[Sensor], wind_from: float = 250.0, **kw: float):
    n = means.shape[0]
    config = DetectionConfig(**kw)
    return detect_events(
        np.arange(n) * 600.0, means, sensors, CENTER, np.full(n, wind_from), config
    )


@pytest.mark.parametrize("n_windows", [0, 1, 12])
def test_series_not_longer_than_the_baseline_gives_no_events(n_windows: int) -> None:
    """With no more than baseline_windows windows there is no baseline: empty list."""
    means = _means(n_windows)
    means[-1:, :] += 50.0
    assert _detect(means, SENSORS) == []


def test_all_nan_column_gives_no_events_and_no_error() -> None:
    """A dead sensor (all NaN) is skipped without error."""
    means = _means(100)
    means[:, 0] = np.nan
    assert _detect(means, SENSORS) == []


def test_step_after_a_nan_gap_is_still_detected() -> None:
    """NaN windows leave the CUSUM unchanged, so a step after a gap is caught."""
    means = _means(100)
    means[40:50, 1] = np.nan
    means[60:, 1] += 3.0
    events = _detect(means, SENSORS)
    assert [e.sensor_id for e in events] == ["A"]
    assert 60 <= events[0].window_index <= 62


def test_events_sorted_by_window_then_sensor_id() -> None:
    """Two sensors alarming in the same window come out ordered by sensor id."""
    means = _means(100)
    means[60:, :] += 3.0
    events = _detect(means, SENSORS)
    keys = [(e.window_index, e.sensor_id) for e in events]
    assert keys == sorted(keys)
    assert keys[0][1] == "A"
    assert keys[1] == (keys[0][0], "B")


def test_refractory_window_suppresses_a_repeat() -> None:
    """A huge persistent step alarms once, then is held for refractory_windows."""
    means = _means(100)
    means[60:, 0] += 100.0
    events = [e for e in _detect(means, SENSORS) if e.sensor_id == "B"]
    assert events[0].window_index == 60
    assert all(
        b.window_index - a.window_index >= 7 for a, b in zip(events, events[1:], strict=False)
    )


@pytest.mark.parametrize(("wind_from", "expected"), [(240.0, True), (241.0, False), (119.0, False)])
def test_downwind_sector_edge_is_inclusive(wind_from: float, expected: bool) -> None:
    """Sensor due north (bearing 0): downwind direction 60 deg is exactly on the 60 deg edge."""
    means = _means(60, 1)
    means[40:, 0] += 5.0
    (event,) = _detect(means, [NORTH], wind_from)
    assert event.downwind_of_site is expected


def test_downwind_wraps_around_north() -> None:
    """Wind from 180 deg blows towards 0 deg: a sensor due north is downwind (diff 0)."""
    means = _means(60, 1)
    means[40:, 0] += 5.0
    (event,) = _detect(means, [NORTH], 180.0)
    assert event.downwind_of_site is True


def test_nan_wind_or_sensor_at_centre_is_not_downwind() -> None:
    """A bearing that cannot be defined gives False, not an error."""
    means = _means(60, 1)
    means[40:, 0] += 5.0
    (event,) = _detect(means, [NORTH], float("nan"))
    assert event.downwind_of_site is False
    at_centre = Sensor(id="C", position=Point3(CENTER[0], CENTER[1], 3.0), noise_ppm=0.05)
    (event,) = _detect(means, [at_centre], 250.0)
    assert event.downwind_of_site is False


def test_flat_history_uses_the_sigma_floor() -> None:
    """A perfectly constant background has MAD 0; sigma_floor_ppm keeps the CUSUM finite."""
    means = np.full((40, 1), 2.0)
    means[30:, 0] = 3.0
    (event,) = _detect(means, [NORTH])
    assert event.window_index == 30
    assert np.isfinite(event.cusum)


def test_shape_mismatches_are_value_errors() -> None:
    """Columns vs sensors, and window arrays vs rows, raise ValueError."""
    means = _means(30)
    with pytest.raises(ValueError, match="sensors"):
        detect_events(np.arange(30) * 600.0, means, SENSORS[:1], CENTER, np.zeros(30))
    with pytest.raises(ValueError, match="one entry per window"):
        detect_events(np.arange(29) * 600.0, means, SENSORS, CENTER, np.zeros(30))
    with pytest.raises(ValueError, match="one entry per window"):
        detect_events(np.arange(30) * 600.0, means, SENSORS, CENTER, np.zeros(31))
    with pytest.raises(ValueError, match="sensors"):
        detect_events(np.arange(30) * 600.0, means[:, 0], SENSORS, CENTER, np.zeros(30))


@pytest.mark.parametrize(
    ("kw", "match"),
    [({"baseline_windows": 0}, "baseline_windows"), ({"sigma_floor_ppm": 0.0}, "sigma_floor")],
)
def test_bad_config_is_value_error(kw: dict[str, float], match: str) -> None:
    """A zero baseline or non-positive sigma floor is rejected."""
    with pytest.raises(ValueError, match=match):
        _detect(_means(30), SENSORS, **kw)
