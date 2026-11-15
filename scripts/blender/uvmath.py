"""World-space box UV projection (pure maths, no ``bpy``)."""


def box_uv(
    co: tuple[float, float, float], normal: tuple[float, float, float], tile_m: float
) -> tuple[float, float]:
    """Project a point onto the plane of the dominant normal axis.

    Ties go to z, then x. The z-dominant plane maps ``(x, y)``, x-dominant ``(y, z)`` and
    y-dominant ``(x, z)``; each coordinate is divided by ``tile_m``.

    Args:
        co: World-space position in metres.
        normal: World-space face normal (need not be unit length).
        tile_m: Texture repeat length in metres.

    Returns:
        The ``(u, v)`` coordinate.
    """
    ax, ay, az = abs(normal[0]), abs(normal[1]), abs(normal[2])
    if az >= ax and az >= ay:
        u, v = co[0], co[1]
    elif ax >= ay:
        u, v = co[1], co[2]
    else:
        u, v = co[0], co[2]
    return (u / tile_m, v / tile_m)
