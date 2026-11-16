"""TEG contactor T-301 (D 1.5 m, H 15 m): column with tray banding, platforms, caged ladder."""

from typing import Any

from parts import mesh_ops
from parts.ladder import ladder
from parts.nozzle import nozzle
from parts.platform import platform, platform_edge, ring_outline
from parts.vessel import vessel
from scene_setup import BuildContext

DIAMETER_M = 1.5
SKIRT_M = 1.5
BAND_RADIUS_EXTRA_M = 0.03
BAND_THICKNESS_M = 0.05
BAND_FIRST_Z_M = 3.0
BAND_SPACING_M = 1.5
PLATFORM_Z_M = (7.0, 13.5)
PLATFORM_REACH_M = 0.9
PLATFORM_SIDES = 16
OPENING_VERTEX = 12
NOZZLE_RADIUS_M = 0.2
NOZZLE_LENGTH_M = 0.5
INLET_Z_M = 2.5
OUTLET_Z_M = 14.0


def _banding(ctx: BuildContext, tag: str, height: float) -> None:
    """Flange rings every 1.5 m from z 3 that suggest the trays."""
    z = BAND_FIRST_Z_M
    while z < height:
        ring = mesh_ops.cylinder(
            f"{tag}_band_{round(z * 10)}",
            DIAMETER_M / 2 + BAND_RADIUS_EXTRA_M,
            BAND_THICKNESS_M,
            (0.0, 0.0, z),
        )
        ctx.add_part(tag, ring, "paint_grey")
        z += BAND_SPACING_M


def _platforms(ctx: BuildContext, tag: str) -> None:
    """Two ring platforms with rails; the ring is open (no rail) on the ladder side, -y."""
    outer = ring_outline(DIAMETER_M / 2 + PLATFORM_REACH_M, PLATFORM_SIDES)
    around = [
        outer[k % PLATFORM_SIDES]
        for k in range(OPENING_VERTEX + 1, OPENING_VERTEX + PLATFORM_SIDES)
    ]
    for z in PLATFORM_Z_M:
        platform(ctx, tag, f"{tag}_deck_{round(z)}", outer, z, hole_radius_m=DIAMETER_M / 2 + 0.02)
        platform_edge(ctx, tag, f"{tag}_edge_{round(z)}", around, z)


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build T-301: skirt, vessel (heads included, z 1.5 to H), banding, platforms, ladder, nozzles.

    The vessel's bottom head hangs inside the skirt (its apex is at the skirt top, z 1.5).

    Args:
        item: Spec item (``type`` ``teg_contactor``; no anchors).
        ctx: Build context.
    """
    tag = item["tag"]
    height = item["size_m"][2]
    radius = DIAMETER_M / 2
    ctx.new_root(item)
    skirt = mesh_ops.cylinder(f"{tag}_skirt", radius, SKIRT_M, (0.0, 0.0, SKIRT_M / 2))
    ctx.add_part(tag, skirt, "paint_dark")
    shell = height - SKIRT_M - DIAMETER_M / 2
    vessel(
        ctx,
        tag,
        f"{tag}_vessel",
        DIAMETER_M,
        shell,
        "Z",
        (0.0, 0.0, SKIRT_M + DIAMETER_M / 4 + shell / 2),
    )
    _banding(ctx, tag, height)
    _platforms(ctx, tag)
    base = (0.0, -(radius + PLATFORM_REACH_M + 0.1), 0.0)
    ladder(ctx, tag, f"{tag}_ladder", base, PLATFORM_Z_M[1], -90.0, caged=True)
    nozzle(
        ctx, tag, f"{tag}_inlet", NOZZLE_RADIUS_M, NOZZLE_LENGTH_M, (-radius, 0.0, INLET_Z_M), "-X"
    )
    nozzle(
        ctx, tag, f"{tag}_outlet", NOZZLE_RADIUS_M, NOZZLE_LENGTH_M, (radius, 0.0, OUTLET_Z_M), "+X"
    )
