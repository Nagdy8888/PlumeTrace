"""Edge-case tests of the replay schema: strict fields, versions, consistency on load."""

import base64
import math
from typing import Any

import pytest
from pydantic import ValidationError

from plumetrace.simulator.replay_schema import (
    KEYFRAME_STEP_S,
    MAX_REPLAY_BYTES,
    REPLAY_SCHEMA_VERSION,
    REPLAY_STEP_S,
    ReplayScenario,
)

GRID_B64 = base64.b64encode(bytes(6)).decode("ascii")


def _doc() -> dict[str, Any]:
    """A minimal valid replay document: 4 one-minute samples, 2 key frames, a 3 x 2 grid."""
    frame = {
        "t_s": 0.0,
        "wind_speed_m_s": 3.0,
        "wind_from_deg": 250.0,
        "stability": "D",
        "sources": [{"anchor_id": "VS-250.tip", "rate_kg_h": 15.0}],
        "grid_b64": GRID_B64,
    }
    return {
        "schema_version": 1,
        "scenario_id": "s9_test",
        "title": "Test",
        "sim_start_utc": "2025-07-14T00:00:00Z",
        "duration_s": 240.0,
        "step_s": 60.0,
        "sensors": [{"id": "AT-101", "x_m": 1.0, "y_m": 2.0, "z_m": 3.0}],
        "series": {"AT-101": [2.0, None, 2.1, 2.2], "FT-250": [0.9, 1.0, 1.1, 1.2]},
        "units": {"AT-101": "ppm", "FT-250": "kg/h"},
        "wind_speed_m_s": [3.0, 3.1, 3.2, 3.3],
        "wind_from_deg": [250.0, 251.0, 252.0, 253.0],
        "stability": ["D", "D", "D", "D"],
        "events": [],
        "log": [{"t_s": 0.0, "kind": "permit", "tag": None, "text": "Hot work"}],
        "grid": {
            "x0_m": 0.0,
            "y0_m": 0.0,
            "dx_m": 5.0,
            "dy_m": 5.0,
            "nx": 3,
            "ny": 2,
            "encoding": "log_u8_0.1_1000ppm",
        },
        "keyframes": [frame, {**frame, "t_s": 120.0}],
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0).",
        "simulated": True,
    }


def test_constants_match_the_plan() -> None:
    """Version 1, 60 s samples, 120 s key frames, 5 MB budget."""
    assert (REPLAY_SCHEMA_VERSION, REPLAY_STEP_S, KEYFRAME_STEP_S) == (1, 60.0, 120.0)
    assert MAX_REPLAY_BYTES == 5_000_000


def test_valid_document_loads_and_round_trips() -> None:
    """The minimal document validates and dumps back to equal data."""
    replay = ReplayScenario.model_validate(_doc())
    assert replay.series["AT-101"][1] is None
    assert ReplayScenario.model_validate_json(replay.model_dump_json()) == replay


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), 2),
        (("simulated",), False),
        (("grid", "encoding"), "log_u8_1_100ppm"),
        (("extra_field",), 1),
        (("sensors", 0, "colour"), "red"),
        (("keyframes", 0, "stability_text"), "stable"),
    ],
)
def test_version_literals_and_unknown_fields_are_rejected(
    path: tuple[Any, ...], value: Any
) -> None:
    """A newer schema version, a non-simulated file or an unknown field fails on load."""
    doc = _doc()
    node: Any = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(ValidationError):
        ReplayScenario.model_validate(doc)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_rejected(bad: float) -> None:
    """NaN would make invalid JSON: it must be None in a series, and never appear elsewhere."""
    doc = _doc()
    doc["series"]["FT-250"][0] = bad
    with pytest.raises(ValidationError):
        ReplayScenario.model_validate(doc)
    doc = _doc()
    doc["wind_speed_m_s"][0] = bad
    with pytest.raises(ValidationError):
        ReplayScenario.model_validate(doc)


def _mutations() -> list[tuple[str, Any]]:
    """Each (description, function that breaks a valid document) pair."""

    def short_wind(d: dict[str, Any]) -> None:
        d["wind_speed_m_s"] = d["wind_speed_m_s"][:3]

    def short_series(d: dict[str, Any]) -> None:
        d["series"]["AT-101"] = d["series"]["AT-101"][:3]

    def unit_missing(d: dict[str, Any]) -> None:
        del d["units"]["FT-250"]

    def wrong_duration(d: dict[str, Any]) -> None:
        d["duration_s"] = 600.0

    def bad_step(d: dict[str, Any]) -> None:
        d["step_s"] = 0.0

    def short_grid(d: dict[str, Any]) -> None:
        d["keyframes"][1]["grid_b64"] = base64.b64encode(bytes(5)).decode("ascii")

    def not_base64(d: dict[str, Any]) -> None:
        d["keyframes"][0]["grid_b64"] = "***"

    def late_frames(d: dict[str, Any]) -> None:
        d["keyframes"][1]["t_s"] = 0.0

    def blank_attribution(d: dict[str, Any]) -> None:
        d["attribution"] = "  "

    return [
        (f.__name__, f)
        for f in (
            short_wind,
            short_series,
            unit_missing,
            wrong_duration,
            bad_step,
            short_grid,
            not_base64,
            late_frames,
            blank_attribution,
        )
    ]


@pytest.mark.parametrize(("name", "mutate"), _mutations())
def test_inconsistent_documents_are_rejected(name: str, mutate: Any) -> None:
    """Lengths, units, durations, grid sizes and key-frame order must agree."""
    doc = _doc()
    mutate(doc)
    with pytest.raises(ValidationError):
        ReplayScenario.model_validate(doc)
