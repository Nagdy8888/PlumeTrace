"""Principled BSDF materials from the Poly Haven CC0 textures (bpy module).

Every equipment item gets its own copy of each material it uses (``naming.material_name``)
because the copy carries that item's baked ambient-occlusion image (see ``bake.py``).
"""

from typing import Any

import bpy
from naming import material_name
from parts.mesh_ops import assign_box_uv
from scene_setup import BuildContext

STEEL = "metal_plate"
# key: base colour (linear), roughness, metallic, diffuse asset, rough asset, roughness factor,
#      normal asset, normal strength
SPECS: dict[str, dict[str, Any]] = {
    "paint_grey": dict(
        color=(0.50, 0.52, 0.50),
        rough=None,
        metallic=0.3,
        diffuse=None,
        rough_tex=STEEL,
        rough_factor=0.8,
        normal=STEEL,
        strength=0.6,
    ),
    "paint_dark": dict(
        color=(0.12, 0.13, 0.14),
        rough=0.6,
        metallic=0.4,
        diffuse=None,
        rough_tex=None,
        rough_factor=1.0,
        normal=STEEL,
        strength=0.6,
    ),
    "safety_yellow": dict(
        color=(0.78, 0.55, 0.03),
        rough=0.55,
        metallic=0.1,
        diffuse=None,
        rough_tex=None,
        rough_factor=1.0,
        normal=None,
        strength=1.0,
    ),
    "concrete": dict(
        color=None,
        rough=None,
        metallic=0.0,
        diffuse="concrete_floor_02",
        rough_tex="concrete_floor_02",
        rough_factor=1.0,
        normal="concrete_floor_02",
        strength=1.0,
    ),
    "gravel": dict(
        color=None,
        rough=None,
        metallic=0.0,
        diffuse="gravel_floor_02",
        rough_tex="gravel_floor_02",
        rough_factor=1.0,
        normal="gravel_floor_02",
        strength=1.0,
    ),
    "cladding": dict(
        color=None,
        rough=None,
        metallic=0.6,
        diffuse="corrugated_iron_02",
        rough_tex="corrugated_iron_02",
        rough_factor=1.0,
        normal="corrugated_iron_02",
        strength=1.0,
    ),
}


def _tex(
    mat: bpy.types.Material,
    ctx: BuildContext,
    asset: str,
    kind: str,
    srgb: bool,
    uv: bpy.types.Node,
) -> bpy.types.Node:
    """Add an Image Texture node for ``<asset>_<kind>_1k.jpg`` fed by the UVMap node."""
    path = next((ctx.textures_dir / asset).glob(f"*_{kind}_1k.jpg"))
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(path), check_existing=True)
    node.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    mat.node_tree.links.new(uv.outputs["UV"], node.inputs["Vector"])
    return node


def _link_roughness(
    mat: bpy.types.Material,
    ctx: BuildContext,
    spec: dict[str, Any],
    bsdf: bpy.types.Node,
    uv: bpy.types.Node,
) -> None:
    """Roughness from the texture's green channel (times a factor), or a constant."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    if spec["rough_tex"] is None:
        bsdf.inputs["Roughness"].default_value = spec["rough"]
        return
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(_tex(mat, ctx, spec["rough_tex"], "rough", False, uv).outputs["Color"], sep.inputs[0])
    out = sep.outputs["Green"]
    if spec["rough_factor"] != 1.0:
        mul = nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = spec["rough_factor"]
        links.new(out, mul.inputs[0])
        out = mul.outputs[0]
    links.new(out, bsdf.inputs["Roughness"])


def make_material(key: str, tag: str, ctx: BuildContext) -> bpy.types.Material:
    """Build the per-equipment copy of material ``key`` for ``tag``.

    Args:
        key: Key of ``SPECS``.
        tag: Equipment tag (named in the material so the AO image can be attached per item).
        ctx: Build context (texture folder).

    Returns:
        The new material.
    """
    spec = SPECS[key]
    mat = bpy.data.materials.new(material_name(key, tag))
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Metallic"].default_value = spec["metallic"]
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    if spec["diffuse"]:
        tex = _tex(mat, ctx, spec["diffuse"], "diff", True, uv)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*spec["color"], 1.0)
    _link_roughness(mat, ctx, spec, bsdf, uv)
    if spec["normal"]:
        normal = nodes.new("ShaderNodeNormalMap")
        normal.uv_map = "UVMap"
        normal.inputs["Strength"].default_value = spec["strength"]
        tex = _tex(mat, ctx, spec["normal"], "nor_gl", False, uv)
        links.new(tex.outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def assign_all(ctx: BuildContext) -> None:
    """Write the box UVs and assign each part its per-equipment material copy.

    Args:
        ctx: Build context; every part carries ``material`` and ``tile_m`` custom properties.
    """
    bpy.context.view_layer.update()
    for tag, objs in ctx.objects_by_tag.items():
        copies: dict[str, bpy.types.Material] = {}
        for obj in objs[1:]:
            key = obj["material"]
            if key not in copies:
                copies[key] = make_material(key, tag, ctx)
            assign_box_uv(obj, obj["tile_m"])
            obj.data.materials.append(copies[key])
