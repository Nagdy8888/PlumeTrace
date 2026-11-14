"""Tests for scenario variant generation."""

import pytest

from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.variants import generate_variants


def test_twenty_deterministic_variants() -> None:
    """Same base and seed -> the same 20 variants, indexed 0..19, base unchanged."""
    base = get_scenario("s1_rod_packing")
    a, b = generate_variants(base), generate_variants(base)
    assert a == b
    assert [v.variant_index for v in a] == list(range(20))
    assert all(v.id == base.id for v in a)
    assert get_scenario("s1_rod_packing") == base


def test_weather_window_fits_the_snapshot() -> None:
    """Every variant's weather window lies inside the 168 h snapshot."""
    for v in generate_variants(get_scenario("s5_sensor_drift")):
        assert 0 <= v.weather_offset_h <= 168 - v.duration_h - 1


def test_rate_and_header_flow_scale_together() -> None:
    """The leak rate and the FT-250 signature scale by the same factor."""
    base = get_scenario("s1_rod_packing")
    base_ft = next(e for e in base.instrument_effects if e.tag == "FT-250").value
    for v in generate_variants(base):
        scale = v.sources[0].rate_kg_h / base.sources[0].rate_kg_h
        assert 0.5 <= scale <= 2.0
        ft = next(e for e in v.instrument_effects if e.tag == "FT-250").value
        assert ft == pytest.approx(base_ft * scale)
        assert v.expected.rate_min_kg_h == pytest.approx(7.5 * scale)


def test_permit_moves_with_the_blowdown() -> None:
    """In S4 variants the permit keeps its 600 s lead over the blowdown (unless clamped at 0)."""
    for v in generate_variants(get_scenario("s4_planned_blowdown")):
        permit = next(e for e in v.log if e.kind == "permit")
        start = v.sources[0].start_s
        assert permit.t_s == pytest.approx(max(0.0, start - 600.0))


def test_logs_stay_sorted_with_distractors() -> None:
    """Distractors are added and the log stays sorted."""
    for v in generate_variants(get_scenario("s1_rod_packing")):
        times = [e.t_s for e in v.log]
        assert times == sorted(times)
        assert len(v.log) >= 3
