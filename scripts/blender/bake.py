"""Cycles ambient-occlusion bake per equipment item into a second UV set (bpy module).

The baked image is wired through a Separate Color node (R) into the ``Occlusion`` input of the
``glTF Material Output`` node group, which the glTF exporter writes as ``occlusionTexture``.
"""

import time

import bpy
from naming import ao_image_name
from scene_setup import BuildContext

GROUP_NAME = "glTF Material Output"
RESOLUTION = {"low": 512, "high": 1024}
SAMPLES = {"low": 16, "high": 128}
GROUND_RESOLUTION = 512
AO_DISTANCE_M = 6.0


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
    """Add the ``AO`` UV layer, pack all faces into it, and keep ``UVMap`` for rendering."""
    layers = obj.data.uv_layers
    layers.new(name="AO")
    layers["UVMap"].active_render = True
    layers.active = layers["AO"]
    _select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.lightmap_pack(
        PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_MARGIN_DIV=0.2
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


def bake_all(ctx: BuildContext, level: str) -> float:
    """Bake ambient occlusion for every equipment object (other objects still occlude).

    Args:
        ctx: Build context; ``objects_by_tag`` holds the joined equipment roots.
        level: ``"low"`` (512 px, 16 samples) or ``"high"`` (1024 px, 128 samples).

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
    for tag, objs in ctx.objects_by_tag.items():
        obj = objs[0]
        size = GROUND_RESOLUTION if tag == "ground" else RESOLUTION[level]
        image = bpy.data.images.new(ao_image_name(tag), size, size)
        image.colorspace_settings.name = "Non-Color"
        _add_ao_layer(obj)
        _wire_ao_image(obj, image)
        _select_only(obj)
        bpy.ops.object.bake(type="AO", margin=8, use_clear=True)
        image.pack()
    return time.monotonic() - start
