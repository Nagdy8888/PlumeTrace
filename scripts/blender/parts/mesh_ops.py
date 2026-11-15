"""Mesh primitives built with ``bmesh`` (never ``bpy.ops.mesh.primitive_*``).

All sizes are in metres. Locations passed in are item-local when the object is later parented to
an equipment root (see ``BuildContext.add_part``).
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from uvmath import box_uv  # scripts/blender is on sys.path (build_station.py)

Vec3 = tuple[float, float, float]
_AXIS_ROTATION = {"Z": None, "X": ("Y", 90.0), "Y": ("X", -90.0)}


def from_bmesh(
    name: str, bm: bmesh.types.BMesh, location: Vec3, rotation_z_deg: float = 0.0
) -> bpy.types.Object:
    """Turn a bmesh into a linked mesh object at ``location``."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, math.radians(rotation_z_deg))
    return obj


def _cone(radius: float, depth: float, segments: int, caps: bool, axis: str) -> bmesh.types.BMesh:
    """Build a bmesh cylinder along ``axis`` ("X", "Y" or "Z") centred on the origin."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=caps,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=depth,
        calc_uvs=False,
    )
    spin = _AXIS_ROTATION[axis]
    if spin is not None:
        matrix = Matrix.Rotation(math.radians(spin[1]), 3, spin[0])
        bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=matrix, verts=bm.verts)
    return bm


def box(name: str, size: Vec3, location: Vec3, rotation_z_deg: float = 0.0) -> bpy.types.Object:
    """Create a box centred on ``location``.

    Args:
        name: Object name.
        size: ``(x, y, z)`` extent in metres.
        location: Centre position.
        rotation_z_deg: Rotation about z in degrees.

    Returns:
        The new object.
    """
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    return from_bmesh(name, bm, location, rotation_z_deg)


def plane(name: str, size_xy: tuple[float, float], location: Vec3) -> bpy.types.Object:
    """Create one upward-facing quad of ``size_xy`` metres centred on ``location``."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((size_xy[0], size_xy[1], 1.0)), verts=bm.verts)
    return from_bmesh(name, bm, location)


def cylinder(
    name: str, radius: float, depth: float, location: Vec3, axis: str = "Z", segments: int = 24
) -> bpy.types.Object:
    """Create a capped cylinder centred on ``location`` with its length along ``axis``."""
    return from_bmesh(name, _cone(radius, depth, segments, True, axis), location)


def half_cylinder(
    name: str, radius: float, depth: float, location: Vec3, axis: str = "X"
) -> bpy.types.Object:
    """Create the upper half of a cylinder (an open shell, e.g. a coupling guard)."""
    bm = _cone(radius, depth, 24, True, axis)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm, geom=geom, plane_co=(0.0, 0.0, 0.0), plane_no=(0.0, 0.0, 1.0), clear_inner=True
    )
    return from_bmesh(name, bm, location)


def tube(name: str, radius: float, wall_m: float, depth: float, location: Vec3) -> bpy.types.Object:
    """Create an open vertical tube: an outer shell plus an inner shell with flipped normals."""
    bm = _cone(radius, depth, 24, False, "Z")
    inner = _cone(radius - wall_m, depth, 24, False, "Z")
    bmesh.ops.reverse_faces(inner, faces=list(inner.faces))
    mesh = bpy.data.meshes.new("tmp_inner")
    inner.to_mesh(mesh)
    inner.free()
    bm.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    return from_bmesh(name, bm, location)


def parent_to(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    """Parent ``child`` to ``parent`` keeping the child's location parent-local."""
    child.parent = parent


def bevel_edges(obj: bpy.types.Object, width_m: float, segments: int = 2) -> None:
    """Add an angle-limited Bevel modifier (applied when the equipment is joined)."""
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width_m
    mod.segments = segments
    mod.limit_method = "ANGLE"


def assign_box_uv(obj: bpy.types.Object, tile_m: float) -> None:
    """Write the ``UVMap`` layer by world-space box projection (``uvmath.box_uv``).

    Args:
        obj: Mesh object whose ``matrix_world`` is up to date.
        tile_m: Texture repeat length in metres.
    """
    mesh = obj.data
    layer = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    world = obj.matrix_world
    rot = world.to_3x3()
    for poly in mesh.polygons:
        n = rot @ poly.normal
        for i in poly.loop_indices:
            p = world @ mesh.vertices[mesh.loops[i].vertex_index].co
            layer.data[i].uv = box_uv((p.x, p.y, p.z), (n.x, n.y, n.z), tile_m)


def shade_by_angle(obj: bpy.types.Object, degrees: float = 50.0) -> None:
    """Smooth-shade faces and mark edges sharper than ``degrees`` as sharp."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    limit = math.radians(degrees)
    for edge in bm.edges:
        edge.smooth = len(edge.link_faces) != 2 or edge.calc_face_angle(0.0) < limit
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(obj.data)
    bm.free()
