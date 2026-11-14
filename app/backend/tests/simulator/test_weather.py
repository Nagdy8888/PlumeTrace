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
