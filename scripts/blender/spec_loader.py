"""Read the exported facility spec (``ks07.json``) for the Blender build.

Pure stdlib, no ``bpy``: Blender's bundled Python has no uv environment, and these helpers are
unit-tested from the uv environment.
"""

import json
from pathlib import Path
from typing import Any


def load_spec(path: Path) -> dict[str, Any]:
    """Load the facility spec JSON.

    Args:
        path: Path to ``ks07.json``.

    Returns:
        The parsed spec.

    Raises:
        ValueError: If the document has no ``equipment`` list.
    """
    spec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if "equipment" not in spec:
        raise ValueError("not a facility spec: missing equipment")
    return spec


def select_equipment(spec: dict[str, Any], only: frozenset[str] | None) -> list[dict[str, Any]]:
    """Pick equipment items in spec order.

    Args:
        spec: The facility spec.
        only: Tags to keep, or ``None`` for every item.

    Returns:
        The selected equipment items, in spec order.

    Raises:
        ValueError: If a tag in ``only`` is not in the spec.
    """
    items: list[dict[str, Any]] = spec["equipment"]
    if only is None:
        return list(items)
    known = {item["tag"] for item in items}
    for tag in sorted(only):
        if tag not in known:
            raise ValueError(f"unknown tag {tag}")
    return [item for item in items if item["tag"] in only]


def anchors_of(item: dict[str, Any]) -> list[tuple[str, tuple[float, float, float]]]:
    """List the anchors of an equipment item.

    Args:
        item: One equipment item of the spec.

    Returns:
        ``(anchor id, position_m)`` pairs in spec order.
    """
    return [
        (a["id"], (float(a["position_m"][0]), float(a["position_m"][1]), float(a["position_m"][2])))
        for a in item.get("anchors", [])
    ]
