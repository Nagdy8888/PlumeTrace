"""Fuel gas skid FG-501 (4 x 3 x 2 m): filters, a valved regulator run and a line heater."""

from typing import Any

from anchors import anchor_local
from parts import mesh_ops
from parts.shapes import block
from parts.skid import skid
from parts.valve import valve
from parts.vessel import vessel
from scene_setup import BuildContext

SKID_HEIGHT_M = 0.25
FILTER_DIAMETER_M = 0.4
FILTER_SHELL_M = 0.9
FILTER_POSITIONS_M = ((-1.2, -0.6), (-1.2, 0.6))
RUN_RADIUS_M = 0.05
RUN_Z_M = 1.0
RUN_HALF_LENGTH_M = 1.8
VALVE_X_M = (-1.0, -0.3, 0.3, 1.0)
SPOOL_X_M = 0.15  # the raised centre section stands between the two middle valves
HEATER_SIZE_M = (1.0, 0.8, 1.0)
HEATER_AT_M = (1.3, 0.9)


def _run(ctx: BuildContext, item: dict[str, Any]) -> None:
    """Regulator run along x with four valves; its centre section is lifted to the anchor height."""
    tag = item["tag"]
    top_z = anchor_local(item, "skid")[2]
    r = RUN_RADIUS_M
    for label, (x0, x1) in (
        ("w", (-RUN_HALF_LENGTH_M, -SPOOL_X_M)),
        ("e", (SPOOL_X_M, RUN_HALF_LENGTH_M)),
    ):
        pipe = mesh_ops.cylinder(
            f"{tag}_run_{label}", r, x1 - x0, ((x0 + x1) / 2, 0.0, RUN_Z_M), axis="X"
        )
        ctx.add_part(tag, pipe, "pipe_gas")
    for sign, label in ((-1, "w"), (1, "e")):
        height = top_z - RUN_Z_M
        spool = mesh_ops.cylinder(
            f"{tag}_spool_{label}", r, height, (sign * SPOOL_X_M, 0.0, RUN_Z_M + height / 2)
        )
        ctx.add_part(tag, spool, "pipe_gas")
    cross = mesh_ops.cylinder(
        f"{tag}_spool_top", r, 2 * SPOOL_X_M + 2 * r, (0.0, 0.0, top_z), axis="X"
    )
    ctx.add_part(tag, cross, "pipe_gas")
    for i, x in enumerate(VALVE_X_M):
        valve(ctx, tag, f"{tag}_valve_{i}", r, (x, 0.0, RUN_Z_M), axis="X")


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build FG-501: skid, two vertical filters, regulator run with four valves, line heater.

    The ``FG-501.skid`` anchor (local ``(0, 0, 1.5)``) sits on the raised centre section of the run.

    Args:
        item: Spec item (``type`` ``fuel_gas_skid``).
        ctx: Build context.
    """
    tag = item["tag"]
    length, width, _ = item["size_m"]
    ctx.new_root(item)
    skid(ctx, tag, length, width, SKID_HEIGHT_M)
    head = FILTER_DIAMETER_M / 4
    for i, (x, y) in enumerate(FILTER_POSITIONS_M):
        centre = SKID_HEIGHT_M + head + FILTER_SHELL_M / 2  # bottom head hangs to the skid
        vessel(
            ctx, tag, f"{tag}_filter_{i}", FILTER_DIAMETER_M, FILTER_SHELL_M, "Z", (x, y, centre)
        )
    _run(ctx, item)
    hx, hy = HEATER_AT_M
    heater = block(f"{tag}_heater", HEATER_SIZE_M, (hx, hy, SKID_HEIGHT_M + HEATER_SIZE_M[2] / 2))
    ctx.add_part(tag, heater, "paint_dark")
