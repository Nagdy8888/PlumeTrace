"""Scene reset and the build context shared by every equipment builder (bpy module)."""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import bpy
import numpy as np
from naming import part_name
from parts.mesh_ops import parent_to

PAINT_JITTER = 0.02  # +-2 % paint value per item


def reset_scene() -> None:
    """Empty the scene and set metric units with unit scale 1.0 (1 unit = 1 m)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    units = bpy.context.scene.unit_settings
    units.system = "METRIC"
    units.scale_length = 1.0


@dataclass
class BuildContext:
    """State shared by the build steps.

    Attributes:
        spec: The facility spec (``ks07.json``).
        textures_dir: Folder with the Poly Haven texture sub-folders.
        rng: Seeded random generator (the model must be reproducible).
        objects_by_tag: Per equipment tag: the root object first, then its parts.
        nodes: Per separate node (``<tag>__<part>``): the node object first, then its parts.
        items: Spec item of each tag that was built.
        paint_value: Per tag: the seeded factor (1 +- 2 %) applied to its ``paint_*`` colours.
    """

    spec: dict[str, Any]
    textures_dir: Path
    rng: np.random.Generator
    objects_by_tag: dict[str, list[bpy.types.Object]] = field(default_factory=dict)
    nodes: dict[str, list[bpy.types.Object]] = field(default_factory=dict)
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    paint_value: dict[str, float] = field(default_factory=dict)

    def new_root(self, item: dict[str, Any]) -> bpy.types.Object:
        """Create the item's root object (empty mesh) at its position and rotation.

        Parts are parented to it in item-local coordinates; before export all parts are joined
        into it, so the root becomes the one node named exactly the tag.

        Args:
            item: Spec item (``tag``, ``position_m``, ``rotation_deg``).

        Returns:
            The root object.
        """
        tag = item["tag"]
        root = bpy.data.objects.new(tag, bpy.data.meshes.new(tag))
        bpy.context.scene.collection.objects.link(root)
        root.location = item["position_m"]
        root.rotation_euler = (0.0, 0.0, math.radians(float(item.get("rotation_deg", 0.0))))
        self.objects_by_tag[tag] = [root]
        self.items[tag] = item
        self.paint_value[tag] = float(self.rng.uniform(1 - PAINT_JITTER, 1 + PAINT_JITTER))
        return root

    def new_node(self, tag: str, part: str, pivot: tuple[float, float, float]) -> bpy.types.Object:
        """Create a part that stays its own glb node ``<tag>__<part>`` (fans, flare tip).

        The node is parented to the item's root with its origin at ``pivot`` (item-local);
        parts added with :meth:`add_node_part` are positioned relative to that pivot and are
        joined into the node at export.

        Args:
            tag: Equipment tag.
            part: Part name, e.g. ``"fan_1"`` (see ``naming.part_name``).
            pivot: Item-local position of the node's origin (e.g. the fan hub).

        Returns:
            The node object.
        """
        name = part_name(tag, part)
        node = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        bpy.context.scene.collection.objects.link(node)
        parent_to(node, self.objects_by_tag[tag][0])
        node.location = pivot
        self.nodes[name] = [node]
        return node

    def add_node_part(
        self, node: bpy.types.Object, obj: bpy.types.Object, material: str, tile_m: float = 2.0
    ) -> bpy.types.Object:
        """Parent a part to a separate node (location relative to the node's pivot).

        Args:
            node: The object returned by :meth:`new_node`.
            obj: The part object.
            material: Material key of ``materials.py``.
            tile_m: Texture repeat length in metres.

        Returns:
            ``obj``.
        """
        parent_to(obj, node)
        obj["material"] = material
        obj["tile_m"] = tile_m
        self.nodes[node.name].append(obj)
        return obj

    def groups(self) -> list[tuple[str, str, list[bpy.types.Object]]]:
        """Every joinable group: ``(tag, name, objects)`` with the node or root object first.

        Returns:
            Root groups (name = tag) followed by separate-node groups (name = ``<tag>__<part>``).
        """
        roots = [(tag, tag, objs) for tag, objs in self.objects_by_tag.items()]
        nodes = [(name.split("__")[0], name, objs) for name, objs in self.nodes.items()]
        return roots + nodes

    def add_part(
        self, tag: str, obj: bpy.types.Object, material: str, tile_m: float = 2.0
    ) -> bpy.types.Object:
        """Parent a part to its root and record its material key and UV tile size.

        Args:
            tag: Equipment tag.
            obj: The part object (location is item-local).
            material: Material key of ``materials.py``.
            tile_m: Texture repeat length in metres.

        Returns:
            ``obj``.
        """
        root = self.objects_by_tag[tag][0]
        parent_to(obj, root)
        obj["material"] = material
        obj["tile_m"] = tile_m
        self.objects_by_tag[tag].append(obj)
        return obj
