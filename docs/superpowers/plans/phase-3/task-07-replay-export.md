# Phase 3 · Task 7 — Plume field and replay scenario export

**Skills:** `plan-execution`, `engineering-core`, `frontend-3d` (plume input contract), `project-documentation`.

**Why:** the Vercel replay needs each scenario as a static file: sensor and instrument series, wind,
events, log, and plume key frames the 3D layer renders (design §9, §10; `frontend-3d/references/plume-and-effects.md`). Budget ≤ 5 MB per file.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/engineering/plume_field.py` |
| Create | `app/backend/plumetrace/simulator/replay_schema.py`, `app/backend/plumetrace/simulator/export.py` |
| Create | `scripts/export_scenarios.py` |
| Modify | `scripts/export_contract.py` (contract now covers the replay format) and `app/backend/tests/test_export_contract.py` (one assertion changes, shown below) |
| Generated | `app/replay/scenarios/s1_rod_packing.json`, `s4_planned_blowdown.json`, `s5_sensor_drift.json`; regenerated `contract.schema.json` / `contract.ts` |
| Create | `app/backend/tests/engineering/test_plume_field.py`, `app/backend/tests/simulator/test_export.py` |

## Interface
`engineering/plume_field.py`:
- `@dataclass(frozen=True) class GridSpec: x0_m: float = 0.0; y0_m: float = 0.0; dx_m: float = 5.0; dy_m: float = 5.0; nx: int = 40; ny: int = 30; z_m: float = 1.5` — cell centres at `x0 + (i + 0.5)·dx`.
- `def ground_grid_ppm(sources: Sequence[TrueSource], t_s: float, wind_speed_m_s: float, wind_from_deg: float, stability: StabilityClass, coeff: CoefficientSet, temp_k: float, pressure_pa: float, grid: GridSpec = GridSpec()) -> npt.NDArray[np.float64]` — shape `(ny, nx)`, sum of `concentration_ppm` of sources active at `t_s` (above background).
- `PPM_MIN: Final = 0.1`; `DECADES: Final = 4.0` (0.1–1000 ppm)
- `def encode_log_u8(ppm: npt.NDArray[np.float64]) -> bytes` — per cell: `0` if `ppm < PPM_MIN`, else `clip(round(1 + 254·log10(ppm/PPM_MIN)/DECADES), 1, 255)`; row-major (`y` then `x`), returned as `bytes`.
- `def decode_log_u8(data: bytes, ny: int, nx: int) -> npt.NDArray[np.float64]` — `0 → 0.0`; `b → PPM_MIN·10^((b − 1)·DECADES/254)`.

`simulator/replay_schema.py` (Pydantic, `extra="forbid"`):
- `REPLAY_SCHEMA_VERSION: Final = 1`; `REPLAY_STEP_S: Final = 60.0`; `KEYFRAME_STEP_S: Final = 120.0`; `MAX_REPLAY_BYTES: Final = 5_000_000`
- `ReplaySensor(id: str, x_m: float, y_m: float, z_m: float)`
- `ReplayEvent(sensor_id: str, window_index: int, window_start_s: float, mean_ppm: float, baseline_ppm: float, downwind_of_site: bool)`
- `ReplaySource(anchor_id: str, rate_kg_h: float)`
- `PlumeKeyframe(t_s: float, wind_speed_m_s: float, wind_from_deg: float, stability: str, sources: list[ReplaySource], grid_b64: str)` (base64 of `encode_log_u8`)
- `ReplayGrid(x0_m, y0_m, dx_m, dy_m: float, nx, ny: int, encoding: Literal["log_u8_0.1_1000ppm"])`
- `ReplayLogEntry(t_s: float, kind: str, tag: str | None, text: str)`
- `ReplayScenario(schema_version: Literal[1], scenario_id: str, title: str, sim_start_utc: str, duration_s: float, step_s: float, sensors: list[ReplaySensor], series: dict[str, list[float | None]], units: dict[str, str], wind_speed_m_s: list[float], wind_from_deg: list[float], stability: list[str], events: list[ReplayEvent], log: list[ReplayLogEntry], grid: ReplayGrid, keyframes: list[PlumeKeyframe], attribution: str, simulated: Literal[True])` — `series` keys: the 8 methane sensors (ppm) and every instrument tag; every list sampled at `step_s` (60 s means; NaN → `None`); `sim_start_utc` ISO-8601 with `Z`.

`simulator/export.py`:
- `def build_replay(run: ScenarioRun, spec: FacilitySpec, attribution: str) -> ReplayScenario` — 60 s means via `window_means(..., window_s=60.0)` for methane and instruments, 60 s wind via `window_wind(..., 60.0)` and `window_mode_class(..., 6, n)`; key frames every 120 s using the **truth** coefficients (`TruthConfig().coeff`) and the 60 s wind at that time; sources = scenario sources active at `t_s`.
- `def replay_bytes(replay: ReplayScenario) -> bytes` — `json.dumps(replay.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"`; raises `ValueError(f"{scenario_id} replay is {n} bytes, budget {MAX_REPLAY_BYTES}")` when over budget.

`scripts/export_scenarios.py`: for every registered scenario: run, build, write `app/replay/scenarios/<id>.json` with `replay_bytes`, print `<id>: <n> bytes`.

`scripts/export_contract.py` changes: add `class Contract(BaseModel): facility: FacilitySpec; replay_scenario: ReplayScenario` and make `build_contract_schema()` return `Contract.model_json_schema()` with `"title": "Contract"`. In `test_export_contract.py` replace the body of `test_contract_schema_describes_facility_spec` with:
```python
    mod = _load_script()
    schema = mod.build_contract_schema()
    assert schema["title"] == "Contract"
    assert {"facility", "replay_scenario"} <= set(schema["properties"])
```

## Tests (full code)

`app/backend/tests/engineering/test_plume_field.py`:
```python
"""Tests for the ground concentration grid and its byte encoding."""

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.plume_field import GridSpec, decode_log_u8, encode_log_u8, ground_grid_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource

SRC = TrueSource(Point3(85.0, 115.0, 12.0), 15.0, 0.0, 1e9)


def test_grid_shape_and_downwind_mass() -> None:
    """The 40 x 30 grid has signal downwind (wind from 250 -> east-north-east) and none upwind."""
    g = ground_grid_ppm([SRC], 10.0, 4.0, 250.0, StabilityClass.D,
                        CoefficientSet.PG_MARTIN, 300.0, 98900.0)
    assert g.shape == (30, 40)
    assert g[:, 30:].max() > 0.0
    assert g[:, :10].max() == 0.0


def test_inactive_source_gives_empty_grid() -> None:
    """Before the source starts the grid is all zero."""
    late = TrueSource(Point3(85.0, 115.0, 12.0), 15.0, 100.0, 1e9)
    assert ground_grid_ppm([late], 10.0, 4.0, 250.0, StabilityClass.D,
                           CoefficientSet.PG_MARTIN, 300.0, 98900.0).max() == 0.0


def test_log_u8_round_trip() -> None:
    """Values round-trip within one quantisation step (4 decades / 254 steps = 3.7 %)."""
    ppm = np.array([[0.0, 0.05, 0.1, 1.0], [10.0, 123.0, 999.0, 5000.0]])
    out = decode_log_u8(encode_log_u8(ppm), 2, 4)
    assert out[0, 0] == 0.0 and out[0, 1] == 0.0
    for v, d in [(0.1, out[0, 2]), (1.0, out[0, 3]), (10.0, out[1, 0]), (123.0, out[1, 1])]:
        assert d == pytest.approx(v, rel=0.04)
    assert out[1, 3] == pytest.approx(1000.0, rel=0.04)
    assert len(encode_log_u8(np.zeros(GridSpec().ny * GridSpec().nx).reshape(30, 40))) == 1200
```

`app/backend/tests/simulator/test_export.py`:
```python
"""Tests for the replay export (format, sampling, budget)."""

import base64
import json

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.export import build_replay, replay_bytes
from plumetrace.simulator.replay_schema import MAX_REPLAY_BYTES
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def test_s1_replay_structure_and_budget() -> None:
    """S1 (6 h): 360 one-minute samples, 180 key frames, every tag present, under 5 MB."""
    replay = build_replay(run_scenario(get_scenario("s1_rod_packing"), SPEC, SNAP), SPEC,
                          SNAP.attribution)
    assert replay.simulated is True and replay.schema_version == 1
    assert len(replay.wind_speed_m_s) == 360
    assert all(len(v) == 360 for v in replay.series.values())
    assert {"AT-101", "AT-108", "FT-250", "TT-202P"} <= set(replay.series)
    assert replay.units["AT-104"] == "ppm" and replay.units["FT-250"] == "kg/h"
    assert len(replay.keyframes) == 180
    assert len(base64.b64decode(replay.keyframes[0].grid_b64)) == 1200
    data = replay_bytes(replay)
    assert len(data) <= MAX_REPLAY_BYTES
    assert json.loads(data)["scenario_id"] == "s1_rod_packing"
    assert replay.sim_start_utc.endswith("Z")
```

## Steps
- [x] Tests → FAIL → implement → full checks green.
- [x] Run `cd app && uv run python ../scripts/export_scenarios.py` (paste sizes), then `uv run python ../scripts/export_contract.py` and `cd frontend && npm run gen:types`; frontend checks still green.
- [x] **Docs.** `docs/reference/REPLAY.md` (new; add to `docs/README.md`): the file format field by field, units, sampling, the `log_u8` encoding (formula + decode), size budget, how to regenerate, "never hand-edit". ENGINEERING.md → "Plume field". Work-log; `STATUS.md` (last 3.7, next 3.8).
- [ ] **Commit** `feat(replay): add plume field encoding and replay scenario export`.
