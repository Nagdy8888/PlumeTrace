# Phase 2 · Task 12 — Truth model (physics for the simulator and the benchmark)

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

**Why:** the simulator (Phase 3) and the benchmark (Task 13) must generate sensor data with
**different physics** from the inversion, otherwise every demo is "solved by construction".
This module is that truth model: Pasquill–Gifford/Martin coefficients, wind meander, gusty speed,
building-wake dilution, sensor noise and drift faults.

## Files
Create `app/backend/plumetrace/engineering/truth_weather.py`, `app/backend/plumetrace/engineering/truth_model.py`, `app/backend/tests/engineering/test_truth_model.py`. (`facility_obstacles` lives in the facility package because engineering must not import facility: create `app/backend/plumetrace/facility/obstacles.py`.)

## Interface

`truth_weather.py`:
- `class HourlyWeather(BaseModel)` (frozen): `hour_index: int`, `wind_speed_m_s: float`, `wind_from_deg: float`, `shortwave_w_m2: float`, `cloud_fraction: float`, `temp_k: float`. (Phase 3 fills this from Open-Meteo.)
- `def synthetic_hourly_weather(hours: int, start_hour_of_day: int, rng: np.random.Generator, prevailing_from_deg: float = 250.0) -> list[HourlyWeather]` — for `i in range(hours)`, local hour `h = (start_hour_of_day + i) % 24`:
  - speed: `exp(ln(4.0) + 0.5·N(0,1))` clipped to `[0.3, 15.0]`;
  - direction: start at `prevailing_from_deg`; each hour `d = d + N(0, 20) − 0.2·angular_diff(d, prevailing)` then `mod 360` (`angular_diff` = signed smallest difference in (−180, 180]);
  - cloud: `rng.beta(2.0, 5.0)`;
  - shortwave: `max(0, 800·sin(π·(h − 6)/12))` for `6 ≤ h ≤ 18`, else `0`; then `× (1 − 0.75·cloud)`;
  - temperature: `300.0` if shortwave > 10 else `285.0`.
  Draw order per hour: speed normal, direction normal, cloud beta.

`truth_model.py`:
```python
@dataclass(frozen=True)
class TruthConfig:
    coeff: CoefficientSet = CoefficientSet.PG_MARTIN
    meander_sd_deg: float = 10.0
    meander_tau_s: float = 120.0
    speed_cv: float = 0.15
    wake_dilution: float = 0.6
    noise_ppm: float = 0.3
    background_ppm: float = BACKGROUND_PPM

@dataclass(frozen=True)
class TrueSource:
    position: Point3
    rate_kg_h: float
    start_s: float
    end_s: float

@dataclass(frozen=True)
class WakeObstacle:
    center_xy: tuple[float, float]
    half_width_m: float
    height_m: float

@dataclass(frozen=True)
class SensorFault:
    sensor_id: str
    drift_ppm_per_h: float
    start_s: float

@dataclass(frozen=True)
class TruthSeries:
    times_s: npt.NDArray[np.float64]          # (T,)
    ppm: npt.NDArray[np.float64]              # (T, S) absolute ppm
    wind_speed_m_s: npt.NDArray[np.float64]   # (T,)
    wind_from_deg: npt.NDArray[np.float64]    # (T,)
    stability: list[StabilityClass]           # length T
    temp_k: npt.NDArray[np.float64]           # (T,)

MIN_SPEED_M_S: Final = 0.3

def simulate_sensors(sources: list[TrueSource], sensors: list[Sensor], weather: list[HourlyWeather],
                     dt_s: float, duration_s: float, rng: np.random.Generator, pressure_pa: float,
                     obstacles: Sequence[WakeObstacle] = (), faults: Sequence[SensorFault] = (),
                     config: TruthConfig = TruthConfig()) -> TruthSeries
```
Per time step `t = k·dt_s`, `k = 0 … floor(duration_s/dt_s) − 1` (split into helpers ≤ 50 lines):
1. **Weather interpolation:** `h = t/3600`, `i = floor(h)`, `f = h − i`; hours beyond the list hold the last entry. Speed linear between hour `i` and `i+1`; direction linear along the shortest arc; temperature, shortwave and cloud from hour `i`.
2. **Meander:** `φ = exp(−dt_s/meander_tau_s)`; `m_0 = σ·ε`, `m_k = φ·m_{k−1} + sqrt(1−φ²)·σ·ε` with `σ = meander_sd_deg`; direction = interpolated + `m_k`.
3. **Gusts:** same AR(1) with stationary sd `speed_cv`: `r_k`; speed = `max(MIN_SPEED_M_S, interpolated·(1 + r_k))`.
4. **Stability:** `pasquill_class(interpolated speed (without gust), shortwave, cloud)`.
5. **Plume:** sum over sources active at t (`start_s ≤ t < end_s`) of `concentration_ppm(rate/3600, speed, direction, source, receptors, stability, config.coeff, temp, pressure_pa)`.
6. **Wake:** a receptor is in an obstacle's wake when, relative to the obstacle centre and the step's wind, `0 < along ≤ 3·height_m` and `|cross| ≤ half_width_m` (use `downwind_crosswind_m`); its plume contribution is multiplied by `wake_dilution` **once** if it is in any wake.
7. **Output:** `background_ppm + plume + N(0, noise_ppm)` per sensor, plus for each fault `drift_ppm_per_h · max(0, t − start_s)/3600` on that sensor.
Random draws per step, in order: meander `ε`, gust `ε`, then `S` sensor-noise values (with `noise_ppm = 0`, still draw them so sequences stay aligned).

`facility/obstacles.py`:
- `SHELTER_HEIGHT_M: Final = 6.0`
- `def facility_obstacles(spec: FacilitySpec) -> list[WakeObstacle]` — every `building` (`half_width = max(size_x, size_y)/2`, `height = size_z`) and every equipment with `shelter: true` (`half_width = max(size_x, size_y)/2`, `height = SHELTER_HEIGHT_M`), in spec order.

## Tests (full code) — `app/backend/tests/engineering/test_truth_model.py`

> Owner decision 2026-11-13: test_background_and_noise_statistics seed 1 -> 0. The literal draw order (meander, gust, then S noise) gives mean 1.8896 for seed 1 (3.8 sigma); the implementation is unbiased over seeds 0-299 (mean 1.9503). Planner defect, not a code change.
```python
"""Tests for the truth model used by the simulator and the benchmark."""

import numpy as np
import pytest

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Point3, Sensor
from plumetrace.engineering.plume import concentration_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import (
    SensorFault,
    TrueSource,
    TruthConfig,
    WakeObstacle,
    simulate_sensors,
)
from plumetrace.engineering.truth_weather import HourlyWeather, synthetic_hourly_weather
from plumetrace.facility.loader import load_facility
from plumetrace.facility.obstacles import facility_obstacles

P = 98900.0
SENSOR = Sensor("S1", Point3(300.0, 0.0, 2.0), 0.3)
SOURCE = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 0.0, 1e9)  # 36 kg/h = 0.01 kg/s
OVERCAST_WEST = [HourlyWeather(hour_index=i, wind_speed_m_s=4.0, wind_from_deg=270.0,
                               shortwave_w_m2=0.0, cloud_fraction=0.9, temp_k=290.0)
                 for i in range(2)]
QUIET = dict(meander_sd_deg=0.0, speed_cv=0.0, wake_dilution=1.0, noise_ppm=0.0)


def _run(config: TruthConfig, sources: list[TrueSource] | None = None, seed: int = 0,
         **kw: object):
    return simulate_sensors(sources if sources is not None else [SOURCE], [SENSOR],
                            OVERCAST_WEST, 10.0, 3600.0, np.random.default_rng(seed), P,
                            config=config, **kw)


def _expected_excess() -> float:
    rec = np.array([[300.0, 0.0, 2.0]])
    return float(concentration_ppm(0.01, 4.0, 270.0, SOURCE.position, rec, StabilityClass.D,
                                   CoefficientSet.BRIGGS_RURAL, 290.0, P)[0])


def test_same_seed_same_series() -> None:
    """The truth model is deterministic for a given seed."""
    a = _run(TruthConfig(), seed=5)
    b = _run(TruthConfig(), seed=5)
    assert np.array_equal(a.ppm, b.ppm)
    assert a.times_s.shape == (360,)


def test_quiet_briggs_config_equals_the_plume_model() -> None:
    """With no randomness and the inversion's coefficients, truth = background + plume model."""
    s = _run(TruthConfig(coeff=CoefficientSet.BRIGGS_RURAL, **QUIET))
    assert np.allclose(s.ppm[:, 0], 1.95 + _expected_excess())
    assert set(s.stability) == {StabilityClass.D}


def test_truth_physics_differs_from_inversion_physics() -> None:
    """Martin coefficients alone change the 300 m centreline excess by more than 10 % (~24 %)."""
    s = _run(TruthConfig(coeff=CoefficientSet.PG_MARTIN, **QUIET))
    truth_excess = float(s.ppm[0, 0]) - 1.95
    assert abs(truth_excess - _expected_excess()) / _expected_excess() > 0.10


def test_background_and_noise_statistics() -> None:
    """No sources: mean 1.95 and standard deviation 0.3 ppm (360 samples)."""
    s = _run(TruthConfig(), sources=[], seed=0)
    assert float(s.ppm.mean()) == pytest.approx(1.95, abs=0.05)
    assert float(s.ppm.std()) == pytest.approx(0.3, abs=0.04)


def test_source_window_is_respected() -> None:
    """A source active only in the second half hour adds nothing before it starts."""
    late = TrueSource(Point3(0.0, 0.0, 2.0), 36.0, 1800.0, 1e9)
    s = _run(TruthConfig(coeff=CoefficientSet.BRIGGS_RURAL, **QUIET), sources=[late])
    assert np.allclose(s.ppm[s.times_s < 1800.0, 0], 1.95)
    assert np.all(s.ppm[s.times_s >= 1800.0, 0] > 1.95)


def test_drift_fault_adds_linear_offset() -> None:
    """1 ppm/h drift from t = 0 adds t/3600 ppm to that sensor only."""
    s = _run(TruthConfig(**QUIET), sources=[],
             faults=[SensorFault("S1", 1.0, 0.0)])
    assert np.allclose(s.ppm[:, 0], 1.95 + s.times_s / 3600.0)


def test_wake_dilutes_receptors_behind_an_obstacle() -> None:
    """A receptor 10 m behind a 10 m-high obstacle (inside 3 x height) is diluted by 0.6."""
    near = Sensor("S1", Point3(60.0, 0.0, 2.0), 0.3)
    obstacle = WakeObstacle((50.0, 0.0), 5.0, 10.0)
    base = TruthConfig(coeff=CoefficientSet.BRIGGS_RURAL, meander_sd_deg=0.0, speed_cv=0.0,
                       noise_ppm=0.0, wake_dilution=0.6)
    with_wake = simulate_sensors([SOURCE], [near], OVERCAST_WEST, 10.0, 600.0,
                                 np.random.default_rng(0), P, obstacles=[obstacle], config=base)
    without = simulate_sensors([SOURCE], [near], OVERCAST_WEST, 10.0, 600.0,
                               np.random.default_rng(0), P, config=base)
    assert np.allclose(with_wake.ppm - 1.95, 0.6 * (without.ppm - 1.95))


def test_facility_obstacles() -> None:
    """KS-07 has two buildings and three compressor shelters."""
    obstacles = facility_obstacles(load_facility())
    assert len(obstacles) == 5
    # Spec order: K-201..K-203 shelters (height 6.0, half width 6.0) come before CR-901, MCC-902.
    assert obstacles[0].height_m == 6.0 and obstacles[0].half_width_m == 6.0
    assert obstacles[-1].height_m == 4.0


def test_synthetic_weather_ranges_and_determinism() -> None:
    """Speeds are clipped, nights have no sun, and the generator is deterministic."""
    a = synthetic_hourly_weather(48, 0, np.random.default_rng(3))
    b = synthetic_hourly_weather(48, 0, np.random.default_rng(3))
    assert a == b
    assert len(a) == 48
    assert all(0.3 <= w.wind_speed_m_s <= 15.0 for w in a)
    assert all(w.shortwave_w_m2 == 0.0 for w in a if (w.hour_index % 24) in (0, 1, 2, 3, 22, 23))
    assert all(0.0 <= w.wind_from_deg < 360.0 for w in a)
```

## Steps
- [x] Tests → FAIL → implement (helpers for interpolation, AR(1) series, wake mask; every function ≤ 50 lines) → full checks green (`check_structure.py` confirms `facility/obstacles.py` imports only `engineering` + facility).
- [x] **Docs.** ENGINEERING.md → "Truth model (why the demo is not an inverse crime)": every mismatch ingredient, its parameter and why; the random-draw order; how Phase 3 will feed Open-Meteo weather. SIMULATOR.md → "Obstacles". Work-log; `STATUS.md` (last 2.12, next 2.13).
- [ ] **Commit** `feat(engineering): add truth model for simulator and benchmark`.
