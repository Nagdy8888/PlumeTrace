# Phase 3 · Task 4 — Scenario model and runner

**Skills:** `plan-execution`, `engineering-core`, `repo-structure`, `project-documentation`.

## Files
| Action | Path |
|---|---|
| Modify | `app/backend/plumetrace/engineering/averaging.py` → add `window_mode_class` |
| Modify | `app/backend/benchmark/runner.py` → `window_stability` becomes a thin call to `window_mode_class` (its existing test must still pass unchanged) |
| Create | `app/backend/plumetrace/simulator/scenario.py`, `app/backend/plumetrace/simulator/runner.py` |
| Create | `app/backend/tests/simulator/test_scenario_runner.py` |

## Interface
`engineering/averaging.py` (add):
- `def window_mode_class(classes: Sequence[StabilityClass], steps_per_window: int, n_windows: int) -> list[StabilityClass]` — most frequent class per window; ties → alphabetically first.

`simulator/scenario.py` (Pydantic, all `frozen=True, extra="forbid"`):
- `class SourceSpec`: `anchor_id: str`, `rate_kg_h: float = Field(ge=0)`, `start_s: float = Field(ge=0)`, `end_s: float = float("inf")`
- `class FaultSpec`: `sensor_id: str`, `drift_ppm_per_h: float`, `start_s: float = Field(ge=0)`
- `class InstrumentEffectSpec`: `tag: str`, `kind: Literal["offset", "set"]`, `value: float`, `start_s: float`, `end_s: float = float("inf")`, `ramp_s: float = 0.0`; method `to_effect() -> InstrumentEffect`
- `class LogEntry`: `t_s: float = Field(ge=0)`, `kind: Literal["permit", "gauging", "maintenance", "shift_note", "calibration"]`, `tag: str | None = None`, `text: str`
- `class ExpectedOutcome`: `triage: Literal["leak", "sensor_fault", "planned_venting"]`, `top_candidate: str | None = None`, `attributed_unit: str | None = None`, `rate_min_kg_h: float | None = None`, `rate_max_kg_h: float | None = None`, `rule_ids: list[str] = []`
- `class ScenarioDefinition`: `id: str = Field(pattern=r"^s[0-9]+_[a-z0-9_]+$")`, `title: str`, `seed: int`, `weather_offset_h: int = Field(ge=0)`, `duration_h: int = Field(ge=1, le=24)`, `sources: list[SourceSpec] = []`, `faults: list[FaultSpec] = []`, `instrument_effects: list[InstrumentEffectSpec] = []`, `log: list[LogEntry] = []`, `expected: ExpectedOutcome`, `variant_index: int | None = None`. Validator: `log` sorted by `t_s` (re-sort on construction via a `model_validator(mode="after")` returning a copy is not possible on frozen models — instead **require** sorted input and raise `ValueError("log entries must be sorted by t_s")`).

`simulator/runner.py`:
- `DT_S: Final = 10.0`
- `@dataclass(frozen=True) class ScenarioRun`: `definition: ScenarioDefinition`, `sim_start_utc: datetime`, `sensors: list[Sensor]`, `series: TruthSeries`, `instruments: dict[str, npt.NDArray[np.float64]]`, `window_start_s: npt.NDArray[np.float64]`, `window_means_ppm: npt.NDArray[np.float64]`, `window_wind_speed_m_s: npt.NDArray[np.float64]`, `window_wind_from_deg: npt.NDArray[np.float64]`, `window_stability: list[StabilityClass]`, `events: list[DetectionEvent]`
- `def site_center_xy(spec: FacilitySpec) -> tuple[float, float]` — centre of the site bounds.
- `def run_scenario(definition: ScenarioDefinition, spec: FacilitySpec, snapshot: WeatherSnapshot) -> ScenarioRun`:
  1. `rng = np.random.default_rng(definition.seed)`;
  2. `weather = slice_hours(snapshot, definition.weather_offset_h, definition.duration_h + 1)`;
  3. sources → `TrueSource(position=<candidate position of anchor_id>, rate_kg_h, start_s, end_s)`; unknown anchor → `KeyError(f"unknown anchor {anchor_id}")`; faults → `SensorFault`;
  4. `series = simulate_sensors(sources, methane_sensors(spec), weather, DT_S, duration_h·3600, rng, spec.site.ambient_pressure_pa, obstacles=facility_obstacles(spec), faults=faults)` (default `TruthConfig()`);
  5. `instruments = simulate_instruments(series.times_s, [e.to_effect() for e in instrument_effects], rng)` (same `rng`, after the sensors);
  6. window means / wind / `window_mode_class(series.stability, int(WINDOW_S/DT_S), n)`;
  7. `events = detect_events(window_start_s, window_means_ppm, sensors, site_center_xy(spec), window_wind_from_deg)`;
  8. `sim_start_utc = snapshot.start_utc + timedelta(hours=definition.weather_offset_h)`.

## Tests (full code) — `app/backend/tests/simulator/test_scenario_runner.py`
```python
"""Tests for the scenario model and runner (real weather snapshot, truth physics)."""

import numpy as np
import pytest
from pydantic import ValidationError

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import run_scenario, site_center_xy
from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    FaultSpec,
    LogEntry,
    ScenarioDefinition,
    SourceSpec,
)
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def _defn(**kw: object) -> ScenarioDefinition:
    base: dict[str, object] = dict(id="s9_test", title="Test", seed=3, weather_offset_h=30,
                                   duration_h=3, expected=ExpectedOutcome(triage="leak"))
    base.update(kw)
    return ScenarioDefinition(**base)


def test_site_center() -> None:
    """The KS-07 site centre is (100, 75)."""
    assert site_center_xy(SPEC) == (100.0, 75.0)


def test_run_shapes_and_determinism() -> None:
    """3 h at 10 s -> 1080 samples, 18 windows; identical for the same seed."""
    d = _defn(sources=[SourceSpec(anchor_id="VS-250.tip", rate_kg_h=20.0, start_s=3600.0)])
    a, b = run_scenario(d, SPEC, SNAP), run_scenario(d, SPEC, SNAP)
    assert a.series.ppm.shape == (1080, 8)
    assert a.window_means_ppm.shape == (18, 8)
    assert len(a.window_stability) == 18
    assert np.array_equal(a.series.ppm, b.series.ppm)
    assert a.sim_start_utc.isoformat().startswith("2025-07-15T06:00:00")
    assert set(a.instruments) >= {"FT-250", "TT-202P"}


def test_quiet_station_raises_no_events() -> None:
    """No sources and no faults -> no detection events."""
    assert run_scenario(_defn(), SPEC, SNAP).events == []


def test_drifting_sensor_is_detected() -> None:
    """A 0.6 ppm/h drift on AT-106 is detected on AT-106 only."""
    run = run_scenario(_defn(faults=[FaultSpec(sensor_id="AT-106", drift_ppm_per_h=0.6,
                                               start_s=1800.0)]), SPEC, SNAP)
    assert {e.sensor_id for e in run.events} == {"AT-106"}


def test_unknown_anchor_and_short_weather() -> None:
    """Bad anchors and scenarios longer than the snapshot fail clearly."""
    with pytest.raises(KeyError, match="NOPE"):
        run_scenario(_defn(sources=[SourceSpec(anchor_id="NOPE", rate_kg_h=1.0, start_s=0.0)]),
                     SPEC, SNAP)
    with pytest.raises(ValueError, match="need"):
        run_scenario(_defn(weather_offset_h=160, duration_h=12), SPEC, SNAP)


def test_log_must_be_sorted() -> None:
    """Unsorted log entries are rejected."""
    with pytest.raises(ValidationError, match="sorted"):
        _defn(log=[LogEntry(t_s=100.0, kind="shift_note", text="b"),
                   LogEntry(t_s=50.0, kind="shift_note", text="a")])
```

## Steps
- [x] Tests → FAIL → implement (add `window_mode_class`; refactor `benchmark.runner.window_stability` to call it) → full checks green, including the Phase 2 benchmark tests.
- [x] **Docs.** SIMULATOR.md → "Scenarios: model and runner" (fields, units, the runner steps, random-draw order, time model). ENGINEERING.md → note `window_mode_class`. Work-log; `STATUS.md` (last 3.4, next 3.5).
- [ ] **Commit** `feat(simulator): add scenario model and runner`.
