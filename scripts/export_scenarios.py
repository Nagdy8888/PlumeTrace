"""Export every registered scenario as a replay file for the static replay build.

For each scenario the script runs the simulation against the committed weather snapshot, builds
the replay document and writes ``app/replay/scenarios/<id>.json`` (UTF-8, LF, sorted keys, at most
5 MB; a larger file is an error and nothing is written for it). It prints ``<id>: <n> bytes``.
It then writes ``app/replay/scenarios/index.json`` (the list of the scenarios above, sorted by
id) and prints ``index.json: <n> bytes``.
No network is used and the output is deterministic.

Run it from the repo root::

    cd app && uv run python ../scripts/export_scenarios.py

The outputs are generated - never edit them by hand.
"""

from pathlib import Path
from typing import Final

from plumetrace.facility.loader import load_facility
from plumetrace.facility.spec import FacilitySpec
from plumetrace.simulator.export import build_index, build_replay, index_bytes, replay_bytes
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import SCENARIOS
from plumetrace.simulator.weather import WeatherSnapshot, load_snapshot

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
OUT_DIR: Final[Path] = REPO_ROOT / "app/replay/scenarios"


def export_scenario(
    scenario_id: str, out_dir: Path, spec: FacilitySpec, snapshot: WeatherSnapshot
) -> int:
    """Run one registered scenario and write its replay file.

    Bytes are written, so Windows never converts LF line endings to CRLF.

    Args:
        scenario_id: A key of ``SCENARIOS``.
        out_dir: Target folder; created if missing.
        spec: The facility spec.
        snapshot: The weather snapshot.

    Returns:
        The size of the file in bytes.

    Raises:
        KeyError: If the id is not registered.
        ValueError: If the replay is over the size budget (no file is written).
    """
    run = run_scenario(SCENARIOS[scenario_id], spec, snapshot)
    data = replay_bytes(build_replay(run, spec, snapshot.attribution))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{scenario_id}.json").write_bytes(data)
    return len(data)


def main() -> int:
    """Export every registered scenario, then the index, and print one size line each.

    Returns:
        Exit code 0.
    """
    spec = load_facility()
    snapshot = load_snapshot()
    for scenario_id in SCENARIOS:
        size = export_scenario(scenario_id, OUT_DIR, spec, snapshot)
        print(f"{scenario_id}: {size} bytes")
    index = index_bytes(build_index(SCENARIOS.values()))
    (OUT_DIR / "index.json").write_bytes(index)
    print(f"index.json: {len(index)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
