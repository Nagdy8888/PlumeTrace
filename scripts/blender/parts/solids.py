"""Bmesh solids shared by the primitives (pure bmesh, no objects are created here)."""

import math

import bmesh
from mathutils import Matrix

SEGMENTS_LARGE = 32  # radius >= 0.3 m
SEGMENTS_MEDIUM = 16  # 0.1 m <= radius < 0.3 m
SEGMENTS_SMALL = 8  # radius < 0.1 m
AXIS_ROTATION = {"Z": None, "X": ("Y", 90.0), "Y": ("X", -90.0)}


def segments_for(radius_m: float) -> int:
    """Number of facets of a round part: 32 from 0.3 m radius, 16 from 0.1 m, else 8.

    Args:
        radius_m: Radius in metres.

    Returns:
        The segment count (the Phase 4 Task 6 convention).
    """
    if radius_m >= 0.3:
        return SEGMENTS_LARGE
    return SEGMENTS_MEDIUM if radius_m >= 0.1 else SEGMENTS_SMALL


def orient(bm: bmesh.types.BMesh, axis: str) -> None:
    """Rotate a bmesh built along z so that its length runs along ``axis`` ("X", "Y" or "Z")."""
    spin = AXIS_ROTATION[axis]
    if spin is not None:
        matrix = Matrix.Rotation(math.radians(spin[1]), 3, spin[0])
        bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=matrix, verts=bm.verts)


def cone_bmesh(
    radius_bottom: float,
    depth: float,
    segments: int,
    caps: bool,
    axis: str,
    radius_top: float | None = None,
) -> bmesh.types.BMesh:
    """Build a bmesh cone or cylinder along ``axis`` centred on the origin.

    Args:
        radius_bottom: Radius at the -axis end, in metres.
        depth: Length along ``axis``, in metres.
        segments: Facets around the axis.
        caps: Close both ends.
        axis: "X", "Y" or "Z".
        radius_top: Radius at the +axis end (default: ``radius_bottom``, a cylinder).

    Returns:
        The new bmesh (the caller frees it).
    """
    bm = bmesh.new()
    top = radius_bottom if radius_top is None else radius_top
    bmesh.ops.create_cone(
        bm,
        cap_ends=caps,
        cap_tris=False,
        segments=segments,
        radius1=radius_bottom,
        radius2=top,
        depth=depth,
        calc_uvs=False,
    )
    orient(bm, axis)
    return bm
