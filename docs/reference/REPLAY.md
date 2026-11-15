# Replay files

One JSON file per scenario in `app/replay/scenarios/` (`s1_rod_packing.json`,
`s4_planned_blowdown.json`, `s5_sensor_drift.json`). The static replay build reads them; they hold
the simulated station only: sensor, instrument and wind series, detection events, the station log
and plume key frames. **They are generated. Never edit them by hand.**

Source of truth: `plumetrace.simulator.replay_schema` (format), `plumetrace.simulator.export`
(builder), `plumetrace.engineering.plume_field` (grid and byte code). The TypeScript types are
generated from the same models (`scripts/export_contract.py`, then `npm run gen:types`).

## Honest labelling

- `simulated` is always `true`: station KS-07 is fictional.
- The weather is **real** public data (Open-Meteo, CC BY 4.0). The station, the sensor readings,
  the instruments and the scenario are **synthetic**. `attribution` holds both: the Open-Meteo
  credit from the weather snapshot, then the fixed sentence "Station KS-07 is fictional and
  simulated; sensor, instrument and scenario data are synthetic. Only the weather is real."
- The file holds **no inversion result and no AI output**. Rate display rule (R1 to R4, owner
  decision 2026-11-14): when a later task adds an inversion result to a replay, a rate is stored
  only as an interval (p05, p50, p95 in kg/h) with the flags `inconclusive`, `rate_at_grid_edge`,
  the top candidate and its probability; a result that is inconclusive, has top `NONE` or sits at
  the grid edge is stored as "not quantified" with its reason; probabilities are model
  probabilities, not calibrated. No single point rate is ever stored for display.
- `keyframes[].sources[].rate_kg_h` is the **simulation input** (the truth used to draw the
  plume), not a measurement and not an estimate. The interface must not show it as a result.

## Format (schema version 1)

Every model rejects unknown fields and non-finite numbers (NaN, infinity). A file that loads
(`ReplayScenario.model_validate_json`) is therefore complete and consistent.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | `1` | Format version; any other value fails to load |
| `scenario_id` | string | For example `s1_rod_packing` |
| `title` | string | Display title |
| `sim_start_utc` | string | UTC time of scenario second 0, ISO 8601 ending in `Z` |
| `duration_s` | number | Scenario length in s |
| `step_s` | number | Sampling step, 60 s (`REPLAY_STEP_S`) |
| `sensors` | list | The 8 methane sensors: `id`, `x_m`, `y_m`, `z_m` (site metres: x east, y north, z up) |
| `series` | map tag to list | 60 s means. Keys: the 8 methane sensors (`AT-101` to `AT-108`, ppm) and the 9 instrument tags (`FT-250`, `TT-201P`, `TT-202P`, `TT-203P`, `FT-601`, `TE-601`, `PT-401`, `PT-402`, `FT-701`). A missing mean is `null` |
| `units` | map tag to string | `ppm`, `kg/h`, `degC`, `kPag`, `Sm3/h`; same keys as `series` |
| `wind_speed_m_s` | list | 60 s mean wind speed in m/s |
| `wind_from_deg` | list | 60 s circular mean wind direction in degrees (direction the wind blows from) |
| `stability` | list | Most frequent Pasquill class (A to F) in each 60 s sample |
| `events` | list | Detection events: `sensor_id`, `window_index`, `window_start_s`, `mean_ppm`, `baseline_ppm`, `downwind_of_site`. They come from the 10-minute detection windows, so `window_start_s` is a multiple of 600 s |
| `log` | list | Station log: `t_s`, `kind`, `tag` (or `null`), `text` |
| `grid` | object | `x0_m`, `y0_m`, `dx_m`, `dy_m`, `nx`, `ny`, `encoding` (`log_u8_0.1_1000ppm`); shared by all key frames. Default 40 x 30 cells of 5 m, covering the 200 m x 150 m site |
| `keyframes` | list | One per 120 s (`KEYFRAME_STEP_S`), strictly increasing `t_s` |
| `attribution` | string | Data credit and the real-versus-synthetic label (above) |
| `simulated` | `true` | Always true |

A key frame has `t_s`, `wind_speed_m_s`, `wind_from_deg`, `stability` (the 60 s values at that
time), `sources` (`anchor_id`, `rate_kg_h` of the scenario sources active at `t_s`; empty before
a leak starts and after it ends) and `grid_b64`.

### Sampling

Sample `k` covers `[60 k, 60 (k + 1))` s and is the mean of the six 10 s simulator samples of that
minute (`window_means` with a 60 s window; a minute with fewer than half its samples valid is
`null`). Wind uses `window_wind` (mean speed, circular mean direction) and `window_mode_class`.
A 6 h scenario has 360 samples and 180 key frames; a 4 h scenario has 240 and 120. Key frame `j`
uses sample `2 j` of the wind and stability, and the 60 s mean air temperature of that minute.

### Key-frame grids

`grid_b64` is base64 (standard alphabet, padded) of `ny * nx` bytes, row-major (`y` then `x`, south
first, west first). Cell `(j, i)` is centred at `x0 + (i + 0.5) dx`, `y0 + (j + 0.5) dy` and at
1.5 m height. The value is the methane concentration above background from the sources active at
that time, with the truth physics (Pasquill-Gifford/Martin coefficients) and no building wake.

### The `log_u8` encoding (0.1 to 1000 ppm, four decades)

```
encode: byte = 0                                            if ppm < 0.1
        byte = clip(round(1 + 254 * log10(ppm / 0.1) / 4), 1, 255)   otherwise
decode: ppm  = 0                                            if byte == 0
        ppm  = 0.1 * 10 ** ((byte - 1) * 4 / 254)           otherwise
```

Byte 1 is 0.1 ppm, byte 255 is 1000 ppm; larger values are clamped to 255. A value inside the
range decodes within half a step (a factor of 1.018, about 1.8 %). `decode_log_u8(data, ny, nx)`
raises `ValueError` when `len(data) != ny * nx`.

Four laws are checked for every input by Hypothesis tests
(`app/backend/tests/engineering/test_plume_field_properties.py`):

1. **Round trip.** For any value from 0.1 to 1000 ppm, `decode(encode(x))` is within half a log
   step of `x` (`abs(log10(y / x))` at most `4 / 254 / 2` decades).
2. **Monotonic.** A larger concentration never gets a smaller byte.
3. **Clamping.** Below 0.1 ppm gives byte 0, which decodes to 0.0. Above 1000 ppm gives byte 255,
   which decodes to 1000 ppm.
4. **Byte count.** One byte per cell, so `len(encode(grid))` is `ny * nx`, and decode restores the
   `(ny, nx)` shape.

## Size budget

At most 5 MB per file (`MAX_REPLAY_BYTES = 5_000_000`; design section 10). `replay_bytes` raises
`ValueError("<id> replay is <n> bytes, budget 5000000")` over the budget and
`scripts/export_scenarios.py` then writes nothing for that scenario. Generated sizes (run 2026-11-15):
`s1_rod_packing` 445 852 bytes, `s4_planned_blowdown` 294 733 bytes, `s5_sensor_drift` 440 244 bytes.

## Determinism and format of the bytes

The same scenario always gives the same bytes: compact JSON (`separators=(",", ":")`), sorted keys,
`ensure_ascii=False`, UTF-8, LF, one trailing newline. The simulation is seeded; no clock or
random source is read at export. A test regenerates each committed file and compares the bytes, a
second test scans them for keys (`secret_scan.py` patterns).

## Regenerate

```
cd app
uv run python ../scripts/export_scenarios.py      # writes app/replay/scenarios/*.json, prints sizes
uv run python ../scripts/export_contract.py       # schema: facility + replay_scenario
cd frontend && npm run gen:types                  # TypeScript types
```

Regenerate whenever the scenario files, the weather snapshot, the engineering core or the replay
schema change. Commit the regenerated files with the change that caused them.

## What is rejected on load

Unknown fields; `schema_version` other than 1; `simulated` other than `true`; NaN or infinity
anywhere; samples whose count does not fit `duration_s / step_s`; a series, wind or stability list
of a different length; `units` and `series` with different tags; key frames not in strictly
increasing time; a `grid_b64` that is not valid base64 or does not decode to `nx * ny` bytes; a
blank `attribution`.
