"""Node, material and image names of the exported glb (names are contracts).

The frontend ``nodeIndex`` and the backend candidate list use the same ids. Pure, no ``bpy``.
"""


def node_name(tag: str) -> str:
    """Name of an equipment root node: exactly the tag."""
    return tag


def part_name(tag: str, part: str) -> str:
    """Name of a part that stays a separate node, e.g. ``E-231__fan_1``."""
    return f"{tag}__{part}"


def material_name(base: str, tag: str) -> str:
    """Name of the per-equipment copy of a material (it carries that equipment's AO image)."""
    return f"{base}__{tag}"


def ao_image_name(tag: str) -> str:
    """Name of the baked ambient-occlusion image of an equipment item."""
    return f"{tag}_ao"
