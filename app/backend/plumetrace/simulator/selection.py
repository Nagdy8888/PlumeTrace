"""Window-selection criteria for the MVP scenarios.

The weather window of each MVP scenario is not guessed: ``scripts/select_scenario_windows.py``
runs every candidate offset of the real weather snapshot and applies the criterion of its
scenario; the first passing offset is written into the scenario file. Pure simulation, no I/O.
The S1 criterion runs the adopted (meander-aware) inversion: it passes the within-window
direction spread of the run to ``InversionInput.wind_dir_sd_deg``.
"""

from typing import Final

import numpy as np

from plumetrace.engineering.averaging import window_direction_sd_deg
from plumetrace.engineering.detection import DetectionEvent
from plumetrace.engineering.inversion import InversionInput, invert
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.spec import FacilitySpec
from plumetrace.simulator.runner import ScenarioRun

# Every 2 h through the week; each scenario still needs duration_h + 1 hours (Task 5 values).
CANDIDATE_OFFSETS_H: Final = tuple(range(0, 161, 2))

# Task 5 values (Phase 3 plan), not from a cited source.
S1_LEAK_START_S: Final = 7200.0
S1_LATEST_EVENT_S: Final = S1_LEAK_START_S + 5400.0
S1_FIRST_WINDOW: Final = 12  # first window of the leak period, also the end of the background
S1_LAST_WIND_WINDOW: Final = 35
S1_MIN_MEAN_WIND_M_S: Final = 2.0
S1_AFTER_EVENT_WINDOWS: Final = 3
S4_VENT_START_S: Final = 7200.0
S4_LATEST_EVENT_S: Final = 8100.0 + 1200.0
S5_FAULTY_SENSOR: Final = "AT-106"
_BACKGROUND_PERCENTILE: Final = 5


def first_event_after(run: ScenarioRun, t_s: float) -> DetectionEvent | None:
    """Return the first detection event whose window starts at or after ``t_s``.

    Args:
        run: A scenario run.
        t_s: Time in scenario seconds.

    Returns:
        The earliest event with ``window_start_s >= t_s`` (ties by sensor id), or None.
    """
    later = [e for e in run.events if e.window_start_s >= t_s]
    return min(later, key=lambda e: (e.window_start_s, e.sensor_id), default=None)


def _s1_wind_ok(run: ScenarioRun) -> bool:
    """Mean window wind speed over windows 12 to 35 is at least 2 m/s (needs all 24 windows)."""
    speed = run.window_wind_speed_m_s
    if len(speed) <= S1_LAST_WIND_WINDOW:
        return False
    mean_m_s = float(np.mean(speed[S1_FIRST_WINDOW : S1_LAST_WIND_WINDOW + 1]))
    return mean_m_s >= S1_MIN_MEAN_WIND_M_S


def _s1_inversion_input(run: ScenarioRun, spec: FacilitySpec, stop: int) -> InversionInput:
    """Build the inversion input for windows ``[S1_FIRST_WINDOW, stop)`` of the run.

    The background is the 5th percentile of each sensor over the windows before the first
    one. The within-window direction spread is computed from the whole 10 s wind series and cut
    to the same windows (it has one value per complete window, like the other window arrays).
    """
    first = S1_FIRST_WINDOW
    means = run.window_means_ppm
    background = np.nanpercentile(means[:first], _BACKGROUND_PERCENTILE, axis=0)
    spread = window_direction_sd_deg(run.series.times_s, run.series.wind_from_deg)
    return InversionInput(
        candidates=emission_candidates(spec),
        sensors=run.sensors,
        observed_ppm_above_bg=(means[first:stop] - background).tolist(),
        wind_speed_m_s=run.window_wind_speed_m_s[first:stop].tolist(),
        wind_from_deg=run.window_wind_from_deg[first:stop].tolist(),
        stability=run.window_stability[first:stop],
        temp_k=float(np.mean(run.series.temp_k)),
        pressure_pa=spec.site.ambient_pressure_pa,
        wind_dir_sd_deg=spread[first:stop].tolist(),
    )


def s1_passes(run: ScenarioRun, spec: FacilitySpec) -> bool:
    """Say whether the S1 story works in this weather window.

    All three must hold: (a) a detection event on any methane sensor starts between the leak
    start (7200 s) and 5400 s later; (b) the mean window wind speed over windows 12 to 35 is at
    least 2.0 m/s; (c) the meander-aware inversion (Briggs rural, default constants) over windows
    12 to ``first_event.window_index + 3`` (both ends included), with the background taken before
    window 12, ranks ``VS-250.tip`` first and is not inconclusive.

    Args:
        run: A run of the S1 definition.
        spec: The facility spec.

    Returns:
        True when the window passes.

    Raises:
        ValueError: If the run has a window whose wind directions cancel exactly (an infinite
            spread, which the inversion input rejects).
    """
    event = first_event_after(run, S1_LEAK_START_S)
    if event is None or event.window_start_s > S1_LATEST_EVENT_S:
        return False
    if not _s1_wind_ok(run):
        return False
    stop = event.window_index + S1_AFTER_EVENT_WINDOWS + 1
    result = invert(_s1_inversion_input(run, spec, stop))
    return result.top_id == "VS-250.tip" and not result.inconclusive


def s4_passes(run: ScenarioRun) -> bool:
    """Say whether the S4 story works: detected during the blowdown, nothing before it.

    Args:
        run: A run of the S4 definition.

    Returns:
        True when an event starts between 7200 s and 9300 s and no event starts before 7200 s.
    """
    if any(e.window_start_s < S4_VENT_START_S for e in run.events):
        return False
    event = first_event_after(run, S4_VENT_START_S)
    return event is not None and event.window_start_s <= S4_LATEST_EVENT_S


def s5_passes(run: ScenarioRun) -> bool:
    """Say whether the S5 story works: only the drifting sensor raises events.

    Args:
        run: A run of the S5 definition.

    Returns:
        True when ``AT-106`` has at least one event and no other sensor has one.
    """
    sensors = {e.sensor_id for e in run.events}
    return S5_FAULTY_SENSOR in sensors and sensors == {S5_FAULTY_SENSOR}
