"""Item-local position of a spec anchor (pure, no ``bpy``).

Builders place geometry so that a named part touches the anchor; the anchor itself always sits at
the spec position (``export.add_anchors``), never at a computed one.
"""

from typing import Any

from layout import Vec3, to_local
from spec_loader import anchors_of


def anchor_local(item: dict[str, Any], suffix: str) -> Vec3:
    """Item-local position of the anchor ``<tag>.<suffix>``.

    Args:
        item: Spec item with ``tag``, ``position_m``, ``rotation_deg`` and ``anchors``.
        suffix: Anchor name after the tag, e.g. ``"packing"`` or ``"door"``.

    Returns:
        The anchor position in the item's local frame, in metres.

    Raises:
        ValueError: If the item has no such anchor.
    """
    wanted = f"{item['tag']}.{suffix}"
    for anchor_id, world in anchors_of(item):
        if anchor_id == wanted:
            return to_local(item, world)
    raise ValueError(f"anchor {wanted} missing from the spec")
