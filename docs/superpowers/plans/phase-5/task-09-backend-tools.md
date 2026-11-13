# Phase 5 · Task 9 — `agent_tools/`: the real `ToolProvider` on a scenario run

**Skills:** `plan-execution`, `engineering-core` (tools only call the tested core; no new physics), `langgraph` (tool contract), `project-documentation`.

**Rule:** every number a tool returns is computed by existing engineering / simulator / rules code
from the scenario run. A tool never invents a value; anything not modelled in MVP is stated as such
(for example no OGI survey data). Units in outputs use the `UNITS` list of Task 2.

## Files (`app/backend/plumetrace/`)
| Action | Path |
|---|---|
| Create | `simulator/inversion_input.py` (`build_inversion_input`) — and refactor `simulator/selection.py` to use it (behaviour unchanged; its tests must stay green) |
| Create | `agent_tools/__init__.py`, `agent_tools/context.py`, `agent_tools/quantities.py`, `agent_tools/sensors.py`, `agent_tools/logs.py`, `agent_tools/process.py`, `agent_tools/locate.py`, `agent_tools/compliance.py`, `agent_tools/provider.py` |
| Create (tests) | `app/backend/tests/agent_tools/conftest.py` (S1/S4/S5 runs, module-scoped), `test_sensors.py`, `test_process.py`, `test_locate.py`, `test_compliance.py`, `test_provider_contract.py` |

## Interfaces
`simulator/inversion_input.py`:
- `BASELINE_WINDOWS: Final = 12` (same as detection's baseline length)
- `def background_ppm(run: ScenarioRun) -> npt.NDArray[np.float64]` — per sensor, 5th percentile (`np.nanpercentile`) of the window means before window `BASELINE_WINDOWS`.
- `def build_inversion_input(run: ScenarioRun, spec: FacilitySpec, start_window: int, end_window: int, snapshot_temp_k: float) -> InversionInput` — observed = window means − background for windows `[start, end]` inclusive (clipped to the run), wind / stability of those windows, candidates `spec_candidates(spec)`, sensors `run.sensors`, `temp_k = snapshot_temp_k`, `pressure_pa = spec.site.ambient_pressure_pa`, Briggs rural (the defaults). This is exactly the construction `s1_passes` used; move it, do not change it.

`agent_tools/context.py`:
- `@dataclass(frozen=True) class RunContext: run_id: str; run: ScenarioRun; spec: FacilitySpec; snapshot: WeatherSnapshot; event: DetectionEvent; event_count: int` — `event` = the earliest event (`min` by `window_index`, ties by `sensor_id`).
- `def make_context(run_id: str, run: ScenarioRun, spec: FacilitySpec, snapshot: WeatherSnapshot) -> RunContext` — `ValueError("run has no detection event")` if `run.events` is empty.
- `EVENT_SPLIT_S` = `event.window_start_s` (before / after boundary for process tags); `PROCESS_WINDOW_S: Final = 1800.0`.

`agent_tools/quantities.py`: `def q(value: float, unit: str) -> Quantity` (rounds to 4 significant digits with `float(f"{value:.4g}")` — what the model sees and copies); `def tag_summary(tag: str, values: npt.NDArray, dt_s: float, split_s: float, unit: str) -> TagSummary` — means over `[split − 1800, split)` and `[split, split + 1800)` (NaN-aware), `change = after − before`.

Tool behaviour (one function per tool, `(ctx, args) -> Output`):
| Tool | Computation |
|---|---|
| `event_context` | `EventContext(run_id, scenario_id=run.definition.id, sensor_id, window_index, window_start_s, sim_start_utc=ISO Z, event_count)` |
| `get_sensor_history` | window means for the sensors and windows; unknown sensor → `ToolInputError("unknown sensor AT-199")`; window out of range → `ToolInputError`; `baseline` = `background_ppm` of that sensor (`ppm`) |
| `get_weather` | arithmetic mean of window wind speeds (`m/s`), `circular_mean_deg` of directions (`deg`), most common stability class (ties → alphabetical), `windows`, `attribution = snapshot.attribution` |
| `get_permit_log` | `run.definition.log` entries with `start_s ≤ t_s ≤ end_s`, as `LogEntryOut` (text unchanged) |
| `get_process_tags` | `tag_summary` for each tag from `run.instruments`; unit from `BASELINES`; unknown tag → `ToolInputError` |
| `check_sensor_health` | `agreeing_sensors` = other sensors with an event within ±3 windows of the event window (sorted); `wind_consistent` = the event's `downwind_of_site`; `drift_rate` = least-squares slope of the sensor's window means over the 12 windows ending at the event window, in `ppm/h`; `verdict_hint`: `suspect_stuck` if the std of the last 6 window means < 0.01 ppm, else `suspect_drift` if `agreeing_sensors == []` and slope > 0.2 ppm/h, else `consistent` |
| `run_plume_inversion` | `invert(build_inversion_input(...))` with `snapshot_temp_k` = mean snapshot temperature over the windows; `top_probability`, top 5 `ranked` (incl. `NONE`) as `CandidateProbability` (`unit "1"`), `rate` = `RateInterval` when the rate is not `None`, `inconclusive`, `reason`, `windows_used` |
| `fuse_evidence` | given the recorded `InversionOut`: top `NONE` → `ToolInputError("inversion top is NONE")`; prior = its candidate probabilities; if the top candidate is a vent anchor that equipment vents to (`VS-250.tip`, from `vents_to`): `header_flow_evidence(change of FT-250, BASELINES["FT-250"].noise_sd · 2, rate p50, "VS-250.tip")` → `fuse(prior, [item])` → `vent_p`; `packing_temperature_lrs(after means of TT-20xP, before means)` keyed by unit (`K-201`…) → `attribute_vent_source(vent_p, lrs)`; output probabilities = the units (descending) followed by the other fused candidates; `applied` = the evidence reasons. Other tops → the prior unchanged with `applied = []` |
| `get_vent_header_flow` | `tag_summary("FT-250")`; `uncertainty = 2 · noise_sd` (`kg/h`) |
| `get_packing_temperatures` | `tag_summary` for TT-201P/202P/203P; `hottest_unit` = unit whose `change` is largest (`TT-202P → K-202`) |
| `get_flare_status` | summaries of FT-601 and TE-601; `pilot_lit = TE-601 after-mean > 200 degC` (`PILOT_LIT_MIN_C: Final = 200.0`, docstring: thermocouple threshold, simulated) |
| `get_tank_status` | summaries of PT-401/402; `vru_online = True` (docstring: no VRU status tag in MVP — always reported online; stated in AGENTS.md) |
| `get_component_inventory` | `counts_for_equipment` (facility) + `bottom_up_ch4_kg_h` per tag; `source` = the counts-table source string |
| `get_ogi_results` | `OgiResultsOut(area_tag, last_survey_utc=None, findings=[])` — no OGI data in MVP scenarios (S6 is stretch) |
| `request_ogi_survey` | `OgiRequestOut(request_id=f"OGI-{run_id[:8]}-{n:02d}", status="requested")`, `n` counts requests in this provider instance |
| `lookup_regulation_rule` | `rules.lookup(...)` → `RuleRef` each (`repair_deadline = q(days, "d")` when set), `table_version = TABLE_VERSION` |
| `compute_co2e` | `per="day"`: `ch4.value · 24` kg → `co2e_t` → `q(.., "t CO2e/d")`; `per="event"`: `co2e_t(ch4.value)` → `t CO2e`; `gwp100 = q(CH4_FOSSIL_GWP100, "1")`, `gwp_source = GWP_SOURCE` |
| `compute_blowdown_mass` | unit must be a `recip_compressor` (else `ToolInputError`); `vented_mass(BLOWDOWN_VOLUME_M3 (from the S4 module), suction p, gas T, ambient p, gas T, composition)` → `volume` m3, `vented_ch4` kg, `gas_mass` kg |

`agent_tools/provider.py` — `class ScenarioToolProvider` implementing `plumetrace_agents.tools.protocol.ToolProvider` by delegating to the functions above with its `RunContext`. Module docstring lists every tool and its source module.

## Tests (key cases; full code for the contract test)
`test_provider_contract.py`:
```python
"""The backend provider satisfies the agents' ToolProvider protocol and its outputs validate."""

import inspect

from plumetrace.agent_tools.provider import ScenarioToolProvider
from plumetrace_agents.tools.protocol import ToolProvider


def test_every_protocol_method_is_implemented() -> None:
    """Same method names and parameter names as the protocol."""
    for name, member in inspect.getmembers(ToolProvider, inspect.isfunction):
        if name.startswith("_"):
            continue
        impl = getattr(ScenarioToolProvider, name)
        assert list(inspect.signature(impl).parameters) == list(inspect.signature(member).parameters)
```
Other tests (use the conftest runs; docstrings cite the scenario facts from Phase 3):
- S1: `event_context().sensor_id` is a downwind sensor; `run_plume_inversion` over `[12, event + 3]` → top `VS-250.tip`, conclusive, `rate.p50` within 7.5–30 kg/h; `fuse_evidence` → top `K-202`; `get_packing_temperatures().hottest_unit == "K-202"`; FT-250 change > 0.
- S4: `get_permit_log(0, 7200)` contains the `PTW-0412` text unchanged; `compute_blowdown_mass("K-201").vented_ch4.value == q(S4_VENTED_CH4_KG, "kg").value`; `compute_blowdown_mass("TK-401")` → `ToolInputError`.
- S5: `check_sensor_health("AT-106")` → `verdict_hint == "suspect_drift"`, `agreeing_sensors == []`, drift rate within 0.4–0.8 ppm/h.
- `compute_co2e` day: `q(14.6, "kg/h")` sourced → `14.6 · 24 · GWP / 1000` (rounded by `q`).
- Unknown sensor / tag / window range → `ToolInputError` with the messages above.
- Every output of every tool validates against its schema model (round-trip `model_dump` → `model_validate`).
- `selection.py` tests from Phase 3 still pass after the refactor.

## Steps
- [ ] Refactor `build_inversion_input` out of `selection.py` first; Phase 3 tests green.
- [ ] Tests → FAIL → implement module by module → `uv run pytest app/backend -q` green.
- [ ] Do not run the graph with `ScriptedLLM` against this provider (scripted call ids and paths belong to the fake profiles). The first full graph run on the real provider is the live run in Task 10.
- [ ] Repo checks (agent_tools imports only allowed packages; modules ≤ 300 lines).
- [ ] **Docs.** AGENTS.md → "Tools" table: fill the "computed from" column with the table above, including the MVP limitations (no OGI data, VRU always online, pilot threshold). Work-log; `STATUS.md` (last 5.9, next 5.9b).
- [ ] **Commit** `feat(agent-tools): implement the ToolProvider on scenario runs`.
