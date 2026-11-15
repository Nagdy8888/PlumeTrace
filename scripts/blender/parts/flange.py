"""Pipe flange part (a thin disc slightly wider than the pipe)."""

import bpy
from scene_setup import BuildContext

from parts import mesh_ops

FLANGE_OVERHANG_M = 0.06
FLANGE_THICKNESS_M = 0.04


def flange(
    ctx: BuildContext,
    tag: str,
    name: str,
    pipe_radius_m: float,
    location: tuple[float, float, float],
    axis: str = "Z",
) -> bpy.types.Object:
    """Add a flange disc around a pipe.

    Args:
        ctx: Build context.
        tag: Equipment tag the part belongs to.
        name: Object name.
        pipe_radius_m: Radius of the pipe it sits on; the disc is 0.06 m wider.
        location: Item-local centre of the disc.
        axis: Pipe direction ("X", "Y" or "Z").

    Returns:
        The part object.
    """
    disc = mesh_ops.cylinder(
        name, pipe_radius_m + FLANGE_OVERHANG_M, FLANGE_THICKNESS_M, location, axis=axis
    )
    return ctx.add_part(tag, disc, "paint_grey")
