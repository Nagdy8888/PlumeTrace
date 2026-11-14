"""Open-Meteo historical weather client (public data, no API key, CC BY 4.0).

One GET per call to the archive API (ERA5 reanalysis). The request carries only coordinates,
dates and weather field names; httpx verifies TLS certificates by default and this module never
changes that. The caller owns the ``httpx.Client``, so tests pass a ``MockTransport``.
"""

from datetime import date, datetime, time, timedelta
from typing import Final

import httpx
from pydantic import BaseModel, ValidationError

from plumetrace.engineering.truth_weather import HourlyWeather

ARCHIVE_URL: Final = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_FIELDS: Final = (
    "wind_speed_10m",
    "wind_direction_10m",
    "shortwave_radiation",
    "cloud_cover",
    "temperature_2m",
)
TIMEOUT_S: Final = 20.0
ATTRIBUTION: Final = "Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis."
_WIND_UNIT: Final = "m/s"
_HOUR: Final = timedelta(hours=1)


class OpenMeteoError(RuntimeError):
    """The API answered, but the data is unusable (gaps, wrong shape, wrong units)."""


class _ArchiveResponse(BaseModel):
    """Shape of the archive response that this client relies on."""

    hourly: dict[str, list[str] | list[float | None]]
    hourly_units: dict[str, str] | None = None


def _parse_body(response: httpx.Response) -> _ArchiveResponse:
    """Decode and shape-check the JSON body.

    Args:
        response: A successful (2xx) HTTP response.

    Returns:
        The validated response model.

    Raises:
        OpenMeteoError: If the body is not JSON or lacks the ``hourly`` block.
    """
    try:
        return _ArchiveResponse.model_validate(response.json())
    except ValueError as exc:  # JSONDecodeError and pydantic.ValidationError
        raise OpenMeteoError(f"unexpected Open-Meteo response: {exc}") from exc


def _parse_times(body: _ArchiveResponse, start: date) -> list[str]:
    """Check the time axis: non-empty, starts at ``start`` 00:00 UTC, one hour apart.

    Args:
        body: The validated response.
        start: First requested day.

    Returns:
        The time strings, in order.

    Raises:
        OpenMeteoError: On a missing, empty, unparseable, shifted or gapped time axis.
    """
    raw = body.hourly.get("time")
    if raw is None or not all(isinstance(t, str) for t in raw):
        raise OpenMeteoError("response has no usable time axis")
    if not raw:
        raise OpenMeteoError("response has no hours")
    stamps: list[datetime] = []
    for text in raw:
        try:
            stamp = datetime.fromisoformat(str(text))
        except ValueError as exc:
            raise OpenMeteoError(f"unparseable time {text!r}") from exc
        if stamp.tzinfo is not None:
            raise OpenMeteoError(f"time {text!r} is not a plain UTC timestamp")
        stamps.append(stamp)
    if stamps[0] != datetime.combine(start, time.min):
        raise OpenMeteoError(f"series starts at {raw[0]}, expected start {start}")
    for text, prev, cur in zip(raw[1:], stamps, stamps[1:], strict=False):
        if cur - prev != _HOUR:
            raise OpenMeteoError(f"time axis is not hourly at {text}")
    return [str(t) for t in raw]


def _series(body: _ArchiveResponse, field: str, n: int) -> list[float | None]:
    """Return one field's values after checking it exists and matches the time axis.

    Args:
        body: The validated response.
        field: Open-Meteo variable name.
        n: Number of hours on the time axis.

    Returns:
        The values, ``None`` where the API had a gap.

    Raises:
        OpenMeteoError: If the field is absent, not numeric or has the wrong length.
    """
    values = body.hourly.get(field)
    if values is None:
        raise OpenMeteoError(f"missing field {field}")
    if len(values) != n:
        raise OpenMeteoError(f"{field} has {len(values)} values for {n} hours")
    numbers: list[float | None] = []
    for value in values:
        if isinstance(value, str):
            raise OpenMeteoError(f"non-numeric value in {field}")
        numbers.append(value)
    return numbers


def _check_wind_unit(body: _ArchiveResponse) -> None:
    """Refuse data whose reported wind unit is not m/s (the API default is km/h).

    Args:
        body: The validated response.

    Raises:
        OpenMeteoError: If the response states another wind speed unit.
    """
    reported = (body.hourly_units or {}).get("wind_speed_10m", _WIND_UNIT)
    if reported != _WIND_UNIT:
        raise OpenMeteoError(f"wind_speed_10m is in {reported!r}, expected {_WIND_UNIT!r}")


def _hour(index: int, stamp: str, row: dict[str, float | None]) -> HourlyWeather:
    """Convert one hour of raw Open-Meteo values.

    Args:
        index: Position in the series (becomes ``hour_index``).
        stamp: The hour's time string, for error messages.
        row: Raw value per Open-Meteo field.

    Returns:
        The validated hour: cloud % to fraction, deg C to K.

    Raises:
        OpenMeteoError: On a ``None`` value or a value that fails physical validation.
    """
    vals: dict[str, float] = {}
    for field in HOURLY_FIELDS:
        value = row[field]
        if value is None:
            raise OpenMeteoError(f"missing value for {field} at {stamp}")
        vals[field] = value
    try:
        return HourlyWeather(
            hour_index=index,
            wind_speed_m_s=vals["wind_speed_10m"],
            wind_from_deg=vals["wind_direction_10m"],
            shortwave_w_m2=vals["shortwave_radiation"],
            cloud_fraction=vals["cloud_cover"] / 100,
            temp_k=vals["temperature_2m"] + 273.15,
        )
    except ValidationError as exc:
        problems = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())
        raise OpenMeteoError(f"invalid weather at {stamp}: {problems}") from exc


def fetch_hourly(
    client: httpx.Client,
    latitude_deg: float,
    longitude_deg: float,
    start: date,
    end: date,
) -> list[HourlyWeather]:
    """Fetch hourly ERA5 weather from Open-Meteo for ``start`` to ``end`` inclusive.

    Args:
        client: HTTP client to use (the caller owns it; tests pass a mock transport).
        latitude_deg: Latitude in degrees.
        longitude_deg: Longitude in degrees.
        start: First day, UTC.
        end: Last day, UTC.

    Returns:
        One ``HourlyWeather`` per hour with ``hour_index`` 0, 1, 2, ...

    Raises:
        ValueError: If ``end`` is before ``start``.
        httpx.HTTPError: On a transport error, a timeout or a non-2xx status.
        OpenMeteoError: If the response has gaps (``None``), a gapped or shifted time axis,
            a wrong wind unit, or values that fail physical validation.
    """
    if end < start:
        raise ValueError(f"end {end} is before start {start}")
    response = client.get(
        ARCHIVE_URL,
        params={
            "latitude": latitude_deg,
            "longitude": longitude_deg,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(HOURLY_FIELDS),
            "wind_speed_unit": "ms",
            "timezone": "UTC",
        },
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    body = _parse_body(response)
    _check_wind_unit(body)
    times = _parse_times(body, start)
    columns = {f: _series(body, f, len(times)) for f in HOURLY_FIELDS}
    return [
        _hour(i, stamp, {f: columns[f][i] for f in HOURLY_FIELDS}) for i, stamp in enumerate(times)
    ]
