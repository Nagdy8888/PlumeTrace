"""Storage tanks TK-401 and TK-402 (D 6 m, H 7 m): cone roof, thief hatch, straight stair."""

import math
from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.handrail import handrail_path
from parts.nozzle import nozzle
from parts.platform import platform, platform_edge
from parts.shapes import tilt
from scene_setup import BuildContext

RADIUS_M = 3.0
ROOF_RISE_M = 0.5  # shell top is H - 0.5
ROOF_EAVE_RADIUS_M = 3.05
HATCH_SIZE_M = (0.4, 0.4, 0.15)
LID_SIZE_M = (0.45, 0.45, 0.03)
LID_TILT_DEG = 5.0
STAIR_STEP_M = 0.25  # one tread per 0.25 m of run and of rise (45 degrees)
STAIR_WIDTH_M = 0.9
STAIR_Y_M = -3.6
TREAD_THICKNESS_M = 0.04
PLATFORM_X_M = (-0.5, 0.5)
PLATFORM_Y_M = (-4.35, -2.85)
NOZZLE_RADIUS_M = 0.15
NOZZLE_LENGTH_M = 0.4
NOZZLE_Z_M = 0.5


def _roof(ctx: BuildContext, item: dict[str, Any]) -> None:
    """Cone roof frustum up to the hatch seat, the thief hatch box and its tilted lid.

    The roof ends in a 0.25 m radius flat on which the hatch stands, so that the lid top is the
    ``<tag>.thief_hatch`` anchor.
    """
    tag = item["tag"]
    top = anchor_local(item, "thief_hatch")[2]
    seat = top - HATCH_SIZE_M[2] - LID_SIZE_M[2]
    eave = item["size_m"][2] - ROOF_RISE_M
    depth = seat - eave
    roof = mesh_ops.cone(
        f"{tag}_roof", ROOF_EAVE_RADIUS_M, 0.25, depth, (0.0, 0.0, eave + depth / 2)
    )
    ctx.add_part(tag, roof, "paint_dark")
    hatch = mesh_ops.box(f"{tag}_hatch", HATCH_SIZE_M, (0.0, 0.0, seat + HATCH_SIZE_M[2] / 2))
    ctx.add_part(tag, hatch, "paint_grey")
    lid = mesh_ops.box(f"{tag}_lid", LID_SIZE_M, (0.0, 0.0, top - LID_SIZE_M[2] / 2))
    tilt(lid, y_deg=LID_TILT_DEG)
    ctx.add_part(tag, lid, "paint_grey")


def _stair(ctx: BuildContext, tag: str, rise: float) -> None:
    """Straight 45 degree stair on the -y side: stringers, treads and a handrail on both sides."""
    top_x = PLATFORM_X_M[0]
    steps = round(rise / STAIR_STEP_M)
    run = steps * STAIR_STEP_M
    bottom_x = top_x - run
    length = math.hypot(run, rise)
    for sign, label in ((-1, "s"), (1, "n")):
        y = STAIR_Y_M + sign * STAIR_WIDTH_M / 2
        stringer = mesh_ops.box(
            f"{tag}_stringer_{label}",
            (length, 0.05, 0.25),
            ((bottom_x + top_x) / 2, y, rise / 2 - 0.12),
        )
        tilt(stringer, y_deg=-45.0)
        ctx.add_part(tag, stringer, "paint_dark")
        handrail_path(ctx, tag, f"{tag}_stair_rail_{label}", [(bottom_x, y, 0.0), (top_x, y, rise)])
    for i in range(1, steps + 1):
        x = bottom_x + (i - 0.5) * STAIR_STEP_M
        size = (STAIR_STEP_M + 0.03, STAIR_WIDTH_M, TREAD_THICKNESS_M)
        tread = mesh_ops.box(
            f"{tag}_tread_{i}", size, (x, STAIR_Y_M, i * STAIR_STEP_M - TREAD_THICKNESS_M / 2)
        )
        ctx.add_part(tag, tread, "grating", tile_m=1.0)


def _landing(ctx: BuildContext, tag: str, rise: float) -> None:
    """The 1.0 x 1.5 m roof platform at the shell edge with rails on its three free sides."""
    (x0, x1), (y0, y1) = PLATFORM_X_M, PLATFORM_Y_M
    platform(ctx, tag, f"{tag}_landing", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], rise)
    platform_edge(ctx, tag, f"{tag}_landing_edge", [(x0, y1), (x1, y1), (x1, y0), (x0, y0)], rise)


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build a tank: shell, cone roof with thief hatch, stair to a roof platform, side nozzle.

    Args:
        item: Spec item (``type`` ``storage_tank``; anchor ``thief_hatch`` at local ``(0, 0, H)``).
        ctx: Build context.
    """
    tag = item["tag"]
    height = item["size_m"][2]
    shell = height - ROOF_RISE_M
    ctx.new_root(item)
    body = mesh_ops.cylinder(f"{tag}_shell", RADIUS_M, shell, (0.0, 0.0, shell / 2))
    ctx.add_part(tag, body, "paint_white")
    _roof(ctx, item)
    _stair(ctx, tag, shell)
    _landing(ctx, tag, shell)
    nozzle(
        ctx,
        tag,
        f"{tag}_nozzle",
        NOZZLE_RADIUS_M,
        NOZZLE_LENGTH_M,
        (-RADIUS_M, 0.0, NOZZLE_Z_M),
        "-X",
    )
