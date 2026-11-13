"""Tests for the truth model used by the simulator and the benchmark."""

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3, Sensor
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import (
    SensorFault,
    TrueSource,
    TruthConfig,
    WakeObstacle,
    simulate_sensors,
)
from plumetrace.engineering.truth_weather import HourlyWeather, synthetic_hourly_weather
from plumetrace.facility.loader import load_facility
from plumetrace.facility.obstacles import facility_obstacles

P = 98900.0
SENSOR = Sensor("S1", Point3(300.0, 0.0, 2.0), 0.3)
SOURCE = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 0.0, 1e9)  # 36 kg/h = 0.01 kg/s
OVERCAST_WEST = [
    HourlyWeather(
        hour_index=i,
        wind_speed_m_s=4.0,
        wind_from_deg=270.0,
        shortwave_w_m2=0.0,
        cloud_fraction=0.9,
        temp_k=290.0,
    )
    for i in range(2)
]
QUIET = dict(meander_sd_deg=0.0, speed_cv=0.0, wake_dilution=1.0, noise_ppm=0.0)


def _run(config: TruthConfig, sources: list[TrueSource] | None = None, seed: int = 0, **kw: object):
    return simulate_sensors(
        sources if sources is not None else [SOURCE],
        [SENSOR],
        OVERCAST_WEST,
        10.0,
        3600.0,
        np.random.default_rng(seed),
        P,
        config=config,
        **kw,
    )


def _expected_excess() -> float:
    rec = np.array([[300.0, 0.0, 2.0]])
    return float(
        concentration_ppm(
            0.01,
            4.0,
            270.0,
            SOURCE.position,
            rec,
            StabilityClass.D,
            CoefficientSet.BRIGGS_RURAL,
            290.0,
            P,
        )[0]
    )


def test_same_seed_same_series() -> None:
    """The truth model is deterministic for a given seed."""
    a = _run(TruthConfig(), seed=5)
    b = _run(TruthConfig(), seed=5)
    assert np.array_equal(a.ppm, b.ppm)
    assert a.times_s.shape == (360,)


def test_quiet_briggs_config_equals_the_plume_model() -> None:
    """With no randomness and the inversion's coefficients, truth = background + plume model."""
    s = _run(TruthConfig(coeff=CoefficientSet.BRIGGS_RURAL, **QUIET))
    assert np.allclose(s.ppm[:, 0], 1.95 + _expected_excess())
    assert set(s.stability) == {StabilityClass.D}


def test_truth_physics_differs_from_inversion_physics() -> None:
    """Martin coefficients alone change the 300 m centreline excess by more than 10 % (~24 %)."""
    s = _run(TruthConfig(coeff=CoefficientSet.PG_MARTIN, **QUIET))
    truth_excess = float(s.ppm[0, 0]) - 1.95
    assert abs(truth_excess - _expected_excess()) / _expected_excess() > 0.10


def test_background_and_noise_statistics() -> None:
    """No sources: mean 1.95 and standard deviation 0.3 ppm (360 samples)."""
    s = _run(TruthConfig(), sources=[], seed=0)
    assert float(s.ppm.mean()) == pytest.approx(1.95, abs=0.05)
    assert float(s.ppm.std()) == pytest.approx(0.3, abs=0.04)


def test_source_window_is_respected() -> None:
    """A source active only in the second half hour adds nothing before it starts."""
    late = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 1800.0, 1e9)
    s = _run(TruthConfig(coeff=CoefficientSet.BRIGGS_RURAL, **QUIET), sources=[late])
    assert np.allclose(s.ppm[s.times_s < 1800.0, 0], 1.95)
    assert np.all(s.ppm[s.times_s >= 1800.0, 0] > 1.95)


def test_drift_fault_adds_linear_offset() -> None:
    """1 ppm/h drift from t = 0 adds t/3600 ppm to that sensor only."""
    s = _run(TruthConfig(**QUIET), sources=[], faults=[SensorFault("S1", 1.0, 0.0)])
    assert np.allclose(s.ppm[:, 0], 1.95 + s.times_s / 3600.0)


def test_wake_dilutes_receptors_behind_an_obstacle() -> None:
    """A receptor 10 m behind a 10 m-high obstacle (inside 3 x height) is diluted by 0.6."""
    near = Sensor("S1", Point3(60.0, 0.0, 2.0), 0.3)
    obstacle = WakeObstacle((50.0, 0.0), 5.0, 10.0)
    base = TruthConfig(
        coeff=CoefficientSet.BRIGGS_RURAL,
        meander_sd_deg=0.0,
        speed_cv=0.0,
        noise_ppm=0.0,
        wake_dilution=0.6,
    )
    with_wake = simulate_sensors(
        [SOURCE],
        [near],
        OVERCAST_WEST,
        10.0,
        600.0,
        np.random.default_rng(0),
        P,
        obstacles=[obstacle],
        config=base,
    )
    without = simulate_sensors(
        [SOURCE], [near], OVERCAST_WEST, 10.0, 600.0, np.random.default_rng(0), P, config=base
    )
    assert np.allclose(with_wake.ppm - 1.95, 0.6 * (without.ppm - 1.95))


def test_facility_obstacles() -> None:
    """KS-07 has two buildings and three compressor shelters."""
    obstacles = facility_obstacles(load_facility())
    assert len(obstacles) == 5
    # Spec order: K-201..K-203 shelters (height 6.0, half width 6.0) come before CR-901, MCC-902.
    assert obstacles[0].height_m == 6.0 and obstacles[0].half_width_m == 6.0
    assert obstacles[-1].height_m == 4.0


def test_synthetic_weather_ranges_and_determinism() -> None:
    """Speeds are clipped, nights have no sun, and the generator is deterministic."""
    a = synthetic_hourly_weather(48, 0, np.random.default_rng(3))
    b = synthetic_hourly_weather(48, 0, np.random.default_rng(3))
    assert a == b
    assert len(a) == 48
    assert all(0.3 <= w.wind_speed_m_s <= 15.0 for w in a)
    assert all(w.shortwave_w_m2 == 0.0 for w in a if (w.hour_index % 24) in (0, 1, 2, 3, 22, 23))
    assert all(0.0 <= w.wind_from_deg < 360.0 for w in a)
