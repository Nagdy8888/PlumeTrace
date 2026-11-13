"""Shared fixtures for facility tests."""

from typing import Any

import pytest


def _site() -> dict[str, Any]:
    """Return the site, gas and operating part of the minimal spec."""
    return {
        "site": {
            "id": "T",
            "name": "Test site",
            "fictional": True,
            "bounds": {"x_min_m": 0, "x_max_m": 100, "y_min_m": 0, "y_max_m": 100},
            "latitude_deg": 0.0,
            "longitude_deg": 0.0,
            "elevation_m": 0.0,
            "ambient_pressure_pa": 101325.0,
        },
        "gas_composition": {"CH4": 0.95, "N2": 0.05},
        "operating": {
            "suction_pressure_pa": 4.5e6,
            "discharge_pressure_pa": 7.0e6,
            "gas_temperature_k": 300.0,
            "throughput_sm3_h": 1000.0,
        },
    }


def _equipment() -> list[dict[str, Any]]:
    """Return the equipment part of the minimal spec."""
    return [
        {
            "tag": "K-202",
            "type": "recip_compressor",
            "position_m": [50, 50, 0],
            "rotation_deg": 0,
            "size_m": [12, 4, 3],
            "vents_to": "VS-250",
            "anchors": [
                {"id": "K-202.packing", "position_m": [48, 50, 1.5], "emission_point": True}
            ],
        },
        {
            "tag": "VS-250",
            "type": "vent_stack",
            "position_m": [60, 80, 0],
            "rotation_deg": 0,
            "size_m": [0.4, 0.4, 12],
            "anchors": [{"id": "VS-250.tip", "position_m": [60, 80, 12], "emission_point": True}],
        },
    ]


def _piping_and_instruments() -> dict[str, Any]:
    """Return the piping and instruments part of the minimal spec."""
    return {
        "piping": [
            {
                "id": "R-1",
                "service": "vent",
                "size_in": 2,
                "waypoints_m": [[48, 50, 2], [60, 80, 1]],
            }
        ],
        "instruments": [
            {"tag": "AT-1", "kind": "methane_point", "position_m": [90, 50, 2], "noise_ppm": 0.3},
            {"tag": "FT-1", "kind": "flow", "position_m": [60, 78, 1], "attaches_to": "VS-250"},
        ],
    }


def _minimal_spec() -> dict[str, Any]:
    """Return a small valid facility spec dict (fresh copy on every call)."""
    return {**_site(), "equipment": _equipment(), **_piping_and_instruments()}


@pytest.fixture
def minimal_spec() -> dict[str, Any]:
    """A small valid facility spec as a plain dict."""
    return _minimal_spec()
