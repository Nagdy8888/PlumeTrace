"""Edge cases of the Open-Meteo client: bad ranges, gaps, malformed bodies (no network)."""

import copy
import inspect
import json
from datetime import date

import httpx
import pytest

from plumetrace.data_sources import open_meteo
from plumetrace.data_sources.open_meteo import TIMEOUT_S, OpenMeteoError, fetch_hourly

DAY = date(2025, 7, 14)


def _payload(n: int = 3) -> dict[str, dict[str, list[object]]]:
    return {
        "hourly": {
            "time": [f"2025-07-14T{h:02d}:00" for h in range(n)],
            "wind_speed_10m": [4.0 + h for h in range(n)],
            "wind_direction_10m": [10 * h for h in range(n)],
            "shortwave_radiation": [0.0] * n,
            "cloud_cover": [10] * n,
            "temperature_2m": [20.0] * n,
        }
    }


def _serve(body: bytes | str, seen: list[httpx.Request] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, content=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _fetch(payload: object) -> list[object]:
    return list(fetch_hourly(_serve(json.dumps(payload)), 39.1, 61.3, DAY, DAY))


def test_end_before_start_is_rejected_without_a_request() -> None:
    """An inverted date range fails before any request is sent."""
    seen: list[httpx.Request] = []
    with pytest.raises(ValueError, match="end"):
        fetch_hourly(_serve(json.dumps(_payload()), seen), 39.1, 61.3, date(2025, 7, 15), DAY)
    assert seen == []


def test_time_axis_with_a_gap_is_rejected() -> None:
    """Hours must be consecutive; a skipped hour in the time axis is an error."""
    bad = _payload()
    bad["hourly"]["time"][2] = "2025-07-14T03:00"
    with pytest.raises(OpenMeteoError, match="time"):
        _fetch(bad)


def test_series_must_start_at_the_start_date() -> None:
    """A series that begins on another day than requested is an error."""
    bad = _payload()
    bad["hourly"]["time"] = [f"2025-07-15T{h:02d}:00" for h in range(3)]
    with pytest.raises(OpenMeteoError, match="start"):
        _fetch(bad)


def test_unparseable_time_is_rejected() -> None:
    """A time string that is not ISO 8601 is an OpenMeteoError."""
    bad = _payload()
    bad["hourly"]["time"][1] = "yesterday"
    with pytest.raises(OpenMeteoError, match="time"):
        _fetch(bad)


def test_array_length_mismatch_is_rejected() -> None:
    """A field with fewer values than the time axis names the field."""
    bad = _payload()
    bad["hourly"]["cloud_cover"] = [10, 10]
    with pytest.raises(OpenMeteoError, match="cloud_cover"):
        _fetch(bad)


def test_missing_field_is_rejected() -> None:
    """A field that is absent from the response names the field."""
    bad = _payload()
    del bad["hourly"]["temperature_2m"]
    with pytest.raises(OpenMeteoError, match="temperature_2m"):
        _fetch(bad)


def test_empty_series_is_rejected() -> None:
    """A response without any hour is an error, not an empty list."""
    with pytest.raises(OpenMeteoError, match="no hours"):
        _fetch({"hourly": {k: [] for k in _payload()["hourly"]}})


@pytest.mark.parametrize("body", ["not json", "[1, 2]", '{"hourly": 3}', "{}"])
def test_malformed_body_is_an_open_meteo_error(body: str) -> None:
    """Bodies that are not the expected JSON shape raise OpenMeteoError."""
    with pytest.raises(OpenMeteoError):
        fetch_hourly(_serve(body), 39.1, 61.3, DAY, DAY)


def test_api_error_body_is_an_open_meteo_error() -> None:
    """An error document with HTTP 200 and no hourly block raises OpenMeteoError."""
    body = json.dumps({"error": True, "reason": "bad parameter"})
    with pytest.raises(OpenMeteoError):
        fetch_hourly(_serve(body), 39.1, 61.3, DAY, DAY)


def test_non_finite_value_is_rejected() -> None:
    """NaN in the response is an OpenMeteoError naming the time."""
    body = json.dumps(_payload()).replace("[4.0, 5.0, 6.0]", "[4.0, NaN, 6.0]")
    assert "NaN" in body
    with pytest.raises(OpenMeteoError, match="2025-07-14T01:00"):
        fetch_hourly(_serve(body), 39.1, 61.3, DAY, DAY)


def test_unphysical_value_is_rejected() -> None:
    """Cloud cover above 100 % fails validation as an OpenMeteoError."""
    bad = copy.deepcopy(_payload())
    bad["hourly"]["cloud_cover"][1] = 120
    with pytest.raises(OpenMeteoError, match="2025-07-14T01:00"):
        _fetch(bad)


def test_wind_unit_other_than_ms_is_rejected() -> None:
    """If the API reports km/h despite wind_speed_unit=ms, refuse the data."""
    bad: dict[str, object] = dict(_payload())
    bad["hourly_units"] = {"wind_speed_10m": "km/h"}
    with pytest.raises(OpenMeteoError, match="m/s"):
        _fetch(bad)


def test_wind_unit_ms_is_accepted() -> None:
    """The documented unit label for ms passes."""
    ok: dict[str, object] = dict(_payload())
    ok["hourly_units"] = {"wind_speed_10m": "m/s"}
    assert len(_fetch(ok)) == 3


def test_timeout_is_set_and_timeouts_propagate() -> None:
    """TIMEOUT_S is sent on the request and a transport timeout is not swallowed."""
    seen: list[httpx.Request] = []
    fetch_hourly(_serve(json.dumps(_payload()), seen), 39.1, 61.3, DAY, DAY)
    assert seen[0].extensions["timeout"]["read"] == TIMEOUT_S

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    client = httpx.Client(transport=httpx.MockTransport(boom))
    with pytest.raises(httpx.TimeoutException):
        fetch_hourly(client, 39.1, 61.3, DAY, DAY)


def test_request_carries_only_weather_parameters() -> None:
    """The query holds coordinates, dates and weather fields; no key, no user data."""
    seen: list[httpx.Request] = []
    fetch_hourly(_serve(json.dumps(_payload()), seen), 39.1, 61.3, DAY, DAY)
    assert set(seen[0].url.params) == {
        "latitude",
        "longitude",
        "start_date",
        "end_date",
        "hourly",
        "wind_speed_unit",
        "timezone",
    }
    assert seen[0].url.host == "archive-api.open-meteo.com"
    assert seen[0].url.scheme == "https"
    assert "authorization" not in seen[0].headers


def test_tls_verification_is_not_disabled_in_the_client_module() -> None:
    """The module never touches TLS settings (httpx verifies certificates by default)."""
    source = inspect.getsource(open_meteo)
    assert "verify" not in source
    assert "http://" not in source
