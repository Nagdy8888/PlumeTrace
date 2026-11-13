"""Tests for procedural component placement and the component-count table."""

from typing import Any

import pytest
from pydantic import ValidationError

from plumetrace.facility.components import (
    ComponentCounts,
    CountsTable,
    counts_for,
    load_component_counts,
    place_route_components,
)
from plumetrace.facility.loader import load_facility
from plumetrace.facility.spec import FacilitySpec
from plumetrace.facility.types import EquipmentType


def _with_route(spec: dict[str, Any], waypoints: list[list[float]]) -> FacilitySpec:
    spec["piping"] = [{"id": "R-T", "service": "gas", "size_in": 4, "waypoints_m": waypoints}]
    return FacilitySpec.model_validate(spec)


def test_straight_route_spacing_and_order(minimal_spec: dict[str, Any]) -> None:
    """24 m straight route: flanges at 0, 12, 24 m; valves at both ends; flange first."""
    spec = _with_route(minimal_spec, [[0, 0, 1], [24, 0, 1]])
    got = [(c.kind, c.position.x_m, c.position.y_m) for c in place_route_components(spec)]
    assert got == [
        ("flange", 0.0, 0.0),
        ("valve", 0.0, 0.0),
        ("flange", 12.0, 0.0),
        ("flange", 24.0, 0.0),
        ("valve", 24.0, 0.0),
    ]


def test_bent_route_measures_distance_along_the_polyline(minimal_spec: dict[str, Any]) -> None:
    """Spacing is cumulative along the route; a waypoint on a spacing point is not duplicated."""
    spec = _with_route(minimal_spec, [[0, 0, 1], [12, 0, 1], [12, 18, 1]])
    got = [(c.kind, c.position.x_m, c.position.y_m) for c in place_route_components(spec)]
    assert got == [
        ("flange", 0.0, 0.0),
        ("valve", 0.0, 0.0),
        ("flange", 12.0, 0.0),
        ("flange", 12.0, 12.0),
        ("flange", 12.0, 18.0),
        ("valve", 12.0, 18.0),
    ]


def test_real_spec_placement_is_deterministic() -> None:
    """Two runs give identical results (3D and candidate generation depend on it)."""
    spec = load_facility()
    first = place_route_components(spec)
    assert first == place_route_components(spec)
    assert len(first) > 30


FIXTURE_TABLE = {
    "source": "fixture",
    "column": "test",
    "notes": "",
    "classes": {
        "compressors": {
            "valves": 1,
            "connectors": 2,
            "open_ended_lines": 3,
            "pressure_relief_valves": 4,
        }
    },
    "equipment_type_map": {"recip_compressor": "compressors", "vent_stack": None},
}


def test_counts_for_maps_types_and_zero_for_unmapped(minimal_spec: dict[str, Any]) -> None:
    """Mapped types get their class counts; null-mapped types get zeros."""
    counts = counts_for(
        FacilitySpec.model_validate(minimal_spec), CountsTable.model_validate(FIXTURE_TABLE)
    )
    assert counts["K-202"] == ComponentCounts(
        valves=1, connectors=2, open_ended_lines=3, pressure_relief_valves=4
    )
    assert counts["VS-250"] == ComponentCounts(
        valves=0, connectors=0, open_ended_lines=0, pressure_relief_valves=0
    )


def test_unknown_class_in_map_is_rejected() -> None:
    """A map entry pointing at a missing class is an error naming that class."""
    bad = dict(FIXTURE_TABLE, equipment_type_map={"recip_compressor": "turbines"})
    with pytest.raises(ValidationError, match="turbines"):
        CountsTable.model_validate(bad)


def test_real_counts_table_matches_the_cited_source() -> None:
    """The shipped table cites Subpart W W-1B (Western U.S.) and maps every equipment type."""
    table = load_component_counts()
    assert "40 CFR Part 98" in table.source
    assert table.column == "Western U.S."
    assert table.classes["compressors"] == ComponentCounts(
        valves=73, connectors=179, open_ended_lines=3, pressure_relief_valves=4
    )
    assert table.classes["separators"] == ComponentCounts(
        valves=34, connectors=106, open_ended_lines=6, pressure_relief_valves=2
    )
    assert set(table.equipment_type_map) == {t.value for t in EquipmentType}
