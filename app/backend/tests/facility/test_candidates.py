"""Tests for the inversion candidate list and the methane sensor list."""

from plumetrace.engineering.geometry import Point3
from plumetrace.facility.candidates import emission_candidates, methane_sensors
from plumetrace.facility.loader import load_facility

EXPECTED_CANDIDATE_IDS = sorted(
    [
        "PIG-101.door",
        "V-100.psv",
        "V-211.psv",
        "V-212.psv",
        "V-213.psv",
        "K-201.packing",
        "K-201.engine_exhaust",
        "K-202.packing",
        "K-202.engine_exhaust",
        "K-203.packing",
        "K-203.engine_exhaust",
        "VS-250.tip",
        "R-302.still_vent",
        "FG-501.skid",
        "TK-401.thief_hatch",
        "TK-402.thief_hatch",
        "VRU-410.skid",
        "V-602.psv",
        "FL-601.tip",
        "M-701.meter",
        "PIG-702.door",
    ]
)


def test_emission_candidates_are_the_21_anchor_points() -> None:
    """Every emission anchor is a candidate, sorted by id."""
    ids = [c.id for c in emission_candidates(load_facility())]
    assert ids == EXPECTED_CANDIDATE_IDS


def test_vent_stack_tip_position() -> None:
    """Anchor coordinates are carried over unchanged."""
    by_id = {c.id: c for c in emission_candidates(load_facility())}
    assert by_id["VS-250.tip"].position == Point3(85.0, 115.0, 12.0)


def test_methane_sensors_sorted_with_noise() -> None:
    """The eight point sensors, sorted, each with 0.3 ppm noise."""
    sensors = methane_sensors(load_facility())
    assert [s.id for s in sensors] == [f"AT-10{i}" for i in range(1, 9)]
    assert all(s.noise_ppm == 0.3 for s in sensors)
    assert sensors[3].position == Point3(195.0, 75.0, 2.0)
