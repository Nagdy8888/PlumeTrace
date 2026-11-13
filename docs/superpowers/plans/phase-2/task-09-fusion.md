# Phase 2 · Task 9 — Evidence fusion and vent-header attribution

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`.

**Why:** in S1 the plume inversion finds the common vent stack `VS-250.tip`; deciding *which*
compressor's packing is leaking needs process evidence (header flow FT-250, packing temperatures
TT-201P/202P/203P). That decision is a coded, tested calculation — never the LLM's judgement.

## Files
Create `app/backend/plumetrace/engineering/fusion.py`, `app/backend/tests/engineering/test_fusion.py`.

## Interface
- Constants (`Final[float]`): `LR_MIN = 0.05`, `LR_MAX = 20.0`, `PACKING_SIGMA_C = 2.0`, `PACKING_K = 1.0`, `HEADER_CONSISTENT_LR = 4.0`, `HEADER_SIGNIFICANCE_SIGMA = 2.0`.
- `class EvidenceItem(BaseModel)` (frozen): `candidate_id: str`, `likelihood_ratio: float` (`Field(gt=0)`), `source_tag: str`, `reason: str`.
- `class FusionResult(BaseModel)`: `probabilities: dict[str, float]` (keys in descending probability order, ties by id), `top_id: str`, `top_probability: float`, `applied: list[EvidenceItem]`.
- `def fuse(prior: dict[str, float], evidence: list[EvidenceItem]) -> FusionResult` — posterior ∝ prior × Π clip(LR, LR_MIN, LR_MAX) over evidence whose `candidate_id` is in the prior; renormalise to sum 1; `applied` lists only those items, in input order. Prior values must be ≥ 0 and sum > 0 (else `ValueError("prior must have positive mass")`).
- `def header_flow_evidence(header_flow_increase_kg_h: float, header_uncertainty_kg_h: float, plume_rate_kg_h: float, vent_candidate_id: str, source_tag: str = "FT-250") -> EvidenceItem` — `significant = increase > HEADER_SIGNIFICANCE_SIGMA × uncertainty`; `consistent = |increase − plume_rate| ≤ 2 × uncertainty`; LR = `HEADER_CONSISTENT_LR` if both, else `1.0`; `reason` states the numbers and the outcome.
- `def packing_temperature_lrs(temps_c: dict[str, float], baseline_c: dict[str, float], sigma_c: float = PACKING_SIGMA_C, k: float = PACKING_K) -> dict[str, float]` — keys are unit tags (e.g. `"K-201"`); `aⱼ = (Tⱼ − baselineⱼ)/sigma_c`; `LRⱼ = clip(exp(k·(aⱼ − mean(a of the other units))), LR_MIN, LR_MAX)`. Requires ≥ 2 units (else `ValueError`).
- `def attribute_vent_source(vent_probability: float, unit_lrs: dict[str, float]) -> dict[str, float]` — `P(unit) = vent_probability · LR / Σ LR`, same key order as `unit_lrs`.

## Tests (full code) — `app/backend/tests/engineering/test_fusion.py`
```python
"""Tests for evidence fusion and vent-header attribution (hand calculations in docstrings)."""

import math

import pytest

from plumetrace.engineering.fusion import (
    EvidenceItem,
    attribute_vent_source,
    fuse,
    header_flow_evidence,
    packing_temperature_lrs,
)

UNITS = ("K-201", "K-202", "K-203")
BASE = {u: 80.0 for u in UNITS}


def test_equal_packing_temperatures_split_evenly() -> None:
    """No temperature anomaly -> LR = 1 for each unit -> vent probability split in three."""
    lrs = packing_temperature_lrs(dict(BASE), BASE)
    shares = attribute_vent_source(0.9, lrs)
    assert all(v == pytest.approx(0.3) for v in shares.values())


def test_hot_packing_takes_most_of_the_vent_probability() -> None:
    """TT-202P +6 C: a = 3 -> LR = clip(e^3) = 20; others e^-1.5 = 0.2231 -> share 0.97817."""
    lrs = packing_temperature_lrs({"K-201": 80.0, "K-202": 86.0, "K-203": 80.0}, BASE)
    assert lrs["K-202"] == 20.0
    assert lrs["K-201"] == pytest.approx(math.exp(-1.5))
    shares = attribute_vent_source(1.0, lrs)
    assert shares["K-202"] == pytest.approx(0.97817, abs=1e-4)
    assert sum(shares.values()) == pytest.approx(1.0)


def test_fuse_renormalises_and_clips() -> None:
    """Posterior sums to 1; an LR of 1000 is clipped to 20."""
    prior = {"A": 0.5, "B": 0.5}
    out = fuse(prior, [EvidenceItem(candidate_id="A", likelihood_ratio=1000.0,
                                    source_tag="X", reason="test")])
    assert out.probabilities["A"] == pytest.approx(20.0 / 21.0)
    assert sum(out.probabilities.values()) == pytest.approx(1.0, abs=1e-9)
    assert out.top_id == "A"
    assert list(out.probabilities) == ["A", "B"]


def test_evidence_for_unknown_candidate_is_ignored() -> None:
    """Evidence about an id not in the prior changes nothing and is not listed as applied."""
    prior = {"A": 0.25, "B": 0.75}
    item = EvidenceItem(candidate_id="Z", likelihood_ratio=5.0, source_tag="X", reason="t")
    out = fuse(prior, [item])
    assert out.probabilities == {"B": 0.75, "A": 0.25}
    assert out.applied == []


def test_header_flow_consistent_and_significant() -> None:
    """+10 +/- 1 kg/h on FT-250 vs a 9 kg/h plume -> significant and consistent -> LR 4."""
    item = header_flow_evidence(10.0, 1.0, 9.0, "VS-250.tip")
    assert item.likelihood_ratio == 4.0
    assert item.candidate_id == "VS-250.tip" and item.source_tag == "FT-250"


def test_header_flow_not_significant() -> None:
    """+0.5 +/- 1 kg/h is within noise -> no information (LR 1)."""
    assert header_flow_evidence(0.5, 1.0, 9.0, "VS-250.tip").likelihood_ratio == 1.0


def test_header_flow_inconsistent_with_plume() -> None:
    """+10 +/- 1 kg/h vs a 30 kg/h plume is significant but inconsistent -> LR 1."""
    assert header_flow_evidence(10.0, 1.0, 30.0, "VS-250.tip").likelihood_ratio == 1.0


def test_invalid_inputs() -> None:
    """Empty prior mass and single-unit attribution are rejected."""
    with pytest.raises(ValueError, match="positive mass"):
        fuse({"A": 0.0}, [])
    with pytest.raises(ValueError):
        packing_temperature_lrs({"K-201": 80.0}, {"K-201": 80.0})
```

## Steps
- [ ] Test → FAIL → implement → full checks green.
- [ ] **Docs.** ENGINEERING.md → "Evidence fusion": why coded, Bayes update with likelihood ratios, clipping, each evidence rule with constants, the S1 walk-through (VS-250 → K-202 with the numbers from the test). Work-log; `STATUS.md` (last 2.9, next 2.10).
- [ ] **Commit** `feat(engineering): add evidence fusion and vent attribution`.
