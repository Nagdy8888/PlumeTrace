"""Safety handrail part: posts every 1.5 m, a top rail and a knee rail (safety yellow)."""

from scene_setup import BuildContext

from parts import mesh_ops

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
