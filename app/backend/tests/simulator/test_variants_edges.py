"""Edge cases of the variant generator: ranges, determinism, distractors, re-validation."""

import math
from typing import Any

import pytest
from pydantic import ValidationError

from plumetrace.simulator.scenario import ExpectedOutcome, ScenarioDefinition, SourceSpec
from plumetrace.simulator.scenarios import SCENARIOS, get_scenario
from plumetrace.simulator.variants import (
    DISTRACTOR_LOG,
    RATE_SCALE_RANGE,
    SNAPSHOT_HOURS,
    TIME_SHIFT_RANGE_S,
    VARIANT_SEED,
    generate_variants,
)


def _base(**kw: Any) -> ScenarioDefinition:
    fields: dict[str, Any] = dict(
        id="s9_test",
        title="Test",
        seed=3,
        weather_offset_h=0,
        duration_h=3,
        expected=ExpectedOutcome(triage="leak"),
    )
    fields.update(kw)
    return ScenarioDefinition(**fields)


def test_family_seed_is_the_task_value() -> None:
    """The default family seed is the Task 6 value, kept apart from the final-evaluation seeds."""
    assert VARIANT_SEED == 20261120


def test_distractor_log_has_the_six_plan_entries() -> None:
    """Six entries, all at t_s = 0, with the plan's kinds and tags."""
    assert [(e.kind, e.tag) for e in DISTRACTOR_LOG] == [
        ("shift_note", None),
        ("maintenance", "E-232"),
        ("gauging", "TK-401"),
        ("calibration", "AT-102"),
        ("shift_note", None),
        ("maintenance", "FG-501"),
    ]
    assert all(e.t_s == 0.0 for e in DISTRACTOR_LOG)


def test_other_seed_gives_other_variants() -> None:
    """A different family seed changes the variants."""
    base = get_scenario("s1_rod_packing")
    assert generate_variants(base, seed=7) != generate_variants(base, seed=8)
    assert generate_variants(base, seed=7) == generate_variants(base, seed=7)


def test_family_seed_is_mixed_with_the_base_id() -> None:
    """Two scenarios with the same seed do not share their random draws."""
    a = generate_variants(get_scenario("s1_rod_packing"), seed=5)
    b = generate_variants(get_scenario("s5_sensor_drift"), seed=5)
    assert [v.weather_offset_h for v in a] != [v.weather_offset_h for v in b]


def test_first_n_variants_do_not_depend_on_n() -> None:
    """Asking for fewer variants gives a prefix of the longer family."""
    base = get_scenario("s4_planned_blowdown")
    assert generate_variants(base, n=5) == generate_variants(base, n=20)[:5]


def test_zero_variants_and_negative_count() -> None:
    """Zero variants give an empty list; a negative count is refused."""
    base = get_scenario("s1_rod_packing")
    assert generate_variants(base, n=0) == []
    with pytest.raises(ValueError, match="n must be >= 0"):
        generate_variants(base, n=-1)


@pytest.mark.parametrize("scenario_id", sorted(SCENARIOS))
def test_every_variant_is_valid_and_keys_are_unique(scenario_id: str) -> None:
    """Each variant passes the scenario rules, keeps the base id and has a unique key."""
    base = get_scenario(scenario_id)
    variants = generate_variants(base)
    assert len({(v.id, v.variant_index) for v in variants}) == 20
    for v in variants:
        assert ScenarioDefinition.model_validate(v.model_dump()) == v
        assert v.id == base.id
        assert v.title == base.title
        assert v.duration_h == base.duration_h
        assert v.seed >= 0
        assert v.expected.triage == base.expected.triage
        assert v.expected.top_candidate == base.expected.top_candidate


def test_rate_scale_and_time_shift_stay_in_their_ranges() -> None:
    """Rate and expected interval scale inside the range; times move by one shared shift."""
    base = get_scenario("s1_rod_packing")
    lo, hi = RATE_SCALE_RANGE
    for v in generate_variants(base):
        scale = v.sources[0].rate_kg_h / base.sources[0].rate_kg_h
        assert lo <= scale <= hi
        assert v.expected.rate_max_kg_h == pytest.approx(30.0 * scale)
        assert v.expected.rate_min_kg_h is not None and v.expected.rate_max_kg_h is not None
        assert v.expected.rate_min_kg_h <= v.expected.rate_max_kg_h
        shift = v.sources[0].start_s - base.sources[0].start_s
        assert TIME_SHIFT_RANGE_S[0] <= shift <= TIME_SHIFT_RANGE_S[1]
        for b, e in zip(base.instrument_effects, v.instrument_effects, strict=True):
            assert e.start_s - b.start_s == pytest.approx(shift)
            assert (e.end_s == math.inf) == (b.end_s == math.inf)
            if b.tag != "FT-250":
                assert e.value == b.value


def test_infinite_source_end_stays_infinite_and_finite_end_moves() -> None:
    """S1 leak never ends; the S4 blowdown keeps its 900 s length."""
    assert all(
        v.sources[0].end_s == math.inf for v in generate_variants(get_scenario("s1_rod_packing"))
    )
    for v in generate_variants(get_scenario("s4_planned_blowdown")):
        assert v.sources[0].end_s - v.sources[0].start_s == pytest.approx(900.0)


def test_s5_has_no_rate_and_the_fault_moves() -> None:
    """S5 has no expected rate to scale; the drift start moves inside 1800 s."""
    base = get_scenario("s5_sensor_drift")
    for v in generate_variants(base):
        assert v.expected.rate_min_kg_h is None and v.expected.rate_max_kg_h is None
        assert abs(v.faults[0].start_s - base.faults[0].start_s) <= 1800.0
        assert v.faults[0].drift_ppm_per_h == base.faults[0].drift_ppm_per_h


def test_distractors_from_the_list_and_base_entries_move_with_the_shift() -> None:
    """0 to 2 distractors drawn from the list; every base entry moves by the shift (clamped)."""
    base = get_scenario("s1_rod_packing")
    texts = {e.text for e in DISTRACTOR_LOG}
    base_texts = {e.text for e in base.log}
    counts = set()
    for v in generate_variants(base):
        shift = v.sources[0].start_s - base.sources[0].start_s
        moved = {e.text: e.t_s for e in v.log if e.text in base_texts}
        assert moved == pytest.approx(
            {e.text: min(max(0.0, e.t_s + shift), v.duration_h * 3600.0) for e in base.log}
        )
        extra = [e for e in v.log if e.text not in base_texts]
        counts.add(len(extra))
        assert all(e.text in texts for e in extra)
        assert len({e.text for e in extra}) == len(extra)
        assert all(0.0 <= e.t_s <= v.duration_h * 3600.0 for e in v.log)
    assert counts <= {0, 1, 2} and len(counts) > 1


def test_s4_permit_lead_and_restart_lag_hold_for_50_seeds_x_20_variants() -> None:
    """S4 permit stays 600 s before the blowdown and the restart line 900 s after it ends."""
    base = get_scenario("s4_planned_blowdown")
    for seed in range(50):
        for v in generate_variants(base, seed=seed):
            src = v.sources[0]
            permit = next(e for e in v.log if e.kind == "permit")
            restart = next(e for e in v.log if e.kind == "maintenance" and e.tag == "K-201")
            assert permit.t_s == pytest.approx(src.start_s - 600.0)
            assert restart.t_s == pytest.approx(src.end_s + 900.0)


def test_s4_base_permit_text_matches_the_source_lead_and_duration() -> None:
    """The permit text states the 600 s lead and 900 s duration the source definition has."""
    base = get_scenario("s4_planned_blowdown")
    src = base.sources[0]
    permit = next(e for e in base.log if e.kind == "permit")
    assert src.start_s - permit.t_s == 600.0 and src.end_s - src.start_s == 900.0
    assert "venting starts 10 minutes after this entry" in permit.text
    assert "lasts about 15 minutes" in permit.text


@pytest.mark.parametrize(
    ("scenario_id", "start"), [("s1_rod_packing", "source"), ("s5_sensor_drift", "fault")]
)
def test_s1_and_s5_base_entries_keep_their_offset_to_the_event(
    scenario_id: str, start: str
) -> None:
    """Base log entries keep their offset to the source or fault start (unless clamped)."""
    base = get_scenario(scenario_id)
    ref = base.sources[0].start_s if start == "source" else base.faults[0].start_s
    for seed in range(50):
        for v in generate_variants(base, seed=seed):
            vref = v.sources[0].start_s if start == "source" else v.faults[0].start_s
            moved = {e.text: e.t_s for e in v.log}
            for e in base.log:
                t = moved[e.text]
                if 0.0 < t < v.duration_h * 3600.0:
                    assert t - vref == pytest.approx(e.t_s - ref)


def test_permit_stays_inside_the_scenario() -> None:
    """A permit entry is clamped into [0, duration]."""
    for v in generate_variants(get_scenario("s4_planned_blowdown")):
        permit = next(e for e in v.log if e.kind == "permit")
        assert 0.0 <= permit.t_s <= v.duration_h * 3600.0


def test_variant_pushed_past_the_end_is_rejected() -> None:
    """A start that the shift moves to or past the scenario end fails re-validation."""
    base = _base(sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=5.0, start_s=10799.0)])
    with pytest.raises(ValidationError, match="inside"):
        generate_variants(base)


def test_variant_with_a_collapsed_source_window_is_rejected() -> None:
    """A window clamped to zero length at t = 0 fails re-validation, not silently."""
    base = _base(
        sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=5.0, start_s=0.0, end_s=10.0)]
    )
    with pytest.raises(ValidationError, match="end_s must be after start_s"):
        generate_variants(base)


def test_weather_window_for_the_longest_scenario_fits() -> None:
    """A 24 h scenario still gets an offset that fits the snapshot."""
    for v in generate_variants(_base(duration_h=24)):
        assert 0 <= v.weather_offset_h <= SNAPSHOT_HOURS - 24 - 1
