"""Splitting ``InversionInput`` into ``inversion_input.py`` keeps the names of ``inversion``.

``inversion`` re-exports the input model and its constants, so every earlier import keeps working
and gives the very same objects.
"""

from plumetrace.engineering import inversion, inversion_input

PUBLIC_NAMES = (
    "DEFAULT_MODEL_REL_ERROR",
    "DEFAULT_OBS_SIGMA_PPM",
    "MAX_ABS_OBS_PPM",
    "MIN_CONCLUSIVE_PROBABILITY",
    "MIN_SIGNAL_TO_NOISE",
    "MIN_USABLE_WINDOWS",
    "NO_SOURCE_ID",
    "NO_SOURCE_PRIOR",
    "CandidateScore",
    "InversionInput",
    "InversionResult",
    "Reason",
    "invert",
)
MOVED_NAMES = (
    "DEFAULT_MODEL_REL_ERROR",
    "DEFAULT_OBS_SIGMA_PPM",
    "MAX_ABS_OBS_PPM",
    "NO_SOURCE_ID",
    "InversionInput",
)


def test_inversion_exports_exactly_the_earlier_public_names() -> None:
    """Every public name of the unsplit module is in ``__all__`` and nothing else is."""
    assert set(inversion.__all__) == set(PUBLIC_NAMES)
    assert all(hasattr(inversion, name) for name in PUBLIC_NAMES)


def test_moved_names_are_the_same_objects() -> None:
    """The names moved to ``inversion_input`` are the same objects when read from ``inversion``."""
    for name in MOVED_NAMES:
        assert getattr(inversion, name) is getattr(inversion_input, name)
