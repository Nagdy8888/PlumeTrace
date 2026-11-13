"""The exported JSON Schema must give json-schema-to-typescript fixed-length number tuples."""

import importlib.util
import json
from types import ModuleType

import pytest

from plumetrace.config import REPO_ROOT


def _load_script() -> ModuleType:
    """Import scripts/export_contract.py as a module."""
    path = REPO_ROOT / "scripts" / "export_contract.py"
    spec = importlib.util.spec_from_file_location("export_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_has_no_prefix_items() -> None:
    """The 2020-12 keyword prefixItems is rewritten; the type generator ignores it."""
    mod = _load_script()
    assert "prefixItems" not in json.dumps(mod.build_contract_schema())


def test_vec3_is_a_fixed_number_tuple() -> None:
    """A position is three numbers: items array plus minItems and maxItems of 3."""
    mod = _load_script()
    schema = mod.build_contract_schema()
    p = schema["$defs"]["Anchor"]["properties"]["position_m"]
    assert p["items"] == [{"type": "number"}] * 3
    assert p["minItems"] == p["maxItems"] == 3


def test_rewrite_rejects_items_next_to_prefix_items() -> None:
    """A node with both keywords would lose one of them silently, so it is an error."""
    mod = _load_script()
    with pytest.raises(ValueError):
        mod._tuples_as_items({"prefixItems": [], "items": {}})


def test_generated_contract_ts_has_no_unknown() -> None:
    """The committed TypeScript types hold [number, number, number], never unknown."""
    path = REPO_ROOT / "app/frontend/src/shared/types/generated/contract.ts"
    text = path.read_text(encoding="utf-8")
    assert "unknown" not in text
    assert "[number, number, number]" in text
