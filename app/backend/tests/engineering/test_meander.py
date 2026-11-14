"""Tests of the optional wind-direction spread (meander) in the averaging, plume and inversion.

The spread option is a project derivation (small-angle variance of a direction-averaged plume),
not a published formula, so these tests prove its algebra and its limits rather than cite a
source: the circular standard deviation, the exact default path, the centreline ratio, the
conserved crosswind integral, the input checks and a recovery on data made with the same option.
"""

import math

import numpy as np
import pytest

from plumetrace.engineering.averaging import window_direction_sd_deg, window_wind
from plumetrace.engineering.dispersion import X_MAX_M, X_MIN_M, CoefficientSet, sigmas_m
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.inversion import InversionInput, invert
from plumetrace.engineering.plume import concentration_kg_m3, concentration_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.facility.candidates import emission_candidates, methane_sensors
from plumetrace.facility.loader import load_facility

SPEC = load_facility()
CANDS = emission_candidates(SPEC)
SENSORS = methane_sensors(SPEC)
D = StabilityClass.D
ORIGIN = Point3(0.0, 0.0, 0.0)
SETS = (CoefficientSet.BRIGGS_RURAL, CoefficientSet.PG_MARTIN)


def _times(n: int) -> np.ndarray:
    return 10.0 * np.arange(n, dtype=np.float64)


# --- (a) circular standard deviation per window -------------------------------------------------


def test_constant_direction_has_exactly_zero_spread() -> None:
    """A window of identical directions has circular sd 0.0 exactly (R = 1, no rounding noise)."""
    for bearing in (0.0, 37.3, 123.456, 250.0, 359.9):
        sd = window_direction_sd_deg(_times(120), np.full(120, bearing))
        assert sd.shape == (2,) and np.all(sd == 0.0)


def test_alternating_350_and_10_degrees() -> None:
    """Directions 350 and 10 give R = cos(10 deg), so sd = degrees(sqrt(-2 ln R)) = 10.02556."""
    from_deg = np.tile([350.0, 10.0], 60)
    sd = window_direction_sd_deg(_times(120), from_deg)
    assert np.allclose(sd, 10.02556, rtol=1e-6, atol=0.0)


def test_spread_is_unchanged_by_rotating_the_directions() -> None:
    """Rotating every direction by 180 degrees leaves the circular sd unchanged."""
    rng = np.random.default_rng(3)
    from_deg = (250.0 + rng.normal(0.0, 12.0, 180)) % 360.0
    a = window_direction_sd_deg(_times(180), from_deg)
    b = window_direction_sd_deg(_times(180), (from_deg + 180.0) % 360.0)
    assert np.allclose(a, b, rtol=1e-9, atol=1e-12)


def test_small_spread_matches_the_linear_standard_deviation() -> None:
    """For a narrow normal spread the circular sd is close to the ordinary sd of the angles."""
    rng = np.random.default_rng(4)
    from_deg = 90.0 + rng.normal(0.0, 5.0, 600)
    sd = window_direction_sd_deg(_times(600), from_deg)
    assert sd.shape == (10,) and np.allclose(sd, 5.0, atol=1.0)


def test_window_under_half_coverage_is_nan() -> None:
    """A window with more than half of its directions missing is NaN; a complete one is not."""
    from_deg = np.full(120, 200.0)
    from_deg[:40] = np.nan
    sd = window_direction_sd_deg(_times(120), from_deg)
    assert np.isnan(sd[0]) and sd[1] == 0.0


def test_nan_exactly_where_window_wind_is_nan() -> None:
    """Any missing direction in a window makes both window_wind and the spread NaN there."""
    from_deg = np.tile([240.0, 260.0], 90)
    from_deg[7] = np.nan  # one missing sample in window 0 only (window_wind has no coverage rule)
    t = _times(180)
    _, mean_dir = window_wind(t, np.full(180, 4.0), from_deg)
    sd = window_direction_sd_deg(t, from_deg)
    assert np.array_equal(np.isnan(sd), np.isnan(mean_dir))
    assert bool(np.isnan(sd[0])) and not np.isnan(sd[1:]).any()


def test_window_grid_matches_window_wind() -> None:
    """A trailing partial window is dropped and a series shorter than one window gives nothing."""
    assert window_direction_sd_deg(_times(130), np.full(130, 10.0)).shape == (2,)
    assert window_direction_sd_deg(_times(30), np.full(30, 10.0)).shape == (0,)


def test_spread_input_checks() -> None:
    """Fewer than two samples and a length mismatch raise ValueError, like window_wind."""
    with pytest.raises(ValueError, match="at least two"):
        window_direction_sd_deg(np.array([0.0]), np.array([1.0]))
    with pytest.raises(ValueError, match="differs"):
        window_direction_sd_deg(_times(120), np.full(119, 10.0))
    with pytest.raises(ValueError, match="differs"):
        window_direction_sd_deg(_times(120), np.full(121, 10.0))


# --- (b) the default path is untouched ---------------------------------------------------------


def test_zero_spread_is_bit_identical_to_the_default_call() -> None:
    """dir_sd_deg=0.0 gives exactly the same array as omitting it, for both coefficient sets."""
    rng = np.random.default_rng(15)
    classes = list(StabilityClass)
    for coeff in SETS:
        for _ in range(30):
            rec = rng.uniform(-300.0, 300.0, (40, 3))
            rec[:, 2] = rng.uniform(0.0, 10.0, 40)
            src = Point3(*rng.uniform(-50.0, 50.0, 2), float(rng.uniform(0.0, 20.0)))
            args = (
                float(rng.uniform(1e-4, 2.0)),
                float(rng.uniform(0.5, 15.0)),
                float(rng.uniform(0.0, 360.0)),
                src,
                rec,
                classes[int(rng.integers(len(classes)))],
                coeff,
            )
            base = concentration_kg_m3(*args)
            assert np.array_equal(base, concentration_kg_m3(*args, dir_sd_deg=0.0))
            ppm = concentration_ppm(*args, 290.0, 98900.0)
            assert np.array_equal(ppm, concentration_ppm(*args, 290.0, 98900.0, dir_sd_deg=0.0))


# --- (c) the centreline ratio -------------------------------------------------------------------


@pytest.mark.parametrize("coeff", SETS)
@pytest.mark.parametrize("sd_deg", [3.0, 10.0, 25.0])
def test_centreline_ratio_is_sigma_y_over_effective_sigma_y(
    coeff: CoefficientSet, sd_deg: float
) -> None:
    """On the ground-level centreline C(sd)/C(0) = sy / sqrt(sy^2 + (x_c radians(sd))^2).

    Distances include both clip edges and points beyond them; ``x_c`` is the along-wind distance
    clipped to the same range as the spreads, and sigma_z is not changed (it cancels).
    """
    for x in (5.0, 10.0, 50.0, 300.0, 1000.0, 1500.0):
        rec = np.array([[x, 0.0, 0.0]])  # wind from 270: the plume travels east, cross = 0
        plain = concentration_kg_m3(0.01, 4.0, 270.0, ORIGIN, rec, D, coeff)[0]
        wide = concentration_kg_m3(0.01, 4.0, 270.0, ORIGIN, rec, D, coeff, dir_sd_deg=sd_deg)[0]
        sy = float(sigmas_m(np.array([x]), D, coeff)[0][0])
        x_c = min(max(x, X_MIN_M), X_MAX_M)
        sy_eff = math.sqrt(sy**2 + (x_c * math.radians(sd_deg)) ** 2)
        assert math.isclose(wide / plain, sy / sy_eff, rel_tol=1e-12)


# --- (d) the crosswind integral is conserved ---------------------------------------------------


@pytest.mark.parametrize("coeff", SETS)
def test_crosswind_integral_is_unchanged_by_the_spread(coeff: CoefficientSet) -> None:
    """Widening sigma_y moves mass sideways but does not change the crosswind integral.

    At 100 m (class D) the effective sigma_y is below 20 m, so +-200 m holds the whole plume.
    """
    y = np.linspace(-200.0, 200.0, 4001)
    rec = np.column_stack([np.full_like(y, 100.0), y, np.zeros_like(y)])
    plain = concentration_kg_m3(0.01, 4.0, 270.0, ORIGIN, rec, D, coeff)
    wide = concentration_kg_m3(0.01, 4.0, 270.0, ORIGIN, rec, D, coeff, dir_sd_deg=10.0)
    assert wide.max() < plain.max()
    assert math.isclose(np.trapezoid(wide, y), np.trapezoid(plain, y), rel_tol=1e-6)


# --- (e) invalid spread -------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [-1.0, -1e-9, math.nan, math.inf, -math.inf])
def test_invalid_direction_spread_raises(bad: float) -> None:
    """A negative or non-finite dir_sd_deg is rejected by both concentration functions."""
    rec = np.array([[100.0, 0.0, 0.0]])
    with pytest.raises(ValueError, match="dir_sd_deg"):
        concentration_kg_m3(0.01, 4.0, 270.0, ORIGIN, rec, D, SETS[0], dir_sd_deg=bad)
    with pytest.raises(ValueError, match="dir_sd_deg"):
        concentration_ppm(0.01, 4.0, 270.0, ORIGIN, rec, D, SETS[0], 290.0, 98900.0, dir_sd_deg=bad)


# --- inversion: synthetic data in the style of test_inversion.py -------------------------------


def _receptors() -> np.ndarray:
    return np.array([[s.position.x_m, s.position.y_m, s.position.z_m] for s in SENSORS])


def _synth(
    rate_kg_h: float = 10.0,
    windows: int = 12,
    gen_sd_deg: float = 0.0,
    seed: int = 1,
    wind_dir_sd_deg: list[float] | None = None,
    unknown_direction: int | None = None,
) -> InversionInput:
    """Observations from VS-250.tip made with ``dir_sd_deg=gen_sd_deg`` plus 0.05 ppm noise.

    ``unknown_direction`` turns the wind direction of that window into NaN after the data exist.
    """
    rng = np.random.default_rng(seed)
    wind_from = 250.0 + rng.uniform(-20.0, 20.0, windows)
    src = {c.id: c for c in CANDS}["VS-250.tip"].position
    obs = np.array(
        [
            concentration_ppm(
                rate_kg_h / 3600.0,
                4.0,
                float(w),
                src,
                _receptors(),
                D,
                CoefficientSet.BRIGGS_RURAL,
                300.0,
                98900.0,
                dir_sd_deg=gen_sd_deg,
            )
            for w in wind_from
        ]
    )
    obs += rng.normal(0.0, 0.05, obs.shape)
    if unknown_direction is not None:
        wind_from[unknown_direction] = np.nan
    return InversionInput(
        candidates=CANDS,
        sensors=SENSORS,
        observed_ppm_above_bg=obs.tolist(),
        wind_speed_m_s=[4.0] * windows,
        wind_from_deg=wind_from.tolist(),
        stability=[D] * windows,
        temp_k=300.0,
        pressure_pa=98900.0,
        wind_dir_sd_deg=wind_dir_sd_deg,
    )


# --- (f) the default inversion is unchanged ----------------------------------------------------


def test_missing_or_zero_wind_dir_sd_gives_the_same_result() -> None:
    """wind_dir_sd_deg None and all zeros give exactly the result without the field."""
    base = invert(_synth()).model_dump()
    assert invert(_synth(wind_dir_sd_deg=None)).model_dump() == base
    assert invert(_synth(wind_dir_sd_deg=[0.0] * 12)).model_dump() == base


def test_nonzero_wind_dir_sd_reaches_the_plume() -> None:
    """A spread of 8 degrees changes the rate estimate, so the field is used by the inversion."""
    narrow = invert(_synth(10.0, gen_sd_deg=8.0))
    wide = invert(_synth(10.0, gen_sd_deg=8.0, wind_dir_sd_deg=[8.0] * 12))
    assert narrow.rate_kg_h != wide.rate_kg_h
    assert narrow.model_dump() != wide.model_dump()


# --- (g) wind_dir_sd_deg validation ------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        [8.0] * 11,
        [8.0] * 13,
        [-1.0] + [8.0] * 11,
        [math.inf] + [8.0] * 11,
        [-math.inf] + [8.0] * 11,
        [math.nan] + [8.0] * 11,
    ],
)
def test_invalid_wind_dir_sd_is_rejected(bad: list[float]) -> None:
    """Wrong length, a negative or infinite value, or NaN where the direction is known: error."""
    with pytest.raises(ValueError, match="wind_dir_sd_deg"):
        _synth(wind_dir_sd_deg=bad)


def test_nan_wind_dir_sd_is_allowed_where_the_direction_is_nan() -> None:
    """NaN spread is accepted for a window whose direction is also NaN; that window is unused."""
    sd = [math.nan] + [8.0] * 11
    inp = _synth(wind_dir_sd_deg=sd, unknown_direction=0)
    assert invert(inp).windows_used == 11


# --- (h) recovery with a known spread -----------------------------------------------------------


def test_recovers_source_and_rate_when_the_spread_is_given() -> None:
    """Data made with an 8 degree spread are inverted with the same spread given per window.

    12 windows, 10 kg/h from VS-250.tip: the candidate is the conclusive top and the median
    rate is within a factor of two of the truth.
    """
    r = invert(_synth(10.0, gen_sd_deg=8.0, wind_dir_sd_deg=[8.0] * 12))
    assert r.top_id == "VS-250.tip"
    assert r.inconclusive is False and r.reason is None
    assert r.rate_kg_h is not None and 5.0 <= r.rate_kg_h <= 20.0
