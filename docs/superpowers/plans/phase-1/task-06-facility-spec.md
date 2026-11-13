# Phase 1 · Task 6 — Facility spec for Station KS-07

**Read first:** design §4 (facility, instruments, gas composition), `repo-structure` (dependency direction: `facility` may import only `engineering`). **Skills:** `plan-execution`, `engineering-core`, `repo-structure`, `project-documentation`.

**Goal:** the single source of truth for the station — equipment, anchors (named leak points),
piping, instruments, gas composition, operating conditions — with strict validation, the
inversion candidate list, the methane sensor list, procedural flange/valve placement and the
cited component-count table.

## Files
| Action | Path (backend = `app/backend/plumetrace/`) |
|---|---|
| Create | `backend/engineering/__init__.py`, `backend/engineering/geometry.py` |
| Create | `backend/facility/__init__.py`, `types.py`, `spec.py`, `loader.py`, `candidates.py`, `components.py` |
| Create | `backend/facility/data/ks07.yaml`, `backend/facility/data/component_counts.yaml` |
| Create (tests) | `app/backend/tests/facility/conftest.py`, `test_loader.py`, `test_validation.py`, `test_candidates.py`, `test_components.py` |
| Create | `docs/reference/SIMULATOR.md`; modify `docs/README.md`, `docs/OWNER_ACTIONS.md` |

## Interfaces (exact names and types)

`engineering/__init__.py`: docstring "Pure engineering core: no I/O, no network, no LLM, no globals."

`engineering/geometry.py`:
```python
@dataclass(frozen=True)
class Point3:
    x_m: float
    y_m: float
    z_m: float

@dataclass(frozen=True)
class Candidate:
    id: str
    position: Point3

@dataclass(frozen=True)
class Sensor:
    id: str
    position: Point3
    noise_ppm: float
```

`facility/types.py`:
- `class EquipmentType(StrEnum)`: `pig_trap, filter_separator, scrubber, recip_compressor, fin_fan_cooler, vent_stack, teg_contactor, teg_regenerator, fuel_gas_skid, storage_tank, vru, knockout_drum, flare_stack, meter_run, building` (value = name).
- `class InstrumentKind(StrEnum)`: `methane_point, met_mast, flow, temperature, pressure, thermocouple`.
- `Vec3 = tuple[float, float, float]`
- Pydantic models (all `model_config = ConfigDict(extra="forbid", frozen=True)`):
  - `Anchor(id: str, position_m: Vec3, emission_point: bool)`
  - `Equipment(tag: str, type: EquipmentType, position_m: Vec3, rotation_deg: float, size_m: Vec3, anchors: list[Anchor] = [], vents_to: str | None = None, shelter: bool = False, description: str = "")`
  - `PipeRoute(id: str, service: Literal["gas", "vent", "flare", "condensate", "fuel_gas"], size_in: float, waypoints_m: list[Vec3] = Field(min_length=2))`
  - `Instrument(tag: str, kind: InstrumentKind, position_m: Vec3, attaches_to: str | None = None, noise_ppm: float | None = None)`
  - `SiteBounds(x_min_m: float, x_max_m: float, y_min_m: float, y_max_m: float)` with method `contains(p: Vec3) -> bool` (x and y inclusive within bounds **and** `z >= 0`)
  - `Site(id: str, name: str, fictional: bool, bounds: SiteBounds, latitude_deg: float, longitude_deg: float, elevation_m: float, ambient_pressure_pa: float)`
  - `OperatingConditions(suction_pressure_pa: float, discharge_pressure_pa: float, gas_temperature_k: float, throughput_sm3_h: float)`

`facility/spec.py`:
- `class FacilitySpec(BaseModel)` (`extra="forbid"`, `frozen=True`): `site: Site`, `gas_composition: dict[str, float]`, `operating: OperatingConditions`, `equipment: list[Equipment]`, `piping: list[PipeRoute]`, `instruments: list[Instrument]`.
- One `@model_validator(mode="after")` that calls these module-level functions in order (each raises `ValueError` with the exact message format shown; keep each ≤ 50 lines):
  1. `_check_unique_tags(spec)` — tags unique across equipment **and** instruments: `f"duplicate tag {tag}"`.
  2. `_check_anchor_ownership(spec)` — every anchor id starts with `f"{equipment.tag}."`: `f"anchor {anchor.id} does not belong to equipment {equipment.tag}"`.
  3. `_check_bounds(spec)` — equipment positions, anchor positions, instrument positions and every pipe waypoint must satisfy `bounds.contains`: `f"{owner} position {position} is outside the site bounds"` where owner = equipment tag, anchor id, instrument tag or route id.
  4. `_check_references(spec)` — `vents_to` must be an equipment tag: `f"{tag} vents_to unknown tag {vents_to}"`; `attaches_to` must be an equipment tag: `f"{tag} attaches_to unknown tag {attaches_to}"`.
  5. `_check_composition(spec)` — `abs(sum - 1) > 1e-6` → `f"gas_composition sums to {total:.6f}, expected 1"`.
- Method `equipment_by_tag(self, tag: str) -> Equipment` — raises `KeyError(f"unknown equipment tag {tag}")`.

`facility/loader.py`: `DEFAULT_SPEC_PATH: Final[Path] = Path(__file__).parent / "data" / "ks07.yaml"`; `def load_facility(path: Path = DEFAULT_SPEC_PATH) -> FacilitySpec` (read with `encoding="utf-8"`, `yaml.safe_load`, `FacilitySpec.model_validate`).

`facility/candidates.py`:
- `def emission_candidates(spec: FacilitySpec) -> list[Candidate]` — every anchor with `emission_point: true`, as `Candidate(id=anchor.id, position=Point3(*anchor.position_m))`, sorted by id.
- `def methane_sensors(spec: FacilitySpec) -> list[Sensor]` — instruments of kind `methane_point`, `Sensor(id=tag, position=Point3(*position_m), noise_ppm=noise_ppm)`, sorted by id. A methane sensor without `noise_ppm` raises `ValueError(f"{tag} has no noise_ppm")`.

`facility/components.py`:
- `FLANGE_SPACING_M: Final = 12.0`; `DEFAULT_COUNTS_PATH: Final[Path] = Path(__file__).parent / "data" / "component_counts.yaml"`
- `@dataclass(frozen=True) class PlacedComponent: kind: Literal["flange", "valve"]; route_id: str; position: Point3`
- `def place_route_components(spec: FacilitySpec, spacing_m: float = FLANGE_SPACING_M) -> list[PlacedComponent]` — for each route in spec order: compute cumulative distance along the polyline; place a **flange** at every waypoint and at every multiple of `spacing_m` along the route (positions interpolated on the segment), merging points closer than 1e-6 m; place a **valve** at the first and last waypoint; order by distance along the route, and at equal distance flange before valve.
- `class ComponentCounts(BaseModel)` (`frozen`): `valves: int, connectors: int, open_ended_lines: int, pressure_relief_valves: int` (all ≥ 0).
- `class CountsTable(BaseModel)`: `source: str`, `column: str`, `notes: str`, `classes: dict[str, ComponentCounts]`, `equipment_type_map: dict[str, str | None]`; validator: every non-null mapped class must be a key of `classes` → `f"equipment_type_map refers to unknown class {name}"`.
- `def load_component_counts(path: Path = DEFAULT_COUNTS_PATH) -> CountsTable`
- `def counts_for(spec: FacilitySpec, table: CountsTable) -> dict[str, ComponentCounts]` — tag → counts of the mapped class; unmapped (`null`) types → all zeros.

## Data files (exact content)

`facility/data/ks07.yaml`:
```yaml
# Station KS-07 — fictional compressor station. Single source of truth for layout, leak points,
# instruments and gas. Coordinates: metres, x = east, y = north, z = up, origin = SW fence corner.
site:
  id: KS-07
  name: Station KS-07
  fictional: true
  bounds: {x_min_m: 0, x_max_m: 200, y_min_m: 0, y_max_m: 150}
  latitude_deg: 39.10     # fictional placement in the Karakum desert region (weather source only)
  longitude_deg: 61.30
  elevation_m: 200
  ambient_pressure_pa: 98900
gas_composition: {CH4: 0.930, C2H6: 0.035, C3H8: 0.008, nC4H10: 0.002, CO2: 0.010, N2: 0.015}
operating:
  suction_pressure_pa: 4500000
  discharge_pressure_pa: 7000000
  gas_temperature_k: 300
  throughput_sm3_h: 41667
equipment:
  - {tag: PIG-101, type: pig_trap, position_m: [15, 75, 0], rotation_deg: 0, size_m: [6, 1.2, 1.5], anchors: [{id: PIG-101.door, position_m: [12, 75, 1.0], emission_point: true}]}
  - {tag: V-100, type: filter_separator, position_m: [30, 75, 0], rotation_deg: 0, size_m: [2, 2, 6], anchors: [{id: V-100.psv, position_m: [30, 75, 6.0], emission_point: true}]}
  - {tag: V-211, type: scrubber, position_m: [62, 57, 0], rotation_deg: 0, size_m: [1.5, 1.5, 5], anchors: [{id: V-211.psv, position_m: [62, 57, 5.0], emission_point: true}]}
  - {tag: V-212, type: scrubber, position_m: [62, 75, 0], rotation_deg: 0, size_m: [1.5, 1.5, 5], anchors: [{id: V-212.psv, position_m: [62, 75, 5.0], emission_point: true}]}
  - {tag: V-213, type: scrubber, position_m: [62, 93, 0], rotation_deg: 0, size_m: [1.5, 1.5, 5], anchors: [{id: V-213.psv, position_m: [62, 93, 5.0], emission_point: true}]}
  - {tag: K-201, type: recip_compressor, position_m: [75, 57, 0], rotation_deg: 0, size_m: [12, 4, 3], shelter: true, vents_to: VS-250, anchors: [{id: K-201.packing, position_m: [73, 57, 1.5], emission_point: true}, {id: K-201.engine_exhaust, position_m: [80, 57, 6.0], emission_point: true}]}
  - {tag: K-202, type: recip_compressor, position_m: [75, 75, 0], rotation_deg: 0, size_m: [12, 4, 3], shelter: true, vents_to: VS-250, anchors: [{id: K-202.packing, position_m: [73, 75, 1.5], emission_point: true}, {id: K-202.engine_exhaust, position_m: [80, 75, 6.0], emission_point: true}]}
  - {tag: K-203, type: recip_compressor, position_m: [75, 93, 0], rotation_deg: 0, size_m: [12, 4, 3], shelter: true, vents_to: VS-250, anchors: [{id: K-203.packing, position_m: [73, 93, 1.5], emission_point: true}, {id: K-203.engine_exhaust, position_m: [80, 93, 6.0], emission_point: true}]}
  - {tag: E-231, type: fin_fan_cooler, position_m: [95, 57, 0], rotation_deg: 0, size_m: [8, 4, 5]}
  - {tag: E-232, type: fin_fan_cooler, position_m: [95, 75, 0], rotation_deg: 0, size_m: [8, 4, 5]}
  - {tag: E-233, type: fin_fan_cooler, position_m: [95, 93, 0], rotation_deg: 0, size_m: [8, 4, 5]}
  - {tag: VS-250, type: vent_stack, position_m: [85, 115, 0], rotation_deg: 0, size_m: [0.4, 0.4, 12], anchors: [{id: VS-250.tip, position_m: [85, 115, 12.0], emission_point: true}]}
  - {tag: T-301, type: teg_contactor, position_m: [120, 60, 0], rotation_deg: 0, size_m: [1.5, 1.5, 15]}
  - {tag: R-302, type: teg_regenerator, position_m: [130, 50, 0], rotation_deg: 0, size_m: [4, 2, 8], anchors: [{id: R-302.still_vent, position_m: [130, 50, 8.0], emission_point: true}]}
  - {tag: FG-501, type: fuel_gas_skid, position_m: [110, 95, 0], rotation_deg: 0, size_m: [4, 3, 2], anchors: [{id: FG-501.skid, position_m: [110, 95, 1.5], emission_point: true}]}
  - {tag: TK-401, type: storage_tank, position_m: [150, 110, 0], rotation_deg: 0, size_m: [6, 6, 7], anchors: [{id: TK-401.thief_hatch, position_m: [150, 110, 7.0], emission_point: true}]}
  - {tag: TK-402, type: storage_tank, position_m: [165, 110, 0], rotation_deg: 0, size_m: [6, 6, 7], anchors: [{id: TK-402.thief_hatch, position_m: [165, 110, 7.0], emission_point: true}]}
  - {tag: VRU-410, type: vru, position_m: [157, 95, 0], rotation_deg: 0, size_m: [4, 3, 2.5], anchors: [{id: VRU-410.skid, position_m: [157, 95, 1.5], emission_point: true}]}
  - {tag: V-602, type: knockout_drum, position_m: [175, 30, 0], rotation_deg: 0, size_m: [6, 2, 2.5], anchors: [{id: V-602.psv, position_m: [175, 30, 4.0], emission_point: true}]}
  - {tag: FL-601, type: flare_stack, position_m: [185, 30, 0], rotation_deg: 0, size_m: [1, 1, 30], anchors: [{id: FL-601.tip, position_m: [185, 30, 30.0], emission_point: true}]}
  - {tag: M-701, type: meter_run, position_m: [175, 75, 0], rotation_deg: 0, size_m: [10, 2, 1.5], anchors: [{id: M-701.meter, position_m: [175, 75, 1.0], emission_point: true}]}
  - {tag: PIG-702, type: pig_trap, position_m: [190, 75, 0], rotation_deg: 0, size_m: [6, 1.2, 1.5], anchors: [{id: PIG-702.door, position_m: [193, 75, 1.0], emission_point: true}]}
  - {tag: CR-901, type: building, position_m: [30, 20, 0], rotation_deg: 0, size_m: [15, 8, 4], description: Control room}
  - {tag: MCC-902, type: building, position_m: [50, 20, 0], rotation_deg: 0, size_m: [10, 6, 4], description: Motor control centre}
piping:
  - {id: R-100, service: gas, size_in: 24, waypoints_m: [[15, 75, 1], [30, 75, 1], [45, 75, 4]]}
  - {id: R-110, service: gas, size_in: 20, waypoints_m: [[45, 57, 4], [45, 93, 4]]}
  - {id: R-111, service: gas, size_in: 12, waypoints_m: [[45, 57, 4], [62, 57, 4], [69, 57, 1.5]]}
  - {id: R-112, service: gas, size_in: 12, waypoints_m: [[45, 75, 4], [62, 75, 4], [69, 75, 1.5]]}
  - {id: R-113, service: gas, size_in: 12, waypoints_m: [[45, 93, 4], [62, 93, 4], [69, 93, 1.5]]}
  - {id: R-121, service: gas, size_in: 10, waypoints_m: [[81, 57, 1.5], [95, 57, 4], [105, 57, 4]]}
  - {id: R-122, service: gas, size_in: 10, waypoints_m: [[81, 75, 1.5], [95, 75, 4], [105, 75, 4]]}
  - {id: R-123, service: gas, size_in: 10, waypoints_m: [[81, 93, 1.5], [95, 93, 4], [105, 93, 4]]}
  - {id: R-130, service: gas, size_in: 20, waypoints_m: [[105, 57, 4], [105, 93, 4]]}
  - {id: R-140, service: gas, size_in: 20, waypoints_m: [[105, 75, 4], [120, 75, 4], [120, 62, 1.5]]}
  - {id: R-150, service: gas, size_in: 20, waypoints_m: [[120, 75, 4], [170, 75, 4], [175, 75, 1], [187, 75, 1]]}
  - {id: R-250, service: vent, size_in: 2, waypoints_m: [[73, 57, 2], [73, 93, 2], [73, 105, 2], [85, 105, 2], [85, 115, 1]]}
  - {id: R-600, service: flare, size_in: 12, waypoints_m: [[105, 57, 4], [105, 30, 4], [175, 30, 2], [185, 30, 1]]}
  - {id: R-400, service: condensate, size_in: 4, waypoints_m: [[62, 57, 0.5], [62, 40, 0.5], [150, 40, 0.5], [150, 107, 0.5]]}
  - {id: R-500, service: fuel_gas, size_in: 2, waypoints_m: [[105, 93, 4], [110, 93, 1.5]]}
instruments:
  - {tag: AT-101, kind: methane_point, position_m: [5, 5, 2.0], noise_ppm: 0.3}
  - {tag: AT-102, kind: methane_point, position_m: [100, 5, 2.0], noise_ppm: 0.3}
  - {tag: AT-103, kind: methane_point, position_m: [195, 5, 2.0], noise_ppm: 0.3}
  - {tag: AT-104, kind: methane_point, position_m: [195, 75, 2.0], noise_ppm: 0.3}
  - {tag: AT-105, kind: methane_point, position_m: [195, 145, 2.0], noise_ppm: 0.3}
  - {tag: AT-106, kind: methane_point, position_m: [100, 145, 2.0], noise_ppm: 0.3}
  - {tag: AT-107, kind: methane_point, position_m: [5, 145, 2.0], noise_ppm: 0.3}
  - {tag: AT-108, kind: methane_point, position_m: [110, 75, 2.0], noise_ppm: 0.3}
  - {tag: MET-01, kind: met_mast, position_m: [10, 140, 10.0]}
  - {tag: FT-250, kind: flow, position_m: [85, 110, 1.0], attaches_to: VS-250}
  - {tag: TT-201P, kind: temperature, position_m: [73, 57, 1.5], attaches_to: K-201}
  - {tag: TT-202P, kind: temperature, position_m: [73, 75, 1.5], attaches_to: K-202}
  - {tag: TT-203P, kind: temperature, position_m: [73, 93, 1.5], attaches_to: K-203}
  - {tag: FT-601, kind: flow, position_m: [178, 30, 1.0], attaches_to: FL-601}
  - {tag: TE-601, kind: thermocouple, position_m: [185, 30, 29.5], attaches_to: FL-601}
  - {tag: PT-401, kind: pressure, position_m: [150, 110, 7.0], attaches_to: TK-401}
  - {tag: PT-402, kind: pressure, position_m: [165, 110, 7.0], attaches_to: TK-402}
  - {tag: FT-701, kind: flow, position_m: [175, 75, 1.0], attaches_to: M-701}
```

`facility/data/component_counts.yaml` (values verified against the 2023 CFR edition on 2026-11-12):
```yaml
source: >-
  40 CFR Part 98, Subpart W, Table W-1B "Default Average Component Counts for Major Onshore Natural
  Gas Production Equipment and Onshore Petroleum and Natural Gas Gathering and Boosting Equipment",
  CFR 2023 edition (govinfo package CFR-2023-title40-vol23), [75 FR 74488, Nov. 30, 2010, as
  amended at 80 FR 64298, Oct. 22, 2015]. The table was removed in the 2024 Subpart W revision
  (89 FR 42323-42325, May 14, 2024); it is the latest published set of default component counts.
  Accessed 2026-11-12.
column: Western U.S.
notes: >-
  Production / gathering-and-boosting default counts are used as a documented proxy for a
  transmission compressor station, for which no default counts are published. The TEG regenerator
  is counted with the contactor as one dehydrator. Reviewed by the owner at Gate 1.
classes:
  wellheads: {valves: 11, connectors: 36, open_ended_lines: 1, pressure_relief_valves: 0}
  separators: {valves: 34, connectors: 106, open_ended_lines: 6, pressure_relief_valves: 2}
  meters_piping: {valves: 14, connectors: 51, open_ended_lines: 1, pressure_relief_valves: 1}
  compressors: {valves: 73, connectors: 179, open_ended_lines: 3, pressure_relief_valves: 4}
  in_line_heaters: {valves: 14, connectors: 65, open_ended_lines: 2, pressure_relief_valves: 1}
  dehydrators: {valves: 24, connectors: 90, open_ended_lines: 2, pressure_relief_valves: 2}
equipment_type_map:
  pig_trap: meters_piping
  filter_separator: separators
  scrubber: separators
  recip_compressor: compressors
  fin_fan_cooler: null
  vent_stack: null
  teg_contactor: dehydrators
  teg_regenerator: null
  fuel_gas_skid: meters_piping
  storage_tank: null
  vru: compressors
  knockout_drum: separators
  flare_stack: null
  meter_run: meters_piping
  building: null
```

## Tests (full code)

`app/backend/tests/facility/conftest.py`:
```python
"""Shared fixtures for facility tests."""

from typing import Any

import pytest


def _minimal_spec() -> dict[str, Any]:
    """Return a small valid facility spec dict (fresh copy on every call)."""
    return {
        "site": {
            "id": "T",
            "name": "Test site",
            "fictional": True,
            "bounds": {"x_min_m": 0, "x_max_m": 100, "y_min_m": 0, "y_max_m": 100},
            "latitude_deg": 0.0,
            "longitude_deg": 0.0,
            "elevation_m": 0.0,
            "ambient_pressure_pa": 101325.0,
        },
        "gas_composition": {"CH4": 0.95, "N2": 0.05},
        "operating": {
            "suction_pressure_pa": 4.5e6,
            "discharge_pressure_pa": 7.0e6,
            "gas_temperature_k": 300.0,
            "throughput_sm3_h": 1000.0,
        },
        "equipment": [
            {
                "tag": "K-202",
                "type": "recip_compressor",
                "position_m": [50, 50, 0],
                "rotation_deg": 0,
                "size_m": [12, 4, 3],
                "vents_to": "VS-250",
                "anchors": [
                    {"id": "K-202.packing", "position_m": [48, 50, 1.5], "emission_point": True}
                ],
            },
            {
                "tag": "VS-250",
                "type": "vent_stack",
                "position_m": [60, 80, 0],
                "rotation_deg": 0,
                "size_m": [0.4, 0.4, 12],
                "anchors": [
                    {"id": "VS-250.tip", "position_m": [60, 80, 12], "emission_point": True}
                ],
            },
        ],
        "piping": [
            {"id": "R-1", "service": "vent", "size_in": 2, "waypoints_m": [[48, 50, 2], [60, 80, 1]]}
        ],
        "instruments": [
            {"tag": "AT-1", "kind": "methane_point", "position_m": [90, 50, 2], "noise_ppm": 0.3},
            {"tag": "FT-1", "kind": "flow", "position_m": [60, 78, 1], "attaches_to": "VS-250"},
        ],
    }


@pytest.fixture
def minimal_spec() -> dict[str, Any]:
    """A small valid facility spec as a plain dict."""
    return _minimal_spec()
```

`app/backend/tests/facility/test_loader.py`:
```python
"""Tests for loading the real KS-07 spec."""

from pathlib import Path

import pytest

from plumetrace.facility.candidates import methane_sensors
from plumetrace.facility.loader import DEFAULT_SPEC_PATH, load_facility


def test_real_spec_loads_with_expected_counts() -> None:
    """KS-07 has 24 equipment items, 15 pipe routes, 18 instruments and 8 methane sensors."""
    spec = load_facility()
    assert spec.site.id == "KS-07"
    assert spec.site.fictional is True
    assert len(spec.equipment) == 24
    assert len(spec.piping) == 15
    assert len(spec.instruments) == 18
    assert len(methane_sensors(spec)) == 8


def test_compressors_vent_to_shared_stack() -> None:
    """S1 relies on all three packing vents being routed to VS-250."""
    spec = load_facility()
    for tag in ("K-201", "K-202", "K-203"):
        assert spec.equipment_by_tag(tag).vents_to == "VS-250"


def test_unknown_tag_lookup_raises() -> None:
    """Looking up a missing tag names the tag."""
    with pytest.raises(KeyError, match="K-999"):
        load_facility().equipment_by_tag("K-999")


def test_gas_composition_sums_to_one() -> None:
    """The KS-07 gas composition is normalised."""
    assert abs(sum(load_facility().gas_composition.values()) - 1.0) < 1e-9


def test_loader_reads_utf8(tmp_path: Path) -> None:
    """Non-ASCII text in the YAML loads on every OS (explicit UTF-8)."""
    text = DEFAULT_SPEC_PATH.read_text(encoding="utf-8").replace(
        "description: Control room}", 'description: "Control room – ambient ≈ 25 °C"}'
    )
    path = tmp_path / "ks07.yaml"
    path.write_text(text, encoding="utf-8")
    spec = load_facility(path)
    assert spec.equipment_by_tag("CR-901").description == "Control room – ambient ≈ 25 °C"
```

`app/backend/tests/facility/test_validation.py`:
```python
"""Validation tests: a broken spec fails with a message naming the offending item."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from plumetrace.facility.spec import FacilitySpec

Mutation = Callable[[dict[str, Any]], None]


def test_minimal_spec_is_valid(minimal_spec: dict[str, Any]) -> None:
    """The fixture itself is valid."""
    FacilitySpec.model_validate(minimal_spec)


def _dup_tag(s: dict[str, Any]) -> None:
    s["equipment"].append(dict(s["equipment"][0], anchors=[]))


def _foreign_anchor(s: dict[str, Any]) -> None:
    s["equipment"][0]["anchors"][0]["id"] = "K-999.packing"


def _out_of_bounds(s: dict[str, Any]) -> None:
    s["equipment"][0]["position_m"] = [250, 10, 0]


def _below_ground(s: dict[str, Any]) -> None:
    s["instruments"][0]["position_m"] = [90, 50, -1]


def _pipe_out(s: dict[str, Any]) -> None:
    s["piping"][0]["waypoints_m"][1] = [60, 180, 1]


def _bad_vent(s: dict[str, Any]) -> None:
    s["equipment"][0]["vents_to"] = "VS-999"


def _bad_attach(s: dict[str, Any]) -> None:
    s["instruments"][1]["attaches_to"] = "X-1"


def _bad_sum(s: dict[str, Any]) -> None:
    s["gas_composition"] = {"CH4": 0.94, "N2": 0.05}


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_dup_tag, "duplicate tag K-202"),
        (_foreign_anchor, "K-999.packing"),
        (_out_of_bounds, "K-202"),
        (_below_ground, "AT-1"),
        (_pipe_out, "R-1"),
        (_bad_vent, "VS-999"),
        (_bad_attach, "X-1"),
        (_bad_sum, "0.99"),
    ],
)
def test_invalid_spec_names_the_item(
    minimal_spec: dict[str, Any], mutate: Mutation, expected: str
) -> None:
    """Each broken spec raises a ValidationError whose message names the offending item."""
    mutate(minimal_spec)
    with pytest.raises(ValidationError, match=expected):
        FacilitySpec.model_validate(minimal_spec)


def test_unknown_field_is_rejected(minimal_spec: dict[str, Any]) -> None:
    """Typos in field names are errors, not silently ignored."""
    minimal_spec["equipment"][0]["vent_to"] = "VS-250"
    with pytest.raises(ValidationError):
        FacilitySpec.model_validate(minimal_spec)
```

`app/backend/tests/facility/test_candidates.py`:
```python
"""Tests for the inversion candidate list and the methane sensor list."""

from plumetrace.engineering.geometry import Point3
from plumetrace.facility.candidates import emission_candidates, methane_sensors
from plumetrace.facility.loader import load_facility

EXPECTED_CANDIDATE_IDS = sorted(
    [
        "PIG-101.door", "V-100.psv", "V-211.psv", "V-212.psv", "V-213.psv",
        "K-201.packing", "K-201.engine_exhaust", "K-202.packing", "K-202.engine_exhaust",
        "K-203.packing", "K-203.engine_exhaust", "VS-250.tip", "R-302.still_vent",
        "FG-501.skid", "TK-401.thief_hatch", "TK-402.thief_hatch", "VRU-410.skid",
        "V-602.psv", "FL-601.tip", "M-701.meter", "PIG-702.door",
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
```

`app/backend/tests/facility/test_components.py`:
```python
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
    "classes": {"compressors": {"valves": 1, "connectors": 2, "open_ended_lines": 3,
                                "pressure_relief_valves": 4}},
    "equipment_type_map": {"recip_compressor": "compressors", "vent_stack": None},
}


def test_counts_for_maps_types_and_zero_for_unmapped(minimal_spec: dict[str, Any]) -> None:
    """Mapped types get their class counts; null-mapped types get zeros."""
    counts = counts_for(FacilitySpec.model_validate(minimal_spec),
                        CountsTable.model_validate(FIXTURE_TABLE))
    assert counts["K-202"] == ComponentCounts(valves=1, connectors=2, open_ended_lines=3,
                                              pressure_relief_valves=4)
    assert counts["VS-250"] == ComponentCounts(valves=0, connectors=0, open_ended_lines=0,
                                               pressure_relief_valves=0)


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
```

## Steps
- [ ] **1.** Write all test files. `uv run pytest backend/tests/facility -q` → collection errors (modules missing).
- [ ] **2.** Write `engineering/geometry.py` and the facility modules per the Interfaces, plus both YAML files exactly as shown.
- [ ] **3.** `uv run pytest -q` → all pass (13 earlier + 24 here = 37: loader 5, validation 10 incl. 8 parametrised, candidates 3, components 6). `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean.
- [ ] **4.** Repo checks pass — `check_structure.py` also verifies `facility` imports only `engineering`.
- [ ] **5. Docs.** `docs/reference/SIMULATOR.md` with section `## Facility KS-07`: coordinate convention; table of all 24 equipment items (tag, type, position, size, anchors); the 21 emission candidates; the 18 instruments; the 15 pipe routes (id, service, size); gas composition; operating conditions; component-count source and mapping (copy the `source` and `notes` text); procedural flange/valve rule; validation rules. Add the SIMULATOR.md row to `docs/README.md`. Work-log row; `STATUS.md` (last 1.6, next 1.7).
- [ ] **6. Commit** `feat(facility): add Station KS-07 facility spec, loader and candidates`.
