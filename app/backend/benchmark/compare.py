"""Command line: score the Task 8 inversion and the meander-aware inversion on the same cases.

Run from ``app/backend``:
``uv run python -m benchmark.compare --seed <fresh seed> --revision $(git rev-parse --short HEAD)``.
There is no default seed: the seed of an official run is chosen and recorded by the caller.

The cases are generated once. Every ``run_case`` seeds its own generator from the case, so both
methods get identical weather, sensor noise and meander: the comparison is paired and
deterministic. Only the ``summary`` of the published benchmark JSON is read.
"""

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from benchmark.calibration import adopt_meander, method_metrics
from benchmark.cases import N_ON_LIST, BenchmarkCase, generate_cases
from benchmark.compare_report import PRE_REGISTERED, verdict_line, write_compare_reports
from benchmark.runner import run_all
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.loader import load_facility

_QUICK_COUNTS = (6, 1, 1)  # on-list, off-list, no-leak: the same first cases as ``--quick``


def _parse(argv: Sequence[str] | None, today: str) -> argparse.Namespace:
    """Parse the command line; ``--seed`` and ``--revision`` are required."""
    p = argparse.ArgumentParser(prog="python -m benchmark.compare", description=__doc__)
    p.add_argument("--seed", type=int, required=True, help="seed of the case set (no default)")
    p.add_argument(
        "--revision", required=True, help="git revision, e.g. $(git rev-parse --short HEAD)"
    )
    p.add_argument("--quick", action="store_true", help="6 on-list, 1 off-list, 1 no-leak case")
    p.add_argument(
        "--published-json",
        type=Path,
        default=Path("../../docs/evidence/benchmark-2026-11-13.json"),
    )
    p.add_argument("--out-md", type=Path, default=Path("../../docs/benchmark-improvement.md"))
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path(f"../../docs/evidence/benchmark-improvement-{today}.json"),
    )
    return p.parse_args(argv)


def _pick(cases: list[BenchmarkCase], quick: bool) -> list[BenchmarkCase]:
    """All cases, or the first few of each kind in quick mode."""
    if not quick:
        return cases
    on, off, none = _QUICK_COUNTS
    return cases[:on] + cases[N_ON_LIST : N_ON_LIST + off] + cases[-none:]


def main(argv: Sequence[str] | None = None) -> None:
    """Run both methods on one case set and write the comparison report and evidence.

    Args:
        argv: Command-line arguments; ``sys.argv`` when None.
    """
    now = datetime.now(UTC)
    args = _parse(argv, now.strftime("%Y-%m-%d"))
    published = json.loads(args.published_json.read_text(encoding="utf-8"))["summary"]
    spec = load_facility()
    cases = _pick(generate_cases(spec, args.seed), args.quick)
    positions = {c.id: c.position for c in emission_candidates(spec)}
    results = {"task8": run_all(cases, spec), "meander": run_all(cases, spec, meander=True)}
    metrics = {name: method_metrics(rows, positions) for name, rows in results.items()}
    adopted = adopt_meander(metrics["task8"], metrics["meander"])
    kinds = Counter(c.kind for c in cases)
    meta = {
        "seed": str(args.seed),
        "revision": args.revision,
        "date": now.strftime("%Y-%m-%d"),
        "pre_registered": PRE_REGISTERED,
        "mode": "quick" if args.quick else "full",
        "cases": ", ".join(f"{n} {kind}" for kind, n in sorted(kinds.items())),
        "adopted": "meander" if adopted else "task8",
    }
    methods = {name: (metrics[name], results[name]) for name in results}
    write_compare_reports(meta, methods, published, adopted, positions, args.out_md, args.out_json)
    print(verdict_line(metrics["task8"], metrics["meander"], adopted))


if __name__ == "__main__":
    main()
