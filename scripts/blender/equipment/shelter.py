"""Open-sided steel shelter with a corrugated roof (for items with ``shelter: true``)."""

import math
from typing import Any

from parts import mesh_ops
from scene_setup import BuildContext

COLUMN_M = 0.24
COLUMN_X_M = (-7.0, 0.0, 7.0)
COLUMN_Y_M = (-3.7, 3.7)
ROOF_Z_M = 5.0
ROOF_PITCH_DEG = 5.0
ROOF_THICKNESS_M = 0.06
BEAM_HEIGHT_M = 0.2
WALL_BOTTOM_Z_M = 2.5


def _roof_z(y_m: float) -> float:
    """Height of the roof centre plane above the item origin at item-local ``y_m``."""
    return ROOF_Z_M + y_m * math.tan(math.radians(ROOF_PITCH_DEG))


def _frame(ctx: BuildContext, tag: str) -> None:
    """Six HEA-proxy columns and two eaves beams, topped to meet the pitched roof."""
    for y in COLUMN_Y_M:
        top = _roof_z(y) - ROOF_THICKNESS_M / 2 - BEAM_HEIGHT_M
        for i, x in enumerate(COLUMN_X_M):
            size = (COLUMN_M, COLUMN_M, top)
            col = mesh_ops.box(f"{tag}_col_{i}_{'n' if y > 0 else 's'}", size, (x, y, top / 2))
            ctx.add_part(tag, col, "paint_dark")
        beam = mesh_ops.box(
            f"{tag}_eave_{'n' if y > 0 else 's'}",
            (COLUMN_X_M[-1] - COLUMN_X_M[0] + COLUMN_M, COLUMN_M, BEAM_HEIGHT_M),
            (0.0, y, top + BEAM_HEIGHT_M / 2),
        )
        ctx.add_part(tag, beam, "paint_dark")


def build_shelter(item: dict[str, Any], ctx: BuildContext) -> None:
    """Add the shelter parts to the item (they join into the item's node at export).

    Args:
        item: Spec item with ``shelter: true``; its root already exists.
        ctx: Build context.
    """
    tag = item["tag"]
    _frame(ctx, tag)
    roof = mesh_ops.box(f"{tag}_roof", (15.0, 8.4, ROOF_THICKNESS_M), (0.0, 0.0, ROOF_Z_M))
    roof.rotation_euler = (math.radians(ROOF_PITCH_DEG), 0.0, 0.0)
    ctx.add_part(tag, roof, "cladding")
    wall_y = COLUMN_Y_M[1] + COLUMN_M / 2 + 0.025
    wall_top = _roof_z(wall_y) - ROOF_THICKNESS_M / 2 - BEAM_HEIGHT_M / 2
    height = wall_top - WALL_BOTTOM_Z_M
    wall = mesh_ops.box(
        f"{tag}_wall", (15.0, 0.05, height), (0.0, wall_y, WALL_BOTTOM_Z_M + height / 2)
    )
    ctx.add_part(tag, wall, "cladding")
