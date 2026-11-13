"""Edge cases of the truth physics: wind, stability, source windows, faults and building wakes."""

from typing import Any

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3, Sensor
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import (
    MIN_SPEED_M_S,
    SensorFault,
    TrueSource,
    TruthConfig,
    TruthSeries,
    WakeObstacle,
    simulate_sensors,
)
from plumetrace.engineering.truth_weather import HourlyWeather, angular_diff_deg

P = 98900.0
S1 = Sensor("S1", Point3(300.0, 0.0, 2.0), 0.3)
SOURCE = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 0.0, 1e9)
BRIGGS = CoefficientSet.BRIGGS_RURAL
QUIET = TruthConfig(
    coeff=BRIGGS, meander_sd_deg=0.0, speed_cv=0.0, wake_dilution=1.0, noise_ppm=0.0
)


def _hour(i: int = 0, **kw: Any) -> HourlyWeather:
    base: dict[str, Any] = dict(
        hour_index=i,
        wind_speed_m_s=4.0,
        wind_from_deg=270.0,
        shortwave_w_m2=0.0,
        cloud_fraction=0.9,
        temp_k=290.0,
    )
    base.update(kw)
    return HourlyWeather(**base)


def _sim(**kw: Any) -> TruthSeries:
    args: dict[str, Any] = dict(
        sources=[SOURCE],
        sensors=[S1],
        weather=[_hour(0), _hour(1)],
        dt_s=10.0,
        duration_s=600.0,
        rng=np.random.default_rng(0),
        pressure_pa=P,
        config=QUIET,
    )
    args.update(kw)
    return simulate_sensors(**args)


def _excess(s: TruthSeries) -> np.ndarray:
    return s.ppm - 1.95


def test_meander_and_gusts_have_the_configured_statistics() -> None:
    """One day at 10 s: direction sd 10 deg, speed CV 0.15, lag-1 correlation exp(-10/120)."""
    cfg = TruthConfig(noise_ppm=0.0)
    weather = [_hour(i) for i in range(25)]
    s = _sim(sources=[], weather=weather, duration_s=86400.0, config=cfg)
    offset = np.array([angular_diff_deg(float(d), 270.0) for d in s.wind_from_deg])
    assert offset.std() == pytest.approx(10.0, rel=0.1)
    assert abs(offset.mean()) < 1.5
    assert s.wind_speed_m_s.mean() == pytest.approx(4.0, rel=0.03)
    assert s.wind_speed_m_s.std() == pytest.approx(0.6, rel=0.1)
    phi = float(np.exp(-10.0 / 120.0))
    assert np.corrcoef(offset[:-1], offset[1:])[0, 1] == pytest.approx(phi, abs=0.03)
    gust = s.wind_speed_m_s
    assert np.corrcoef(gust[:-1], gust[1:])[0, 1] == pytest.approx(phi, abs=0.03)


def test_speed_is_floored_in_calm_and_under_huge_gusts() -> None:
    """A calm hour (0 m/s) and a gust CV of 5 never go below 0.3 m/s; readings stay finite."""
    calm = _sim(weather=[_hour(0, wind_speed_m_s=0.0)], config=QUIET)
    assert np.all(calm.wind_speed_m_s == MIN_SPEED_M_S)
    assert np.all(np.isfinite(calm.ppm))
    wild = TruthConfig(coeff=BRIGGS, speed_cv=5.0, noise_ppm=0.0)
    s = _sim(duration_s=3600.0, config=wild)
    assert s.wind_speed_m_s.min() >= MIN_SPEED_M_S
    assert np.all(np.isfinite(s.ppm))


def test_direction_wraps_through_north_and_stays_in_range() -> None:
    """Interpolating 350 to 10 deg gives 0 deg half an hour in; meander never leaves [0, 360)."""
    weather = [_hour(0, wind_from_deg=350.0), _hour(1, wind_from_deg=10.0)]
    s = _sim(weather=weather, duration_s=3600.0, dt_s=300.0, config=QUIET)
    assert s.wind_from_deg[0] == 350.0
    assert s.wind_from_deg[6] == 0.0
    assert s.wind_from_deg[3] == pytest.approx(355.0)
    noisy = _sim(weather=weather, duration_s=3600.0, config=TruthConfig(meander_sd_deg=40.0))
    assert noisy.wind_from_deg.min() >= 0.0 and noisy.wind_from_deg.max() < 360.0


def test_hours_past_the_list_hold_the_last_entry() -> None:
    """Three hours of run on two hours of weather: the last hour is held, no error."""
    weather = [_hour(0, wind_speed_m_s=2.0), _hour(1, wind_speed_m_s=6.0)]
    s = _sim(sources=[], weather=weather, duration_s=3 * 3600.0, dt_s=600.0)
    assert np.all(s.wind_speed_m_s[6:] == 6.0)
    assert s.wind_speed_m_s[0] == 2.0


def test_temperature_and_stability_follow_the_hour_and_ignore_gusts() -> None:
    """Temperature is taken from hour i; stability uses the speed without gusts."""
    weather = [
        _hour(0, wind_speed_m_s=1.0, shortwave_w_m2=800.0, cloud_fraction=0.0, temp_k=280.0),
        _hour(1, wind_speed_m_s=1.0, shortwave_w_m2=0.0, cloud_fraction=0.9, temp_k=290.0),
    ]
    wild = TruthConfig(coeff=BRIGGS, speed_cv=0.5, noise_ppm=0.0)
    s = _sim(weather=weather, duration_s=7200.0, dt_s=600.0, config=wild)
    first, second = s.times_s < 3600.0, s.times_s >= 3600.0
    assert np.all(s.temp_k[first] == 280.0) and np.all(s.temp_k[second] == 290.0)
    assert [c for c, f in zip(s.stability, first, strict=True) if f] == [StabilityClass.A] * 6
    assert [c for c, f in zip(s.stability, second, strict=True) if f] == [StabilityClass.D] * 6


def test_zero_rate_and_inactive_sources_leave_only_the_background() -> None:
    """Zero rate, an empty window and a window after the run add nothing."""
    zero = TrueSource(Point3(0.0, 0.0, 2.0), 0.0, 0.0, 1e9)
    empty = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 100.0, 100.0)
    later = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 1e6, 2e6)
    s = _sim(sources=[zero, empty, later])
    assert np.all(s.ppm == 1.95)


def test_source_window_is_start_inclusive_and_end_exclusive() -> None:
    """A source from 100 s to 200 s is active at t = 100 and off again at t = 200."""
    window = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 100.0, 200.0)
    s = _sim(sources=[window])
    on = (s.times_s >= 100.0) & (s.times_s < 200.0)
    assert np.all(s.ppm[on, 0] > 1.95)
    assert np.all(s.ppm[~on, 0] == 1.95)
    assert on.sum() == 10


def test_sources_add_up_and_scale_linearly() -> None:
    """Two identical sources give twice the excess; doubling the rate does the same."""
    one = _excess(_sim())
    two = _excess(_sim(sources=[SOURCE, SOURCE]))
    double = TrueSource(Point3(0.0, 0.0, 2.0), 72.0, 0.0, 1e9)
    assert np.allclose(two, 2.0 * one)
    assert np.allclose(_excess(_sim(sources=[double])), 2.0 * one)


def test_a_sensor_upwind_of_the_source_sees_the_background() -> None:
    """Wind from the west: a sensor west of the source is not in the plume."""
    west = Sensor("W", Point3(-100.0, 0.0, 2.0), 0.3)
    assert np.all(_sim(sensors=[west]).ppm == 1.95)


def test_sensor_at_the_source_is_finite() -> None:
    """A receptor exactly at the source (zero distance) gives a finite, not NaN, reading."""
    here = Sensor("H", Point3(0.0, 0.0, 2.0), 0.3)
    s = _sim(sensors=[here])
    assert np.all(np.isfinite(s.ppm))


def test_fault_start_delay_sign_and_stacking() -> None:
    """Drift starts at start_s, can be negative, adds up on one sensor, leaves others alone."""
    other = Sensor("S2", Point3(-100.0, 0.0, 2.0), 0.3)
    faults = [SensorFault("S1", 2.0, 300.0), SensorFault("S1", -0.5, 0.0)]
    s = _sim(sources=[], sensors=[S1, other], faults=faults, duration_s=3600.0)
    t = s.times_s
    expected = 1.95 + 2.0 * np.maximum(0.0, t - 300.0) / 3600.0 - 0.5 * t / 3600.0
    assert np.allclose(s.ppm[:, 0], expected)
    assert np.all(s.ppm[:, 1] == 1.95)
    assert s.ppm[0, 0] == 1.95


def test_fault_before_the_run_starts_is_a_constant_ramp() -> None:
    """A fault that started an hour before t = 0 already has a one-hour drift at t = 0."""
    s = _sim(sources=[], faults=[SensorFault("S1", 1.0, -3600.0)], duration_s=100.0)
    assert s.ppm[0, 0] == pytest.approx(1.95 + 1.0)


def _wake_pair(sensor_x: float, **obstacle: Any) -> tuple[float, float]:
    """Return (diluted excess, plain excess) of a sensor at ``sensor_x`` on the x axis."""
    near = Sensor("S1", Point3(sensor_x, 0.0, 2.0), 0.3)
    shape: dict[str, Any] = dict(center_xy=(50.0, 0.0), half_width_m=5.0, height_m=10.0)
    shape.update(obstacle)
    cfg = TruthConfig(coeff=BRIGGS, meander_sd_deg=0.0, speed_cv=0.0, noise_ppm=0.0)
    wake = _sim(sensors=[near], obstacles=[WakeObstacle(**shape)], duration_s=10.0, config=cfg)
    plain = _sim(sensors=[near], duration_s=10.0, config=cfg)
    return float(wake.ppm[0, 0] - 1.95), float(plain.ppm[0, 0] - 1.95)


@pytest.mark.parametrize(
    "x, diluted",
    [
        (55.0, True),  # inside the wake
        (80.0, True),  # exactly 3 x height behind the centre: boundary is inclusive
        (80.5, False),  # just beyond the wake
        (50.0, False),  # at the obstacle centre: along = 0 is not in the wake
        (40.0, False),  # upstream of the obstacle
    ],
)
def test_wake_length_is_three_heights_with_inclusive_end(x: float, diluted: bool) -> None:
    """The wake is 0 < along <= 3 * height behind the obstacle centre."""
    with_wake, plain = _wake_pair(x)
    assert plain > 0.0
    assert with_wake == pytest.approx(0.6 * plain if diluted else plain)


def test_wake_is_limited_to_the_obstacle_width() -> None:
    """Crosswind offset equal to the half width is in the wake, a metre more is outside."""
    inside = Sensor("A", Point3(60.0, 5.0, 2.0), 0.3)
    outside = Sensor("B", Point3(60.0, 6.0, 2.0), 0.3)
    cfg = TruthConfig(coeff=BRIGGS, meander_sd_deg=0.0, speed_cv=0.0, noise_ppm=0.0)
    ob = WakeObstacle((50.0, 0.0), 5.0, 10.0)
    both = [inside, outside]
    wake = _sim(sensors=both, obstacles=[ob], duration_s=10.0, config=cfg)
    plain = _sim(sensors=both, duration_s=10.0, config=cfg)
    ratio = (wake.ppm[0] - 1.95) / (plain.ppm[0] - 1.95)
    assert ratio == pytest.approx([0.6, 1.0])


def test_overlapping_wakes_dilute_only_once() -> None:
    """A receptor in two wakes is multiplied by the dilution once, not squared."""
    near = Sensor("S1", Point3(60.0, 0.0, 2.0), 0.3)
    cfg = TruthConfig(coeff=BRIGGS, meander_sd_deg=0.0, speed_cv=0.0, noise_ppm=0.0)
    two = [WakeObstacle((50.0, 0.0), 5.0, 10.0), WakeObstacle((45.0, 0.0), 8.0, 12.0)]
    one = _sim(sensors=[near], obstacles=two[:1], duration_s=10.0, config=cfg)
    both = _sim(sensors=[near], obstacles=two, duration_s=10.0, config=cfg)
    assert np.allclose(both.ppm, one.ppm)


def test_wake_follows_the_wind_direction() -> None:
    """With the wind from the south the wake lies north of the obstacle, not east of it."""
    weather = [_hour(0, wind_from_deg=180.0), _hour(1, wind_from_deg=180.0)]
    src = TrueSource(Point3(50.0, -50.0, 2.0), 36.0, 0.0, 1e9)
    north = Sensor("N", Point3(50.0, 10.0, 2.0), 0.3)
    east = Sensor("E", Point3(60.0, 0.0, 2.0), 0.3)
    cfg = TruthConfig(coeff=BRIGGS, meander_sd_deg=0.0, speed_cv=0.0, noise_ppm=0.0)
    ob = WakeObstacle((50.0, 0.0), 5.0, 10.0)
    kw: dict[str, Any] = dict(sources=[src], sensors=[north, east], weather=weather, config=cfg)
    wake = _sim(obstacles=[ob], duration_s=10.0, **kw)
    plain = _sim(duration_s=10.0, **kw)
    assert (wake.ppm[0, 0] - 1.95) == pytest.approx(0.6 * (plain.ppm[0, 0] - 1.95))
    assert wake.ppm[0, 1] == plain.ppm[0, 1]


def test_zero_dilution_removes_the_plume_in_the_wake() -> None:
    """A dilution of 0 is allowed and leaves only the background behind the obstacle."""
    near = Sensor("S1", Point3(60.0, 0.0, 2.0), 0.3)
    cfg = TruthConfig(
        coeff=BRIGGS, meander_sd_deg=0.0, speed_cv=0.0, noise_ppm=0.0, wake_dilution=0.0
    )
    ob = WakeObstacle((50.0, 0.0), 5.0, 10.0)
    s = _sim(sensors=[near], obstacles=[ob], duration_s=10.0, config=cfg)
    assert s.ppm[0, 0] == 1.95
