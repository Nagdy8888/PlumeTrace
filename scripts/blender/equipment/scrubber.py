"""Inlet scrubbers V-211..V-213 (D 1.5 m, H 5 m): a vertical separator without a platform."""

from typing import Any

from parts.separator import build_separator
from scene_setup import BuildContext


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build a scrubber: skirt, vessel, PSV on top, nozzles, level gauge and an uncaged ladder.

    Args:
        item: Spec item (``type`` ``scrubber``).
        ctx: Build context.
    """
    build_separator(item, ctx, with_platform=False)
