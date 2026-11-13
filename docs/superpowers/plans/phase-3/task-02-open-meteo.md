# Phase 3 · Task 2 — Real weather from Open-Meteo

**Skills:** `plan-execution`, `security-checks` (outbound HTTP rules), `project-documentation`.

**Why:** the plumes are driven by real hourly weather for the site's coordinates (design §8). The
fetched data is committed as a snapshot so scenarios are reproducible offline. Open-Meteo data is
CC BY 4.0 and must be attributed.

The API was probed by the planner on 2026-11-13: the URL and field names below are correct.

## Files
| Action | Path |
|---|---|
| Modify | `app/backend/pyproject.toml` → add `"httpx==0.28.1"` |
| Create | `app/backend/plumetrace/data_sources/__init__.py`, `app/backend/plumetrace/data_sources/open_meteo.py` |
| Create | `app/backend/plumetrace/simulator/__init__.py`, `app/backend/plumetrace/simulator/weather.py` |
| Create | `scripts/fetch_weather.py` |
| Generated (committed) | `app/backend/plumetrace/simulator/data/weather_ks07_2025-07-14_2025-07-20.json` |
| Create | `app/backend/tests/data_sources/test_open_meteo.py`, `app/backend/tests/simulator/test_weather.py` |

## Interface
`data_sources/open_meteo.py`:
- `ARCHIVE_URL: Final = "https://archive-api.open-meteo.com/v1/archive"`
- `HOURLY_FIELDS: Final = ("wind_speed_10m", "wind_direction_10m", "shortwave_radiation", "cloud_cover", "temperature_2m")`
- `TIMEOUT_S: Final = 20.0`
- `ATTRIBUTION: Final = "Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis."`
- `class OpenMeteoError(RuntimeError)`
- `def fetch_hourly(client: httpx.Client, latitude_deg: float, longitude_deg: float, start: date, end: date) -> list[HourlyWeather]` — GET with params `latitude`, `longitude`, `start_date` / `end_date` (ISO), `hourly=",".join(HOURLY_FIELDS)`, `wind_speed_unit="ms"`, `timezone="UTC"`, `timeout=TIMEOUT_S`; `response.raise_for_status()`; validate the JSON with a private Pydantic model `_ArchiveResponse` (`hourly: dict[str, list[float | None]]` + `hourly["time"]: list[str]`); raise `OpenMeteoError(f"missing value for {field} at {time}")` on any `None`; convert: `cloud_fraction = cloud_cover/100`, `temp_k = temperature_2m + 273.15`; `hour_index` = position (0, 1, 2, …).

`simulator/weather.py`:
- `@dataclass(frozen=True) class WeatherSnapshot: start_utc: datetime; hours: list[HourlyWeather]; attribution: str`
- `DEFAULT_SNAPSHOT_PATH: Final[Path]` = the committed JSON path above
- `def load_snapshot(path: Path = DEFAULT_SNAPSHOT_PATH) -> WeatherSnapshot` — JSON `{"start_utc": "...Z", "attribution": "...", "hours": [HourlyWeather dicts]}`; validates contiguous `hour_index` 0..n-1.
- `def slice_hours(snapshot: WeatherSnapshot, offset_h: int, hours: int) -> list[HourlyWeather]` — returns re-indexed hours (`hour_index` from 0); raises `ValueError(f"snapshot has {n} hours, need {offset_h + hours}")` when too short.

`scripts/fetch_weather.py` — `main()` uses `load_facility()` for lat/lon, fetches 2025-07-14 … 2025-07-20 (168 hours) with `httpx.Client()`, writes the JSON (UTF-8, LF, `sort_keys=True`, `indent=2`) with `"start_utc": "2025-07-14T00:00:00Z"` and the attribution. Run: `cd app && uv run python ../scripts/fetch_weather.py`.

## Tests (full code)

`app/backend/tests/data_sources/test_open_meteo.py`:
```python
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
```

`app/backend/tests/simulator/test_weather.py`:
```python
"""Tests for the committed weather snapshot."""

import pytest

from plumetrace.simulator.weather import load_snapshot, slice_hours


def test_snapshot_is_a_full_week_with_attribution() -> None:
    """168 contiguous hours from 2025-07-14 00:00 UTC, attributed to Open-Meteo."""
    snap = load_snapshot()
    assert len(snap.hours) == 168
    assert snap.start_utc.isoformat().startswith("2025-07-14T00:00:00")
    assert "Open-Meteo" in snap.attribution
    assert all(0.0 <= h.cloud_fraction <= 1.0 for h in snap.hours)


def test_slice_reindexes_and_checks_length() -> None:
    """Slices start at hour_index 0; too-long requests fail with a clear message."""
    snap = load_snapshot()
    part = slice_hours(snap, 30, 7)
    assert [h.hour_index for h in part] == list(range(7))
    assert part[0].wind_speed_m_s == snap.hours[30].wind_speed_m_s
    with pytest.raises(ValueError, match="need 170"):
        slice_hours(snap, 165, 5)
```

## Steps
- [ ] Add httpx; `uv sync`. Write tests → FAIL. Implement `open_meteo.py`, `weather.py`, the script.
- [ ] Run the script (network). If the request fails, STOP and report the error. Commit the generated JSON.
- [ ] Full checks green (`check_structure.py`: `data_sources` imports only `engineering`/`facility`/`config`; `simulator` imports `engineering`/`facility`).
- [ ] **Docs.** SIMULATOR.md → "Weather": source, period, fields, conversions, attribution text, how to refresh. `docs/reference/SECURITY.md` (create with a "Outbound network" section): Open-Meteo is the only outbound call besides OpenAI/LangSmith; timeout; TLS verified (httpx default). Add SECURITY.md to `docs/README.md`. Work-log; `STATUS.md` (last 3.2, next 3.3).
- [ ] **Commit** `feat(weather): add Open-Meteo client and KS-07 weather snapshot`.
