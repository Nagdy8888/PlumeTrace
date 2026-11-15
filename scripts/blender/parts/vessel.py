"""Horizontal pressure vessel part: shell, 2:1 elliptical heads and flanged nozzle stubs."""

import bmesh
import bpy
from mathutils import Vector
from scene_setup import BuildContext

from parts import mesh_ops
from parts.flange import flange

STUB_RADIUS_M = 0.1
STUB_LENGTH_M = 0.3


def _head(
    name: str, diameter_m: float, location: tuple[float, float, float], side: int
) -> bpy.types.Object:
    """Half-ellipsoid head (2:1) bulging towards ``side`` (+1 or -1) along x."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
    bmesh.ops.scale(
        bm, vec=Vector((diameter_m / 4, diameter_m / 2, diameter_m / 2)), verts=bm.verts
    )
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    plane_no = (float(side), 0.0, 0.0)  # clear_inner removes the half behind the plane
    bmesh.ops.bisect_plane(
        bm, geom=geom, plane_co=(0.0, 0.0, 0.0), plane_no=plane_no, clear_inner=True
    )
    return mesh_ops.from_bmesh(name, bm, location)


def horizontal_vessel(
    ctx: BuildContext,
    tag: str,
    name: str,
    diameter_m: float,
    length_m: float,
    location: tuple[float, float, float],
) -> None:
    """Add a horizontal vessel along x, ``length_m`` long overall including its heads.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        diameter_m: Shell diameter.
        length_m: Overall length (heads included), without the nozzle stubs.
        location: Item-local centre of the vessel.
    """
    cx, cy, cz = location
    shell_len = length_m - diameter_m / 2
    shell = mesh_ops.cylinder(f"{name}_shell", diameter_m / 2, shell_len, location, axis="X")
    ctx.add_part(tag, shell, "paint_grey")
    for side, label in ((1, "e"), (-1, "w")):
        head = _head(f"{name}_head_{label}", diameter_m, (cx + side * shell_len / 2, cy, cz), side)
        ctx.add_part(tag, head, "paint_grey")
        tip = cx + side * length_m / 2
        stub_at = (tip + side * STUB_LENGTH_M / 2, cy, cz)
        stub_name = f"{name}_stub_{label}"
        stub = mesh_ops.cylinder(stub_name, STUB_RADIUS_M, STUB_LENGTH_M, stub_at, axis="X")
        ctx.add_part(tag, stub, "paint_grey")
        flange_at = (tip + side * STUB_LENGTH_M, cy, cz)
        flange(ctx, tag, f"{name}_flange_{label}", STUB_RADIUS_M, flange_at, axis="X")
