# Phase 3 · Task 3 — Non-methane instruments

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

**Why:** triage and fusion need process evidence: the vent header flow FT-250, the packing-case
temperatures TT-201P/202P/203P, flare flow and pilot, tank pressures and throughput (design §4).

## Files
Create `app/backend/plumetrace/simulator/instruments.py`, `app/backend/tests/simulator/test_instruments.py`.

## Interface
```python
@dataclass(frozen=True)
class InstrumentBaseline:
    tag: str
    unit: str
    mean: float
    noise_sd: float

BASELINES: Final[Mapping[str, InstrumentBaseline]] = MappingProxyType({
    "FT-250":  InstrumentBaseline("FT-250", "kg/h", 0.9, 0.25),      # packing vent header, whole gas
    "TT-201P": InstrumentBaseline("TT-201P", "degC", 80.0, 0.5),
    "TT-202P": InstrumentBaseline("TT-202P", "degC", 80.0, 0.5),
    "TT-203P": InstrumentBaseline("TT-203P", "degC", 80.0, 0.5),
    "FT-601":  InstrumentBaseline("FT-601", "kg/h", 5.0, 0.5),       # flare header flow, whole gas
    "TE-601":  InstrumentBaseline("TE-601", "degC", 600.0, 10.0),    # pilot thermocouple
    "PT-401":  InstrumentBaseline("PT-401", "kPag", 2.0, 0.05),
    "PT-402":  InstrumentBaseline("PT-402", "kPag", 2.0, 0.05),
    "FT-701":  InstrumentBaseline("FT-701", "Sm3/h", 41667.0, 200.0),
})

@dataclass(frozen=True)
class InstrumentEffect:
    tag: str
    kind: Literal["offset", "set"]   # offset: add `value`; set: replace with `value` (noise still added)
    value: float
    start_s: float
    end_s: float = float("inf")
    ramp_s: float = 0.0              # linear ramp from 0 to full effect over ramp_s after start_s

def simulate_instruments(times_s: npt.NDArray[np.float64], effects: Sequence[InstrumentEffect],
                         rng: np.random.Generator) -> dict[str, npt.NDArray[np.float64]]
```
Behaviour: for every tag in `BASELINES` (in mapping order) draw `rng.normal(0, noise_sd, len(times_s))`
(always, so sequences stay aligned); start from `mean`; for each effect on that tag compute the
weight `w(t) = 0` before `start_s` or at/after `end_s`, else `min(1, (t − start_s)/ramp_s)` (`1` when
`ramp_s == 0`); `offset`: `value += w·effect.value`; `set`: `value = (1 − w)·value + w·effect.value`.
Effects apply in the given order; noise is added last. An effect on an unknown tag raises
`KeyError(f"unknown instrument {tag}")`.

Helper used by scenarios:
- `def packing_leak_effects(unit_tag: str, ch4_rate_kg_h: float, ch4_mass_fraction: float, start_s: float, ramp_s: float = 1800.0) -> list[InstrumentEffect]` — FT-250 offset `ch4_rate_kg_h / ch4_mass_fraction` (whole gas) and `TT-{n}P` offset `+6.0 °C` for `unit_tag = "K-20n"`, both ramped.

## Tests (full code) — `app/backend/tests/simulator/test_instruments.py`
```python
"""Tests for the instrument simulator."""

import numpy as np
import pytest

from plumetrace.simulator.instruments import (
    BASELINES,
    InstrumentEffect,
    packing_leak_effects,
    simulate_instruments,
)

T = np.arange(0.0, 7200.0, 10.0)


def test_baselines_and_noise() -> None:
    """Every instrument is produced at its baseline mean with its noise level."""
    out = simulate_instruments(T, [], np.random.default_rng(0))
    assert set(out) == set(BASELINES)
    for tag, b in BASELINES.items():
        assert float(out[tag].mean()) == pytest.approx(b.mean, abs=4 * b.noise_sd / np.sqrt(len(T)))
        assert float(out[tag].std()) == pytest.approx(b.noise_sd, rel=0.15)


def test_ramped_offset() -> None:
    """An offset ramps linearly over ramp_s and then holds."""
    eff = [InstrumentEffect("TT-202P", "offset", 6.0, start_s=1000.0, ramp_s=1000.0)]
    clean = simulate_instruments(T, [], np.random.default_rng(1))["TT-202P"]
    out = simulate_instruments(T, eff, np.random.default_rng(1))["TT-202P"]
    delta = out - clean
    assert delta[T < 1000.0].max() == 0.0
    assert delta[T == 1500.0][0] == pytest.approx(3.0)
    assert np.allclose(delta[T >= 2000.0], 6.0)


def test_set_effect_replaces_value_inside_window() -> None:
    """A 'set' effect replaces the mean (pilot out -> ambient) only inside its window."""
    eff = [InstrumentEffect("TE-601", "set", 30.0, start_s=3600.0, end_s=5400.0)]
    out = simulate_instruments(T, eff, np.random.default_rng(2))["TE-601"]
    assert float(out[(T >= 3600.0) & (T < 5400.0)].mean()) == pytest.approx(30.0, abs=2.0)
    assert float(out[T < 3600.0].mean()) == pytest.approx(600.0, abs=2.0)


def test_packing_leak_effects() -> None:
    """15 kg/h CH4 at w = 0.8623 -> FT-250 +17.395 kg/h whole gas; TT-202P +6 C."""
    effs = packing_leak_effects("K-202", 15.0, 0.8623, start_s=7200.0)
    by_tag = {e.tag: e for e in effs}
    assert set(by_tag) == {"FT-250", "TT-202P"}
    assert by_tag["FT-250"].value == pytest.approx(17.395, abs=1e-3)
    assert by_tag["TT-202P"].value == 6.0 and by_tag["TT-202P"].ramp_s == 1800.0


def test_unknown_tag_rejected() -> None:
    """Effects must target a known instrument."""
    with pytest.raises(KeyError, match="XX-1"):
        simulate_instruments(T, [InstrumentEffect("XX-1", "offset", 1.0, 0.0)],
                             np.random.default_rng(0))
```

## Steps
- [ ] Tests → FAIL → implement → full checks green.
- [ ] **Docs.** SIMULATOR.md → "Instruments": table of every tag (meaning, unit, baseline, noise), effect model, the packing-leak signature and why (header flow in whole gas; hot packing). Work-log; `STATUS.md` (last 3.3, next 3.4).
- [ ] **Commit** `feat(simulator): add non-methane instrument simulator`.
