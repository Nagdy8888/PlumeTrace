"""Edge cases of window averaging: short series, bad lengths, empty input."""

import numpy as np
import pytest

from plumetrace.engineering.averaging import circular_mean_deg, window_means, window_wind


def test_fewer_samples_than_one_window_gives_empty_results() -> None:
    """5 min of samples holds no complete 10-min window: empty arrays, not an error."""
    t = np.arange(0.0, 300.0, 10.0)
    starts, means = window_means(t, np.ones((30, 2)))
    assert starts.shape == (0,)
    assert means.shape == (0, 2)
    s, d = window_wind(t, np.ones(30), np.full(30, 90.0))
    assert s.shape == (0,)
    assert d.shape == (0,)


@pytest.mark.parametrize("n_samples", [0, 1])
def test_fewer_than_two_samples_is_value_error(n_samples: int) -> None:
    """The step dt needs two samples; fewer raises a clear ValueError."""
    t = np.zeros(n_samples)
    with pytest.raises(ValueError, match="at least two samples"):
        window_means(t, np.ones((n_samples, 1)))
    with pytest.raises(ValueError, match="at least two samples"):
        window_wind(t, np.ones(n_samples), np.ones(n_samples))


@pytest.mark.parametrize("n_values", [59, 61])
def test_length_mismatch_is_value_error(n_values: int) -> None:
    """A values or wind array longer or shorter than times_s is rejected."""
    t = np.arange(0.0, 600.0, 10.0)
    with pytest.raises(ValueError, match="length"):
        window_means(t, np.ones((n_values, 1)))
    with pytest.raises(ValueError, match="length"):
        window_wind(t, np.ones(n_values), np.ones(60))
    with pytest.raises(ValueError, match="length"):
        window_wind(t, np.ones(60), np.ones(n_values))


def test_circular_mean_of_empty_is_value_error() -> None:
    """The mean of no directions is undefined; it must not return 0.0 (north)."""
    with pytest.raises(ValueError, match="empty"):
        circular_mean_deg(np.array([]))
