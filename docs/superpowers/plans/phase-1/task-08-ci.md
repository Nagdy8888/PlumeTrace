# Phase 1 · Task 8 — Local CI: one check runner and a git pre-commit hook (no GitHub Actions)

**Read first:** `security-checks`, `testing-strategy`. **Skills:** `plan-execution`, `security-checks`, `contribution-workflow`, `project-documentation`.

**Owner decision (2026-11-13):** the GitHub account has billing problems, so **GitHub Actions are
not used at all** — no `.github/` folder (the structure checker refuses one). Every check runs
**locally** with one script, and a git pre-commit hook runs the quick checks before every commit.
The full run is required before every phase gate and at the release gate.

**Goal:** `scripts/ci_local.py` runs every check of the definition of done in a fixed order and
prints a summary; `scripts/install_git_hooks.py` installs the pre-commit hook. Later tasks add
their stages to `STAGES` (each such task says so).

## Files
| Action | Path |
|---|---|
| Create | `scripts/ci_local.py`, `scripts/install_git_hooks.py` |
| Create (tests) | `app/backend/tests/test_ci_local.py` |
| Modify | `docs/LOCAL_DEVELOPMENT.md` → `## Checks`; `docs/OWNER_ACTIONS.md`; `docs/reference/TESTING.md` (create; see the `testing-strategy` skill for its sections) |

## `scripts/ci_local.py` (exact content)
```python
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
        exe = shutil.which(argv[0]) or argv[0]  # npm/npx are .cmd files on Windows
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
```

## `scripts/install_git_hooks.py` (exact content)
```python
"""Install the git pre-commit hook that runs the quick local checks (scripts/ci_local.py)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = (
    "#!/bin/sh\n"
    "# Installed by scripts/install_git_hooks.py: quick local checks before every commit.\n"
    "# GitHub Actions are not used; never bypass this hook with --no-verify.\n"
    "exec python scripts/ci_local.py\n"
)


def main() -> int:
    """Write .git/hooks/pre-commit; refuse to overwrite a different existing hook."""
    hooks = ROOT / ".git" / "hooks"
    if not hooks.is_dir():
        print("not a git repository: run git init first")
        return 1
    target = hooks / "pre-commit"
    if target.exists() and target.read_text(encoding="utf-8") != HOOK:
        print(f"a different pre-commit hook exists; not overwritten: {target}")
        return 1
    target.write_bytes(HOOK.encode("utf-8"))
    target.chmod(0o755)
    print("installed .git/hooks/pre-commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Test (full code) — `app/backend/tests/test_ci_local.py`
```python
"""The local check runner selects stages by mode, stops on failure and reports a summary."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "ci_local.py"
spec = importlib.util.spec_from_file_location("ci_local", SCRIPT)
assert spec and spec.loader
ci = importlib.util.module_from_spec(spec)
sys.modules["ci_local"] = ci  # dataclasses need the module registered
spec.loader.exec_module(ci)


def _result(code: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(args=[], returncode=code)


def test_quick_mode_excludes_full_only_stages() -> None:
    """Quick runs the fast stages; full replaces the quick test stages with the full ones."""
    quick = {s.name for s in ci.select("quick")}
    full = {s.name for s in ci.select("full")}
    assert "python-tests" in quick and "python-tests-full" not in quick
    assert "python-tests-full" in full and "python-tests" not in full
    assert "contract-drift" in full and "contract-drift" not in quick
    assert {"structure", "env", "secrets", "slop", "ruff", "mypy"} <= quick & full


def test_unknown_stage_name_is_an_error() -> None:
    """--only with a wrong name stops before running anything."""
    with pytest.raises(SystemExit, match="unknown stage: nope"):
        ci.select("quick", ["nope"])


def test_stage_stops_at_first_failing_command() -> None:
    """A failing first command means the second never runs."""
    calls: list[list[str]] = []

    def runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        return _result(1)

    stage = ci.Stage("two", ((".", ("git", "status")), (".", ("git", "log"))))
    assert ci.run_stage(stage, runner) is False and len(calls) == 1


def test_main_reports_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 1 and a FAILED line naming the failing stage; passing stages are listed too."""
    monkeypatch.setattr(
        ci, "STAGES", (ci.Stage("good", ((".", ("ok",)),)), ci.Stage("bad", ((".", ("no",)),)))
    )

    def runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        return _result(0 if argv[-1] == "ok" or argv[0].endswith("ok") else 1)

    assert ci.main([], runner) == 1
    out = capsys.readouterr().out
    assert "FAILED: bad" in out and "good" in out


def test_stage_env_is_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stage variables reach the command environment."""
    seen: dict[str, str] = {}

    def runner(argv: list[str], **kw: object) -> subprocess.CompletedProcess[bytes]:
        seen.update(kw["env"])  # type: ignore[arg-type]
        return _result(0)

    ci.run_stage(ci.Stage("db", ((".", ("x",)),), env=(("PLUMETRACE_REQUIRE_DB", "1"),)), runner)
    assert seen["PLUMETRACE_REQUIRE_DB"] == "1"
```
(`parents[3]` = repo root from `app/backend/tests/test_ci_local.py`. `ok`/`no` are fake executables — `shutil.which` returns `None`, so the runner receives the bare names.)

## Steps
- [x] **1.** Test → FAIL → create both scripts exactly as shown → `cd app && uv run pytest backend/tests/test_ci_local.py -q` green; ruff (incl. `../scripts`), ruff format, mypy clean.
- [x] **2.** `python scripts/install_git_hooks.py` → `installed .git/hooks/pre-commit`.
- [x] **3.** `python scripts/ci_local.py` (quick) → all stages pass; then with local Supabase running `python scripts/ci_local.py --full` → all stages pass (the `frontend-coverage` stage needs Task 5's `test:coverage` script; the `contract-drift` stage needs Task 7). Paste both summary tables.
- [x] **4.** `cd app && uv run pip-audit` and `cd app/frontend && npm audit --audit-level=high` once by hand (they become stages in Phase 6 Task 6). A high/critical finding: STOP and report (do not upgrade pins yourself).
- [x] **5. Docs.** `LOCAL_DEVELOPMENT.md` → `## Checks`: "There is no GitHub Actions CI (owner decision 2026-11-13). Run `python scripts/ci_local.py` (quick; also the pre-commit hook) and `python scripts/ci_local.py --full` (before every phase gate; needs local Supabase). Install the hook once after cloning: `python scripts/install_git_hooks.py`. Never commit with `--no-verify`." plus the stage list (`--list` output). `OWNER_ACTIONS.md`: keep "GitHub Actions stay off". `TESTING.md` (per `testing-strategy`). Work-log row; `STATUS.md` (last 1.8, next "Gate 1").
- [ ] **6. Commit** `build(checks): add the local check runner and pre-commit hook`. (The hook runs on this commit — it must pass.) Do **not** push.

## Phase 1 exit
Write `docs/evidence/2026-11-phase-1-checks.md` with the date, the git revision (`git rev-parse --short HEAD`) and the outputs from step 3 and 4. Add it to `docs/README.md`. Set `STATUS.md`: "Phase 1 complete — waiting for Gate 1 (ks07.yaml, gas composition, component_counts.yaml, emission sources)". Commit `docs(evidence): record phase 1 checks`. STOP.
