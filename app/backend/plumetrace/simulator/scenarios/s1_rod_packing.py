"""S1: a rod-packing leak on K-202, routed through the common vent header to VS-250.

The station is simulated. The leak starts 2 h into a 6 h scenario; the instrument signature
(vent header flow FT-250 and the K-202 packing temperature) is built by
``plumetrace.simulator.instruments.packing_leak_effects``. ``WEATHER_OFFSET_H`` is the first
passing offset printed by ``scripts/select_scenario_windows.py`` (never edit it by hand).
"""

from typing import Final

from plumetrace.engineering.gas import GasComposition, ch4_mass_fraction
from plumetrace.facility.loader import load_facility
from plumetrace.simulator.instruments import packing_leak_effects
from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    InstrumentEffectSpec,
    LogEntry,
    ScenarioDefinition,
    SourceSpec,
)

S1_SEED: Final = 101
WEATHER_OFFSET_H: Final = 0
S1_LEAK_RATE_KG_H: Final = 15.0
S1_LEAK_START_S: Final = 7200.0

KS07_COMPOSITION: Final = GasComposition(mole_fractions=load_facility().gas_composition)

_EFFECTS: Final = [
    InstrumentEffectSpec(
        tag=e.tag, kind=e.kind, value=e.value, start_s=e.start_s, end_s=e.end_s, ramp_s=e.ramp_s
    )
    for e in packing_leak_effects(
        "K-202", S1_LEAK_RATE_KG_H, ch4_mass_fraction(KS07_COMPOSITION), start_s=S1_LEAK_START_S
    )
]

S1_ROD_PACKING: Final = ScenarioDefinition(
    id="s1_rod_packing",
    title="K-202 rod-packing leak via vent stack VS-250",
    seed=S1_SEED,
    weather_offset_h=WEATHER_OFFSET_H,
    duration_h=6,
    sources=[
        SourceSpec(anchor_id="VS-250.tip", rate_kg_h=S1_LEAK_RATE_KG_H, start_s=S1_LEAK_START_S)
    ],
    instrument_effects=_EFFECTS,
    log=[
        LogEntry(
            t_s=600,
            kind="shift_note",
            text="Day shift handover: K-201, K-202 and K-203 running; VRU-410 online.",
        ),
        LogEntry(
            t_s=4000,
            kind="gauging",
            tag="TK-402",
            text="TK-402 gauged by the operator; thief hatch closed and latched after gauging.",
        ),
        LogEntry(
            t_s=5000,
            kind="maintenance",
            tag="AT-103",
            text="Instrument technician completed a routine check of AT-103.",
        ),
    ],
    expected=ExpectedOutcome(
        triage="leak",
        top_candidate="VS-250.tip",
        attributed_unit="K-202",
        rate_min_kg_h=7.5,
        rate_max_kg_h=30.0,
    ),
)
