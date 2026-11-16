"""Skid part: two longitudinal W-beams, cross-beams at most 2.5 m apart and a deck plate."""

import math

from scene_setup import BuildContext

from parts import mesh_ops

BEAM_M = 0.3
FLANGE_M = 0.02
DECK_M = 0.05
MAX_CROSS_SPACING_M = 2.5


def _w_beam(
    ctx: BuildContext, tag: str, name: str, length_m: float, y_m: float, beam_m: float
) -> None:
    """One W-beam along x: web plus two flanges, resting on the ground (z 0 up to ``beam_m``)."""
    parts = (
        ("web", (length_m, FLANGE_M, beam_m - 2 * FLANGE_M), (0.0, y_m, beam_m / 2)),
        ("top", (length_m, beam_m, FLANGE_M), (0.0, y_m, beam_m - FLANGE_M / 2)),
        ("bottom", (length_m, beam_m, FLANGE_M), (0.0, y_m, FLANGE_M / 2)),
    )
    for label, size, at in parts:
        ctx.add_part(tag, mesh_ops.box(f"{name}_{label}", size, at), "paint_dark")


def skid(
    ctx: BuildContext,
    tag: str,
    length_m: float,
    width_m: float,
    height_m: float = BEAM_M + DECK_M,
) -> None:
    """Add the skid base frame (envelope ``length_m`` x ``width_m`` x ``height_m``).

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        length_m: Length along x.
        width_m: Width along y.
        height_m: Total height: beams of ``height_m - 0.05`` plus a 0.05 m deck plate.
    """
    beam_m = height_m - DECK_M
    edge = width_m / 2 - beam_m / 2
    for side, y in (("s", -edge), ("n", edge)):
        _w_beam(ctx, tag, f"{tag}_beam_{side}", length_m, y, beam_m)
    span = length_m - beam_m
    count = math.ceil(span / MAX_CROSS_SPACING_M) + 1
    for i in range(count):
        x = -span / 2 + i * span / (count - 1)
        size = (beam_m / 2, 2 * edge - beam_m, beam_m - 2 * FLANGE_M)
        cross = mesh_ops.box(f"{tag}_cross_{i}", size, (x, 0.0, beam_m / 2))
        ctx.add_part(tag, cross, "paint_dark")
    deck = mesh_ops.box(f"{tag}_deck", (length_m, width_m, DECK_M), (0.0, 0.0, beam_m + DECK_M / 2))
    ctx.add_part(tag, deck, "paint_dark")
