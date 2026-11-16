"""Fixed ladder part: two rails, rungs and an optional safety cage of hoops."""

import math

from scene_setup import BuildContext

from parts import mesh_ops

RAIL_M = 0.06
RAIL_GAP_M = 0.45
RUNG_RADIUS_M = 0.012
RUNG_SPACING_M = 0.3
HOOP_RADIUS_M = 0.35
HOOP_TUBE_M = 0.015
HOOP_SPACING_M = 0.9
HOOP_START_M = 2.2  # above the base
HOOP_OFFSET_M = 0.25  # hoop centre in front of the rail plane
EXTENSION_M = 1.0  # rails continue above the landing as hand holds


def ladder(
    ctx: BuildContext,
    tag: str,
    name: str,
    base: tuple[float, float, float],
    top_z: float,
    facing_deg: float,
    caged: bool,
) -> None:
    """Add a fixed ladder from ``base`` up to a landing at ``top_z``.

    Rails (0.06 x 0.06 m) are 0.45 m apart and run 1.0 m above the landing; rungs (radius 0.012 m)
    every 0.3 m; a cage adds torus hoops (radius 0.35 m) every 0.9 m from 2.2 m above the base.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        base: Item-local ``(x, y, z)`` of the ladder centre at its foot.
        top_z: Item-local height of the landing.
        facing_deg: Direction the climber's side faces, degrees about z (0 = +x, -90 = -y).
        caged: Add the safety cage on the climber's side.
    """
    x0, y0, z0 = base
    fx, fy = math.cos(math.radians(facing_deg)), math.sin(math.radians(facing_deg))
    height = top_z + EXTENSION_M - z0
    for side, label in ((1, "l"), (-1, "r")):
        at = (x0 - fy * RAIL_GAP_M / 2 * side, y0 + fx * RAIL_GAP_M / 2 * side, z0 + height / 2)
        rail = mesh_ops.box(f"{name}_rail_{label}", (RAIL_M, RAIL_M, height), at)
        ctx.add_part(tag, rail, "paint_grey")
    for i in range(1, int((top_z + EXTENSION_M - z0) / RUNG_SPACING_M)):
        rung = mesh_ops.cylinder(
            f"{name}_rung_{i}",
            RUNG_RADIUS_M,
            RAIL_GAP_M,
            (x0, y0, z0 + i * RUNG_SPACING_M),
            axis="X",
            rotation_z_deg=facing_deg + 90.0,
        )
        ctx.add_part(tag, rung, "paint_grey")
    if not caged:
        return
    centre = (x0 + fx * HOOP_OFFSET_M, y0 + fy * HOOP_OFFSET_M)
    z = z0 + HOOP_START_M
    while z <= top_z:
        hoop = mesh_ops.torus(
            f"{name}_hoop_{round(z * 10)}", HOOP_RADIUS_M, HOOP_TUBE_M, (*centre, z)
        )
        ctx.add_part(tag, hoop, "paint_grey")
        z += HOOP_SPACING_M
