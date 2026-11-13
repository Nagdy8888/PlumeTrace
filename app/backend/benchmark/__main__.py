"""Command line: run the benchmark, print the results table and write the report files.

Run from ``app/backend``: ``uv run python -m benchmark --revision $(git rev-parse --short HEAD)``.
"""

import argparse
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from benchmark.cases import BENCHMARK_SEED, N_ON_LIST, BenchmarkCase, generate_cases
from benchmark.metrics import summarize
from benchmark.report import results_table, write_reports
from benchmark.runner import run_all
from plumetrace.engineering.inversion import InversionInput
from plumetrace.engineering.truth_model import TruthConfig
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.loader import load_facility

_QUICK_COUNTS = (6, 1, 1)


def _parse(argv: Sequence[str] | None, today: str) -> argparse.Namespace:
    """Parse the command line."""
    p = argparse.ArgumentParser(prog="python -m benchmark", description=__doc__)
    p.add_argument("--seed", type=int, default=BENCHMARK_SEED)
    p.add_argument("--quick", action="store_true", help="6 on-list, 1 off-list, 1 no-leak case")
    p.add_argument(
        "--revision", required=True, help="git revision, e.g. $(git rev-parse --short HEAD)"
    )
    p.add_argument("--out-md", type=Path, default=Path("../../docs/benchmark.md"))
    p.add_argument(
        "--out-json", type=Path, default=Path(f"../../docs/evidence/benchmark-{today}.json")
    )
    return p.parse_args(argv)


def _pick(cases: list[BenchmarkCase], quick: bool) -> list[BenchmarkCase]:
    """All cases, or the first few of each kind in quick mode."""
    if not quick:
        return cases
    on, off, none = _QUICK_COUNTS
    return cases[:on] + cases[N_ON_LIST : N_ON_LIST + off] + cases[-none:]


def main(argv: Sequence[str] | None = None) -> None:
    """Run the benchmark and write ``docs/benchmark.md`` and the evidence JSON.

    Args:
        argv: Command-line arguments; ``sys.argv`` when None.
    """
    now = datetime.now(UTC)
    args = _parse(argv, now.strftime("%Y-%m-%d"))
    spec = load_facility()
    cases = _pick(generate_cases(spec, args.seed), args.quick)
    results = run_all(cases, spec)
    positions = {c.id: c.position for c in emission_candidates(spec)}
    summary = summarize(results, positions)
    kinds = Counter(c.kind for c in cases)
    meta = {
        "seed": str(args.seed),
        "revision": args.revision,
        "date": now.strftime("%Y-%m-%d"),
        "inversion coefficients": InversionInput.model_fields["coeff"].default.name,
        "truth coefficients": TruthConfig().coeff.name,
        "cases": ", ".join(f"{n} {kind}" for kind, n in sorted(kinds.items())),
        "mode": "quick" if args.quick else "full",
    }
    write_reports(summary, results, meta, args.out_md, args.out_json)
    print(results_table(summary))


if __name__ == "__main__":
    main()
