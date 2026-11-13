"""Tests for the benchmark package (deterministic cases, metric definitions, report)."""

from benchmark.cases import N_NO_LEAK, N_OFF_LIST, N_ON_LIST, BenchmarkCase, generate_cases
from benchmark.metrics import summarize
from benchmark.report import METRIC_LABELS, render_markdown
from benchmark.runner import CaseResult, run_all, window_stability

from plumetrace.engineering.inversion import CandidateScore, InversionResult
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.loader import load_facility

SPEC = load_facility()
POSITIONS = {c.id: c.position for c in emission_candidates(SPEC)}


def test_case_generation_counts_and_determinism() -> None:
    """250 cases in a fixed order, identical for the same seed."""
    a = generate_cases(SPEC)
    assert len(a) == N_ON_LIST + N_OFF_LIST + N_NO_LEAK == 250
    assert [c.kind for c in a].count("off_list") == 40
    assert a == generate_cases(SPEC)
    assert all(0.5 <= c.source.rate_kg_h <= 100.0 for c in a if c.source is not None)


def test_window_stability_mode() -> None:
    """Most frequent class per window; ties go to the alphabetically first class."""
    s = [StabilityClass.D] * 4 + [StabilityClass.C] * 2 + [StabilityClass.E, StabilityClass.F] * 3
    assert window_stability(s, 6, 2) == [StabilityClass.D, StabilityClass.E]


def test_quick_run_produces_results() -> None:
    """The end-to-end pipeline runs on a few cases."""
    cases = generate_cases(SPEC)
    picked = cases[:2] + [cases[N_ON_LIST]] + [cases[-1]]
    results = run_all(picked, SPEC)
    assert len(results) == 4
    assert all(r.result.windows_used >= 0 for r in results)


def _result(top: str, ids: list[str], inconclusive: bool, rate: float | None) -> InversionResult:
    ranked = [CandidateScore(id=i, probability=1.0 / len(ids)) for i in ids]
    return InversionResult(
        ranked=ranked,
        top_id=top,
        top_probability=0.9,
        rate_kg_h=rate,
        rate_p05_kg_h=None,
        rate_p95_kg_h=None,
        rate_at_grid_edge=False,
        inconclusive=inconclusive,
        reason="ambiguous" if inconclusive else None,
        windows_used=36,
    )


def _leak(i: int, true_id: str, rate: float, result: InversionResult) -> CaseResult:
    case = BenchmarkCase(
        case_id=f"on_list-{i:03d}",
        kind="on_list",
        source=TrueSource(POSITIONS[true_id], rate, 0.0, 21600.0),
        true_candidate_id=true_id,
        start_hour_of_day=0,
        seed=i,
    )
    return CaseResult(
        case=case, result=result, dominant_stability=StabilityClass.D, true_rate_kg_h=rate
    )


def _none(i: int, result: InversionResult) -> CaseResult:
    case = BenchmarkCase(
        case_id=f"no_leak-{i:03d}",
        kind="no_leak",
        source=None,
        true_candidate_id=None,
        start_hour_of_day=0,
        seed=i,
    )
    return CaseResult(
        case=case, result=result, dominant_stability=StabilityClass.D, true_rate_kg_h=None
    )


def test_summary_definitions() -> None:
    """3 of 4 leaks correct, 1 inconclusive, 1 of 2 no-leak cases is a false call."""
    v = "VS-250.tip"
    results = [
        _leak(0, v, 10.0, _result(v, [v, "NONE"], False, 10.0)),
        _leak(1, v, 10.0, _result(v, [v, "NONE"], False, 12.0)),
        _leak(2, v, 10.0, _result(v, [v, "NONE"], False, 5.0)),
        _leak(3, v, 10.0, _result(v, [v, "NONE"], True, None)),
        _none(0, _result("NONE", ["NONE", v], False, None)),
        _none(1, _result(v, [v, "NONE"], False, 3.0)),
    ]
    s = summarize(results, POSITIONS)
    assert (s.n_leak, s.n_no_leak) == (4, 2)
    assert s.top1_all == 0.75
    assert s.top1_conclusive == 1.0
    assert s.top3_all == 0.75
    assert s.inconclusive_rate == 0.25
    assert s.false_call_rate == 0.5
    assert s.rate_rel_error_median == 0.2
    assert abs((s.rate_rel_error_p90 or 0.0) - 0.44) < 1e-9


def test_report_contains_every_metric() -> None:
    """The markdown report names every headline metric."""
    v = "VS-250.tip"
    s = summarize([_leak(0, v, 10.0, _result(v, [v], False, 10.0))], POSITIONS)
    md = render_markdown(s, {"seed": "1", "revision": "abc1234", "date": "2026-11-13"})
    for label in METRIC_LABELS.values():
        assert label in md
    assert "do not edit by hand" in md
