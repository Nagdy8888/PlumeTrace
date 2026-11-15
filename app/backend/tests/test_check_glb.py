"""Tests for scripts/check_glb.py (builds a tiny GLB in memory, no Blender)."""

import importlib.util
import json
import struct
from pathlib import Path
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT

FACILITY_JSON = REPO_ROOT / "app/frontend/src/shared/facility/ks07.json"
JSON_CHUNK = 0x4E4F534A
ALL_K202 = ["K-202", "K-202.packing", "K-202.engine_exhaust"]


def _load() -> ModuleType:
    """Import scripts/check_glb.py by file path."""
    path = REPO_ROOT / "scripts" / "check_glb.py"
    spec = importlib.util.spec_from_file_location("check_glb", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _glb(path: Path, names: list[str], magic: bytes = b"glTF") -> Path:
    """Write a minimal GLB (header + one JSON chunk padded with spaces) with the node names."""
    doc = json.dumps({"asset": {"version": "2.0"}, "nodes": [{"name": n} for n in names]})
    body = doc.encode("utf-8")
    body += b" " * (-len(body) % 4)
    header = magic + struct.pack("<II", 2, 12 + 8 + len(body))
    path.write_bytes(header + struct.pack("<II", len(body), JSON_CHUNK) + body)
    return path


def test_required_names_include_anchors() -> None:
    """Required names are the tag plus every anchor id."""
    mod = _load()
    spec = json.loads(FACILITY_JSON.read_text(encoding="utf-8"))
    assert mod.required_names(spec, frozenset({"K-202"})) == set(ALL_K202)


def test_missing_anchor_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A glb without an anchor node returns 1 and names it."""
    mod = _load()
    glb = _glb(tmp_path / "a.glb", ["K-202", "K-202.packing"])
    code = mod.main(["--glb", str(glb), "--spec", str(FACILITY_JSON), "--only", "K-202"])
    assert code == 1
    assert "missing nodes: ['K-202.engine_exhaust']" in capsys.readouterr().out


def test_complete_glb_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A glb with every required node returns 0."""
    mod = _load()
    glb = _glb(tmp_path / "a.glb", ALL_K202)
    code = mod.main(["--glb", str(glb), "--spec", str(FACILITY_JSON), "--only", "K-202"])
    assert code == 0
    assert capsys.readouterr().out.startswith("glb OK: 3 nodes,")


def test_bad_magic_is_rejected(tmp_path: Path) -> None:
    """A file that does not start with glTF raises ValueError."""
    mod = _load()
    glb = _glb(tmp_path / "b.glb", ["K-202"], magic=b"glTX")
    with pytest.raises(ValueError, match="magic"):
        mod.read_glb_json(glb)


def test_size_budget(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--max-bytes 10 fails on any real file."""
    mod = _load()
    glb = _glb(tmp_path / "a.glb", ALL_K202)
    argv = ["--glb", str(glb), "--spec", str(FACILITY_JSON), "--only", "K-202", "--max-bytes", "10"]
    assert mod.main(argv) == 1
    assert "budget 10" in capsys.readouterr().out
