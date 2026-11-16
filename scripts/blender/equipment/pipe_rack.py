"""Portal frames under the two elevated headers, joined into one node ``SITE__racks`` (bpy module).

Rack A runs along x = 45 (y 57 to 93), rack B along x = 105 (y 30 to 93). A frame stands every 6 m
from the start of the rack; a last frame closes the rack when its length is not a multiple of 6 m.
"""

from naming import RACKS_TAG
from parts import mesh_ops
from scene_setup import BuildContext

RACKS = (("A", 45.0, 57.0, 93.0), ("B", 105.0, 30.0, 93.0))  # name, x, y start, y end
FRAME_SPACING_M = 6.0
COLUMN_M = 0.3
COLUMN_OFFSET_M = 1.5
BEAM_SIZE_M = (3.3, 0.3, 0.3)
BEAM_Z_M = 3.55  # top of steel 3.7 m; the pipes (centre z 4) rest on it


def _frame_ys(y_start: float, y_end: float) -> list[float]:
    """Frame positions: every 6 m from the start, plus the end when it is not on the grid."""
    count = int((y_end - y_start) / FRAME_SPACING_M) + 1
    ys = [y_start + i * FRAME_SPACING_M for i in range(count)]
    if ys[-1] < y_end - 1e-9:
        ys.append(y_end)
    return ys


def build_racks(ctx: BuildContext) -> None:
    """Build the node ``SITE__racks`` (two columns and a beam per frame, material ``paint_dark``).

    Args:
        ctx: Build context.
    """
    ctx.new_root(
        {"tag": RACKS_TAG, "type": "site", "position_m": [0.0, 0.0, 0.0], "rotation_deg": 0.0}
    )
    column_h = BEAM_Z_M - BEAM_SIZE_M[2] / 2  # up to the underside of the beam
    for rack, x, y_start, y_end in RACKS:
        for y in _frame_ys(y_start, y_end):
            for side, dx in (("w", -COLUMN_OFFSET_M), ("e", COLUMN_OFFSET_M)):
                column = mesh_ops.box(
                    f"rack_{rack}_{y:g}_col_{side}",
                    (COLUMN_M, COLUMN_M, column_h),
                    (x + dx, y, column_h / 2),
                )
                ctx.add_part(RACKS_TAG, column, "paint_dark")
            beam = mesh_ops.box(f"rack_{rack}_{y:g}_beam", BEAM_SIZE_M, (x, y, BEAM_Z_M))
            ctx.add_part(RACKS_TAG, beam, "paint_dark")
