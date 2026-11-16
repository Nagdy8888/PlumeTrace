"""Pressure vessel parts: shell, 2:1 elliptical heads and (horizontal) flanged nozzle stubs."""

from typing import Literal

import bmesh
import bpy
from mathutils import Vector
from scene_setup import BuildContext

from parts import mesh_ops
from parts.flange import flange

STUB_RADIUS_M = 0.1
STUB_LENGTH_M = 0.3
Vec3 = tuple[float, float, float]


def _head(
    name: str, diameter_m: float, location: Vec3, side: int, axis: Literal["X", "Z"] = "X"
) -> bpy.types.Object:
    """Half-ellipsoid head (2:1, depth D/4) bulging towards ``side`` (+1 or -1) along ``axis``."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
    half, depth = diameter_m / 2, diameter_m / 4
    scale = (depth, half, half) if axis == "X" else (half, half, depth)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    plane_no = (float(side), 0.0, 0.0) if axis == "X" else (0.0, 0.0, float(side))
    # clear_inner removes the half behind the plane
    bmesh.ops.bisect_plane(
        bm, geom=geom, plane_co=(0.0, 0.0, 0.0), plane_no=plane_no, clear_inner=True
    )
    return mesh_ops.from_bmesh(name, bm, location)


def vessel(
    ctx: BuildContext,
    tag: str,
    name: str,
    diameter_m: float,
    shell_length_m: float,
    axis: Literal["X", "Z"],
    location: Vec3,
    heads: str = "2:1",
    material: str = "paint_grey",
) -> None:
    """Add a vessel: a cylindrical shell with 2:1 elliptical heads (head depth D/4).

    Total length is ``shell_length_m + D/2`` with heads, ``shell_length_m`` without.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        diameter_m: Shell diameter.
        shell_length_m: Length of the cylindrical shell between the head tangent lines.
        axis: Long axis, "X" (horizontal) or "Z" (vertical).
        location: Item-local centre of the shell (also the centre of the whole vessel).
        heads: ``"2:1"`` for two elliptical heads, ``"none"`` for the bare shell.
        material: Material key of the shell and heads.

    Raises:
        ValueError: If ``heads`` is neither ``"2:1"`` nor ``"none"``.
    """
    if heads not in ("2:1", "none"):
        raise ValueError(f"unknown head type {heads!r}")
    shell = mesh_ops.cylinder(f"{name}_shell", diameter_m / 2, shell_length_m, location, axis=axis)
    ctx.add_part(tag, shell, material)
    if heads == "none":
        return
    offset = Vector((1.0, 0.0, 0.0) if axis == "X" else (0.0, 0.0, 1.0)) * (shell_length_m / 2)
    for side, label in ((1, "end"), (-1, "start")):
        at = Vector(location) + offset * side
        head = _head(f"{name}_head_{label}", diameter_m, (at.x, at.y, at.z), side, axis)
        ctx.add_part(tag, head, material)


def horizontal_vessel(
    ctx: BuildContext,
    tag: str,
    name: str,
    diameter_m: float,
    length_m: float,
    location: Vec3,
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
