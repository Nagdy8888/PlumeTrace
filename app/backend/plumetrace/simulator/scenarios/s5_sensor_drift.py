"""S5: a slow upward drift on the north-fence sensor AT-106; no methane is released.

The station is simulated. ``WEATHER_OFFSET_H`` is the first passing offset printed by
``scripts/select_scenario_windows.py`` (never edit it by hand).
"""

from typing import Final

from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    FaultSpec,
    LogEntry,
    ScenarioDefinition,
)

S5_SEED: Final = 105
WEATHER_OFFSET_H: Final = 0

S5_SENSOR_DRIFT: Final = ScenarioDefinition(
    id="s5_sensor_drift",
    title="Sensor drift on AT-106",
    seed=S5_SEED,
    weather_offset_h=WEATHER_OFFSET_H,
    duration_h=6,
    faults=[FaultSpec(sensor_id="AT-106", drift_ppm_per_h=0.6, start_s=3600.0)],
    log=[
        LogEntry(
            t_s=300,
            kind="calibration",
            tag="AT-106",
            text="AT-106 last bump test 2025-03-02; next test overdue.",
        ),
        LogEntry(
            t_s=3000,
            kind="shift_note",
            text="No work permits open on the north fence today.",
        ),
    ],
    expected=ExpectedOutcome(triage="sensor_fault"),
)
