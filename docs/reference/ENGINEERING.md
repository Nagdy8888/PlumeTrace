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

## 4. Design decisions and assumptions

- Ideal gas law for ppm and kg/m3; at 288.15 K and 101325 Pa pure methane is 0.67850 kg/m3.
- `scf_to_sm3` ignores the 60 °F versus 15 °C reference difference (about 0.2 %).
- Z uses the closed-form Papay correlation (no iteration) with Kay's rule, not AGA8; adequate for
  the sweet KS-07 gas, not for sour or rich gas.
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
of a bad sum or unknown component (hand calculations in the docstrings). Run from `app/`:
`uv run pytest backend/tests/engineering -q`.

## 8. How to extend

Add a constant only in `constants.py` with a `# source:` comment, never inline in a model. Name
every quantity with its unit suffix. Keep functions pure.

## 9. Changelog

- 2026-11-13: constants and unit conversions added (Phase 2 Task 1).
- 2026-11-13: gas composition, Papay Z factor, density and CH4 fractions added (Phase 2 Task 2).
