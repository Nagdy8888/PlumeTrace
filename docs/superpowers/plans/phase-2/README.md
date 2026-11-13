# Phase 2 — Engineering core

> **For agentic workers:** load `plan-execution` and `engineering-core` first. **Do not start
> until STATUS.md records Owner Gate 1 as signed off.** Execute the task files in numeric order,
> one per session/subagent, exactly as written. Every test is given as full code — copy it
> verbatim; never edit a test to make it pass. Expected values were computed by the planner and
> cross-checked; if one cannot pass with the specified implementation, STOP and report.

**Goal:** the tested pure-Python physics behind every number PlumeTrace shows, and the honest
model-mismatch benchmark published in `docs/benchmark.md`.

**Spec:** design §5 (all), §4 (gas composition, instruments), §7 (S1/S4/S5 needs).

## Task order
| # | File | Delivers |
|---|---|---|
| 1 | `task-01-units-constants.md` | `constants.py`, `units.py` (+ numpy dependency) |
| 2 | `task-02-gas-properties.md` | `gas.py` (composition, Papay Z, density, fractions) |
| 3 | `task-03-stability.md` | `stability.py` (Pasquill class from weather) |
| 4 | `task-04-dispersion.md` | `dispersion.py` (Briggs rural + Pasquill–Gifford/Martin) |
| 5 | `task-05-plume.md` | `plume.py` (Gaussian plume forward model) |
| 6 | `task-06-averaging.md` | `averaging.py` (windows, circular mean, calm) |
| 7 | `task-07-detection.md` | `detection.py` (rolling baseline + CUSUM) |
| 8 | `task-08-inversion.md` | `inversion_model.py`, `inversion.py` (Bayesian source inversion) |
| 9 | `task-09-fusion.md` | `fusion.py` (evidence fusion, vent attribution) |
| 10 | `task-10-flare-blowdown.md` | `flare.py`, `blowdown.py` |
| 11 | `task-11-inventory-intensity.md` | `emission_factors.py`, `inventory.py`, `intensity.py` |
| 12 | `task-12-truth-model.md` | `truth_weather.py`, `truth_model.py` |
| 13 | `task-13-benchmark.md` | `app/backend/benchmark/` + `docs/benchmark.md` |
| 14 | `task-14-property-tests.md` | Hypothesis property-based and metamorphic tests of the physics laws |

## Global constraints (every task)
- Everything in `phase-1/README.md` → Global constraints still applies.
- `app/backend/plumetrace/engineering/` is **pure**: no file/network I/O, no LLM, no global mutable state, no `print`. Randomness only through a `numpy.random.Generator` passed in. Constants and factor tables are Python modules with source comments (no YAML in `engineering/`).
- SI inside; every quantity name carries its unit (`rate_kg_h`, `u_m_s`, `conc_ppm`, `temp_k`, `pressure_pa`, `x_m`). Conversions only via `units.py`.
- Coordinates: x east, y north, z up (m). Wind direction = meteorological **from**, degrees clockwise from north; the plume travels toward `from + 180°`.
- Values written in a task are copied verbatim. If a cited source disagrees, STOP and report.
- Vectorise with numpy. Functions ≤ 50 lines, modules ≤ 300 lines, ≤ 12 top-level definitions per module (`check_structure.py`).
- Tests live in `app/backend/tests/engineering/` (no `__init__.py`). Test docstrings say what is proven and cite the reference for physics values.
- After every task: full check list from `plan-execution` → "Finishing a task" (pytest, ruff, ruff format, mypy, the repo checks), docs section in `docs/reference/ENGINEERING.md`, work-log row, `STATUS.md`, commit.

## Review focus (edge cases pinned by tests in this phase)
1. Calm / zero wind → plume raises `ValueError` for `u ≤ 0`; inversion returns `inconclusive` with reason `"calm"` (Tasks 5, 8).
2. Receptor next to the source (along-wind distance < 10 m) → clipped, finite (Task 5).
3. Wind direction wrap-around 359°/1° → circular mean ≈ 0° (Task 6).
4. Sensor dropout (`NaN`) → ignored by detection and inversion (Tasks 7, 8).
5. Leak larger than the rate grid (> 500 kg/h) → `rate_at_grid_edge = True` (Task 8).

## Phase exit — Owner Gate 2
After Task 13: `docs/reference/ENGINEERING.md` complete, `docs/benchmark.md` generated, evidence
JSON committed. `STATUS.md`: "Phase 2 complete — waiting for Gate 2 (physics assumptions +
benchmark). Improvement round: not started." STOP. Do not tune anything to improve the numbers.
