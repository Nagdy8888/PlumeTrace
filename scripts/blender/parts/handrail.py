"""Safety handrail part: posts every 1.5 m, a top rail and a knee rail (safety yellow)."""

import math

from scene_setup import BuildContext

from parts import mesh_ops, shapes

POST_SPACING_M = 1.5
POST_RADIUS_M = 0.025
TOP_RAIL_Z_M = 1.1
KNEE_RAIL_Z_M = 0.55


def handrail(ctx: BuildContext, tag: str, length_m: float, y_m: float, base_z_m: float) -> None:
    """Add a handrail along x, centred on x = 0, at item-local ``y_m``.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        length_m: Rail length along x.
        y_m: Item-local y of the rail.
        base_z_m: Item-local z of the post bases.
    """
    count = round(length_m / POST_SPACING_M) + 1
    for i in range(count):
        x = -length_m / 2 + i * POST_SPACING_M
        at = (x, y_m, base_z_m + TOP_RAIL_Z_M / 2)
        post = mesh_ops.cylinder(f"{tag}_post_{i}", POST_RADIUS_M, TOP_RAIL_Z_M, at, segments=8)
        ctx.add_part(tag, post, "safety_yellow")
    for label, z in (("top", TOP_RAIL_Z_M), ("knee", KNEE_RAIL_Z_M)):
        rail = mesh_ops.cylinder(
            f"{tag}_rail_{label}",
            POST_RADIUS_M,
            length_m,
            (0.0, y_m, base_z_m + z),
            axis="X",
            segments=8,
        )
        ctx.add_part(tag, rail, "safety_yellow")


def handrail_path(
    ctx: BuildContext, tag: str, name: str, points: list[tuple[float, float, float]]
) -> None:
    """Add a handrail along a polyline of foot points (flat, or sloped like a stair).

    Posts stand every 1.5 m or less (and at every corner); the top rail is 1.1 m and the knee rail
    0.55 m above the foot line, both straight rods between the posts.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        points: Item-local foot points ``(x, y, z)`` in walking order (at least two).

    Raises:
        ValueError: If fewer than two points are given.
    """
    if len(points) < 2:
        raise ValueError("a handrail needs at least two points")
    posts: list[tuple[float, float, float]] = [points[0]]
    for a, b in zip(points, points[1:], strict=False):
        steps = max(1, math.ceil(math.dist(a, b) / POST_SPACING_M))
        posts += [
            tuple(a[k] + (b[k] - a[k]) * i / steps for k in range(3)) for i in range(1, steps + 1)
        ]
    for i, (x, y, z) in enumerate(posts):
        post = shapes.rod(f"{name}_post_{i}", (x, y, z), (x, y, z + TOP_RAIL_Z_M), POST_RADIUS_M)
        ctx.add_part(tag, post, "safety_yellow")
    for label, h in (("top", TOP_RAIL_Z_M), ("knee", KNEE_RAIL_Z_M)):
        for i, (a, b) in enumerate(zip(posts, posts[1:], strict=False)):
            rail = shapes.rod(
                f"{name}_{label}_{i}", (a[0], a[1], a[2] + h), (b[0], b[1], b[2] + h), POST_RADIUS_M
            )
            ctx.add_part(tag, rail, "safety_yellow")
