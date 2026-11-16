"""Cycles ambient-occlusion bake per equipment item into a second UV set (bpy module).

Every group of ``ctx.groups()`` is baked (item roots, separate nodes, ``SITE__ground``,
``SITE__racks``, ``SITE__fence``) except the piping routes. The ``AO`` layer is an unwrap with
``uv.smart_project``, so large faces get large islands (owner ruling C3).

The baked image is wired through a Separate Color node (R) into the ``Occlusion`` input of the
``glTF Material Output`` node group, which the glTF exporter writes as ``occlusionTexture``.
"""

import math
import time

import bpy
from layout import ao_resolution
from naming import GROUND_TAG, PIPE_PREFIX, ao_image_name
from scene_setup import BuildContext

GROUP_NAME = "glTF Material Output"
SAMPLES = {"low": 16, "high": 128}
AO_DISTANCE_M = 6.0
UNWRAP_ANGLE_DEG = 66.0  # Blender's default angle limit for splitting islands
UNWRAP_MARGIN = 0.02  # island margin as a fraction of the UV space


def _occlusion_group() -> bpy.types.NodeTree:
    """Return the ``glTF Material Output`` node group, creating it once (input ``Occlusion``)."""
    group = bpy.data.node_groups.get(GROUP_NAME)
    if group is None:
        group = bpy.data.node_groups.new(GROUP_NAME, "ShaderNodeTree")
        group.interface.new_socket("Occlusion", socket_type="NodeSocketFloat")
    return group


def _select_only(obj: bpy.types.Object) -> None:
    """Make ``obj`` the only selected and the active object."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _add_ao_layer(obj: bpy.types.Object) -> None:
    """Add the ``AO`` UV layer, unwrap it with smart project, and keep ``UVMap`` for rendering."""
    layers = obj.data.uv_layers
    layers.new(name="AO")
    layers["UVMap"].active_render = True
    layers.active = layers["AO"]
    _select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(UNWRAP_ANGLE_DEG),
        island_margin=UNWRAP_MARGIN,
        scale_to_bounds=True,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def _wire_ao_image(obj: bpy.types.Object, image: bpy.types.Image) -> None:
    """In every material of ``obj`` add the AO image node (active) feeding the glTF occlusion."""
    group = _occlusion_group()
    for mat in obj.data.materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        for node in nodes:
            node.select = False
        uv = nodes.new("ShaderNodeUVMap")
        uv.uv_map = "AO"
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        sep = nodes.new("ShaderNodeSeparateColor")
        out = nodes.new("ShaderNodeGroup")
        out.node_tree = group
        links.new(uv.outputs["UV"], tex.inputs["Vector"])
        links.new(tex.outputs["Color"], sep.inputs[0])
        links.new(sep.outputs["Red"], out.inputs["Occlusion"])
        tex.select = True
        nodes.active = tex


def _bake_order(ctx: BuildContext) -> list[tuple[str, str, list[bpy.types.Object]]]:
    """The groups to bake, ground first (the order only helps debugging), no piping routes."""
    groups = [g for g in ctx.groups() if not g[1].startswith(PIPE_PREFIX)]
    return sorted(groups, key=lambda g: g[1] != GROUND_TAG)


def bake_all(ctx: BuildContext, level: str) -> float:
    """Bake ambient occlusion for every group except piping (other objects still occlude).

    The image size comes from ``layout.ao_resolution`` by the item type: ``SITE__ground`` and the
    compressors 1024 px on ``high``, the rest 512 px, everything 256 px on ``low``. A separate
    node (a fan, the flare tip) uses the type of its parent item.

    Args:
        ctx: Build context; ``groups()`` holds the joined roots and separate nodes.
        level: ``"low"`` (256 px, 16 samples) or ``"high"`` (see above, 128 samples).

    Returns:
        Wall-clock seconds spent baking.
    """
    start = time.monotonic()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES[level]
    scene.cycles.use_denoising = False
    scene.world = bpy.data.worlds.new("ao_world")
    scene.world.light_settings.distance = AO_DISTANCE_M
    for tag, name, objs in _bake_order(ctx):
        obj = objs[0]
        size = ao_resolution(ctx.items[tag]["type"], level)
        image = bpy.data.images.new(ao_image_name(name), size, size)
        image.colorspace_settings.name = "Non-Color"
        _add_ao_layer(obj)
        _wire_ao_image(obj, image)
        _select_only(obj)
        bpy.ops.object.bake(type="AO", margin=8, use_clear=True)
        image.pack()
    return time.monotonic() - start
