"""Edge cases of the scenario model: every invalid number or window is rejected on construction."""

from typing import Any

import pytest
from pydantic import ValidationError

from plumetrace.simulator.instruments import InstrumentEffect
from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    FaultSpec,
    InstrumentEffectSpec,
    LogEntry,
    ScenarioDefinition,
    SourceSpec,
)

INF = float("inf")
NAN = float("nan")


def _defn(**kw: Any) -> ScenarioDefinition:
    base: dict[str, Any] = dict(
        id="s9_test",
        title="Test",
        seed=3,
        weather_offset_h=0,
        duration_h=3,
        expected=ExpectedOutcome(triage="leak"),
    )
    base.update(kw)
    return ScenarioDefinition(**base)


@pytest.mark.parametrize(
    "kw",
    [
        dict(rate_kg_h=INF, start_s=0.0),
        dict(rate_kg_h=NAN, start_s=0.0),
        dict(rate_kg_h=-1.0, start_s=0.0),
        dict(rate_kg_h=1.0, start_s=INF),
        dict(rate_kg_h=1.0, start_s=-1.0),
        dict(rate_kg_h=1.0, start_s=100.0, end_s=100.0),
        dict(rate_kg_h=1.0, start_s=100.0, end_s=50.0),
        dict(rate_kg_h=1.0, start_s=100.0, end_s=NAN),
    ],
)
def test_source_spec_rejects_bad_numbers(kw: dict[str, float]) -> None:
    """Non-finite, negative or inverted source numbers raise a validation error."""
    with pytest.raises(ValidationError):
        SourceSpec(anchor_id="VS-250.tip", **kw)


def test_source_spec_accepts_zero_rate_and_open_end_and_is_frozen() -> None:
    """A zero rate and an infinite end are valid; the model is frozen and rejects extras."""
    s: Any = SourceSpec(anchor_id="VS-250.tip", rate_kg_h=0.0, start_s=0.0)
    assert s.end_s == INF
    with pytest.raises(ValidationError):
        s.rate_kg_h = 1.0
    extra: dict[str, Any] = dict(anchor_id="a", rate_kg_h=1.0, start_s=0.0, colour="red")
    with pytest.raises(ValidationError):
        SourceSpec(**extra)


@pytest.mark.parametrize(
    "kw",
    [
        dict(drift_ppm_per_h=INF, start_s=0.0),
        dict(drift_ppm_per_h=NAN, start_s=0.0),
        dict(drift_ppm_per_h=0.5, start_s=INF),
        dict(drift_ppm_per_h=0.5, start_s=-1.0),
    ],
)
def test_fault_spec_rejects_bad_numbers(kw: dict[str, float]) -> None:
    """A non-finite drift or start, or a negative start, is rejected."""
    with pytest.raises(ValidationError):
        FaultSpec(sensor_id="AT-106", **kw)


def test_fault_spec_accepts_negative_drift() -> None:
    """Drift may be negative."""
    assert FaultSpec(sensor_id="AT-106", drift_ppm_per_h=-0.4, start_s=0.0).drift_ppm_per_h == -0.4


@pytest.mark.parametrize(
    "kw",
    [
        dict(tag="NOPE", kind="offset", value=1.0, start_s=0.0),
        dict(tag="FT-250", kind="multiply", value=1.0, start_s=0.0),
        dict(tag="FT-250", kind="offset", value=NAN, start_s=0.0),
        dict(tag="FT-250", kind="offset", value=INF, start_s=0.0),
        dict(tag="FT-250", kind="offset", value=1.0, start_s=INF),
        dict(tag="FT-250", kind="offset", value=1.0, start_s=10.0, end_s=10.0),
        dict(tag="FT-250", kind="offset", value=1.0, start_s=10.0, end_s=NAN),
        dict(tag="FT-250", kind="offset", value=1.0, start_s=0.0, ramp_s=-1.0),
        dict(tag="FT-250", kind="offset", value=1.0, start_s=0.0, ramp_s=INF),
    ],
)
def test_effect_spec_rejects_invalid_effects(kw: dict[str, Any]) -> None:
    """Unknown tag, bad kind, non-finite numbers, empty window or bad ramp are rejected."""
    with pytest.raises(ValidationError):
        InstrumentEffectSpec(**kw)


def test_effect_spec_to_effect_copies_every_field() -> None:
    """``to_effect`` gives the matching ``InstrumentEffect``."""
    spec = InstrumentEffectSpec(
        tag="TT-202P", kind="set", value=95.0, start_s=60.0, end_s=900.0, ramp_s=30.0
    )
    assert spec.to_effect() == InstrumentEffect("TT-202P", "set", 95.0, 60.0, 900.0, 30.0)


@pytest.mark.parametrize(
    "kw",
    [
        dict(t_s=INF, text="x"),
        dict(t_s=NAN, text="x"),
        dict(t_s=-1.0, text="x"),
        dict(t_s=0.0, text=""),
        dict(t_s=0.0, text="   "),
    ],
)
def test_log_entry_rejects_bad_time_or_blank_text(kw: dict[str, Any]) -> None:
    """A non-finite or negative time, or blank text, is rejected."""
    with pytest.raises(ValidationError):
        LogEntry(kind="shift_note", **kw)


@pytest.mark.parametrize(
    "kw",
    [
        dict(rate_min_kg_h=5.0),
        dict(rate_max_kg_h=5.0),
        dict(rate_min_kg_h=9.0, rate_max_kg_h=5.0),
        dict(rate_min_kg_h=-1.0, rate_max_kg_h=5.0),
        dict(rate_min_kg_h=1.0, rate_max_kg_h=INF),
        dict(rate_min_kg_h=NAN, rate_max_kg_h=5.0),
    ],
)
def test_expected_rate_is_an_interval_or_absent(kw: dict[str, float]) -> None:
    """A rate is stored only as a finite ``min <= max`` interval, never as one number."""
    with pytest.raises(ValidationError):
        ExpectedOutcome(triage="leak", **kw)


def test_expected_rate_interval_accepted() -> None:
    """A valid interval, and no rate at all, are accepted."""
    assert ExpectedOutcome(triage="leak", rate_min_kg_h=5.0, rate_max_kg_h=5.0).rule_ids == []
    assert ExpectedOutcome(triage="planned_venting").rate_min_kg_h is None


@pytest.mark.parametrize("bad_id", ["S1_x", "s1", "s1-x", "x1_leak", "s_1x", "s1_X", ""])
def test_scenario_id_pattern(bad_id: str) -> None:
    """Ids must match ``s<digits>_<lowercase words>``."""
    with pytest.raises(ValidationError):
        _defn(id=bad_id)


@pytest.mark.parametrize(
    "kw", [dict(duration_h=0), dict(duration_h=25), dict(weather_offset_h=-1), dict(seed=-1)]
)
def test_scenario_numbers_out_of_range(kw: dict[str, int]) -> None:
    """Duration 1-24 h, a non-negative offset and a non-negative seed."""
    with pytest.raises(ValidationError):
        _defn(**kw)


def test_everything_must_start_inside_the_scenario() -> None:
    """Sources, faults, effects start before the end; log entries at or before it."""
    end_s = 3 * 3600.0
    late_source = SourceSpec(anchor_id="VS-250.tip", rate_kg_h=1.0, start_s=end_s)
    late_fault = FaultSpec(sensor_id="AT-106", drift_ppm_per_h=0.5, start_s=end_s)
    late_effect = InstrumentEffectSpec(tag="FT-250", kind="offset", value=1.0, start_s=end_s)
    late_log = LogEntry(t_s=end_s + 1.0, kind="shift_note", text="late")
    for kw in (
        dict(sources=[late_source]),
        dict(faults=[late_fault]),
        dict(instrument_effects=[late_effect]),
        dict(log=[late_log]),
    ):
        with pytest.raises(ValidationError, match="duration"):
            _defn(**kw)
    assert _defn(log=[LogEntry(t_s=end_s, kind="shift_note", text="end")]).log[0].t_s == end_s


def test_equal_log_times_pass_and_empty_lists_are_valid() -> None:
    """Equal times keep their order and pass; empty sources, faults, effects and log are valid."""
    d = _defn(
        log=[
            LogEntry(t_s=5.0, kind="permit", text="a"),
            LogEntry(t_s=5.0, kind="gauging", text="b"),
        ]
    )
    assert [e.text for e in d.log] == ["a", "b"]
    q = _defn()
    assert q.sources == [] and q.faults == [] and q.instrument_effects == [] and q.log == []


def test_scenario_is_frozen_and_rejects_unknown_fields() -> None:
    """Frozen and ``extra="forbid"``."""
    d: Any = _defn()
    with pytest.raises(ValidationError):
        d.title = "other"
    with pytest.raises(ValidationError):
        _defn(colour="red")
