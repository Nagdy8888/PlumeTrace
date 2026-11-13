"""Tests for window averaging and wind statistics."""

import numpy as np
import pytest

from plumetrace.engineering.averaging import circular_mean_deg, is_calm, window_means, window_wind


def test_two_complete_windows_and_partial_dropped() -> None:
    """25 min of 10 s samples -> 2 complete 10-min windows; the 5-min tail is dropped."""
    t = np.arange(0.0, 1500.0, 10.0)
    v = np.column_stack([np.where(t < 600.0, 1.0, 3.0), np.full(t.shape, 2.0)])
    starts, means = window_means(t, v)
    assert starts.tolist() == [0.0, 600.0]
    assert means.shape == (2, 2)
    assert means[:, 0].tolist() == [1.0, 3.0]
    assert means[:, 1].tolist() == [2.0, 2.0]


def test_low_coverage_window_is_nan() -> None:
    """A sensor with 70 % NaN samples in a window gives NaN for that window."""
    t = np.arange(0.0, 600.0, 10.0)
    v = np.ones((60, 1))
    v[:42, 0] = np.nan
    _, means = window_means(t, v)
    assert np.isnan(means[0, 0])


def test_half_coverage_window_is_kept() -> None:
    """Exactly 50 % valid samples is enough."""
    t = np.arange(0.0, 600.0, 10.0)
    v = np.ones((60, 1))
    v[:30, 0] = np.nan
    _, means = window_means(t, v)
    assert means[0, 0] == 1.0


def test_circular_mean_wraps_around_north() -> None:
    """359 and 1 degrees average to 0, not 180."""
    assert circular_mean_deg(np.array([359.0, 1.0])) == pytest.approx(0.0, abs=1e-9)
    assert circular_mean_deg(np.array([350.0, 20.0])) == pytest.approx(5.0, abs=1e-9)
    assert circular_mean_deg(np.array([90.0, 90.0, 270.0])) == pytest.approx(90.0, abs=1e-9)


def test_window_wind() -> None:
    """Mean speed is arithmetic; mean direction is circular."""
    t = np.arange(0.0, 600.0, 10.0)
    speed = np.where(np.arange(60) % 2 == 0, 3.0, 5.0)
    direction = np.where(np.arange(60) % 2 == 0, 355.0, 5.0)
    s, d = window_wind(t, speed, direction)
    assert s.tolist() == [4.0]
    assert d[0] == pytest.approx(0.0, abs=1e-9)


def test_calm_threshold() -> None:
    """Below 1 m/s is calm; 1 m/s is not."""
    assert is_calm(0.99) is True
    assert is_calm(1.0) is False
