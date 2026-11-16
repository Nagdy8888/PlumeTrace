"""Pipe radius, corner fillets and support spacing (pure maths, no ``bpy``).

The bpy builder ``equipment/pipe_route.py`` turns these into curves and posts. Sizes are metres.
"""

import math
from collections.abc import Sequence

Vec3 = tuple[float, float, float]

MIN_RADIUS_M = 0.03
INCH_M = 0.0254
STRAIGHT_DEG = 1.0  # a turn below this is treated as a straight run
TANGENT_SEGMENT_SHARE = 0.45  # a fillet takes at most this share of an adjacent segment
END_CLEARANCE_M = 1.0


def pipe_radius_m(size_in: float) -> float:
    """Visual outside radius of a pipe (the nominal size is used as the outside diameter).

    Args:
        size_in: Nominal size in inches.

    Returns:
        ``max(0.03, size_in * 0.0254 / 2)`` in metres.
    """
    return max(MIN_RADIUS_M, size_in * INCH_M / 2)


def _sub(a: Vec3, b: Vec3) -> Vec3:
    """Component-wise ``a - b``."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec3, b: Vec3) -> Vec3:
    """Component-wise ``a + b``."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Vec3, k: float) -> Vec3:
    """Scale ``a`` by ``k``."""
    return (a[0] * k, a[1] * k, a[2] * k)


def _unit(a: Vec3) -> Vec3:
    """Unit vector of ``a`` (``a`` must not be zero)."""
    return _scale(a, 1.0 / math.hypot(*a))


def _corner_arc(
    prev: Vec3, corner: Vec3, nxt: Vec3, bend_radius_m: float, steps: int
) -> list[Vec3]:
    """Points of the arc that rounds ``corner``, or ``[corner]`` when it is (nearly) straight."""
    d_in, d_out = _unit(_sub(corner, prev)), _unit(_sub(nxt, corner))
    cos_turn = max(-1.0, min(1.0, sum(a * b for a, b in zip(d_in, d_out, strict=True))))
    turn = math.acos(cos_turn)
    if math.degrees(turn) < STRAIGHT_DEG or math.sin(turn) < 1e-9:
        return [corner]
    shorter = min(math.dist(prev, corner), math.dist(corner, nxt))
    tangent = min(bend_radius_m * math.tan(turn / 2), TANGENT_SEGMENT_SHARE * shorter)
    radius = tangent / math.tan(turn / 2)
    start = _sub(corner, _scale(d_in, tangent))
    end = _add(corner, _scale(d_out, tangent))
    toward_centre = _unit(_sub(d_out, d_in))
    centre = _add(corner, _scale(toward_centre, radius / math.cos(turn / 2)))
    u0, u1 = _scale(_sub(start, centre), 1 / radius), _scale(_sub(end, centre), 1 / radius)
    arc: list[Vec3] = []
    for i in range(steps + 1):
        s = i / steps
        w0, w1 = math.sin((1 - s) * turn) / math.sin(turn), math.sin(s * turn) / math.sin(turn)
        arc.append(_add(centre, _scale(_add(_scale(u0, w0), _scale(u1, w1)), radius)))
    return arc


def fillet_polyline(points: Sequence[Vec3], bend_radius_m: float, steps: int = 6) -> list[Vec3]:
    """Round every interior corner of a polyline with a circular arc.

    The arc is tangent to both segments. Its tangent distance is
    ``min(bend_radius * tan(theta / 2), 0.45 * shorter adjacent segment)`` with ``theta`` the turn
    angle. A turn below 1 degree is kept as it is, and the two end points never move.

    Args:
        points: Route way points ``(x, y, z)`` in metres (at least two).
        bend_radius_m: Wanted bend radius in metres.
        steps: Arc sections per corner (a corner becomes ``steps + 1`` points).

    Returns:
        The new polyline, endpoints identical to the input.
    """
    out: list[Vec3] = [points[0]]
    for i in range(1, len(points) - 1):
        out.extend(_corner_arc(points[i - 1], points[i], points[i + 1], bend_radius_m, steps))
    out.append(points[-1])
    return out


def support_points(
    points: Sequence[Vec3], spacing_m: float = 6.0, min_z_m: float = 1.0
) -> list[Vec3]:
    """Pipe-centre positions of the supports along a polyline.

    A support sits every ``spacing_m`` of path length from the first point (first at
    ``spacing_m``), only where the pipe centre is at least ``min_z_m`` high and the point is at
    least 1 m from both ends of the path.

    Args:
        points: Polyline ``(x, y, z)`` in metres.
        spacing_m: Path distance between supports in metres.
        min_z_m: Lowest pipe-centre height that gets a support, in metres.

    Returns:
        The support positions in path order.
    """
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:], strict=False)]
    total = sum(lengths)
    found: list[Vec3] = []
    walked, distance = 0.0, spacing_m
    for (a, b), length in zip(zip(points, points[1:], strict=False), lengths, strict=True):
        while distance <= walked + length + 1e-9 and distance <= total:
            if length > 0:
                at = _add(a, _scale(_unit(_sub(b, a)), distance - walked))
                clear = END_CLEARANCE_M <= distance <= total - END_CLEARANCE_M + 1e-9
                if at[2] >= min_z_m and clear:
                    found.append(at)
            distance += spacing_m
        walked += length
    return found
