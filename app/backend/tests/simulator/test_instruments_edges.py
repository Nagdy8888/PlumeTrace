"""Edge cases of the instrument simulator: input validation, determinism, effect maths."""

from typing import Any

import numpy as np
import pytest

from plumetrace.simulator.instruments import (
    BASELINES,
    InstrumentEffect,
    packing_leak_effects,
    simulate_instruments,
)

T = np.arange(0.0, 3600.0, 10.0)
_BAD_KIND: Any = "multiply"


def _run(effects: list[InstrumentEffect], seed: int = 3) -> dict[str, Any]:
    return simulate_instruments(T, effects, np.random.default_rng(seed))


def test_same_seed_same_output_and_inputs_untouched() -> None:
    """Same seed gives identical arrays; the time axis is not modified."""
    t = T.copy()
    a = _run([])
    b = _run([])
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert np.array_equal(T, t)


def test_output_shape_dtype_and_order() -> None:
    """Every series has len(times) float64 finite values, keys in BASELINES order."""
    out = _run([])
    assert list(out) == list(BASELINES)
    for v in out.values():
        assert v.shape == T.shape and v.dtype == np.float64 and np.isfinite(v).all()


def test_effects_do_not_shift_other_tags_noise() -> None:
    """Noise is always drawn, so an effect on one tag leaves every other tag unchanged."""
    clean = _run([])
    out = _run([InstrumentEffect("FT-250", "offset", 5.0, 0.0)])
    for tag in BASELINES:
        if tag != "FT-250":
            assert np.array_equal(out[tag], clean[tag])


def test_effect_before_the_series_and_after_end_has_no_effect() -> None:
    """A window outside the time axis changes nothing; end_s is exclusive."""
    clean = _run([])
    far = _run([InstrumentEffect("PT-401", "offset", 9.0, 1e6, 2e6)])
    assert np.array_equal(far["PT-401"], clean["PT-401"])
    ended = _run([InstrumentEffect("PT-401", "offset", 9.0, 0.0, end_s=100.0)])
    delta = ended["PT-401"] - clean["PT-401"]
    assert np.allclose(delta[T < 100.0], 9.0) and np.allclose(delta[T >= 100.0], 0.0)


def test_set_with_ramp_blends_and_effects_apply_in_order() -> None:
    """A ramped set blends (1 - w)*value + w*target; a later offset adds on top."""
    eff = [
        InstrumentEffect("PT-402", "set", 10.0, 1000.0, ramp_s=1000.0),
        InstrumentEffect("PT-402", "offset", 1.0, 0.0),
    ]
    clean = _run([])["PT-402"]
    out = _run(eff)["PT-402"]
    i = int(np.flatnonzero(T == 1500.0)[0])
    noise = clean[i] - BASELINES["PT-402"].mean
    assert out[i] == pytest.approx(0.5 * BASELINES["PT-402"].mean + 0.5 * 10.0 + 1.0 + noise)
    j = int(np.flatnonzero(T == 2500.0)[0])
    assert out[j] == pytest.approx(10.0 + 1.0 + (clean[j] - BASELINES["PT-402"].mean))


@pytest.mark.parametrize("bad", [[], [[1.0, 2.0]], [0.0, float("nan")], [0.0, float("inf")]])
def test_bad_time_axis_rejected(bad: list[Any]) -> None:
    """Empty, 2-D or non-finite time axes raise ValueError."""
    with pytest.raises(ValueError, match="times_s"):
        simulate_instruments(np.array(bad, dtype=float), [], np.random.default_rng(0))


@pytest.mark.parametrize(
    "effect",
    [
        InstrumentEffect("FT-250", _BAD_KIND, 1.0, 0.0),
        InstrumentEffect("FT-250", "offset", float("nan"), 0.0),
        InstrumentEffect("FT-250", "offset", float("inf"), 0.0),
        InstrumentEffect("FT-250", "offset", 1.0, float("nan")),
        InstrumentEffect("FT-250", "offset", 1.0, 0.0, end_s=float("nan")),
        InstrumentEffect("FT-250", "offset", 1.0, 10.0, end_s=10.0),
        InstrumentEffect("FT-250", "offset", 1.0, 0.0, ramp_s=-1.0),
        InstrumentEffect("FT-250", "offset", 1.0, 0.0, ramp_s=float("nan")),
        InstrumentEffect("FT-250", "offset", 1.0, 0.0, ramp_s=float("inf")),
    ],
)
def test_bad_effect_rejected(effect: InstrumentEffect) -> None:
    """Malformed effects raise ValueError (never NaN output)."""
    with pytest.raises(ValueError, match="effect"):
        _run([effect])


def test_rng_untouched_when_validation_fails() -> None:
    """A rejected call draws nothing from the generator."""
    rng = np.random.default_rng(5)
    with pytest.raises(ValueError, match="effect"):
        simulate_instruments(T, [InstrumentEffect("FT-250", "offset", float("nan"), 0.0)], rng)
    assert rng.random() == np.random.default_rng(5).random()


@pytest.mark.parametrize("unit_tag", ["K-204", "K-20", "TT-202P", "", "K-2020"])
def test_packing_unit_tag_rejected(unit_tag: str) -> None:
    """Only K-201..K-203 map to a packing temperature instrument."""
    with pytest.raises(ValueError, match="unit_tag"):
        packing_leak_effects(unit_tag, 15.0, 0.86, start_s=0.0)


@pytest.mark.parametrize(
    ("rate", "frac", "start", "ramp"),
    [
        (0.0, 0.86, 0.0, 1800.0),
        (-1.0, 0.86, 0.0, 1800.0),
        (float("nan"), 0.86, 0.0, 1800.0),
        (15.0, 0.0, 0.0, 1800.0),
        (15.0, 1.5, 0.0, 1800.0),
        (15.0, float("nan"), 0.0, 1800.0),
        (15.0, 0.86, float("nan"), 1800.0),
        (15.0, 0.86, 0.0, -1.0),
    ],
)
def test_packing_leak_bad_numbers_rejected(
    rate: float, frac: float, start: float, ramp: float
) -> None:
    """Non-positive/non-finite rate, fraction outside (0, 1], bad start or ramp raise ValueError."""
    with pytest.raises(ValueError, match="packing leak"):
        packing_leak_effects("K-201", rate, frac, start_s=start, ramp_s=ramp)


def test_packing_leak_effects_run_through_the_simulator() -> None:
    """The helper's effects are accepted and raise the header flow and K-203 temperature."""
    effs = packing_leak_effects("K-203", 10.0, 0.8, start_s=600.0, ramp_s=0.0)
    clean = _run([])
    out = _run(effs)
    assert {e.tag for e in effs} == {"FT-250", "TT-203P"}
    after = T >= 600.0
    assert np.allclose((out["FT-250"] - clean["FT-250"])[after], 12.5)
    assert np.allclose((out["TT-203P"] - clean["TT-203P"])[after], 6.0)
