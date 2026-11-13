"""Emission-factor inventory: a site total from component counts, and one OGI-found leaker.

Two jobs, two factor tables (see ``emission_factors``):

* ``bottom_up_ch4_kg_h``: the site's average component emissions, from component counts times the
  EPA-453/R-95-017 average gas factors (total organic compounds), converted to methane.
* ``leaker_ch4_kg_h``: one component found leaking by optical gas imaging (scenario S6), from the
  Subpart W Table W-4 leaker factors (total hydrocarbon), converted to methane.

Caveat: the component counts that feed ``bottom_up_ch4_kg_h`` come from the facility package
(``ComponentCounts``). For KS-07 they are Subpart W Table W-1B production and gathering-and-boosting
defaults used as an UNVERIFIED PROXY for a transmission compressor station (Gate 1 owner decision,
see ``docs/OWNER_ACTIONS.md``). The inventory number is therefore an order-of-magnitude estimate,
not a measurement.
"""

import math
from collections.abc import Mapping
from typing import Literal, TypedDict

from plumetrace.engineering.constants import (
    FT3_TO_M3,
    HYDROCARBONS,
    M_CH4_KG_MOL,
    P_STD_PA,
    R_J_MOL_K,
    T_STD_K,
)
from plumetrace.engineering.emission_factors import (
    EPA_1995_AVERAGE_GAS_TOC_KG_H,
    SUBPART_W_W4_LEAKER_THC_SCF_H,
)
from plumetrace.engineering.gas import (
    GasComposition,
    ch4_hydrocarbon_mass_fraction,
    ch4_hydrocarbon_mole_fraction,
)


class ComponentCountsDict(TypedDict):
    """Component counts of one equipment item (``ComponentCounts.model_dump()``).

    Attributes:
        valves: Number of valves.
        connectors: Number of connectors.
        open_ended_lines: Number of open-ended lines.
        pressure_relief_valves: Number of pressure relief valves.
    """

    valves: int
    connectors: int
    open_ended_lines: int
    pressure_relief_valves: int


LeakerComponent = Literal[
    "valve", "connector", "open_ended_line", "pressure_relief_valve", "meter", "other"
]
LeakerLocation = Literal["compressor", "non_compressor"]

# factor key in EPA_1995_AVERAGE_GAS_TOC_KG_H per count field; pressure relief valves use the
# "others" factor (table footnote c)
_FACTOR_KEY: dict[str, str] = {
    "valves": "valves",
    "connectors": "connectors",
    "open_ended_lines": "open_ended_lines",
    "pressure_relief_valves": "others",
}


def _require_hydrocarbons(comp: GasComposition) -> None:
    """Raise ValueError if the gas has no hydrocarbon to convert a TOC or THC factor with."""
    if sum(x for k, x in comp.mole_fractions.items() if k in HYDROCARBONS) <= 0.0:
        raise ValueError("gas composition has no hydrocarbon; cannot convert TOC or THC to CH4")


def _toc_kg_h(tag: str, counts: ComponentCountsDict) -> float:
    """Return the total organic compound rate of one equipment item in kg/h.

    Raises:
        ValueError: If a count is missing, not an integer or negative, or the sum overflows.
    """
    values: Mapping[str, object] = counts
    total_kg_h = 0.0
    for field, factor_key in _FACTOR_KEY.items():
        if field not in values:
            raise ValueError(f"{tag}: missing count '{field}'")
        count = values[field]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{tag}: {field} must be a non-negative integer, got {count!r}")
        try:
            total_kg_h += count * EPA_1995_AVERAGE_GAS_TOC_KG_H[factor_key]
        except OverflowError:
            raise ValueError(f"{tag}: {field} is too large for a finite rate") from None
    if not math.isfinite(total_kg_h):
        raise ValueError(f"{tag}: the total organic compound rate is not finite")
    return total_kg_h


def bottom_up_ch4_kg_h(counts: Mapping[str, ComponentCountsDict], comp: GasComposition) -> float:
    """Return the site's average component methane emission in kg/h.

    ``sum over tags of (valves*f[valves] + connectors*f[connectors] + open_ended_lines*
    f[open_ended_lines] + pressure_relief_valves*f[others]) * w`` with ``f`` the EPA-453/R-95-017
    Table 2-4 gas-service average factors (kg TOC/h/source) and ``w`` the methane share of the
    hydrocarbon mass. Converting total organic compounds to methane by that share is an
    approximation. Pressure relief valves use the "others" factor per the table footnote.

    The counts are the Subpart W Table W-1B production defaults used as an UNVERIFIED PROXY for a
    transmission compressor station, so the result is an order-of-magnitude figure.

    Args:
        counts: Component counts per equipment tag (``ComponentCounts.model_dump()``). An empty
            mapping gives 0.
        comp: Gas composition (needs at least one hydrocarbon).

    Returns:
        Methane in kg/h (finite, not negative).

    Raises:
        ValueError: If the gas has no hydrocarbon, a count is missing, negative or not an
            integer, or the result is not finite.
    """
    _require_hydrocarbons(comp)
    toc_kg_h = sum(_toc_kg_h(tag, c) for tag, c in counts.items())
    ch4_kg_h = toc_kg_h * ch4_hydrocarbon_mass_fraction(comp)
    if not math.isfinite(ch4_kg_h):
        raise ValueError("the inventory is not finite")
    return ch4_kg_h


def leaker_ch4_kg_h(
    component: LeakerComponent, location: LeakerLocation, comp: GasComposition
) -> float:
    """Return the methane rate of one leaking component found by optical gas imaging, in kg/h.

    ``scf_h * FT3_TO_M3 * (P_STD / (R * T_STD)) * x_CH4,hc * M_CH4`` with ``scf_h`` the Subpart W
    Table W-4 total hydrocarbon leaker factor, and ``x_CH4,hc`` the methane share of hydrocarbon
    moles. The 60 degF scf versus 15 degC Sm3 reference difference is ignored (about 0.2 %).

    Args:
        component: Leaking component type.
        location: ``"compressor"`` or ``"non_compressor"``.
        comp: Gas composition (needs at least one hydrocarbon).

    Returns:
        Methane in kg/h.

    Raises:
        ValueError: If the component or location is unknown or the gas has no hydrocarbon.
    """
    if location not in SUBPART_W_W4_LEAKER_THC_SCF_H:
        raise ValueError(f"unknown leaker location {location!r}")
    factors = SUBPART_W_W4_LEAKER_THC_SCF_H[location]
    if component not in factors:
        raise ValueError(f"unknown leaker component {component!r}")
    _require_hydrocarbons(comp)
    mol_per_m3 = P_STD_PA / (R_J_MOL_K * T_STD_K)
    thc_mol_h = factors[component] * FT3_TO_M3 * mol_per_m3
    return thc_mol_h * ch4_hydrocarbon_mole_fraction(comp) * M_CH4_KG_MOL
