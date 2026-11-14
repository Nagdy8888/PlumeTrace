"""Tests for the scenario model and runner (real weather snapshot, truth physics)."""

import numpy as np
import pytest
from pydantic import ValidationError

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import run_scenario, site_center_xy
from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    FaultSpec,
    LogEntry,
    ScenarioDefinition,
    SourceSpec,
)
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def _defn(**kw: object) -> ScenarioDefinition:
    base: dict[str, object] = dict(
        id="s9_test",
        title="Test",
        seed=3,
        weather_offset_h=30,
        duration_h=3,
        expected=ExpectedOutcome(triage="leak"),
    )
    base.update(kw)
    return ScenarioDefinition(**base)


def test_site_center() -> None:
    """The KS-07 site centre is (100, 75)."""
    assert site_center_xy(SPEC) == (100.0, 75.0)


def test_run_shapes_and_determinism() -> None:
    """3 h at 10 s -> 1080 samples, 18 windows; identical for the same seed."""
    d = _defn(sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=20.0, start_s=3600.0)])
    a, b = run_scenario(d, SPEC, SNAP), run_scenario(d, SPEC, SNAP)
    assert a.series.ppm.shape == (1080, 8)
    assert a.window_means_ppm.shape == (18, 8)
    assert len(a.window_stability) == 18
    assert np.array_equal(a.series.ppm, b.series.ppm)
    assert a.sim_start_utc.isoformat().startswith("2025-07-15T06:00:00")
    assert set(a.instruments) >= {"FT-250", "TT-202P"}


def test_quiet_station_raises_no_events() -> None:
    """No sources and no faults -> no detection events."""
    assert run_scenario(_defn(), SPEC, SNAP).events == []


def test_drifting_sensor_is_detected() -> None:
    """A 0.6 ppm/h drift on AT-106 is detected on AT-106 only."""
    run = run_scenario(
        _defn(faults=[FaultSpec(sensor_id="AT-106", drift_ppm_per_h=0.6, start_s=1800.0)]),
        SPEC,
        SNAP,
    )
    assert {e.sensor_id for e in run.events} == {"AT-106"}


def test_unknown_anchor_and_short_weather() -> None:
    """Bad anchors and scenarios longer than the snapshot fail clearly."""
    with pytest.raises(KeyError, match="NOPE"):
        run_scenario(
            _defn(sources=[SourceSpec(anchor_id="NOPE", rate_kg_h=1.0, start_s=0.0)]), SPEC, SNAP
        )
    with pytest.raises(ValueError, match="need"):
        run_scenario(_defn(weather_offset_h=160, duration_h=12), SPEC, SNAP)


def test_log_must_be_sorted() -> None:
    """Unsorted log entries are rejected."""
    with pytest.raises(ValidationError, match="sorted"):
        _defn(
            log=[
                LogEntry(t_s=100.0, kind="shift_note", text="b"),
                LogEntry(t_s=50.0, kind="shift_note", text="a"),
            ]
        )
