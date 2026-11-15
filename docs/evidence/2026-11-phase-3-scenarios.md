# Phase 3 scenarios

Date: 2026-11-15. Evidence label: **local / synthetic + public-data (weather)**: the station is fictional and simulated;
sensor, instrument and scenario data are synthetic. Only the weather snapshot is real
(Open-Meteo, attributed in the replay files). Python 3.12.11, run from `app/` on the committed
tree of Phase 3 Tasks 1 to 7 plus Task 8.

## What the numbers are

For each MVP scenario: the selected weather offset (`weather_offset_h`, hours into the weather
snapshot) and the UTC time that scenario second 0 maps to, the CUSUM detection events (sensor,
10-minute window, window mean, baseline), and the size of the replay file in `app/replay/scenarios/`.
For S1 the table also holds the inversion result on the event windows: windows 12 up to and
including the first event window plus 3 (the S1 criterion of
`plumetrace.simulator.selection`), background from the windows before window 12, and the
within-window wind direction spread passed to the meander-aware inversion.

## Scenarios

| Scenario | Offset (h) | Sim start (UTC) | Duration | Detection events | Replay file |
|---|---|---|---|---|---|
| `s1_rod_packing` | 0 | 2025-07-14 00:00 | 6 h | 3 (AT-101 w13, AT-102 w17, AT-101 w28) | 445,852 bytes |
| `s4_planned_blowdown` | 0 | 2025-07-14 00:00 | 4 h | 2 (AT-101 w12, AT-102 w12) | 294,773 bytes |
| `s5_sensor_drift` | 0 | 2025-07-14 00:00 | 6 h | 2 (both AT-106: w13, w24) | 440,244 bytes |

All three selection criteria (Task 5) pass at the first candidate offset, 0 h.

## S1 inversion on the event windows (model estimate)

| Item | Value |
|---|---|
| Windows used | 5 (windows 12 to 16) |
| Most probable hypothesis | `VS-250.tip` |
| Model probability | 0.912 |
| Inconclusive | no |
| Rate at grid edge | no |
| Model estimate of the rate (2 significant figures) | 15–39 kg/h (median 24) |
| Simulated true rate (scenario file) | 15.0 kg/h |

The probability is the model's posterior for the hypothesis, not a measured certainty, and the
rate is a model estimate shown as an interval. The interval is suppressed when the result is
inconclusive, the top hypothesis is `NONE` or the median sits at the grid edge; none of those
applies here. The simulated true rate lies inside the interval.

The upper end of the interval (p95, 39 kg/h) is above the designed upper end of the expected range
(`rate_max_kg_h` = 30.0 kg/h in `s1_rod_packing.py`); the simulated true rate, 15.0 kg/h, is inside
the interval (15 to 39 kg/h).

Caveat (Gate 2): the meander-aware correction models the same wind-direction process that the truth
model puts into the simulated data, so this result is optimistic and partly self-consistent on a
simulated station. It is not evidence of real-world accuracy, and the probabilities are model
probabilities, not calibrated. The benchmark page for the "model estimate" and the "model
probability" of the inversion is [docs/benchmark-improvement.md](../benchmark-improvement.md).

## How the numbers were generated

Throwaway snippet (not committed), run from `app/` with `uv run python <snippet>`:

```python
"""Throwaway: numbers for docs/evidence/2026-11-phase-3-scenarios.md (not committed)."""

from pathlib import Path

from plumetrace.facility.loader import load_facility
from plumetrace.engineering.inversion import invert
from plumetrace.simulator.runner import run_scenario
from plumetrace.simulator.scenarios import get_scenario
from plumetrace.simulator.selection import (
    S1_FIRST_WINDOW,
    S1_LEAK_START_S,
    S1_AFTER_EVENT_WINDOWS,
    _s1_inversion_input,
    first_event_after,
)
from plumetrace.simulator.weather import load_snapshot

spec, snap = load_facility(), load_snapshot()
replay_dir = Path("replay/scenarios")  # run from app/
for sid in ("s1_rod_packing", "s4_planned_blowdown", "s5_sensor_drift"):
    d = get_scenario(sid)
    run = run_scenario(d, spec, snap)
    size = (replay_dir / f"{sid}.json").stat().st_size
    print(f"== {sid}: weather_offset_h={d.weather_offset_h} sim_start_utc={run.sim_start_utc.isoformat()} "
          f"duration_h={d.duration_h} replay_bytes={size}")
    print(f"   events={len(run.events)}")
    for e in run.events[:6]:
        print(f"   event sensor={e.sensor_id} window={e.window_index} start_s={e.window_start_s:.0f} "
              f"mean_ppm={e.mean_ppm:.3f} baseline_ppm={e.baseline_ppm:.3f}")
    if sid == "s1_rod_packing":
        ev = first_event_after(run, S1_LEAK_START_S)
        stop = ev.window_index + S1_AFTER_EVENT_WINDOWS + 1
        r = invert(_s1_inversion_input(run, spec, stop))
        print(f"   inversion windows [{S1_FIRST_WINDOW},{stop}) windows_used={r.windows_used}")
        print(f"   top_id={r.top_id} model_probability={r.top_probability:.3f} "
              f"inconclusive={r.inconclusive} reason={r.reason} at_grid_edge={r.rate_at_grid_edge}")
        shown = not (r.inconclusive or r.top_id == "NONE" or r.rate_at_grid_edge)
        if shown:
            print(f"   model estimate interval p05/p50/p95 kg/h = "
                  f"{r.rate_p05_kg_h:.2f}/{r.rate_kg_h:.2f}/{r.rate_p95_kg_h:.2f}")
        else:
            print("   rate interval suppressed")
        print("   truth rate_kg_h:", [s.rate_kg_h for s in d.sources])
```

Output (raw tool output, not for display; full-precision values):

```text
== s1_rod_packing: weather_offset_h=0 sim_start_utc=2025-07-14T00:00:00+00:00 duration_h=6 replay_bytes=445852
   events=3
   event sensor=AT-101 window=13 start_s=7800 mean_ppm=2.062 baseline_ppm=1.965
   event sensor=AT-102 window=17 start_s=10200 mean_ppm=2.493 baseline_ppm=2.001
   event sensor=AT-101 window=28 start_s=16800 mean_ppm=2.525 baseline_ppm=2.012
   inversion windows [12,17) windows_used=5
   top_id=VS-250.tip model_probability=0.912 inconclusive=False reason=None at_grid_edge=False
   model estimate interval p05/p50/p95 kg/h = 14.56/23.74/39.02
   truth rate_kg_h: [15.0]
== s4_planned_blowdown: weather_offset_h=0 sim_start_utc=2025-07-14T00:00:00+00:00 duration_h=4 replay_bytes=294773
   events=2
   event sensor=AT-101 window=12 start_s=7200 mean_ppm=5.654 baseline_ppm=1.958
   event sensor=AT-102 window=12 start_s=7200 mean_ppm=17.139 baseline_ppm=1.951
== s5_sensor_drift: weather_offset_h=0 sim_start_utc=2025-07-14T00:00:00+00:00 duration_h=6 replay_bytes=440244
   events=2
   event sensor=AT-106 window=13 start_s=7800 mean_ppm=2.690 baseline_ppm=2.043
   event sensor=AT-106 window=24 start_s=14400 mean_ppm=3.766 baseline_ppm=3.107
```
