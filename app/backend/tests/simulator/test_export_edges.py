"""Edge-case tests of the replay export: content, determinism, NaN, budget, labels, keys."""

import base64
import dataclasses
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from plumetrace.config import REPO_ROOT
from plumetrace.engineering.plume_field import GridSpec, decode_log_u8
from plumetrace.facility.loader import load_facility
from plumetrace.simulator import export
from plumetrace.simulator.export import build_replay, replay_bytes
from plumetrace.simulator.replay_schema import MAX_REPLAY_BYTES, ReplayScenario
from plumetrace.simulator.runner import ScenarioRun, run_scenario
from plumetrace.simulator.scenarios import SCENARIOS, get_scenario
from plumetrace.simulator.weather import load_snapshot

SPEC = load_facility()
SNAP = load_snapshot()
FAKE_KEY = "sk-" + "Q7" * 12  # built at run time so this file never matches the scanner
REPLAY_DIR = REPO_ROOT / "app/replay/scenarios"


def _run(scenario_id: str) -> ScenarioRun:
    """Run one MVP scenario against the committed weather."""
    return run_scenario(get_scenario(scenario_id), SPEC, SNAP)


RUN = _run("s4_planned_blowdown")  # 4 h: 240 samples, 120 key frames, vent from 7200 s
REPLAY = build_replay(RUN, SPEC, SNAP.attribution)


def _scanner() -> ModuleType:
    """Import the security-checks secret_scan.py script as a module."""
    path = REPO_ROOT / ".claude/skills/security-checks/scripts/secret_scan.py"
    spec = importlib.util.spec_from_file_location("secret_scan", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_is_deterministic() -> None:
    """Building twice, and from a fresh run, gives identical bytes."""
    again = build_replay(_run("s4_planned_blowdown"), SPEC, SNAP.attribution)
    assert replay_bytes(REPLAY) == replay_bytes(REPLAY) == replay_bytes(again)


def test_bytes_are_compact_sorted_utf8_lf() -> None:
    """Compact separators, sorted keys at every level, one trailing LF, no CR, no NaN token."""
    data = replay_bytes(REPLAY)
    assert data.endswith(b"}\n") and data.count(b"\n") == 1 and b"\r" not in data
    assert b"NaN" not in data and b"Infinity" not in data and b'": ' not in data

    def check_sorted(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _ in pairs]
        assert keys == sorted(keys)
        return dict(pairs)

    json.loads(data.decode("utf-8"), object_pairs_hook=check_sorted)


def test_over_budget_raises_with_the_documented_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """A file over the budget is refused with the scenario id, size and budget."""
    monkeypatch.setattr(export, "MAX_REPLAY_BYTES", 1000)
    size = (
        len(
            json.dumps(
                REPLAY.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        )
        + 1
    )
    with pytest.raises(
        ValueError, match=f"s4_planned_blowdown replay is {size} bytes, budget 1000"
    ):
        replay_bytes(REPLAY)


def test_sampling_is_the_60_s_mean() -> None:
    """Sample k of a sensor and of an instrument is the mean of the six 10 s samples of minute k."""
    ppm = RUN.series.ppm
    assert REPLAY.series["AT-101"][3] == pytest.approx(float(ppm[18:24, 0].mean()), rel=1e-12)
    ft = RUN.instruments["FT-250"]
    assert REPLAY.series["FT-250"][5] == pytest.approx(float(ft[30:36].mean()), rel=1e-12)
    assert REPLAY.wind_speed_m_s[7] == pytest.approx(
        float(RUN.series.wind_speed_m_s[42:48].mean()), rel=1e-12
    )
    assert (
        set(REPLAY.units)
        == set(REPLAY.series)
        == {s.id for s in RUN.sensors} | set(RUN.instruments)
    )
    assert [s.id for s in REPLAY.sensors] == [s.id for s in RUN.sensors]
    assert all(c in "ABCDEF" and len(c) == 1 for c in REPLAY.stability)


def test_missing_window_becomes_none_not_nan() -> None:
    """A minute with no valid samples is stored as None; the file stays valid JSON."""
    ft = RUN.instruments["FT-250"].copy()
    ft[60:66] = np.nan
    run = dataclasses.replace(RUN, instruments={**RUN.instruments, "FT-250": ft})
    replay = build_replay(run, SPEC, SNAP.attribution)
    assert replay.series["FT-250"][10] is None and replay.series["FT-250"][9] is not None
    assert json.loads(replay_bytes(replay))["series"]["FT-250"][10] is None


def test_infinite_reading_is_refused() -> None:
    """Only NaN means missing: an infinite reading fails validation instead of being hidden."""
    ft = RUN.instruments["FT-250"].copy()
    ft[0:6] = np.inf
    run = dataclasses.replace(RUN, instruments={**RUN.instruments, "FT-250": ft})
    with pytest.raises(ValidationError):
        build_replay(run, SPEC, SNAP.attribution)


def test_keyframes_follow_the_sources_and_the_wind() -> None:
    """One key frame per 120 s; empty before the vent opens (7200 s); wind from the 60 s series."""
    frames = REPLAY.keyframes
    assert [f.t_s for f in frames] == [120.0 * k for k in range(120)]
    cells = REPLAY.grid.nx * REPLAY.grid.ny
    assert (REPLAY.grid.nx, REPLAY.grid.ny) == (GridSpec().nx, GridSpec().ny)
    specs = get_scenario("s4_planned_blowdown").sources
    seen_active = False
    for k, frame in enumerate(frames):
        grid = decode_log_u8(base64.b64decode(frame.grid_b64), REPLAY.grid.ny, REPLAY.grid.nx)
        assert grid.size == cells
        assert frame.wind_speed_m_s == REPLAY.wind_speed_m_s[2 * k]
        assert frame.wind_from_deg == REPLAY.wind_from_deg[2 * k]
        assert frame.stability == REPLAY.stability[2 * k]
        active = [s.anchor_id for s in specs if s.start_s <= frame.t_s < s.end_s]
        assert [s.anchor_id for s in frame.sources] == active
        assert (grid.max() > 0.0) == bool(active)
        seen_active = seen_active or bool(active)
    assert seen_active and frames[0].sources == [] and frames[-1].sources == []
    assert all(s.rate_kg_h > 0.0 for f in frames for s in f.sources)


def test_events_log_and_start_time_are_copied() -> None:
    """Events, log lines and the UTC start of the run appear unchanged in the file."""
    assert [(e.sensor_id, e.window_index, e.window_start_s) for e in REPLAY.events] == [
        (e.sensor_id, e.window_index, e.window_start_s) for e in RUN.events
    ]
    assert len(REPLAY.events) >= 1
    assert [(e.t_s, e.kind, e.tag, e.text) for e in REPLAY.log] == [
        (e.t_s, e.kind, e.tag, e.text) for e in RUN.definition.log
    ]
    assert REPLAY.sim_start_utc == "2025-07-14T00:00:00Z"
    assert REPLAY.scenario_id == "s4_planned_blowdown" and REPLAY.title == RUN.definition.title


def test_labels_real_weather_and_synthetic_data() -> None:
    """The file says it is simulated, credits Open-Meteo and says the station data is synthetic."""
    assert REPLAY.simulated is True
    assert REPLAY.attribution.startswith(SNAP.attribution)
    assert "Open-Meteo" in REPLAY.attribution
    assert "synthetic" in REPLAY.attribution and "simulated" in REPLAY.attribution


def test_file_holds_no_inversion_result() -> None:
    """The format has no inversion output, so no rate can be shown as a point estimate."""
    assert not any("invers" in key or "p05" in key for key in ReplayScenario.model_fields)
    assert not any("rate" in key for key in ReplayScenario.model_fields)


def test_scanner_accepts_the_bytes_and_catches_a_planted_key(tmp_path: Path) -> None:
    """secret_scan finds nothing in the replay bytes and does flag a key added to them."""
    scanner = _scanner()
    clean = tmp_path / "clean.json"
    clean.write_bytes(replay_bytes(REPLAY))
    assert scanner.scan_file(clean, {}) == []
    planted = tmp_path / "planted.json"
    planted.write_bytes(
        replay_bytes(REPLAY).replace(b'"title"', f'"k":"{FAKE_KEY}","title"'.encode())
    )
    assert scanner.scan_file(planted, {}) != []


@pytest.mark.parametrize("scenario_id", sorted(SCENARIOS))
def test_committed_replay_files_are_valid_small_clean_and_reproducible(scenario_id: str) -> None:
    """Each generated file loads, fits the budget, has no key and equals a fresh export."""
    path = REPLAY_DIR / f"{scenario_id}.json"
    data = path.read_bytes()
    assert len(data) <= MAX_REPLAY_BYTES and b"\r" not in data
    assert ReplayScenario.model_validate_json(data).scenario_id == scenario_id
    assert _scanner().scan_file(path, {}) == []
    fresh = build_replay(_run(scenario_id), SPEC, SNAP.attribution)
    assert data == replay_bytes(fresh)
