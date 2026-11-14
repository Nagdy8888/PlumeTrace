"""Tests for window_mode_class: per-window most frequent stability class."""

from collections import Counter

from hypothesis import given, settings
from hypothesis import strategies as st

from plumetrace.engineering.averaging import window_mode_class
from plumetrace.engineering.stability import StabilityClass

LAW = settings(max_examples=200, derandomize=True, deadline=None, database=None)
A, B, C, D, E = (
    StabilityClass.A,
    StabilityClass.B,
    StabilityClass.C,
    StabilityClass.D,
    StabilityClass.E,
)


def _oracle_mode(classes: list[StabilityClass]) -> StabilityClass:
    """The per-slice logic of benchmark.runner at 23b8703 (copied as the oracle)."""
    counts = Counter(classes)
    return min(counts, key=lambda c: (-counts[c], c.value))


def _oracle(classes: list[StabilityClass], n: int, windows: int) -> list[StabilityClass]:
    return [_oracle_mode(classes[k * n : (k + 1) * n]) for k in range(windows)]


def test_mode_per_window() -> None:
    """The most frequent class wins in each window."""
    s = [D, D, E, E, E, D]
    assert window_mode_class(s, 3, 2) == [D, E]


def test_ties_go_to_the_alphabetically_first_class() -> None:
    """A 2-2 tie between E and B gives B; a three-way tie gives A."""
    assert window_mode_class([E, B, E, B], 4, 1) == [B]
    assert window_mode_class([C, A, B], 3, 1) == [A]


def test_zero_windows_gives_empty_list() -> None:
    """n_windows = 0 returns an empty list."""
    assert window_mode_class([A] * 5, 2, 0) == []


@LAW
@given(
    classes=st.lists(st.sampled_from(list(StabilityClass)), min_size=1, max_size=60),
    n=st.integers(min_value=1, max_value=12),
)
def test_equals_the_old_per_slice_logic(classes: list[StabilityClass], n: int) -> None:
    """Equals the old benchmark logic for every length, with ties and a partial last window."""
    complete = len(classes) // n
    for windows in {complete, max(complete - 1, 0)}:
        assert window_mode_class(classes, n, windows) == _oracle(classes, n, windows)
    # a trailing partial window, asked for explicitly, is the mode of the short tail
    if len(classes) % n:
        assert window_mode_class(classes, n, complete + 1) == _oracle(classes, n, complete + 1)
