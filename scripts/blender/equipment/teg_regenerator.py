"""TEG regenerator R-302 (4 x 2 x 8 m): reboiler, firebox, burner stack, still column, drum."""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.flange import flange
from parts.saddle import saddle
from parts.shapes import block
from parts.vessel import vessel
from scene_setup import BuildContext

REBOILER_DIAMETER_M = 1.4
REBOILER_Z_M = 1.3
FIREBOX_M = 1.2
BURNER_RADIUS_M = 0.15
BURNER_TOP_Z_M = 5.0
STILL_RADIUS_M = 0.2
SURGE_DIAMETER_M = 0.8
SURGE_LENGTH_M = 2.0
SURGE_Y_M = 1.2
SURGE_Z_M = 0.8


def _still_column(ctx: BuildContext, item: dict[str, Any]) -> None:
    """Still column from the reboiler top to the ``R-302.still_vent`` anchor, with a flange."""
    tag = item["tag"]
    bottom = REBOILER_Z_M + REBOILER_DIAMETER_M / 2
    top = anchor_local(item, "still_vent")[2]
    column = mesh_ops.cylinder(
        f"{tag}_still", STILL_RADIUS_M, top - bottom, (0.0, 0.0, (top + bottom) / 2)
    )
    ctx.add_part(tag, column, "paint_grey")
    flange(ctx, tag, f"{tag}_still_flange", STILL_RADIUS_M, (0.0, 0.0, bottom + 1.5))


def _burner(ctx: BuildContext, tag: str, length: float) -> None:
    """Firebox on the ground at the -x end and the burner stack above it."""
    x = -length / 2 + FIREBOX_M / 2
    box = block(f"{tag}_firebox", (FIREBOX_M, FIREBOX_M, FIREBOX_M), (x, 0.0, FIREBOX_M / 2))
    ctx.add_part(tag, box, "paint_dark")
    stack_x = -length / 2 + 0.4
    stack = mesh_ops.cylinder(
        f"{tag}_burner",
        BURNER_RADIUS_M,
        BURNER_TOP_Z_M - FIREBOX_M,
        (stack_x, 0.0, (BURNER_TOP_Z_M + FIREBOX_M) / 2),
    )
    ctx.add_part(tag, stack, "paint_dark")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build R-302: reboiler on two saddles, firebox, burner stack, still column, surge drum.

    The still column's top is the ``R-302.still_vent`` anchor (z 8.0).

    Args:
        item: Spec item (``type`` ``teg_regenerator``).
        ctx: Build context.
    """
    tag = item["tag"]
    length = item["size_m"][0]
    ctx.new_root(item)
    shell = length - REBOILER_DIAMETER_M / 2
    vessel(ctx, tag, f"{tag}_reboiler", REBOILER_DIAMETER_M, shell, "X", (0.0, 0.0, REBOILER_Z_M))
    for sign, label in ((1, "e"), (-1, "w")):
        saddle(
            ctx, tag, f"{tag}_saddle_{label}", REBOILER_DIAMETER_M, sign * length / 4, REBOILER_Z_M
        )
    _burner(ctx, tag, length)
    _still_column(ctx, item)
    surge = (0.0, SURGE_Y_M, SURGE_Z_M)
    vessel(
        ctx,
        tag,
        f"{tag}_surge",
        SURGE_DIAMETER_M,
        SURGE_LENGTH_M - SURGE_DIAMETER_M / 2,
        "X",
        surge,
    )
    for sign, label in ((1, "e"), (-1, "w")):
        saddle(
            ctx,
            tag,
            f"{tag}_surge_saddle_{label}",
            SURGE_DIAMETER_M,
            sign * 0.5,
            SURGE_Z_M,
            y_m=SURGE_Y_M,
        )
