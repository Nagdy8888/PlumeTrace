"""Yard ground: one gravel quad (spike patch; the full station arrives in Task 7)."""

from parts import mesh_ops
from scene_setup import BuildContext

GROUND_TAG = "ground"
GROUND_CENTER_M = (80.0, 95.0)
GROUND_SIZE_M = (60.0, 70.0)
GROUND_Z_M = -0.02  # just under the concrete pad tops (z 0) so they never z-fight


def build_ground(ctx: BuildContext) -> None:
    """Add the gravel ground patch as its own node ``ground``.

    Args:
        ctx: Build context.
    """
    cx, cy = GROUND_CENTER_M
    item = {"tag": GROUND_TAG, "position_m": [cx, cy, GROUND_Z_M], "rotation_deg": 0.0}
    ctx.new_root(item)
    quad = mesh_ops.plane(f"{GROUND_TAG}_gravel", GROUND_SIZE_M, (0.0, 0.0, 0.0))
    ctx.add_part(GROUND_TAG, quad, "gravel", tile_m=4.0)
