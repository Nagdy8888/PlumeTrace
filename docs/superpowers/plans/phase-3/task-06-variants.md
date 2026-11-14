# Phase 3 · Task 6 — Scenario variants (families for the agent evaluation)

**Skills:** `plan-execution`, `agentic-council:oracle-ai-evaluation`, `project-documentation`.

**Why:** design §6 "Agent evaluation": ~20 randomised variants per scenario (weather window, leak
rate, timing, distractor log entries, noise) so the evaluation is statistically meaningful.

## Files
Create `app/backend/plumetrace/simulator/variants.py`, `app/backend/tests/simulator/test_variants.py`.

## Interface
- `VARIANTS_PER_SCENARIO: Final = 20`; `VARIANT_SEED: Final = 20261120`; `RATE_SCALE_RANGE: Final = (0.5, 2.0)`; `TIME_SHIFT_RANGE_S: Final = (-1800.0, 1800.0)`; `SNAPSHOT_HOURS: Final = 168`
- `DISTRACTOR_LOG: Final[tuple[LogEntry, ...]]` — exactly these six entries (all with `t_s=0.0`; the generator assigns times):
  1. `("shift_note", None, "Radio check with the dispatch centre completed.")`
  2. `("maintenance", "E-232", "Fin-fan E-232 belt tension checked; no action needed.")`
  3. `("gauging", "TK-401", "TK-401 gauged; hatch closed and latched.")`
  4. `("calibration", "AT-102", "AT-102 bump test passed.")`
  5. `("shift_note", None, "Contractor vehicle entered the site for scaffolding inspection.")`
  6. `("maintenance", "FG-501", "Fuel gas filter differential pressure logged at 0.3 bar.")`
- `def generate_variants(base: ScenarioDefinition, n: int = VARIANTS_PER_SCENARIO, seed: int = VARIANT_SEED) -> list[ScenarioDefinition]` — `rng = np.random.default_rng([seed, <stable hash of base.id>])` where the hash is `int.from_bytes(hashlib.sha256(base.id.encode()).digest()[:4], "big")`. For `i in range(n)`, draws in this order:
  1. `offset = int(rng.integers(0, SNAPSHOT_HOURS - base.duration_h - 1 + 1))`
  2. `scale = exp(rng.uniform(ln 0.5, ln 2.0))`
  3. `shift = rng.uniform(-1800, 1800)`
  4. `k = int(rng.integers(0, 3))` distractors chosen with `rng.choice(6, size=k, replace=False)`, each placed at `t_s = rng.uniform(0, duration_h·3600)`
  5. `variant_seed = int(rng.integers(2**31))`

  Then build the variant with `model_copy(update=...)`: `weather_offset_h=offset`, `seed=variant_seed`, `variant_index=i`; every source `rate_kg_h × scale`, `start_s + shift`, `end_s + shift` (clamped to ≥ 0; infinite stays infinite); every instrument effect: `start_s + shift` (and `end_s + shift`), and FT-250 `offset` values × `scale`; every fault `start_s + shift` (clamped ≥ 0); every `permit` log entry `t_s + shift` (clamped to `[0, duration_h·3600]`); other base log entries unchanged; distractors added; log re-sorted by `t_s`; expected `rate_min_kg_h`/`rate_max_kg_h` × `scale` when present.

## Tests (full code) — `app/backend/tests/simulator/test_variants.py`
```python
"""Tests for scenario variant generation."""

import pytest

from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.variants import generate_variants


def test_twenty_deterministic_variants() -> None:
    """Same base and seed -> the same 20 variants, indexed 0..19, base unchanged."""
    base = get_scenario("s1_rod_packing")
    a, b = generate_variants(base), generate_variants(base)
    assert a == b
    assert [v.variant_index for v in a] == list(range(20))
    assert all(v.id == base.id for v in a)
    assert get_scenario("s1_rod_packing") == base


def test_weather_window_fits_the_snapshot() -> None:
    """Every variant's weather window lies inside the 168 h snapshot."""
    for v in generate_variants(get_scenario("s5_sensor_drift")):
        assert 0 <= v.weather_offset_h <= 168 - v.duration_h - 1


def test_rate_and_header_flow_scale_together() -> None:
    """The leak rate and the FT-250 signature scale by the same factor."""
    base = get_scenario("s1_rod_packing")
    base_ft = next(e for e in base.instrument_effects if e.tag == "FT-250").value
    for v in generate_variants(base):
        scale = v.sources[0].rate_kg_h / base.sources[0].rate_kg_h
        assert 0.5 <= scale <= 2.0
        ft = next(e for e in v.instrument_effects if e.tag == "FT-250").value
        assert ft == pytest.approx(base_ft * scale)
        assert v.expected.rate_min_kg_h == pytest.approx(7.5 * scale)


def test_permit_moves_with_the_blowdown() -> None:
    """In S4 variants the permit keeps its 600 s lead over the blowdown (unless clamped at 0)."""
    for v in generate_variants(get_scenario("s4_planned_blowdown")):
        permit = next(e for e in v.log if e.kind == "permit")
        start = v.sources[0].start_s
        assert permit.t_s == pytest.approx(max(0.0, start - 600.0))


def test_logs_stay_sorted_with_distractors() -> None:
    """Distractors are added and the log stays sorted."""
    for v in generate_variants(get_scenario("s1_rod_packing")):
        times = [e.t_s for e in v.log]
        assert times == sorted(times)
        assert len(v.log) >= 3
```

## Steps
- [x] Tests → FAIL → implement → full checks green.
- [x] **Docs.** SIMULATOR.md → "Variants": what varies and why, the draw order, the distractor list, how variants feed the evaluation (Phase 5). Work-log; `STATUS.md` (last 3.6, next 3.7).
- [ ] **Commit** `feat(simulator): add scenario variant generator`.
