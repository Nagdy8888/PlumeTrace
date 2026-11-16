"""Equipment builders by spec ``type`` (registry used by ``build_station.py``)."""

from collections.abc import Callable
from typing import Any

from scene_setup import BuildContext

from equipment import (
    building,
    compressor,
    filter_separator,
    fin_fan,
    flare_stack,
    fuel_gas_skid,
    knockout_drum,
    meter_run,
    pig_trap,
    scrubber,
    storage_tank,
    teg_contactor,
    teg_regenerator,
    vent_stack,
    vru,
)

BUILDERS: dict[str, Callable[[dict[str, Any], BuildContext], None]] = {
    "pig_trap": pig_trap.build,
    "filter_separator": filter_separator.build,
    "scrubber": scrubber.build,
    "recip_compressor": compressor.build,
    "fin_fan_cooler": fin_fan.build,
    "vent_stack": vent_stack.build,
    "teg_contactor": teg_contactor.build,
    "teg_regenerator": teg_regenerator.build,
    "fuel_gas_skid": fuel_gas_skid.build,
    "storage_tank": storage_tank.build,
    "vru": vru.build,
    "knockout_drum": knockout_drum.build,
    "flare_stack": flare_stack.build,
    "meter_run": meter_run.build,
    "building": building.build,
}
