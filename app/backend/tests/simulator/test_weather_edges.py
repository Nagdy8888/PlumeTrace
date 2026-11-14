"""Edge cases of the weather snapshot loader and slicing; the committed file's format."""

import json
from pathlib import Path

import pytest

from plumetrace.simulator.weather import DEFAULT_SNAPSHOT_PATH, load_snapshot, slice_hours


def _hour(i: int) -> dict[str, object]:
    return {
        "hour_index": i,
        "wind_speed_m_s": 3.0,
        "wind_from_deg": 90.0,
        "shortwave_w_m2": 0.0,
        "cloud_fraction": 0.2,
        "temp_k": 295.0,
    }


def _write(tmp_path: Path, **overrides: object) -> Path:
    doc: dict[str, object] = {
        "start_utc": "2025-07-14T00:00:00Z",
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis.",
        "hours": [_hour(i) for i in range(4)],
    }
    doc.update(overrides)
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_valid_file_loads(tmp_path: Path) -> None:
    """A well-formed file loads with UTC start and its hours."""
    snap = load_snapshot(_write(tmp_path))
    offset = snap.start_utc.utcoffset()
    assert len(snap.hours) == 4
    assert offset is not None and offset.total_seconds() == 0


def test_gap_in_hour_index_is_rejected(tmp_path: Path) -> None:
    """hour_index must run 0..n-1 without gaps."""
    hours = [_hour(0), _hour(1), _hour(3)]
    with pytest.raises(ValueError, match="contiguous"):
        load_snapshot(_write(tmp_path, hours=hours))


def test_unordered_hour_index_is_rejected(tmp_path: Path) -> None:
    """Out-of-order hour_index values are not contiguous 0..n-1."""
    with pytest.raises(ValueError, match="contiguous"):
        load_snapshot(_write(tmp_path, hours=[_hour(1), _hour(0)]))


def test_null_value_is_rejected(tmp_path: Path) -> None:
    """A null in an hour (a data gap) fails to load."""
    hours = [_hour(0), {**_hour(1), "wind_speed_m_s": None}]
    with pytest.raises(ValueError, match="wind_speed_m_s"):
        load_snapshot(_write(tmp_path, hours=hours))


def test_empty_hours_are_rejected(tmp_path: Path) -> None:
    """A snapshot without hours is an error."""
    with pytest.raises(ValueError, match="no hours"):
        load_snapshot(_write(tmp_path, hours=[]))


@pytest.mark.parametrize("key", ["start_utc", "attribution", "hours"])
def test_missing_key_is_rejected(tmp_path: Path, key: str) -> None:
    """Each top-level key is required and the error names it."""
    path = _write(tmp_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc[key]
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match=key):
        load_snapshot(path)


def test_blank_attribution_is_rejected(tmp_path: Path) -> None:
    """CC BY needs attribution, so an empty one is refused."""
    with pytest.raises(ValueError, match="attribution"):
        load_snapshot(_write(tmp_path, attribution="  "))


def test_naive_start_is_rejected(tmp_path: Path) -> None:
    """start_utc must carry a UTC marker."""
    with pytest.raises(ValueError, match="start_utc"):
        load_snapshot(_write(tmp_path, start_utc="2025-07-14T00:00:00"))


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    """Broken JSON raises ValueError (JSONDecodeError is one)."""
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match=r"."):
        load_snapshot(path)


@pytest.mark.parametrize(("offset", "hours"), [(-1, 3), (0, 0), (0, -2)])
def test_slice_rejects_nonsense_arguments(offset: int, hours: int) -> None:
    """Negative offsets and empty slices are refused instead of wrapping around."""
    snap = load_snapshot()
    with pytest.raises(ValueError, match="offset_h"):
        slice_hours(snap, offset, hours)


def test_slice_to_the_exact_end_works() -> None:
    """The last hour of the week can be sliced."""
    snap = load_snapshot()
    part = slice_hours(snap, 167, 1)
    assert len(part) == 1 and part[0].wind_speed_m_s == snap.hours[167].wind_speed_m_s


def test_committed_file_is_generated_output_format() -> None:
    """UTF-8, LF, sorted keys, indent 2, trailing newline, no nulls, 168 hours."""
    raw = DEFAULT_SNAPSHOT_PATH.read_bytes()
    text = raw.decode("utf-8")
    assert b"\r" not in raw and text.endswith("}\n")
    doc = json.loads(text)
    assert text == json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    assert "null" not in text
    assert len(doc["hours"]) == 168
    assert doc["start_utc"] == "2025-07-14T00:00:00Z"
