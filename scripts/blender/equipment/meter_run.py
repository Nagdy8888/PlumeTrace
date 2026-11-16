"""Metering run M-701 (10 x 2 x 1.5 m): meter tube, ultrasonic meter, bypass, valves, supports."""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.flange import FLANGE_THICKNESS_M, flange
from parts.shapes import block
from parts.valve import valve
from scene_setup import BuildContext

TUBE_RADIUS_M = 0.2
TUBE_Z_M = 1.0
METER_SIZE_M = (0.6, 0.5, 0.6)
BYPASS_RADIUS_M = 0.12
BYPASS_Y_M = 0.6
BYPASS_HALF_LENGTH_M = 4.0
VALVE_X_M = 3.5
SUPPORT_SIZE_M = (0.2, 1.6, 0.8)
SUPPORT_SPACING_M = 2.0


BYPASS_Z_M = SUPPORT_SIZE_M[2] + BYPASS_RADIUS_M  # the bypass bottom rests on the supports


def _lines(ctx: BuildContext, tag: str, length: float) -> None:
    """Meter tube, bypass and the two cross connections between them."""
    pipe_len = length - 2 * FLANGE_THICKNESS_M  # the end flanges take the last 0.04 m each
    tube = mesh_ops.cylinder(f"{tag}_tube", TUBE_RADIUS_M, pipe_len, (0.0, 0.0, TUBE_Z_M), axis="X")
    ctx.add_part(tag, tube, "pipe_gas")
    at = (0.0, BYPASS_Y_M, BYPASS_Z_M)
    bypass = mesh_ops.cylinder(
        f"{tag}_bypass", BYPASS_RADIUS_M, 2 * BYPASS_HALF_LENGTH_M, at, axis="X"
    )
    ctx.add_part(tag, bypass, "pipe_gas")
    for sign, label in ((-1, "w"), (1, "e")):
        cross_at = (sign * BYPASS_HALF_LENGTH_M, BYPASS_Y_M / 2, BYPASS_Z_M)
        cross = mesh_ops.cylinder(
            f"{tag}_cross_{label}", BYPASS_RADIUS_M, BYPASS_Y_M, cross_at, axis="Y"
        )
        ctx.add_part(tag, cross, "pipe_gas")


def _fittings(ctx: BuildContext, tag: str, length: float) -> None:
    """Flanges at the tube ends and the meter, and a valve on each line at x = +-3.5."""
    for sign, label in ((-1, "w"), (1, "e")):
        end = (sign * (length / 2 - FLANGE_THICKNESS_M / 2), 0.0, TUBE_Z_M)
        flange(ctx, tag, f"{tag}_end_flange_{label}", TUBE_RADIUS_M, end, "X")
        face = (sign * (METER_SIZE_M[0] / 2 + 0.03), 0.0, TUBE_Z_M)
        flange(ctx, tag, f"{tag}_meter_flange_{label}", TUBE_RADIUS_M, face, "X")
        on_tube = (sign * VALVE_X_M, 0.0, TUBE_Z_M)
        valve(ctx, tag, f"{tag}_valve_tube_{label}", TUBE_RADIUS_M, on_tube, "X")
        on_bypass = (sign * VALVE_X_M, BYPASS_Y_M, BYPASS_Z_M)
        valve(ctx, tag, f"{tag}_valve_bypass_{label}", BYPASS_RADIUS_M, on_bypass, "X")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build M-701: tube, meter body on the ``M-701.meter`` anchor, bypass, four valves, supports.

    Args:
        item: Spec item (``type`` ``meter_run``).
        ctx: Build context.
    """
    tag = item["tag"]
    length = item["size_m"][0]
    ctx.new_root(item)
    _lines(ctx, tag, length)
    _fittings(ctx, tag, length)
    meter = block(f"{tag}_meter", METER_SIZE_M, anchor_local(item, "meter"))
    ctx.add_part(tag, meter, "paint_grey")
    count = int(length / SUPPORT_SPACING_M)  # x = -4, -2, 0, 2, 4 for L = 10
    for i in range(count):
        x = (i - (count - 1) / 2) * SUPPORT_SPACING_M
        support = mesh_ops.box(
            f"{tag}_support_{i}", SUPPORT_SIZE_M, (x, 0.0, SUPPORT_SIZE_M[2] / 2)
        )
        ctx.add_part(tag, support, "paint_dark")
