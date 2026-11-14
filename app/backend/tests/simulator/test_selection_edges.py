"""Edge cases of the window-selection criteria (own tests, beside the plan tests)."""

from dataclasses import replace

import numpy as np
import pytest

from plumetrace.engineering.averaging import window_direction_sd_deg
from plumetrace.engineering.detection import DetectionEvent
from plumetrace.engineering.inversion import InversionInput, InversionResult
from plumetrace.facility.loader import load_facility
from plumetrace.simulator import selection
from plumetrace.simulator.runner import ScenarioRun, run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.selection import (
    first_event_after,
    s1_passes,
    s4_passes,
    s5_passes,
)
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()
S1_RUN = run_scenario(get_scenario("s1_rod_packing"), SPEC, SNAP)


def _event(sensor: str, window: int) -> DetectionEvent:
    return DetectionEvent(
        sensor_id=sensor,
        window_index=window,
        window_start_s=600.0 * window,
        mean_ppm=3.0,
        baseline_ppm=2.0,
        cusum=5.5,
        downwind_of_site=True,
    )


def _with_events(run: ScenarioRun, *events: DetectionEvent) -> ScenarioRun:
    return replace(run, events=list(events))


class _FakeInversion:
    """Replaces ``selection.invert``: records the input and answers with a chosen result."""

    def __init__(self, top_id: str = "VS-250.tip", inconclusive: bool = False) -> None:
        self.inputs: list[InversionInput] = []
        self._result = InversionResult(
            ranked=[],
            top_id=top_id,
            top_probability=0.9,
            rate_kg_h=None,
            rate_p05_kg_h=None,
            rate_p95_kg_h=None,
            rate_at_grid_edge=False,
            inconclusive=inconclusive,
            reason="calm" if inconclusive else None,
            windows_used=5,
        )

    def __call__(self, inp: InversionInput) -> InversionResult:
        self.inputs.append(inp)
        return self._result


def _patch(
    monkeypatch: pytest.MonkeyPatch, top_id: str = "VS-250.tip", inconclusive: bool = False
) -> _FakeInversion:
    fake = _FakeInversion(top_id, inconclusive)
    monkeypatch.setattr(selection, "invert", fake)
    return fake


def test_first_event_after_is_inclusive_and_sorted() -> None:
    """The earliest event at or after t wins; ties go to the lower sensor id; none gives None."""
    run = _with_events(S1_RUN, _event("AT-105", 14), _event("AT-102", 14), _event("AT-101", 20))
    assert first_event_after(run, 7200.0) is not None
    found = first_event_after(run, 8400.0)
    assert found is not None
    assert (found.sensor_id, found.window_index) == ("AT-102", 14)
    assert first_event_after(run, 8400.1) == run.events[2]
    assert first_event_after(run, 12001.0) is None
    assert first_event_after(_with_events(S1_RUN), 0.0) is None


def test_s1_needs_an_event_in_the_first_90_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    """No event, an event before the leak, or one later than 7200 + 5400 s fails (a)."""
    _patch(monkeypatch)
    assert not s1_passes(_with_events(S1_RUN), SPEC)
    assert not s1_passes(_with_events(S1_RUN, _event("AT-101", 5)), SPEC)
    assert not s1_passes(_with_events(S1_RUN, _event("AT-101", 22)), SPEC)
    assert s1_passes(_with_events(S1_RUN, _event("AT-101", 21)), SPEC)  # 12600 s: included
    assert s1_passes(_with_events(S1_RUN, _event("AT-101", 12)), SPEC)  # 7200 s: included


def test_s1_wind_criterion(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mean over windows 12-35 must be at least 2.0 m/s; other windows do not count."""
    _patch(monkeypatch)
    run = _with_events(S1_RUN, _event("AT-101", 13))

    def with_speed(inside: float, outside: float) -> ScenarioRun:
        speed = np.full(36, outside)
        speed[12:36] = inside
        return replace(run, window_wind_speed_m_s=speed)

    assert s1_passes(with_speed(2.0, 0.0), SPEC)
    assert not s1_passes(with_speed(1.99, 9.0), SPEC)
    assert not s1_passes(replace(run, window_wind_speed_m_s=np.full(35, 5.0)), SPEC)
    last = np.full(36, 1.9)  # window 35 is part of the mean: (23 * 1.9 + 5.0) / 24 > 2.0
    last[35] = 5.0
    assert s1_passes(replace(run, window_wind_speed_m_s=last), SPEC)


def test_s1_inversion_gets_the_direction_spread_aligned_to_its_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows 12 to event + 3, background before 12, and one spread value per used window."""
    fake = _patch(monkeypatch)
    assert s1_passes(_with_events(S1_RUN, _event("AT-101", 13)), SPEC)
    inp = fake.inputs[0]
    spread = window_direction_sd_deg(S1_RUN.series.times_s, S1_RUN.series.wind_from_deg)
    means = S1_RUN.window_means_ppm
    background = np.nanpercentile(means[:12], 5, axis=0)
    assert inp.wind_dir_sd_deg == spread[12:17].tolist()  # windows 12..16 (event 13 + 3)
    assert len(inp.observed_ppm_above_bg) == 5
    assert inp.wind_from_deg == S1_RUN.window_wind_from_deg[12:17].tolist()
    assert np.allclose(inp.observed_ppm_above_bg, means[12:17] - background)


def test_s1_window_range_is_cut_at_the_end_of_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """An event at window 21 uses windows 12 to 24, never past the run."""
    fake = _patch(monkeypatch)
    assert s1_passes(_with_events(S1_RUN, _event("AT-101", 21)), SPEC)
    assert len(fake.inputs[0].observed_ppm_above_bg) == 13


@pytest.mark.parametrize(("top", "inconclusive"), [("K-203.packing", False), ("VS-250.tip", True)])
def test_s1_needs_a_conclusive_vs250_result(
    monkeypatch: pytest.MonkeyPatch, top: str, inconclusive: bool
) -> None:
    """A different top candidate, or an inconclusive result, fails (c)."""
    _patch(monkeypatch, top_id=top, inconclusive=inconclusive)
    assert not s1_passes(_with_events(S1_RUN, _event("AT-101", 13)), SPEC)


def test_s1_infinite_direction_spread_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A window whose directions cancel exactly has an infinite spread: a clear ValueError."""
    inf_spread = np.full(36, np.inf)
    monkeypatch.setattr(selection, "window_direction_sd_deg", lambda *_a, **_k: inf_spread)
    with pytest.raises(ValueError, match="wind_dir_sd_deg"):
        s1_passes(_with_events(S1_RUN, _event("AT-101", 13)), SPEC)


def test_s4_window_edges() -> None:
    """An event in [7200, 9300] counts; one before 7200 or only later than 9300 fails."""
    run = S1_RUN
    assert not s4_passes(_with_events(run))
    assert s4_passes(_with_events(run, _event("AT-102", 12)))
    assert s4_passes(_with_events(run, _event("AT-102", 15)))  # 9000 s
    assert not s4_passes(_with_events(run, _event("AT-102", 16)))  # 9600 s
    assert not s4_passes(_with_events(run, _event("AT-102", 11), _event("AT-102", 13)))
    assert not s4_passes(_with_events(run, _event("AT-102", 3)))


def test_s5_only_the_drifting_sensor() -> None:
    """At least one AT-106 event and no other sensor."""
    assert not s5_passes(_with_events(S1_RUN))
    assert s5_passes(_with_events(S1_RUN, _event("AT-106", 13), _event("AT-106", 24)))
    assert not s5_passes(_with_events(S1_RUN, _event("AT-106", 13), _event("AT-101", 14)))
    assert not s5_passes(_with_events(S1_RUN, _event("AT-101", 14)))
