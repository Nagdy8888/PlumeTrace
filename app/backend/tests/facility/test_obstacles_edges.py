"""Edge cases of the facility wake obstacles: order, sizes, flags, empty and rotated spec."""

from plumetrace.engineering.truth_model import WakeObstacle
from plumetrace.facility.loader import load_facility
from plumetrace.facility.obstacles import SHELTER_HEIGHT_M, facility_obstacles
from plumetrace.facility.types import Equipment


def test_shelter_height_constant() -> None:
    """The shelter height is the Task 12 value of 6 m."""
    assert SHELTER_HEIGHT_M == 6.0


def test_ks07_obstacles_in_spec_order() -> None:
    """Three compressor shelters (K-201..K-203 at y 57, 75, 93), then CR-901 and MCC-902."""
    obstacles = facility_obstacles(load_facility())
    assert obstacles == [
        WakeObstacle((75.0, 57.0), 6.0, 6.0),
        WakeObstacle((75.0, 75.0), 6.0, 6.0),
        WakeObstacle((75.0, 93.0), 6.0, 6.0),
        WakeObstacle((30.0, 20.0), 7.5, 4.0),
        WakeObstacle((50.0, 20.0), 5.0, 4.0),
    ]


def test_half_width_uses_the_larger_footprint_side() -> None:
    """Half width is max(size_x, size_y) / 2: the control room is 15 x 8 m, so 7.5 m."""
    control_room = facility_obstacles(load_facility())[3]
    assert control_room.half_width_m == 7.5


def test_spec_without_buildings_or_shelters_has_no_obstacles() -> None:
    """Equipment that is neither a building nor in a shelter makes no wake."""
    spec = load_facility()
    plain = [e for e in spec.equipment if e.type != "building" and not e.shelter]
    assert plain  # the station has such equipment
    assert facility_obstacles(spec.model_copy(update={"equipment": plain})) == []
    assert facility_obstacles(spec.model_copy(update={"equipment": []})) == []


def test_building_flagged_as_shelter_is_listed_once_with_its_own_height() -> None:
    """A building with shelter: true is one obstacle, with the building rule (height size_z)."""
    spec = load_facility()
    building = next(e for e in spec.equipment if e.tag == "CR-901")
    flagged: Equipment = building.model_copy(update={"shelter": True})
    result = facility_obstacles(spec.model_copy(update={"equipment": [flagged]}))
    assert result == [WakeObstacle((30.0, 20.0), 7.5, 4.0)]


def test_rotation_is_ignored_and_taller_than_shelter_buildings_keep_their_height() -> None:
    """Rotation does not change the obstacle; a 12 m building keeps 12 m, not the shelter 6 m."""
    spec = load_facility()
    building = next(e for e in spec.equipment if e.tag == "MCC-902")
    tall = building.model_copy(update={"rotation_deg": 45.0, "size_m": (10.0, 6.0, 12.0)})
    result = facility_obstacles(spec.model_copy(update={"equipment": [tall]}))
    assert result == [WakeObstacle((50.0, 20.0), 5.0, 12.0)]
