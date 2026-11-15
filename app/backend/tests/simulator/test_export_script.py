"""Tests for scripts/export_scenarios.py and the replay part of the exported contract."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT
from plumetrace.facility.loader import load_facility
from plumetrace.simulator import export
from plumetrace.simulator.weather import load_snapshot


def _load(name: str) -> ModuleType:
    """Import scripts/<name>.py as a module."""
    path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_scenario_writes_the_replay_bytes(tmp_path: Path) -> None:
    """The file is the replay bytes (LF, trailing newline) and the return value is its size."""
    mod = _load("export_scenarios")
    out = tmp_path / "nested" / "scenarios"
    size = mod.export_scenario("s5_sensor_drift", out, load_facility(), load_snapshot())
    data = (out / "s5_sensor_drift.json").read_bytes()
    assert size == len(data) and data.endswith(b"}\n") and b"\r" not in data


def test_unknown_scenario_and_over_budget_write_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown id is a KeyError; an over-budget replay raises before any file exists."""
    mod = _load("export_scenarios")
    spec, snap = load_facility(), load_snapshot()
    with pytest.raises(KeyError):
        mod.export_scenario("s9_nothing", tmp_path, spec, snap)
    monkeypatch.setattr(export, "MAX_REPLAY_BYTES", 10)
    with pytest.raises(ValueError, match="budget 10"):
        mod.export_scenario("s5_sensor_drift", tmp_path, spec, snap)
    assert list(tmp_path.iterdir()) == []


def test_contract_schema_includes_the_replay_format() -> None:
    """The contract carries the replay models, including the version literal and strict fields."""
    schema = _load("export_contract").build_contract_schema()
    defs = schema["$defs"]
    assert {"ReplayScenario", "PlumeKeyframe", "ReplayGrid", "FacilitySpec"} <= set(defs)
    assert defs["ReplayScenario"]["properties"]["schema_version"]["const"] == 1
    assert defs["ReplayScenario"]["additionalProperties"] is False
