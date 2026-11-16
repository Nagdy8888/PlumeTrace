"""Vertical gas separator shared by the filter separator V-100 and the scrubbers V-211..213."""

import math
from typing import Any

from anchors import anchor_local
from scene_setup import BuildContext

from parts import mesh_ops
from parts.flange import flange
from parts.ladder import ladder
from parts.nozzle import nozzle
from parts.platform import platform, platform_edge, ring_outline
from parts.vessel import vessel

SKIRT_M = 0.8
PSV_RADIUS_M = 0.1
NOZZLE_RADIUS_M = 0.3
NOZZLE_LENGTH_M = 0.5
INLET_Z_M = 2.2
OUTLET_Z_M = 4.2
GAUGE_RADIUS_M = 0.04
GAUGE_Z_M = (1.5, 3.5)
GAUGE_OFFSET_M = 0.15
PLATFORM_REACH_M = 0.9  # platform ring outer radius = D/2 + this
PLATFORM_DROP_M = 0.6  # platform top face below the item height
PLATFORM_SIDES = 16
LADDER_STANDOFF_M = 0.2  # uncaged ladder, from the shell
OPENING_VERTEX = 12  # the platform ring has no rail around the vertex on -y (270 degrees)


def _nozzles(ctx: BuildContext, tag: str, radius: float, shell_top: float) -> None:
    """Inlet nozzle facing -x, outlet nozzle facing +x (kept 0.5 m below the shell top)."""
    outlet_z = min(OUTLET_Z_M, shell_top - NOZZLE_LENGTH_M)
    for label, sign, z in (("inlet", -1, INLET_Z_M), ("outlet", 1, outlet_z)):
        direction = "+X" if sign > 0 else "-X"
        nozzle(
            ctx,
            tag,
            f"{tag}_{label}",
            NOZZLE_RADIUS_M,
            NOZZLE_LENGTH_M,
            (sign * radius, 0.0, z),
            direction,
        )


def _gauge(ctx: BuildContext, tag: str, radius: float) -> None:
    """Level gauge column on +y with two stubs to the shell."""
    y = radius + GAUGE_OFFSET_M
    z0, z1 = GAUGE_Z_M
    column = mesh_ops.cylinder(f"{tag}_gauge", GAUGE_RADIUS_M, z1 - z0, (0.0, y, (z0 + z1) / 2))
    ctx.add_part(tag, column, "paint_dark")
    for z in GAUGE_Z_M:
        stub = mesh_ops.cylinder(
            f"{tag}_gauge_stub_{round(z * 10)}",
            GAUGE_RADIUS_M,
            GAUGE_OFFSET_M,
            (0.0, radius + GAUGE_OFFSET_M / 2, z),
            axis="Y",
        )
        ctx.add_part(tag, stub, "paint_dark")


def _top_platform(
    ctx: BuildContext, tag: str, radius: float, top_head_z: float, height: float
) -> float:
    """Ring platform around the top head with rails, toe plates and the ladder opening on -y.

    Returns:
        The item-local height of the platform's top face.
    """
    z = height - PLATFORM_DROP_M
    outer = ring_outline(radius + PLATFORM_REACH_M, PLATFORM_SIDES)
    depth = radius / 2  # head depth D/4
    rise = min(max(z - top_head_z + depth, 0.0), depth)
    hole = radius * math.sqrt(max(1 - (rise / depth) ** 2, 0.0)) + 0.02
    platform(ctx, tag, f"{tag}_deck", outer, z, hole_radius_m=hole)
    around = [
        outer[k % PLATFORM_SIDES]
        for k in range(OPENING_VERTEX + 1, OPENING_VERTEX + PLATFORM_SIDES)
    ]
    platform_edge(ctx, tag, f"{tag}_edge", around, z)
    return z


def build_separator(item: dict[str, Any], ctx: BuildContext, with_platform: bool) -> None:
    """Build a vertical separator: skirt, vessel with heads, PSV, nozzles, gauge, ladder.

    The vessel's bottom head hangs inside the skirt; the PSV rises from the top head to the item
    height ``H`` (its top is the ``<tag>.psv`` anchor). With ``with_platform`` the item gets a
    ring platform near the top and a caged ladder to it; otherwise an uncaged ladder to ``H - 0.6``.

    Args:
        item: Spec item (``size_m`` = ``D, D, H``; anchor ``psv`` at local ``(0, 0, H)``).
        ctx: Build context.
        with_platform: Add the top platform and the caged ladder.
    """
    tag = item["tag"]
    diameter, _, height = item["size_m"]
    radius = diameter / 2
    ctx.new_root(item)
    skirt = mesh_ops.cylinder(f"{tag}_skirt", radius, SKIRT_M, (0.0, 0.0, SKIRT_M / 2))
    ctx.add_part(tag, skirt, "paint_dark")
    shell = height - SKIRT_M - diameter / 2
    vessel(ctx, tag, f"{tag}_vessel", diameter, shell, "Z", (0.0, 0.0, SKIRT_M + shell / 2))
    top_head_z = SKIRT_M + shell + diameter / 4
    psv_top = anchor_local(item, "psv")[2]
    psv = mesh_ops.cylinder(
        f"{tag}_psv", PSV_RADIUS_M, psv_top - top_head_z, (0.0, 0.0, (psv_top + top_head_z) / 2)
    )
    ctx.add_part(tag, psv, "paint_grey")
    flange(ctx, tag, f"{tag}_psv_flange", PSV_RADIUS_M, (0.0, 0.0, top_head_z + 0.1))
    _nozzles(ctx, tag, radius, SKIRT_M + shell)
    _gauge(ctx, tag, radius)
    if with_platform:
        deck_z = _top_platform(ctx, tag, radius, top_head_z, height)
        base = (0.0, -(radius + PLATFORM_REACH_M + 0.1), 0.0)
        ladder(ctx, tag, f"{tag}_ladder", base, deck_z, -90.0, caged=True)
    else:
        base = (0.0, -(radius + LADDER_STANDOFF_M), 0.0)
        ladder(ctx, tag, f"{tag}_ladder", base, height - PLATFORM_DROP_M, -90.0, caged=False)
        for z in (1.2, 3.0, 4.0):
            bracket = mesh_ops.box(
                f"{tag}_bracket_{round(z * 10)}",
                (0.5, LADDER_STANDOFF_M, 0.05),
                (0.0, -(radius + LADDER_STANDOFF_M / 2 - 0.02), z),
            )
            ctx.add_part(tag, bracket, "paint_grey")
