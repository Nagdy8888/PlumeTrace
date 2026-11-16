"""Mesh primitives built with ``bmesh`` (never ``bpy.ops.mesh.primitive_*``).

All sizes are in metres. Locations passed in are item-local when the object is later parented to
an equipment root (see ``BuildContext.add_part``). Facet counts follow ``solids.segments_for``.
"""

import math

import bmesh
import bpy
from mathutils import Vector
from uvmath import box_uv  # scripts/blender is on sys.path (build_station.py)

from parts.solids import cone_bmesh, orient, segments_for

Vec3 = tuple[float, float, float]


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
    name: str,
    radius: float,
    depth: float,
    location: Vec3,
    axis: str = "Z",
    segments: int | None = None,
    rotation_z_deg: float = 0.0,
) -> bpy.types.Object:
    """Create a capped cylinder centred on ``location`` with its length along ``axis``.

    Args:
        name: Object name.
        radius: Radius in metres.
        depth: Length along ``axis`` in metres.
        location: Centre position.
        axis: "X", "Y" or "Z".
        segments: Facets (default: by radius, see ``solids.segments_for``).
        rotation_z_deg: Rotation about z in degrees (applied to the whole object).

    Returns:
        The new object.
    """
    bm = cone_bmesh(radius, depth, segments or segments_for(radius), True, axis)
    return from_bmesh(name, bm, location, rotation_z_deg)


def cone(
    name: str, r_bottom: float, r_top: float, depth: float, location: Vec3, axis: str = "Z"
) -> bpy.types.Object:
    """Create a capped cone (or frustum) centred on ``location``.

    Args:
        name: Object name.
        r_bottom: Radius at the -axis end in metres (0 gives a point).
        r_top: Radius at the +axis end in metres.
        depth: Length along ``axis`` in metres.
        location: Centre position.
        axis: "X", "Y" or "Z".

    Returns:
        The new object.
    """
    segments = segments_for(max(r_bottom, r_top))
    return from_bmesh(name, cone_bmesh(r_bottom, depth, segments, True, axis, r_top), location)


def torus(
    name: str, major_r: float, minor_r: float, location: Vec3, axis: str = "Z"
) -> bpy.types.Object:
    """Create a torus (ring) whose hole runs along ``axis``.

    Args:
        name: Object name.
        major_r: Distance from the centre to the tube centre, in metres.
        minor_r: Tube radius in metres.
        location: Centre position.
        axis: Direction of the hole: "X", "Y" or "Z".

    Returns:
        The new object (``segments_for(major_r)`` facets around, ``segments_for(minor_r)`` round).
    """
    around, round_ = segments_for(major_r), segments_for(minor_r)
    bm = bmesh.new()
    rings = []
    for i in range(around):
        u = 2 * math.pi * i / around
        ring = []
        for j in range(round_):
            v = 2 * math.pi * j / round_
            radial = major_r + minor_r * math.cos(v)
            at = (radial * math.cos(u), radial * math.sin(u), minor_r * math.sin(v))
            ring.append(bm.verts.new(at))
        rings.append(ring)
    for i in range(around):
        a, b = rings[i], rings[(i + 1) % around]
        for j in range(round_):
            k = (j + 1) % round_
            bm.faces.new((a[j], b[j], b[k], a[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    orient(bm, axis)
    return from_bmesh(name, bm, location)


def half_cylinder(
    name: str, radius: float, depth: float, location: Vec3, axis: str = "X"
) -> bpy.types.Object:
    """Create the upper half of a cylinder (an open shell, e.g. a coupling guard)."""
    bm = cone_bmesh(radius, depth, 24, True, axis)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm, geom=geom, plane_co=(0.0, 0.0, 0.0), plane_no=(0.0, 0.0, 1.0), clear_inner=True
    )
    return from_bmesh(name, bm, location)


def tube(name: str, radius: float, wall_m: float, depth: float, location: Vec3) -> bpy.types.Object:
    """Create an open vertical tube: an outer shell plus an inner shell with flipped normals."""
    bm = cone_bmesh(radius, depth, 24, False, "Z")
    inner = cone_bmesh(radius - wall_m, depth, 24, False, "Z")
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
