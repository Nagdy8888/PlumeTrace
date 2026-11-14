"""Tests for the instrument simulator."""

import numpy as np
import pytest

from plumetrace.simulator.instruments import (
    BASELINES,
    InstrumentEffect,
    packing_leak_effects,
    simulate_instruments,
)

T = np.arange(0.0, 7200.0, 10.0)


def test_baselines_and_noise() -> None:
    """Every instrument is produced at its baseline mean with its noise level."""
    out = simulate_instruments(T, [], np.random.default_rng(0))
    assert set(out) == set(BASELINES)
    for tag, b in BASELINES.items():
        assert float(out[tag].mean()) == pytest.approx(b.mean, abs=4 * b.noise_sd / np.sqrt(len(T)))
        assert float(out[tag].std()) == pytest.approx(b.noise_sd, rel=0.15)


def test_ramped_offset() -> None:
    """An offset ramps linearly over ramp_s and then holds."""
    eff = [InstrumentEffect("TT-202P", "offset", 6.0, start_s=1000.0, ramp_s=1000.0)]
    clean = simulate_instruments(T, [], np.random.default_rng(1))["TT-202P"]
    out = simulate_instruments(T, eff, np.random.default_rng(1))["TT-202P"]
    delta = out - clean
    assert delta[T < 1000.0].max() == 0.0
    assert delta[T == 1500.0][0] == pytest.approx(3.0)
    assert np.allclose(delta[T >= 2000.0], 6.0)


def test_set_effect_replaces_value_inside_window() -> None:
    """A 'set' effect replaces the mean (pilot out -> ambient) only inside its window."""
    eff = [InstrumentEffect("TE-601", "set", 30.0, start_s=3600.0, end_s=5400.0)]
    out = simulate_instruments(T, eff, np.random.default_rng(2))["TE-601"]
    assert float(out[(T >= 3600.0) & (T < 5400.0)].mean()) == pytest.approx(30.0, abs=2.0)
    assert float(out[T < 3600.0].mean()) == pytest.approx(600.0, abs=2.0)


def test_packing_leak_effects() -> None:
    """15 kg/h CH4 at w = 0.8623 -> FT-250 +17.395 kg/h whole gas; TT-202P +6 C."""
    effs = packing_leak_effects("K-202", 15.0, 0.8623, start_s=7200.0)
    by_tag = {e.tag: e for e in effs}
    assert set(by_tag) == {"FT-250", "TT-202P"}
    assert by_tag["FT-250"].value == pytest.approx(17.395, abs=1e-3)
    assert by_tag["TT-202P"].value == 6.0 and by_tag["TT-202P"].ramp_s == 1800.0


def test_unknown_tag_rejected() -> None:
    """Effects must target a known instrument."""
    with pytest.raises(KeyError, match="XX-1"):
        simulate_instruments(
            T, [InstrumentEffect("XX-1", "offset", 1.0, 0.0)], np.random.default_rng(0)
        )
