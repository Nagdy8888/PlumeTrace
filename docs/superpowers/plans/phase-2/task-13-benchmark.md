# Phase 2 · Task 13 — Honest model-mismatch benchmark and report

**Skills:** `plan-execution`, `engineering-core`, `project-documentation`, `verify-and-review`.

**Why:** the published accuracy figure is the project's credibility anchor (design §5 "Validation").
Test leaks are generated with the truth model (Task 12), located with the inversion (Task 8), and
scored. Numbers are published exactly as produced — never tuned, never edited by hand.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/benchmark/__init__.py` (docstring only), `cases.py`, `runner.py`, `metrics.py`, `report.py`, `__main__.py` |
| Create | `app/backend/tests/benchmark/test_benchmark.py` |
| Generated | `docs/benchmark.md`, `docs/evidence/benchmark-<YYYY-MM-DD>.json` |
| Modify | `docs/reference/ENGINEERING.md` → "Benchmark", `docs/README.md` (add benchmark.md) |

`benchmark` is imported as a top-level package because `app/pyproject.toml` already sets
`pythonpath = ["backend"]` for pytest; run the CLI from `app/backend` with `uv run python -m benchmark`.

## Interface

`cases.py`:
- Constants: `BENCHMARK_SEED = 20261112`, `N_ON_LIST = 160`, `N_OFF_LIST = 40`, `N_NO_LEAK = 50`, `OFF_LIST_MIN_M = 2.0`, `OFF_LIST_MAX_M = 10.0`, `RATE_MIN_KG_H = 0.5`, `RATE_MAX_KG_H = 100.0`, `CASE_HOURS = 6`, `DT_S = 10.0`.
- `@dataclass(frozen=True) class BenchmarkCase`: `case_id: str`, `kind: Literal["on_list", "off_list", "no_leak"]`, `source: TrueSource | None`, `true_candidate_id: str | None`, `start_hour_of_day: int`, `seed: int`.
- `def generate_cases(spec: FacilitySpec, seed: int = BENCHMARK_SEED) -> list[BenchmarkCase]` — one `rng = np.random.default_rng(seed)`; order: all on-list, then off-list, then no-leak; ids `f"{kind}-{i:03d}"` (i from 0 within each kind). Per case, draws in this order:
  - on-list: candidate `cands[rng.integers(len(cands))]`; rate `exp(rng.uniform(ln 0.5, ln 100))`; `start_hour_of_day = int(rng.integers(24))`; `seed = int(rng.integers(2**31))`; source at the candidate position, active `[0, CASE_HOURS·3600)`; `true_candidate_id` = candidate id.
  - off-list: as on-list, plus after the candidate draw: angle `rng.uniform(0, 2π)`, radius `rng.uniform(2, 10)`; source at candidate + `(r·cos a, r·sin a, 0)`, clipped into the site bounds; `true_candidate_id` = that base candidate.
  - no-leak: `start_hour_of_day`, `seed`; `source=None`, `true_candidate_id=None`.

`runner.py`:
- `@dataclass(frozen=True) class CaseResult`: `case: BenchmarkCase`, `result: InversionResult`, `dominant_stability: StabilityClass`, `true_rate_kg_h: float | None`.
- `def window_stability(classes: list[StabilityClass], steps_per_window: int, n_windows: int) -> list[StabilityClass]` — most frequent class in each window (ties → alphabetically first).
- `def run_case(case: BenchmarkCase, spec: FacilitySpec) -> CaseResult`:
  1. `rng = np.random.default_rng(case.seed)`; `weather = synthetic_hourly_weather(CASE_HOURS + 1, case.start_hour_of_day, rng)`;
  2. `series = simulate_sensors([case.source] if case.source else [], methane_sensors(spec), weather, DT_S, CASE_HOURS·3600, rng, spec.site.ambient_pressure_pa, obstacles=facility_obstacles(spec))` (default `TruthConfig()` — PG_MARTIN, meander, gusts, wake, noise);
  3. `starts, means = window_means(series.times_s, series.ppm)`; `speed, direction = window_wind(series.times_s, series.wind_speed_m_s, series.wind_from_deg)`; `stab = window_stability(series.stability, int(WINDOW_S / DT_S), len(starts))`;
  4. background per sensor = `np.nanpercentile(means, 5, axis=0)`; observations = `means − background`;
  5. `invert(InversionInput(candidates=emission_candidates(spec), sensors=methane_sensors(spec), observed_ppm_above_bg=…, wind_speed_m_s=speed, wind_from_deg=direction, stability=stab, temp_k=mean of series.temp_k, pressure_pa=spec.site.ambient_pressure_pa))` (default coefficients = BRIGGS_RURAL);
  6. `dominant_stability` = most frequent of `stab` (ties → alphabetically first).
- `def run_all(cases: list[BenchmarkCase], spec: FacilitySpec) -> list[CaseResult]`.

`metrics.py`:
- `SIZE_BINS: Final = (("<5", 0.0, 5.0), ("5-20", 5.0, 20.0), ("20-100", 20.0, 100.0 + 1e-9))`
- `class BenchmarkSummary(BaseModel)`: `n_leak: int`, `n_no_leak: int`, `top1_all: float`, `top1_conclusive: float`, `top3_all: float`, `rate_rel_error_median: float | None`, `rate_rel_error_p90: float | None`, `inconclusive_rate: float`, `false_call_rate: float`, `by_stability: dict[str, dict[str, float]]`, `by_size: dict[str, dict[str, float]]` (each inner dict: `{"n": …, "top1_all": …, "inconclusive_rate": …}`).
- `def is_correct(cr: CaseResult, k: int, positions: Mapping[str, Point3]) -> bool` — leak cases only. Take `cr.result.ranked` ids in order, **remove `"NONE"`**, keep the first `k`; correct if one of them equals `true_candidate_id` (on-list) or its position lies within `OFF_LIST_MAX_M` horizontally of the true source position (off-list). An inconclusive result is never correct.
- `def summarize(results: list[CaseResult], positions: Mapping[str, Point3]) -> BenchmarkSummary` — every rate is `0.0` when its denominator is 0. `top1_all` = correct(k=1)/n_leak; `top1_conclusive` = correct(k=1)/conclusive leak cases (0.0 if none); `top3_all` = correct(k=3)/n_leak; rate error `|rate_kg_h − true|/true` over leak cases that are conclusive and correct at k=1 → median and `np.percentile(..., 90)` (None if empty); `inconclusive_rate` over leak cases; `false_call_rate` = no-leak cases that are conclusive with `top_id != "NONE"`, divided by n_no_leak; splits computed with the same definitions.

`report.py`:
- `METRIC_LABELS: Final = {"top1_all": "Top-1 accuracy (all leak cases)", "top1_conclusive": "Top-1 accuracy (conclusive leak cases)", "top3_all": "Top-3 accuracy (all leak cases)", "rate_rel_error_median": "Rate error, median (relative)", "rate_rel_error_p90": "Rate error, 90th percentile (relative)", "inconclusive_rate": "Inconclusive rate (leak cases)", "false_call_rate": "False-call rate (no-leak cases)"}`
- `def render_markdown(summary: BenchmarkSummary, meta: Mapping[str, str]) -> str` — title `# PlumeTrace inversion benchmark`; a "Run" table from `meta` (seed, revision, date, inversion coefficients, truth coefficients, case counts); a "Results" table `| Metric | Value |` using `METRIC_LABELS` and values formatted with 3 significant figures (`f"{v:.3g}"`, `—` for None); "By stability class" and "By leak size" tables; a "Method" paragraph (truth ≠ inversion physics, off-list sources, background estimated as the 5th percentile, no tuning); a final line "Generated by `python -m benchmark`; do not edit by hand."
- `def write_reports(summary: BenchmarkSummary, results: list[CaseResult], meta: Mapping[str, str], out_md: Path, out_json: Path) -> None` — markdown as UTF-8 bytes with LF; JSON = `{"meta": …, "summary": summary.model_dump(), "cases": [{case_id, kind, true_candidate_id, true_rate_kg_h, top_id, top_probability, inconclusive, reason, rate_kg_h} …]}` with `sort_keys=True, indent=2`.

`__main__.py`: argparse `--seed` (default `BENCHMARK_SEED`), `--quick` (first 6 on-list, 1 off-list, 1 no-leak cases), `--revision` (required string, e.g. `$(git rev-parse --short HEAD)`), `--out-md` (default `../../docs/benchmark.md`), `--out-json` (default `../../docs/evidence/benchmark-<UTC date>.json`). Prints the results table to stdout. No `subprocess`.

## Tests (full code) — `app/backend/tests/benchmark/test_benchmark.py`
```python
"""Tests for the benchmark package (deterministic cases, metric definitions, report)."""

from benchmark.cases import N_NO_LEAK, N_OFF_LIST, N_ON_LIST, BenchmarkCase, generate_cases
from benchmark.metrics import summarize
from benchmark.report import METRIC_LABELS, render_markdown
from benchmark.runner import CaseResult, run_all, window_stability
from plumetrace.engineering.geometry import Point3
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
    return InversionResult(ranked=ranked, top_id=top, top_probability=0.9, rate_kg_h=rate,
                           rate_p05_kg_h=None, rate_p95_kg_h=None, rate_at_grid_edge=False,
                           inconclusive=inconclusive,
                           reason="ambiguous" if inconclusive else None, windows_used=36)


def _leak(i: int, true_id: str, rate: float, result: InversionResult) -> CaseResult:
    case = BenchmarkCase(case_id=f"on_list-{i:03d}", kind="on_list",
                         source=TrueSource(POSITIONS[true_id], rate, 0.0, 21600.0),
                         true_candidate_id=true_id, start_hour_of_day=0, seed=i)
    return CaseResult(case=case, result=result, dominant_stability=StabilityClass.D,
                      true_rate_kg_h=rate)


def _none(i: int, result: InversionResult) -> CaseResult:
    case = BenchmarkCase(case_id=f"no_leak-{i:03d}", kind="no_leak", source=None,
                         true_candidate_id=None, start_hour_of_day=0, seed=i)
    return CaseResult(case=case, result=result, dominant_stability=StabilityClass.D,
                      true_rate_kg_h=None)


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
```

## Steps
- [x] **1.** Tests → FAIL (imports) → implement the five modules (each ≤ 300 lines, functions ≤ 50) → `uv run pytest -q` all green; ruff (`uv run ruff check .` covers `backend/benchmark`), ruff format, mypy (benchmark is not in mypy `packages`; still fully type-annotated), repo checks. Evidence: `app/backend/tests/benchmark/` (22 tests pass); `python scripts/ci_local.py` all stages passed.
- [x] **2. Full run** (≈ several minutes): `cd app/backend && uv run python -m benchmark --revision $(git rev-parse --short HEAD)` → writes `docs/benchmark.md` and `docs/evidence/benchmark-<date>.json`. Paste the printed results table into your report and the work log. Evidence: `docs/evidence/benchmark-2026-11-13.json`, `docs/benchmark.md` (`--revision 23b8703`).
- [x] **3.** Do **not** change any constant, threshold or coefficient to improve the numbers. The improvement round is decided by the owner at Gate 2. Evidence: `docs/WORK_LOG.md` Task 13 row (no constant, threshold, seed or case list changed; sha256 of `app/backend/benchmark/*.py` recorded).
- [x] **4. Docs.** ENGINEERING.md → "Benchmark": method, mismatch ingredients, case generation, metric definitions (copy from `metrics.py`), how to reproduce, link to `docs/benchmark.md`. Add `benchmark.md` to `docs/README.md`. Work-log; `STATUS.md` (last 2.13, next 2.14). Evidence: `docs/reference/ENGINEERING.md` section "Benchmark"; `docs/README.md`; `docs/WORK_LOG.md`.
- [ ] **5. Commit** `feat(benchmark): add model-mismatch inversion benchmark and report` (include the generated report and evidence JSON). STOP — Phase 2 is complete.
