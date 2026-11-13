"""Benchmark metrics: top-k accuracy, rate error, inconclusive and false-call rates."""

import math
from collections.abc import Callable, Mapping
from typing import Final

import numpy as np
from pydantic import BaseModel

from benchmark.cases import OFF_LIST_MAX_M
from benchmark.runner import CaseResult
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.inversion import NO_SOURCE_ID

# Leak-size bins in kg/h: (label, lower edge inclusive, upper edge exclusive).
SIZE_BINS: Final = (("<5", 0.0, 5.0), ("5-20", 5.0, 20.0), ("20-100", 20.0, 100.0 + 1e-9))

_P90: Final = 90


class BenchmarkSummary(BaseModel):
    """Headline numbers of one benchmark run.

    Attributes:
        n_leak: Number of leak cases (on-list and off-list).
        n_no_leak: Number of no-leak cases.
        top1_all: Share of leak cases whose top-1 is correct (inconclusive counts as wrong).
        top1_conclusive: The same, over the conclusive leak cases only.
        top3_all: Share of leak cases with the true source among the top 3 (``NONE`` removed).
        rate_rel_error_median: Median of ``|rate - true| / true`` over conclusive, top-1-correct
            leak cases; None when there are none.
        rate_rel_error_p90: 90th percentile of the same errors; None when there are none.
        inconclusive_rate: Share of leak cases that are inconclusive.
        false_call_rate: Share of no-leak cases that are conclusive with a source named.
        by_stability: Per dominant stability class, ``{"n", "top1_all", "inconclusive_rate"}``
            over the leak cases.
        by_size: The same per true leak-size bin (``SIZE_BINS``).
    """

    n_leak: int
    n_no_leak: int
    top1_all: float
    top1_conclusive: float
    top3_all: float
    rate_rel_error_median: float | None
    rate_rel_error_p90: float | None
    inconclusive_rate: float
    false_call_rate: float
    by_stability: dict[str, dict[str, float]]
    by_size: dict[str, dict[str, float]]


def is_correct(cr: CaseResult, k: int, positions: Mapping[str, Point3]) -> bool:
    """Whether the true source is among the first ``k`` ranked candidates.

    ``NONE`` is removed from the ranking first. An on-list case needs the true candidate id; an
    off-list case needs a candidate within ``OFF_LIST_MAX_M`` horizontally of the true source.
    An inconclusive result is never correct.

    Args:
        cr: A leak case with its result.
        k: How many ranked candidates count (> 0).
        positions: Candidate positions by id.

    Returns:
        True when the result is conclusive and the true source is in the top ``k``.

    Raises:
        ValueError: If the case is a no-leak case.
    """
    case = cr.case
    if case.source is None:
        raise ValueError("is_correct is defined for leak cases only")
    if cr.result.inconclusive:
        return False
    ids = [s.id for s in cr.result.ranked if s.id != NO_SOURCE_ID][:k]
    if case.kind == "on_list":
        return case.true_candidate_id in ids
    src = case.source.position
    return any(
        math.hypot(positions[i].x_m - src.x_m, positions[i].y_m - src.y_m) <= OFF_LIST_MAX_M
        for i in ids
    )


def _share(count: int, total: int) -> float:
    """``count / total``, or 0.0 when ``total`` is 0."""
    return count / total if total else 0.0


def _group(leaks: list[CaseResult], positions: Mapping[str, Point3]) -> dict[str, float]:
    """The per-split numbers: case count, top-1 over all, inconclusive rate."""
    n = len(leaks)
    top1 = sum(is_correct(r, 1, positions) for r in leaks)
    return {
        "n": float(n),
        "top1_all": _share(top1, n),
        "inconclusive_rate": _share(sum(r.result.inconclusive for r in leaks), n),
    }


def _split(
    leaks: list[CaseResult],
    key: Callable[[CaseResult], str],
    labels: list[str],
    positions: Mapping[str, Point3],
) -> dict[str, dict[str, float]]:
    """Group the leak cases by ``key`` and compute the per-split numbers."""
    return {label: _group([r for r in leaks if key(r) == label], positions) for label in labels}


def _size_label(rate_kg_h: float | None) -> str:
    """The ``SIZE_BINS`` label holding a true rate."""
    return next(name for name, lo, hi in SIZE_BINS if lo <= (rate_kg_h or 0.0) < hi)


def _rate_errors(correct: list[CaseResult]) -> list[float]:
    """Relative rate errors of conclusive, top-1-correct leak cases that report a rate."""
    return [
        abs(r.result.rate_kg_h - r.true_rate_kg_h) / r.true_rate_kg_h
        for r in correct
        if r.result.rate_kg_h is not None and r.true_rate_kg_h
    ]


def summarize(results: list[CaseResult], positions: Mapping[str, Point3]) -> BenchmarkSummary:
    """Compute the benchmark metrics; every rate is 0.0 when its denominator is 0.

    Args:
        results: All case results, leak and no-leak.
        positions: Candidate positions by id.

    Returns:
        The summary, including splits by stability class and by leak size.
    """
    leaks = [r for r in results if r.case.source is not None]
    nones = [r for r in results if r.case.source is None]
    conclusive = [r for r in leaks if not r.result.inconclusive]
    top1 = [r for r in leaks if is_correct(r, 1, positions)]
    errors = _rate_errors(top1)
    false_calls = [
        r for r in nones if not r.result.inconclusive and r.result.top_id != NO_SOURCE_ID
    ]
    classes = sorted({r.dominant_stability.value for r in leaks})
    return BenchmarkSummary(
        n_leak=len(leaks),
        n_no_leak=len(nones),
        top1_all=_share(len(top1), len(leaks)),
        top1_conclusive=_share(len(top1), len(conclusive)),
        top3_all=_share(sum(is_correct(r, 3, positions) for r in leaks), len(leaks)),
        rate_rel_error_median=float(np.median(errors)) if errors else None,
        rate_rel_error_p90=float(np.percentile(errors, _P90)) if errors else None,
        inconclusive_rate=_share(len(leaks) - len(conclusive), len(leaks)),
        false_call_rate=_share(len(false_calls), len(nones)),
        by_stability=_split(leaks, lambda r: r.dominant_stability.value, classes, positions),
        by_size=_split(
            leaks, lambda r: _size_label(r.true_rate_kg_h), [b[0] for b in SIZE_BINS], positions
        ),
    )
