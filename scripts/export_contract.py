"""Export the facility JSON Schema and facility data for the frontend.

The Pydantic models in ``plumetrace.facility`` are the source of truth. This script writes
the JSON Schema (input of ``npm run gen:types``) and the KS-07 facility as JSON. The output is
deterministic: UTF-8, LF line endings, sorted keys, trailing newline.

Run it from the repo root::

    cd app && uv run python ../scripts/export_contract.py

The outputs are generated - never edit them by hand.
"""

import json
from pathlib import Path
from typing import Final, cast

from plumetrace.facility.loader import load_facility
from plumetrace.facility.spec import FacilitySpec

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SCHEMA_OUT: Final[Path] = REPO_ROOT / "app/frontend/src/shared/types/generated/contract.schema.json"
FACILITY_OUT: Final[Path] = REPO_ROOT / "app/frontend/src/shared/facility/ks07.json"


def _tuples_as_items(node: object) -> object:
    """Rewrite ``prefixItems`` to the draft-07 ``items`` array form.

    Pydantic emits JSON Schema 2020-12 ``prefixItems`` for fixed-length tuples.
    json-schema-to-typescript 16.0.0 ignores ``prefixItems`` and types the members as
    ``unknown``; ``items: [...]`` together with ``minItems`` and ``maxItems`` gives
    ``[number, number, number]``.

    Args:
        node: A JSON Schema node (dict, list or scalar), rewritten recursively.

    Returns:
        A copy of ``node`` with every ``prefixItems`` key renamed to ``items``.

    Raises:
        ValueError: If a node has both ``prefixItems`` and ``items``.
    """
    if isinstance(node, dict):
        if "prefixItems" in node and "items" in node:
            raise ValueError("schema node has both prefixItems and items")
        return {
            ("items" if k == "prefixItems" else k): _tuples_as_items(v) for k, v in node.items()
        }
    if isinstance(node, list):
        return [_tuples_as_items(v) for v in node]
    return node


def build_contract_schema() -> dict[str, object]:
    """Build the JSON Schema of the facility model.

    Returns:
        The ``FacilitySpec`` JSON Schema with ``title`` set to ``FacilitySpec`` and fixed-length
        tuples in the ``items`` array form (see ``_tuples_as_items``).
    """
    schema = cast(dict[str, object], _tuples_as_items(FacilitySpec.model_json_schema()))
    schema["title"] = "FacilitySpec"
    return schema


def build_facility_json(spec: FacilitySpec) -> dict[str, object]:
    """Convert a facility spec to JSON-compatible data.

    Args:
        spec: The validated facility.

    Returns:
        The spec as plain dicts, lists and scalars.
    """
    return spec.model_dump(mode="json")


def write_json(path: Path, data: object) -> None:
    """Write ``data`` as deterministic JSON (UTF-8, LF, sorted keys, trailing newline).

    Bytes are written so Windows never converts LF line endings to CRLF.

    Args:
        path: Target file; parent directories are created.
        data: JSON-serialisable data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))


def main() -> int:
    """Write the schema and the facility JSON, print both paths.

    Returns:
        Exit code 0.
    """
    write_json(SCHEMA_OUT, build_contract_schema())
    write_json(FACILITY_OUT, build_facility_json(load_facility()))
    for out in (SCHEMA_OUT, FACILITY_OUT):
        print(out.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
