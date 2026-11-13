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
