"""Pig launcher / receiver PIG-101 and PIG-702 (6 x 1.2 x 1.5 m).

The closure door is at the end whose sign matches the local x of the ``<tag>.door`` anchor
(PIG-101: -x, PIG-702: +x); the reducer and the line stub are at the other end.
"""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.flange import flange
from parts.nozzle import nozzle
from parts.saddle import saddle
from parts.valve import valve
from parts.vessel import vessel
from scene_setup import BuildContext

BARREL_DIAMETER_M = 0.6
CENTRE_Z_M = 1.0
REDUCER_LENGTH_M = 0.4
LINE_RADIUS_M = 0.2
LINE_LENGTH_M = 0.8
DOOR_RADIUS_M = 0.425
DOOR_THICKNESS_M = 0.15
KICKER_RADIUS_M = 0.05
KICKER_RISE_M = 0.3
KICKER_REACH_M = 0.5
PAD_M = 0.2


def _end_fittings(ctx: BuildContext, item: dict[str, Any], door_x: float, sign: int) -> None:
    """Closure door at the anchor, then (at the far end) reducer and the flanged line stub."""
    tag = item["tag"]
    door = mesh_ops.cylinder(
        f"{tag}_door", DOOR_RADIUS_M, DOOR_THICKNESS_M, (door_x, 0.0, CENTRE_Z_M), axis="X"
    )
    ctx.add_part(tag, door, "paint_dark")
    flange(
        ctx,
        tag,
        f"{tag}_door_flange",
        BARREL_DIAMETER_M / 2,
        (door_x - sign * 0.1, 0.0, CENTRE_Z_M),
        axis="X",
    )
    barrel_end = door_x - sign * DOOR_THICKNESS_M / 2 - sign * (item["size_m"][0] - 1.2)
    small, big = LINE_RADIUS_M, BARREL_DIAMETER_M / 2
    far = -sign
    # the cone's -x end is its first radius: small end points away from the barrel
    r_bottom, r_top = (small, big) if far < 0 else (big, small)
    mid = barrel_end + far * REDUCER_LENGTH_M / 2
    reducer = mesh_ops.cone(
        f"{tag}_reducer", r_bottom, r_top, REDUCER_LENGTH_M, (mid, 0.0, CENTRE_Z_M), "X"
    )
    ctx.add_part(tag, reducer, "paint_grey")
    stub_start = barrel_end + far * REDUCER_LENGTH_M
    nozzle(
        ctx,
        tag,
        f"{tag}_line",
        LINE_RADIUS_M,
        LINE_LENGTH_M,
        (stub_start, 0.0, CENTRE_Z_M),
        "+X" if far > 0 else "-X",
    )


def _kicker(ctx: BuildContext, tag: str, x: float) -> None:
    """Kicker line on top of the barrel: a riser, a cross pipe along y and a valve."""
    top = CENTRE_Z_M + BARREL_DIAMETER_M / 2
    z = top + KICKER_RISE_M
    riser = mesh_ops.cylinder(
        f"{tag}_kicker_riser", KICKER_RADIUS_M, KICKER_RISE_M, (x, 0.0, top + KICKER_RISE_M / 2)
    )
    ctx.add_part(tag, riser, "pipe_gas")
    cross = mesh_ops.cylinder(
        f"{tag}_kicker_pipe", KICKER_RADIUS_M, KICKER_REACH_M, (x, KICKER_REACH_M / 2, z), axis="Y"
    )
    ctx.add_part(tag, cross, "pipe_gas")
    valve(ctx, tag, f"{tag}_kicker_valve", KICKER_RADIUS_M, (x, KICKER_REACH_M * 0.6, z), axis="Y")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build a pig trap: pad, barrel, two saddles, door, reducer, line stub and kicker valve.

    Args:
        item: Spec item (``type`` ``pig_trap``; anchor ``door`` at local ``(+-3, 0, 1)``).
        ctx: Build context.
    """
    tag = item["tag"]
    length, width, _ = item["size_m"]
    door_x = anchor_local(item, "door")[0]
    sign = 1 if door_x > 0 else -1
    ctx.new_root(item)
    pad = mesh_ops.box(f"{tag}_pad", (length + 1.0, width + 1.0, PAD_M), (0.0, 0.0, -PAD_M / 2))
    ctx.add_part(tag, pad, "concrete", tile_m=3.0)
    barrel_len = length - 1.2
    barrel_centre = door_x - sign * (DOOR_THICKNESS_M / 2 + barrel_len / 2)
    vessel(
        ctx,
        tag,
        f"{tag}_barrel",
        BARREL_DIAMETER_M,
        barrel_len,
        "X",
        (barrel_centre, 0.0, CENTRE_Z_M),
        heads="none",
    )
    for s, label in ((1, "e"), (-1, "w")):
        saddle(ctx, tag, f"{tag}_saddle_{label}", BARREL_DIAMETER_M, s * length / 4, CENTRE_Z_M)
    _end_fittings(ctx, item, door_x, sign)
    _kicker(ctx, tag, sign * length / 3)
