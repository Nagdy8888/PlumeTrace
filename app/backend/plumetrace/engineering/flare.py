"""Flare methane slip: the methane that leaves a flare unburned.

Pure function in SI units (kg/h). A lit flare destroys a fraction of the methane sent to it; an
unlit flare (pilot out) destroys none.
"""

import math
from typing import Final

# source: 98 % destruction and removal efficiency, the default for a lit, well-operated flare in
# OGMP 2.0 guidance and EPA AP-42 §13.5; real efficiency varies with wind and flow (design §5.3)
DEFAULT_DESTRUCTION_EFFICIENCY: Final = 0.98


def _require_unit_interval(name: str, value: float) -> None:
    """Raise ValueError unless value is a number in [0, 1] (NaN and inf fail)."""
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def flare_ch4_slip_kg_h(
    flared_gas_kg_h: float,
    ch4_mass_fraction: float,
    pilot_lit: bool,
    destruction_efficiency: float = DEFAULT_DESTRUCTION_EFFICIENCY,
) -> float:
    """Return the methane emitted by a flare, in kg/h.

    Lit: ``(1 - DE) * flared * w``. Unlit: ``flared * w`` (the efficiency is not used, but is
    still validated).

    Args:
        flared_gas_kg_h: Gas mass flow sent to the flare in kg/h (finite, not negative).
        ch4_mass_fraction: Methane mass fraction ``w`` of that gas, in [0, 1].
        pilot_lit: True when the pilot flame is lit.
        destruction_efficiency: Destruction efficiency ``DE`` of a lit flare, in [0, 1].

    Returns:
        Emitted methane in kg/h (never above ``flared_gas_kg_h * ch4_mass_fraction``).

    Raises:
        ValueError: If the flow is negative or not finite, or a fraction is outside [0, 1]
            or NaN.
    """
    if not math.isfinite(flared_gas_kg_h) or flared_gas_kg_h < 0.0:
        raise ValueError(f"flared_gas_kg_h must be finite and >= 0, got {flared_gas_kg_h}")
    _require_unit_interval("ch4_mass_fraction", ch4_mass_fraction)
    _require_unit_interval("destruction_efficiency", destruction_efficiency)
    ch4_sent_kg_h = flared_gas_kg_h * ch4_mass_fraction
    return (1.0 - destruction_efficiency) * ch4_sent_kg_h if pilot_lit else ch4_sent_kg_h
