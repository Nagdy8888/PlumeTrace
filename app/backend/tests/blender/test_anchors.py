"""Tests for scripts/blender/anchors.py (runs in the uv env, no Blender).

Written after the module, so not red-first.
"""

import importlib
import json
import sys
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT

BLENDER_DIR = REPO_ROOT / "scripts" / "blender"
SPEC = REPO_ROOT / "app" / "frontend" / "src" / "shared" / "facility" / "ks07.json"


def _anchors_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import scripts/blender/anchors.py with scripts/blender on sys.path (as in Blender)."""
    monkeypatch.syspath_prepend(str(BLENDER_DIR))
    for name in ("anchors", "layout", "spec_loader"):
        sys.modules.pop(name, None)
    return importlib.import_module("anchors")


def test_anchor_local_of_rotated_item(monkeypatch: pytest.MonkeyPatch) -> None:
    """An anchor 2 m north of an item rotated 90 degrees is 2 m along its local x."""
    mod = _anchors_module(monkeypatch)
    item = {
        "tag": "X-1",
        "position_m": [10, 20, 0],
        "rotation_deg": 90,
        "anchors": [{"id": "X-1.tip", "position_m": [10, 22, 1]}],
    }
    assert mod.anchor_local(item, "tip") == pytest.approx((2, 0, 1), abs=1e-9)


def test_missing_anchor_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Asking for an anchor the item does not have raises ValueError naming it."""
    mod = _anchors_module(monkeypatch)
    with pytest.raises(ValueError, match="X-1.nope"):
        mod.anchor_local({"tag": "X-1", "position_m": [0, 0, 0]}, "nope")


def test_door_anchors_of_the_two_pig_traps_face_opposite_ends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PIG-101's door is at local x -3 and PIG-702's at +3: the builder picks the end by sign."""
    mod = _anchors_module(monkeypatch)
    items = {i["tag"]: i for i in json.loads(SPEC.read_text(encoding="utf-8"))["equipment"]}
    assert mod.anchor_local(items["PIG-101"], "door")[0] == pytest.approx(-3.0)
    assert mod.anchor_local(items["PIG-702"], "door")[0] == pytest.approx(3.0)
