"""Join each equipment item into one node, add anchors, and export the glb (bpy module)."""

from pathlib import Path

import bpy
from layout import to_local
from parts.mesh_ops import shade_by_angle
from scene_setup import BuildContext
from spec_loader import anchors_of

ANCHOR_DISPLAY_SIZE_M = 0.2


def add_anchors(ctx: BuildContext) -> None:
    """Create one empty per spec anchor (``<tag>.<anchor>``), parented to the item's root."""
    for tag, item in ctx.items.items():
        root = ctx.objects_by_tag[tag][0]
        for anchor_id, world in anchors_of(item):
            empty = bpy.data.objects.new(anchor_id, None)
            empty.empty_display_size = ANCHOR_DISPLAY_SIZE_M
            bpy.context.scene.collection.objects.link(empty)
            empty.parent = root
            empty.location = to_local(item, world)


def _apply_modifiers(obj: bpy.types.Object) -> None:
    """Replace ``obj``'s mesh by its evaluated mesh so modifiers (bevel) survive the join."""
    if not obj.modifiers:
        return
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = bpy.data.meshes.new_from_object(evaluated)
    old = obj.data
    obj.modifiers.clear()
    obj.data = mesh
    bpy.data.meshes.remove(old)


def join_equipment(ctx: BuildContext) -> None:
    """Join every static part of an item into its root, which is named exactly the tag.

    Anchor empties stay children of the root. Call before baking (one AO image per item).

    Args:
        ctx: Build context.
    """
    bpy.context.view_layer.update()
    for objs in ctx.objects_by_tag.values():
        root, parts = objs[0], objs[1:]
        for part in parts:
            _apply_modifiers(part)
        bpy.ops.object.select_all(action="DESELECT")
        for part in parts:
            part.select_set(True)
        root.select_set(True)
        bpy.context.view_layer.objects.active = root
        bpy.ops.object.join()
        shade_by_angle(root)


def export_glb(out: Path) -> None:
    """Export the whole scene as a binary glTF (Y-up, modifiers applied, no lights or cameras).

    Args:
        out: Target ``.glb`` path; its folder is created.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(out),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_cameras=False,
        export_lights=False,
        export_extras=False,
        use_selection=False,
    )
