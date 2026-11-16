"""Vessel saddle part: a box support under a horizontal vessel."""

from scene_setup import BuildContext

from parts import mesh_ops

SADDLE_LENGTH_M = 0.3
SADDLE_WIDTH_FACTOR = 0.8  # of the vessel diameter


def saddle(
    ctx: BuildContext,
    tag: str,
    name: str,
    vessel_diameter_m: float,
    x_m: float,
    vessel_centre_z_m: float,
    y_m: float = 0.0,
) -> None:
    """Add a saddle: 0.3 m along the vessel, 0.8 D across, from the ground to the vessel underside.

    Args:
        ctx: Build context.
        tag: Equipment tag the part belongs to.
        name: Object name.
        vessel_diameter_m: Diameter of the vessel it carries.
        x_m: Item-local x of the saddle centre.
        vessel_centre_z_m: Item-local z of the vessel axis (the saddle top is the underside).
        y_m: Item-local y of the vessel axis.
    """
    height = vessel_centre_z_m - vessel_diameter_m / 2
    size = (SADDLE_LENGTH_M, SADDLE_WIDTH_FACTOR * vessel_diameter_m, height)
    obj = mesh_ops.box(name, size, (x_m, y_m, height / 2))
    ctx.add_part(tag, obj, "paint_dark")
