"""Tests for the replay export (format, sampling, budget)."""

import base64
import json

from plumetrace.facility.loader import load_facility
from plumetrace.simulator.export import build_replay, replay_bytes
from plumetrace.simulator.replay_schema import MAX_REPLAY_BYTES
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()


def test_s1_replay_structure_and_budget() -> None:
    """S1 (6 h): 360 one-minute samples, 180 key frames, every tag present, under 5 MB."""
    replay = build_replay(
        run_scenario(get_scenario("s1_rod_packing"), SPEC, SNAP), SPEC, SNAP.attribution
    )
    assert replay.simulated is True and replay.schema_version == 1
    assert len(replay.wind_speed_m_s) == 360
    assert all(len(v) == 360 for v in replay.series.values())
    assert {"AT-101", "AT-108", "FT-250", "TT-202P"} <= set(replay.series)
    assert replay.units["AT-104"] == "ppm" and replay.units["FT-250"] == "kg/h"
    assert len(replay.keyframes) == 180
    assert len(base64.b64decode(replay.keyframes[0].grid_b64)) == 1200
    data = replay_bytes(replay)
    assert len(data) <= MAX_REPLAY_BYTES
    assert json.loads(data)["scenario_id"] == "s1_rod_packing"
    assert replay.sim_start_utc.endswith("Z")


def test_index_lists_registered_scenarios_sorted() -> None:
    """index.json lists the three MVP scenarios, sorted by id."""
    from plumetrace.simulator.export import build_index
    from plumetrace.simulator.scenarios import SCENARIOS

    index = build_index(SCENARIOS.values())
    assert index.schema_version == 1
    assert [e.id for e in index.scenarios] == [
        "s1_rod_packing",
        "s4_planned_blowdown",
        "s5_sensor_drift",
    ]
    assert [e.duration_h for e in index.scenarios] == [6, 4, 6]
