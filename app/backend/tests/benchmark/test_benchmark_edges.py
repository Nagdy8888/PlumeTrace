"""Edge tests for the benchmark: case geometry, metric corner cases, report files, the CLI."""

import json
import math
from pathlib import Path
from typing import Any

import pytest
from benchmark.__main__ import main
from benchmark.cases import (
    CASE_HOURS,
    N_NO_LEAK,
    N_OFF_LIST,
    N_ON_LIST,
    OFF_LIST_MAX_M,
    OFF_LIST_MIN_M,
    BenchmarkCase,
    generate_cases,
)
from benchmark.metrics import SIZE_BINS, is_correct, summarize
from benchmark.report import METRIC_LABELS, render_markdown, write_reports
from benchmark.runner import CaseResult, window_stability

from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.inversion import CandidateScore, InversionResult
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.loader import load_facility

SPEC = load_facility()
CANDS = emission_candidates(SPEC)
POSITIONS = {c.id: c.position for c in CANDS}
A, B = CANDS[0], CANDS[-1]


def _res(ids: list[str], inconclusive: bool = False, rate: float | None = 10.0) -> InversionResult:
    return InversionResult(
        ranked=[CandidateScore(id=i, probability=1.0 / len(ids)) for i in ids],
        top_id=ids[0],
        top_probability=0.5,
        rate_kg_h=rate,
        rate_p05_kg_h=None,
        rate_p95_kg_h=None,
        rate_at_grid_edge=False,
        inconclusive=inconclusive,
        reason="ambiguous" if inconclusive else None,
        windows_used=36,
    )


def _case(
    kind: Any,
    true_id: str | None,
    pos: Point3 | None,
    rate: float = 10.0,
) -> BenchmarkCase:
    source = TrueSource(pos, rate, 0.0, 21600.0) if pos else None
    return BenchmarkCase("c-000", kind, source, true_id, 0, 1)


def _cr(
    case: BenchmarkCase,
    result: InversionResult,
    stability: StabilityClass = StabilityClass.D,
) -> CaseResult:
    return CaseResult(case, result, stability, case.source.rate_kg_h if case.source else None)


def test_case_ids_and_order() -> None:
    """Ids count from 0 within each kind; kinds appear in the fixed order."""
    cases = generate_cases(SPEC)
    assert cases[0].case_id == "on_list-000"
    assert cases[N_ON_LIST - 1].case_id == f"on_list-{N_ON_LIST - 1:03d}"
    assert cases[N_ON_LIST].case_id == "off_list-000"
    assert cases[-1].case_id == f"no_leak-{N_NO_LEAK - 1:03d}"
    assert len({c.case_id for c in cases}) == len(cases)
    kinds = [c.kind for c in cases]
    assert kinds == ["on_list"] * N_ON_LIST + ["off_list"] * N_OFF_LIST + ["no_leak"] * N_NO_LEAK


def test_on_list_sources_sit_at_the_candidate() -> None:
    """An on-list source is at the named candidate and runs for the whole case."""
    for c in generate_cases(SPEC)[:N_ON_LIST]:
        assert c.source is not None
        assert c.source.position == POSITIONS[str(c.true_candidate_id)]
        assert (c.source.start_s, c.source.end_s) == (0.0, CASE_HOURS * 3600.0)
        assert 0 <= c.start_hour_of_day <= 23


def test_off_list_sources_are_offset_and_inside_the_site() -> None:
    """An off-list source is at most 10 m from its candidate, inside the bounds."""
    b = SPEC.site.bounds
    offsets = []
    for c in generate_cases(SPEC)[N_ON_LIST : N_ON_LIST + N_OFF_LIST]:
        assert c.source is not None
        base = POSITIONS[str(c.true_candidate_id)]
        p = c.source.position
        assert b.x_min_m <= p.x_m <= b.x_max_m
        assert b.y_min_m <= p.y_m <= b.y_max_m
        assert p.z_m == base.z_m
        offsets.append(math.hypot(p.x_m - base.x_m, p.y_m - base.y_m))
    assert max(offsets) <= OFF_LIST_MAX_M + 1e-9
    assert max(offsets) >= OFF_LIST_MIN_M
    assert sum(o >= OFF_LIST_MIN_M - 1e-9 for o in offsets) >= len(offsets) // 2


def test_no_leak_cases_have_no_source() -> None:
    """A no-leak case has no source and no true candidate."""
    for c in generate_cases(SPEC)[-N_NO_LEAK:]:
        assert (c.source, c.true_candidate_id) == (None, None)


def test_other_seed_gives_other_cases() -> None:
    """A different seed changes the draws."""
    assert generate_cases(SPEC, 1) != generate_cases(SPEC, 2)


def test_window_stability_empty_windows_and_partial_tail() -> None:
    """No windows gives an empty list; a partial trailing window is ignored."""
    assert window_stability([StabilityClass.A] * 5, 2, 0) == []
    s = [StabilityClass.B, StabilityClass.B, StabilityClass.A, StabilityClass.F, StabilityClass.F]
    assert window_stability(s, 2, 2) == [StabilityClass.B, StabilityClass.A]


def test_is_correct_top_k_skips_none() -> None:
    """NONE is removed before the top k is taken; an inconclusive result is never correct."""
    case = _case("on_list", B.id, B.position)
    assert not is_correct(_cr(case, _res([A.id, "NONE", B.id])), 1, POSITIONS)
    assert is_correct(_cr(case, _res([A.id, "NONE", B.id])), 2, POSITIONS)
    assert is_correct(_cr(case, _res(["NONE", A.id, B.id])), 2, POSITIONS)
    assert not is_correct(_cr(case, _res([B.id], inconclusive=True)), 3, POSITIONS)


def test_is_correct_off_list_uses_distance() -> None:
    """Off-list: any ranked candidate within 10 m of the true source counts."""
    far = max(
        CANDS,
        key=lambda c: math.hypot(c.position.x_m - A.position.x_m, c.position.y_m - A.position.y_m),
    )
    src = Point3(A.position.x_m + 6.0, A.position.y_m, A.position.z_m)
    case = _case("off_list", A.id, src)
    assert is_correct(_cr(case, _res([A.id])), 1, POSITIONS)
    assert not is_correct(_cr(case, _res([far.id])), 1, POSITIONS)


def test_is_correct_rejects_no_leak_cases() -> None:
    """The metric is defined for leak cases only."""
    with pytest.raises(ValueError, match="leak cases only"):
        is_correct(_cr(_case("no_leak", None, None), _res(["NONE"])), 1, POSITIONS)


def test_summarize_empty_is_all_zero() -> None:
    """With no cases every rate is 0.0 and the rate errors are None."""
    s = summarize([], POSITIONS)
    assert (s.n_leak, s.n_no_leak, s.top1_all, s.top1_conclusive, s.top3_all) == (0, 0, 0, 0, 0)
    assert (s.inconclusive_rate, s.false_call_rate) == (0.0, 0.0)
    assert s.rate_rel_error_median is None
    assert s.rate_rel_error_p90 is None
    assert s.by_stability == {}
    assert set(s.by_size) == {name for name, _, _ in SIZE_BINS}


def test_summarize_all_inconclusive_has_no_conclusive_accuracy() -> None:
    """Only inconclusive leak cases: top-1 over conclusive cases is 0.0, not a division error."""
    case = _case("on_list", A.id, A.position)
    s = summarize([_cr(case, _res([A.id], inconclusive=True, rate=None))], POSITIONS)
    assert (s.top1_all, s.top1_conclusive, s.inconclusive_rate) == (0.0, 0.0, 1.0)
    assert s.rate_rel_error_median is None


def test_summarize_splits_by_size_edges_and_stability() -> None:
    """Rates 5.0 and 100.0 fall in the upper bins; classes group by dominant stability."""
    results = [
        _cr(_case("on_list", A.id, A.position, 4.9), _res([A.id]), StabilityClass.C),
        _cr(_case("on_list", A.id, A.position, 5.0), _res([B.id]), StabilityClass.D),
        _cr(_case("on_list", A.id, A.position, 100.0), _res([A.id]), StabilityClass.D),
    ]
    s = summarize(results, POSITIONS)
    assert [s.by_size[k]["n"] for k in ("<5", "5-20", "20-100")] == [1, 1, 1]
    assert s.by_size["5-20"]["top1_all"] == 0.0
    assert s.by_stability["D"] == {"n": 2.0, "top1_all": 0.5, "inconclusive_rate": 0.0}
    assert set(s.by_stability) == {"C", "D"}


def test_false_call_needs_a_conclusive_source() -> None:
    """A no-leak case is a false call only if conclusive and not NONE."""
    none_case = _case("no_leak", None, None)
    results = [
        _cr(none_case, _res(["NONE", A.id], rate=None)),
        _cr(none_case, _res([A.id, "NONE"], inconclusive=True)),
        _cr(none_case, _res([A.id, "NONE"])),
        _cr(none_case, _res([B.id, "NONE"])),
    ]
    assert summarize(results, POSITIONS).false_call_rate == 0.5


def test_render_markdown_formats_values() -> None:
    """Three significant figures; an em dash for a missing rate error; no CRLF."""
    case = _case("on_list", A.id, A.position)
    s = summarize([_cr(case, _res([A.id], inconclusive=True, rate=None))], POSITIONS)
    md = render_markdown(s, {"seed": "1", "revision": "abc1234", "date": "2026-11-13"})
    assert "| Rate error, median (relative) | — |" in md
    assert "| Inconclusive rate (leak cases) | 1 |" in md
    assert "\r" not in md
    assert md.startswith("# PlumeTrace inversion benchmark\n")
    assert md.endswith("do not edit by hand.\n")
    assert all(label in md for label in METRIC_LABELS.values())


def test_write_reports_bytes_and_json(tmp_path: Path) -> None:
    """Markdown is UTF-8 with LF; the JSON has sorted keys and one row per case."""
    case = _case("on_list", A.id, A.position)
    results = [_cr(case, _res([A.id]))]
    s = summarize(results, POSITIONS)
    out_md, out_json = tmp_path / "a" / "b.md", tmp_path / "c" / "d.json"
    write_reports(s, results, {"seed": "1"}, out_md, out_json)
    raw = out_md.read_bytes()
    assert b"\r" not in raw
    raw.decode("utf-8")
    doc = json.loads(out_json.read_bytes())
    assert list(doc) == ["cases", "meta", "summary"]
    assert doc["meta"] == {"seed": "1"}
    assert sorted(doc["cases"][0]) == sorted(
        [
            "case_id",
            "kind",
            "true_candidate_id",
            "true_rate_kg_h",
            "top_id",
            "top_probability",
            "inconclusive",
            "reason",
            "rate_kg_h",
        ]
    )
    assert out_json.read_bytes().endswith(b"}\n")


def test_cli_quick_run_writes_both_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--quick runs 6 + 1 + 1 cases, prints the table and writes the report and evidence."""
    md, js = tmp_path / "benchmark.md", tmp_path / "ev" / "benchmark.json"
    main(["--quick", "--revision", "abc1234", "--out-md", str(md), "--out-json", str(js)])
    assert "| Metric | Value |" in capsys.readouterr().out
    doc = json.loads(js.read_text(encoding="utf-8"))
    assert len(doc["cases"]) == 8
    assert doc["meta"]["revision"] == "abc1234"
    assert doc["meta"]["mode"] == "quick"
    assert "abc1234" in md.read_text(encoding="utf-8")


def test_cli_requires_a_revision() -> None:
    """--revision is mandatory so every report names the code it came from."""
    with pytest.raises(SystemExit):
        main(["--quick"])
