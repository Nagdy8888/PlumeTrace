"""Vapour recovery unit VRU-410 (4 x 3 x 2.5 m): screw compressor, motor, scrubber, panel."""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.flange import flange
from parts.shapes import block
from parts.skid import skid
from parts.vessel import vessel
from scene_setup import BuildContext

SKID_HEIGHT_M = 0.25
COMPRESSOR_SIZE_M = (1.6, 1.0, 1.0)
COMPRESSOR_X_M = -0.5
MOTOR_RADIUS_M = 0.35
MOTOR_LENGTH_M = 1.0
MOTOR_X_M = 0.9
SCRUBBER_DIAMETER_M = 0.6
SCRUBBER_SHELL_M = 1.4
SCRUBBER_AT_M = (-1.5, 1.0)
PANEL_SIZE_M = (0.8, 0.3, 1.6)
PANEL_Y_M = -1.3
SPOOL_RADIUS_M = 0.06


def _drive(ctx: BuildContext, tag: str) -> None:
    """Motor on a foot, aligned with the compressor shaft, and the coupling between them."""
    z = SKID_HEIGHT_M + COMPRESSOR_SIZE_M[2] / 2
    motor = mesh_ops.cylinder(
        f"{tag}_motor", MOTOR_RADIUS_M, MOTOR_LENGTH_M, (MOTOR_X_M, 0.0, z), axis="X"
    )
    ctx.add_part(tag, motor, "paint_grey")
    foot_h = z - MOTOR_RADIUS_M - SKID_HEIGHT_M
    foot = mesh_ops.box(
        f"{tag}_motor_foot", (0.7, 0.5, foot_h), (MOTOR_X_M, 0.0, SKID_HEIGHT_M + foot_h / 2)
    )
    ctx.add_part(tag, foot, "paint_dark")
    start = COMPRESSOR_X_M + COMPRESSOR_SIZE_M[0] / 2
    end = MOTOR_X_M - MOTOR_LENGTH_M / 2
    coupling = mesh_ops.cylinder(
        f"{tag}_coupling", 0.1, end - start, ((start + end) / 2, 0.0, z), axis="X"
    )
    ctx.add_part(tag, coupling, "safety_yellow")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build VRU-410: skid, compressor box with a discharge spool, motor, scrubber, panel.

    The 0.25 m discharge spool on the compressor top (z 1.25) reaches the ``VRU-410.skid`` anchor.

    Args:
        item: Spec item (``type`` ``vru``).
        ctx: Build context.
    """
    tag = item["tag"]
    length, width, _ = item["size_m"]
    ctx.new_root(item)
    skid(ctx, tag, length, width, SKID_HEIGHT_M)
    cz = SKID_HEIGHT_M + COMPRESSOR_SIZE_M[2] / 2
    compressor = block(f"{tag}_compressor", COMPRESSOR_SIZE_M, (COMPRESSOR_X_M, 0.0, cz))
    ctx.add_part(tag, compressor, "paint_grey")
    _drive(ctx, tag)
    top = SKID_HEIGHT_M + COMPRESSOR_SIZE_M[2]
    ax, ay, az = anchor_local(item, "skid")
    spool = mesh_ops.cylinder(f"{tag}_spool", SPOOL_RADIUS_M, az - top, (ax, ay, (az + top) / 2))
    ctx.add_part(tag, spool, "pipe_gas")
    flange(ctx, tag, f"{tag}_spool_flange", SPOOL_RADIUS_M, (ax, ay, az - 0.03))
    head = SCRUBBER_DIAMETER_M / 4
    sx, sy = SCRUBBER_AT_M
    centre = SKID_HEIGHT_M + head + SCRUBBER_SHELL_M / 2  # bottom head hangs to the skid
    vessel(
        ctx, tag, f"{tag}_scrubber", SCRUBBER_DIAMETER_M, SCRUBBER_SHELL_M, "Z", (sx, sy, centre)
    )
    panel = block(
        f"{tag}_panel", PANEL_SIZE_M, (0.0, PANEL_Y_M, SKID_HEIGHT_M + PANEL_SIZE_M[2] / 2)
    )
    ctx.add_part(tag, panel, "paint_dark")
