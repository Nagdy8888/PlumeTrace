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

## 4. Design decisions and assumptions

- Ideal gas law for ppm and kg/m3; at 288.15 K and 101325 Pa pure methane is 0.67850 kg/m3.
- `scf_to_sm3` ignores the 60 °F versus 15 °C reference difference (about 0.2 %).
- GWP values are AR6 fossil methane (29.8 over 100 years, 82.5 over 20 years).

## 5. Limits and failure behaviour

No input validation: temperature and pressure must be positive (division by `T`, `P`, `M`
otherwise yields inf or nan). Callers pass physically valid values.

## 6. Configuration

None. Constants are code, not settings.

## 7. Testing and evidence

`app/backend/tests/engineering/test_units.py`: constant values, rate conversions, methane density
at standard conditions, ppm round trip, array shape, scf and CO2e. Run from `app/`:
`uv run pytest backend/tests/engineering -q`.

## 8. How to extend

Add a constant only in `constants.py` with a `# source:` comment, never inline in a model. Name
every quantity with its unit suffix. Keep functions pure.

## 9. Changelog

- 2026-11-13: constants and unit conversions added (Phase 2 Task 1).
