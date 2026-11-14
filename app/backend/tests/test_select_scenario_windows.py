"""Tests for scripts/select_scenario_windows.py (stub runs: no simulation, no network)."""

import importlib.util
from dataclasses import replace
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.scenario import ScenarioDefinition
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def _load_script() -> ModuleType:
    """Import scripts/select_scenario_windows.py as a module."""
    path = REPO_ROOT / "scripts" / "select_scenario_windows.py"
    spec = importlib.util.spec_from_file_location("select_scenario_windows", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, passing: set[tuple[str, int]]
) -> list[tuple[str, int]]:
    """Replace the run and the criteria; ``passing`` holds the (scenario, offset) that pass."""
    runs: list[tuple[str, int]] = []

    def fake_run(
        definition: ScenarioDefinition, _spec: object, _snap: object
    ) -> ScenarioDefinition:
        runs.append((definition.id, definition.weather_offset_h))
        return definition

    monkeypatch.setattr(mod, "run_scenario", fake_run)
    monkeypatch.setattr(
        mod,
        "_criteria",
        lambda _spec: {
            i: (lambda d, i=i: (i, d.weather_offset_h) in passing)
            for i in ("s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift")
        },
    )
    monkeypatch.setattr(mod, "CANDIDATE_OFFSETS_H", (0, 2, 4, 160))
    return runs


def test_only_offsets_that_fit_are_run_and_the_first_pass_wins(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With a 9 h snapshot only the offsets that leave duration + 1 hours are run."""
    mod = _load_script()
    short = replace(SNAP, hours=SNAP.hours[:9])
    runs = _stub(mod, monkeypatch, {("s1_rod_packing", 2), ("s4_planned_blowdown", 0)})
    first = mod.select_windows(SPEC, short)
    # s1 and s5 need 7 h, s4 needs 5 h: offsets 0 and 2 fit all, offset 4 fits only s4 (4+5=9)
    assert runs == [
        ("s1_rod_packing", 0),
        ("s1_rod_packing", 2),
        ("s4_planned_blowdown", 0),
        ("s4_planned_blowdown", 2),
        ("s4_planned_blowdown", 4),
        ("s5_sensor_drift", 0),
        ("s5_sensor_drift", 2),
    ]
    assert first == {"s1_rod_packing": 2, "s4_planned_blowdown": 0, "s5_sensor_drift": None}
    out = capsys.readouterr().out.splitlines()
    assert out[:2] == ["s1_rod_packing: offset 0 h FAIL", "s1_rod_packing: offset 2 h PASS"]


def test_exit_code(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """0 when every scenario has a passing offset, 1 when one has none (and says NONE)."""
    mod = _load_script()
    every = {(i, 0) for i in ("s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift")}
    _stub(mod, monkeypatch, every)
    assert mod.main() == 0
    assert "s5_sensor_drift: first passing offset 0 h" in capsys.readouterr().out
    _stub(mod, monkeypatch, every - {("s5_sensor_drift", 0)})
    assert mod.main() == 1
    assert "s5_sensor_drift: first passing offset NONE h" in capsys.readouterr().out
