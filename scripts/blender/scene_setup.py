"""Scene reset and the build context shared by every equipment builder (bpy module)."""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import bpy
import numpy as np
from parts.mesh_ops import parent_to


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
        items: Spec item of each tag that was built.
    """

    spec: dict[str, Any]
    textures_dir: Path
    rng: np.random.Generator
    objects_by_tag: dict[str, list[bpy.types.Object]] = field(default_factory=dict)
    items: dict[str, dict[str, Any]] = field(default_factory=dict)

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
        return root

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
