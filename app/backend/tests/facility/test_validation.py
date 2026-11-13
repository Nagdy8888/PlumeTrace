"""Validation tests: a broken spec fails with a message naming the offending item."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from plumetrace.facility.spec import FacilitySpec

Mutation = Callable[[dict[str, Any]], None]


def test_minimal_spec_is_valid(minimal_spec: dict[str, Any]) -> None:
    """The fixture itself is valid."""
    FacilitySpec.model_validate(minimal_spec)


def _dup_tag(s: dict[str, Any]) -> None:
    s["equipment"].append(dict(s["equipment"][0], anchors=[]))


def _foreign_anchor(s: dict[str, Any]) -> None:
    s["equipment"][0]["anchors"][0]["id"] = "K-999.packing"


def _out_of_bounds(s: dict[str, Any]) -> None:
    s["equipment"][0]["position_m"] = [250, 10, 0]


def _below_ground(s: dict[str, Any]) -> None:
    s["instruments"][0]["position_m"] = [90, 50, -1]


def _pipe_out(s: dict[str, Any]) -> None:
    s["piping"][0]["waypoints_m"][1] = [60, 180, 1]


def _bad_vent(s: dict[str, Any]) -> None:
    s["equipment"][0]["vents_to"] = "VS-999"


def _bad_attach(s: dict[str, Any]) -> None:
    s["instruments"][1]["attaches_to"] = "X-1"


def _bad_sum(s: dict[str, Any]) -> None:
    s["gas_composition"] = {"CH4": 0.94, "N2": 0.05}


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_dup_tag, "duplicate tag K-202"),
        (_foreign_anchor, "K-999.packing"),
        (_out_of_bounds, "K-202"),
        (_below_ground, "AT-1"),
        (_pipe_out, "R-1"),
        (_bad_vent, "VS-999"),
        (_bad_attach, "X-1"),
        (_bad_sum, "0.99"),
    ],
)
def test_invalid_spec_names_the_item(
    minimal_spec: dict[str, Any], mutate: Mutation, expected: str
) -> None:
    """Each broken spec raises a ValidationError whose message names the offending item."""
    mutate(minimal_spec)
    with pytest.raises(ValidationError, match=expected):
        FacilitySpec.model_validate(minimal_spec)


def test_unknown_field_is_rejected(minimal_spec: dict[str, Any]) -> None:
    """Typos in field names are errors, not silently ignored."""
    minimal_spec["equipment"][0]["vent_to"] = "VS-250"
    with pytest.raises(ValidationError):
        FacilitySpec.model_validate(minimal_spec)
