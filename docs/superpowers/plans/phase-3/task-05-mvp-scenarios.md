# Phase 3 · Task 5 — MVP scenarios S1, S4, S5

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

**Why:** these three stories are the demo (design §7). Their weather window is not guessed: a
selection script evaluates every candidate window of the real weather snapshot against explicit
criteria and the **first** window that passes is written into the scenario file.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/simulator/scenarios/__init__.py` (registry), `s1_rod_packing.py`, `s4_planned_blowdown.py`, `s5_sensor_drift.py` |
| Create | `app/backend/plumetrace/simulator/selection.py` (criteria functions) |
| Create | `scripts/select_scenario_windows.py` |
| Create | `app/backend/tests/simulator/test_mvp_scenarios.py` |

## Scenario definitions (exact values; `WEATHER_OFFSET_H` filled in by step 3)

**S1 — `s1_rod_packing.py`**: `S1_SEED = 101`, `WEATHER_OFFSET_H = <selected>`, duration 6 h.
- Source: `SourceSpec(anchor_id="VS-250.tip", rate_kg_h=15.0, start_s=7200.0)` (K-202 packing leak routed through the common vent header to VS-250).
- Instrument effects: `packing_leak_effects("K-202", 15.0, ch4_mass_fraction(KS07_COMPOSITION), start_s=7200.0)` converted to `InstrumentEffectSpec` (KS07 composition built from `load_facility().gas_composition`).
- Log (sorted): `(600, "shift_note", None, "Day shift handover: K-201, K-202 and K-203 running; VRU-410 online.")`, `(4000, "gauging", "TK-402", "TK-402 gauged by the operator; thief hatch closed and latched after gauging.")`, `(5000, "maintenance", "AT-103", "Instrument technician completed a routine check of AT-103.")`.
- Expected: `triage="leak"`, `top_candidate="VS-250.tip"`, `attributed_unit="K-202"`, `rate_min_kg_h=7.5`, `rate_max_kg_h=30.0`.

**S4 — `s4_planned_blowdown.py`**: `S4_SEED = 104`, `WEATHER_OFFSET_H = <selected>`, duration 4 h.
- Blowdown size from the engineering tool: `BLOWDOWN_VOLUME_M3 = 8.0` from `operating.suction_pressure_pa` at `operating.gas_temperature_k` down to `site.ambient_pressure_pa` at the same temperature → `vented_mass(...)`. The source rate is `ch4_mass_kg / 0.25` kg/h, active `start_s=7200.0`, `end_s=8100.0` (15 minutes), at `VS-250.tip`.
- Log: `(6600, "permit", "K-201", "PTW-0412: planned blowdown of K-201 for discharge valve maintenance, minutes 120-135 of this shift, vented to VS-250.")`, `(9000, "maintenance", "K-201", "K-201 discharge valve replaced; unit restarted.")`.
- Expected: `triage="planned_venting"`, `top_candidate=None`.
- Module constant `S4_VENTED_CH4_KG` = the computed CH4 mass (used by tests and later by the agents' `log_vented_volume`).

**S5 — `s5_sensor_drift.py`**: `S5_SEED = 105`, `WEATHER_OFFSET_H = <selected>`, duration 6 h.
- Fault: `FaultSpec(sensor_id="AT-106", drift_ppm_per_h=0.6, start_s=3600.0)`; no sources.
- Log: `(300, "calibration", "AT-106", "AT-106 last bump test 2025-03-02; next test overdue.")`, `(3000, "shift_note", None, "No work permits open on the north fence today.")`.
- Expected: `triage="sensor_fault"`, `top_candidate=None`.

Registry `simulator/scenarios/__init__.py`: `SCENARIOS: Final[Mapping[str, ScenarioDefinition]]` with the three ids; `def get_scenario(scenario_id: str) -> ScenarioDefinition` (`KeyError(f"unknown scenario {scenario_id}")`).

## Selection criteria — `simulator/selection.py`
- `CANDIDATE_OFFSETS_H: Final = tuple(range(0, 161, 2))` (every 2 h through the week; each scenario still needs `duration_h + 1` hours).
- `def first_event_after(run: ScenarioRun, t_s: float) -> DetectionEvent | None`
- `def s1_passes(run: ScenarioRun, spec: FacilitySpec) -> bool` — all of: (a) an event on any methane sensor with `window_start_s` in `[7200, 7200 + 5400]`; (b) mean window wind speed over windows 12–35 ≥ 2.0 m/s; (c) `invert(...)` (Briggs, default constants) on windows `[12, first_event.window_index + 3]` with background = 5th percentile of each sensor's windows **before** window 12 returns `top_id == "VS-250.tip"` and `inconclusive is False`.
- `def s4_passes(run: ScenarioRun) -> bool` — an event with `window_start_s` in `[7200, 8100 + 1200]` and no event before 7200.
- `def s5_passes(run: ScenarioRun) -> bool` — at least one `AT-106` event and no event on any other sensor.

`scripts/select_scenario_windows.py`: for each scenario, for each offset in `CANDIDATE_OFFSETS_H` that fits the snapshot, build the definition with that offset (`model_copy(update={"weather_offset_h": o})`), run it, apply the criterion, print `s1_rod_packing: offset 14 h PASS` lines and the first passing offset per scenario; exit code 1 if any scenario has no passing offset.

## Tests (full code) — `app/backend/tests/simulator/test_mvp_scenarios.py`
```python
"""The three MVP scenarios behave as their stories require (truth physics, real weather)."""

import pytest

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import SCENARIOS, get_scenario
from plumetrace.simulator.scenarios.s4_planned_blowdown import S4_VENTED_CH4_KG
from plumetrace.simulator.selection import s1_passes, s4_passes, s5_passes
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def test_registry() -> None:
    """Exactly the three MVP scenarios are registered."""
    assert set(SCENARIOS) == {"s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"}
    with pytest.raises(KeyError, match="s9"):
        get_scenario("s9_unknown")


def test_s1_story() -> None:
    """S1: detected after the leak starts; inversion points at VS-250.tip."""
    assert s1_passes(run_scenario(get_scenario("s1_rod_packing"), SPEC, SNAP), SPEC)


def test_s4_story() -> None:
    """S4: the blowdown is detected during its window and nothing before it."""
    assert s4_passes(run_scenario(get_scenario("s4_planned_blowdown"), SPEC, SNAP))


def test_s5_story() -> None:
    """S5: only the drifting sensor raises events."""
    assert s5_passes(run_scenario(get_scenario("s5_sensor_drift"), SPEC, SNAP))


def test_s4_vented_mass_comes_from_the_blowdown_tool() -> None:
    """8 m3 from 4.5 MPa to ambient at 300 K vents a plausible CH4 mass (tens to hundreds kg)."""
    assert 50.0 < S4_VENTED_CH4_KG < 500.0
    s4 = get_scenario("s4_planned_blowdown")
    assert s4.sources[0].rate_kg_h == pytest.approx(S4_VENTED_CH4_KG / 0.25)
```

## Steps
- [ ] **1.** Write `selection.py`, the three scenario modules with `WEATHER_OFFSET_H = 0` temporarily, the registry, and the script.
- [ ] **2.** Run `cd app && uv run python ../scripts/select_scenario_windows.py`. Paste the full output.
- [ ] **3.** Set each `WEATHER_OFFSET_H` to the **first** passing offset printed for that scenario. If a scenario has no passing offset, STOP and report the output (do not change any other value).
- [ ] **4.** Write the tests → run → all pass. Full checks green.
- [ ] **5. Docs.** SIMULATOR.md → "MVP scenarios": each story, every value, the selected offsets and the matching UTC start times, the selection criteria and why. Work-log (paste the selection output); `STATUS.md` (last 3.5, next 3.6).
- [ ] **6. Commit** `feat(scenarios): add MVP scenarios S1, S4, S5 with selected weather windows`.
