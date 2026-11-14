# Engineering core

The pure physics of PlumeTrace, in package `plumetrace.engineering`: constants and unit conversions,
gas properties, Pasquill stability classes, dispersion coefficients, the Gaussian plume forward
model, window averaging, event detection, source inversion, evidence fusion, flare slip, blowdown
vented mass, the emission-factor inventory, methane intensity and a truth model that generates
synthetic sensor data. The model-mismatch benchmark in `app/backend/benchmark/` (a separate
package) scores the inversion against that truth model. Design reference: section 5 of
`docs/superpowers/specs/2026-11-12-plumetrace-design.md`.

## 1. Purpose and scope

Does: hold every physical constant once, with its source; convert units at the edges so the rest of
the core works in SI; and answer the engineering questions behind the product with tested
calculations: how much a plume of a given rate reads at a sensor, whether a sensor series rose,
which emission candidate leaks and at what rate, how process evidence shifts that ranking, and how
much methane a flare, a blowdown, a component inventory or a found leaker emits. Does not: call an
LLM, read files, touch the network or keep global state. The agents never produce an engineering
number themselves; every number comes from one of these functions through a tool (project rule 4).

## 2. How it works

Data path for a leak event: raw sensor and weather samples go through `averaging` (10-minute
windows, NaN where coverage is poor, circular mean wind) into `detection` (a CUSUM per sensor says
something rose) and `inversion`. The inversion calls the Gaussian `plume` forward model, which takes
its spreads from `dispersion` using a Pasquill class from `stability`, for every candidate source
and a grid of rates, and returns ranked candidates with probabilities and a rate with a 90 %
interval, or an explicit inconclusive result. `fusion` then updates that ranking with process
evidence (header flow, packing temperatures) and shares a vent probability among compressor units.
Quantification side: `flare` (methane slip), `blowdown` (vented mass, uses `gas`), `inventory` with
`emission_factors` (bottom-up site total and OGI leaker rates) and `intensity` (methane intensity in
percent). `truth_model` and its helper modules generate sensor data with deliberately different
physics; the simulator (Phase 3) and the benchmark use it, so the demo is not an inverse crime.
`constants.py` defines named `Final[float]` values; `units.py` imports them and exposes pure
functions (ideal gas law for the concentration conversions).

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
no meander (unless `dir_sd_deg` is given, see below), no chemistry or deposition; spreads are
clipped at 10 m, so the model is not valid within about 10 m of the source (value there equals the
10 m value). Reference: Turner, *Workbook of Atmospheric Dispersion Estimates*, 2nd ed., 1994.

**Meander option (`dir_sd_deg`, project derivation, not a published formula).** Both concentration
functions take a keyword-only `dir_sd_deg` (default 0.0), the standard deviation in degrees of the
wind direction inside the averaging window. With `dir_sd_deg > 0` the horizontal spread becomes

```
sigma_y,eff^2 = sigma_y^2 + (x_c * radians(dir_sd_deg))^2
```

where `x_c` is the along-wind distance clipped to 10 to 1000 m exactly as `sigmas_m` clips it
(`X_MIN_M`, `X_MAX_M`) and `sigma_z` is unchanged. Derivation: a plume whose axis wanders with
direction standard deviation `s` (radians) is, averaged over the window, the narrow plume smeared
sideways. At distance `x` the axis is displaced by `x tan(theta)`, about `x theta` for a small angle,
so the displacement variance is `(x s)^2`; adding it to the plume's own `sigma_y^2` is the
small-angle variance of a direction-averaged plume. The small-angle step is the limit: at 20 degrees
`tan` differs from the angle by about 4 %, and it grows beyond that, so the option is meant for
spreads of the order of 10 degrees. The crosswind integral of `C` is unchanged (a Gaussian in `y`
integrates to the same value for any `sigma_y`), the centreline value falls by `sigma_y /
sigma_y,eff`, and nothing changes for `along <= 0`. With exactly `dir_sd_deg = 0.0` the original
code path runs with no extra arithmetic, so results are bit-identical to the version without the
option. `ValueError` for a negative or non-finite `dir_sd_deg`. The spread is measured from data
(`window_direction_sd_deg`), never taken from the truth model's setting.

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
- `window_direction_sd_deg(times_s, from_deg, window_s=WINDOW_S)` returns per complete window the
  circular standard deviation of the direction in degrees, `degrees(sqrt(-2 ln R))` with `R` the
  mean resultant length of the unit vectors (`R = 1` for a constant direction, so exactly 0.0; `R`
  is computed as the mean of `cos(direction - circular mean)` and clipped to `[0, 1]`). It uses the
  same windows and the same `ValueError`s as `window_wind` and is NaN exactly where `window_wind`
  is NaN: a window with any missing direction is NaN, so a window under 50 % coverage is NaN too
  (there is no partial-coverage average). Alternating 350 and 10 degrees give 10.02556 degrees. A
  window whose directions cancel exactly (`R = 0`) would give infinity. This is the measured input
  of the plume's `dir_sd_deg` option; it describes the 10 s direction samples inside each window.
- `window_mode_class(classes, steps_per_window, n_windows)` returns the most frequent stability class
  in each of the first `n_windows` windows of `steps_per_window` steps (window k is
  `classes[k * n : (k + 1) * n]`); a tie goes to the alphabetically first class, `n_windows = 0`
  gives an empty list, and a requested window with no steps raises `ValueError`. It is the logic
  that was private to `benchmark.runner` (`window_stability` now calls it); a Hypothesis test checks
  it equals the old per-slice rule, ties and a partial last window included (Phase 3 Task 4).
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

### Source inversion

Modules `plumetrace.engineering.inversion` (public API and decisions), `inversion_input` (the
`InversionInput` model and its checks, re-exported by `inversion` together with `NO_SOURCE_ID`,
`MAX_ABS_OBS_PPM`, `DEFAULT_OBS_SIGMA_PPM` and `DEFAULT_MODEL_REL_ERROR`) and `inversion_model`
(numerics). Answers: which of the emission candidates leaks, at what rate, and how sure are we.

`invert(InversionInput) -> InversionResult`. `InversionInput` holds the candidates, the sensors,
the window means above background (`W x S`, NaN or infinity = missing), wind speed, wind "from"
bearing and stability class per window, `temp_k`, `pressure_pa`, `obs_sigma_ppm` (default 0.1),
`model_rel_error` (default 0.6) and the dispersion coefficient set (default Briggs rural). It raises
`ValueError` for empty candidates or sensors, a candidate id of `NONE` or a duplicate id, any array
whose length differs from the number of windows, a row whose width differs from the number of
sensors, and a non-positive `obs_sigma_ppm`, `temp_k` or `pressure_pa`, or a negative `model_rel_error`.

Optional `wind_dir_sd_deg: list[float] | None = None`: the within-window wind-direction standard
deviation per window in degrees (from `window_direction_sd_deg`), passed to the plume as
`dir_sd_deg` for each used window (see Gaussian plume, Meander option). `None`, the default, is the
behaviour above, unchanged; all zeros gives exactly the same result as `None` (tested). It raises
`ValueError` for a length different from the number of windows, a negative or infinite value, and a
NaN value in a window whose wind direction is known (NaN is allowed where the direction is NaN; that
window is not used). The model-error term `model_rel_error` is not changed by the option.

- **Hypothesis space:** the 21 KS-07 emission candidates plus `NONE` (no source), so `C + 1 = 22`
  hypotheses.
- **Priors:** `NONE` 0.5 (`NO_SOURCE_PRIOR`), the other 0.5 shared equally by the candidates. Most
  windows in operation are not leaks, and a prior of `1 / (C + 1)` for `NONE` would make a quiet site
  look like it probably has a leak somewhere; 0.5 says "no leak" and "a leak" are equally plausible
  before seeing data. Each hypothesis spreads its prior evenly over the rate grid.
- **Rate grid:** `RATE_GRID_KG_H = geomspace(0.1, 500, 80)` (log spacing, step about 11 %).
- **Likelihood:** `pred = response[c, w, s] x rate` where `response` is `concentration_ppm` for
  1 kg/s; variance `obs_sigma_ppm^2 + (model_rel_error x pred)^2`; the log-likelihood is the sum of
  `-0.5 ((y - pred)^2 / var + ln(2 pi var))` over non-missing readings. The second variance term is
  the plume model error: a reading may differ from the prediction by a share of the
  prediction, not only by sensor noise. `NONE` has
  `pred = 0`.
- **Posterior:** log-sum-exp normalisation over the `(C + 1) x Q` cells; a candidate's probability
  is the sum over the grid; `ranked` is sorted by probability, ties by id, and sums to 1.
- **Rate:** for a candidate top, the conditional posterior over the grid gives the median and the
  5th and 95th percentiles by linear interpolation of the CDF on ln(rate). `rate_at_grid_edge` is
  true when the median is at or beyond the second grid value from either end (rate possibly outside
  0.1-500 kg/h).
- **Input checks:** every finite value of `observed_ppm_above_bg` must satisfy
  `abs(value) <= MAX_ABS_OBS_PPM` (bound inclusive); NaN and infinity stay allowed and mean missing.
  A finite negative `wind_speed_m_s` is rejected (NaN means unknown). Both raise `ValueError`. If the
  log-posterior is still not finite (for example an absurd `obs_sigma_ppm`), `invert` raises
  `ValueError` instead of returning a made-up distribution (it fails visibly, with no new reason).
- **Windows:** used when wind speed and direction are finite, speed is at least `CALM_WIND_M_S` and
  at least one sensor has a valid reading. `windows_used` counts them.

| Constant | Value | Role |
|---|---|---|
| `NO_SOURCE_PRIOR` | 0.5 | prior of `NONE` |
| `MIN_CONCLUSIVE_PROBABILITY` | 0.6 | below this the top is `ambiguous` |
| `MIN_SIGNAL_TO_NOISE` | 3.0 | predicted peak below `3 x obs_sigma_ppm` is a `weak_signal` |
| `MIN_USABLE_WINDOWS` | 2 | fewer is `calm` or `too_few_windows` |
| `DEFAULT_OBS_SIGMA_PPM` | 0.1 | observation noise |
| `DEFAULT_MODEL_REL_ERROR` | 0.6 | relative plume model error |
| `MAX_ABS_OBS_PPM` | 1.0e6 | largest accepted finite `abs(observation)`; pure methane, a mole-fraction difference cannot exceed it |

Decision (`reason`; the `calm` and `too_few_windows` rule is an owner ruling, 2026-11-13): `calm`
(at least one window and every window has a finite speed below the calm limit),
`too_few_windows` (fewer than 2 usable windows otherwise, including no windows, all-NaN data or
unknown wind speed or direction; a mix of calm and unknown-wind windows is `too_few_windows`), `ambiguous` (top probability below 0.6), `weak_signal` (conclusive top candidate, but
`max(response[top]) x median` is below `3 x obs_sigma_ppm`). Otherwise conclusive with
`reason = None`. A `NONE` top has no rate. These four cases return `inconclusive = True`; calm and
too-few-windows return `ranked = []`, `top_id = "NONE"`, `top_probability = 0.0`. An ambiguous or
weak result still reports the rate of its top candidate: read it together with the reason.

Measured behaviour (planner prototype and the tests): source recovered at p = 1.0; pure noise gives
`NONE` conclusively (p about 0.84 on the test seed); mirror-symmetric candidates give p = 0.5 and
`ambiguous`; 36 windows x 21 candidates x 8 sensors x 80 rates runs in about 0.04 s (limit 2 s).

Limits: candidates whose plume never reaches a sensor are indistinguishable from no source (their
response is zero, so they tie with `NONE`; the result is `ambiguous`, and the rate shown is then
only the prior). The model-error term is independent per reading, so the rate interval narrows as windows
accumulate and does not cover the true rate: the multiplicative variance term pulls the median about
25 % below it (7.1 to 7.7 kg/h for a 10 kg/h KS-07 test leak, three seeds, 12 to 1000 windows). Measured
p95/p05 ratio on that leak: about 1.93 at 12 windows (covers 10 kg/h), 1.48 at 36, 1.25 at 100 and
1.21 at 300 to 1000 (does not cover), so it plateaus near 1.8 grid steps (one step is a ratio of
1.114). The benchmark (Task 13) measures real coverage. Tests use data generated by the same plume model, so they check the algorithm,
not model mismatch. The constants above are Phase 2 Task 8 values.

### Evidence fusion

Module `plumetrace.engineering.fusion`. Why it is code: in scenario S1 the plume inversion finds the
common vent stack `VS-250.tip`, but deciding which compressor's packing leaks needs process evidence
(header flow FT-250, packing temperatures TT-201P, TT-202P, TT-203P). That decision is a tested
calculation, never the LLM's judgement (project rule 4).

- **Bayes update with likelihood ratios:** `fuse(prior, evidence) -> FusionResult`. The posterior of a
  candidate is its prior times the product of the clipped likelihood ratios (LR) of the evidence items
  about it, renormalised to sum 1. An LR above 1 supports the candidate, below 1 argues against it.
  Items are treated as independent, so two items on one candidate multiply. Items about an id that is
  not in the prior are ignored and are not in `applied`. `probabilities` is ordered by descending
  probability, ties by id; `top_id` is the first key.
- **Clipping:** every LR is cut to `[LR_MIN, LR_MAX] = [0.05, 20]` before it is used, so no single
  instrument can drive a candidate to 0 or 1 alone. `EvidenceItem` rejects an LR that is not above
  zero (NaN included); an infinite LR is accepted and clipped to 20.
- **Header flow rule:** `header_flow_evidence(increase, uncertainty, plume_rate, vent_candidate_id,
  source_tag="FT-250")`. `significant = increase > 2 x uncertainty` (`HEADER_SIGNIFICANCE_SIGMA`);
  `consistent = |increase - plume_rate| <= 2 x uncertainty`. Both true gives LR 4
  (`HEADER_CONSISTENT_LR`), otherwise 1.0: a missing or contradicting header signal is "no
  information", never evidence against the vent. The `reason` text states the three numbers and the
  outcome.
- **Packing temperature rule:** `packing_temperature_lrs(temps_c, baseline_c, sigma_c=2.0, k=1.0)`.
  `a_j = (T_j - baseline_j) / sigma_c`, `LR_j = clip(exp(k x (a_j - mean(a of the other units))))`.
  Comparing a unit with its peers cancels a rise shared by all units (ambient temperature, load), so
  only a unit hotter than the others gets weight. At least two units are required.
- **Attribution:** `attribute_vent_source(vent_probability, unit_lrs)` gives
  `P(unit) = vent_probability x LR / sum(LR)`, in the key order of `unit_lrs`; the shares add up to
  the vent probability.
- **Failure behaviour:** all of these raise `ValueError` instead of returning NaN: a prior with a
  negative, NaN or infinite value, an empty prior, zero or overflowing total mass (also after the
  update); a non-finite header input, an uncertainty not above zero, a negative plume rate; fewer
  than two units, a unit without a baseline, a non-finite temperature or baseline, `sigma_c` not
  above zero, a negative or infinite `k`; a vent probability outside 0 to 1, no units, a negative or
  non-finite LR, or an LR sum of zero. A very large exponent is cut to `LR_MAX` without an overflow.
  An LR of exactly 0 is accepted in `attribute_vent_source` (that unit gets no share).

| Constant | Value | Role |
|---|---|---|
| `LR_MIN` | 0.05 | lower clip of every LR |
| `LR_MAX` | 20.0 | upper clip of every LR |
| `PACKING_SIGMA_C` | 2.0 | temperature scale `sigma_c` in degC |
| `PACKING_K` | 1.0 | steepness `k` of the temperature LR |
| `HEADER_CONSISTENT_LR` | 4.0 | LR of a significant, plume-consistent header increase |
| `HEADER_SIGNIFICANCE_SIGMA` | 2.0 | header increase must exceed this many uncertainties |

All six are Phase 2 Task 9 values (project choices, not published or calibrated constants).

S1 walk-through (hand calculation, as in the tests). FT-250 reads +10 +/- 1 kg/h and the plume rate
is 9 kg/h: 10 > 2 x 1 and |10 - 9| = 1 <= 2, so the LR for `VS-250.tip` is 4. With an illustrative
prior of 0.5 for `VS-250.tip` and 0.5 for the rest, the posterior is 0.5 x 4 / (0.5 x 4 + 0.5) = 0.8.
The packing probes read K-201 80, K-202 86, K-203 80 degC against baselines of 80: `a = (0, 3, 0)`.
K-202: `exp(3 - 0) = 20.09`, clipped to 20. K-201 and K-203: `exp(0 - 1.5) = 0.2231`. The share of K-202
is `20 / (20 + 2 x 0.2231) = 0.97817`, so `P(K-202) = 0.8 x 0.97817 = 0.7825` and each other unit gets
`0.8 x 0.2231 / 20.4463 = 0.0087`.

Limits:
- The LRs are not calibrated against plant data. 0.05, 20, 4, 2 degC and `k = 1` are project
  choices; treat the output as a ranking with a stated rule, not as a measured probability.
- Evidence items are assumed independent (naive Bayes). Two probes that respond to the same
  cause, such as two packing temperatures that rise together, are counted twice if both are given as
  items. The clip at 20 limits the damage but does not remove it.
- Attribution assumes exactly one leaking unit on the vent header; two leaking units are not
  represented and show as one hot unit and one cold-looking unit.
- The header rule compares against the plume rate from the inversion, which is not unbiased: the
  likelihood in Source inversion pulls the median rate about 25 % low in the tests. A true header
  increase can therefore fail the `consistent` test and give LR 1, which loses information but does
  not mislead. The rule's factor 2 on the consistency tolerance is fixed in code, not a constant.
- The header rule never lowers the vent probability; the absence of a header increase is not
  treated as evidence against the vent.
- The temperature rule needs a trustworthy per-unit baseline. A drifting thermocouple raises one
  anomaly and is read as a hot packing; sensor faults are not detected here.
- The prior for `fuse` and `vent_probability` come from the inversion posterior, so its limits (see
  Source inversion) carry through.

### Flare

Module `plumetrace.engineering.flare`. Methane that leaves the flare stack unburned, in kg/h:

```
lit:    slip = (1 - DE) * flared_gas_kg_h * w
unlit:  slip =            flared_gas_kg_h * w
```

`w` is the methane mass fraction of the flared gas (`ch4_mass_fraction(comp)` from Gas properties)
and `DE` the destruction efficiency. `DEFAULT_DESTRUCTION_EFFICIENCY = 0.98`: the source comment in
the code reads "98 % destruction and removal efficiency, the default for a lit, well-operated flare
in OGMP 2.0 guidance and EPA AP-42 §13.5; real efficiency varies with wind and flow (design §5.3)".
With the pilot out nothing is destroyed, so an unlit flare emits all of the methane sent to it
(scenario S3). `DE` is not used for an unlit flare but is still validated.

Hand calculation (plan tests): 100 kg/h of gas with `w = 0.8624` carries 86.24 kg/h of methane. Lit
at `DE = 0.98` that gives `0.02 * 86.24 = 1.7248` kg/h; unlit, 86.24 kg/h.

`flare_ch4_slip_kg_h` raises `ValueError` for a negative, NaN or infinite flow, for `w` outside
`[0, 1]` and for `DE` outside `[0, 1]` (NaN included). `DE = 1` and `DE = 0` are allowed. The result
is never above `flared_gas_kg_h * w`, so a huge finite flow cannot overflow.

Limits:

- One fixed `DE` for every condition. A real flare's efficiency falls with crosswind, with very
  low or very high flow and with steam or air assist; the 0.98 is a typical well-operated value,
  not a prediction for a given hour. The caller may pass another `DE`, but nothing in this module
  derives it from the weather or the flow.
- The model is binary on the pilot: lit or unlit. A flame that is partly blown out, or a pilot
  that flickers, is not represented.
- The flared gas flow and the pilot status come from the flare meter and pilot thermocouple. A
  wrong reading gives a wrong slip; the function cannot check it.
- Only methane slip is computed. Other products of incomplete combustion are not.

### Blowdown

Module `plumetrace.engineering.blowdown`. Gas released when an isolated volume is depressurised
(scenario S4, a planned blowdown):

```
gas_mass_kg = V * (rho(p_i, T_i) - rho(p_f, T_f))
ch4_mass_kg = gas_mass_kg * ch4_mass_fraction(comp)
```

`rho` is the real-gas `density_kg_m3` (`P M / (Z R T)`, Papay Z, see Gas properties). All pressures
are absolute. `vented_mass(...)` returns a frozen `BlowdownResult(gas_mass_kg, ch4_mass_kg)`. In S4
the isolated volume `V` is the sum of the isolated vessels and piping taken from the facility
spec; the scenario and the agent tool supply it, this module takes it as an input.

Hand calculation (plan test, KS-07 gas, `M = 0.017302 kg/mol`, `Tpc = 196.65 K`,
`Ppc = 4.6139 MPa`): 10 m3 from 7.0 MPa and 300 K to 98.9 kPa and 300 K. At 7.0 MPa, `Z = 0.86248`
and `rho = 56.297 kg/m3`; at 98.9 kPa, `Z = 0.99761` and `rho = 0.68766 kg/m3`. Vented gas
`= 10 * (56.297 - 0.68766) = 556.09 kg`; with a methane mass fraction of 0.86234 that is 479.54 kg
of methane.

`vented_mass` raises `ValueError` (it never returns NaN or infinity) for:

- a volume that is NaN or infinite (`volume_m3 must be finite`) or not above zero
  (`volume_m3 must be > 0`);
- a pressure or temperature that is NaN, infinite, zero or negative (the message names it);
- a final pressure above the initial one (`p_final_pa must not exceed p_initial_pa`);
- a density that is not positive, which happens when the Papay Z falls to zero or below (for
  example 20 K at 10 MPa) and so lies outside the correlation's range;
- a final gas denser than the initial gas (for example the same pressure but a colder final gas):
  that is not a venting, so it is rejected instead of returned as a negative mass;
- a vented mass that overflows to infinity (absurd volume).

Equal pressures and temperatures give 0 kg. A final pressure at or below ambient is accepted; the
function does not know the ambient pressure, and the caller chooses the final state.

Limits:

- Only the start and end states are used. The path (choked then subcritical flow, cooling by
  expansion, heat from the vessel wall) is not simulated, so the caller must supply `T_f`. A real
  blowdown cools the gas, which raises the final density; using the start temperature for `T_f`
  therefore lowers `rho_f` and slightly over-states the mass released (the final density is small
  against the initial one at near-ambient final pressure).
- Z comes from the closed-form Papay correlation with Kay's rule (see Gas properties), valid for
  sweet natural gas at moderate reduced pressures. Outside that range (very cold gas, very high
  pressure) the density is wrong; only a non-positive density is detected and rejected.
- The result is only as good as the isolated volume and the pressure and temperature readings.
  Dead legs, a partly closed isolation valve, or gas that flows in from outside the isolated
  section during the blowdown are not modelled.
- The vented gas has the composition `comp` throughout; there is no fractionation of heavier
  components.
- The mass is released, not necessarily emitted: if the blowdown goes to the flare, the methane that
  reaches the atmosphere is the flare slip above, not this mass.

### Inventory

Modules `plumetrace.engineering.emission_factors` (two read-only factor tables) and
`plumetrace.engineering.inventory` (two functions). Two jobs, two tables:

| Job | Function | Table | Why |
|---|---|---|---|
| Site inventory, all components, average | `bottom_up_ch4_kg_h(counts, comp)` | `EPA_1995_AVERAGE_GAS_TOC_KG_H` | an average over all components of a population, leaking or not |
| One component found leaking by OGI (scenario S6) | `leaker_ch4_kg_h(component, location, comp)` | `SUBPART_W_W4_LEAKER_THC_SCF_H` | a factor for a component already known to leak |

Table 1, `EPA_1995_AVERAGE_GAS_TOC_KG_H` (kg of total organic compounds per hour per source). Source
comment in the code: EPA-453/R-95-017 "1995 Protocol for Equipment Leak Emission Estimates", Table
2-4 "Oil and Gas Production Operations Average Emission Factors", gas service, p. 2-14. The values
are total organic compounds, which include methane and ethane. "others" covers compressors,
diaphragms, drains, dump arms, hatches, instruments, meters, pressure relief valves, polished rods,
relief valves and vents (table footnote c).

| Source | kg TOC/h |
|---|---|
| valves | 4.5e-3 |
| pump seals | 2.4e-3 |
| others | 8.8e-3 |
| connectors | 2.0e-4 |
| flanges | 3.9e-4 |
| open-ended lines | 2.0e-3 |

Table 2, `SUBPART_W_W4_LEAKER_THC_SCF_H` (scf of total hydrocarbon per hour per leaking component).
Source comment in the code: 40 CFR Part 98 Subpart W, Table W-4 "Default Total Hydrocarbon Leaker
Emission Factors", onshore natural gas transmission compression, gas service, column "If you survey
using any of the methods in § 98.234(a)(1), (3), or (5)" (optical gas imaging); [89 FR 42325, May
14, 2024]; CFR 2025 edition.

| Component | compressor | non-compressor |
|---|---|---|
| valve | 24.2 | 10.5 |
| connector | 9.13 | 9.3 |
| open-ended line | 28.2 | 18.4 |
| pressure relief valve | 64.8 | 3.28 |
| meter | 31.6 | 4.79 |
| other | 6.70 | 6.70 |

`bottom_up_ch4_kg_h` sums, over every equipment tag,
`valves*f[valves] + connectors*f[connectors] + open_ended_lines*f[open_ended_lines] +
pressure_relief_valves*f[others]` (pressure relief valves take the "others" factor, table footnote
c) and multiplies the total by `ch4_hydrocarbon_mass_fraction(comp)` (TOC to CH4 by the methane
share of hydrocarbon mass; an approximation). The input is a mapping tag to
`ComponentCountsDict`, i.e. `ComponentCounts.model_dump()` from the facility package (engineering
never imports facility). Flanges and pump seals have factors in the table but no count in the
interface, so they are not summed.

`leaker_ch4_kg_h` converts `scf_h` to methane: `scf_h * FT3_TO_M3 * (P_STD_PA / (R * T_STD_K)) *
ch4_hydrocarbon_mole_fraction(comp) * M_CH4_KG_MOL` (THC to CH4 by the methane share of hydrocarbon
moles). The 60 degF scf versus 15 degC Sm3 reference difference is ignored (about 0.2 %).

Hand calculations (KS-07 gas: the hydrocarbons weigh 16.4415 g per mole of gas, so the methane
share of hydrocarbon mass is `0.930 * 16.043 / 16.4415 = 0.90746`; the share of hydrocarbon moles
is `0.930 / 0.975`; 1 m3 of ideal gas at 288.15 K and 101325 Pa holds 42.2925 mol):

- One compressor with 73 valves, 179 connectors, 3 open-ended lines and 4 relief valves:
  `73*4.5e-3 + 179*2.0e-4 + 3*2.0e-3 + 4*8.8e-3 = 0.4055 kg TOC/h`; times 0.90746 is 0.36798 kg
  CH4/h (about 3.2 t CH4 per year if it ran all year).
- A non-compressor valve leaker: `10.5 scf/h = 0.29733 m3/h = 12.575 mol/h`; times 0.930/0.975 and
  16.043 g/mol is 0.19243 kg CH4/h. A compressor valve leaker (24.2 scf/h) gives 0.44349 kg/h.

Both functions raise `ValueError` (they never return NaN or infinity) for: a gas without any
hydrocarbon (a TOC or THC factor cannot be converted); a count that is missing, negative, not an
integer (booleans and floats included) or so large that the rate is not finite (the message names
the equipment tag and the field); an unknown leaker component or location. An empty mapping gives
0.0, and a gas with hydrocarbons but no methane gives 0.0.

Limits:

- **The component counts are an unverified proxy.** For KS-07 the counts passed in come from the
  facility package: Subpart W Table W-1B (CFR 2023 edition) default counts for onshore natural gas
  production and gathering-and-boosting equipment, used for a transmission compressor station for
  which no default counts are published. The owner accepted them as a proxy at Gate 1
  (2026-11-13); the transcription is still to be verified against the primary text
  (`docs/OWNER_ACTIONS.md`). The site inventory inherits that, so treat it as an order of
  magnitude, not a measurement.
- The average factors describe a US oil and gas production population in the early 1990s. They are
  applied to a different kind of site (a compressor station) and a different decade; the site's
  real leak rate can be far from the average, because leaks are very unevenly distributed (a few
  large leakers dominate).
- Flanges and pump seals are not counted (no count in the interface), and every relief valve uses
  the broad "others" factor. The sum is therefore not a complete component census.
- TOC to CH4 uses the methane share of hydrocarbon mass of the bulk gas, THC to CH4 the share of
  hydrocarbon moles. Both assume a leak has the same composition as the pipeline gas.
- The W-4 factors are per leaker, not per component: they say how much a component emits once it
  leaks, not how often one leaks, and not for how long. Turning a found leak into an annual figure
  needs a duration the module does not know.
- The two tables have different bases (kg TOC/h versus scf THC/h) and different origins, so a
  site total from Table 1 and an OGI leaker from Table 2 are not additive without care.
- Results are rates for the stated gas; converting to CO2-equivalent (GWP100 or GWP20) is
  `units.co2e_kg`, and the choice of horizon belongs to the caller.

### Methane intensity

Module `plumetrace.engineering.intensity`. `methane_intensity_percent(ch4_emitted_kg_h,
throughput_sm3_h)` returns

```
intensity [%] = (ch4_emitted_kg_h / rho_CH4,std) / throughput_sm3_h * 100
```

where `rho_CH4,std = ppm_to_kg_m3(1e6, T_STD_K, P_STD_PA) = 0.67850 kg/Sm3` (pure methane, ideal
gas, 15 degC, 101325 Pa). The basis is volume: emitted methane volume at standard conditions over
gas handled volume, following the OGCI methane-intensity methodology (methane emitted volume
divided by gas handled volume).

Hand calculation (plan test): 6.785 kg/h is 10.000 Sm3/h; over 1000 Sm3/h that is 1.000 %. For
the KS-07 station, 1 kg/h of methane over 1000 Sm3/h is `1 / 0.67850 / 1000 * 100 = 0.1474 %`.

`ValueError` for a throughput that is zero, negative, NaN or infinite, an emission that is negative,
NaN or infinite, and a ratio that overflows. Zero emission gives 0 %. The result is not capped at
100 %.

Limits:

- It is an instantaneous rate over an instantaneous flow. A reported intensity is normally an
  annual figure; the caller must use rates and flows that cover the same period.
- Only the two numbers passed in are used. What counts as "gas handled" for a compressor station
  (throughput versus marketed gas) is the caller's choice and changes the percentage; this module
  does not decide it.
- Volumes use the ideal gas law at 15 degC. A mass basis, or a different reference temperature
  such as 60 degF, gives a slightly different percentage.

### Truth model (why the demo is not an inverse crime)

Modules `plumetrace.engineering.truth_weather` and `plumetrace.engineering.truth_model`, and
`plumetrace.facility.obstacles` (it lives in `facility` because `engineering` may not import it).
To keep each file within the size limits, `WakeObstacle` and the wake rule are in `truth_wake`,
`SensorFault` and its drift in `truth_faults`, the AR(1) meander and gusts in `truth_turbulence`;
`truth_model` re-exports both types. The public helpers of these modules (`interpolate_weather`,
`InterpolatedWeather`, `stability_series`, `angular_diff_deg`, `turbulent_wind`, `ar1_series`,
`wake_mask`, `apply_faults`) are the truth model's internal building blocks, not part of the plan
interface.
The simulator (Phase 3) and the benchmark (Task 13) generate sensor data with this model. The
inversion fits data with Briggs coefficients and a steady plume, so data made by the same model
would be "solved by construction" (an inverse crime). The truth model therefore differs on purpose:

| Ingredient | Parameter (default) | Why it is there |
|---|---|---|
| Other dispersion coefficients | `TruthConfig.coeff = PG_MARTIN` (inversion: `BRIGGS_RURAL`) | The two fits of the same curves differ. At 300 m on class D the centreline excess is about 24 % higher with Martin: 4.17 ppm against 3.36 ppm for 36 kg/h, 4 m/s, 290 K, 98 900 Pa, source and receptor at 2 m (hand calculation: `sy`, `sz` = 23.65 m, 14.95 m Briggs; 23.18 m, 12.17 m Martin). |
| Wind-direction meander | `meander_sd_deg = 10`, `meander_tau_s = 120` | A real wind direction wanders on the minute scale; the inversion sees window means. |
| Gusty speed | `speed_cv = 0.15`, same `meander_tau_s`, floor `MIN_SPEED_M_S = 0.3` | Speed varies around the hourly value. |
| Building wake | `wake_dilution = 0.6`; wake length 3 obstacle heights | Receptors close behind a building or shelter see less plume; the inversion has no obstacles. |
| Sensor noise | `noise_ppm = 0.3` | White Gaussian noise on every reading. |
| Drift faults | `SensorFault(sensor_id, drift_ppm_per_h, start_s)` | A fault adds `drift * max(0, t - start) / 3600` ppm to one sensor. |
| Own weather and stability | hourly weather, class by `pasquill_class` | Stability follows the hourly sun and cloud, not the inversion's window. |

The 0.3 m/s floor, the wake length of 3 heights, the 6 m shelter height and the 200 000-step cap
are Task 12 project values (no published source is claimed). The coefficient sets are the ones of
Dispersion coefficients.

Per time step `t = k * dt_s`, `k = 0 ... floor(duration_s / dt_s) - 1` (`simulate_sensors`):

1. **Weather:** `h = t / 3600`, `i = floor(h)`, `f = h - i`. Speed is linear between hour `i` and
   `i + 1`; direction is linear along the shortest arc; temperature, shortwave and cloud come from
   hour `i`. Hours past the list hold the last entry.
2. **Meander:** `phi = exp(-dt_s / meander_tau_s)`, `m_0 = sd * e_0`,
   `m_k = phi * m_(k-1) + sqrt(1 - phi^2) * sd * e_k`; direction = interpolated + `m_k`, wrapped to
   [0, 360).
3. **Gusts:** the same AR(1) with stationary sd `speed_cv` gives `r_k`;
   `speed = max(0.3, interpolated * (1 + r_k))`.
4. **Stability:** `pasquill_class(interpolated speed without gust, shortwave, cloud)`.
5. **Plume:** sum over sources with `start_s <= t < end_s` of `concentration_ppm(rate / 3600,
   speed, direction, source, receptors, stability, coeff, temp, pressure)`.
6. **Wake:** a receptor is in an obstacle's wake when, in the wind frame centred on the obstacle,
   `0 < along <= 3 * height_m` and `|cross| <= half_width_m`. Its plume is multiplied by
   `wake_dilution` once, however many wakes it is in.
7. **Output:** `background_ppm + plume + noise_ppm * e` per sensor, plus the drift of each fault.

**Random-draw order.** All draws are made up front as `rng.standard_normal((T, 2 + S))`, which
equals drawing step by step: per step the meander value, the gust value, then one noise value per
sensor in sensor order. The draws are made even when `noise_ppm`, `meander_sd_deg` or `speed_cv`
is 0, so a seed gives aligned sequences whatever the configuration, and the generator advances by
exactly `T * (2 + S)` values. The same seed and inputs give a bit-identical series. The weather
generator draws three values per hour: speed normal, direction normal, cloud beta.

**Synthetic weather** (`synthetic_hourly_weather(hours, start_hour_of_day, rng, prevailing)`):
speed `exp(ln 4 + 0.5 z)` clipped to 0.3 to 15 m/s; direction a mean-reverting walk
`d = d + N(0, 20) - 0.2 * angular_diff(d, prevailing)` (hour 0 is already one step from the
prevailing direction, default 250 deg); cloud `beta(2, 5)`; shortwave `800 sin(pi (h - 6) / 12)`
from 06 to 18 h local time times `(1 - 0.75 cloud)`, else 0; temperature 300 K if shortwave exceeds
10 W/m2, else 285 K. All of these numbers are Task 12 values.

**How Phase 3 feeds real weather.** The simulator will build one `HourlyWeather` per hour from
Open-Meteo hourly data (wind speed, wind direction, shortwave radiation, cloud cover,
temperature), converted to m/s, degrees, W/m2, a 0 to 1 fraction and K, with `hour_index` counting
from 0. `HourlyWeather` rejects non-finite or unphysical values at construction (negative speed,
cloud outside 0 to 1, temperature not above 0 K), so bad API data fails at the boundary. A calm
hour (0 m/s) is valid input: the speed floor of 0.3 m/s applies.

`ValueError` (never NaN) for: no sensors, repeated sensor ids, a fault on an unknown sensor, empty
weather, `dt_s` or `pressure_pa` not positive and finite, a duration that is not finite or shorter
than one step (zero steps is an error, not an empty series), more than 200 000 steps, an invalid
`TruthConfig`, `TrueSource`, `WakeObstacle` or `SensorFault` (checked at construction), and a
reading that is not finite (for example drifts that overflow). A source's `end_s` may be infinite.

Limits:

- It is the same Gaussian plume formula as the inversion (`concentration_ppm`) with another
  coefficient set plus noise. It does not test structural errors such as plume rise, dense-gas or
  buoyant behaviour, terrain, or a non-Gaussian vertical profile. A good benchmark result shows
  robustness to these mismatches only, not to every real-world error.
- Stability changes only at the hour boundaries of the weather (speed interpolates, sun and cloud
  do not), so a class can jump while the wind changes smoothly. The class uses no gusts.
- Meander and gusts share one correlation time and are stationary; there is no averaging-time
  dependence of the spread, and the plume is evaluated as steady state at every step.
- The wake is a box rule: one fixed factor, three heights long, one width, no recirculation or
  plume lift. A source inside a wake is not treated; only receptors are tested. A receptor inside
  the obstacle footprint (`along <= 0` from the centre) counts as outside. Rotation is ignored and
  the larger footprint side gives the width (a conservative square), see Obstacles in
  SIMULATOR.md.
- Noise is white and Gaussian with one `noise_ppm` for all sensors; `Sensor.noise_ppm` is not
  used. Drift is linear and unbounded; there is no dropout (NaN), saturation or stuck value.
- Pressure is constant, temperature is constant within an hour. Distances are clipped to 10 to
  1000 m as in Dispersion coefficients, so beyond 1 km the spread stops growing.
- The synthetic weather is deliberately simple: independent hourly speeds and clouds, no seasons,
  two temperatures, no latitude. It is for tests and the benchmark, not a climate model.
- A run is limited to 200 000 steps (about 23 days at 10 s); the step count is
  `floor(duration_s / dt_s + 1e-9)` so that `0.3 / 0.1` still gives 3.

### Benchmark

Package `benchmark` in `app/backend/benchmark/` (not part of `plumetrace`; imported top level
because pytest sets `pythonpath = ["backend"]`). It answers: how well does the Task 8 inversion
find and size a leak when the data come from different physics? Results are published in
[docs/benchmark.md](../benchmark.md) with the case-level evidence in
`docs/evidence/benchmark-<date>.json`. Evidence label: **synthetic** (a simulated station and
simulated sensors).

**Method.** `cases.generate_cases` makes 250 cases from one seeded generator (`BENCHMARK_SEED`
20261112): 160 on-list leaks (source exactly at an emission candidate), 40 off-list leaks (source
2 to 10 m from a candidate, clipped into the site bounds) and 50 no-leak controls. Rates are
log-uniform between 0.5 and 100 kg/h; each case has a random start hour and its own seed. Each case
runs 6 hours at 10 s steps through the truth model (`simulate_sensors` with the default
`TruthConfig`). `runner.run_case` then takes 10-minute window means (36 windows), the window wind
and the most frequent stability class per window, subtracts a per-sensor background (5th percentile
of the window means) and calls `invert` with its defaults (Briggs rural).

**Mismatch ingredients** (the inversion has none of them): Pasquill-Gifford/Martin coefficients
instead of Briggs rural, wind meander (10 degrees), gusty speed (15 %), building-wake dilution
(0.6), sensor noise (0.3 ppm), and off-list sources. Sensor faults and drift are not used in this
run (the truth model supports them).

**Metric definitions** (`metrics.py`; every rate is 0.0 when its denominator is 0):

- `is_correct(cr, k, positions)`: leak cases only. Take the ranked ids in order, remove `NONE`, keep
  the first `k`. Correct if one of them is the true candidate (on-list) or lies within 10 m
  horizontally of the true source (off-list). An inconclusive result is never correct.
- `top1_all` = correct at k = 1 over all leak cases; `top1_conclusive` = the same count over the
  conclusive leak cases; `top3_all` = correct at k = 3 over all leak cases.
- Rate error = `|rate - true| / true` over leak cases that are conclusive and correct at k = 1;
  median and 90th percentile (`None` when there are none).
- `inconclusive_rate` = inconclusive leak cases over all leak cases.
- `false_call_rate` = no-leak cases that are conclusive with a top id other than `NONE`, over all
  no-leak cases.
- Splits: by the dominant stability class of the case and by true rate (bins `<5`, `5-20`,
  `20-100` kg/h), over leak cases, each with `n`, `top1_all` and `inconclusive_rate`.

**Reproduce.** From `app/backend`:
`uv run python -m benchmark --revision $(git rev-parse --short HEAD)` (about one minute). Options:
`--seed`, `--quick` (6 on-list, 1 off-list, 1 no-leak case), `--out-md`, `--out-json`. The run is
deterministic: the same seed and code give the same numbers. The report and the evidence file are
written by the program and are never edited by hand.

**What the run of 2026-11-13 shows** (numbers from `docs/evidence/benchmark-2026-11-13.json`):

| Metric | Value |
|---|---|
| Top-1 accuracy (all leak cases) | 0.4 |
| Top-1 accuracy (conclusive leak cases) | 0.491 |
| Top-3 accuracy (all leak cases) | 0.62 |
| Rate error, median (relative) | 1.13 |
| Rate error, 90th percentile (relative) | 26.7 |
| Inconclusive rate (leak cases) | 0.185 |
| False-call rate (no-leak cases) | 0 |

- With these mismatches the inversion names the right source for 40 % of the leak cases (and for
  49 % of those where it commits). Top-3 is 62 %. The median rate error is 113 %, and the 90th
  percentile is 27 times the true rate: the rate is not trustworthy at this level of mismatch.
- Of the 77 conclusive leak cases (57 on-list, 20 off-list) whose top id is the true candidate,
  the median estimate-to-truth ratio is 1.84, 31 are below the true rate and 26 sit at the top
  edge of the rate grid (`rate_at_grid_edge`; estimates of 451 kg/h or more, grid 0.1 to 500).
  On-list only (57 cases): median 2.43, 24 below the true rate, 19 at the edge. The probable cause (looked at in one case): a sensor
  a few tens of metres from the source sees hits from a plume whose direction wanders (meander),
  while the inversion places a narrow plume along the 10-minute mean direction; to explain a hit
  it considers unlikely it needs a very large rate. We read this as model mismatch, not a coding
  fault: a one-off check on the first 40 cases with matched physics (Briggs coefficients, no
  meander, gusts or wake, low noise) named the true source in 31 of 40 cases (15 of 40 with the
  full truth model) with a median estimate-to-truth ratio of 0.76 (2.4 with the full truth model),
  consistent with the low bias Task 8 found on clean data. This check is **post-hoc, indicative
  only and not reproducible from the repo** (no script or evidence file was kept); do not cite it
  as a result.
- The false-call rate is 0 partly because 35 of the 50 no-leak cases are inconclusive
  (`ambiguous` or `weak_signal`); 15 are conclusive `NONE` and none names a source. The "never
  cry wolf" result is therefore also a "often says nothing" result.
- Accuracy is lowest in stability class D (0.342, 73 cases) and F (0.2, only 10 cases) and highest
  in C (0.522); the `20-100` kg/h bin has the fewest inconclusive cases (0.0606) but not the best
  top-1 (0.364). Small classes (F: 10 cases) carry a wide uncertainty.

**Limitations.** One seed and 250 cases: the figures carry sampling error (for a proportion near
0.4 with 200 leak cases, roughly plus or minus 0.07: an approximate 95 % half-width for a proportion near 0.4 over 200 leak cases: 2 x sqrt(0.4 x 0.6 / 200) = 0.069). Not tuned: constants, thresholds,
coefficients and the case list were fixed before the run; the improvement round is the owner's
decision at Gate 2 (the improvement round that followed is described below). The inversion's noise and model-error settings are the Task 8 defaults, its
rate estimates carry the known low bias of about 25 % on clean data, and the fusion step (Task 9)
is not part of this benchmark, so the figures describe the physics inversion alone. The truth
model is another Gaussian plume (see Truth model above); it does not test plume rise,
buoyancy, terrain or non-Gaussian profiles. The weather is synthetic, the station is simulated and
no real leak data were used.

**Disclosure (Gate 2).** The omitted sensor faults and drift (the benchmark has none) and the missing numeric false-alarm target are a deviation from design section 5 ("occasional sensor faults") and section 5.1b (false-alarm-rate target), accepted at Gate 2. The detection false-alarm rate was measured only in the planner prototype (0 of 20 clean no-leak seeds) and has no numeric target. The 8-sensor layout is kept, not optimised. One seed per method: about plus or minus 0.07 sampling error (an approximate 95 % half-width for a proportion near 0.4 over 200 leak cases: 2 x sqrt(0.4 x 0.6 / 200) = 0.069). The truth model shares the Gaussian formula, so the mismatch is partial (no plume rise, no terrain).


### Post-hoc reading of the committed evidence (not part of the published scoring)

The headline false-call rate of 0 counts only the 50 no-leak cases. Reading the committed JSON
`docs/evidence/benchmark-2026-11-13.json` for the 200 leak cases shows how the conclusive calls
behave. This is a reading made after the run; no code, constant, threshold or scoring changed, and
`docs/benchmark.md` is unchanged.

- 163 of the 200 leak cases are conclusive. In 9 of them the top is `NONE` (a conclusive "no
  leak" on a real leak: a missed leak, median top probability 0.663, highest 0.81). In the other
  154 a source id is named: 77 times the true candidate id and 77 times another id (one of these
  is an off-list case whose named candidate lies within 10 m of the true source, which the
  published metric counts as correct; the metric also looks past a top `NONE` to the next ranked
  id, which the JSON does not store, so the exact count of correct calls, 80, comes from the
  summary and not from the case list).
- Of the 77 calls that name another id, 8 name a candidate within 10 m of the true source
  (recomputed with `generate_cases(spec, 20261112)` and the committed JSON): one off-list case at
  9.1 m, which counts as correct under the metric, and seven on-list cases at 7.0 m, which count as
  wrong because an on-list case requires the exact id. The JSON alone does not hold the positions.
- The posterior does not separate right from wrong. The median `top_probability` is 1.0 both for the
  77 calls that name the true id and for the 77 that name another id; 76 of the first and 67 of the
  second have probability 0.95 or more. A wrong call is typically as confident as a right one: the
  probabilities are overconfident and should not be read as calibrated. This reading does not
  establish why.

Reproduce (from the repository root, standard library only):

```python
import json
import statistics as st

cases = json.load(open("docs/evidence/benchmark-2026-11-13.json"))["cases"]
leak = [c for c in cases if c["kind"] != "no_leak" and not c["inconclusive"]]
none = [c for c in leak if c["top_id"] == "NONE"]
named = [c for c in leak if c["top_id"] != "NONE"]
same = [c for c in named if c["top_id"] == c["true_candidate_id"]]
other = [c for c in named if c["top_id"] != c["true_candidate_id"]]
for name, group in (("same id", same), ("other id", other), ("NONE", none)):
    p = [c["top_probability"] for c in group]
    print(name, len(group), round(st.median(p), 3), sum(x >= 0.95 for x in p))
```

Output: `same id 77 1.0 76`, `other id 77 1.0 67`, `NONE 9 0.663 0`. Whether to add a
calibration or false-assurance metric is a decision for the owner's improvement round; it is not
added to `metrics.py` here.

### Improvement round (pre-registered 2026-11-14)

The published run (seed 20261112, revision 23b8703) stays the unchanged "before". The improvement
round scores two methods on one fresh case set with the unchanged scoring code (`metrics.py`,
`cases.py`) plus new calibration metrics. Everything below was fixed before any fresh run; the
commit that contains it is the pre-registration commit, and the official run happens at that commit.

**The change.** The Task 8 inversion assumes a narrow plume along the 10-minute mean wind
direction, while the truth model meanders. The meander-aware method (Gaussian plume, Meander
option) widens `sigma_y` by the circular standard deviation of the 10 s met-mast direction in each
window (`window_direction_sd_deg`, from the truth output `wind_from_deg`), so the spread is measured
from the data and never taken from the truth model's setting. `run_case(case, spec, meander=True)`
passes it to the inversion; `meander=False`, the default, is the published path unchanged (the
published files reproduce byte for byte apart from the date).

**Metric definitions** (`calibration.py`; correctness is `metrics.is_correct`, unchanged; every rate
is 0.0 on an empty denominator and the median is None):

- named = leak cases that are conclusive with a top id other than `NONE`.
- `confident_wrong_rate` = named cases wrong at k = 1 with `top_probability >= 0.95`, over named.
- `missed_leak_rate` = conclusive leak cases with top `NONE`, over all leak cases.
- good = named cases correct at k = 1 that report a rate.
- `rate_in_interval` = good cases with `p05 <= true rate <= p95` (both ends inclusive), over good.
- `grid_edge_share` = good cases with `rate_at_grid_edge`, over good.
- `median_rate_ratio` = median of `rate / true rate` over good.
- reliability, over named cases, in the bins `[0.6, 0.8)`, `[0.8, 0.95)` and `[0.95, 1.0]` (the last
  bin has no upper edge, so a probability a rounding step above 1.0 stays in it): n and top-1
  accuracy per bin (accuracy 0.0 for an empty bin).

**Adoption rule** (`adopt_meander(t8, m)`, applied by the code, not by hand). Adopt the
meander-aware method if and only if `m.top1_all >= t8.top1_all` (top-1 over all leak cases, from
`summarize`) and `m.confident_wrong_rate <= t8.confident_wrong_rate` and `m.false_call_rate <=
t8.false_call_rate` (from `summarize`). Ties adopt. Otherwise the app keeps the Task 8 method.

**How the comparison is paired.** `benchmark.compare` generates the cases once with
`generate_cases(spec, seed)` and runs `run_all` twice on them. Every `run_case` creates its own
generator from `case.seed`, so both methods get identical weather, noise and meander, and the only
difference is the direction spread given to the inversion. The seed is a required argument (there is
no default). Only the `summary` of the published JSON is read, for the "published" column; the
calibration rows show "not recorded" there.

**Reproduce** (from `app/backend`; the official run is task 2.17 at the pre-registration commit H,
not part of this change, and the seed below was not run by any test or by this change):
`uv run python -m benchmark.compare --seed 20261114 --revision $(git rev-parse --short HEAD)`.
It writes `docs/benchmark-improvement.md` and `docs/evidence/benchmark-improvement-<UTC date>.json`
(options `--published-json`, `--out-md`, `--out-json`, `--quick`). Both files are generated and never
edited by hand; two runs give identical files apart from the date.

**Rules against tuning.**
1. No run of seed 20261114 (test, manual or quick) before the pre-registration commit.
2. One official run, at commit H, written to the evidence files above.
3. If a bug is found after the run, the fix is code only, labelled post-hoc, the benchmark is rerun
   once and both evidence files are kept; scoring, metrics, thresholds and the rule are not changed.
4. No second improvement round.

### Improvement round results (run 2026-11-14 at efc74af, seed 20261114)

The one official run of the pre-registered comparison, made once at the pre-registration commit
`efc74af`, with the command given above and without `--quick`. A second run into other paths gave
byte-identical files. The generated files are `docs/benchmark-improvement.md` and
`docs/evidence/benchmark-improvement-2026-11-14.json`; the table and the verdict below are copied
from the generated Markdown. Evidence label: synthetic.

| Metric | Published (seed 20261112) | Fresh Task 8 | Fresh meander-aware |
|---|---|---|---|
| Top-1 accuracy (all leak cases) | 0.4 | 0.48 | 0.69 |
| Top-1 accuracy (conclusive leak cases) | 0.491 | 0.552 | 0.836 |
| Top-3 accuracy (all leak cases) | 0.62 | 0.72 | 0.805 |
| Rate error, median (relative) | 1.13 | 1.34 | 0.177 |
| Rate error, 90th percentile (relative) | 26.7 | 49.2 | 0.611 |
| Inconclusive rate (leak cases) | 0.185 | 0.13 | 0.175 |
| False-call rate (no-leak cases) | 0 | 0 | 0 |
| Confident-wrong rate (named cases wrong with p >= 0.95) | not recorded | 0.407 | 0.122 |
| Missed-leak rate (conclusive NONE on a leak case) | not recorded | 0.035 | 0.005 |
| Rate inside the 90 % interval (good cases) | not recorded | 0.2 | 0.428 |
| Rate at the grid edge (good cases) | not recorded | 0.316 | 0 |
| Median rate / true rate (good cases) | not recorded | 2.34 | 0.932 |

Reliability of the stated probability (named cases):

| Top probability | Task 8 named | Task 8 top-1 | Meander named | Meander top-1 |
|---|---|---|---|---|
| [0.6, 0.8) | 2 | 0 | 4 | 0.5 |
| [0.8, 0.95) | 4 | 0.5 | 6 | 0.333 |
| [0.95, 1.0] | 161 | 0.578 | 154 | 0.87 |

**Adopted for the app: meander-aware.** Rule: adopt the meander-aware method only if its top-1 accuracy is at least Task 8's and its confident-wrong rate and false-call rate are each at most Task 8's (ties adopt). Compared (meander-aware / Task 8): top-1 0.69 / 0.48; confident-wrong 0.122 / 0.407; false-call 0 / 0.

**Reading of the data** (plain, no more than the numbers show; hypotheses are marked).

- Accuracy. On the fresh seed the Task 8 method names the right source in 0.48 of the leak cases
  (top-1) and 0.72 in its top three; the meander-aware method in 0.69 and 0.805. The same cases are
  used for both, so the comparison is paired. Both methods have a false-call rate of 0 on the 50
  no-leak cases.
- Rate. Over the good cases (named, right at top-1, with a rate: 95 for Task 8, 138 for
  meander-aware) the median relative rate error is 1.34 for Task 8 and 0.177 for meander-aware, the
  90th percentile 49.2 and 0.611. The median rate over the true rate is 2.34 and 0.932, and the share
  of rates at the edge of the rate grid is 0.316 and 0. The two sets of good cases differ, so these
  rate figures are not a like-for-like comparison of the same cases.
- Inconclusive. The inconclusive rate is 0.13 for Task 8 and 0.175 for meander-aware: the meander
  method says "inconclusive" more often, most visibly in stability classes E and F (0.116 and 0.125
  for Task 8, 0.209 and 0.375 for meander-aware; class F has 8 cases).
- Missed and confident-wrong calls. The missed-leak rate (a conclusive `NONE` on a real leak) is
  0.035 and 0.005. The confident-wrong rate (a wrong named source with probability 0.95 or more) is
  0.407 for Task 8 and 0.122 for meander-aware.
- Is the probability calibrated? No, for either method. Among the named cases that state a
  probability of 0.95 or more (161 for Task 8, 154 for meander-aware) the top-1 accuracy is 0.578
  and 0.87. A calibrated probability would give about 0.95 or more in that bin. The meander-aware
  method is closer but still below it. The other two bins hold at most 6 cases per method and say
  little. The 90 % rate interval holds the true rate in 0.2 (Task 8) and 0.428 (meander-aware) of the
  good cases, against 0.9 for a calibrated interval: the intervals are too narrow for both. This is
  why the app labels these values "model estimate" and "model probability" (rate display rule,
  section 4).
- Seed spread. The Task 8 method was run on two seeds: the published seed (top-1 0.4, rate error
  median 1.13, inconclusive 0.185) and the fresh seed (0.48, 1.34, 0.13). That difference between
  seeds for one method is the order of the sampling error of one seed (about plus or minus 0.07, an approximate 95 % half-width for a proportion near 0.4 over 200 leak cases: 2 x sqrt(0.4 x 0.6 / 200) = 0.069); small differences between methods on a single seed should
  be read with that in mind. The top-1 gap between the two methods on the fresh seed is larger than
  the spread between the two Task 8 runs.
- Inverse crime (a statement, not a hypothesis). The meander in the benchmark data is generated by a wind-direction process acting on the same Gaussian plume formula that the meander-aware correction models. The correction is therefore partly self-consistent with the data generator: the measured gain is an optimistic result for a simulated station, an upper bound for a real site, and is not evidence of real-world accuracy. Checked against the code: the truth model (`truth_model.py`, `truth_turbulence.py`) adds a stationary AR(1) wind-direction meander (default standard deviation 10 degrees, correlation time 120 s) to the hourly wind direction and evaluates `concentration_ppm`, the same Gaussian plume formula as the inversion, at every 10 s step with the Martin coefficient set; the 10-minute window mean of that series is a time average of Gaussian plumes whose axis wanders, which is the situation the correction `sigma_y,eff^2 = sigma_y^2 + (x s)^2` describes.
- Hypotheses (not tested by this run). The gain is consistent with the within-window direction
  spread being the main cause of the poor published rate result, because the method widens exactly
  the spread the truth model injects. The meander-aware method is given the measured direction
  spread of the same truth model that produces the data, so a real station, whose wind may behave
  differently, may see a smaller gain. The higher inconclusive rate may come from the wider plume
  responding less sharply to a source; this was not examined.

**Adoption.** The code printed "Adopted for the app: meander-aware" (top-1 0.69 against 0.48,
confident-wrong 0.122 against 0.407, false-call 0 against 0). Downstream: the places that build the
window input of the inversion in later phases (Phase 3 Task 5 `selection.py` and Phase 5 Task 9
`build_inversion_input`) pass one more argument,
`wind_dir_sd_deg=window_direction_sd_deg(series.times_s, series.wind_from_deg)`, sliced to the same
windows; this is a deviation pre-approved by the Gate 2 decision (STATUS.md decisions log), and the
phase task files are not edited. The published run at `23b8703` stays the "before" and the Task 8
default path is unchanged.

## 4. Design decisions and assumptions

Index of the assumptions and limits that matter when reading a result. Each points to the module
section above that states it in full; the numbers are measured there.

| Topic | Assumption or limit | Where |
|---|---|---|
| Plume model | Gaussian, steady state over the averaging period, flat terrain, no plume rise for vents, no buildings, meander, chemistry or deposition | Gaussian plume |
| Wind | The 10 m wind is used at all heights | Gaussian plume |
| Ground | Total reflection (image source), `C = 0` wherever `along <= 0` | Gaussian plume |
| Dispersion | Briggs rural and Martin fits are extrapolated below 100 m; distances clipped to 10 to 1000 m, so within 10 m the value equals the 10 m value and beyond 1 km the spread stops growing; sigmas floored at 0.5 m | Dispersion coefficients, Truth model limits |
| Averaging | 10-minute windows, a window with under 50 % valid samples is NaN, a trailing partial window is dropped; a wind below 1 m/s is calm and not modelled | Averaging |
| Stability | Pasquill class from wind, shortwave and cloud; the W/m2 and cloud thresholds are project choices (Task 3); split cells resolve to the more stable class; in the truth model the class changes only on the hour | Stability, Truth model limits |
| Gas | Z from the closed-form Papay correlation with Kay's rule: sweet natural gas at moderate reduced pressures only, not AGA8, not sour or rich gas | Gas properties, Blowdown limits |
| Inversion | On clean data (the same plume model) the rate median sits about 25 % below the truth, and the 90 % interval narrows as windows accumulate until it no longer covers the truth; candidates that no sensor sees tie with `NONE` | Source inversion limits |
| Fusion | The likelihood ratios (0.05, 20, 4, 2 degC, `k = 1`) are project choices, not calibrated; evidence items are treated as independent (naive Bayes) | Evidence fusion limits |
| Truth model | It is the same Gaussian formula as the inversion with another coefficient set, meander, gusts, wakes and noise, so the mismatch is partial: plume rise, buoyant or dense-gas behaviour, terrain and non-Gaussian profiles are not tested | Truth model limits |
| Inventory | The component counts are an UNVERIFIED PROXY (Subpart W Table W-1B production and gathering defaults used for a transmission compressor station); the average factors are an early-1990s US production population | Inventory limits |
| Meander option | Optional `dir_sd_deg` widens `sigma_y` by the measured within-window direction spread; small-angle approximation; a project derivation, not a citation; measured effect on the fresh seed (synthetic, one seed): top-1 0.69 against 0.48 and median rate error 0.177 against 1.34 for the meander-aware method and the Task 8 method; see Improvement round results | Gaussian plume, Averaging, Source inversion, Improvement round results |
| Benchmark | Synthetic data, one seed, 250 cases; rate error at this mismatch is large (median 113 %); not tuned | Benchmark |
| Citations | Coefficients, factors and defaults (Briggs rural, Martin, EPA 1995 Protocol Table 2-4, Subpart W Tables W-1B and W-4, AP-42 §13.5, OGMP 2.0 98 %) are copied from the project plan with their source names; none has yet been checked against the primary publication (owner action before the Phase 7 release gate). | Dispersion coefficients, Inventory, Flare |
| Rate display rule | Binding for Phases 3 to 7; applies to inversion and fusion outputs, not the bottom-up inventory KPI. R1: the inversion rate is shown only as an interval "p05–p95 kg/h (median p50)" with 2 significant figures, never the median alone (UI, captions, drafts, reports). R2: the rate is suppressed when the result is inconclusive, the top is `NONE` or `rate_at_grid_edge` is true (the UI shows "rate not quantified" plus the reason, "outside model range" for the grid edge); pre-approved Phase 5 Task 9 deviation: `run_plume_inversion` returns `rate = None` in those cases and the locate agent then returns `status="inconclusive"` with an OGI request; if S1 hits the grid edge that is a Gate 3 scenario issue, not a reason to relax the rule. R3: every inversion rate and probability carries the fixed label "model estimate" / "model probability" with a link to the benchmark page, never "confidence", "certain" or "calibrated". R4: Phase 7 About and README take benchmark numbers only from the generated evidence JSON of the adopted method, showing top-1, rate-in-interval, confident-wrong rate and inconclusive rate next to the published 23b8703 numbers. Full text: `docs/superpowers/plans/STATUS.md`, Owner decisions log, entry 2026-11-14 Gate 2 | Improvement round results |

Smaller decisions: the ideal gas law is used for ppm and kg/m3 (at 288.15 K and 101325 Pa pure
methane is 0.67850 kg/m3); `scf_to_sm3` ignores the 60 degF versus 15 degC reference difference
(about 0.2 %); GWP values are AR6 fossil methane (29.8 over 100 years, 82.5 over 20 years).

## 5. Limits and failure behaviour

Policy: a function that takes external data checks it and raises `ValueError` with a message that
names the rejected input; it does not fill a default or return NaN. Pydantic models (for example
`GasComposition`, `EvidenceItem`, `HourlyWeather`, `TruthConfig`) reject bad values when they are
built (`pydantic.ValidationError` is a `ValueError`). NaN and infinity are used on purpose only as
"missing" in the window averages, the detection series and the inversion readings. Notable
rejections, by module (the module sections list the rest):

- Wind: `concentration_kg_m3` rejects a wind speed `<= 0` and a negative rate. `invert` rejects a
  finite negative wind speed; an unknown wind is NaN. Calm windows (below 1 m/s) are not an error:
  they are not used, and `invert` returns an inconclusive `calm` or `too_few_windows` result.
- Direction spread: both concentration functions reject a negative or non-finite `dir_sd_deg`;
  `invert` rejects a `wind_dir_sd_deg` of the wrong length, with a negative or infinite value, or
  with NaN where the wind direction is known.
- Shapes and lengths: `window_means`, `window_wind`, `detect_events` and `invert` raise on an array
  whose length or width does not match the time axis or the sensor count; `window_means` and
  `window_wind` also on fewer than two samples; `circular_mean_deg` on an empty array. Nothing is
  truncated.
- NaN and infinity: `flare_ch4_slip_kg_h`, `vented_mass`, `methane_intensity_percent`, the
  inventory functions, `fuse` and the truth model reject non-finite inputs. `invert` accepts them
  as missing readings but rejects a finite reading above `MAX_ABS_OBS_PPM` (1e6 ppm, inclusive
  bound) in absolute value, and raises when the log-posterior is not finite (for example an absurd
  `obs_sigma_ppm`) instead of returning a made-up distribution.
- Durations and steps: the truth model rejects `dt_s` or `pressure_pa` that is not positive and
  finite, a duration shorter than one step (zero steps is an error) and more than 200 000 steps.
- Unknown ids and names: `invert` rejects an empty candidate or sensor list, the id `NONE` and
  duplicate ids; the truth model rejects repeated sensor ids and a fault on an unknown sensor; the
  inventory rejects an unknown leaker component or location and a missing, negative or non-integer
  count; `GasComposition` rejects an unknown component. `fuse` ignores evidence about an id that is
  not in the prior (documented, not an error).
- Physical consistency: `vented_mass` rejects a final pressure above the initial one, a non-positive
  density (Papay out of range) and a final gas denser than the initial; `HourlyWeather` rejects a
  negative speed, a cloud fraction outside 0 to 1 and a temperature not above 0 K.

Not validated (callers pass physically valid values): `units` conversions (a zero temperature or
pressure gives inf or nan), `pasquill_class`, `sigmas_m`, `downwind_crosswind_m`, and
`z_factor_papay` outside its range (only a non-positive density is detected, in `vented_mass`).

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
wrap-around, NaN wind, sensor at the centre, flat history, shape and config errors.
`app/backend/tests/engineering/test_inversion.py`: recovery of a 10 kg/h source with a covering rate
interval, calm and too-few-windows, pure noise, mirror-symmetric ambiguity, 30 % NaN, a leak beyond the
grid and the 2 s budget. `test_inversion_edges.py`: empty and all-NaN data, NaN or infinite wind
and readings, ranking ties, single sensor, receptor next to the source, unreachable candidate,
`weak_signal`, low grid edge, candidate order, known zero wind versus unknown wind, the pure-methane
bound (inclusive), the negative-speed rule, the non-finite posterior guard and every input validation.
`app/backend/tests/engineering/test_fusion.py`: equal temperatures split evenly, the hot-packing share
(0.97817), renormalising and clipping, evidence for an unknown candidate, the three header cases and
the two basic rejections. `test_fusion_edges.py`: unusable priors (empty, zero, negative, NaN,
infinite, overflow), unnormalised prior, zero prior stays zero, clipping at both ends and infinite LR,
rejected LRs, repeated evidence, ties, underflow, header boundaries and reason text, non-physical
header and temperature input, common-mode rise, cold unit, overflow-safe extremes, key order and
every attribution rejection.
`app/backend/tests/engineering/test_flare.py`: unlit flare vents all methane (86.24 kg/h), lit flare
slips 2 % (1.7248 kg/h), negative flow and bad fraction. `test_flare_edges.py`: the 0.98 default,
zero flow or methane, inclusive efficiency bounds, unlit flare ignoring DE, slip monotone in DE,
huge flow, and NaN, infinite or out-of-range flow, fraction and efficiency (also when unlit).
`app/backend/tests/engineering/test_blowdown.py`: 10 m3 from 7.0 MPa (556.09 kg), no pressure drop,
pressure increase and zero volume. `test_blowdown_edges.py`: frozen result, linearity in volume,
deeper blowdown vents more, a colder final state, a final gas denser than the initial one,
non-finite and non-positive volume, pressure and temperature, Z out of range, overflow and a tiny
volume.
`app/backend/tests/engineering/test_inventory.py`: transcribed factors, one compressor
(0.36798 kg CH4/h), summing equipment, the valve leaker conversion (0.19243 and 0.44349 kg/h).
`test_inventory_edges.py`: empty site, the relief-valve "others" factor from raw numbers, linearity,
lean gas, gas without methane, bad and missing counts, the tag in the message, an absurd count, a
million valves, gas without hydrocarbons, all twelve leaker cells, the meter conversion from raw
constants, unknown names and read-only tables. `test_intensity.py`: 1.000 % and zero throughput.
`test_intensity_edges.py`: zero emission, scaling, the methane density check, above 100 %, tiny
throughput, bad throughput and emission, overflow.
`app/backend/tests/engineering/test_truth_model.py` (plan tests): determinism, the quiet Briggs
configuration equals the plume model, Martin differs from Briggs by more than 10 %, background and
noise statistics, the source window, linear drift, the 0.6 wake dilution, KS-07 obstacles and the
synthetic weather ranges (the noise statistics test uses seed 0: the plan's seed 1 is a 3.8-sigma
outlier draw for the specified draw order, so `test_noise_is_unbiased_pooled_over_50_seeds` checks the
bias over 18 000 pooled samples, owner decision 2026-11-13). `test_truth_model_edges.py`: step count and time axis, every
`ValueError` of the set-up and of the four input types, draw order and generator advance (also
with zero noise), meander on draw 0 and gusts on draw 1 against the documented recursion, wind
independent of the noise level, seeds, column order, overflow. `test_truth_model_physics_edges.py`:
the stationary statistics of meander and gusts (sd 10 deg, CV 0.15, lag-1 correlation exp(-1/12)),
the speed floor, wrap-around through north, hold of the last hour, stability and temperature per
hour, source windows (start inclusive, end exclusive), linearity, upwind sensors, drift start and
sign, and the wake boundaries (inclusive 3 heights, centre, width, once only, wind direction, zero
dilution). `test_truth_weather_edges.py`: `HourlyWeather` validation, `angular_diff_deg`, the
generator's draw order and three draws per hour, day and night, the clock shift, clipping and
wrap-around over thousands of hours, and the interpolation. `app/backend/tests/facility/
test_obstacles_edges.py`: obstacle order, sizes, flags, empty spec, rotation.
`app/backend/tests/benchmark/test_calibration.py`: each calibration metric on hand-built results
(including empty denominators, the `0.95` inclusive edge and the bin edges `0.8` and `0.95`), the
reuse of `summarize`, and the adoption truth table (each condition failing alone, ties adopt).
`test_compare.py`: `run_case(meander=False)` equals `run_case()`, `run_case(meander=True)` is valid
and finite, the quick comparison on the published seed writes both files and is identical on a
second run apart from the date, `--seed` is required, and no benchmark source or test holds the
fresh seed.
`app/backend/tests/engineering/test_meander.py` (32 tests): the circular sd of a window (constant
direction is exactly 0.0, 350/10 degrees give 10.02556, a 180 degree rotation changes nothing, NaN
where `window_wind` is NaN), `dir_sd_deg = 0.0` bit-identical to the default for both coefficient
sets, the ground-level centreline ratio `sigma_y / sigma_y,eff` at both clip edges, the unchanged
crosswind integral, rejection of a negative or non-finite spread, the inversion unchanged for `None`
and all zeros, every `wind_dir_sd_deg` check, and a recovery of 10 kg/h from VS-250.tip on data made
with an 8 degree spread (same plume model for data and inversion, so it checks the plumbing, not
mismatch). `test_inversion_reexport.py`: `inversion` still exports the same names and the moved ones
are the same objects.
Run from `app/`: `uv run pytest backend/tests/engineering -q`.

### Physical laws tested

`app/backend/tests/engineering/test_properties.py` (Hypothesis 6.170.14, 11 tests). Every test
uses `settings(max_examples=200, derandomize=True, deadline=None, database=None)`: 200 examples,
the same inputs on every run, no time limit per example and no example database (nothing is stored
or replayed between runs; Hypothesis may still create a gitignored `.hypothesis/constants` cache). Inputs are
drawn over: rate 1e-5 to 5 kg/s, wind speed 0.5 to 20 m/s, any bearing, source height 0 to 30 m,
1 to 1500 m downwind, +-300 m crosswind, receptor height 0 to 10 m, every stability class and both
coefficient sets.

| Test | Law checked | Source |
|---|---|---|
| `test_plume_is_linear_in_rate` | C(kQ) = k C(Q) | Turner (1994), eq. 1-1 (C is proportional to Q) |
| `test_plume_scales_inversely_with_wind_speed` | C u is the same for any wind speed | Turner (1994), eq. 1-1 (C is proportional to 1/u; no plume rise) |
| `test_nothing_upwind` | concentration is exactly 0 for receptors behind the source | Turner (1994), eq. 1-1 domain (downwind only) |
| `test_crosswind_mirror_symmetry_and_finiteness` | mirroring across the plume axis gives the same value; finite and non-negative | Turner (1994), eq. 1-1 (even in crosswind offset) |
| `test_rotating_the_scene_with_the_wind_changes_nothing` | rotating source, receptor and wind direction together leaves C unchanged | geometry of the wind-aligned frame |
| `test_ppm_round_trip` | kg/m3 to ppm to kg/m3 returns the input | ideal-gas law (`units.py`) |
| `test_circular_mean_rotates_with_the_data` | rotating every direction by phi rotates the circular mean by phi; result in [0, 360) | definition of the circular mean |
| `test_fusion_is_a_probability_and_order_free` | posterior is non-negative, sums to 1 and does not depend on evidence order | Bayes update with clipped likelihood ratios (`fusion.py`) |
| `test_neutral_evidence_keeps_the_prior` | likelihood ratio 1 everywhere returns the normalised prior | Bayes update with clipped likelihood ratios (`fusion.py`) |
| `test_unlit_flare_never_slips_less_than_lit` | 0 <= lit slip <= unlit slip | flare destruction efficiency (`flare.py`) |
| `test_pipeline_gas_properties_stay_physical` | for CH4 >= 85 %, 0 < Z <= 1.05 and the CH4 mass fraction is in [0, 1], over 1 to 80 bar and 260 to 330 K | Papay correlation, Kay's rule (`gas.py`) |

Only these laws are checked. The tests do not check mass conservation of the plume, monotone fall
with distance, or any property of the inversion or the truth model.


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
- 2026-11-13: Bayesian source inversion added (Phase 2 Task 8).
- 2026-11-13: evidence fusion and vent-header attribution added (Phase 2 Task 9).
- 2026-11-13: flare methane slip and blowdown vented mass added (Phase 2 Task 10).
- 2026-11-13: emission-factor inventory and methane intensity added (Phase 2 Task 11).
- 2026-11-13: truth model (weather, meander, gusts, wakes, noise, drift) for the simulator and the benchmark added (Phase 2 Task 12).
- 2026-11-13: model-mismatch benchmark (250 cases) and its report added (Phase 2 Task 13).
- 2026-11-14: property-based and metamorphic tests of the physics laws added (Phase 2 Task 14).
- 2026-11-14: Phase 2 gate documentation: intro, assumptions index and failure-behaviour sections rewritten for the whole core; the matched-physics check labelled post-hoc and not reproducible; a post-hoc reading of the benchmark evidence added (no code or scoring changed).
- 2026-11-14: optional within-window wind-direction spread added: `window_direction_sd_deg`, `dir_sd_deg` on the plume, `wind_dir_sd_deg` on the inversion; `InversionInput` moved to `inversion_input.py` (Phase 2 improvement round 2.15). The default behaviour and the published benchmark are unchanged; the effect of the option on the benchmark was not yet measured at that point (see the entry on the official run below).
- 2026-11-14: benchmark improvement round prepared: calibration metrics, the adoption rule and `python -m benchmark.compare` (Phase 2 improvement round 2.16); scoring code and the published benchmark unchanged; no fresh run yet at that point (see the entry on the official run below).
- 2026-11-14: the official improvement run was made once at the pre-registration commit `efc74af` (`python -m benchmark.compare --seed 20261114`, synthetic data, one seed per method): meander-aware top-1 0.69 against 0.48 for the Task 8 method, median rate error 0.177 against 1.34, confident-wrong rate 0.122 against 0.407, false-call rate 0 for both; the adoption rule printed "Adopted for the app: meander-aware". The probabilities and the 90 % rate intervals are not calibrated for either method. Results, reading and caveats are in "Improvement round results"; Gate 2 closed (delegated decision, `docs/evidence/2026-11-phase-2-gate-2.md`).
- 2026-11-14: `window_mode_class` added to the averaging module; `benchmark.runner.window_stability` delegates to it (Phase 3 Task 4).
