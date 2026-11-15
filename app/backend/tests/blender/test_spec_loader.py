"""Tests for scripts/blender/spec_loader.py (runs in the uv env, no Blender)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT

FACILITY_JSON = REPO_ROOT / "app/frontend/src/shared/facility/ks07.json"


def _load(name: str) -> ModuleType:
    """Import a module from scripts/blender by file path."""
    path = REPO_ROOT / "scripts" / "blender" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"blender_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selects_spike_equipment_in_spec_order() -> None:
    """The spike selection returns K-202 and VS-250 with their anchors."""
    mod = _load("spec_loader")
    spec = mod.load_spec(FACILITY_JSON)
    items = mod.select_equipment(spec, frozenset({"VS-250", "K-202"}))
    assert [i["tag"] for i in items] == ["K-202", "VS-250"]
    assert ("VS-250.tip", (85.0, 115.0, 12.0)) in [
        (a, tuple(p)) for a, p in mod.anchors_of(items[1])
    ]


def test_unknown_tag_is_rejected() -> None:
    """A typo in --only fails loudly."""
    mod = _load("spec_loader")
    with pytest.raises(ValueError, match="unknown tag K-999"):
        mod.select_equipment(mod.load_spec(FACILITY_JSON), frozenset({"K-999"}))


def test_rejects_non_spec_json(tmp_path: Path) -> None:
    """A JSON file without equipment is not a facility spec."""
    mod = _load("spec_loader")
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing equipment"):
        mod.load_spec(p)
