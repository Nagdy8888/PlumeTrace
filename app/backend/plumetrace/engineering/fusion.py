"""Evidence fusion and vent-header attribution.

Pure Python, no I/O. A Bayes update with clipped likelihood ratios combines the plume inversion
posterior with process evidence, and a second step shares the vent-stack probability among the
compressor units that feed the common vent header. The LLM never makes this decision.
"""

import math
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

# Task 9 values (project choices, not published constants).
LR_MIN: Final[float] = 0.05
LR_MAX: Final[float] = 20.0
PACKING_SIGMA_C: Final[float] = 2.0
PACKING_K: Final[float] = 1.0
HEADER_CONSISTENT_LR: Final[float] = 4.0
HEADER_SIGNIFICANCE_SIGMA: Final[float] = 2.0

# exp() overflows above about 709; any exponent past this is clipped to LR_MAX anyway.
_MAX_EXPONENT: Final[float] = 700.0


class EvidenceItem(BaseModel):
    """One piece of process evidence about one candidate.

    Attributes:
        candidate_id: Candidate the evidence is about.
        likelihood_ratio: How much more likely the evidence is if the candidate leaks than
            if it does not; above 1 supports the candidate. Must be above zero.
        source_tag: Instrument or rule that produced the evidence.
        reason: Plain-language statement of the numbers and the outcome.
    """

    model_config = ConfigDict(frozen=True)

    candidate_id: str
    likelihood_ratio: float = Field(gt=0)
    source_tag: str
    reason: str


class FusionResult(BaseModel):
    """Posterior after fusing the evidence.

    Attributes:
        probabilities: Posterior per candidate, keys in descending probability, ties by id.
        top_id: Candidate with the highest probability.
        top_probability: Its probability.
        applied: The evidence items that were used, in input order.
    """

    probabilities: dict[str, float]
    top_id: str
    top_probability: float
    applied: list[EvidenceItem]


def _check_prior(prior: dict[str, float]) -> None:
    """Raise ValueError unless every prior value is finite and non-negative with a positive sum."""
    for candidate_id, value in prior.items():
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"prior must have positive mass (bad value for {candidate_id!r})")
    total = sum(prior.values())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("prior must have positive mass (sum is zero, empty or too large)")


def _clip_lr(likelihood_ratio: float) -> float:
    return min(max(likelihood_ratio, LR_MIN), LR_MAX)


def fuse(prior: dict[str, float], evidence: list[EvidenceItem]) -> FusionResult:
    """Update a prior with likelihood-ratio evidence (naive Bayes) and renormalise.

    The posterior is proportional to the prior times the product of the clipped likelihood
    ratios of the evidence items about that candidate. Items about a candidate that is not in
    the prior are ignored and not listed as applied. Items are treated as independent.

    Args:
        prior: Prior weight per candidate id; need not sum to 1.
        evidence: Evidence items, in the order they were produced.

    Returns:
        The posterior, the top candidate and the items that were applied.

    Raises:
        ValueError: If a prior value is negative or not finite, or the prior (or the weights
            after the update) have no positive, finite total mass.
    """
    _check_prior(prior)
    weights = dict(prior)
    applied = [item for item in evidence if item.candidate_id in prior]
    for item in applied:
        weights[item.candidate_id] *= _clip_lr(item.likelihood_ratio)
    total = sum(weights.values())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("prior must have positive mass (zero or overflow after the update)")
    ordered = sorted(weights, key=lambda cid: (-weights[cid], cid))
    probabilities = {cid: weights[cid] / total for cid in ordered}
    top_id = ordered[0]
    return FusionResult(
        probabilities=probabilities,
        top_id=top_id,
        top_probability=probabilities[top_id],
        applied=applied,
    )


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")


def _check_header_inputs(increase_kg_h: float, uncertainty_kg_h: float, plume_kg_h: float) -> None:
    """Raise ValueError for non-finite header inputs, a bad uncertainty or a negative rate."""
    _require_finite("header_flow_increase_kg_h", increase_kg_h)
    _require_finite("header_uncertainty_kg_h", uncertainty_kg_h)
    _require_finite("plume_rate_kg_h", plume_kg_h)
    if uncertainty_kg_h <= 0.0:
        raise ValueError("header_uncertainty_kg_h must be above zero")
    if plume_kg_h < 0.0:
        raise ValueError("plume_rate_kg_h must not be negative")


def _header_outcome(significant: bool, consistent: bool) -> tuple[str, float]:
    """Return the outcome text and the likelihood ratio of the header rule."""
    if significant and consistent:
        return "significant and consistent with the plume", HEADER_CONSISTENT_LR
    if significant:
        return "significant but inconsistent with the plume", 1.0
    return "not significant", 1.0


def header_flow_evidence(
    header_flow_increase_kg_h: float,
    header_uncertainty_kg_h: float,
    plume_rate_kg_h: float,
    vent_candidate_id: str,
    source_tag: str = "FT-250",
) -> EvidenceItem:
    """Turn a vent-header flow increase into evidence for the vent candidate.

    The increase is significant when it exceeds ``HEADER_SIGNIFICANCE_SIGMA`` times its
    uncertainty, and consistent when it is within two uncertainties of the plume rate. Both
    give ``HEADER_CONSISTENT_LR``; anything else gives 1 (no information, never against).

    Args:
        header_flow_increase_kg_h: Header flow above its baseline, in kg/h (may be negative).
        header_uncertainty_kg_h: One-sigma uncertainty of that increase, in kg/h; above zero.
        plume_rate_kg_h: Emission rate from the plume inversion, in kg/h; not negative.
        vent_candidate_id: Candidate the evidence is about (the vent stack).
        source_tag: Instrument tag of the header flow meter.

    Returns:
        The evidence item with a reason that states the numbers and the outcome.

    Raises:
        ValueError: If an input is not finite, the uncertainty is not above zero or the plume
            rate is negative.
    """
    _check_header_inputs(header_flow_increase_kg_h, header_uncertainty_kg_h, plume_rate_kg_h)
    significant = header_flow_increase_kg_h > HEADER_SIGNIFICANCE_SIGMA * header_uncertainty_kg_h
    gap_kg_h = abs(header_flow_increase_kg_h - plume_rate_kg_h)
    consistent = gap_kg_h <= 2.0 * header_uncertainty_kg_h
    numbers = (
        f"{source_tag} increase {header_flow_increase_kg_h:.2f} +/- "
        f"{header_uncertainty_kg_h:.2f} kg/h, plume rate {plume_rate_kg_h:.2f} kg/h"
    )
    outcome, lr = _header_outcome(significant, consistent)
    return EvidenceItem(
        candidate_id=vent_candidate_id,
        likelihood_ratio=lr,
        source_tag=source_tag,
        reason=f"{numbers}: {outcome}, likelihood ratio {lr:g}",
    )


def _anomalies(
    temps_c: dict[str, float], baseline_c: dict[str, float], sigma_c: float
) -> dict[str, float]:
    """Return the temperature anomaly of each unit in units of ``sigma_c``, after validation."""
    if len(temps_c) < 2:
        raise ValueError("at least two units are required")
    _require_finite("sigma_c", sigma_c)
    if sigma_c <= 0.0:
        raise ValueError("sigma_c must be above zero")
    anomalies: dict[str, float] = {}
    for unit, temp_c in temps_c.items():
        if unit not in baseline_c:
            raise ValueError(f"no baseline temperature for {unit!r}")
        _require_finite(f"temperature of {unit!r}", temp_c)
        _require_finite(f"baseline of {unit!r}", baseline_c[unit])
        anomalies[unit] = (temp_c - baseline_c[unit]) / sigma_c
        _require_finite(f"anomaly of {unit!r}", anomalies[unit])
    return anomalies


def packing_temperature_lrs(
    temps_c: dict[str, float],
    baseline_c: dict[str, float],
    sigma_c: float = PACKING_SIGMA_C,
    k: float = PACKING_K,
) -> dict[str, float]:
    """Likelihood ratio that each unit's packing leaks, from packing temperatures.

    With ``a = (T - baseline) / sigma_c`` the ratio of a unit is
    ``clip(exp(k * (a - mean(a of the other units))), LR_MIN, LR_MAX)``. A rise shared by all
    units (ambient or load) cancels, so only a unit hotter than its peers gets weight.

    Args:
        temps_c: Packing temperature per unit tag, in degC; at least two units.
        baseline_c: Normal packing temperature per unit tag, in degC; covers every unit.
        sigma_c: Temperature scale, in degC; above zero.
        k: Steepness of the ratio; finite and not negative.

    Returns:
        Likelihood ratio per unit tag, in the order of ``temps_c``.

    Raises:
        ValueError: If fewer than two units are given, a baseline is missing, a temperature
            is not finite, ``sigma_c`` is not above zero or ``k`` is negative or not finite.
    """
    _require_finite("k", k)
    if k < 0.0:
        raise ValueError("k must not be negative")
    anomalies = _anomalies(temps_c, baseline_c, sigma_c)
    total = sum(anomalies.values())
    count = len(anomalies)
    lrs: dict[str, float] = {}
    for unit, a in anomalies.items():
        others_mean = (total - a) / (count - 1)
        exponent = k * (a - others_mean)
        _require_finite(f"exponent of {unit!r}", exponent)
        lrs[unit] = _clip_lr(math.exp(min(exponent, _MAX_EXPONENT)))
    return lrs


def attribute_vent_source(vent_probability: float, unit_lrs: dict[str, float]) -> dict[str, float]:
    """Share the vent-stack probability among the units by their likelihood ratios.

    ``P(unit) = vent_probability * LR / sum(LR)``.

    Args:
        vent_probability: Probability that the vent stack is the source, from 0 to 1.
        unit_lrs: Likelihood ratio per unit tag; not negative, with a positive sum.

    Returns:
        Probability per unit tag, in the order of ``unit_lrs``; they add up to
        ``vent_probability``.

    Raises:
        ValueError: If the probability is outside 0 to 1 or not finite, there are no units, an
            LR is negative or not finite, or all LRs are zero.
    """
    if not 0.0 <= vent_probability <= 1.0:
        raise ValueError(f"vent_probability must be between 0 and 1, got {vent_probability}")
    for unit, lr in unit_lrs.items():
        if not math.isfinite(lr) or lr < 0.0:
            raise ValueError(f"likelihood ratio of {unit!r} must be finite and not negative")
    total = sum(unit_lrs.values())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("unit_lrs must have a positive, finite sum")
    return {unit: vent_probability * lr / total for unit, lr in unit_lrs.items()}
