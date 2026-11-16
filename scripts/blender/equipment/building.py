"""Control room CR-901 and motor control centre MCC-902: panel boxes with a parapet and a door."""

from typing import Any

from parts import mesh_ops
from parts.shapes import block
from scene_setup import BuildContext

PARAPET_M = 0.3
PARAPET_THICKNESS_M = 0.15
DOOR_SIZE_M = (1.0, 0.05, 2.1)
WINDOW_SIZE_M = (1.2, 0.05, 1.0)
WINDOW_Z_M = 1.5  # centre: the windows span z 1.0 to 2.0
WINDOW_SPACING_M = 2.5
HVAC_SIZE_M = (1.5, 1.0, 0.8)
LOUVRE_SIZE_M = (0.05, 1.0, 0.6)
LOUVRE_Y_M = (-1.5, 0.0, 1.5)
LOUVRE_Z_M = 2.0
CONTROL_ROOM_TAG = "CR-901"


def _parapet(ctx: BuildContext, tag: str, length: float, width: float, height: float) -> None:
    """Four wall strips 0.3 m high around the roof edge."""
    t, z = PARAPET_THICKNESS_M, height + PARAPET_M / 2
    strips = (
        ("s", (length, t, PARAPET_M), (0.0, -(width / 2 - t / 2), z)),
        ("n", (length, t, PARAPET_M), (0.0, width / 2 - t / 2, z)),
        ("w", (t, width - 2 * t, PARAPET_M), (-(length / 2 - t / 2), 0.0, z)),
        ("e", (t, width - 2 * t, PARAPET_M), (length / 2 - t / 2, 0.0, z)),
    )
    for label, size, at in strips:
        ctx.add_part(
            tag, mesh_ops.box(f"{tag}_parapet_{label}", size, at), "building_panel", tile_m=3.0
        )


def _openings(ctx: BuildContext, tag: str, length: float, width: float) -> None:
    """Door on the -y wall; the control room also gets windows every 2.5 m (door skipped)."""
    y = -width / 2
    door = mesh_ops.box(f"{tag}_door", DOOR_SIZE_M, (0.0, y, DOOR_SIZE_M[2] / 2))
    ctx.add_part(tag, door, "paint_dark")
    if tag != CONTROL_ROOM_TAG:
        return
    count = int((length / 2 - WINDOW_SIZE_M[0] / 2) / WINDOW_SPACING_M)
    for k in range(-count, count + 1):
        if k == 0:
            continue  # the door
        window = mesh_ops.box(
            f"{tag}_window_{k + count}", WINDOW_SIZE_M, (k * WINDOW_SPACING_M, y, WINDOW_Z_M)
        )
        ctx.add_part(tag, window, "glass")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build a building: panel box, parapet, door, roof HVAC unit; windows (CR-901) or louvres.

    Args:
        item: Spec item (``type`` ``building``; no anchors).
        ctx: Build context.
    """
    tag = item["tag"]
    length, width, height = item["size_m"]
    ctx.new_root(item)
    body = block(f"{tag}_body", (length, width, height), (0.0, 0.0, height / 2))
    ctx.add_part(tag, body, "building_panel", tile_m=3.0)
    _parapet(ctx, tag, length, width, height)
    _openings(ctx, tag, length, width)
    hvac_at = (length / 4, 0.0, height + HVAC_SIZE_M[2] / 2)
    ctx.add_part(tag, block(f"{tag}_hvac", HVAC_SIZE_M, hvac_at), "paint_grey")
    if tag == CONTROL_ROOM_TAG:
        return
    for i, y in enumerate(LOUVRE_Y_M):
        louvre = mesh_ops.box(f"{tag}_louvre_{i}", LOUVRE_SIZE_M, (length / 2, y, LOUVRE_Z_M))
        ctx.add_part(tag, louvre, "paint_dark")
