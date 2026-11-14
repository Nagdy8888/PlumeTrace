"""Tests of the pre-registered calibration metrics and the adoption rule (hand-built results)."""

import pytest
from benchmark.calibration import (
    CONFIDENT_P,
    MethodMetrics,
    adopt_meander,
    calibration_metrics,
    method_metrics,
)
from benchmark.cases import BenchmarkCase
from benchmark.metrics import BenchmarkSummary, summarize
from benchmark.runner import CaseResult

from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.inversion import NO_SOURCE_ID, CandidateScore, InversionResult
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.loader import load_facility

CANDS = emission_candidates(load_facility())
POSITIONS = {c.id: c.position for c in CANDS}
TRUE_ID, OTHER_ID = CANDS[0].id, CANDS[-1].id
BIN_LABELS = ["[0.6, 0.8)", "[0.8, 0.95)", "[0.95, 1.0]"]


def _leak(
    top: str,
    p: float = 0.9,
    rate: float | None = 10.0,
    true_rate: float = 10.0,
    p05: float | None = 8.0,
    p95: float | None = 12.0,
    edge: bool = False,
    inconclusive: bool = False,
) -> CaseResult:
    """An on-list leak case whose true source is ``TRUE_ID`` and whose inversion says ``top``."""
    ids = [top] if top != OTHER_ID else [top, TRUE_ID]
    result = InversionResult(
        ranked=[CandidateScore(id=i, probability=p if i == top else 0.1) for i in ids],
        top_id=top,
        top_probability=p,
        rate_kg_h=rate,
        rate_p05_kg_h=p05,
        rate_p95_kg_h=p95,
        rate_at_grid_edge=edge,
        inconclusive=inconclusive,
        reason="ambiguous" if inconclusive else None,
        windows_used=36,
    )
    src = TrueSource(Point3(0.0, 0.0, 0.0), true_rate, 0.0, 21600.0)
    case = BenchmarkCase("on_list-000", "on_list", src, TRUE_ID, 0, 1)
    return CaseResult(case, result, StabilityClass.D, true_rate)


def _no_leak(top: str = NO_SOURCE_ID) -> CaseResult:
    """A no-leak control case."""
    result = InversionResult(
        ranked=[CandidateScore(id=top, probability=0.9)],
        top_id=top,
        top_probability=0.9,
        rate_kg_h=None,
        rate_p05_kg_h=None,
        rate_p95_kg_h=None,
        rate_at_grid_edge=False,
        inconclusive=False,
        reason=None,
        windows_used=36,
    )
    case = BenchmarkCase("no_leak-000", "no_leak", None, None, 0, 1)
    return CaseResult(case, result, StabilityClass.D, None)


def test_confident_wrong_rate() -> None:
    """Wrong named calls with p >= 0.95, over all named calls; p = 0.95 counts, 0.94 does not."""
    results = [
        _leak(OTHER_ID, p=0.95),  # wrong and confident: counts
        _leak(OTHER_ID, p=0.94),  # wrong, not confident
        _leak(TRUE_ID, p=0.99),  # confident but right
        _leak(TRUE_ID, p=0.7),
        _leak(NO_SOURCE_ID, p=0.97, rate=None, p05=None, p95=None),  # not named
        _leak(OTHER_ID, p=0.99, inconclusive=True),  # not conclusive, not named
        _no_leak(OTHER_ID),  # no-leak cases are never named
    ]
    assert CONFIDENT_P == 0.95
    assert calibration_metrics(results, POSITIONS).confident_wrong_rate == 0.25


def test_missed_leak_rate() -> None:
    """Conclusive NONE on a leak case over all leak cases; inconclusive and no-leak are excluded."""
    none = {"rate": None, "p05": None, "p95": None}
    results = [
        _leak(NO_SOURCE_ID, **none),
        _leak(NO_SOURCE_ID, **none),
        _leak(NO_SOURCE_ID, inconclusive=True, **none),
        _leak(TRUE_ID),
        _leak(OTHER_ID),
        _no_leak(),
        _no_leak(),
    ]
    assert calibration_metrics(results, POSITIONS).missed_leak_rate == 2 / 5


def test_rate_metrics_use_only_good_cases() -> None:
    """Good = named, right at k = 1, with a rate; interval ends are inclusive."""
    results = [
        _leak(TRUE_ID, rate=10.0, true_rate=10.0, p05=10.0, p95=11.0),  # p05 == true: inside
        _leak(TRUE_ID, rate=20.0, true_rate=10.0, p05=15.0, p95=25.0, edge=True),  # above
        _leak(TRUE_ID, rate=5.0, true_rate=10.0, p05=3.0, p95=10.0),  # p95 == true: inside
        _leak(TRUE_ID, rate=None, p05=None, p95=None),  # right but no rate: not good
        _leak(OTHER_ID, rate=10.0, p05=1.0, p95=100.0),  # wrong: not good
    ]
    c = calibration_metrics(results, POSITIONS)
    assert (c.n_named, c.n_good) == (5, 3)
    assert c.rate_in_interval == 2 / 3
    assert c.grid_edge_share == 1 / 3
    assert c.median_rate_ratio == 1.0  # ratios 1.0, 2.0, 0.5


def test_empty_denominators() -> None:
    """With nothing to divide by every rate is 0.0, the median is None and every bin is empty."""
    for results in ([], [_no_leak(), _no_leak(OTHER_ID)]):
        c = calibration_metrics(results, POSITIONS)
        assert (c.confident_wrong_rate, c.missed_leak_rate) == (0.0, 0.0)
        assert (c.rate_in_interval, c.grid_edge_share) == (0.0, 0.0)
        assert c.median_rate_ratio is None
        assert (c.n_named, c.n_good) == (0, 0)
        assert list(c.reliability) == BIN_LABELS
        assert all(v == {"n": 0.0, "accuracy": 0.0} for v in c.reliability.values())


def test_reliability_bin_edges() -> None:
    """0.8 opens the second bin and 0.95 the third; values just below stay; above 1.0 is third."""
    results = [
        _leak(TRUE_ID, p=0.6),
        _leak(OTHER_ID, p=0.7999999),
        _leak(TRUE_ID, p=0.8),
        _leak(OTHER_ID, p=0.9499999),
        _leak(TRUE_ID, p=0.95),
        _leak(TRUE_ID, p=1.0),
        _leak(OTHER_ID, p=1.0000000000001),
    ]
    rel = calibration_metrics(results, POSITIONS).reliability
    assert rel["[0.6, 0.8)"] == {"n": 2.0, "accuracy": 0.5}
    assert rel["[0.8, 0.95)"] == {"n": 2.0, "accuracy": 0.5}
    assert rel["[0.95, 1.0]"] == {"n": 3.0, "accuracy": 2 / 3}


def test_method_metrics_reuses_summarize() -> None:
    """The bundle holds exactly what ``summarize`` returns plus the calibration metrics."""
    results = [_leak(TRUE_ID, p=0.99), _leak(OTHER_ID, p=0.97), _no_leak()]
    mm = method_metrics(results, POSITIONS)
    assert mm.summary == summarize(results, POSITIONS)
    assert mm.calibration == calibration_metrics(results, POSITIONS)
    assert (mm.top1_all, mm.false_call_rate) == (mm.summary.top1_all, mm.summary.false_call_rate)
    assert mm.confident_wrong_rate == 0.5


def _bundle(top1: float, wrong: float, false_call: float) -> MethodMetrics:
    """A bundle with the three adoption numbers set and everything else filler."""
    summary = BenchmarkSummary(
        n_leak=10,
        n_no_leak=10,
        top1_all=top1,
        top1_conclusive=top1,
        top3_all=top1,
        rate_rel_error_median=None,
        rate_rel_error_p90=None,
        inconclusive_rate=0.0,
        false_call_rate=false_call,
        by_stability={},
        by_size={},
    )
    calibration = calibration_metrics([], POSITIONS).model_copy(
        update={"confident_wrong_rate": wrong}
    )
    return MethodMetrics(summary=summary, calibration=calibration)


@pytest.mark.parametrize(
    ("meander", "expected"),
    [
        ((0.5, 0.2, 0.1), True),  # all three equal: ties adopt
        ((0.6, 0.1, 0.0), True),  # better on all three
        ((0.49, 0.2, 0.1), False),  # top-1 alone is worse
        ((0.5, 0.21, 0.1), False),  # confident-wrong alone is worse
        ((0.5, 0.2, 0.11), False),  # false-call alone is worse
        ((0.9, 0.2, 0.1), True),  # much better top-1, ties elsewhere
        ((0.5, 0.0, 0.1), True),
        ((0.5, 0.2, 0.0), True),
    ],
)
def test_adopt_meander_truth_table(meander: tuple[float, float, float], expected: bool) -> None:
    """Adopt iff top-1 >= Task 8 and confident-wrong <= Task 8 and false-call <= Task 8."""
    assert adopt_meander(_bundle(0.5, 0.2, 0.1), _bundle(*meander)) is expected
