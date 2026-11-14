"""The MVP scenario definitions carry exactly the values of the plan (own tests)."""

from typing import Any

import pytest

from plumetrace.engineering.gas import ch4_mass_fraction
from plumetrace.simulator.scenarios import SCENARIOS, get_scenario
from plumetrace.simulator.scenarios.s1_rod_packing import KS07_COMPOSITION, S1_SEED
from plumetrace.simulator.scenarios.s1_rod_packing import WEATHER_OFFSET_H as S1_OFFSET
from plumetrace.simulator.scenarios.s4_planned_blowdown import S4_SEED
from plumetrace.simulator.scenarios.s4_planned_blowdown import WEATHER_OFFSET_H as S4_OFFSET
from plumetrace.simulator.scenarios.s5_sensor_drift import S5_SEED
from plumetrace.simulator.scenarios.s5_sensor_drift import WEATHER_OFFSET_H as S5_OFFSET
from plumetrace.simulator.selection import CANDIDATE_OFFSETS_H


def test_ids_seeds_and_offsets() -> None:
    """Registry keys are the definition ids; seeds are 101, 104, 105; offsets are candidates."""
    assert all(k == d.id for k, d in SCENARIOS.items())
    assert (S1_SEED, S4_SEED, S5_SEED) == (101, 104, 105)
    ids = ("s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift")
    assert [get_scenario(i).seed for i in ids] == [101, 104, 105]
    for offset in (S1_OFFSET, S4_OFFSET, S5_OFFSET):
        assert offset in CANDIDATE_OFFSETS_H
    assert [get_scenario(i).weather_offset_h for i in ids] == [S1_OFFSET, S4_OFFSET, S5_OFFSET]


def test_candidate_offsets() -> None:
    """Every 2 h from 0 to 160 h: 81 candidates."""
    assert CANDIDATE_OFFSETS_H[:3] == (0, 2, 4)
    assert CANDIDATE_OFFSETS_H[-1] == 160
    assert len(CANDIDATE_OFFSETS_H) == 81


def test_registry_is_read_only() -> None:
    """The registry cannot be changed at run time."""
    registry: Any = SCENARIOS
    with pytest.raises(TypeError):
        registry["s9_x"] = get_scenario("s1_rod_packing")


def test_s1_values() -> None:
    """S1: 6 h, 15 kg/h at VS-250.tip from 7200 s, FT-250 and TT-202P effects, three log lines."""
    d = get_scenario("s1_rod_packing")
    assert d.duration_h == 6
    assert [(s.anchor_id, s.rate_kg_h, s.start_s, s.end_s) for s in d.sources] == [
        ("VS-250.tip", 15.0, 7200.0, float("inf"))
    ]
    assert [(e.tag, e.kind, e.start_s, e.ramp_s) for e in d.instrument_effects] == [
        ("FT-250", "offset", 7200.0, 1800.0),
        ("TT-202P", "offset", 7200.0, 1800.0),
    ]
    # whole-gas flow: the CH4 rate divided by the CH4 mass fraction
    assert d.instrument_effects[0].value == pytest.approx(
        15.0 / ch4_mass_fraction(KS07_COMPOSITION)
    )
    assert [(e.t_s, e.kind, e.tag) for e in d.log] == [
        (600, "shift_note", None),
        (4000, "gauging", "TK-402"),
        (5000, "maintenance", "AT-103"),
    ]
    assert (d.expected.triage, d.expected.top_candidate, d.expected.attributed_unit) == (
        "leak",
        "VS-250.tip",
        "K-202",
    )
    assert (d.expected.rate_min_kg_h, d.expected.rate_max_kg_h) == (7.5, 30.0)


def test_s4_values() -> None:
    """S4: 4 h, a 15 minute source at VS-250.tip from 7200 s, permit and maintenance log."""
    d = get_scenario("s4_planned_blowdown")
    assert d.duration_h == 4
    assert [(s.anchor_id, s.start_s, s.end_s) for s in d.sources] == [
        ("VS-250.tip", 7200.0, 8100.0)
    ]
    assert [(e.t_s, e.kind, e.tag) for e in d.log] == [
        (6600, "permit", "K-201"),
        (9000, "maintenance", "K-201"),
    ]
    assert d.log[0].text.startswith("PTW-0412: planned blowdown of K-201")
    assert (d.expected.triage, d.expected.top_candidate) == ("planned_venting", None)


def test_s5_values() -> None:
    """S5: 6 h, AT-106 drifts 0.6 ppm/h from 3600 s, no sources, two log lines."""
    d = get_scenario("s5_sensor_drift")
    assert d.duration_h == 6
    assert d.sources == []
    assert [(f.sensor_id, f.drift_ppm_per_h, f.start_s) for f in d.faults] == [
        ("AT-106", 0.6, 3600.0)
    ]
    assert [(e.t_s, e.kind, e.tag) for e in d.log] == [
        (300, "calibration", "AT-106"),
        (3000, "shift_note", None),
    ]
    assert (d.expected.triage, d.expected.top_candidate) == ("sensor_fault", None)
