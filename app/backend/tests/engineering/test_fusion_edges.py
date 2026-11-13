"""Edge cases of evidence fusion: bad priors, clipping, ties, non-finite input, boundaries."""

import math

import pytest

from plumetrace.engineering.fusion import (
    EvidenceItem,
    attribute_vent_source,
    fuse,
    header_flow_evidence,
    packing_temperature_lrs,
)

BASE = {"K-201": 80.0, "K-202": 80.0, "K-203": 80.0}


def _item(cid: str, lr: float) -> EvidenceItem:
    return EvidenceItem(candidate_id=cid, likelihood_ratio=lr, source_tag="X", reason="t")


@pytest.mark.parametrize(
    "prior",
    [
        {},
        {"A": 0.0, "B": 0.0},
        {"A": -0.1, "B": 1.1},
        {"A": math.nan, "B": 1.0},
        {"A": math.inf, "B": 1.0},
        {"A": 1e308, "B": 1e308},
    ],
)
def test_fuse_rejects_unusable_prior(prior: dict[str, float]) -> None:
    """Empty, zero, negative, NaN, infinite or overflowing prior mass fails visibly."""
    with pytest.raises(ValueError, match="positive mass"):
        fuse(prior, [])


def test_fuse_renormalises_an_unnormalised_prior() -> None:
    """Prior (1, 3) behaves like (0.25, 0.75); no evidence leaves it unchanged."""
    out = fuse({"A": 1.0, "B": 3.0}, [])
    assert out.probabilities == {"B": 0.75, "A": 0.25}
    assert out.top_id == "B" and out.top_probability == 0.75


def test_zero_prior_stays_zero() -> None:
    """A candidate with prior 0 cannot be revived by evidence."""
    out = fuse({"A": 0.0, "B": 1.0}, [_item("A", 20.0)])
    assert out.probabilities["A"] == 0.0 and out.top_id == "B"
    assert len(out.applied) == 1


def test_clipping_both_ends_and_infinite_lr() -> None:
    """LR 0.001 is raised to 0.05; LR inf is cut to 20."""
    low = fuse({"A": 0.5, "B": 0.5}, [_item("A", 0.001)])
    assert low.probabilities["A"] == pytest.approx(0.05 / 1.05)
    high = fuse({"A": 0.5, "B": 0.5}, [_item("A", math.inf)])
    assert high.probabilities["A"] == pytest.approx(20.0 / 21.0)


@pytest.mark.parametrize("lr", [0.0, -1.0, math.nan])
def test_evidence_item_rejects_nonpositive_or_nan_lr(lr: float) -> None:
    """Likelihood ratios must be strictly positive numbers."""
    with pytest.raises(ValueError):
        _item("A", lr)


def test_evidence_multiplies_in_input_order() -> None:
    """Two items on one candidate multiply: 2 x 3 = 6 -> A = 6/7 with an even prior."""
    items = [_item("A", 2.0), _item("Z", 9.0), _item("A", 3.0)]
    out = fuse({"A": 0.5, "B": 0.5}, items)
    assert out.probabilities["A"] == pytest.approx(6.0 / 7.0)
    assert [i.likelihood_ratio for i in out.applied] == [2.0, 3.0]


def test_ties_are_ordered_by_id() -> None:
    """Equal probabilities are listed by id and the top is the first id."""
    out = fuse({"B": 0.5, "A": 0.5}, [])
    assert list(out.probabilities) == ["A", "B"] and out.top_id == "A"


def test_underflow_to_zero_mass_fails_visibly() -> None:
    """A subnormal prior times an LR below 1 loses all mass: error, not NaN."""
    with pytest.raises(ValueError, match="positive mass"):
        fuse({"A": 5e-324}, [_item("A", 0.05)])


def test_header_flow_boundaries_are_strict_and_inclusive() -> None:
    """Increase of exactly 2 sigma is not significant; |gap| of exactly 2 sigma is consistent."""
    assert header_flow_evidence(2.0, 1.0, 2.0, "V").likelihood_ratio == 1.0
    assert header_flow_evidence(4.0, 1.0, 2.0, "V").likelihood_ratio == 4.0


def test_header_flow_decrease_is_no_information() -> None:
    """A header flow drop is never evidence for the vent."""
    assert header_flow_evidence(-10.0, 1.0, 9.0, "V").likelihood_ratio == 1.0


def test_header_flow_reason_states_numbers_and_outcome() -> None:
    """The reason carries the three numbers and the outcome; the tag can be overridden."""
    item = header_flow_evidence(10.0, 1.0, 9.0, "V", source_tag="FT-9")
    assert item.source_tag == "FT-9"
    for text in ("10.0", "1.0", "9.0", "consistent"):
        assert text in item.reason
    assert "not significant" in header_flow_evidence(0.5, 1.0, 9.0, "V").reason
    assert "inconsistent" in header_flow_evidence(10.0, 1.0, 30.0, "V").reason


@pytest.mark.parametrize(
    "args",
    [
        (math.nan, 1.0, 9.0),
        (10.0, math.inf, 9.0),
        (10.0, 0.0, 9.0),
        (10.0, -1.0, 9.0),
        (10.0, 1.0, -1.0),
        (10.0, 1.0, math.nan),
        (math.inf, 1.0, 9.0),
    ],
)
def test_header_flow_rejects_nonphysical_input(args: tuple[float, float, float]) -> None:
    """NaN, infinite, zero or negative uncertainty and a negative plume rate raise."""
    with pytest.raises(ValueError):
        header_flow_evidence(*args, "V")


def test_common_mode_temperature_rise_gives_no_information() -> None:
    """All units +5 C: a is the same for every unit, so every LR is 1."""
    lrs = packing_temperature_lrs({u: 85.0 for u in BASE}, BASE)
    assert all(v == pytest.approx(1.0) for v in lrs.values())


def test_cold_unit_is_clipped_low_and_order_kept() -> None:
    """One unit 20 C cold gives LR 0.05 (the floor); key order follows the input."""
    temps = {"K-203": 80.0, "K-201": 60.0, "K-202": 80.0}
    lrs = packing_temperature_lrs(temps, BASE)
    assert list(lrs) == ["K-203", "K-201", "K-202"]
    assert lrs["K-201"] == 0.05


def test_extreme_temperature_does_not_overflow() -> None:
    """A huge reading is clipped to 20 instead of raising OverflowError."""
    lrs = packing_temperature_lrs({"K-201": 1e9, "K-202": 80.0}, BASE)
    assert lrs["K-201"] == 20.0


def test_two_units_are_enough() -> None:
    """Two units work: the other unit's mean is the single other anomaly."""
    lrs = packing_temperature_lrs({"A": 84.0, "B": 80.0}, {"A": 80.0, "B": 80.0})
    assert lrs["A"] == pytest.approx(math.exp(2.0)) and lrs["B"] == pytest.approx(math.exp(-2.0))


@pytest.mark.parametrize(
    ("temps", "baseline", "kw"),
    [
        ({}, {}, {}),
        ({"K-201": 80.0, "K-202": 80.0}, {"K-201": 80.0}, {}),
        ({"K-201": 80.0, "K-202": math.nan}, BASE, {}),
        ({"K-201": 80.0, "K-202": 80.0}, {"K-201": 80.0, "K-202": math.inf}, {}),
        ({"K-201": 80.0, "K-202": 80.0}, BASE, {"sigma_c": 0.0}),
        ({"K-201": 80.0, "K-202": 80.0}, BASE, {"sigma_c": math.nan}),
        ({"K-201": 80.0, "K-202": 80.0}, BASE, {"k": -1.0}),
        ({"K-201": 80.0, "K-202": 80.0}, BASE, {"k": math.inf}),
    ],
)
def test_packing_rejects_bad_input(
    temps: dict[str, float], baseline: dict[str, float], kw: dict[str, float]
) -> None:
    """Too few units, a missing baseline, non-finite values and bad sigma or k raise."""
    with pytest.raises(ValueError):
        packing_temperature_lrs(temps, baseline, **kw)


def test_attribute_keeps_order_and_total() -> None:
    """Shares follow the input order and add up to the vent probability."""
    shares = attribute_vent_source(0.6, {"B": 1.0, "A": 3.0})
    assert list(shares) == ["B", "A"]
    assert shares["A"] == pytest.approx(0.45) and sum(shares.values()) == pytest.approx(0.6)


def test_attribute_zero_probability_and_zero_lr() -> None:
    """Vent probability 0 gives all zeros; an LR of 0 gives that unit no share."""
    assert attribute_vent_source(0.0, {"A": 1.0, "B": 2.0}) == {"A": 0.0, "B": 0.0}
    assert attribute_vent_source(1.0, {"A": 0.0, "B": 2.0}) == {"A": 0.0, "B": 1.0}


@pytest.mark.parametrize(
    ("vent", "lrs"),
    [
        (1.1, {"A": 1.0}),
        (-0.1, {"A": 1.0}),
        (math.nan, {"A": 1.0}),
        (0.5, {}),
        (0.5, {"A": 0.0, "B": 0.0}),
        (0.5, {"A": -1.0, "B": 2.0}),
        (0.5, {"A": math.nan, "B": 2.0}),
        (0.5, {"A": math.inf, "B": 2.0}),
    ],
)
def test_attribute_rejects_bad_input(vent: float, lrs: dict[str, float]) -> None:
    """Probability outside 0..1, no units, no weight or a bad LR raise."""
    with pytest.raises(ValueError):
        attribute_vent_source(vent, lrs)
