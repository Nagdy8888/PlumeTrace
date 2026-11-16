"""One piping route of the spec as a filleted tube with flanges, valves and supports (bpy module).

The route is the node ``PIPE__<route id>`` (see ``naming.pipe_tag``). It is visual only: radius,
colour and fittings come from the spec size and service, never from a calculation. Routes are
not baked (thin parts have no useful occlusion texture); they still occlude the baked items.
"""

import math
from typing import Any

import bpy
from naming import pipe_tag
from parts import mesh_ops
from parts.flange import FLANGE_OVERHANG_M, FLANGE_THICKNESS_M
from parts.shapes import rod
from parts.valve import valve
from piping_math import Vec3, fillet_polyline, pipe_radius_m, support_points
from scene_setup import BuildContext

SERVICE_MATERIAL = {
    "gas": "pipe_gas",
    "vent": "pipe_vent",
    "flare": "pipe_vent",
    "condensate": "pipe_condensate",
    "fuel_gas": "pipe_fuel",
}
BEND_FACTOR = 1.5  # bend radius = 1.5 pipe diameters
VALVE_MIN_SIZE_IN = 10.0
VALVE_FROM_END_M = 1.5
LARGE_RADIUS_M = 0.1  # from this radius the tube profile gets 4 bevel steps, below it 2
POST_M = 0.2
BAR_SIZE_M = (0.2, 0.8, 0.15)  # along the pipe, across it, thick


def _tube(name: str, points: list[Vec3], radius_m: float) -> bpy.types.Object:
    """Sweep a round profile along ``points``: a poly curve with a bevel, taken as a mesh."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius_m
    curve.bevel_resolution = 4 if radius_m >= LARGE_RADIUS_M else 2
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, (x, y, z) in zip(spline.points, points, strict=True):
        point.co = (float(x), float(y), float(z), 1.0)
    holder = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(holder)
    bpy.context.view_layer.update()
    evaluated = holder.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = bpy.data.meshes.new_from_object(evaluated)
    bpy.data.objects.remove(holder)
    bpy.data.curves.remove(curve)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _toward(a: Vec3, b: Vec3, distance_m: float) -> Vec3:
    """The point ``distance_m`` from ``a`` along the straight line to ``b``."""
    length = math.dist(a, b)
    k = distance_m / length
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)


def _end_fittings(ctx: BuildContext, tag: str, route: dict[str, Any], radius_m: float) -> None:
    """Flanges at both ends and, on lines of 10 inch or more, a valve 1.5 m from each end."""
    way = [tuple(float(c) for c in p) for p in route["waypoints_m"]]
    ends = ((way[0], way[1], "a"), (way[-1], way[-2], "b"))
    for end, inner, label in ends:
        near = _toward(end, inner, FLANGE_THICKNESS_M)
        disc = rod(f"{tag}_flange_{label}", end, near, radius_m + FLANGE_OVERHANG_M)
        ctx.add_part(tag, disc, "paint_grey")
        if route["size_in"] >= VALVE_MIN_SIZE_IN:
            axis = "X" if abs(inner[0] - end[0]) >= abs(inner[1] - end[1]) else "Y"
            spot = _toward(end, inner, VALVE_FROM_END_M)
            valve(ctx, tag, f"{tag}_valve_{label}", radius_m, spot, axis)


def _heading_deg(points: list[Vec3], at: Vec3) -> float:
    """Plan heading (degrees, from +x) of the path segment nearest to ``at``."""
    best, heading = math.inf, 0.0
    for a, b in zip(points, points[1:], strict=False):
        length = math.dist(a, b)
        if length == 0.0:
            continue
        t = max(0.0, min(1.0, sum((at[i] - a[i]) * (b[i] - a[i]) for i in range(3)) / length**2))
        foot = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        if (gap := math.dist(at, foot)) < best:
            best, heading = gap, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return heading


def _supports(ctx: BuildContext, tag: str, points: list[Vec3], radius_m: float) -> None:
    """A post from the ground and a crossbar under the pipe at each ``support_points`` position."""
    for n, (x, y, z) in enumerate(support_points(points)):
        heading = _heading_deg(points, (x, y, z))
        under = z - radius_m
        post_h = under - BAR_SIZE_M[2]
        post = mesh_ops.box(f"{tag}_sup_{n}_post", (POST_M, POST_M, post_h), (x, y, post_h / 2))
        bar = mesh_ops.box(
            f"{tag}_sup_{n}_bar", BAR_SIZE_M, (x, y, under - BAR_SIZE_M[2] / 2), heading
        )
        ctx.add_part(tag, post, "paint_dark")
        ctx.add_part(tag, bar, "paint_dark")


def build(route: dict[str, Any], ctx: BuildContext) -> None:
    """Build one piping route as the node ``PIPE__<id>``.

    Args:
        route: Spec ``piping`` entry (``id``, ``service``, ``size_in``, ``waypoints_m``).
        ctx: Build context.
    """
    tag = pipe_tag(route["id"])
    ctx.new_root({"tag": tag, "type": "pipe", "position_m": [0.0, 0.0, 0.0], "rotation_deg": 0.0})
    radius = pipe_radius_m(float(route["size_in"]))
    way = [tuple(float(c) for c in p) for p in route["waypoints_m"]]
    points = fillet_polyline(way, BEND_FACTOR * 2 * radius)
    ctx.add_part(tag, _tube(f"{tag}_tube", points, radius), SERVICE_MATERIAL[route["service"]])
    _end_fittings(ctx, tag, route, radius)
    _supports(ctx, tag, points, radius)
