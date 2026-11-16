"""Access platform part: a 0.05 m grating plate, toe plates and a handrail on the open edges."""

import math

from scene_setup import BuildContext

from parts import mesh_ops, shapes
from parts.handrail import handrail_path

PLATE_M = 0.05
TOE_HEIGHT_M = 0.1
TOE_THICKNESS_M = 0.01
Point2 = tuple[float, float]


def ring_outline(radius_m: float, sides: int = 16) -> list[Point2]:
    """Regular polygon around the origin, counter-clockwise, first vertex on +x.

    Args:
        radius_m: Circumradius in metres.
        sides: Number of vertices (16 puts a vertex on every 22.5 degrees, so one on -y).

    Returns:
        The vertices ``(x, y)``.
    """
    angles = [2 * math.pi * k / sides for k in range(sides)]
    return [(radius_m * math.cos(a), radius_m * math.sin(a)) for a in angles]


def platform(
    ctx: BuildContext,
    tag: str,
    name: str,
    outline: list[Point2],
    z_m: float,
    hole_radius_m: float | None = None,
) -> None:
    """Add the grating plate; its top face is at ``z_m``.

    Args:
        ctx: Build context.
        tag: Equipment tag the part belongs to.
        name: Object name.
        outline: Plate outline, counter-clockwise from above (item-local metres).
        z_m: Item-local height of the plate's top face.
        hole_radius_m: Radius of a round opening around the outline's centre (for a vessel or
            stack that passes through), or ``None`` for a solid plate.
    """
    hole = None
    if hole_radius_m is not None:
        cx = sum(p[0] for p in outline) / len(outline)
        cy = sum(p[1] for p in outline) / len(outline)
        hole = [
            (
                cx + hole_radius_m * (px - cx) / math.dist((px, py), (cx, cy)),
                cy + hole_radius_m * (py - cy) / math.dist((px, py), (cx, cy)),
            )
            for px, py in outline
        ]
    plate = shapes.slab(f"{name}_plate", outline, z_m, PLATE_M, hole)
    ctx.add_part(tag, plate, "grating", tile_m=1.0)


def platform_edge(ctx: BuildContext, tag: str, name: str, points: list[Point2], z_m: float) -> None:
    """Add toe plates and a handrail along an open edge of a platform.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        points: The open edge as a polyline ``(x, y)``, in walking order.
        z_m: Item-local height of the platform's top face (the posts stand on it).
    """
    for i, (a, b) in enumerate(zip(points, points[1:], strict=False)):
        length = math.dist(a, b)
        angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, z_m + TOE_HEIGHT_M / 2)
        toe = mesh_ops.box(f"{name}_toe_{i}", (length, TOE_THICKNESS_M, TOE_HEIGHT_M), mid, angle)
        ctx.add_part(tag, toe, "safety_yellow")
    handrail_path(ctx, tag, f"{name}_rail", [(x, y, z_m) for x, y in points])
