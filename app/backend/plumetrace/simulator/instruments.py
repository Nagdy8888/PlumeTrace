"""Non-methane instruments of KS-07: baselines, noise and scripted effects.

Pure simulation: no network, no database, deterministic for a seed through the ``numpy``
generator the caller passes. The values in ``BASELINES`` and the packing-leak signature are
Task 3 values (design section 4), not taken from a published source.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class InstrumentBaseline:
    """Normal operating level of one instrument.

    Attributes:
        tag: Instrument tag, as in ``ks07.yaml``.
        unit: Unit of the reading.
        mean: Baseline value in ``unit``.
        noise_sd: Standard deviation of the Gaussian reading noise, in ``unit``.
    """

    tag: str
    unit: str
    mean: float
    noise_sd: float


BASELINES: Final[Mapping[str, InstrumentBaseline]] = MappingProxyType(
    {
        "FT-250": InstrumentBaseline("FT-250", "kg/h", 0.9, 0.25),  # packing vent header, whole gas
        "TT-201P": InstrumentBaseline("TT-201P", "degC", 80.0, 0.5),
        "TT-202P": InstrumentBaseline("TT-202P", "degC", 80.0, 0.5),
        "TT-203P": InstrumentBaseline("TT-203P", "degC", 80.0, 0.5),
        "FT-601": InstrumentBaseline("FT-601", "kg/h", 5.0, 0.5),  # flare header flow, whole gas
        "TE-601": InstrumentBaseline("TE-601", "degC", 600.0, 10.0),  # pilot thermocouple
        "PT-401": InstrumentBaseline("PT-401", "kPag", 2.0, 0.05),
        "PT-402": InstrumentBaseline("PT-402", "kPag", 2.0, 0.05),
        "FT-701": InstrumentBaseline("FT-701", "Sm3/h", 41667.0, 200.0),
    }
)

# Task 3 value: packing-case temperature rise that comes with a packing leak.
_PACKING_TEMP_RISE_C: Final[float] = 6.0


@dataclass(frozen=True)
class InstrumentEffect:
    """A scripted change to one instrument.

    Attributes:
        tag: Instrument tag; must be a key of ``BASELINES``.
        kind: ``"offset"`` adds ``value``; ``"set"`` replaces the level with ``value``
            (noise is still added).
        value: Offset or target level, in the instrument's unit.
        start_s: Start time in scenario seconds.
        end_s: End time (exclusive); infinite by default.
        ramp_s: Linear ramp from 0 to full effect over ``ramp_s`` after ``start_s``.
    """

    tag: str
    kind: Literal[
        "offset", "set"
    ]  # offset: add `value`; set: replace with `value` (noise still added)
    value: float
    start_s: float
    end_s: float = float("inf")
    ramp_s: float = 0.0  # linear ramp from 0 to full effect over ramp_s after start_s


def _validate_effect(effect: InstrumentEffect) -> None:
    """Raise if the effect names an unknown tag or has an unusable number."""
    if effect.tag not in BASELINES:
        raise KeyError(f"unknown instrument {effect.tag}")
    if effect.kind not in ("offset", "set"):
        raise ValueError(f"effect on {effect.tag}: kind {effect.kind!r} is not offset or set")
    if not (np.isfinite(effect.value) and np.isfinite(effect.start_s)):
        raise ValueError(f"effect on {effect.tag}: value and start_s must be finite")
    if np.isnan(effect.end_s) or effect.end_s <= effect.start_s:
        raise ValueError(f"effect on {effect.tag}: end_s must be after start_s")
    if not (np.isfinite(effect.ramp_s) and effect.ramp_s >= 0.0):
        raise ValueError(f"effect on {effect.tag}: ramp_s must be finite and >= 0")


def _weight(times_s: npt.NDArray[np.float64], effect: InstrumentEffect) -> npt.NDArray[np.float64]:
    """Return the effect weight per time: 0 outside the window, ramping to 1 inside."""
    inside = (times_s >= effect.start_s) & (times_s < effect.end_s)
    if effect.ramp_s == 0.0:
        return inside.astype(np.float64)
    ramp = np.minimum(1.0, (times_s - effect.start_s) / effect.ramp_s)
    return np.where(inside, ramp, 0.0)


def simulate_instruments(
    times_s: npt.NDArray[np.float64],
    effects: Sequence[InstrumentEffect],
    rng: np.random.Generator,
) -> dict[str, npt.NDArray[np.float64]]:
    """Simulate every instrument in ``BASELINES`` over ``times_s``.

    Noise is always drawn for every tag, in mapping order, so a run with effects stays
    aligned with a run without. Effects apply in the given order; noise is added last.

    Args:
        times_s: Scenario times in seconds; 1-D, non-empty, finite.
        effects: Scripted changes.
        rng: Seeded generator; the only source of randomness.

    Returns:
        Tag to series (same length as ``times_s``, all finite).

    Raises:
        KeyError: An effect names an unknown instrument.
        ValueError: ``times_s`` is empty, not 1-D or not finite, or an effect is malformed.
    """
    times = np.asarray(times_s, dtype=np.float64)
    if times.ndim != 1 or times.size == 0 or not np.isfinite(times).all():
        raise ValueError("times_s must be a non-empty 1-D array of finite values")
    for effect in effects:
        _validate_effect(effect)
    out: dict[str, npt.NDArray[np.float64]] = {}
    for tag, base in BASELINES.items():
        noise = rng.normal(0.0, base.noise_sd, times.size)
        value = np.full(times.size, base.mean, dtype=np.float64)
        for effect in (e for e in effects if e.tag == tag):
            w = _weight(times, effect)
            if effect.kind == "offset":
                value = value + w * effect.value
            else:
                value = (1.0 - w) * value + w * effect.value
        out[tag] = value + noise
    return out


def packing_leak_effects(
    unit_tag: str,
    ch4_rate_kg_h: float,
    ch4_mass_fraction: float,
    start_s: float,
    ramp_s: float = 1800.0,
) -> list[InstrumentEffect]:
    """Build the instrument signature of a rod-packing leak on one compressor.

    The vent header flow FT-250 reads whole gas, so it rises by the methane rate divided by
    the methane mass fraction; the packing case of the unit (``TT-20nP`` for ``K-20n``) runs
    hotter.

    Args:
        unit_tag: Compressor tag, ``K-201``, ``K-202`` or ``K-203``.
        ch4_rate_kg_h: Methane leak rate in kg/h; finite and positive.
        ch4_mass_fraction: Methane mass fraction of the gas, in (0, 1].
        start_s: Leak start in scenario seconds.
        ramp_s: Ramp length in seconds, finite and >= 0.

    Returns:
        Two ramped offset effects: FT-250 and the unit's packing temperature.

    Raises:
        ValueError: Unknown ``unit_tag`` or a number outside its range.
    """
    temp_tag = f"TT-{unit_tag[2:]}P" if unit_tag.startswith("K-") else ""
    if temp_tag not in BASELINES:
        raise ValueError(f"packing leak unit_tag {unit_tag!r} has no packing temperature")
    if not (np.isfinite(ch4_rate_kg_h) and ch4_rate_kg_h > 0.0):
        raise ValueError("packing leak ch4_rate_kg_h must be finite and positive")
    if not (np.isfinite(ch4_mass_fraction) and 0.0 < ch4_mass_fraction <= 1.0):
        raise ValueError("packing leak ch4_mass_fraction must be in (0, 1]")
    if not (np.isfinite(start_s) and np.isfinite(ramp_s) and ramp_s >= 0.0):
        raise ValueError("packing leak start_s must be finite and ramp_s finite and >= 0")
    return [
        InstrumentEffect(
            "FT-250", "offset", ch4_rate_kg_h / ch4_mass_fraction, start_s, ramp_s=ramp_s
        ),
        InstrumentEffect(temp_tag, "offset", _PACKING_TEMP_RISE_C, start_s, ramp_s=ramp_s),
    ]
