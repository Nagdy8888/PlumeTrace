"""Run one benchmark case: truth-model sensor data, window means, then the inversion."""

from collections import Counter
from dataclasses import dataclass

import numpy as np

from benchmark.cases import CASE_HOURS, DT_S, BenchmarkCase
from plumetrace.engineering.averaging import (
    WINDOW_S,
    window_direction_sd_deg,
    window_means,
    window_mode_class,
    window_wind,
)
from plumetrace.engineering.inversion import InversionInput, InversionResult, invert
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import simulate_sensors
from plumetrace.engineering.truth_weather import synthetic_hourly_weather
from plumetrace.facility.candidates import emission_candidates, methane_sensors
from plumetrace.facility.obstacles import facility_obstacles
from plumetrace.facility.spec import FacilitySpec

_BACKGROUND_PERCENTILE = 5


@dataclass(frozen=True)
class CaseResult:
    """A case and what the inversion made of it.

    Attributes:
        case: The benchmark case.
        result: The inversion result.
        dominant_stability: Most frequent stability class over the case windows.
        true_rate_kg_h: The true rate in kg/h, or None for a no-leak case.
    """

    case: BenchmarkCase
    result: InversionResult
    dominant_stability: StabilityClass
    true_rate_kg_h: float | None


def _mode(classes: list[StabilityClass]) -> StabilityClass:
    """Most frequent class; ties go to the alphabetically first class."""
    counts = Counter(classes)
    return min(counts, key=lambda c: (-counts[c], c.value))


def window_stability(
    classes: list[StabilityClass], steps_per_window: int, n_windows: int
) -> list[StabilityClass]:
    """Most frequent stability class in each window.

    Args:
        classes: One class per time step.
        steps_per_window: Time steps in one window (> 0).
        n_windows: Number of complete windows to return.

    Returns:
        One class per window; ties go to the alphabetically first class.
    """
    return window_mode_class(classes, steps_per_window, n_windows)


def run_case(case: BenchmarkCase, spec: FacilitySpec, *, meander: bool = False) -> CaseResult:
    """Simulate one case with the truth model and locate the source with the inversion.

    The inversion uses its default Briggs rural coefficients and sees the background-subtracted
    10-minute means only; the background is the 5th percentile of each sensor window means.
    With ``meander`` it also gets, per window, the circular standard deviation of the 10 s
    wind-direction series (``window_direction_sd_deg``), measured from the data, not the truth
    model's setting. Both settings simulate identical data: the generator is seeded by the case.

    Args:
        case: The case to run.
        spec: The facility spec.
        meander: Give the inversion the measured within-window direction spread.

    Returns:
        The case, the inversion result, the dominant stability and the true rate.
    """
    rng = np.random.default_rng(case.seed)
    weather = synthetic_hourly_weather(CASE_HOURS + 1, case.start_hour_of_day, rng)
    sensors = methane_sensors(spec)
    series = simulate_sensors(
        [case.source] if case.source else [],
        sensors,
        weather,
        DT_S,
        CASE_HOURS * 3600,
        rng,
        spec.site.ambient_pressure_pa,
        obstacles=facility_obstacles(spec),
    )
    starts, means = window_means(series.times_s, series.ppm)
    speed, direction = window_wind(series.times_s, series.wind_speed_m_s, series.wind_from_deg)
    stab = window_stability(series.stability, int(WINDOW_S / DT_S), len(starts))
    background = np.nanpercentile(means, _BACKGROUND_PERCENTILE, axis=0)
    spread = window_direction_sd_deg(series.times_s, series.wind_from_deg) if meander else None
    result = invert(
        InversionInput(
            candidates=emission_candidates(spec),
            sensors=sensors,
            observed_ppm_above_bg=(means - background).tolist(),
            wind_speed_m_s=speed.tolist(),
            wind_from_deg=direction.tolist(),
            stability=stab,
            temp_k=float(np.mean(series.temp_k)),
            pressure_pa=spec.site.ambient_pressure_pa,
            wind_dir_sd_deg=None if spread is None else spread.tolist(),
        )
    )
    true_rate = case.source.rate_kg_h if case.source else None
    return CaseResult(case, result, _mode(stab), true_rate)


def run_all(
    cases: list[BenchmarkCase], spec: FacilitySpec, *, meander: bool = False
) -> list[CaseResult]:
    """Run every case in order.

    Args:
        cases: The cases.
        spec: The facility spec.
        meander: Run with the measured direction spread, see ``run_case``.

    Returns:
        One result per case, in the same order.
    """
    return [run_case(c, spec, meander=meander) for c in cases]
