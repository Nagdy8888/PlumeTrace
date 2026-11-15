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
    args = parser.parse_args(argv)
    only = frozenset(t for t in args.only.split(",") if t) or None
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    names = node_names(read_glb_json(args.glb))
    missing = sorted(required_names(spec, only) - names)
    size = args.glb.stat().st_size
    if missing:
        print(f"missing nodes: {missing}")
        return 1
    if args.max_bytes is not None and size > args.max_bytes:
        print(f"glb is {size} bytes, budget {args.max_bytes}")
        return 1
    print(f"glb OK: {len(names)} nodes, {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
