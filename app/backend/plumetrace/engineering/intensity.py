"""Methane intensity: emitted methane as a percentage of the gas handled, on a volume basis."""

import math

from plumetrace.engineering.constants import P_STD_PA, T_STD_K
from plumetrace.engineering.units import ppm_to_kg_m3


def methane_intensity_percent(ch4_emitted_kg_h: float, throughput_sm3_h: float) -> float:
    """Return the methane intensity in percent.

    Volume basis, following the OGCI methane-intensity methodology (methane emitted volume divided
    by gas handled volume): the emitted methane mass is converted to a volume at standard
    conditions (15 degC, 101325 Pa, ideal gas; pure methane is 0.6785 kg/Sm3) and divided by the gas
    throughput in Sm3/h, times 100. The result is not capped: it can exceed 100 % for an emission
    larger than the gas handled.

    Args:
        ch4_emitted_kg_h: Methane emitted in kg/h (finite, not negative).
        throughput_sm3_h: Gas handled in Sm3/h (finite, above zero).

    Returns:
        Intensity in percent (finite).

    Raises:
        ValueError: If the throughput is not finite and above zero, the emission is negative or
            not finite, or the ratio overflows.
    """
    if not (math.isfinite(throughput_sm3_h) and throughput_sm3_h > 0.0):
        raise ValueError(f"throughput_sm3_h must be finite and > 0, got {throughput_sm3_h}")
    if not (math.isfinite(ch4_emitted_kg_h) and ch4_emitted_kg_h >= 0.0):
        raise ValueError(f"ch4_emitted_kg_h must be finite and >= 0, got {ch4_emitted_kg_h}")
    ch4_sm3_h = ch4_emitted_kg_h / float(ppm_to_kg_m3(1e6, T_STD_K, P_STD_PA))
    intensity_percent = ch4_sm3_h / throughput_sm3_h * 100.0
    if not math.isfinite(intensity_percent):
        raise ValueError("the intensity is not finite (ratio overflows)")
    return intensity_percent
