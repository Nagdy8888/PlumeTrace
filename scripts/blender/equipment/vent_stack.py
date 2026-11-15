"""Vent stack VS-250: base plate, flanged stack, flame arrestor, open tip and guy-wire lugs."""

import math
from typing import Any

from parts import mesh_ops
from parts.flange import flange
from scene_setup import BuildContext

STACK_RADIUS_M = 0.2
BASE_M = 0.05
ARRESTOR_BOTTOM_M = 11.2
STACK_TOP_M = 11.7
TIP_TOP_M = 12.0


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build VS-250 (12 m vent stack, open tip at z 12.0).

    Args:
        item: Spec item (``type`` ``vent_stack``).
        ctx: Build context.
    """
    tag = item["tag"]
    ctx.new_root(item)
    plate = mesh_ops.box(f"{tag}_base", (1.0, 1.0, BASE_M), (0.0, 0.0, BASE_M / 2))
    ctx.add_part(tag, plate, "paint_dark")
    length = STACK_TOP_M - BASE_M
    stack = mesh_ops.cylinder(
        f"{tag}_stack", STACK_RADIUS_M, length, (0.0, 0.0, BASE_M + length / 2)
    )
    ctx.add_part(tag, stack, "paint_grey")
    for z in (3.0, 6.0, 9.0):
        flange(ctx, tag, f"{tag}_flange_{int(z)}", STACK_RADIUS_M, (0.0, 0.0, z))
    mid = (ARRESTOR_BOTTOM_M + STACK_TOP_M) / 2
    arrestor = mesh_ops.cylinder(
        f"{tag}_arrestor", 0.3, STACK_TOP_M - ARRESTOR_BOTTOM_M, (0.0, 0.0, mid)
    )
    ctx.add_part(tag, arrestor, "paint_grey")
    tip = mesh_ops.tube(
        f"{tag}_tip", 0.22, 0.04, TIP_TOP_M - STACK_TOP_M, (0.0, 0.0, (STACK_TOP_M + TIP_TOP_M) / 2)
    )
    ctx.add_part(tag, tip, "paint_grey")
    for i in range(3):
        angle = math.radians(90 + 120 * i)
        at = (0.24 * math.cos(angle), 0.24 * math.sin(angle), 9.0)
        lug = mesh_ops.box(f"{tag}_lug_{i}", (0.08, 0.08, 0.12), at, math.degrees(angle))
        ctx.add_part(tag, lug, "paint_dark")
    stub = mesh_ops.cylinder(f"{tag}_inlet", 0.1, 1.0, (0.0, -0.5, 0.2), axis="Y")
    ctx.add_part(tag, stub, "paint_grey")
