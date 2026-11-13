"""Wake obstacles of the station, derived from the facility spec.

``facility`` may import ``engineering`` but not the other way round, so the function that turns a
spec into the truth model's ``WakeObstacle`` list lives here.
"""

from typing import Final

from plumetrace.engineering.truth_wake import WakeObstacle
from plumetrace.facility.spec import FacilitySpec
from plumetrace.facility.types import EquipmentType

# Task 12 value: height assumed for every equipment item that sits inside a shelter (m).
SHELTER_HEIGHT_M: Final = 6.0


def facility_obstacles(spec: FacilitySpec) -> list[WakeObstacle]:
    """List the buildings and shelters that make wakes.

    Every ``building`` uses its own height (``size_z``); every other equipment with
    ``shelter: true`` uses ``SHELTER_HEIGHT_M``. The half width is ``max(size_x, size_y) / 2``
    and the centre is the footprint centre; the rotation is ignored (a conservative square
    footprint). A building that is also flagged as a shelter is listed once, as a building.

    Args:
        spec: The facility spec.

    Returns:
        One obstacle per building or shelter, in spec order.
    """
    found: list[WakeObstacle] = []
    for equipment in spec.equipment:
        is_building = equipment.type is EquipmentType.building
        if not (is_building or equipment.shelter):
            continue
        size_x, size_y, size_z = equipment.size_m
        found.append(
            WakeObstacle(
                center_xy=(equipment.position_m[0], equipment.position_m[1]),
                half_width_m=max(size_x, size_y) / 2.0,
                height_m=size_z if is_building else SHELTER_HEIGHT_M,
            )
        )
    return found
