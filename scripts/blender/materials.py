"""Principled BSDF materials from the Poly Haven CC0 textures (bpy module).

Every equipment item gets its own copy of each material it uses (``naming.material_name``)
because the copy carries that item's baked ambient-occlusion image (see ``bake.py``).
"""

from typing import Any

import bpy
from naming import material_name
from parts.mesh_ops import assign_box_uv
from scene_setup import BuildContext


def _spec(
    color: tuple[float, float, float] | None = None,
    rough: float | None = None,
    metallic: float = 0.0,
    diffuse: str | None = None,
    rough_tex: str | None = None,
    rough_factor: float = 1.0,
    normal: str | None = None,
    strength: float = 1.0,
    diffuse_factor: float = 1.0,
) -> dict[str, Any]:
    """Build one material table row.

    Args:
        color: Base colour (linear RGB), or ``None`` when a diffuse asset gives it.
        rough: Constant roughness, used when ``rough_tex`` is ``None``.
        metallic: Metallic value.
        diffuse: Poly Haven asset whose diffuse map is the base colour.
        rough_tex: Poly Haven asset whose roughness map (green channel) drives roughness.
        rough_factor: Factor on the roughness map.
        normal: Poly Haven asset whose normal map is used.
        strength: Normal map strength.
        diffuse_factor: Factor multiplied onto the diffuse map (darkens a texture that is too
            bright under the sun, e.g. the gravel yard).

    Returns:
        The row as a dict (keys of the ``SPECS`` consumers).
    """
    return dict(
        color=color,
        rough=rough,
        metallic=metallic,
        diffuse=diffuse,
        rough_tex=rough_tex,
        rough_factor=rough_factor,
        normal=normal,
        strength=strength,
        diffuse_factor=diffuse_factor,
    )


# Owner ruling C1 (spike review): the tread-plate maps of ``metal_plate`` are never mapped onto
# painted vessels, pipes or panels, so every ``paint_*`` and ``pipe_gas`` has a constant roughness
# and no normal map. Texture sets are used only where they are the real surface.
# Owner ruling C2 (spike review): the gravel must not read as snow, so its diffuse map is
# multiplied by a factor in the 0.4 to 0.7 band.
GRAVEL_FACTOR = 0.45
SPECS: dict[str, dict[str, Any]] = {
    "paint_grey": _spec(color=(0.50, 0.52, 0.50), rough=0.5, metallic=0.3),
    "paint_dark": _spec(color=(0.12, 0.13, 0.14), rough=0.6, metallic=0.4),
    "paint_red": _spec(color=(0.50, 0.05, 0.04), rough=0.5, metallic=0.2),
    "paint_white": _spec(color=(0.80, 0.80, 0.78), rough=0.5, metallic=0.2),
    "pipe_gas": _spec(color=(0.60, 0.58, 0.40), rough=0.55, metallic=0.3),
    "pipe_vent": _spec(color=(0.45, 0.47, 0.48), rough=0.55, metallic=0.3),
    "pipe_condensate": _spec(color=(0.28, 0.20, 0.12), rough=0.55, metallic=0.3),
    "pipe_fuel": _spec(color=(0.70, 0.55, 0.05), rough=0.55, metallic=0.3),
    "asphalt": _spec(color=(0.06, 0.06, 0.06), rough=0.9),
    "safety_yellow": _spec(color=(0.78, 0.55, 0.03), rough=0.55, metallic=0.1),
    "glass": _spec(color=(0.05, 0.07, 0.08), rough=0.1),
    "building_panel": _spec(
        color=(0.62, 0.62, 0.58), rough=0.7, metallic=0.1, normal="concrete_floor_02", strength=0.3
    ),
    "grating": _spec(
        diffuse="metal_grate_rusty",
        rough_tex="metal_grate_rusty",
        metallic=0.7,
        normal="metal_grate_rusty",
    ),
    "concrete": _spec(
        diffuse="concrete_floor_02", rough_tex="concrete_floor_02", normal="concrete_floor_02"
    ),
    "gravel": _spec(
        diffuse="gravel_floor_02",
        rough_tex="gravel_floor_02",
        normal="gravel_floor_02",
        diffuse_factor=GRAVEL_FACTOR,
    ),
    "gravel_far": _spec(
        diffuse="gravel_floor_02",
        rough=1.0,
        normal="gravel_floor_02",
        diffuse_factor=GRAVEL_FACTOR,
    ),
    "cladding": _spec(
        diffuse="corrugated_iron_02",
        rough_tex="corrugated_iron_02",
        metallic=0.6,
        normal="corrugated_iron_02",
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


def make_material(
    key: str, tag: str, ctx: BuildContext, paint_value: float = 1.0
) -> bpy.types.Material:
    """Build the per-equipment copy of material ``key`` for ``tag``.

    Args:
        key: Key of ``SPECS``.
        tag: Equipment tag or separate-node name (named in the material so the AO image can be
            attached per item).
        ctx: Build context (texture folder).
        paint_value: Factor on the base colour of ``paint_*`` keys (the item's seeded +-2 %).

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
        colour = tex.outputs["Color"]
        if spec["diffuse_factor"] != 1.0:
            tint = nodes.new("ShaderNodeMix")
            tint.data_type = "RGBA"
            tint.blend_type = "MULTIPLY"
            tint.inputs["Factor"].default_value = 1.0
            tint.inputs["B"].default_value = (*(spec["diffuse_factor"],) * 3, 1.0)
            links.new(colour, tint.inputs["A"])
            colour = tint.outputs["Result"]
        links.new(colour, bsdf.inputs["Base Color"])
    else:
        factor = paint_value if key.startswith("paint_") else 1.0
        bsdf.inputs["Base Color"].default_value = (*(c * factor for c in spec["color"]), 1.0)
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
    for tag, name, objs in ctx.groups():
        copies: dict[str, bpy.types.Material] = {}
        for obj in objs[1:]:
            key = obj["material"]
            if key not in copies:
                copies[key] = make_material(key, name, ctx, ctx.paint_value[tag])
            assign_box_uv(obj, obj["tile_m"])
            obj.data.materials.append(copies[key])
