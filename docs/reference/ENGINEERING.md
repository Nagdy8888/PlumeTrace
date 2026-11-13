# Engineering core

The pure physics of PlumeTrace: constants, unit conversions and (added by later Phase 2 tasks)
dispersion, inversion and emission quantification. Design reference: section 5 of
`docs/superpowers/specs/2026-11-12-plumetrace-design.md`. Package: `plumetrace.engineering`.

## 1. Purpose and scope

Does: hold every physical constant once, with its source, and convert units at the edges so the
rest of the core works in SI. Does not: call an LLM, read files, touch the network or keep global
state. Later Phase 2 tasks add their own sections to this page.

## 2. How it works

`constants.py` defines named `Final[float]` values; `units.py` imports them and exposes pure
functions. Gas concentration conversions use the ideal gas law.

## 3. Public interface

### Units and constants

#### Constants (`plumetrace.engineering.constants`)

| Name | Value | Unit | Source |
|---|---|---|---|
| `R_J_MOL_K` | 8.314462618 | J/(mol K) | CODATA 2018 molar gas constant |
| `M_CH4_KG_MOL` | 0.016043 | kg/mol | NIST Chemistry WebBook, methane |
| `T_STD_K` | 288.15 | K | ISO 13443 standard reference conditions (15 °C) |
| `P_STD_PA` | 101325.0 | Pa | ISO 13443 standard reference conditions |
| `FT3_TO_M3` | 0.028316846592 | m3 per ft3 | exact (1 ft = 0.3048 m) |
| `GWP100_CH4_FOSSIL` | 29.8 | kg CO2e per kg CH4 | IPCC AR6 WG1 Ch. 7, Table 7.15 (fossil CH4) |
| `GWP20_CH4_FOSSIL` | 82.5 | kg CO2e per kg CH4 | IPCC AR6 WG1 Ch. 7, Table 7.15 (fossil CH4) |
| `BACKGROUND_PPM` | 1.95 | ppm | approximate global mean surface CH4 (design §5) |
| `HOURS_PER_YEAR` | 8760.0 | h | non-leap year |

#### Conversions (`plumetrace.engineering.units`)

`FloatOrArray = float | numpy.typing.NDArray[numpy.float64]`. Array input keeps its shape.

| Function | Formula |
|---|---|
| `kg_h_to_kg_s(rate_kg_h)` | `rate / 3600` |
| `kg_s_to_kg_h(rate_kg_s)` | `rate * 3600` |
| `kg_m3_to_ppm(conc_kg_m3, temp_k, pressure_pa, molar_mass_kg_mol=M_CH4_KG_MOL)` | `conc * R * T / (P * M) * 1e6` |
| `ppm_to_kg_m3(conc_ppm, temp_k, pressure_pa, molar_mass_kg_mol=M_CH4_KG_MOL)` | `conc_ppm * 1e-6 * P * M / (R * T)` |
| `scf_to_sm3(volume_scf)` | `volume * FT3_TO_M3` |
| `kg_h_to_t_yr(rate_kg_h)` | `rate * 8760 / 1000` |
| `co2e_kg(ch4_kg, horizon)` | `ch4_kg * GWP100_CH4_FOSSIL` or `* GWP20_CH4_FOSSIL` |

### Gas properties

Module `plumetrace.engineering.gas`; component table in `plumetrace.engineering.constants`
(`GAS_COMPONENTS`, `HYDROCARBONS`). Source of the table: NIST Chemistry WebBook (molar masses and
critical constants), retrieved 2026-11.

| Component | Molar mass (kg/mol) | Critical temp (K) | Critical pressure (Pa) |
|---|---|---|---|
| `CH4` | 0.016043 | 190.56 | 4.599e6 |
| `C2H6` | 0.03007 | 305.32 | 4.872e6 |
| `C3H8` | 0.044097 | 369.83 | 4.248e6 |
| `nC4H10` | 0.05812 | 425.12 | 3.796e6 |
| `CO2` | 0.04401 | 304.13 | 7.377e6 |
| `N2` | 0.028013 | 126.2 | 3.396e6 |

`GasComposition` (frozen Pydantic model) holds `mole_fractions`; it rejects an unknown component
(`unknown gas component H2S`), a negative value and a sum that differs from 1 by more than 1e-6.

| Function | Formula |
|---|---|
| `molar_mass_kg_mol(comp)` | sum of `x_i * M_i` |
| `pseudo_critical(comp)` | Kay's rule: `Tpc = sum x_i Tc_i`, `Ppc = sum x_i Pc_i`, returns `(tpc_k, ppc_pa)` |
| `z_factor_papay(pressure_pa, temp_k, comp)` | `Pr = P/Ppc`, `Tr = T/Tpc`, `Z = 1 - 3.52 Pr exp(-2.260 Tr) + 0.247 Pr^2 exp(-1.878 Tr)` (Papay 1968) |
| `density_kg_m3(pressure_pa, temp_k, comp)` | `P M / (Z R T)` |
| `ch4_mass_fraction(comp)` | `x_CH4 M_CH4 / M_mix` (whole gas) |
| `ch4_hydrocarbon_mass_fraction(comp)` | `x_CH4 M_CH4 / sum_HC x_i M_i`; converts total-organic-compound factors to CH4 |
| `ch4_hydrocarbon_mole_fraction(comp)` | `x_CH4 / sum_HC x_i`; converts total-hydrocarbon volumes to CH4 |
| `std_volume_to_ch4_kg(volume_sm3, comp)` | `(P_STD V / (R T_STD)) x_CH4 M_CH4` |

Papay validity: sweet natural gas at moderate reduced pressures. The KS-07 discharge case
(7.0 MPa, 300 K, Pr 1.52, Tr 1.53) is inside that range; Z there is 0.862.

### Stability

Module `plumetrace.engineering.stability`. Pasquill-Gifford-Turner classes A (very unstable) to F
(moderately stable) from Turner (1994), Workbook of Atmospheric Dispersion Estimates, 2nd ed.,
Table 1-1. `pasquill_class(wind_speed_m_s, shortwave_w_m2, cloud_fraction)` returns a
`StabilityClass` (`StrEnum`) using lookup tables, not nested conditions.

Thresholds (`Final[float]` constants): `DAY_SHORTWAVE_W_M2 = 10`, `STRONG_W_M2 = 600`,
`MODERATE_W_M2 = 300`, `OVERCAST_FRACTION = 0.875`, `NIGHT_CLOUDY_FRACTION = 0.5`.

1. Cloud fraction at least 0.875 (overcast), day or night: class D.
2. Day is shortwave above 10 W/m2. Insolation is strong above 600, moderate from 300 to 600
   inclusive, slight below 300.
3. Night: cloudy at cloud fraction 0.5 or more, clear otherwise.
4. Wind bins (m/s): below 2, 2 to below 3, 3 to below 5, 5 to below 6, 6 and above.

| u (m/s) | day strong | day moderate | day slight | night cloudy | night clear |
|---|---|---|---|---|---|
| < 2 | A | B | B | F | F |
| 2 to < 3 | B | B | C | E | F |
| 3 to < 5 | B | C | C | D | E |
| 5 to < 6 | C | D | D | D | D |
| >= 6 | C | D | D | D | D |

Resolution rule: the classic table has split cells (for example A-B, B-C, C-D, E-F). Each is
resolved to the more stable letter. This is conservative: a more stable class gives a narrower,
more concentrated plume and so higher predicted concentrations, which errs toward detecting a
leak rather than missing one.

### Dispersion coefficients

Module `plumetrace.engineering.dispersion`. `sigmas_m(x_m, stability, coeff)` returns
`(sigma_y_m, sigma_z_m)` for a numpy array of downwind distances. `CoefficientSet` (`StrEnum`) is
`BRIGGS_RURAL` or `PG_MARTIN`. Steps: clip `x_m` to `[X_MIN_M, X_MAX_M]` = `[10, 1000]` m, evaluate
the set, floor both results at `SIGMA_MIN_M` = 0.5 m. Coefficients are module-level
`MappingProxyType` tables keyed by `StabilityClass`.

**BRIGGS_RURAL** (Briggs 1973, open country; Seinfeld & Pandis, Atmospheric Chemistry and Physics,
3rd ed., Table 18.3). x in m, sigma in m.

| Class | sigma_y | sigma_z |
|---|---|---|
| A | `0.22 x (1 + 0.0001 x)^-0.5` | `0.20 x` |
| B | `0.16 x (1 + 0.0001 x)^-0.5` | `0.12 x` |
| C | `0.11 x (1 + 0.0001 x)^-0.5` | `0.08 x (1 + 0.0002 x)^-0.5` |
| D | `0.08 x (1 + 0.0001 x)^-0.5` | `0.06 x (1 + 0.0015 x)^-0.5` |
| E | `0.06 x (1 + 0.0001 x)^-0.5` | `0.03 x (1 + 0.0003 x)^-1` |
| F | `0.04 x (1 + 0.0001 x)^-0.5` | `0.016 x (1 + 0.0003 x)^-1` |

**PG_MARTIN** (Martin 1976 fit of the Pasquill-Gifford curves for x < 1 km; Cooper & Alley, Air
Pollution Control, Table 20-1). `x_km = x / 1000`; `sigma_y = a x_km^0.894`;
`sigma_z = c x_km^d + f`.

| Class | a | c | d | f |
|---|---|---|---|---|
| A | 213 | 440.8 | 1.941 | 9.27 |
| B | 156 | 106.6 | 1.149 | 3.3 |
| C | 104 | 61.0 | 0.911 | 0.0 |
| D | 68 | 33.2 | 0.725 | -1.7 |
| E | 50.5 | 22.8 | 0.678 | -1.3 |
| F | 34 | 14.35 | 0.740 | -0.35 |

Validity: classic fits are extrapolated below 100 m; the benchmark measures the consequence. The
two sets differ by more than 15 % in sigma_z at 300 m, class D, so a truth model built on one set
is not the inversion model built on the other. The Martin class D sigma_z is below the 0.5 m
floor under about 24 m; the floor applies there.

### Gaussian plume

Module `plumetrace.engineering.plume`. Forward model: concentration above background at receptor
points from one continuous point source, with total ground reflection.

```
C = Q / (2 pi u sy sz) * exp(-y^2 / (2 sy^2)) * [ exp(-(z - H)^2 / (2 sz^2)) + exp(-(z + H)^2 / (2 sz^2)) ]
```

| Symbol | Meaning | Unit |
|---|---|---|
| `Q` (`rate_kg_s`) | emission rate, >= 0 | kg/s |
| `u` (`wind_speed_m_s`) | wind speed, > 0 (the 10 m wind at all heights) | m/s |
| `sy`, `sz` | horizontal and vertical spread, `sigmas_m(x, stability, coeff)` | m |
| `x` (along) | downwind distance of the receptor; clipped to 10 m inside `sigmas_m` | m |
| `y` (cross) | crosswind distance of the receptor | m |
| `z` | receptor height | m |
| `H` (`source.z_m`) | source height | m |
| `C` | concentration above background | kg/m3 |

Functions:

- `downwind_crosswind_m(source, receptors_xy, wind_from_deg)` returns `(along_m, cross_m)`.
- `concentration_kg_m3(rate_kg_s, wind_speed_m_s, wind_from_deg, source, receptors, stability, coeff)`
  takes `receptors` of shape `(N, 3)` and returns shape `(N,)`. `ValueError` if
  `wind_speed_m_s <= 0` or `rate_kg_s < 0`.
- `concentration_ppm(..., temp_k, pressure_pa)` is the same result through `kg_m3_to_ppm`.

Coordinates and wind: x = east, y = north, z = up (site coordinates, metres). `wind_from_deg` is
the meteorological bearing the wind blows FROM, clockwise from north. The plume travels toward
`theta = radians(wind_from_deg + 180)`. With `dx`, `dy` the receptor offset from the source,
`along = dx sin(theta) + dy cos(theta)` and `cross = dx cos(theta) - dy sin(theta)`.
In words: wind from 270 (west) gives `theta` = 90 degrees, so east is downwind; wind from 180
(south) gives `theta` = 0, so north is downwind. A receptor 100 m north of the source with wind
from 180 has `along` = 100 m and `cross` = 0.

Assumptions: steady state over the averaging period, flat terrain, no plume rise for vents, the 10 m
wind used at all heights, total ground reflection (the second exponential is the image source at
-H). Limits: `C = 0` wherever `along <= 0` (upwind of, or level with, the source); no buildings,
no meander, no chemistry or deposition; spreads are clipped at 10 m, so the model is not valid
within about 10 m of the source (value there equals the 10 m value). Reference: Turner,
*Workbook of Atmospheric Dispersion Estimates*, 2nd ed., 1994.

### Averaging

Module `plumetrace.engineering.averaging`. The plume model predicts roughly 10-minute mean
concentrations, so raw sensor and weather samples are averaged into complete windows before they
are compared with it; single samples carry turbulent noise the model does not describe.

- `window_means(times_s, values, window_s=WINDOW_S)` with `times_s` shape `(T,)` (constant step
  `dt`) and `values` shape `(T, S)` returns `(window_start_s (W,), means (W, S))`. Window k covers
  `[t0 + k window_s, t0 + (k+1) window_s)`, `t0 = times_s[0]`. Only complete windows are returned;
  a trailing partial window is dropped; a series shorter than one window gives empty results
  (shapes `(0,)` and `(0, S)`).
- Input checks: fewer than two samples, or a `values`, `speed_m_s` or `from_deg` whose length
  differs from `times_s` (longer or shorter, nothing is truncated), raises `ValueError`.
- Coverage rule: the mean uses the non-NaN samples; if there are fewer than
  `MIN_COVERAGE x window_s / dt` of them (`MIN_COVERAGE` = 0.5), the window is NaN. Exactly 50 % is
  kept.
- `circular_mean_deg(directions_deg)` is the vector mean of unit vectors, so 359 and 1 degrees
  average to 0, not 180. The result is in `[0, 360)`; values within 1e-9 of 360 return 0.0. An
  empty array raises `ValueError`.
- `window_wind(times_s, speed_m_s, from_deg, window_s=WINDOW_S)` returns per complete window the
  arithmetic mean speed and the circular mean direction. It has no NaN coverage rule.
- `is_calm(speed_m_s)` is `speed_m_s < CALM_WIND_M_S` (1 m/s): the plume formula divides by wind
  speed, so calm windows are not modelled.

`WINDOW_S` = 600 s, `CALM_WIND_M_S` = 1.0 and `MIN_COVERAGE` = 0.5 are Phase 2 Task 6 values.

### Event detection

Module `plumetrace.engineering.detection`. Finds sustained rises of a methane sensor above its own
recent background on the 10-minute window means from `window_means`. It flags that something
changed; it does not decide leak versus sensor fault (triage's job) and does not locate or size it.

`detect_events(window_start_s (W,), means_ppm (W, S), sensors, site_center_xy, wind_from_deg (W,),
config=DetectionConfig())` returns `DetectionEvent`s (frozen) sorted by `(window_index, sensor_id)`.
Per sensor column, for each window `t >= baseline_windows`:

- baseline = median of the previous `baseline_windows` non-NaN means; sigma = `max(1.4826 x median
  absolute deviation, sigma_floor_ppm)` (1.4826 turns the MAD into a normal sigma);
- one-sided CUSUM `S = max(0, S + (x - baseline) / sigma - k_sigma)`; `S > h_sigma` raises an event
  (fields: sensor, window index and start, mean, baseline, the `S` that crossed), resets `S` to 0 and
  holds the sensor at 0 for `refractory_windows`;
- a NaN window leaves `S` unchanged; an empty history skips the window.

| Parameter | Default | Meaning |
|---|---|---|
| `baseline_windows` | 12 | windows (2 h) in the rolling baseline |
| `k_sigma` | 0.5 | allowance per window; rises smaller than 0.5 sigma never accumulate |
| `h_sigma` | 5.0 | decision threshold on `S`, in sigmas |
| `sigma_floor_ppm` | 0.1 | lower bound of sigma, so a flat history cannot give huge scores |
| `refractory_windows` | 6 | windows held at zero after an event (one event per episode) |
| `downwind_half_angle_deg` | 60.0 | half width of the downwind sector |

Why CUSUM: a step of a few sigma crosses `h_sigma` in one or two windows, and a slow drift too small
for a per-window threshold still accumulates `(drift - k_sigma)` per window until it crosses. The
rolling median baseline follows slow background changes and ignores a few outliers.

`downwind_of_site` is true when the bearing from `site_center_xy` to the sensor
(`degrees(atan2(dx, dy)) mod 360`) is within `downwind_half_angle_deg` (inclusive, smallest angular
difference) of `(wind_from_deg[t] + 180) mod 360`. A NaN wind direction or a sensor exactly at the
site centre has no bearing and gives false.

Measured behaviour (planner prototype, same algorithm and defaults): 0 false alarms over 20 seeds x
2 days x 8 sensors of Gaussian noise (sigma 0.05 ppm around 1.95 ppm); a +2 ppm step caught at its
first window; a +0.02 ppm/window drift caught at window 63 (drift began at 50). Tests assert the
same on seed 7. Limits: the first `baseline_windows` windows are never tested; a series with
`W <= baseline_windows` gives no events; a rise lasting longer than the baseline becomes the new
baseline. `ValueError` for a `means_ppm` that is not `(W, S)` with S
sensors, window or wind arrays of the wrong length, `baseline_windows < 1` or a non-positive
`sigma_floor_ppm`. The defaults are Phase 2 Task 7 values.

## 4. Design decisions and assumptions

- Ideal gas law for ppm and kg/m3; at 288.15 K and 101325 Pa pure methane is 0.67850 kg/m3.
- `scf_to_sm3` ignores the 60 °F versus 15 °C reference difference (about 0.2 %).
- Z uses the closed-form Papay correlation (no iteration) with Kay's rule, not AGA8; adequate for
  the sweet KS-07 gas, not for sour or rich gas.
- The 600 and 300 W/m2 insolation bins, the 10 W/m2 day/night split and the cloud fractions are
  Phase 2 Task 3 thresholds (project choices, not Turner's own W/m2 values). Split cells of the
  Pasquill table resolve to the more stable class (see Stability).
- GWP values are AR6 fossil methane (29.8 over 100 years, 82.5 over 20 years).

## 5. Limits and failure behaviour

No input validation: temperature and pressure must be positive (division by `T`, `P`, `M`
otherwise yields inf or nan). Callers pass physically valid values.

## 6. Configuration

None. Constants are code, not settings.

## 7. Testing and evidence

`app/backend/tests/engineering/test_units.py`: constant values, rate conversions, methane density
at standard conditions, ppm round trip, array shape, scf and CO2e.
`app/backend/tests/engineering/test_gas.py`: KS-07 molar mass, Kay's rule, Papay Z at 7.0 MPa and at
standard conditions, density, the three CH4 fractions, standard volume to CH4 mass, and rejection
of a bad sum or unknown component (hand calculations in the docstrings).
`app/backend/tests/engineering/test_stability.py`: every cell of the table, overcast, and the bin
boundaries (u = 2, 3; 600, 300, 10 W/m2; cloud 0.5).
`app/backend/tests/engineering/test_dispersion.py`: hand-calculated Briggs D at 1000 m and Martin D at
500 m, the 0.5 m floor, distance clipping, monotone growth for all classes and both sets, and the
300 m difference between sets.
`app/backend/tests/engineering/test_plume.py`: closed form for a ground source on the centreline,
linearity in Q, symmetry across the axis, zero upwind, wind direction convention, near-source
clipping, ground reflection for an elevated source, input validation and vectorised equals loop.
`app/backend/tests/engineering/test_averaging.py`: complete windows with the partial tail dropped,
the NaN coverage rule (70 % missing is NaN, 50 % kept), circular mean across north, window wind and
the calm threshold. `test_averaging_edges.py`: series shorter than one window, fewer than two
samples, length mismatch in both directions and empty circular mean.
`app/backend/tests/engineering/test_detection.py`: no false alarms on noise, one prompt event for a
step, a slow drift, NaN dropout and the downwind flag. `test_detection_edges.py`: short or empty
series, all-NaN sensor, step after a gap, ordering, refractory hold, inclusive sector edge and
wrap-around, NaN wind, sensor at the centre, flat history, shape and config errors. Run from
`app/`: `uv run pytest backend/tests/engineering -q`.

## 8. How to extend

Add a constant only in `constants.py` with a `# source:` comment, never inline in a model. Name
every quantity with its unit suffix. Keep functions pure.

## 9. Changelog

- 2026-11-13: constants and unit conversions added (Phase 2 Task 1).
- 2026-11-13: gas composition, Papay Z factor, density and CH4 fractions added (Phase 2 Task 2).
- 2026-11-13: Pasquill stability classification added (Phase 2 Task 3).
- 2026-11-13: Briggs rural and Pasquill-Gifford (Martin) dispersion coefficients added (Phase 2 Task 4).
- 2026-11-13: Gaussian plume forward model added (Phase 2 Task 5).
- 2026-11-13: window averaging, circular wind mean and calm detection added (Phase 2 Task 6).
- 2026-11-13: CUSUM event detection added (Phase 2 Task 7).
