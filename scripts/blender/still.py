"""Render a review still of one equipment item with Cycles (bpy module, for visual checks only).

The camera stands 2.5 times the item's largest dimension away, 30 degrees above the horizon, to
the south-west of the item; the sun is at azimuth 250 degrees, elevation 18 degrees (as in the
frontend ``Sun.tsx``). The still is a review aid, not part of the shipped glb.
"""

import math
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

SAMPLES = 32
FILTER_WIDTH_PX = 2.5  # softer pixel filter than the 1.5 default: keeps the PNGs under 400 KB
WIDTH_PX = 960
HEIGHT_PX = 540
LENS_MM = 35.0
DISTANCE_FACTOR = 2.5
ELEVATION_DEG = 30.0
SUN_AZIMUTH_DEG = 250.0
SUN_ELEVATION_DEG = 18.0
SUN_STRENGTH = 2.5
SKY_COLOR = (0.55, 0.62, 0.70, 1.0)
FLOOR_COLOR = (0.30, 0.28, 0.25, 1.0)
FLOOR_SIZE_M = 400.0
FLOOR_Z_M = -0.05  # under the ground patch (z -0.02) so the two never z-fight


def camera_position(item: dict[str, Any]) -> tuple[Vector, Vector]:
    """Camera and target positions for an item (world metres, z up).

    Args:
        item: Spec item with ``position_m`` and ``size_m``.

    Returns:
        ``(camera, target)``: the target is the item's centre at half its height; the camera is
        ``2.5 * max(size_m)`` away at 30 degrees elevation towards the south-west (-x, -y).
    """
    px, py, pz = item["position_m"]
    size = item["size_m"]
    target = Vector((px, py, pz + size[2] / 2))
    distance = DISTANCE_FACTOR * max(size)
    horizontal = distance * math.cos(math.radians(ELEVATION_DEG))
    offset = Vector((-horizontal / math.sqrt(2), -horizontal / math.sqrt(2), 0.0))
    offset.z = distance * math.sin(math.radians(ELEVATION_DEG))
    return target + offset, target


def _add_sun() -> None:
    """Add the sun lamp pointing from azimuth 250, elevation 18 degrees."""
    az, el = math.radians(SUN_AZIMUTH_DEG), math.radians(SUN_ELEVATION_DEG)
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    data = bpy.data.lights.new("still_sun", "SUN")
    data.energy = SUN_STRENGTH
    sun = bpy.data.objects.new("still_sun", data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()


def _add_floor(centre: Vector) -> bpy.types.Object:
    """Add a large plain backdrop floor centred on ``centre`` (render only; removed afterwards)."""
    mat = bpy.data.materials.new("still_floor")
    mat.diffuse_color = FLOOR_COLOR
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = FLOOR_COLOR
    mesh = bpy.data.meshes.new("still_floor")
    half = FLOOR_SIZE_M / 2
    mesh.from_pydata(
        [(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [], [(0, 1, 2, 3)]
    )
    mesh.materials.append(mat)
    floor = bpy.data.objects.new("still_floor", mesh)
    bpy.context.scene.collection.objects.link(floor)
    floor.location = (centre.x, centre.y, FLOOR_Z_M)
    return floor


def render_still(item: dict[str, Any], out: Path) -> None:
    """Render a 960 x 540 PNG of ``item`` (Cycles CPU, 32 samples, denoised).

    A plain backdrop floor (the gravel patch is hidden for the render), the camera and the sun
    exist only for the render; they are removed again, so the export that follows holds none of
    them.

    Args:
        item: Spec item to frame (the first selected tag).
        out: Target ``.png`` path; its folder is created.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.filter_width = FILTER_WIDTH_PX
    scene.render.resolution_x, scene.render.resolution_y = WIDTH_PX, HEIGHT_PX
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 100
    scene.world = bpy.data.worlds.new("still_world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = SKY_COLOR
    _add_sun()
    position, target = camera_position(item)
    floor = _add_floor(target)
    patch = bpy.data.objects.get("ground")  # the gravel patch is noisy and fills the PNG
    if patch is not None:
        patch.hide_render = True
    camera = bpy.data.objects.new("still_camera", bpy.data.cameras.new("still_camera"))
    camera.data.lens = LENS_MM
    bpy.context.scene.collection.objects.link(camera)
    camera.location = position
    camera.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    if patch is not None:
        patch.hide_render = False
    for helper in (floor, camera, bpy.data.objects["still_sun"]):
        bpy.data.objects.remove(helper)
