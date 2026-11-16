"""Fin-fan air coolers E-231..E-233 (8 x 4 x 5 m) with two fans that stay separate glb nodes.

The fans are the nodes ``<tag>__fan_1`` (x = -L/4) and ``<tag>__fan_2`` (x = +L/4); each has its
origin at the hub so the frontend can spin it about its local z axis.
"""

import math
from typing import Any

from parts import mesh_ops
from parts.platform import platform, platform_edge
from parts.shapes import block, tilt
from scene_setup import BuildContext

LEG_M = 0.25
LEG_TOP_Z_M = 3.5
PLENUM_Z_M = (3.5, 4.3)
BUNDLE_Z_M = (4.3, 4.7)
HEADER_Z_M = (4.3, 4.9)
HEADER_X_M = 0.4
FAN_Z_M = 3.4
RING_MAJOR_M = 1.6
RING_MINOR_M = 0.06
HUB_RADIUS_M = 0.2
HUB_HEIGHT_M = 0.25
BLADE_SIZE_M = (1.45, 0.28, 0.03)
BLADE_PITCH_DEG = 12.0
BLADES = 4
MOTOR_SIZE_M = (0.5, 0.5, 0.6)
MOTOR_Z_M = (2.6, 3.2)
WALKWAY_Z_M = 4.75  # top face; the plate rests on the bundle top (4.7)
WALKWAY_Y_M = (1.2, 2.0)
WALKWAY_INSET_M = 0.5  # from the headers


def _frame(ctx: BuildContext, tag: str, length: float, width: float) -> None:
    """Four legs, plenum, tube bundle and the two end headers."""
    for i, (sx, sy) in enumerate((x, y) for x in (-1, 1) for y in (-1, 1)):
        at = (sx * (length / 2 - LEG_M / 2), sy * (width / 2 - LEG_M / 2), LEG_TOP_Z_M / 2)
        ctx.add_part(
            tag, mesh_ops.box(f"{tag}_leg_{i}", (LEG_M, LEG_M, LEG_TOP_Z_M), at), "paint_dark"
        )
    for label, (z0, z1), material in (
        ("plenum", PLENUM_Z_M, "paint_grey"),
        ("bundle", BUNDLE_Z_M, "paint_grey"),
    ):
        ctx.add_part(
            tag,
            block(f"{tag}_{label}", (length, width, z1 - z0), (0.0, 0.0, (z0 + z1) / 2)),
            material,
        )
    z0, z1 = HEADER_Z_M
    for sign, label in ((-1, "inlet"), (1, "outlet")):
        at = (sign * (length / 2 - HEADER_X_M / 2), 0.0, (z0 + z1) / 2)
        header = mesh_ops.box(f"{tag}_header_{label}", (HEADER_X_M, width, z1 - z0), at)
        ctx.add_part(tag, header, "paint_dark")


def _motor_mount(ctx: BuildContext, tag: str, x: float, width: float, index: int) -> None:
    """Motor under the hub, its shaft, a cross beam through the motor and four hangers."""
    z0, z1 = MOTOR_Z_M
    motor = mesh_ops.box(f"{tag}_motor_{index}", MOTOR_SIZE_M, (x, 0.0, (z0 + z1) / 2))
    ctx.add_part(tag, motor, "paint_dark")
    shaft = mesh_ops.cylinder(
        f"{tag}_shaft_{index}", 0.05, FAN_Z_M - z1, (x, 0.0, (z1 + FAN_Z_M) / 2)
    )
    ctx.add_part(tag, shaft, "paint_grey")
    reach = width / 2 - 0.3
    beam = mesh_ops.box(
        f"{tag}_motor_beam_{index}", (0.12, 2 * reach, 0.12), (x, 0.0, (z0 + z1) / 2)
    )
    ctx.add_part(tag, beam, "paint_dark")
    for sy, label in ((-1, "s"), (1, "n")):
        height = PLENUM_Z_M[0] + 0.1 - (z0 + z1) / 2
        hanger = mesh_ops.box(
            f"{tag}_hanger_{index}{label}",
            (0.12, 0.12, height),
            (x, sy * reach, (z0 + z1) / 2 + height / 2),
        )
        ctx.add_part(tag, hanger, "paint_dark")


def _fan(ctx: BuildContext, tag: str, x: float, index: int) -> None:
    """One fan as a separate node: hub plus four pitched blades, pivot at the hub."""
    node = ctx.new_node(tag, f"fan_{index}", (x, 0.0, FAN_Z_M))
    hub = mesh_ops.cylinder(f"{tag}_hub_{index}", HUB_RADIUS_M, HUB_HEIGHT_M, (0.0, 0.0, 0.0))
    ctx.add_node_part(node, hub, "paint_dark")
    radial = BLADE_SIZE_M[0] / 2 + 0.1  # blade root sits inside the hub
    for k in range(BLADES):
        angle = 360.0 * k / BLADES
        place = (
            radial * math.cos(math.radians(angle)),
            radial * math.sin(math.radians(angle)),
            0.0,
        )
        blade = mesh_ops.box(f"{tag}_blade_{index}_{k}", BLADE_SIZE_M, place)
        tilt(blade, x_deg=BLADE_PITCH_DEG, z_deg=angle)  # pitch about its long axis, then turn
        ctx.add_node_part(node, blade, "paint_grey")


def _walkway(ctx: BuildContext, tag: str, length: float) -> None:
    """Grating walkway on the +y edge of the bundle, handrail on its outer edge and ends."""
    half = length / 2 - HEADER_X_M - WALKWAY_INSET_M
    y0, y1 = WALKWAY_Y_M
    platform(
        ctx, tag, f"{tag}_walkway", [(-half, y0), (half, y0), (half, y1), (-half, y1)], WALKWAY_Z_M
    )
    edge = [(-half, y0), (-half, y1), (half, y1), (half, y0)]
    platform_edge(ctx, tag, f"{tag}_walkway_edge", edge, WALKWAY_Z_M)


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build a fin-fan cooler: frame, bundle, headers, fan rings, motors, two fan nodes, walkway.

    Args:
        item: Spec item (``type`` ``fin_fan_cooler``; no anchors).
        ctx: Build context.
    """
    tag = item["tag"]
    length, width, _ = item["size_m"]
    ctx.new_root(item)
    _frame(ctx, tag, length, width)
    for index, x in ((1, -length / 4), (2, length / 4)):
        ring = mesh_ops.torus(f"{tag}_ring_{index}", RING_MAJOR_M, RING_MINOR_M, (x, 0.0, FAN_Z_M))
        ctx.add_part(tag, ring, "paint_grey")
        _motor_mount(ctx, tag, x, width, index)
        _fan(ctx, tag, x, index)
    _walkway(ctx, tag, length)
