"""Gate valve part: body, stem and a handwheel at a seeded angle."""

from scene_setup import BuildContext

from parts import mesh_ops
from parts.shapes import tilt

BODY_LENGTH_FACTOR = 2.5  # of the pipe radius, along the pipe
BODY_SIZE_FACTOR = 2.0  # of the pipe radius, across and up
MIN_RADIUS_M = 0.01


def valve(
    ctx: BuildContext,
    tag: str,
    name: str,
    pipe_radius_m: float,
    location: tuple[float, float, float],
    axis: str = "X",
) -> None:
    """Add a valve on a horizontal pipe: body, vertical stem and a handwheel.

    The handwheel (a torus of radius 2 r with one spoke) is turned by an angle drawn from
    ``ctx.rng``, so the valves of a station do not all look identical and a rebuild reproduces it.

    Args:
        ctx: Build context.
        tag: Equipment tag the parts belong to.
        name: Base object name.
        pipe_radius_m: Radius ``r`` of the pipe it sits on.
        location: Item-local centre of the valve body (on the pipe axis).
        axis: Pipe direction, "X" or "Y".
    """
    r = pipe_radius_m
    x, y, z = location
    along, across = BODY_LENGTH_FACTOR * r, BODY_SIZE_FACTOR * r
    size = (along, across, across) if axis == "X" else (across, along, across)
    ctx.add_part(tag, mesh_ops.box(f"{name}_body", size, location), "paint_dark")
    stem_h = across * 1.2
    stem_z = z + across / 2 + stem_h / 2
    stem = mesh_ops.cylinder(f"{name}_stem", max(r * 0.15, MIN_RADIUS_M), stem_h, (x, y, stem_z))
    ctx.add_part(tag, stem, "paint_grey")
    wheel_z = z + across / 2 + stem_h
    wheel = mesh_ops.torus(f"{name}_wheel", across, max(r * 0.15, MIN_RADIUS_M), (x, y, wheel_z))
    ctx.add_part(tag, wheel, "safety_yellow")
    spoke = mesh_ops.box(
        f"{name}_spoke", (2 * across, max(r * 0.2, MIN_RADIUS_M), 0.01), (x, y, wheel_z)
    )
    tilt(spoke, z_deg=float(ctx.rng.uniform(0.0, 180.0)))
    ctx.add_part(tag, spoke, "safety_yellow")
