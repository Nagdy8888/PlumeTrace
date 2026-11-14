"""Tests for the Open-Meteo client using a mock transport (no network)."""

import json
from datetime import date

import httpx
import pytest

from plumetrace.data_sources.open_meteo import OpenMeteoError, fetch_hourly

PAYLOAD = {
    "hourly": {
        "time": ["2025-07-14T00:00", "2025-07-14T01:00"],
        "wind_speed_10m": [4.66, 5.32],
        "wind_direction_10m": [4, 15],
        "shortwave_radiation": [0.0, 2.0],
        "cloud_cover": [0, 50],
        "temperature_2m": [28.8, 27.3],
    }
}


def _client(payload: dict[str, object], seen: list[httpx.Request]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=json.dumps(payload))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_converts_units_and_sends_expected_query() -> None:
    """Cloud % -> fraction, deg C -> K, m/s requested, UTC requested."""
    seen: list[httpx.Request] = []
    hours = fetch_hourly(_client(PAYLOAD, seen), 39.10, 61.30, date(2025, 7, 14), date(2025, 7, 14))
    assert [h.hour_index for h in hours] == [0, 1]
    assert hours[1].cloud_fraction == pytest.approx(0.5)
    assert hours[0].temp_k == pytest.approx(301.95)
    assert hours[0].wind_from_deg == 4.0 and hours[0].wind_speed_m_s == 4.66
    q = seen[0].url.params
    assert q["wind_speed_unit"] == "ms" and q["timezone"] == "UTC"
    assert q["start_date"] == "2025-07-14"
    assert "shortwave_radiation" in q["hourly"]


def test_missing_values_are_rejected() -> None:
    """A null in any field is an error naming the field and time."""
    bad = json.loads(json.dumps(PAYLOAD))
    bad["hourly"]["wind_speed_10m"][1] = None
    with pytest.raises(OpenMeteoError, match="wind_speed_10m"):
        fetch_hourly(_client(bad, []), 39.1, 61.3, date(2025, 7, 14), date(2025, 7, 14))


def test_http_errors_propagate() -> None:
    """Server errors are not swallowed."""
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_hourly(client, 39.1, 61.3, date(2025, 7, 14), date(2025, 7, 14))
