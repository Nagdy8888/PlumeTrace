"""Filter separator V-100 (D 2 m, H 6 m): a vertical separator with a top platform."""

from typing import Any

from parts.separator import build_separator
from scene_setup import BuildContext


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build V-100: skirt, vessel, PSV, nozzles, level gauge, ring platform and caged ladder.

    Args:
        item: Spec item (``type`` ``filter_separator``).
        ctx: Build context.
    """
    build_separator(item, ctx, with_platform=True)
