"""Nozzle part: a short pipe with a flange at its outer end."""

from scene_setup import BuildContext

from parts import mesh_ops
from parts.flange import FLANGE_THICKNESS_M, flange

Vec3 = tuple[float, float, float]
DIRECTIONS = {
    "+X": ("X", 1),
    "-X": ("X", -1),
    "+Y": ("Y", 1),
    "-Y": ("Y", -1),
    "+Z": ("Z", 1),
    "-Z": ("Z", -1),
}
_UNIT = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


def nozzle(
    ctx: BuildContext,
    tag: str,
    name: str,
    radius_m: float,
    length_m: float,
    start: Vec3,
    direction: str,
    material: str = "paint_grey",
) -> Vec3:
    """Add a nozzle: a pipe from ``start`` along ``direction`` with a flange at its outer end.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        radius_m: Pipe radius.
        length_m: Pipe length from ``start`` to the outer flange face.
        start: Item-local centre of the pipe's inner end (on the vessel wall).
        direction: One of ``"+X"``, ``"-X"``, ``"+Y"``, ``"-Y"``, ``"+Z"``, ``"-Z"``.
        material: Material key of the pipe.

    Returns:
        The item-local centre of the outer flange face.

    Raises:
        ValueError: If ``direction`` is not one of the six axis directions.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"unknown nozzle direction {direction!r}")
    axis, sign = DIRECTIONS[direction]
    unit = _UNIT[axis]
    pipe_len = length_m - FLANGE_THICKNESS_M  # the flange takes the last 0.04 m
    centre = tuple(s + sign * u * pipe_len / 2 for s, u in zip(start, unit, strict=True))
    pipe = mesh_ops.cylinder(f"{name}_pipe", radius_m, pipe_len, centre, axis=axis)
    ctx.add_part(tag, pipe, material)
    end = tuple(s + sign * u * length_m for s, u in zip(start, unit, strict=True))
    face = tuple(e - sign * u * FLANGE_THICKNESS_M / 2 for e, u in zip(end, unit, strict=True))
    flange(ctx, tag, f"{name}_flange", radius_m, face, axis=axis)
    return (end[0], end[1], end[2])
