"""The facility spec model and its cross-reference validation.

``FacilitySpec`` is the validated form of ``data/ks07.yaml``. A broken spec fails with a message
that names the offending tag, anchor id or route id.
"""

from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from plumetrace.facility.types import (
    Equipment,
    Instrument,
    OperatingConditions,
    PipeRoute,
    Site,
    Vec3,
)


def _check_unique_tags(spec: "FacilitySpec") -> None:
    """Require tags to be unique across equipment and instruments.

    Args:
        spec: The spec being validated.

    Raises:
        ValueError: If a tag appears more than once.
    """
    tags = [e.tag for e in spec.equipment] + [i.tag for i in spec.instruments]
    for tag, count in Counter(tags).items():
        if count > 1:
            raise ValueError(f"duplicate tag {tag}")


def _check_anchor_ownership(spec: "FacilitySpec") -> None:
    """Require every anchor id to start with its equipment tag and a dot.

    Args:
        spec: The spec being validated.

    Raises:
        ValueError: If an anchor id does not start with ``<tag>.``.
    """
    for equipment in spec.equipment:
        for anchor in equipment.anchors:
            if not anchor.id.startswith(f"{equipment.tag}."):
                raise ValueError(f"anchor {anchor.id} does not belong to equipment {equipment.tag}")


def _positions(spec: "FacilitySpec") -> list[tuple[str, Vec3]]:
    """List every (owner, position) pair that must lie inside the site bounds.

    Args:
        spec: The spec being validated.

    Returns:
        Equipment, anchor, instrument and pipe-waypoint positions with their owner name.
    """
    pairs: list[tuple[str, Vec3]] = []
    for equipment in spec.equipment:
        pairs.append((equipment.tag, equipment.position_m))
        pairs.extend((anchor.id, anchor.position_m) for anchor in equipment.anchors)
    pairs.extend((instrument.tag, instrument.position_m) for instrument in spec.instruments)
    for route in spec.piping:
        pairs.extend((route.id, waypoint) for waypoint in route.waypoints_m)
    return pairs


def _check_bounds(spec: "FacilitySpec") -> None:
    """Require every position to be inside the site bounds and not below ground.

    Args:
        spec: The spec being validated.

    Raises:
        ValueError: If a position is outside the bounds.
    """
    for owner, position in _positions(spec):
        if not spec.site.bounds.contains(position):
            raise ValueError(f"{owner} position {position} is outside the site bounds")


def _check_references(spec: "FacilitySpec") -> None:
    """Require ``vents_to`` and ``attaches_to`` to name existing equipment.

    Args:
        spec: The spec being validated.

    Raises:
        ValueError: If a reference names an unknown equipment tag.
    """
    known = {e.tag for e in spec.equipment}
    for equipment in spec.equipment:
        if equipment.vents_to is not None and equipment.vents_to not in known:
            raise ValueError(f"{equipment.tag} vents_to unknown tag {equipment.vents_to}")
    for instrument in spec.instruments:
        if instrument.attaches_to is not None and instrument.attaches_to not in known:
            raise ValueError(f"{instrument.tag} attaches_to unknown tag {instrument.attaches_to}")


def _check_composition(spec: "FacilitySpec") -> None:
    """Require the gas composition (mole fractions) to sum to 1.

    Args:
        spec: The spec being validated.

    Raises:
        ValueError: If the fractions do not sum to 1 within 1e-6.
    """
    total = sum(spec.gas_composition.values())
    if abs(total - 1) > 1e-6:
        raise ValueError(f"gas_composition sums to {total:.6f}, expected 1")


class FacilitySpec(BaseModel):
    """Validated description of the station.

    Attributes:
        site: Site identity, bounds and location.
        gas_composition: Mole fractions by species; must sum to 1.
        operating: Normal operating conditions.
        equipment: All equipment, each with its anchors.
        piping: Pipe routes as polylines.
        instruments: All instruments.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    site: Site
    gas_composition: dict[str, float]
    operating: OperatingConditions
    equipment: list[Equipment]
    piping: list[PipeRoute]
    instruments: list[Instrument]

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Run every cross-reference check in order.

        Returns:
            The validated spec.
        """
        _check_unique_tags(self)
        _check_anchor_ownership(self)
        _check_bounds(self)
        _check_references(self)
        _check_composition(self)
        return self

    def equipment_by_tag(self, tag: str) -> Equipment:
        """Look up equipment by tag.

        Args:
            tag: Equipment tag, for example ``K-202``.

        Returns:
            The matching equipment.

        Raises:
            KeyError: If no equipment has this tag.
        """
        for equipment in self.equipment:
            if equipment.tag == tag:
                return equipment
        raise KeyError(f"unknown equipment tag {tag}")
