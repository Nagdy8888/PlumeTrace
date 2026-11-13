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
    out = fuse(
        prior,
        [EvidenceItem(candidate_id="A", likelihood_ratio=1000.0, source_tag="X", reason="test")],
    )
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
