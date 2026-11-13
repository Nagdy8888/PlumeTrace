"""Run the PlumeTrace checks locally, in a fixed order (GitHub Actions are not used).

Usage, from the repository root:
    python scripts/ci_local.py             quick stages (the pre-commit hook runs this)
    python scripts/ci_local.py --full      every stage; the local database is required
    python scripts/ci_local.py --only ruff,mypy
    python scripts/ci_local.py --list
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
Command = tuple[str, tuple[str, ...]]
BOTH = frozenset({"quick", "full"})
QUICK = frozenset({"quick"})
FULL = frozenset({"full"})


@dataclass(frozen=True)
class Stage:
    """One named check: commands run in order, each from a folder relative to the repo root."""

    name: str
    commands: tuple[Command, ...]
    modes: frozenset[str] = BOTH
    env: tuple[tuple[str, str], ...] = ()


def _skill(script: str, *args: str) -> Command:
    """Build a command that runs a project-skill script with this interpreter in isolated mode."""
    return (".", (PY, "-I", f".claude/skills/{script}", *args))


STAGES: tuple[Stage, ...] = (
    Stage("structure", (_skill("repo-structure/scripts/check_structure.py", "."),)),
    Stage("env", (_skill("security-checks/scripts/check_env.py", "."),)),
    Stage("secrets", (_skill("security-checks/scripts/secret_scan.py", "."),)),
    Stage("slop", (_skill("frontend-design/scripts/check_slop.py", "app/frontend/src"),)),
    Stage(
        "ruff",
        (
            ("app", ("uv", "run", "ruff", "check", ".")),
            ("app", ("uv", "run", "ruff", "check", "--config", "pyproject.toml", "../scripts")),
        ),
    ),
    Stage(
        "ruff-format",
        (
            (
                "app",
                (
                    "uv",
                    "run",
                    "ruff",
                    "format",
                    "--check",
                    "--config",
                    "pyproject.toml",
                    ".",
                    "../scripts",
                ),
            ),
        ),
    ),
    Stage("mypy", (("app", ("uv", "run", "mypy")),)),
    Stage(
        "python-tests",
        (("app", ("uv", "run", "pytest", "-q", "-m", "not slow and not fuzz")),),
        modes=QUICK,
    ),
    Stage(
        "python-tests-full",
        (
            (
                "app",
                (
                    "uv",
                    "run",
                    "pytest",
                    "-q",
                    "-m",
                    "not fuzz",
                    "--cov=plumetrace",
                    "--cov=plumetrace_agents",
                    "--cov-report=term-missing:skip-covered",
                    "--cov-fail-under=85",
                ),
            ),
        ),
        modes=FULL,
        env=(("PLUMETRACE_REQUIRE_DB", "1"),),
    ),
    Stage("frontend-lint", (("app/frontend", ("npm", "run", "lint")),)),
    Stage("frontend-typecheck", (("app/frontend", ("npm", "run", "typecheck")),)),
    Stage("frontend-test", (("app/frontend", ("npm", "run", "test")),), modes=QUICK),
    Stage("frontend-coverage", (("app/frontend", ("npm", "run", "test:coverage")),), modes=FULL),
    Stage("frontend-build", (("app/frontend", ("npm", "run", "build")),), modes=FULL),
    Stage(
        "contract-drift",
        (
            ("app", ("uv", "run", "python", "../scripts/export_contract.py")),
            ("app/frontend", ("npm", "run", "gen:types")),
            (".", ("git", "diff", "--exit-code", "--", "app/frontend/src/shared")),
        ),
        modes=FULL,
    ),
)

Runner = Callable[..., subprocess.CompletedProcess[bytes]]


def select(mode: str, only: Sequence[str] = ()) -> list[Stage]:
    """Return the stages to run: the named ones (any mode) or every stage of the mode."""
    if only:
        unknown = sorted(set(only) - {s.name for s in STAGES})
        if unknown:
            raise SystemExit(f"unknown stage: {', '.join(unknown)}")
        return [s for s in STAGES if s.name in only]
    return [s for s in STAGES if mode in s.modes]


def run_stage(stage: Stage, runner: Runner = subprocess.run) -> bool:
    """Run one stage's commands in order; stop at the first failing command."""
    env = {**os.environ, **dict(stage.env)}
    for cwd, argv in stage.commands:
        print(f"$ ({cwd}) {' '.join(argv)}", flush=True)
        cmd = shutil.which(f"{argv[0]}.cmd") if os.name == "nt" else None  # npm/npx on Windows
        exe = cmd or shutil.which(argv[0]) or argv[0]
        result = runner([exe, *argv[1:]], cwd=ROOT / cwd, env=env, check=False)
        if result.returncode != 0:
            return False
    return True


def main(argv: Sequence[str] | None = None, runner: Runner = subprocess.run) -> int:
    """Parse arguments, run the stages, print a summary; 0 only when every stage passed."""
    parser = argparse.ArgumentParser(description="Run the PlumeTrace checks locally.")
    parser.add_argument("--full", action="store_true", help="run every stage (database required)")
    parser.add_argument("--only", default="", help="comma-separated stage names")
    parser.add_argument("--list", action="store_true", help="list the stages and exit")
    args = parser.parse_args(argv)
    if args.list:
        for s in STAGES:
            print(f"{s.name:22} {'/'.join(sorted(s.modes))}")
        return 0
    only = [n for n in args.only.split(",") if n]
    results: list[tuple[str, bool, float]] = []
    for stage in select("full" if args.full else "quick", only):
        start = time.monotonic()
        results.append((stage.name, run_stage(stage, runner), time.monotonic() - start))
    print("\nstage                  result  seconds")
    for name, ok, seconds in results:
        print(f"{name:22} {'pass' if ok else 'FAIL':7} {seconds:7.1f}")
    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("all stages passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
