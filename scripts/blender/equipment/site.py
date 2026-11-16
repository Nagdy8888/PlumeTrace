"""Yard ground, outer terrain, equipment pads, road, tank bund and fence (bpy module).

World frame: x east 0 to 200, y north 0 to 150, z up. The ground, pads, road and bund are joined
into one node ``SITE__ground``; the fence is the node ``SITE__fence``. Parts are placed in world
coordinates because both roots sit at the origin.
"""

from typing import Any

from fence_math import fence_post_xy
from naming import FENCE_TAG, GROUND_TAG
from parts import mesh_ops
from parts.shapes import rod
from scene_setup import BuildContext

YARD_M = (200.0, 150.0)
YARD_Z_M = -0.02  # just under the pad tops (z 0) so they never z-fight
TERRAIN_M = 600.0
TERRAIN_DROP_M = 0.05
PAD_THICKNESS_M = 0.2
PAD_MARGIN_M = 1.0
OWN_PAD_TYPES = frozenset({"recip_compressor", "pig_trap", "building"})
ROAD_Y_M = (9.0, 15.0)
ROAD_THICKNESS_M = 0.05
ROAD_TOP_M = 0.02
BUND_X_M = (144.0, 171.0)
BUND_Y_M = (103.0, 117.0)
BUND_WALL_M = 0.25
BUND_HEIGHT_M = 1.0
POST_SPACING_M = 3.0
POST_RADIUS_M = 0.03
POST_HEIGHT_M = 2.2
RAIL_RADIUS_M = 0.02
RAIL_Z_M = (0.3, 2.1)  # bottom and top rail heights (plan-silent)


def _site_root(ctx: BuildContext, tag: str, kind: str) -> None:
    """Create a world-origin root for a site node (``kind`` picks its AO size in ``layout``)."""
    ctx.new_root({"tag": tag, "type": kind, "position_m": [0.0, 0.0, 0.0], "rotation_deg": 0.0})


def _pads(ctx: BuildContext, items: list[dict[str, Any]]) -> None:
    """Concrete pad (L + 1) x (W + 1) x 0.2 m, top at z 0, under items with no pad of their own."""
    for item in items:
        if item["type"] in OWN_PAD_TYPES:
            continue
        length, width, _ = item["size_m"]
        px, py, _ = item["position_m"]
        size = (length + PAD_MARGIN_M, width + PAD_MARGIN_M, PAD_THICKNESS_M)
        pad = mesh_ops.box(
            f"{item['tag']}_site_pad",
            size,
            (px, py, -PAD_THICKNESS_M / 2),
            float(item.get("rotation_deg", 0.0)),
        )
        ctx.add_part(GROUND_TAG, pad, "concrete", tile_m=3.0)


def _bund(ctx: BuildContext) -> None:
    """Four concrete walls (0.25 m thick, 1 m high) round the two storage tanks."""
    (x0, x1), (y0, y1) = BUND_X_M, BUND_Y_M
    cx, cy, z = (x0 + x1) / 2, (y0 + y1) / 2, BUND_HEIGHT_M / 2
    walls = {
        "south": ((x1 - x0 + BUND_WALL_M, BUND_WALL_M, BUND_HEIGHT_M), (cx, y0, z)),
        "north": ((x1 - x0 + BUND_WALL_M, BUND_WALL_M, BUND_HEIGHT_M), (cx, y1, z)),
        "west": ((BUND_WALL_M, y1 - y0, BUND_HEIGHT_M), (x0, cy, z)),
        "east": ((BUND_WALL_M, y1 - y0, BUND_HEIGHT_M), (x1, cy, z)),
    }
    for side, (size, location) in walls.items():
        ctx.add_part(GROUND_TAG, mesh_ops.box(f"bund_{side}", size, location), "concrete", 3.0)


def build_ground(ctx: BuildContext, items: list[dict[str, Any]], full: bool) -> None:
    """Build the node ``SITE__ground``: yard, outer terrain, pads, road and (full build) the bund.

    Args:
        ctx: Build context.
        items: The equipment items that were built (they get pads).
        full: ``True`` for the whole station (adds the tank bund); a ``--only`` build skips it.
    """
    _site_root(ctx, GROUND_TAG, "ground")
    cx, cy = YARD_M[0] / 2, YARD_M[1] / 2
    yard = mesh_ops.plane("yard", YARD_M, (cx, cy, YARD_Z_M))
    ctx.add_part(GROUND_TAG, yard, "gravel", tile_m=4.0)
    terrain = mesh_ops.plane("terrain", (TERRAIN_M, TERRAIN_M), (cx, cy, YARD_Z_M - TERRAIN_DROP_M))
    ctx.add_part(GROUND_TAG, terrain, "gravel_far", tile_m=8.0)
    _pads(ctx, items)
    y0, y1 = ROAD_Y_M
    road_z = ROAD_TOP_M - ROAD_THICKNESS_M / 2
    road = mesh_ops.box("road", (YARD_M[0], y1 - y0, ROAD_THICKNESS_M), (cx, (y0 + y1) / 2, road_z))
    ctx.add_part(GROUND_TAG, road, "asphalt", tile_m=4.0)
    if full:
        _bund(ctx)


def _fence_rails(ctx: BuildContext) -> None:
    """Top and bottom rails along each side; the west side is split at the gate."""
    width, depth = YARD_M
    gate_lo, gate_hi = ROAD_Y_M
    sides = [
        ((0.0, 0.0), (width, 0.0)),
        ((0.0, depth), (width, depth)),
        ((width, 0.0), (width, depth)),
        ((0.0, 0.0), (0.0, gate_lo)),
        ((0.0, gate_hi), (0.0, depth)),
    ]
    for n, ((x0, y0), (x1, y1)) in enumerate(sides):
        for label, z in zip(("bottom", "top"), RAIL_Z_M, strict=True):
            piece = rod(f"fence_rail_{n}_{label}", (x0, y0, z), (x1, y1, z), RAIL_RADIUS_M)
            ctx.add_part(FENCE_TAG, piece, "paint_grey")


def build_fence(ctx: BuildContext) -> None:
    """Build the node ``SITE__fence``: posts every 3 m, two rails, a gate gap at x 0, y 9 to 15.

    Args:
        ctx: Build context.
    """
    _site_root(ctx, FENCE_TAG, "site")
    for n, (x, y) in enumerate(fence_post_xy(*YARD_M, POST_SPACING_M, ROAD_Y_M)):
        at = (x, y, POST_HEIGHT_M / 2)
        post = mesh_ops.cylinder(f"fence_post_{n}", POST_RADIUS_M, POST_HEIGHT_M, at)
        ctx.add_part(FENCE_TAG, post, "paint_grey")
    _fence_rails(ctx)
