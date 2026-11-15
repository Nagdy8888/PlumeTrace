"""Compressor skid part: two W-beams, five cross-beams and a deck plate."""

from scene_setup import BuildContext

from parts import mesh_ops

BEAM_M = 0.3
FLANGE_M = 0.02
DECK_M = 0.05
CROSS_BEAMS = 5


def _w_beam(ctx: BuildContext, tag: str, name: str, length_m: float, y_m: float) -> None:
    """One W-beam along x: web plus two flanges, resting on the pad (z 0 to 0.3)."""
    parts = (
        ("web", (length_m, FLANGE_M, BEAM_M - 2 * FLANGE_M), (0.0, y_m, BEAM_M / 2)),
        ("top", (length_m, BEAM_M, FLANGE_M), (0.0, y_m, BEAM_M - FLANGE_M / 2)),
        ("bottom", (length_m, BEAM_M, FLANGE_M), (0.0, y_m, FLANGE_M / 2)),
    )
    for label, size, at in parts:
        ctx.add_part(tag, mesh_ops.box(f"{name}_{label}", size, at), "paint_dark")


def skid(ctx: BuildContext, tag: str, length_m: float, width_m: float) -> None:
    """Add the skid base frame (envelope ``length_m`` x ``width_m`` x 0.35 m).

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        length_m: Length along x.
        width_m: Width along y.
    """
    edge = width_m / 2 - BEAM_M / 2
    for side, y in (("s", -edge), ("n", edge)):
        _w_beam(ctx, tag, f"{tag}_beam_{side}", length_m, y)
    span = length_m - BEAM_M
    for i in range(CROSS_BEAMS):
        x = -span / 2 + i * span / (CROSS_BEAMS - 1)
        size = (BEAM_M / 2, 2 * edge - BEAM_M, BEAM_M - 2 * FLANGE_M)
        cross = mesh_ops.box(f"{tag}_cross_{i}", size, (x, 0.0, BEAM_M / 2))
        ctx.add_part(tag, cross, "paint_dark")
    deck = mesh_ops.box(f"{tag}_deck", (length_m, width_m, DECK_M), (0.0, 0.0, BEAM_M + DECK_M / 2))
    ctx.add_part(tag, deck, "paint_dark")
