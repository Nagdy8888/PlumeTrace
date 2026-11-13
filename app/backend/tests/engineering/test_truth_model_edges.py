"""Edge cases of the truth model set-up: validation, time axis, draw order and reproducibility."""

from typing import Any

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3, Sensor
from plumetrace.engineering.truth_model import (
    SensorFault,
    TrueSource,
    TruthConfig,
    TruthSeries,
    WakeObstacle,
    simulate_sensors,
)
from plumetrace.engineering.truth_weather import HourlyWeather

NAN = float("nan")
INF = float("inf")
P = 98900.0
S1 = Sensor("S1", Point3(300.0, 0.0, 2.0), 0.3)
S2 = Sensor("S2", Point3(200.0, 20.0, 2.0), 0.3)
SOURCE = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 0.0, 1e9)
WEATHER = [
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
QUIET = TruthConfig(meander_sd_deg=0.0, speed_cv=0.0, wake_dilution=1.0, noise_ppm=0.0)


def _sim(**kw: Any) -> TruthSeries:
    args: dict[str, Any] = dict(
        sources=[SOURCE],
        sensors=[S1],
        weather=WEATHER,
        dt_s=10.0,
        duration_s=100.0,
        rng=np.random.default_rng(0),
        pressure_pa=P,
    )
    args.update(kw)
    return simulate_sensors(**args)


@pytest.mark.parametrize(
    "duration, dt, steps",
    [(35.0, 10.0, 3), (10.0, 10.0, 1), (0.3, 0.1, 3), (3600.0, 10.0, 360), (3599.9, 10.0, 359)],
)
def test_step_count_is_floor_of_duration_over_dt(duration: float, dt: float, steps: int) -> None:
    """``floor(duration / dt)`` steps at times ``k * dt``; rounding must not lose a step."""
    s = _sim(duration_s=duration, dt_s=dt, config=QUIET)
    assert s.times_s.shape == (steps,)
    assert s.ppm.shape == (steps, 1)
    assert len(s.stability) == steps
    assert s.wind_speed_m_s.shape == s.wind_from_deg.shape == s.temp_k.shape == (steps,)
    assert np.allclose(s.times_s, np.arange(steps) * dt)


@pytest.mark.parametrize("dt", [0.0, -10.0, NAN, INF])
def test_bad_time_step_is_rejected(dt: float) -> None:
    """The step must be a positive finite number."""
    with pytest.raises(ValueError, match="dt_s"):
        _sim(dt_s=dt)


@pytest.mark.parametrize("duration", [0.0, -5.0, 9.99, NAN, INF])
def test_bad_duration_is_rejected(duration: float) -> None:
    """A duration shorter than one step (zero steps) or not finite is an error, not an empty run."""
    with pytest.raises(ValueError, match="duration_s"):
        _sim(duration_s=duration)


def test_too_many_steps_is_rejected() -> None:
    """A time axis of more than 200000 steps is refused before anything is allocated."""
    with pytest.raises(ValueError, match="200000"):
        _sim(duration_s=1e9, dt_s=1.0)
    assert _sim(duration_s=20.0, dt_s=1.0, config=QUIET).times_s.shape == (20,)


@pytest.mark.parametrize("pressure", [0.0, -1.0, NAN, INF])
def test_bad_pressure_is_rejected(pressure: float) -> None:
    """Pressure must be positive and finite."""
    with pytest.raises(ValueError, match="pressure_pa"):
        _sim(pressure_pa=pressure)


def test_empty_or_inconsistent_sensors_are_rejected() -> None:
    """No sensors, repeated ids and a fault on an unknown sensor all fail visibly."""
    with pytest.raises(ValueError, match="sensors must not be empty"):
        _sim(sensors=[])
    with pytest.raises(ValueError, match="unique"):
        _sim(sensors=[S1, Sensor("S1", Point3(5.0, 5.0, 2.0), 0.3)])
    with pytest.raises(ValueError, match="unknown sensor S9"):
        _sim(faults=[SensorFault("S9", 1.0, 0.0)])


def test_empty_weather_is_rejected() -> None:
    """The weather list must have at least one hour."""
    with pytest.raises(ValueError, match="weather"):
        _sim(weather=[])


@pytest.mark.parametrize(
    "kw",
    [
        dict(meander_sd_deg=-1.0),
        dict(meander_sd_deg=NAN),
        dict(meander_tau_s=0.0),
        dict(meander_tau_s=-5.0),
        dict(meander_tau_s=INF),
        dict(speed_cv=-0.1),
        dict(speed_cv=INF),
        dict(wake_dilution=-0.1),
        dict(wake_dilution=1.1),
        dict(wake_dilution=NAN),
        dict(noise_ppm=-0.1),
        dict(noise_ppm=NAN),
        dict(background_ppm=-1.0),
        dict(background_ppm=INF),
    ],
)
def test_truth_config_rejects_unphysical_values(kw: dict[str, float]) -> None:
    """The config fails at construction, so a bad value never reaches a series."""
    with pytest.raises(ValueError, match="TruthConfig"):
        TruthConfig(**kw)


def test_truth_config_defaults_are_the_plan_values() -> None:
    """Defaults: Martin coefficients, 10 deg meander over 120 s, CV 0.15, dilution 0.6."""
    c = TruthConfig()
    assert c.coeff is CoefficientSet.PG_MARTIN
    assert (c.meander_sd_deg, c.meander_tau_s, c.speed_cv) == (10.0, 120.0, 0.15)
    assert (c.wake_dilution, c.noise_ppm, c.background_ppm) == (0.6, 0.3, 1.95)
    assert TruthConfig(coeff=CoefficientSet.BRIGGS_RURAL).coeff is CoefficientSet.BRIGGS_RURAL


@pytest.mark.parametrize(
    "args",
    [
        (Point3(NAN, 0.0, 2.0), 1.0, 0.0, 10.0),
        (Point3(0.0, INF, 2.0), 1.0, 0.0, 10.0),
        (Point3(0.0, 0.0, 2.0), -1.0, 0.0, 10.0),
        (Point3(0.0, 0.0, 2.0), NAN, 0.0, 10.0),
        (Point3(0.0, 0.0, 2.0), INF, 0.0, 10.0),
        (Point3(0.0, 0.0, 2.0), 1.0, NAN, 10.0),
        (Point3(0.0, 0.0, 2.0), 1.0, 20.0, 10.0),
        (Point3(0.0, 0.0, 2.0), 1.0, 0.0, NAN),
    ],
)
def test_true_source_rejects_bad_values(args: tuple[Any, ...]) -> None:
    """Non-finite position or start, a negative or infinite rate and an inverted window fail."""
    with pytest.raises(ValueError, match="TrueSource|rate_kg_h|end_s"):
        TrueSource(*args)


def test_true_source_allows_open_ended_and_empty_windows() -> None:
    """An infinite end and a zero-length window are valid; a zero rate is valid."""
    assert TrueSource(Point3(0.0, 0.0, 2.0), 1.0, 0.0, INF).end_s == INF
    assert TrueSource(Point3(0.0, 0.0, 2.0), 0.0, 5.0, 5.0).rate_kg_h == 0.0


@pytest.mark.parametrize(
    "args",
    [
        ((NAN, 0.0), 5.0, 10.0),
        ((0.0, 0.0), 0.0, 10.0),
        ((0.0, 0.0), 5.0, 0.0),
        ((0.0, 0.0), -5.0, 10.0),
        ((0.0, 0.0), 5.0, INF),
        ((0.0, 0.0), INF, 10.0),
    ],
)
def test_wake_obstacle_rejects_bad_values(args: tuple[Any, ...]) -> None:
    """A wake needs a finite centre and a positive finite size."""
    with pytest.raises(ValueError, match="WakeObstacle|> 0"):
        WakeObstacle(*args)


@pytest.mark.parametrize("args", [("S1", NAN, 0.0), ("S1", INF, 0.0), ("S1", 1.0, NAN)])
def test_sensor_fault_rejects_non_finite_values(args: tuple[Any, ...]) -> None:
    """Drift and start must be finite numbers."""
    with pytest.raises(ValueError, match="SensorFault"):
        SensorFault(*args)


@pytest.mark.filterwarnings("ignore:overflow encountered")
def test_summed_faults_that_overflow_fail_visibly() -> None:
    """Never return inf: two near-maximal drifts on one sensor overflow and raise."""
    big = SensorFault("S1", 1.7e308, 0.0)
    with pytest.raises(ValueError, match="not finite"):
        _sim(sources=[], faults=[big, big], duration_s=7200.0, dt_s=3600.0, config=QUIET)


def test_noise_only_series_matches_the_documented_draw_order() -> None:
    """Per step the draws are meander, gust, then one value per sensor, in sensor order."""
    cfg = TruthConfig(meander_sd_deg=0.0, speed_cv=0.0, noise_ppm=0.5, background_ppm=2.0)
    s = _sim(
        sources=[], sensors=[S1, S2], duration_s=200.0, config=cfg, rng=np.random.default_rng(9)
    )
    ref = np.random.default_rng(9)
    expected = np.empty((20, 2))
    for k in range(20):
        ref.standard_normal()  # meander
        ref.standard_normal()  # gust
        expected[k] = [ref.standard_normal(), ref.standard_normal()]
    assert np.allclose(s.ppm, 2.0 + 0.5 * expected)


@pytest.mark.parametrize("noise", [0.0, 0.3])
def test_generator_advances_by_two_plus_s_draws_per_step(noise: float) -> None:
    """Even with noise_ppm = 0 the same number of draws is consumed, so sequences stay aligned."""
    rng = np.random.default_rng(3)
    _sim(sensors=[S1, S2], duration_s=100.0, rng=rng, config=TruthConfig(noise_ppm=noise))
    ref = np.random.default_rng(3)
    ref.standard_normal(10 * 4)
    assert rng.random() == ref.random()


def test_wind_is_the_same_whatever_the_noise_level() -> None:
    """Noise level does not change the meander and gust draws (alignment guarantee)."""
    a = _sim(duration_s=600.0, config=TruthConfig(noise_ppm=0.0), rng=np.random.default_rng(2))
    b = _sim(duration_s=600.0, config=TruthConfig(noise_ppm=0.7), rng=np.random.default_rng(2))
    assert np.array_equal(a.wind_from_deg, b.wind_from_deg)
    assert np.array_equal(a.wind_speed_m_s, b.wind_speed_m_s)
    assert not np.array_equal(a.ppm, b.ppm)


def test_different_seeds_give_different_series_and_sensor_noise_is_independent() -> None:
    """Seeds matter, and two sensors at the same place do not share their noise."""
    a = _sim(sources=[], rng=np.random.default_rng(1))
    b = _sim(sources=[], rng=np.random.default_rng(2))
    assert not np.array_equal(a.ppm, b.ppm)
    twin = Sensor("S3", S1.position, 0.3)
    c = _sim(sources=[], sensors=[S1, twin], duration_s=1000.0)
    assert not np.allclose(c.ppm[:, 0], c.ppm[:, 1])


def test_sensor_order_sets_the_columns_and_sensor_noise_field_is_ignored() -> None:
    """Columns follow the sensor list; ``Sensor.noise_ppm`` is not used (config.noise_ppm is)."""
    loud = Sensor("S2", Point3(300.0, 0.0, 2.0), 100.0)
    s = _sim(sensors=[loud, S1], config=QUIET)
    assert np.allclose(s.ppm[:, 0], s.ppm[:, 1])
    far = _sim(sensors=[S1, Sensor("S2", Point3(-300.0, 0.0, 2.0), 0.3)], config=QUIET)
    assert far.ppm[0, 0] > 1.95
    assert far.ppm[0, 1] == 1.95  # the upwind sensor sees only the background


def _ar1_reference(eps: np.ndarray, phi: float, sd: float) -> list[float]:
    """The documented recursion: x_0 = sd e_0 and x_k = phi x_(k-1) + sqrt(1 - phi^2) sd e_k."""
    out = [sd * float(eps[0])]
    for e in eps[1:]:
        out.append(phi * out[-1] + float(np.sqrt(1.0 - phi**2)) * sd * float(e))
    return out


def test_meander_uses_the_first_draw_and_gusts_the_second() -> None:
    """Direction = 270 + AR(1) of draw 0; speed = 4 (1 + AR(1) of draw 1); phi = exp(-dt / tau)."""
    steps = 30
    eps = np.random.default_rng(4).standard_normal((steps, 3))
    phi = float(np.exp(-10.0 / 120.0))
    cfg = TruthConfig(noise_ppm=0.0)
    s = _sim(sources=[], duration_s=300.0, config=cfg, rng=np.random.default_rng(4))
    meander = np.array(_ar1_reference(eps[:, 0], phi, 10.0))
    gust = np.array(_ar1_reference(eps[:, 1], phi, 0.15))
    assert np.allclose(s.wind_from_deg, (270.0 + meander) % 360.0)
    assert np.allclose(s.wind_speed_m_s, np.maximum(0.3, 4.0 * (1.0 + gust)))


def test_noise_is_unbiased_pooled_over_50_seeds() -> None:
    """Seeds 0-49 pooled (50 x 360 = 18000 samples) give mean 1.95 and std 0.3 ppm.

    The tolerance of 0.01 ppm is about 4.5 sigma of the pooled mean (0.3 / sqrt(18000) =
    0.00224 ppm), so a single unlucky seed cannot fail it but a real bias would.
    """
    series = [
        _sim(
            sources=[],
            sensors=[S1],
            duration_s=3600.0,
            config=TruthConfig(),
            rng=np.random.default_rng(seed),
        ).ppm
        for seed in range(50)
    ]
    pooled = np.concatenate(series).ravel()
    assert pooled.size == 18000
    assert float(pooled.mean()) == pytest.approx(1.95, abs=0.01)
    assert float(pooled.std()) == pytest.approx(0.3, abs=0.01)


def test_truth_model_explicitly_exports_its_reexported_types() -> None:
    """``__all__`` lists the public names, so mypy strict accepts imports of the moved types."""
    from plumetrace.engineering import truth_faults, truth_model, truth_wake

    names = {"SensorFault", "WakeObstacle", "TrueSource", "TruthConfig", "TruthSeries"}
    assert names | {"MIN_SPEED_M_S", "simulate_sensors"} <= set(truth_model.__all__)
    assert truth_model.SensorFault is truth_faults.SensorFault
    assert truth_model.WakeObstacle is truth_wake.WakeObstacle
    assert all(hasattr(truth_model, name) for name in truth_model.__all__)
