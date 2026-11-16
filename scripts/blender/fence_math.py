"""Fence post positions (pure maths, no ``bpy``).

The bpy builder ``equipment/site.py`` turns these into post cylinders. Sizes are metres.
"""


def _axis_m(length_m: float, step_m: float) -> list[float]:
    """Multiples of ``step_m`` below ``length_m`` plus the end point (no stray post past it)."""
    n = int(length_m / step_m)
    values = [i * step_m for i in range(n + 1) if i * step_m < length_m]
    return [*values, length_m]


def fence_post_xy(
    width_m: float, depth_m: float, step_m: float, gate_y_m: tuple[float, float]
) -> list[tuple[float, float]]:
    """Post positions every ``step_m`` along the four bounds, none inside the west gate gap.

    Args:
        width_m: Yard size along x (east).
        depth_m: Yard size along y (north).
        step_m: Post spacing.
        gate_y_m: ``(low, high)`` y range of the gap in the west side (x 0); posts strictly
            between the two values are left out.

    Returns:
        Sorted ``(x, y)`` points.
    """
    xs = _axis_m(width_m, step_m)
    ys = _axis_m(depth_m, step_m)
    points = {(x, 0.0) for x in xs} | {(x, depth_m) for x in xs}
    points |= {(0.0, y) for y in ys} | {(width_m, y) for y in ys}
    lo, hi = gate_y_m
    return sorted(p for p in points if not (p[0] == 0.0 and lo < p[1] < hi))
