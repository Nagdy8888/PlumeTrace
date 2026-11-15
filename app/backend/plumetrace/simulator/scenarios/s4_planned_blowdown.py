"""S4: a planned blowdown of K-201 vented to VS-250, covered by permit PTW-0412.

The station is simulated. The vented methane mass comes from the engineering blowdown tool
(``plumetrace.engineering.blowdown.vented_mass``), never from a typed number. The source runs
for 15 minutes, so its rate is the mass divided by 0.25 h. ``WEATHER_OFFSET_H`` is the first
passing offset printed by ``scripts/select_scenario_windows.py`` (never edit it by hand).
"""

from typing import Final

from plumetrace.engineering.blowdown import vented_mass
from plumetrace.engineering.gas import GasComposition
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.scenario import ExpectedOutcome, LogEntry, ScenarioDefinition, SourceSpec

S4_SEED: Final = 104
WEATHER_OFFSET_H: Final = 0
BLOWDOWN_VOLUME_M3: Final = 8.0
S4_VENT_START_S: Final = 7200.0
S4_VENT_END_S: Final = 8100.0
_VENT_HOURS: Final = 0.25


def _vented_ch4_kg() -> float:
    """Return the CH4 mass in kg of the blowdown from suction pressure to ambient pressure."""
    spec = load_facility()
    temp_k = spec.operating.gas_temperature_k
    result = vented_mass(
        BLOWDOWN_VOLUME_M3,
        spec.operating.suction_pressure_pa,
        temp_k,
        spec.site.ambient_pressure_pa,
        temp_k,
        GasComposition(mole_fractions=spec.gas_composition),
    )
    return result.ch4_mass_kg


S4_VENTED_CH4_KG: Final = _vented_ch4_kg()

S4_PLANNED_BLOWDOWN: Final = ScenarioDefinition(
    id="s4_planned_blowdown",
    title="Planned blowdown of K-201 vented to VS-250",
    seed=S4_SEED,
    weather_offset_h=WEATHER_OFFSET_H,
    duration_h=4,
    sources=[
        SourceSpec(
            anchor_id="VS-250.tip",
            rate_kg_h=S4_VENTED_CH4_KG / _VENT_HOURS,
            start_s=S4_VENT_START_S,
            end_s=S4_VENT_END_S,
        )
    ],
    log=[
        LogEntry(
            t_s=6600,
            kind="permit",
            tag="K-201",
            text=(
                "PTW-0412: planned blowdown of K-201 for discharge valve maintenance, "
                "vented to VS-250; venting starts 10 minutes after this entry and lasts about "
                "15 minutes."
            ),
        ),
        LogEntry(
            t_s=9000,
            kind="maintenance",
            tag="K-201",
            text="K-201 discharge valve replaced; unit restarted.",
        ),
    ],
    expected=ExpectedOutcome(triage="planned_venting"),
)
