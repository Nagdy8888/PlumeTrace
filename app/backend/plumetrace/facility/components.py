"""Procedural flange and valve placement on pipe routes, and the cited component-count table.

Flanges sit at every waypoint and every ``spacing_m`` along a route; valves sit at the first and
last waypoint. The count table holds the default component counts used by the emission-factor
leak estimate (source cited in ``data/component_counts.yaml``).
"""

import math
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from plumetrace.engineering.geometry import Point3
from plumetrace.facility.spec import FacilitySpec
from plumetrace.facility.types import PipeRoute, Vec3

FLANGE_SPACING_M: Final = 12.0
DEFAULT_COUNTS_PATH: Final[Path] = Path(__file__).parent / "data" / "component_counts.yaml"
_MERGE_TOLERANCE_M: Final = 1e-6


@dataclass(frozen=True)
class PlacedComponent:
    """A flange or valve placed on a pipe route.

    Attributes:
        kind: ``flange`` or ``valve``.
        route_id: Id of the route it sits on.
        position: Position in site coordinates.
    """

    kind: Literal["flange", "valve"]
    route_id: str
    position: Point3


def _cumulative_m(waypoints: list[Vec3]) -> list[float]:
    """Return the distance along the polyline at each waypoint, starting at 0.

    Args:
        waypoints: Polyline points.

    Returns:
        One cumulative distance in metres per waypoint.
    """
    cumulative = [0.0]
    for a, b in pairwise(waypoints):
        cumulative.append(cumulative[-1] + math.dist(a, b))
    return cumulative


def _point_at(waypoints: list[Vec3], cumulative: list[float], distance_m: float) -> Point3:
    """Interpolate the point at a distance along the polyline.

    Args:
        waypoints: Polyline points.
        cumulative: Cumulative distances from ``_cumulative_m``.
        distance_m: Distance along the polyline, within its total length.

    Returns:
        The interpolated point.
    """
    for i, at in enumerate(cumulative):
        if abs(at - distance_m) <= _MERGE_TOLERANCE_M:
            return Point3(*waypoints[i])  # exact waypoint, no interpolation error
    for i in range(len(waypoints) - 1):
        start, end = cumulative[i], cumulative[i + 1]
        if end > start and distance_m <= end:
            t = (distance_m - start) / (end - start)
            a, b = waypoints[i], waypoints[i + 1]
            return Point3(*(a[k] + t * (b[k] - a[k]) for k in range(3)))
    return Point3(*waypoints[-1])


def _flange_distances_m(cumulative: list[float], spacing_m: float) -> list[float]:
    """Return sorted flange distances: every waypoint and every multiple of the spacing.

    Args:
        cumulative: Cumulative distances at the waypoints.
        spacing_m: Flange spacing in metres.

    Returns:
        Sorted distances with points closer than 1e-6 m merged (the earlier one is kept).
    """
    distances = list(cumulative)
    step = 0
    while step * spacing_m <= cumulative[-1]:
        distances.append(step * spacing_m)
        step += 1
    merged: list[float] = []
    for distance in sorted(distances):
        if not merged or distance - merged[-1] > _MERGE_TOLERANCE_M:
            merged.append(distance)
    return merged


def _route_components(route: PipeRoute, spacing_m: float) -> list[PlacedComponent]:
    """Place the flanges and valves of one route, ordered along it.

    Args:
        route: The pipe route.
        spacing_m: Flange spacing in metres.

    Returns:
        Components ordered by distance along the route, flange before valve at equal distance.
    """
    waypoints = route.waypoints_m
    cumulative = _cumulative_m(waypoints)
    placed = [
        (d, 0, PlacedComponent("flange", route.id, _point_at(waypoints, cumulative, d)))
        for d in _flange_distances_m(cumulative, spacing_m)
    ]
    for d, waypoint in ((cumulative[0], waypoints[0]), (cumulative[-1], waypoints[-1])):
        placed.append((d, 1, PlacedComponent("valve", route.id, Point3(*waypoint))))
    placed.sort(key=lambda item: (item[0], item[1]))
    return [component for _, _, component in placed]


def place_route_components(
    spec: FacilitySpec, spacing_m: float = FLANGE_SPACING_M
) -> list[PlacedComponent]:
    """Place flanges and valves on every pipe route, in spec order.

    Args:
        spec: The facility spec.
        spacing_m: Flange spacing along a route in metres.

    Returns:
        All placed components, route by route.
    """
    return [c for route in spec.piping for c in _route_components(route, spacing_m)]


class ComponentCounts(BaseModel):
    """Default component counts for one equipment class.

    Attributes:
        valves: Number of valves.
        connectors: Number of connectors.
        open_ended_lines: Number of open-ended lines.
        pressure_relief_valves: Number of pressure relief valves.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    valves: int = Field(ge=0)
    connectors: int = Field(ge=0)
    open_ended_lines: int = Field(ge=0)
    pressure_relief_valves: int = Field(ge=0)


class CountsTable(BaseModel):
    """The cited default component-count table and the equipment-type mapping.

    Attributes:
        source: Citation of the published table.
        column: Table column used (region).
        notes: Caveats on how the table is applied.
        classes: Counts per published equipment class.
        equipment_type_map: Equipment type to class name, or ``None`` for no counted components.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    column: str
    notes: str
    classes: dict[str, ComponentCounts]
    equipment_type_map: dict[str, str | None]

    @model_validator(mode="after")
    def _check_map(self) -> Self:
        """Require every mapped class name to exist in ``classes``.

        Returns:
            The validated table.

        Raises:
            ValueError: If the map refers to an unknown class.
        """
        for name in self.equipment_type_map.values():
            if name is not None and name not in self.classes:
                raise ValueError(f"equipment_type_map refers to unknown class {name}")
        return self


def load_component_counts(path: Path = DEFAULT_COUNTS_PATH) -> CountsTable:
    """Read and validate the component-count table.

    Args:
        path: YAML file to read; defaults to the shipped table.

    Returns:
        The validated table.
    """
    return CountsTable.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def counts_for(spec: FacilitySpec, table: CountsTable) -> dict[str, ComponentCounts]:
    """Give each equipment item the counts of its mapped class.

    Args:
        spec: The facility spec.
        table: The component-count table.

    Returns:
        Equipment tag to counts; types mapped to ``None`` get all zeros.
    """
    zero = ComponentCounts(valves=0, connectors=0, open_ended_lines=0, pressure_relief_valves=0)
    result: dict[str, ComponentCounts] = {}
    for equipment in spec.equipment:
        name = table.equipment_type_map[equipment.type.value]
        result[equipment.tag] = zero if name is None else table.classes[name]
    return result
