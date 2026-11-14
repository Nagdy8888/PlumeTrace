"""Edge cases of the scenario runner: weather length, draw order, determinism, events."""

from datetime import UTC
from typing import Any

import numpy as np
import pytest

from plumetrace.engineering.detection import DetectionConfig
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import DT_S, run_scenario
from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    FaultSpec,
    InstrumentEffectSpec,
    ScenarioDefinition,
    SourceSpec,
)
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()
N_HOURS = len(SNAP.hours)


def _defn(**kw: Any) -> ScenarioDefinition:
    base: dict[str, Any] = dict(
        id="s9_test",
        title="Test",
        seed=3,
        weather_offset_h=30,
        duration_h=3,
        expected=ExpectedOutcome(triage="leak"),
    )
    base.update(kw)
    return ScenarioDefinition(**base)


def test_too_long_scenario_names_the_scenario_and_the_hours_needed() -> None:
    """A scenario past the snapshot end fails naming its id and the hours it needs."""
    d = _defn(id="s9_long_one", weather_offset_h=160, duration_h=12)
    with pytest.raises(ValueError, match=r"s9_long_one needs 173 weather hours.*has 168"):
        run_scenario(d, SPEC, SNAP)


def test_weather_boundary_is_exact() -> None:
    """Offset + duration + 1 equal to the snapshot length runs; one more hour fails."""
    ok = _defn(weather_offset_h=N_HOURS - 4, duration_h=3)
    assert run_scenario(ok, SPEC, SNAP).series.ppm.shape[0] == 1080
    with pytest.raises(ValueError, match="need"):
        run_scenario(_defn(weather_offset_h=N_HOURS - 3, duration_h=3), SPEC, SNAP)


def test_unknown_fault_sensor_is_a_value_error_naming_it() -> None:
    """A fault on a sensor that does not exist fails clearly."""
    d = _defn(faults=[FaultSpec(sensor_id="AT-999", drift_ppm_per_h=0.5, start_s=0.0)])
    with pytest.raises(ValueError, match="AT-999"):
        run_scenario(d, SPEC, SNAP)


def test_non_emission_anchor_is_unknown() -> None:
    """Only emission-point anchors are valid; an equipment tag or a made-up anchor is not."""
    for anchor in ("VS-250", "K-201.nothing", ""):
        d = _defn(sources=[SourceSpec(anchor_id=anchor, rate_kg_h=1.0, start_s=0.0)])
        with pytest.raises(KeyError, match="unknown anchor"):
            run_scenario(d, SPEC, SNAP)


def test_same_seed_same_everything_other_seed_differs() -> None:
    """Seed reproducibility covers readings, instruments, winds and events."""
    kw: dict[str, Any] = dict(
        faults=[FaultSpec(sensor_id="AT-106", drift_ppm_per_h=0.6, start_s=1800.0)],
        instrument_effects=[
            InstrumentEffectSpec(tag="FT-250", kind="offset", value=4.0, start_s=0)
        ],
    )
    a, b = run_scenario(_defn(**kw), SPEC, SNAP), run_scenario(_defn(**kw), SPEC, SNAP)
    other = run_scenario(_defn(seed=4, **kw), SPEC, SNAP)
    assert all(np.array_equal(a.instruments[k], b.instruments[k]) for k in a.instruments)
    assert np.array_equal(a.window_wind_from_deg, b.window_wind_from_deg)
    assert a.events == b.events
    assert not np.array_equal(a.series.ppm, other.series.ppm)
    assert not np.array_equal(a.instruments["FT-250"], other.instruments["FT-250"])


def test_instruments_use_the_same_generator_after_the_sensors() -> None:
    """The sensor draw count does not depend on the sources, so the instruments are unchanged."""
    quiet = run_scenario(_defn(), SPEC, SNAP)
    leak = run_scenario(
        _defn(sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=20.0, start_s=0.0)]),
        SPEC,
        SNAP,
    )
    assert all(np.array_equal(quiet.instruments[k], leak.instruments[k]) for k in quiet.instruments)
    assert not np.array_equal(quiet.series.ppm, leak.series.ppm)


def test_instrument_effects_are_applied_in_the_given_order() -> None:
    """Overlapping effects on one tag are applied in order: an offset after a set adds to it."""
    base = run_scenario(_defn(), SPEC, SNAP).instruments["TT-202P"]
    set_then_offset = [
        InstrumentEffectSpec(tag="TT-202P", kind="set", value=100.0, start_s=0.0),
        InstrumentEffectSpec(tag="TT-202P", kind="offset", value=5.0, start_s=0.0),
    ]
    out = run_scenario(_defn(instrument_effects=set_then_offset), SPEC, SNAP)
    delta = out.instruments["TT-202P"] - base
    assert np.allclose(delta, 25.0)  # (100 - 80) set, then +5: noise identical, mean 80 -> 105


def test_run_arrays_are_consistent_and_time_is_utc() -> None:
    """Window arrays have one entry per complete window; the start is a UTC time."""
    run = run_scenario(_defn(duration_h=2), SPEC, SNAP)
    assert DT_S == 10.0 and run.series.times_s[1] - run.series.times_s[0] == DT_S
    assert run.window_start_s.tolist() == [600.0 * k for k in range(12)]
    for arr in (run.window_wind_speed_m_s, run.window_wind_from_deg):
        assert arr.shape == (12,)
    assert len(run.window_stability) == 12 and len(run.series.stability) == 720
    assert run.sim_start_utc.tzinfo is UTC or run.sim_start_utc.utcoffset().total_seconds() == 0
    assert [s.id for s in run.sensors] == sorted(s.id for s in run.sensors) and len(
        run.sensors
    ) == 8


def test_sources_and_effects_are_active_inside_their_windows_only() -> None:
    """A source that ends early leaves the later windows at background; an end_s is exclusive."""
    d = _defn(
        sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=60.0, start_s=0.0, end_s=1200.0)]
    )
    run = run_scenario(d, SPEC, SNAP)
    quiet = run_scenario(_defn(), SPEC, SNAP)
    # same seed, same noise: the series differ exactly where the source emitted
    differs = np.abs(run.series.ppm - quiet.series.ppm).max(axis=1) > 0.0
    assert differs[:120].any()
    assert not differs[120:].any()


def test_a_zero_rate_source_changes_nothing() -> None:
    """Rate 0 emits nothing: same readings and no events."""
    quiet = run_scenario(_defn(), SPEC, SNAP)
    zero = run_scenario(
        _defn(sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=0.0, start_s=0.0)]), SPEC, SNAP
    )
    assert np.array_equal(quiet.series.ppm, zero.series.ppm) and zero.events == []


def test_one_event_per_sensor_inside_the_refractory_period() -> None:
    """A drift that keeps rising never gives two events for one sensor within the refractory time.

    Phase 3 README review focus 3: detection holds a sensor for ``refractory_windows`` after an
    event, so two events of one sensor are always more than that many windows apart.
    """
    drifting = _defn(
        duration_h=8,
        faults=[FaultSpec(sensor_id="AT-106", drift_ppm_per_h=6.0, start_s=1800.0)],
    )
    run = run_scenario(drifting, SPEC, SNAP)
    refractory = DetectionConfig().refractory_windows
    by_sensor: dict[str, list[int]] = {}
    for event in run.events:
        by_sensor.setdefault(event.sensor_id, []).append(event.window_index)
    assert by_sensor, "the strong drift must raise at least one event"
    for index in by_sensor.values():
        assert all(b - a > refractory for a, b in zip(index, index[1:], strict=False))
    assert [e.window_index for e in run.events] == sorted(e.window_index for e in run.events)
