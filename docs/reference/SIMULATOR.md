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

## Weather

The plumes are driven by real hourly weather for the site's coordinates (design section 8). The
data is fetched once, committed as a snapshot and read offline, so every scenario is reproducible.
The station is simulated; **the weather is real** and is labelled real and attributed.

| Item | Value |
|---|---|
| Source | Open-Meteo historical weather API (ERA5 reanalysis), `https://archive-api.open-meteo.com/v1/archive`, no API key |
| Verified against | The official Open-Meteo documentation and licence pages, 2026-11-14: endpoint, variable names, units, `wind_speed_unit` options (default `kmh`) and `timezone` (default GMT) |
| Location | `site.latitude_deg`, `site.longitude_deg` of KS-07 (39.10, 61.30; the site itself is fictional) |
| Period | 2025-07-14 to 2025-07-20 inclusive, UTC, 168 hours; `start_utc` is `2025-07-14T00:00:00Z` |
| Snapshot file | `app/backend/plumetrace/simulator/data/weather_ks07_2025-07-14_2025-07-20.json` (generated, never hand-edited) |
| Licence | CC BY 4.0 (API data). Free for non-commercial use within the published rate limits |
| Attribution text | `Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis.` (constant `ATTRIBUTION`, stored in the snapshot). Open-Meteo asks for a link next to any place its data is shown; the UI must link the text to <https://open-meteo.com/> |

### Fields and conversions

The request asks for `wind_speed_unit=ms` and `timezone=UTC`, so the wind needs no conversion. The
client refuses a response whose `hourly_units` says the wind is not in m/s.

| Open-Meteo variable | Unit as requested | `HourlyWeather` field | Conversion |
|---|---|---|---|
| `wind_speed_10m` | m/s | `wind_speed_m_s` | none |
| `wind_direction_10m` | degrees, direction the wind blows from | `wind_from_deg` | none |
| `shortwave_radiation` | W/m2 (mean of the preceding hour) | `shortwave_w_m2` | none |
| `cloud_cover` | percent | `cloud_fraction` | divide by 100 |
| `temperature_2m` | degrees C | `temp_k` | add 273.15 |

`hour_index` is the position in the series (0, 1, 2, ...).

### Modules

| Module | Responsibility |
|---|---|
| `plumetrace.data_sources.open_meteo` | `fetch_hourly(client, lat, lon, start, end)`: one GET, validation, unit conversion. Constants `ARCHIVE_URL`, `HOURLY_FIELDS`, `TIMEOUT_S`, `ATTRIBUTION`; error `OpenMeteoError`. The only network code for weather |
| `plumetrace.simulator.weather` | `load_snapshot(path)` reads and validates the committed file; `slice_hours(snapshot, offset_h, hours)` returns re-indexed hours |
| `scripts/fetch_weather.py` | Fetches the week and writes the snapshot (UTF-8, LF, sorted keys, indent 2) |

### What is rejected

| Situation | Result |
|---|---|
| `end` before `start` | `ValueError`, no request is sent |
| HTTP error, timeout | `httpx.HTTPError` subclass, raised to the caller |
| Body is not the expected JSON, no `hourly` block | `OpenMeteoError` |
| `null` value, missing field, field shorter than the time axis | `OpenMeteoError` naming the field (and the time) |
| Time axis empty, not starting at `start` 00:00, or not hourly | `OpenMeteoError` |
| NaN, negative wind or radiation, cloud outside 0-100 % | `OpenMeteoError` naming the time |
| Wrong number of hours (script: not 168) | the script exits 1 and writes nothing |
| Snapshot with a `null`, a blank attribution, no hours, a naive `start_utc` or `hour_index` not 0..n-1 | `ValueError` from `load_snapshot` |
| `slice_hours` with a negative offset, fewer than 1 hour, or more hours than the snapshot has | `ValueError` (`snapshot has N hours, need M`) |

### How to refresh

```
cd app && uv run python ../scripts/fetch_weather.py
```

This makes one real request to the public API (free, no key, no cost). If it fails the script
prints the reason and keeps the existing file; do not edit the JSON by hand. Review the diff
before committing: the weather changes every scenario that uses these hours. Outbound-network
controls are in `docs/reference/SECURITY.md`.

## Instruments

`plumetrace.simulator.instruments` produces the non-methane process readings that triage and
fusion use as evidence (design section 4). It is pure simulation: no network, no database, and
deterministic for a seed because the caller passes the `numpy` generator. The baselines are
**Task 3 values** (chosen for the simulation, not taken from a published source). The station is
simulated and so are these readings.

### Tags

| Tag | Meaning | Unit | Baseline mean | Noise sd |
|---|---|---|---|---|
| `FT-250` | Packing vent header flow (VS-250), whole gas | kg/h | 0.9 | 0.25 |
| `TT-201P` | Packing case temperature, K-201 | degC | 80.0 | 0.5 |
| `TT-202P` | Packing case temperature, K-202 | degC | 80.0 | 0.5 |
| `TT-203P` | Packing case temperature, K-203 | degC | 80.0 | 0.5 |
| `FT-601` | Flare header flow (FL-601), whole gas | kg/h | 5.0 | 0.5 |
| `TE-601` | Flare pilot thermocouple | degC | 600.0 | 10.0 |
| `PT-401` | Tank TK-401 pressure | kPag | 2.0 | 0.05 |
| `PT-402` | Tank TK-402 pressure | kPag | 2.0 | 0.05 |
| `FT-701` | Throughput meter M-701 | Sm3/h | 41667.0 | 200.0 |

### Effect model

`simulate_instruments(times_s, effects, rng)` returns a dict of tag to series (float64, same
length as `times_s`, always finite). For every tag, in table order, it draws
`rng.normal(0, noise_sd, n)` (always, so a run with effects stays aligned with a run without),
starts from the mean, applies the effects on that tag in the order given, and adds the noise last.

An `InstrumentEffect` has a `tag`, a `kind`, a `value`, a window `[start_s, end_s)` (`end_s`
defaults to infinity) and `ramp_s`. Its weight is `w(t) = 0` before `start_s` or at/after
`end_s`, else `min(1, (t - start_s) / ramp_s)` (1 when `ramp_s == 0`).

| Kind | Result |
|---|---|
| `offset` | `value += w * effect.value` |
| `set` | `value = (1 - w) * value + w * effect.value` (noise is still added, so a pilot "out" reads about 30 degC plus noise) |

### Packing-leak signature

`packing_leak_effects(unit_tag, ch4_rate_kg_h, ch4_mass_fraction, start_s, ramp_s=1800)` gives
two ramped offsets for a leak on `K-20n`:

- `FT-250` rises by `ch4_rate_kg_h / ch4_mass_fraction`. The header meter reads **whole gas**, not
  methane, so the methane rate is divided by the methane mass fraction (15 kg/h CH4 at 0.8623 is
  +17.395 kg/h).
- `TT-20nP` rises by +6.0 degC (a Task 3 value). A leaking packing runs hot, and the temperature
  of the leaking unit is what separates K-201, K-202 and K-203.

### What is rejected

| Situation | Result |
|---|---|
| Effect on a tag not in the table | `KeyError("unknown instrument <tag>")` |
| `times_s` empty, not 1-D or not finite | `ValueError` |
| Effect with a `kind` other than `offset`/`set`, non-finite `value` or `start_s`, NaN `end_s`, `end_s <= start_s`, or `ramp_s` negative or not finite | `ValueError` naming the tag; nothing is drawn from the generator |
| `packing_leak_effects` with a `unit_tag` that is not `K-201` to `K-203`, a non-positive or non-finite rate, a mass fraction outside (0, 1], a non-finite start or a bad ramp | `ValueError` |

The simulator never returns NaN. Sensor dropout is not modelled here.

## Scenarios: model and runner

`plumetrace.simulator.scenario` holds the scenario definition and `plumetrace.simulator.runner`
runs it. Both are pure simulation: no network, no database, deterministic for a seed. The station
and the scenarios are simulated. All models are frozen and reject unknown fields.

### Model (`scenario.py`)

| Model | Fields (unit) | Rejected |
|---|---|---|
| `SourceSpec` | `anchor_id`, `rate_kg_h` (kg/h, >= 0), `start_s` (s, >= 0), `end_s` (s, default infinity, exclusive) | non-finite rate or start, `end_s` not after `start_s` |
| `FaultSpec` | `sensor_id`, `drift_ppm_per_h` (ppm/h, may be negative), `start_s` (s, >= 0) | non-finite drift or start |
| `InstrumentEffectSpec` | `tag`, `kind` (`offset` or `set`), `value`, `start_s`, `end_s`, `ramp_s` (s); `to_effect()` gives the `InstrumentEffect` | tag not in `BASELINES`, non-finite value or start, `end_s` not after `start_s`, bad ramp |
| `LogEntry` | `t_s` (s, >= 0), `kind` (permit, gauging, maintenance, shift_note, calibration), `tag`, `text` | infinite time, blank text |
| `ExpectedOutcome` | `triage` (leak, sensor_fault, planned_venting), `top_candidate`, `attributed_unit`, `rate_min_kg_h`, `rate_max_kg_h`, `rule_ids` | one rate bound without the other, non-finite, negative or `min > max` |
| `ScenarioDefinition` | `id` (`s<digits>_<lowercase words>`), `title`, `seed` (>= 0), `weather_offset_h` (>= 0), `duration_h` (1-24), `sources`, `faults`, `instrument_effects`, `log`, `expected`, `variant_index` | unsorted `log`, any source, fault or effect start at or after the end, a log time after the end, a negative seed |

Time model: every `t_s`, `start_s` and `end_s` is seconds from the scenario start. Second 0 is
`snapshot.start_utc + weather_offset_h` hours (`ScenarioRun.sim_start_utc`). The step is
`DT_S = 10.0` s. Several effects on one instrument overlap freely and are applied in list order
(see "Effect model"); several faults on one sensor add up.

The expected rate is stored only as an interval, never a single number, so a UI that shows it
follows the rate display rule (interval, never a point value). The interval is the design intent,
not a model output.

### Runner (`runner.py`)

`run_scenario(definition, spec, snapshot)` does, in this order:

1. `rng = numpy.random.default_rng(definition.seed)`.
2. Slices `duration_h + 1` weather hours from `weather_offset_h` (`slice_hours`). A snapshot that
   is too short raises `ValueError` naming the scenario and the hours needed, for example
   `scenario s9_long_one needs 173 weather hours (...), snapshot has 168`.
3. Maps each source to a `TrueSource` at the emission-point anchor `anchor_id`; an unknown anchor
   raises `KeyError("unknown anchor <id>")`. A fault on an unknown sensor raises `ValueError`.
4. `simulate_sensors` with the default `TruthConfig`, the facility obstacles and the faults.
5. `simulate_instruments` with the same `rng`.
6. 10-minute window means, wind (mean speed, circular mean direction) and the most frequent
   stability class per window (`window_mode_class`).
7. `detect_events` on the absolute window means, with the site centre
   (`site_center_xy`, the centre of the site bounds, `(100, 75)` for KS-07) and the window wind
   directions. Detection holds a sensor for six windows after an event, so one sensor never has two
   events inside that period.

Random-draw order: the generator draws first inside `simulate_sensors` (one block of
`steps x (2 + sensors)` standard normals, whatever the sources), then inside
`simulate_instruments` (one normal series per tag in `BASELINES` order). So the instrument series
do not change when a source is added. Same seed, same definition, same snapshot gives identical
arrays and events.

`ScenarioRun` holds the definition, `sim_start_utc`, the sensors, the 10 s `series`
(`TruthSeries`), the instrument series, the window arrays (start, means, wind speed, wind
direction, stability) and the events. For the meander-aware inversion (adopted at Gate 2) the
caller builds `wind_dir_sd_deg` from `series.times_s` and `series.wind_from_deg` with
`window_direction_sd_deg`, one value per window; the runner itself does not call the inversion.

### What is rejected

| Situation | Result |
|---|---|
| Invalid number, window or id in a model | `pydantic.ValidationError` (a `ValueError`) |
| Source on an unknown or non-emission anchor | `KeyError("unknown anchor <id>")` |
| Fault on an unknown sensor | `ValueError` naming it |
| Scenario longer than the weather snapshot | `ValueError` naming the scenario and the hours needed |

## MVP scenarios

The three demo stories (design section 7) live in `plumetrace.simulator.scenarios`
(`s1_rod_packing.py`, `s4_planned_blowdown.py`, `s5_sensor_drift.py`). `SCENARIOS` is a read-only
mapping from id to `ScenarioDefinition`; `get_scenario(id)` raises `KeyError("unknown scenario <id>")`.
The station and all three stories are simulated. Titles, the instrument signature and the
expected-rate interval are Task 5 values (no cited source); the log texts are the Task 5 texts.
Every scenario is deterministic for its seed on the committed weather snapshot.

### Values

| | S1 `s1_rod_packing` | S4 `s4_planned_blowdown` | S5 `s5_sensor_drift` |
|---|---|---|---|
| Story | K-202 rod-packing leak, routed through the vent header to VS-250 | Planned blowdown of K-201 under permit PTW-0412, vented to VS-250 | Slow drift on AT-106; no methane released |
| Seed | 101 | 104 | 105 |
| Duration | 6 h | 4 h | 6 h |
| `WEATHER_OFFSET_H` | 0 | 0 | 0 |
| Source | `VS-250.tip`, 15.0 kg/h from 7200 s, no end | `VS-250.tip`, 933.67 kg/h from 7200 s to 8100 s | none |
| Fault | none | none | `AT-106`, 0.6 ppm/h from 3600 s |
| Instrument effects | FT-250 offset +17.39 kg/h (CH4 rate / CH4 mass fraction of the KS-07 gas), TT-202P offset +6.0 degC; both ramp over 1800 s from 7200 s | none | none |
| Expected | triage `leak`, top candidate `VS-250.tip`, unit `K-202`, rate interval 7.5 to 30.0 kg/h | triage `planned_venting`, no top candidate | triage `sensor_fault`, no top candidate |

Log lines (`t_s`, kind, tag, text), exactly as in the files:

- S1: (600, shift_note, none, "Day shift handover: K-201, K-202 and K-203 running; VRU-410 online."), (4000, gauging, TK-402, "TK-402 gauged by the operator; thief hatch closed and latched after gauging."), (5000, maintenance, AT-103, "Instrument technician completed a routine check of AT-103.").
- S4: (6600, permit, K-201, "PTW-0412: planned blowdown of K-201 for discharge valve maintenance, vented to VS-250; venting starts 10 minutes after this entry and lasts about 15 minutes."), (9000, maintenance, K-201, "K-201 discharge valve replaced; unit restarted.").
- S5: (300, calibration, AT-106, "AT-106 last bump test 2025-03-02; next test overdue."), (3000, shift_note, none, "No work permits open on the north fence today.").

S4 blowdown size: `BLOWDOWN_VOLUME_M3 = 8.0` goes through the engineering tool `vented_mass` from the
suction pressure (4.5 MPa absolute) at the operating gas temperature (300 K) down to the site ambient
pressure (98.9 kPa) at the same temperature, with the KS-07 gas composition. Result:
`S4_VENTED_CH4_KG = 233.42 kg` of methane. The source rate is that mass divided by 0.25 h, so the
15 minute source (7200 s to 8100 s) releases exactly that mass. The constant is exported for the tests and
for the agents' `log_vented_volume` tool. The permit text is relative to its own entry ("venting starts
10 minutes after this entry and lasts about 15 minutes"), which matches the 600 s lead (entry at 6600 s,
source from 7200 s) and the 900 s duration, and stays true when a variant moves the entry.

### Weather windows: how they were selected

The window is not guessed. `simulator/selection.py` holds one criterion per story and
`scripts/select_scenario_windows.py` evaluates every candidate offset
(`CANDIDATE_OFFSETS_H`: every 2 h from 0 to 160 h; an offset is skipped when
`offset + duration_h + 1` exceeds the 168 snapshot hours) with the scenario run on the real weather.
The **first** passing offset is the one written into the scenario file. The script reads only the committed
snapshot (no network) and prints `<scenario>: offset <h> h PASS|FAIL` for each candidate, then
`<scenario>: first passing offset <h> h`; the exit code is 1 if a scenario has none. Run:
`cd app && uv run python ../scripts/select_scenario_windows.py`.

| Scenario | Criterion (all must hold) | Why |
|---|---|---|
| S1 `s1_passes` | (a) a detection event on any methane sensor starts between 7200 s and 7200 + 5400 s; (b) mean window wind speed over windows 12 to 35 is at least 2.0 m/s; (c) the meander-aware inversion (Briggs rural, default constants) over windows 12 to `first_event.window_index + 3`, both ends included, with the background taken as the 5th percentile of each sensor over windows 0 to 11, ranks `VS-250.tip` first and is not inconclusive | (a) the leak must be seen soon after it starts; (b) calm air gives no usable plume; (c) the story needs the location to be found from the first event |
| S4 `s4_passes` | an event with window start between 7200 s and 8100 + 1200 s, and no event before 7200 s | the blowdown is seen during its window and nothing is seen before it, so the permit explains the only event |
| S5 `s5_passes` | at least one `AT-106` event and no event on any other sensor | only the drifting sensor may alarm |

Meander-aware inversion (Gate 2 decision): the S1 inversion input carries
`wind_dir_sd_deg = window_direction_sd_deg(series.times_s, series.wind_from_deg)`, computed over the whole
10 s wind series and cut to the same windows as the observations (one value per complete window, 36
for 6 h). An infinite spread (directions that cancel exactly in a window) is rejected by `InversionInput`
and raised as `ValueError` instead of being hidden. Reading of the plan text: "windows `[12, first_event.window_index + 3]`"
includes both ends.

Result of the selection run on the committed snapshot (full output in the work log): S1 passes at
offsets 0, 2, 24, 26, 28, 34, 36, 122, 124 and 128 h; S4 passes at 77 of the 81 candidates (fails at
74, 94, 116 and 118 h); S5 passes at every candidate. The first passing offset is **0 h** for all
three, so every `WEATHER_OFFSET_H` is 0.
The S4 and S5 pass criteria are loose: they pass at almost every candidate offset, so the selection
does not discriminate between windows for these two scenarios; the first passing offset (0 h) is a
default, not an optimum.

| Scenario | Offset | Scenario start (UTC) |
|---|---|---|
| S1 | 0 h | 2025-07-14 00:00 |
| S4 | 0 h | 2025-07-14 00:00 |
| S5 | 0 h | 2025-07-14 00:00 |

The weather is the first hours of the real week (Open-Meteo, CC BY 4.0). Offset 0 is midnight UTC,
about 05:00 local time at the site longitude (the site is fictional); the plan's log texts say
"Day shift handover" and were kept as given.

### Detection and the S1 inversion at the selected window (truth physics)

| Scenario | Events (sensor, window start) |
|---|---|
| S1 | AT-101 at 7800 s (mean 2.06 ppm), AT-102 at 10200 s, AT-101 at 16800 s |
| S4 | AT-101 and AT-102 at 7200 s |
| S5 | AT-106 at 7800 s and at 14400 s |

S1 first event: AT-101, window 13 (7800 s). The mean wind over windows 12 to 35 is 3.86 m/s. The
meander-aware inversion over windows 12 to 16 (5 windows) gives top `VS-250.tip`, model probability
0.912 (model probability), model estimate of the rate 15–39 kg/h (median 24), not inconclusive, not at
the grid edge. The second candidate is `K-203.engine_exhaust` (model probability 0.079). Rates are shown
to 2 significant figures; the meaning of "model estimate" and the limits of these probabilities are in
[`docs/benchmark-improvement.md`](../benchmark-improvement.md).

Caveat (Gate 2): the meander-aware correction models the same wind-direction process the truth model
injects into the simulated data, so this result is optimistic and partly self-consistent for a simulated
station; it is not evidence of real-world accuracy. Probabilities are model probabilities, not calibrated.

### Rate display rule (R1-R4) for S1

- The expected rate is stored only as the interval 7.5 to 30.0 kg/h in `ExpectedOutcome`
  (`rate_min_kg_h`, `rate_max_kg_h`); no single expected rate exists. The 15.0 kg/h in `SourceSpec` is the
  simulation input (the truth), never shown as an AI result.
- An inversion rate is shown as `p05 to p95 kg/h (median p50)` (R1) with the label "model estimate" (R3).
  It is shown as "rate not quantified" when the result is inconclusive, the top is `NONE` or
  `rate_at_grid_edge` is true (R2).
- S1 outcome under this rule: the result at the selected window is conclusive and not at the grid edge, so it
  is shown as an interval (15–39 kg/h, median 24, a model estimate). The interval contains the true 15.0 kg/h; its
  upper end is above the designed 30.0 kg/h bound. No grid-edge issue arises, so there is no Gate 3
  scenario issue on this point. The probability 0.912 is a model probability (see the Gate 2 caveat above).
- For information only (scratch check, not part of the pipeline): the same windows without the direction
  spread give the same top candidate (model probability 0.712) but a model estimate interval of
  96–390 kg/h. This is a scratch comparison only, not a result of the pipeline.

## Replay export

`plumetrace.simulator.export.build_replay(run, spec, attribution)` turns a scenario run into the
replay document (`plumetrace.simulator.replay_schema.ReplayScenario`), and `replay_bytes` writes it
as deterministic JSON (compact, sorted keys, UTF-8, LF, at most 5 MB, else `ValueError`).
`scripts/export_scenarios.py` runs every registered scenario and writes
`app/replay/scenarios/<id>.json` (generated, never edited by hand). The full format, the grid
encoding, the size budget and how to regenerate are in `docs/reference/REPLAY.md`.

- Series are 60 s means (sensors, the nine instruments, wind); key frames every 120 s are drawn with
  the **truth** coefficients (`TruthConfig().coeff`) and the 60 s wind at that time.
- The file carries `simulated: true`, the Open-Meteo credit (the weather is real public data) and
  the sentence that the station, sensors, instruments and scenario are synthetic.
- The replay holds no inversion result. The rate display rule (R1 to R4, above) applies to any
  result added later: interval only, "not quantified" when inconclusive, top `NONE` or at the grid
  edge, "model estimate" and "model probability" wording. `keyframes[].sources[].rate_kg_h` is the
  simulation input used to draw the plume, never shown as a result.
- Sizes on 2026-11-15: S1 445 852 bytes, S4 294 773 bytes, S5 440 244 bytes.

## Saving a run and the Phase 3 evidence

`plumetrace.api.run_store.save_scenario_run` writes a scenario run (run row, detection events and 60 s
readings of every sensor and instrument) to the local database; see "Saving scenario runs" in
`DATABASE.md`. The numbers of the three MVP scenarios (selected offset and UTC start, detection events,
the S1 inversion on the event windows and the replay file sizes) are recorded in
`docs/evidence/2026-11-phase-3-scenarios.md`, with the throwaway snippet and its output. The inversion
there is shown as a model estimate interval with a model probability, as the rate display rule requires.
Re-saving a scenario run creates a new run (a new run id with its own rows). A saved run stays
`status = 'running'` with `finished_at` null: known and accepted at Gate 3; Phase 5 Task 10 ends every
run in a terminal status.

## Variants

`plumetrace.simulator.variants.generate_variants(base, n=20, seed=VARIANT_SEED)` turns one MVP scenario
into a family of randomised variants. The agent evaluation (Phase 5) runs the agents on every variant so
the result does not rest on one hand-picked story (design section 6). The station and every variant are
simulated. The ranges and distractor texts below are Task 6 values (no cited source).

### What varies and why

| Parameter | Range | Why |
|---|---|---|
| `weather_offset_h` | integer, 0 to 168 - `duration_h` - 1 (the run fits the 168 h snapshot) | different wind speed, direction and stability |
| rate scale | log-uniform in `RATE_SCALE_RANGE` = 0.5 to 2.0 | leak sizes from half to double the base rate; log-uniform so halving and doubling are equally likely |
| time shift | uniform in `TIME_SHIFT_RANGE_S` = -1800 s to +1800 s | the event does not always start at the same minute |
| distractor log entries | 0 to 2 of the six in `DISTRACTOR_LOG`, each at a random time inside the run | irrelevant but plausible lines the agent must ignore |
| `seed` | integer 0 to 2^31 - 1 | different sensor noise and wind-direction wander |

What the scale multiplies: every source `rate_kg_h`, the `offset` value of the FT-250 effects (the vent
header signature scales with the leak) and the expected rate interval. What the shift moves: source,
instrument-effect and fault start times (and finite end times), and every base log entry. Source and fault
starts and source ends are clamped at 0; log entry times are clamped to 0 to the scenario length. The
distractor entries stay where they were drawn. The temperature effects (TT-20xP) are shifted but not scaled.

### Draw order

The generator is `np.random.default_rng([seed, h])` with `h` the first four bytes of the SHA-256 of
`base.id` as a big-endian integer, so two scenarios with the same seed draw differently. For each variant
`i` in `range(n)` it draws, in this order: (1) `offset`, (2) `scale = exp(uniform(ln 0.5, ln 2.0))`,
(3) `shift = uniform(-1800, 1800)`, (4) `k = integers(0, 3)` then `choice(6, size=k, replace=False)` and one
`uniform(0, duration_h * 3600)` time per chosen entry, (5) the variant seed `integers(2**31)`. The same
base, `n` and seed give identical variants, and the first `m` variants of a family do not depend on `n`.

### Distractor list

1. `shift_note`: "Radio check with the dispatch centre completed."
2. `maintenance` E-232: "Fin-fan E-232 belt tension checked; no action needed."
3. `gauging` TK-401: "TK-401 gauged; hatch closed and latched."
4. `calibration` AT-102: "AT-102 bump test passed."
5. `shift_note`: "Contractor vehicle entered the site for scaffolding inspection."
6. `maintenance` FG-501: "Fuel gas filter differential pressure logged at 0.3 bar."

### Ids and expected outcomes

- A variant keeps the base `id`; `(id, variant_index)` with `variant_index` 0 to `n - 1` is its unique,
  stable key (the same inputs always give the same key and content).
- The expected outcome comes from the scenario design, never from running the inversion: triage class,
  top candidate and attributed unit are those of the base. The expected rate interval is the base interval
  multiplied by the variant's rate scale (for S1, 7.5 to 30.0 kg/h times 0.5 to 2.0). No variant stores a
  single point rate for display (rate display rule R1-R4); S4 and S5 have no expected rate.
- The variant code never calls the inversion.

### Validation

`model_copy(update=...)` does not validate, so every generated variant is re-validated with
`ScenarioDefinition.model_validate(variant.model_dump())`. A shift that pushes a start to or past the end
of the scenario, or collapses a source window to zero length at t = 0, raises `pydantic.ValidationError`
(a `ValueError`) instead of returning an invalid scenario. A negative `n` raises `ValueError`. The three
MVP scenarios give 20 valid variants each at the default seed.

### S4 and FT-250, and the S4 plume rate in variants (Gate 3 disclosure)

FT-250 meters the packing vent header only, so the S4 blowdown line bypasses it and S4 shows no FT-250
rise (an assumption of the simulated station). S4 variants scale the plume rate (rate scale 0.5 to 2.0)
for detection diversity, while the mass a log tool reports stays the volume-based estimate
(`S4_VENTED_CH4_KG`, about 233 kg CH4); no evaluator compares the two, and no prompt, evaluator or fake
may expect an S4 FT-250 signature.

### Former limit, fixed at Gate 3

The Task 6 plan moved only `permit` entries with the shift, so the "K-201 discharge valve replaced; unit
restarted" entry stayed at 9000 s and in 7 of the 20 default S4 variants the blowdown was still venting
when the line said the unit restarted. Gate 3 (2026-11-15) changed `_log` to move every base log entry by
the shift (deviation from the plan, owner decision). Now in every S4 variant the permit entry is exactly
600 s before the blowdown start and the restart entry exactly 900 s after its end (tested over 50 seeds
x 20 variants); S1 and S5 base entries keep their offset to the source or fault start (unless clamped).
