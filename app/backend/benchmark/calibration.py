"""Pre-registered calibration metrics and the adoption rule of the improvement round.

The published benchmark scores accuracy; these metrics ask whether the stated probabilities and
rate intervals can be trusted. Definitions, fixed before any fresh run (2026-11-14):

- ``named``: leak cases that are conclusive with a top id other than ``NONE``.
- ``confident_wrong_rate``: named cases wrong at k = 1 with ``top_probability >= 0.95``, over named.
- ``missed_leak_rate``: leak cases that are conclusive with top ``NONE``, over all leak cases.
- ``good``: named cases correct at k = 1 that report a rate.
- ``rate_in_interval``: good cases with ``p05 <= true rate <= p95``, over good.
- ``grid_edge_share``: good cases with ``rate_at_grid_edge``, over good.
- ``median_rate_ratio``: median of ``rate / true rate`` over good.
- ``reliability``: n and top-1 accuracy of the named cases per ``top_probability`` bin.

Every rate is 0.0 on an empty denominator; the median is None. Correctness is ``is_correct``.
"""

import math
from collections.abc import Mapping
from typing import Final

import numpy as np
from pydantic import BaseModel, ConfigDict

from benchmark.metrics import BenchmarkSummary, is_correct, summarize
from benchmark.runner import CaseResult
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.inversion import NO_SOURCE_ID

CONFIDENT_P: Final = 0.95

# Reliability bins on top_probability: (label, lower edge inclusive, upper edge exclusive). The
# last bin has no upper edge, so a probability a rounding step above 1.0 still lands in it.
RELIABILITY_BINS: Final = (
    ("[0.6, 0.8)", 0.6, 0.8),
    ("[0.8, 0.95)", 0.8, CONFIDENT_P),
    ("[0.95, 1.0]", CONFIDENT_P, math.inf),
)


class Calibration(BaseModel):
    """The calibration metrics of one method on one case set.

    Attributes:
        n_named: Number of named cases (conclusive leak cases whose top id is not ``NONE``).
        n_good: Number of good cases (named, right at k = 1, with a rate).
        confident_wrong_rate: Named cases wrong at k = 1 with p >= 0.95, over named.
        missed_leak_rate: Conclusive ``NONE`` on a leak case, over all leak cases.
        rate_in_interval: Good cases whose 90 % interval holds the true rate, over good.
        grid_edge_share: Good cases at the rate-grid edge, over good.
        median_rate_ratio: Median of ``rate / true rate`` over good; None when there are none.
        reliability: Per bin of ``RELIABILITY_BINS``, ``{"n", "accuracy"}`` over the named cases.
    """

    model_config = ConfigDict(frozen=True)

    n_named: int
    n_good: int
    confident_wrong_rate: float
    missed_leak_rate: float
    rate_in_interval: float
    grid_edge_share: float
    median_rate_ratio: float | None
    reliability: dict[str, dict[str, float]]


class MethodMetrics(BaseModel):
    """The metric bundle of one method: the published summary plus the calibration metrics.

    Attributes:
        summary: ``summarize`` output (accuracy, rate error, inconclusive and false-call rates).
        calibration: The calibration metrics.
    """

    model_config = ConfigDict(frozen=True)

    summary: BenchmarkSummary
    calibration: Calibration

    @property
    def top1_all(self) -> float:
        """Top-1 accuracy over all leak cases."""
        return self.summary.top1_all

    @property
    def false_call_rate(self) -> float:
        """Share of no-leak cases that are conclusive with a source named."""
        return self.summary.false_call_rate

    @property
    def confident_wrong_rate(self) -> float:
        """Share of named cases that are wrong with probability 0.95 or more."""
        return self.calibration.confident_wrong_rate


def _ratio(count: int, total: int) -> float:
    """``count / total``, or 0.0 when ``total`` is 0."""
    return count / total if total else 0.0


def _reliability(
    named: list[CaseResult], positions: Mapping[str, Point3]
) -> dict[str, dict[str, float]]:
    """Count and top-1 accuracy of the named cases in each probability bin."""
    out: dict[str, dict[str, float]] = {}
    for label, lo, hi in RELIABILITY_BINS:
        group = [r for r in named if lo <= r.result.top_probability < hi]
        right = sum(is_correct(r, 1, positions) for r in group)
        out[label] = {"n": float(len(group)), "accuracy": _ratio(right, len(group))}
    return out


def calibration_metrics(results: list[CaseResult], positions: Mapping[str, Point3]) -> Calibration:
    """Compute the calibration metrics from case results (leak and no-leak).

    Args:
        results: All case results; no-leak cases are ignored.
        positions: Candidate positions by id.

    Returns:
        The metrics as defined in the module docstring.
    """
    leaks = [r for r in results if r.case.source is not None]
    named = [r for r in leaks if not r.result.inconclusive and r.result.top_id != NO_SOURCE_ID]
    right = [r for r in named if is_correct(r, 1, positions)]
    wrong_sure = [
        r
        for r in named
        if r.result.top_probability >= CONFIDENT_P and not is_correct(r, 1, positions)
    ]
    missed = [r for r in leaks if not r.result.inconclusive and r.result.top_id == NO_SOURCE_ID]
    good = [r for r in right if r.result.rate_kg_h is not None and r.true_rate_kg_h]
    inside = [
        r
        for r in good
        if r.result.rate_p05_kg_h is not None
        and r.result.rate_p95_kg_h is not None
        and r.result.rate_p05_kg_h <= (r.true_rate_kg_h or 0.0) <= r.result.rate_p95_kg_h
    ]
    ratios = [(r.result.rate_kg_h or 0.0) / (r.true_rate_kg_h or 1.0) for r in good]
    return Calibration(
        n_named=len(named),
        n_good=len(good),
        confident_wrong_rate=_ratio(len(wrong_sure), len(named)),
        missed_leak_rate=_ratio(len(missed), len(leaks)),
        rate_in_interval=_ratio(len(inside), len(good)),
        grid_edge_share=_ratio(sum(r.result.rate_at_grid_edge for r in good), len(good)),
        median_rate_ratio=float(np.median(ratios)) if ratios else None,
        reliability=_reliability(named, positions),
    )


def method_metrics(results: list[CaseResult], positions: Mapping[str, Point3]) -> MethodMetrics:
    """The published summary and the calibration metrics of one method.

    Args:
        results: All case results of the method.
        positions: Candidate positions by id.

    Returns:
        The bundle; the summary is exactly ``summarize(results, positions)``.
    """
    return MethodMetrics(
        summary=summarize(results, positions),
        calibration=calibration_metrics(results, positions),
    )


def adopt_meander(t8: MethodMetrics, m: MethodMetrics) -> bool:
    """The pre-registered adoption rule: adopt the meander-aware method or keep Task 8.

    Adopt if and only if the meander method's top-1 accuracy (all leak cases) is at least the
    Task 8 one, its confident-wrong rate is at most the Task 8 one and its false-call rate is
    at most the Task 8 one. Ties adopt.

    Args:
        t8: Metrics of the Task 8 inversion on the fresh case set.
        m: Metrics of the meander-aware inversion on the same cases.

    Returns:
        True when the meander-aware method is adopted for the app.
    """
    return (
        m.top1_all >= t8.top1_all
        and m.confident_wrong_rate <= t8.confident_wrong_rate
        and m.false_call_rate <= t8.false_call_rate
    )
