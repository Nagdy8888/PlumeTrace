"""Check an exported glb: valid header, every spec tag and anchor present, size within budget.

Run it from the repo root::

    cd app && uv run python ../scripts/check_glb.py --glb frontend/public/models/ks07.glb \
        --spec frontend/src/shared/facility/ks07.json --only K-202,VS-250 --max-bytes 2000000

Stdlib only.
"""

import argparse
import json
import struct
from collections.abc import Sequence
from pathlib import Path
from typing import Any

GLB_MAGIC = b"glTF"
JSON_CHUNK_TYPE = 0x4E4F534A
TRIANGLES = 4  # glTF primitive mode; a primitive without a mode is a triangle list
SEPARATE_NODES = {"fin_fan_cooler": ("fan_1", "fan_2"), "flare_stack": ("tip",)}


def read_glb_json(path: Path) -> dict[str, Any]:
    """Validate the GLB header and return the JSON chunk.

    Args:
        path: The ``.glb`` file.

    Returns:
        The parsed glTF JSON.

    Raises:
        ValueError: If the magic, version or first chunk type is wrong, or the chunk is cut off.
    """
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("file too short for a glb")
    if data[:4] != GLB_MAGIC:
        raise ValueError("bad magic: not a glb")
    version = struct.unpack_from("<I", data, 4)[0]
    if version != 2:
        raise ValueError(f"unsupported glb version {version}")
    length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != JSON_CHUNK_TYPE:
        raise ValueError("first chunk is not JSON")
    if 20 + length > len(data):
        raise ValueError("JSON chunk is cut off")
    gltf: dict[str, Any] = json.loads(data[20 : 20 + length].decode("utf-8"))
    return gltf


def node_names(gltf: dict[str, Any]) -> set[str]:
    """Return the names of every node that has one."""
    return {n["name"] for n in gltf.get("nodes", []) if "name" in n}


def required_names(spec: dict[str, Any], only: frozenset[str] | None) -> set[str]:
    """Return the selected equipment tags and all their anchor ids.

    Args:
        spec: The facility spec (``ks07.json``).
        only: Tags to check, or ``None`` for every item.

    Returns:
        The node names the glb must contain.
    """
    names: set[str] = set()
    for item in spec["equipment"]:
        if only is None or item["tag"] in only:
            names.add(item["tag"])
            names.update(a["id"] for a in item.get("anchors", []))
    return names


def separate_node_names(spec: dict[str, Any], only: frozenset[str] | None) -> set[str]:
    """Return the names of the separate (animatable) nodes ``<tag>__<part>`` of the selected items.

    The Blender generator keeps the two fans of a fin-fan cooler and the flare tip as nodes of
    their own (``E-231__fan_1``, ``FL-601__tip``); an optimiser that dedups or instances identical
    meshes can drop them, so they are required like tags and anchors.

    Args:
        spec: The facility spec (``ks07.json``).
        only: Tags to check, or ``None`` for every item.

    Returns:
        The separate node names the glb must contain.
    """
    return {
        f"{item['tag']}__{part}"
        for item in spec["equipment"]
        if only is None or item["tag"] in only
        for part in SEPARATE_NODES.get(item["type"], ())
    }


def _instance_count(node: dict[str, Any], accessors: list[dict[str, Any]]) -> int:
    """Instances a node draws: the ``EXT_mesh_gpu_instancing`` accessor count, else 1."""
    ext = node.get("extensions", {}).get("EXT_mesh_gpu_instancing")
    if ext is None:
        return 1
    return max(accessors[i]["count"] for i in ext["attributes"].values())


def _mesh_primitives(gltf: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Every (node with a mesh, primitive of that mesh) pair of the glTF."""
    meshes = gltf.get("meshes", [])
    return [
        (node, primitive)
        for node in gltf.get("nodes", [])
        if "mesh" in node
        for primitive in meshes[node["mesh"]]["primitives"]
    ]


def triangle_count(gltf: dict[str, Any]) -> int:
    """Count the triangles drawn per frame, instances included.

    Args:
        gltf: The glTF JSON.

    Returns:
        The sum over every node with a mesh of the triangle-list primitives' index count // 3
        (``POSITION`` count // 3 without indices), times the node's instance count.
    """
    accessors = gltf.get("accessors", [])
    total = 0
    for node, primitive in _mesh_primitives(gltf):
        if primitive.get("mode", TRIANGLES) != TRIANGLES:
            continue
        source = primitive.get("indices", primitive["attributes"]["POSITION"])
        total += accessors[source]["count"] // 3 * _instance_count(node, accessors)
    return total


def draw_call_estimate(gltf: dict[str, Any]) -> int:
    """Estimate the draw calls: one per (node with a mesh, primitive).

    An instanced node counts once per primitive.

    Args:
        gltf: The glTF JSON.

    Returns:
        The number of (node, primitive) pairs.
    """
    return len(_mesh_primitives(gltf))


def main(argv: Sequence[str] | None = None) -> int:
    """Check the glb; print the result.

    Args:
        argv: Command-line arguments (default: ``sys.argv``).

    Returns:
        0 when valid, complete and within budget; 1 otherwise.
    """
    parser = argparse.ArgumentParser(description="Check an exported glb against the spec.")
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--only", default="", help="comma-separated tags (default: all)")
    parser.add_argument("--max-bytes", type=int, default=None)
    parser.add_argument("--max-triangles", type=int, default=None)
    parser.add_argument("--max-draw-calls", type=int, default=None)
    args = parser.parse_args(argv)
    only = frozenset(t for t in args.only.split(",") if t) or None
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    gltf = read_glb_json(args.glb)
    names = node_names(gltf)
    missing = sorted((required_names(spec, only) | separate_node_names(spec, only)) - names)
    size = args.glb.stat().st_size
    tris, calls = triangle_count(gltf), draw_call_estimate(gltf)
    if missing:
        print(f"missing nodes: {missing}")
        return 1
    for label, value, limit in (
        ("bytes", size, args.max_bytes),
        ("triangles", tris, args.max_triangles),
        ("draw calls", calls, args.max_draw_calls),
    ):
        if limit is not None and value > limit:
            print(f"glb has {value} {label}, budget {limit}")
            return 1
    print(f"glb OK: {len(names)} nodes, {size} bytes, {tris} triangles, {calls} draw calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
