"""Composite shapes built on ``mesh_ops``: rods between two points, bevelled blocks, slabs."""

import math

import bmesh
import bpy
from mathutils import Vector

from parts import mesh_ops
from parts.solids import cone_bmesh, segments_for

Vec3 = tuple[float, float, float]
BEVEL_M = 0.02
BEVEL_MIN_LONGEST_M = 1.0
BEVEL_MIN_SHORTEST_M = 0.1  # below this a 0.02 m bevel would eat the whole face


def block(name: str, size: Vec3, location: Vec3, rotation_z_deg: float = 0.0) -> bpy.types.Object:
    """Create a box, with a 0.02 m bevel when it is a block of 1 m or more.

    Args:
        name: Object name.
        size: ``(x, y, z)`` extent in metres.
        location: Centre position.
        rotation_z_deg: Rotation about z in degrees.

    Returns:
        The new object; the Bevel modifier is applied when the equipment is joined.
    """
    obj = mesh_ops.box(name, size, location, rotation_z_deg)
    if max(size) >= BEVEL_MIN_LONGEST_M and min(size) >= BEVEL_MIN_SHORTEST_M:
        mesh_ops.bevel_edges(obj, BEVEL_M)
    return obj


def tilt(obj: bpy.types.Object, x_deg: float = 0.0, y_deg: float = 0.0, z_deg: float = 0.0) -> None:
    """Set the object's rotation about x, y and z (degrees, applied in x, y, z order)."""
    obj.rotation_euler = (math.radians(x_deg), math.radians(y_deg), math.radians(z_deg))


def rod(name: str, start: Vec3, end: Vec3, radius: float) -> bpy.types.Object:
    """Create a capped cylinder between two points (any direction).

    Args:
        name: Object name.
        start: One end centre, in metres.
        end: The other end centre, in metres.
        radius: Radius in metres.

    Returns:
        The new object, located at the midpoint.

    Raises:
        ValueError: If the two points coincide.
    """
    delta = Vector(end) - Vector(start)
    if delta.length < 1e-9:
        raise ValueError(f"rod {name} has zero length")
    bm = cone_bmesh(radius, delta.length, segments_for(radius), True, "Z")
    matrix = Vector((0.0, 0.0, 1.0)).rotation_difference(delta).to_matrix()
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=matrix, verts=bm.verts)
    mid = (Vector(start) + Vector(end)) / 2
    return mesh_ops.from_bmesh(name, bm, (mid.x, mid.y, mid.z))


def slab(
    name: str,
    outer: list[tuple[float, float]],
    z_top: float,
    thickness: float,
    inner: list[tuple[float, float]] | None = None,
) -> bpy.types.Object:
    """Create a closed plate from a counter-clockwise outline, optionally with a hole.

    Args:
        name: Object name.
        outer: Outline ``(x, y)`` points, counter-clockwise seen from above.
        z_top: Height of the top face, in metres; the plate lies below it.
        thickness: Plate thickness in metres.
        inner: Hole outline with the same number of points as ``outer`` (vertex i of the hole
            sits on the ray of vertex i of the outline), or ``None`` for a solid plate.

    Returns:
        The new object (origin at the world origin of its parent frame).
    """
    bm = bmesh.new()
    n = len(outer)

    def ring(points: list[tuple[float, float]], z: float) -> list[bmesh.types.BMVert]:
        return [bm.verts.new((x, y, z)) for x, y in points]

    top, bottom = ring(outer, z_top), ring(outer, z_top - thickness)
    if inner is None:
        bm.faces.new(top)
        bm.faces.new(reversed(bottom))
    else:
        hole_top, hole_bottom = ring(inner, z_top), ring(inner, z_top - thickness)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bottom[i], bottom[j], top[j], top[i]))
        if inner is not None:
            bm.faces.new((top[i], top[j], hole_top[j], hole_top[i]))
            bm.faces.new((bottom[j], bottom[i], hole_bottom[i], hole_bottom[j]))
            bm.faces.new((hole_bottom[j], hole_bottom[i], hole_top[i], hole_top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_ops.from_bmesh(name, bm, (0.0, 0.0, 0.0))
