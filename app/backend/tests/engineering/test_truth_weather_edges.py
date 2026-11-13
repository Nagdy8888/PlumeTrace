"""Edge cases of the truth weather: validation, draw order, wrap-around and interpolation."""

import math
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from plumetrace.engineering.truth_weather import (
    HourlyWeather,
    angular_diff_deg,
    interpolate_weather,
    synthetic_hourly_weather,
)

NAN = float("nan")
INF = float("inf")


def _w(i: int = 0, **kw: Any) -> HourlyWeather:
    base: dict[str, Any] = dict(
        hour_index=i,
        wind_speed_m_s=4.0,
        wind_from_deg=270.0,
        shortwave_w_m2=0.0,
        cloud_fraction=0.5,
        temp_k=290.0,
    )
    base.update(kw)
    return HourlyWeather(**base)


@pytest.mark.parametrize(
    "field, value",
    [
        ("wind_speed_m_s", -0.1),
        ("wind_speed_m_s", NAN),
        ("wind_speed_m_s", INF),
        ("wind_from_deg", NAN),
        ("wind_from_deg", INF),
        ("shortwave_w_m2", -1.0),
        ("shortwave_w_m2", NAN),
        ("cloud_fraction", 1.01),
        ("cloud_fraction", -0.01),
        ("cloud_fraction", NAN),
        ("temp_k", 0.0),
        ("temp_k", -5.0),
        ("temp_k", NAN),
        ("hour_index", -1),
    ],
)
def test_hourly_weather_rejects_unphysical_values(field: str, value: float) -> None:
    """Negative or non-finite weather fails at construction, never inside the series."""
    with pytest.raises(ValidationError):
        _w(**{field: value})


def test_hourly_weather_is_frozen_and_allows_calm() -> None:
    """A calm hour (0 m/s) is valid input; the model is immutable."""
    w = _w(wind_speed_m_s=0.0)
    assert w.wind_speed_m_s == 0.0
    with pytest.raises(ValidationError):
        w.temp_k = 300.0


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (10.0, 350.0, 20.0),
        (350.0, 10.0, -20.0),
        (180.0, 0.0, 180.0),
        (0.0, 180.0, 180.0),
        (-1e-20, 0.0, 0.0),
        (90.0, 90.0, 0.0),
        (725.0, 5.0, 0.0),
    ],
)
def test_angular_diff_is_in_minus_180_to_180(a: float, b: float, expected: float) -> None:
    """The signed smallest difference lies in (-180, 180]; +180 is kept, -180 is not."""
    assert angular_diff_deg(a, b) == pytest.approx(expected)


def test_zero_hours_is_an_empty_list_and_negative_hours_fail() -> None:
    """No hours gives no weather and consumes no random numbers; negative hours is an error."""
    rng = np.random.default_rng(0)
    assert synthetic_hourly_weather(0, 0, rng) == []
    assert rng.random() == np.random.default_rng(0).random()
    with pytest.raises(ValueError, match="hours"):
        synthetic_hourly_weather(-1, 0, np.random.default_rng(0))


@pytest.mark.parametrize("start", [-1, 24, 100])
def test_start_hour_must_be_a_clock_hour(start: int) -> None:
    """The local start hour is 0 to 23."""
    with pytest.raises(ValueError, match="start_hour_of_day"):
        synthetic_hourly_weather(3, start, np.random.default_rng(0))


@pytest.mark.parametrize("prevailing", [NAN, INF, -INF])
def test_prevailing_direction_must_be_finite(prevailing: float) -> None:
    """A non-finite prevailing direction is rejected."""
    with pytest.raises(ValueError, match="prevailing_from_deg"):
        synthetic_hourly_weather(3, 0, np.random.default_rng(0), prevailing)


def test_draw_order_is_speed_direction_cloud() -> None:
    """Hour 0 uses the first three draws in the order normal, normal, beta."""
    ref = np.random.default_rng(11)
    z_speed = ref.standard_normal()
    z_dir = ref.normal(0.0, 20.0)
    cloud = ref.beta(2.0, 5.0)
    w = synthetic_hourly_weather(1, 12, np.random.default_rng(11))[0]
    assert w.wind_speed_m_s == pytest.approx(math.exp(math.log(4.0) + 0.5 * z_speed))
    assert w.wind_from_deg == pytest.approx((250.0 + z_dir) % 360.0)
    assert w.cloud_fraction == pytest.approx(cloud)
    sun = 800.0 * math.sin(math.pi * 6 / 12) * (1 - 0.75 * cloud)
    assert w.shortwave_w_m2 == pytest.approx(sun)
    assert w.temp_k == 300.0


def test_consumes_exactly_three_draws_per_hour() -> None:
    """Three random numbers per hour keep later draws aligned for the caller."""
    rng = np.random.default_rng(4)
    synthetic_hourly_weather(10, 0, rng)
    ref = np.random.default_rng(4)
    for _ in range(10):
        ref.standard_normal()
        ref.normal(0.0, 20.0)
        ref.beta(2.0, 5.0)
    assert rng.random() == ref.random()


def test_day_night_shape_hour_index_and_temperature() -> None:
    """Sun only between 06 and 18 h, hour_index counts from 0, temperature follows the sun."""
    ws = synthetic_hourly_weather(24, 0, np.random.default_rng(2))
    assert [w.hour_index for w in ws] == list(range(24))
    for w in ws:
        h = w.hour_index
        if h < 6 or h > 18:
            assert w.shortwave_w_m2 == 0.0
        elif 6 < h < 18:
            assert w.shortwave_w_m2 > 0.0
        else:  # sin(0) and sin(pi) at the edges: zero up to rounding
            assert w.shortwave_w_m2 < 1e-9
        assert w.temp_k == (300.0 if w.shortwave_w_m2 > 10.0 else 285.0)
        assert 0.0 <= w.cloud_fraction <= 1.0


def test_start_hour_shifts_the_clock() -> None:
    """Starting at 12 local time puts the first hour in the sun and hour 12 at night."""
    ws = synthetic_hourly_weather(24, 12, np.random.default_rng(2))
    assert ws[0].shortwave_w_m2 > 0.0
    assert ws[12].shortwave_w_m2 == 0.0


def test_long_series_stays_in_range_and_is_clipped_at_15() -> None:
    """Over 5000 hours speed hits the 15 m/s ceiling and stays in [0.3, 15].

    The direction stays in [0, 360) and near the prevailing direction.
    """
    ws = synthetic_hourly_weather(5000, 0, np.random.default_rng(8))
    speeds = np.array([w.wind_speed_m_s for w in ws])
    dirs = np.array([w.wind_from_deg for w in ws])
    assert speeds.max() == 15.0
    assert speeds.min() >= 0.3
    assert dirs.min() >= 0.0 and dirs.max() < 360.0
    spread = np.array([angular_diff_deg(float(d), 250.0) for d in dirs])
    assert abs(spread.mean()) < 5.0
    # AR(1) walk: sd = 20 / sqrt(1 - 0.8**2) = 33.3 deg (before the wrap into +-180).
    assert spread.std() == pytest.approx(33.3, abs=4.0)


def test_prevailing_direction_wraps() -> None:
    """A prevailing direction of 5 deg lets the walk cross north without leaving [0, 360)."""
    ws = synthetic_hourly_weather(500, 0, np.random.default_rng(1), prevailing_from_deg=5.0)
    dirs = np.array([w.wind_from_deg for w in ws])
    assert dirs.min() >= 0.0 and dirs.max() < 360.0
    assert dirs.min() < 90.0 and dirs.max() > 270.0  # it did cross north


def test_interpolation_mid_hour_and_hold_last() -> None:
    """Speed is linear between hours, the rest comes from hour i, hours past the end hold."""
    ws = [
        _w(0, wind_speed_m_s=2.0, temp_k=280.0, shortwave_w_m2=0.0, cloud_fraction=0.1),
        _w(1, wind_speed_m_s=6.0, temp_k=290.0, shortwave_w_m2=500.0, cloud_fraction=0.9),
    ]
    t = np.array([0.0, 1800.0, 3599.0, 3600.0, 5400.0, 7200.0, 1e7])
    out = interpolate_weather(ws, t)
    assert out.speed_m_s[1] == pytest.approx(4.0)
    assert out.speed_m_s[2] == pytest.approx(2.0 + 4.0 * 3599.0 / 3600.0)
    assert list(out.speed_m_s[3:]) == [6.0, 6.0, 6.0, 6.0]
    assert list(out.temp_k) == [280.0, 280.0, 280.0, 290.0, 290.0, 290.0, 290.0]
    assert list(out.shortwave_w_m2[:3]) == [0.0, 0.0, 0.0]
    assert out.cloud_fraction[3] == 0.9


def test_direction_interpolates_along_the_shortest_arc() -> None:
    """350 to 10 passes through north, not through south; the result is in [0, 360)."""
    ws = [_w(0, wind_from_deg=350.0), _w(1, wind_from_deg=10.0)]
    out = interpolate_weather(ws, np.array([0.0, 900.0, 1800.0, 2700.0, 3600.0]))
    assert list(np.round(out.from_deg, 6)) == [350.0, 355.0, 0.0, 5.0, 10.0]
    assert out.from_deg.min() >= 0.0 and out.from_deg.max() < 360.0


def test_single_hour_list_holds_forever() -> None:
    """One hour of weather is held for any time."""
    out = interpolate_weather([_w(0)], np.array([0.0, 1e5]))
    assert list(out.speed_m_s) == [4.0, 4.0]


def test_interpolation_rejects_bad_input() -> None:
    """No weather, negative or non-finite times are errors."""
    with pytest.raises(ValueError, match="weather"):
        interpolate_weather([], np.array([0.0]))
    for bad in (np.array([-1.0]), np.array([NAN]), np.array([INF])):
        with pytest.raises(ValueError, match="times_s"):
            interpolate_weather([_w(0)], bad)


def test_empty_time_array_gives_empty_arrays() -> None:
    """An empty time axis maps to empty arrays (the caller decides if that is an error)."""
    out = interpolate_weather([_w(0)], np.array([], dtype=np.float64))
    assert out.speed_m_s.shape == (0,) and out.from_deg.shape == (0,)
