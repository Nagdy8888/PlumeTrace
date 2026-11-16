"""Flare knockout drum V-602 (6 x 2 x 2.5 m): horizontal vessel on saddles with a PSV."""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.flange import flange
from parts.nozzle import nozzle
from parts.saddle import saddle
from parts.vessel import vessel
from scene_setup import BuildContext

DIAMETER_M = 2.0
CENTRE_Z_M = 1.25
PSV_BODY_RADIUS_M = 0.12
PSV_BODY_HEIGHT_M = 0.5
PSV_OUTLET_RADIUS_M = 0.08
DRAIN_RADIUS_M = 0.1
DRAIN_LENGTH_M = 0.2


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build V-602: vessel (total length L), two saddles, PSV with its outlet pipe, drain nozzle.

    The PSV outlet pipe rises to the ``V-602.psv`` anchor (z 4.0).

    Args:
        item: Spec item (``type`` ``knockout_drum``).
        ctx: Build context.
    """
    tag = item["tag"]
    length = item["size_m"][0]
    ctx.new_root(item)
    vessel(
        ctx, tag, f"{tag}_vessel", DIAMETER_M, length - DIAMETER_M / 2, "X", (0.0, 0.0, CENTRE_Z_M)
    )
    for sign, label in ((1, "e"), (-1, "w")):
        saddle(ctx, tag, f"{tag}_saddle_{label}", DIAMETER_M, sign * length / 4, CENTRE_Z_M)
    body_bottom = CENTRE_Z_M + DIAMETER_M / 2
    body = mesh_ops.cylinder(
        f"{tag}_psv_body",
        PSV_BODY_RADIUS_M,
        PSV_BODY_HEIGHT_M,
        (0.0, 0.0, body_bottom + PSV_BODY_HEIGHT_M / 2),
    )
    ctx.add_part(tag, body, "paint_grey")
    flange(ctx, tag, f"{tag}_psv_flange", PSV_BODY_RADIUS_M, (0.0, 0.0, body_bottom + 0.1))
    outlet_bottom = body_bottom + PSV_BODY_HEIGHT_M
    outlet_top = anchor_local(item, "psv")[2]
    outlet = mesh_ops.cylinder(
        f"{tag}_psv_outlet",
        PSV_OUTLET_RADIUS_M,
        outlet_top - outlet_bottom,
        (0.0, 0.0, (outlet_top + outlet_bottom) / 2),
    )
    ctx.add_part(tag, outlet, "paint_grey")
    drain_x = -(length / 2 - DIAMETER_M / 4 - 0.2)  # under the -x end, clear of the head
    nozzle(
        ctx,
        tag,
        f"{tag}_drain",
        DRAIN_RADIUS_M,
        DRAIN_LENGTH_M,
        (drain_x, 0.0, CENTRE_Z_M - DIAMETER_M / 2),
        "-Z",
    )
