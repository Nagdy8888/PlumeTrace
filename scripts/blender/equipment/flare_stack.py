"""Flare stack FL-601 (1 x 1 x 30 m) with the flare tip as the separate node ``FL-601__tip``.

The tip node has its origin at z 28.5 (the top of the stack); its wind shield ring's top centre is
the ``FL-601.tip`` anchor (z 30.0).
"""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.ladder import ladder
from parts.platform import platform, platform_edge, ring_outline
from parts.shapes import rod
from scene_setup import BuildContext

BASE_PLATE_M = (2.0, 2.0, 0.1)
R_LOW_M, R_MID_M, R_TOP_M = 0.5, 0.4, 0.3
Z_LOW_END_M = 10.0  # section boundaries (the cone transitions are centred on them)
Z_MID_END_M = 20.0
Z_TOP_M = 28.5
TRANSITION_M = 0.5
BANDS_FROM_M = 19.5  # the top 9 m are banded in six 1.5 m sections
BAND_M = 1.5
BAND_EXTRA_M = 0.005
PLATFORMS_M = (15.0, 28.0)
PLATFORM_RADIUS_M = 1.4
PLATFORM_SIDES = 16
OPENING_VERTEX = 12
LADDER_TOP_Z_M = 28.0
PILOT_RADIUS_M = 0.025
PILOT_Y_M = 0.6
TIP_RADIUS_M = 0.35
TIP_Z_M = (28.5, 29.8)
SHIELD_RADIUS_M = 0.45
SHIELD_HEIGHT_M = 0.4  # its top is the anchor


def _span(
    ctx: BuildContext, tag: str, name: str, r: float, z0: float, z1: float, material: str
) -> None:
    """Cylinder section between two heights."""
    section = mesh_ops.cylinder(f"{tag}_{name}", r, z1 - z0, (0.0, 0.0, (z0 + z1) / 2))
    ctx.add_part(tag, section, material)


def _taper(
    ctx: BuildContext, tag: str, name: str, r0: float, r1: float, zc: float, material: str
) -> None:
    """Cone transition of 0.5 m centred on height ``zc``: radius ``r0`` below, ``r1`` above."""
    cone = mesh_ops.cone(f"{tag}_{name}", r0, r1, TRANSITION_M, (0.0, 0.0, zc))
    ctx.add_part(tag, cone, material)


def _stack(ctx: BuildContext, tag: str) -> None:
    """Steel sections with cone transitions; the top 9 m are alternating red and white bands."""
    half = TRANSITION_M / 2
    _span(ctx, tag, "low", R_LOW_M, BASE_PLATE_M[2], Z_LOW_END_M - half, "paint_grey")
    _taper(ctx, tag, "taper_1", R_LOW_M, R_MID_M, Z_LOW_END_M, "paint_grey")
    _span(ctx, tag, "mid", R_MID_M, Z_LOW_END_M + half, BANDS_FROM_M, "paint_grey")
    for i in range(6):
        material = "paint_red" if i % 2 == 1 else "paint_white"  # the top band (i = 5) is red
        z0, z1 = BANDS_FROM_M + i * BAND_M, BANDS_FROM_M + (i + 1) * BAND_M
        if i == 0:  # the first band also covers the 0.4 -> 0.3 transition at z 20
            _span(ctx, tag, "band_0_mid", R_MID_M + BAND_EXTRA_M, z0, Z_MID_END_M - half, material)
            _taper(
                ctx,
                tag,
                "band_0_taper",
                R_MID_M + BAND_EXTRA_M,
                R_TOP_M + BAND_EXTRA_M,
                Z_MID_END_M,
                material,
            )
            z0 = Z_MID_END_M + half
        _span(ctx, tag, f"band_{i}", R_TOP_M + BAND_EXTRA_M, z0, min(z1, Z_TOP_M), material)


def _access(ctx: BuildContext, tag: str) -> None:
    """Two ring platforms, the caged ladder on -y and the pilot gas line with three clamps."""
    outer = ring_outline(PLATFORM_RADIUS_M, PLATFORM_SIDES)
    around = [
        outer[k % PLATFORM_SIDES]
        for k in range(OPENING_VERTEX + 1, OPENING_VERTEX + PLATFORM_SIDES)
    ]
    for z in PLATFORMS_M:
        r = R_MID_M if z < Z_MID_END_M else R_TOP_M
        platform(ctx, tag, f"{tag}_deck_{round(z)}", outer, z, hole_radius_m=r + 0.02)
        platform_edge(ctx, tag, f"{tag}_edge_{round(z)}", around, z)
    base = (0.0, -(PLATFORM_RADIUS_M + 0.1), 0.0)
    ladder(ctx, tag, f"{tag}_ladder", base, LADDER_TOP_Z_M, -90.0, caged=True)
    pilot = rod(f"{tag}_pilot", (0.0, PILOT_Y_M, 0.5), (0.0, PILOT_Y_M, Z_TOP_M), PILOT_RADIUS_M)
    ctx.add_part(tag, pilot, "pipe_gas")
    for z in (5.0, 15.0, 25.0):
        clamp = mesh_ops.box(
            f"{tag}_clamp_{round(z)}", (0.06, 0.3, 0.06), (0.0, PILOT_Y_M - 0.15, z)
        )
        ctx.add_part(tag, clamp, "paint_dark")


def _tip(ctx: BuildContext, item: dict[str, Any]) -> None:
    """The separate node ``<tag>__tip``: burner tip cylinder and the open wind shield ring.

    The ring's top centre is placed at the ``<tag>.tip`` anchor.
    """
    tag = item["tag"]
    z0, z1 = TIP_Z_M
    node = ctx.new_node(tag, "tip", (0.0, 0.0, z0))
    cylinder = mesh_ops.cylinder(
        f"{tag}_tip_body", TIP_RADIUS_M, z1 - z0, (0.0, 0.0, (z1 - z0) / 2)
    )
    ctx.add_node_part(node, cylinder, "paint_dark")
    top = anchor_local(item, "tip")[2]
    centre = top - SHIELD_HEIGHT_M / 2 - z0  # relative to the node pivot
    ring = mesh_ops.tube(
        f"{tag}_shield", SHIELD_RADIUS_M, 0.03, SHIELD_HEIGHT_M, (0.0, 0.0, centre)
    )
    ctx.add_node_part(node, ring, "paint_grey")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build FL-601: base plate, stack with aviation bands, platforms, ladder, pilot line, tip node.

    Args:
        item: Spec item (``type`` ``flare_stack``; anchor ``tip`` at local ``(0, 0, 30)``).
        ctx: Build context.
    """
    tag = item["tag"]
    ctx.new_root(item)
    plate = mesh_ops.box(f"{tag}_base", BASE_PLATE_M, (0.0, 0.0, BASE_PLATE_M[2] / 2))
    ctx.add_part(tag, plate, "paint_dark")
    _stack(ctx, tag)
    _access(ctx, tag)
    _tip(ctx, item)
