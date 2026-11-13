# Simulator and facility

Phase 1 Task 6 delivers the facility part. The scenario simulator (S1-S6) is added in Phase 2 and
extends this page. Source of truth for the station: `app/backend/plumetrace/facility/data/ks07.yaml`;
design reference: section 4 (facility, instruments, gas composition).

## Facility KS-07

Station KS-07 is a **fictional**, simulated compressor station (`site.fictional: true`). The
latitude and longitude (39.10, 61.30, Karakum desert region) are used only to fetch real weather.

### Coordinate convention

Metres. x = east, y = north, z = up. Origin = south-west fence corner. The site is 200 m (x) by
150 m (y). All positions in the YAML use this frame; `position_m` is `[x, y, z]`.

An equipment `position_m` is the **footprint centre at its base** (x, y = centre of the footprint, z = bottom of the box). `size_m` is the axis-aligned box (x, y, z) before rotation, centred on `position_m` in x and y and rising from it in z. Anchor and instrument positions are points.

### Modules

| Module (`plumetrace.facility.`) | Responsibility |
|---|---|
| `types` | Frozen Pydantic models (`Equipment`, `Anchor`, `PipeRoute`, `Instrument`, `Site`, `SiteBounds`, `OperatingConditions`) and the enums `EquipmentType`, `InstrumentKind`. Unknown fields are rejected. |
| `spec` | `FacilitySpec` and its validation rules; `equipment_by_tag`. |
| `loader` | `load_facility(path)` reads the YAML as UTF-8 with `yaml.safe_load` and validates it. |
| `candidates` | `emission_candidates(spec)` and `methane_sensors(spec)`, returning `plumetrace.engineering.geometry` types. |
| `components` | Procedural flange and valve placement and the component-count table. |
| `obstacles` | `facility_obstacles(spec)`: buildings and shelters as wake obstacles for the truth model. |

`facility` imports only `plumetrace.engineering` (checked by `check_structure.py`).

### Equipment (24 items)

| Tag | Type | Position (m) | Size (m) | Anchors |
|---|---|---|---|---|
| PIG-101 | pig_trap | (15, 75, 0) | (6, 1.2, 1.5) | `PIG-101.door` |
| V-100 | filter_separator | (30, 75, 0) | (2, 2, 6) | `V-100.psv` |
| V-211 | scrubber | (62, 57, 0) | (1.5, 1.5, 5) | `V-211.psv` |
| V-212 | scrubber | (62, 75, 0) | (1.5, 1.5, 5) | `V-212.psv` |
| V-213 | scrubber | (62, 93, 0) | (1.5, 1.5, 5) | `V-213.psv` |
| K-201 | recip_compressor | (75, 57, 0) | (12, 4, 3) | `K-201.packing`, `K-201.engine_exhaust` |
| K-202 | recip_compressor | (75, 75, 0) | (12, 4, 3) | `K-202.packing`, `K-202.engine_exhaust` |
| K-203 | recip_compressor | (75, 93, 0) | (12, 4, 3) | `K-203.packing`, `K-203.engine_exhaust` |
| E-231 | fin_fan_cooler | (95, 57, 0) | (8, 4, 5) | none |
| E-232 | fin_fan_cooler | (95, 75, 0) | (8, 4, 5) | none |
| E-233 | fin_fan_cooler | (95, 93, 0) | (8, 4, 5) | none |
| VS-250 | vent_stack | (85, 115, 0) | (0.4, 0.4, 12) | `VS-250.tip` |
| T-301 | teg_contactor | (120, 60, 0) | (1.5, 1.5, 15) | none |
| R-302 | teg_regenerator | (130, 50, 0) | (4, 2, 8) | `R-302.still_vent` |
| FG-501 | fuel_gas_skid | (110, 95, 0) | (4, 3, 2) | `FG-501.skid` |
| TK-401 | storage_tank | (150, 110, 0) | (6, 6, 7) | `TK-401.thief_hatch` |
| TK-402 | storage_tank | (165, 110, 0) | (6, 6, 7) | `TK-402.thief_hatch` |
| VRU-410 | vru | (157, 95, 0) | (4, 3, 2.5) | `VRU-410.skid` |
| V-602 | knockout_drum | (175, 30, 0) | (6, 2, 2.5) | `V-602.psv` |
| FL-601 | flare_stack | (185, 30, 0) | (1, 1, 30) | `FL-601.tip` |
| M-701 | meter_run | (175, 75, 0) | (10, 2, 1.5) | `M-701.meter` |
| PIG-702 | pig_trap | (190, 75, 0) | (6, 1.2, 1.5) | `PIG-702.door` |
| CR-901 | building | (30, 20, 0) | (15, 8, 4) | none |
| MCC-902 | building | (50, 20, 0) | (10, 6, 4) | none |

Compressors K-201, K-202 and K-203 are in shelters and vent to VS-250. CR-901 is the control room
and MCC-902 the motor control centre.

### Emission candidates (21)

Every anchor with `emission_point: true` is a candidate source for the inversion, sorted by id.

| Candidate id | Position (m) |
|---|---|
| `FG-501.skid` | (110, 95, 1.5) |
| `FL-601.tip` | (185, 30, 30) |
| `K-201.engine_exhaust` | (80, 57, 6) |
| `K-201.packing` | (73, 57, 1.5) |
| `K-202.engine_exhaust` | (80, 75, 6) |
| `K-202.packing` | (73, 75, 1.5) |
| `K-203.engine_exhaust` | (80, 93, 6) |
| `K-203.packing` | (73, 93, 1.5) |
| `M-701.meter` | (175, 75, 1) |
| `PIG-101.door` | (12, 75, 1) |
| `PIG-702.door` | (193, 75, 1) |
| `R-302.still_vent` | (130, 50, 8) |
| `TK-401.thief_hatch` | (150, 110, 7) |
| `TK-402.thief_hatch` | (165, 110, 7) |
| `V-100.psv` | (30, 75, 6) |
| `V-211.psv` | (62, 57, 5) |
| `V-212.psv` | (62, 75, 5) |
| `V-213.psv` | (62, 93, 5) |
| `V-602.psv` | (175, 30, 4) |
| `VRU-410.skid` | (157, 95, 1.5) |
| `VS-250.tip` | (85, 115, 12) |

### Instruments (18)

| Tag | Kind | Position (m) | Attaches to | Noise (ppm) |
|---|---|---|---|---|
| AT-101 | methane_point | (5, 5, 2) | - | 0.3 |
| AT-102 | methane_point | (100, 5, 2) | - | 0.3 |
| AT-103 | methane_point | (195, 5, 2) | - | 0.3 |
| AT-104 | methane_point | (195, 75, 2) | - | 0.3 |
| AT-105 | methane_point | (195, 145, 2) | - | 0.3 |
| AT-106 | methane_point | (100, 145, 2) | - | 0.3 |
| AT-107 | methane_point | (5, 145, 2) | - | 0.3 |
| AT-108 | methane_point | (110, 75, 2) | - | 0.3 |
| MET-01 | met_mast | (10, 140, 10) | - | - |
| FT-250 | flow | (85, 110, 1) | VS-250 | - |
| TT-201P | temperature | (73, 57, 1.5) | K-201 | - |
| TT-202P | temperature | (73, 75, 1.5) | K-202 | - |
| TT-203P | temperature | (73, 93, 1.5) | K-203 | - |
| FT-601 | flow | (178, 30, 1) | FL-601 | - |
| TE-601 | thermocouple | (185, 30, 29.5) | FL-601 | - |
| PT-401 | pressure | (150, 110, 7) | TK-401 | - |
| PT-402 | pressure | (165, 110, 7) | TK-402 | - |
| FT-701 | flow | (175, 75, 1) | M-701 | - |

The eight `methane_point` sensors (AT-101 to AT-108) feed `methane_sensors`; each must have
`noise_ppm`.

### Pipe routes (15)

| Id | Service | Size (in) | Waypoints |
|---|---|---|---|
| R-100 | gas | 24 | 3 |
| R-110 | gas | 20 | 2 |
| R-111 | gas | 12 | 3 |
| R-112 | gas | 12 | 3 |
| R-113 | gas | 12 | 3 |
| R-121 | gas | 10 | 3 |
| R-122 | gas | 10 | 3 |
| R-123 | gas | 10 | 3 |
| R-130 | gas | 20 | 2 |
| R-140 | gas | 20 | 3 |
| R-150 | gas | 20 | 4 |
| R-250 | vent | 2 | 5 |
| R-600 | flare | 12 | 4 |
| R-400 | condensate | 4 | 4 |
| R-500 | fuel_gas | 2 | 2 |

### Gas composition (mole fraction)

**Source:** none; illustrative pipeline-quality composition chosen by the owner at Gate 1 (2026-11-13), inside the design range CH4 0.90-0.95; not from a cited gas analysis; the station is simulated.

| Species | Fraction |
|---|---|
| CH4 | 0.930 |
| C2H6 | 0.035 |
| C3H8 | 0.008 |
| nC4H10 | 0.002 |
| CO2 | 0.010 |
| N2 | 0.015 |

### Operating conditions and site

| Quantity | Value |
|---|---|
| Suction pressure (absolute) | 4.5e+06 Pa |
| Discharge pressure (absolute) | 7e+06 Pa |
| Gas temperature | 300 K |
| Throughput | 41667 sm3/h |
| Ambient pressure (absolute) | 98900 Pa |
| Ground elevation | 200 m |

All pressures are absolute, not gauge: the Phase 2 Z factor and blowdown use absolute pressure. 98900 Pa matches the ISA (ISO 2533) value at 200 m (98.95 kPa).

### Procedural flanges and valves

`place_route_components(spec, spacing_m=FLANGE_SPACING_M)` (12 m) places, for each route in spec
order: a **flange** at every waypoint and at every multiple of the spacing measured along the
polyline (positions interpolated on the segment; points closer than 1e-6 m are merged), and a
**valve** at the first and last waypoint. Components are ordered by distance along the route, a
flange before a valve at equal distance. The result is deterministic; the 3D scene and the
candidate generation depend on that.

### Component counts

`component_counts.yaml` holds default component counts per equipment class; `counts_for(spec, table)`
maps each equipment tag to the counts of its class (types mapped to `null` get zeros).

**Source:** 40 CFR Part 98, Subpart W, Table W-1B "Default Average Component Counts for Major Onshore Natural Gas Production Equipment and Onshore Petroleum and Natural Gas Gathering and Boosting Equipment", CFR 2023 edition (govinfo package CFR-2023-title40-vol23), [75 FR 74488, Nov. 30, 2010, as amended at 80 FR 64298, Oct. 22, 2015]. The table was removed in the 2024 Subpart W revision (89 FR 42323-42325, May 14, 2024); it is the latest published set of default component counts. Accessed 2026-11-12.

**Column used:** Western U.S.

**Notes:** Production / gathering-and-boosting default counts are used as a documented proxy for a transmission compressor station, for which no default counts are published. The TEG regenerator is counted with the contactor as one dehydrator. Accepted by the owner at Gate 1 (2026-11-13) as a proxy. The numbers were transcribed from the CFR 2023 edition and are not yet verified against the primary text (see docs/OWNER_ACTIONS.md).

**Proxy:** not verified against the primary source.

| Class | Valves | Connectors | Open-ended lines | Pressure relief valves |
|---|---|---|---|---|
| wellheads | 11 | 36 | 1 | 0 |
| separators | 34 | 106 | 6 | 2 |
| meters_piping | 14 | 51 | 1 | 1 |
| compressors | 73 | 179 | 3 | 4 |
| in_line_heaters | 14 | 65 | 2 | 1 |
| dehydrators | 24 | 90 | 2 | 2 |

| Equipment type | Class |
|---|---|
| pig_trap | meters_piping |
| filter_separator | separators |
| scrubber | separators |
| recip_compressor | compressors |
| fin_fan_cooler | none (zeros) |
| vent_stack | none (zeros) |
| teg_contactor | dehydrators |
| teg_regenerator | none (zeros) |
| fuel_gas_skid | meters_piping |
| storage_tank | none (zeros) |
| vru | compressors |
| knockout_drum | separators |
| flare_stack | none (zeros) |
| meter_run | meters_piping |
| building | none (zeros) |

### Obstacles

`plumetrace.facility.obstacles.facility_obstacles(spec)` turns the spec into the list of
`WakeObstacle` objects that the truth model uses for building wakes (see "Truth model" in
`docs/reference/ENGINEERING.md`). Every equipment of type `building` and every equipment with
`shelter: true` is one obstacle, in spec order: centre = footprint centre (x, y), half width =
`max(size_x, size_y) / 2`, height = `size_z` for a building and `SHELTER_HEIGHT_M = 6.0` m for a
shelter (a Task 12 project value). A building that is also flagged as a shelter is listed once, as
a building. Rotation is ignored.

| Obstacle | Centre (x, y) m | Half width m | Height m | Wake length (3 x height) m |
|---|---|---|---|---|
| K-201 shelter | 75, 57 | 6.0 | 6.0 | 18 |
| K-202 shelter | 75, 75 | 6.0 | 6.0 | 18 |
| K-203 shelter | 75, 93 | 6.0 | 6.0 | 18 |
| CR-901 control room | 30, 20 | 7.5 | 4.0 | 12 |
| MCC-902 motor control centre | 50, 20 | 5.0 | 4.0 | 12 |

A receptor is in a wake when it is up to three heights downwind of the centre and within the half
width across the wind. The shelter height is not the real roof height of the compressor (the box
is 3 m high); it stands for the building envelope around the unit.

### Validation rules

`FacilitySpec` runs these checks in order; each failure names the offending item.

1. Tags are unique across equipment and instruments (`duplicate tag <tag>`).
2. Every anchor id starts with `<equipment tag>.` (`anchor <id> does not belong to equipment <tag>`).
3. Equipment, anchor, instrument positions and every pipe waypoint are inside the site bounds and
   not below ground (`<owner> position <p> is outside the site bounds`).
4. `vents_to` and `attaches_to` name existing equipment (`<tag> vents_to unknown tag <x>`).
5. The gas composition sums to 1 within 1e-6 (`gas_composition sums to <total>, expected 1`).

Unknown fields anywhere in the YAML are rejected, so a typo is an error. The Gate 1 owner review
of `ks07.yaml`, the gas composition, `component_counts.yaml` and the emission sources is listed
in `docs/OWNER_ACTIONS.md`.

### Gate 1 decisions (2026-11-13)

- **Location:** the site is fictional. The check against Carbon Mapper coverage is deferred to Phase 8 Task 4.
- **Emission candidates:** the 21 are kept. Packing (into the shelter) and `VS-250.tip` (via the header) are separate by design. Pneumatics and blowdown are not candidates: scenario S4 releases at `VS-250.tip` and `blowdown.py` quantifies it.
- **Methane sensors:** the eight are kept. `PIG-101.door` and `V-100.psv` are about 70-75 m from AT-101 and AT-107. The benchmark reports per-candidate results, and Gate 2 decides on any extra sensor.
- **Pipe ends:** the gaps at the ends of R-140 and R-500 (about 1.25 m and 0.5 m) are cosmetic and handled in Phase 4.

Gate 1 is signed off.
