"""Inversion candidates (emission anchors) and methane sensors derived from the facility spec."""

from plumetrace.engineering.geometry import Candidate, Point3, Sensor
from plumetrace.facility.spec import FacilitySpec
from plumetrace.facility.types import InstrumentKind


def emission_candidates(spec: FacilitySpec) -> list[Candidate]:
    """List every anchor flagged as an emission point.

    Args:
        spec: The facility spec.

    Returns:
        One candidate per anchor with ``emission_point`` true, sorted by anchor id.
    """
    found = [
        Candidate(id=anchor.id, position=Point3(*anchor.position_m))
        for equipment in spec.equipment
        for anchor in equipment.anchors
        if anchor.emission_point
    ]
    return sorted(found, key=lambda candidate: candidate.id)


def methane_sensors(spec: FacilitySpec) -> list[Sensor]:
    """List the methane point sensors.

    Args:
        spec: The facility spec.

    Returns:
        One sensor per instrument of kind ``methane_point``, sorted by tag.

    Raises:
        ValueError: If a methane sensor has no ``noise_ppm``.
    """
    sensors: list[Sensor] = []
    for instrument in spec.instruments:
        if instrument.kind is not InstrumentKind.methane_point:
            continue
        if instrument.noise_ppm is None:
            raise ValueError(f"{instrument.tag} has no noise_ppm")
        sensors.append(
            Sensor(
                id=instrument.tag,
                position=Point3(*instrument.position_m),
                noise_ppm=instrument.noise_ppm,
            )
        )
    return sorted(sensors, key=lambda sensor: sensor.id)
