"""Fetch the KS-07 weather week from Open-Meteo and write the committed snapshot.

One real request to the free public Open-Meteo archive API (no key, no account). The output is
deterministic: UTF-8, LF line endings, sorted keys, trailing newline. If the request fails, the
data has gaps or the hour count is wrong, nothing is written and the exit code is 1.

Run it from the repo root::

    cd app && uv run python ../scripts/fetch_weather.py

The output is generated - never edit it by hand. Data: Open-Meteo.com, CC BY 4.0.
"""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Final

import httpx

from plumetrace.data_sources.open_meteo import ATTRIBUTION, OpenMeteoError, fetch_hourly
from plumetrace.engineering.truth_weather import HourlyWeather
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.weather import DEFAULT_SNAPSHOT_PATH

SNAPSHOT_OUT: Final[Path] = DEFAULT_SNAPSHOT_PATH
START: Final = date(2025, 7, 14)
END: Final = date(2025, 7, 20)
EXPECTED_HOURS: Final = 168


def build_snapshot(hours: list[HourlyWeather]) -> dict[str, object]:
    """Build the snapshot document from fetched hours.

    Args:
        hours: Hourly weather starting 2025-07-14 00:00 UTC.

    Returns:
        The JSON-compatible snapshot.

    Raises:
        OpenMeteoError: If the series is not exactly 168 hours.
    """
    if len(hours) != EXPECTED_HOURS:
        raise OpenMeteoError(f"expected {EXPECTED_HOURS} hours, got {len(hours)}")
    return {
        "start_utc": "2025-07-14T00:00:00Z",
        "attribution": ATTRIBUTION,
        "hours": [h.model_dump(mode="json") for h in hours],
    }


def write_json(path: Path, data: object) -> None:
    """Write ``data`` as deterministic JSON (UTF-8, LF, sorted keys, trailing newline).

    Bytes are written so Windows never converts LF line endings to CRLF.

    Args:
        path: Target file; parent directories are created.
        data: JSON-serialisable data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))


def main() -> int:
    """Fetch the week, validate it and write the snapshot.

    Returns:
        0 on success; 1 if the request failed or the data is unusable (nothing is written).
    """
    site = load_facility().site
    try:
        with httpx.Client() as client:
            hours = fetch_hourly(client, site.latitude_deg, site.longitude_deg, START, END)
        snapshot = build_snapshot(hours)
    except httpx.HTTPError as exc:
        print(f"Open-Meteo request failed: {exc}", file=sys.stderr)
        return 1
    except OpenMeteoError as exc:
        print(f"Open-Meteo data unusable: {exc}", file=sys.stderr)
        return 1
    write_json(SNAPSHOT_OUT, snapshot)
    print(SNAPSHOT_OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
