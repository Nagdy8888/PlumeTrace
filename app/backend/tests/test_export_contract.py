"""Tests for scripts/export_contract.py (deterministic, LF-only generated files)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from plumetrace.config import REPO_ROOT
from plumetrace.facility.loader import load_facility


def _load_script() -> ModuleType:
    """Import scripts/export_contract.py as a module."""
    path = REPO_ROOT / "scripts" / "export_contract.py"
    spec = importlib.util.spec_from_file_location("export_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_json_is_deterministic_and_lf_only(tmp_path: Path) -> None:
    """Same data -> identical bytes; LF line endings; sorted keys; trailing newline."""
    mod = _load_script()
    data = {"b": 1, "a": {"z": "°", "y": [1, 2]}}
    first, second = tmp_path / "1.json", tmp_path / "2.json"
    mod.write_json(first, data)
    mod.write_json(second, data)
    raw = first.read_bytes()
    assert raw == second.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw
    assert list(json.loads(raw.decode("utf-8"))) == ["a", "b"]
    assert "°".encode() in raw


def test_facility_json_has_site_and_candidates() -> None:
    """The exported facility carries the site id and all equipment."""
    mod = _load_script()
    data = mod.build_facility_json(load_facility())
    assert data["site"]["id"] == "KS-07"
    assert len(data["equipment"]) == 24


def test_contract_schema_describes_facility_spec() -> None:
    """The JSON Schema is the FacilitySpec model's schema."""
    mod = _load_script()
    schema = mod.build_contract_schema()
    assert schema["title"] == "FacilitySpec"
    assert "equipment" in schema["properties"]
