"""Spec (world) to item-local coordinates (pure maths, no ``bpy``).

Rotation is about z, counter-clockwise, in degrees (``rotation_deg`` of the spec item).
"""

import math
from typing import Any

Vec3 = tuple[float, float, float]


def _rotate_z(p: Vec3, deg: float) -> Vec3:
    """Rotate ``p`` counter-clockwise about z by ``deg`` degrees."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])


def to_local(item: dict[str, Any], world: Vec3) -> Vec3:
    """Convert a world position to the item's local frame (subtract position, rotate by -rotation).

    Args:
        item: Spec item with ``position_m`` and ``rotation_deg``.
        world: World position in metres.

    Returns:
        The local position in metres.
    """
    px, py, pz = item["position_m"]
    shifted = (world[0] - px, world[1] - py, world[2] - pz)
    return _rotate_z(shifted, -float(item.get("rotation_deg", 0.0)))


def to_world(item: dict[str, Any], local: Vec3) -> Vec3:
    """Convert an item-local position to world coordinates (inverse of :func:`to_local`).

    Args:
        item: Spec item with ``position_m`` and ``rotation_deg``.
        local: Local position in metres.

    Returns:
        The world position in metres.
    """
    x, y, z = _rotate_z(local, float(item.get("rotation_deg", 0.0)))
    px, py, pz = item["position_m"]
    return (x + px, y + py, z + pz)


def ao_resolution(equipment_type: str, level: str) -> int:
    """Pixel size of an item's baked ambient-occlusion image (keeps texture memory in budget).

    Args:
        equipment_type: Spec ``EquipmentType`` value, or ``"ground"`` for the ground patch.
        level: Bake quality, ``"low"`` or ``"high"``.

    Returns:
        256 for ``"low"``; for ``"high"`` 1024 for ``recip_compressor`` and ``ground``, else 512.

    Raises:
        ValueError: If ``level`` is neither ``"low"`` nor ``"high"``.
    """
    if level == "low":
        return 256
    if level == "high":
        return 1024 if equipment_type in ("recip_compressor", "ground") else 512
    raise ValueError(f"unknown bake level {level!r}")
