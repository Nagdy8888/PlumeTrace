"""Build the replay document of a scenario run and serialise it to bytes.

Pure: no network, no database, no file I/O (``scripts/export_scenarios.py`` writes the bytes).
The document holds 60 s means of the sensors, the instruments and the wind, the detection
events, the station log and plume key frames drawn with the truth physics. It holds no
inversion result. The format is in ``plumetrace.simulator.replay_schema``.
"""

import base64
import json
import math
from collections.abc import Iterable
from datetime import UTC
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.averaging import window_means, window_mode_class, window_wind
from plumetrace.engineering.plume_field import GridSpec, encode_log_u8, ground_grid_ppm
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_model import TrueSource, TruthConfig
from plumetrace.facility.spec import FacilitySpec
from plumetrace.simulator.instruments import BASELINES
from plumetrace.simulator.replay_schema import (
    KEYFRAME_STEP_S,
    MAX_REPLAY_BYTES,
    REPLAY_SCHEMA_VERSION,
    REPLAY_STEP_S,
    PlumeKeyframe,
    ReplayEvent,
    ReplayGrid,
    ReplayIndex,
    ReplayIndexEntry,
    ReplayLogEntry,
    ReplayScenario,
    ReplaySensor,
    ReplaySource,
)
from plumetrace.simulator.runner import DT_S, ScenarioRun, _true_sources
from plumetrace.simulator.scenario import ScenarioDefinition

# Task 7 wording: the real-versus-synthetic label every replay file carries (design section 10).
DATA_LABEL: Final = (
    "Station KS-07 is fictional and simulated; sensor, instrument and scenario data are "
    "synthetic. Only the weather is real."
)


def _per_minute(run: ScenarioRun, values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Return the 60 s means of a 10 s series (a minute with under half its samples is NaN)."""
    _, means = window_means(run.series.times_s, values.reshape(-1, 1), REPLAY_STEP_S)
    out: npt.NDArray[np.float64] = means[:, 0]
    return out


def _samples(values: npt.NDArray[np.float64]) -> list[float | None]:
    """Turn NaN into ``None`` (a missing sample); every other value is kept as it is."""
    return [None if math.isnan(v) else float(v) for v in values]


def _series_and_units(run: ScenarioRun) -> tuple[dict[str, list[float | None]], dict[str, str]]:
    """Return the 60 s series and the unit of every methane sensor and instrument tag."""
    _, means = window_means(run.series.times_s, run.series.ppm, REPLAY_STEP_S)
    series = {s.id: _samples(means[:, i]) for i, s in enumerate(run.sensors)}
    units = {s.id: "ppm" for s in run.sensors}
    for tag, values in run.instruments.items():
        series[tag] = _samples(_per_minute(run, values))
        units[tag] = BASELINES[tag].unit
    return series, units


def _minute_wind(
    run: ScenarioRun,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], list[StabilityClass]]:
    """Return the 60 s mean wind speed, circular mean direction and most frequent class."""
    speed, from_deg = window_wind(
        run.series.times_s, run.series.wind_speed_m_s, run.series.wind_from_deg, REPLAY_STEP_S
    )
    stability = window_mode_class(run.series.stability, round(REPLAY_STEP_S / DT_S), len(speed))
    return speed, from_deg, stability


def _sensors_and_events(run: ScenarioRun) -> tuple[list[ReplaySensor], list[ReplayEvent]]:
    """Copy the sensor positions and the detection events into replay models."""
    sensors = [
        ReplaySensor(id=s.id, x_m=s.position.x_m, y_m=s.position.y_m, z_m=s.position.z_m)
        for s in run.sensors
    ]
    events = [
        ReplayEvent(
            sensor_id=e.sensor_id,
            window_index=e.window_index,
            window_start_s=e.window_start_s,
            mean_ppm=e.mean_ppm,
            baseline_ppm=e.baseline_ppm,
            downwind_of_site=e.downwind_of_site,
        )
        for e in run.events
    ]
    return sensors, events


def _grid_model(grid: GridSpec) -> ReplayGrid:
    """Describe the key-frame grid and its byte encoding for the file."""
    return ReplayGrid(
        x0_m=grid.x0_m,
        y0_m=grid.y0_m,
        dx_m=grid.dx_m,
        dy_m=grid.dy_m,
        nx=grid.nx,
        ny=grid.ny,
        encoding="log_u8_0.1_1000ppm",
    )


def _keyframes(run: ScenarioRun, spec: FacilitySpec, grid: GridSpec) -> list[PlumeKeyframe]:
    """Draw a key frame every ``KEYFRAME_STEP_S`` with the truth coefficients and the 60 s wind."""
    speed, from_deg, stability = _minute_wind(run)
    temp_k = _per_minute(run, run.series.temp_k)
    truth = _true_sources(run.definition, spec)
    anchors = [s.anchor_id for s in run.definition.sources]
    frames: list[PlumeKeyframe] = []
    for k in range(0, len(speed), round(KEYFRAME_STEP_S / REPLAY_STEP_S)):
        t_s = k * REPLAY_STEP_S
        active = [(a, s) for a, s in zip(anchors, truth, strict=True) if _is_active(s, t_s)]
        ppm = ground_grid_ppm(
            [s for _, s in active],
            t_s,
            float(speed[k]),
            float(from_deg[k]),
            stability[k],
            TruthConfig().coeff,
            float(temp_k[k]),
            spec.site.ambient_pressure_pa,
            grid,
        )
        frames.append(
            PlumeKeyframe(
                t_s=t_s,
                wind_speed_m_s=float(speed[k]),
                wind_from_deg=float(from_deg[k]),
                stability=stability[k].value,
                sources=[ReplaySource(anchor_id=a, rate_kg_h=s.rate_kg_h) for a, s in active],
                grid_b64=base64.b64encode(encode_log_u8(ppm)).decode("ascii"),
            )
        )
    return frames


def _is_active(source: TrueSource, t_s: float) -> bool:
    """Say whether the source emits at ``t_s`` (``start_s <= t_s < end_s``)."""
    return source.start_s <= t_s < source.end_s


def build_replay(run: ScenarioRun, spec: FacilitySpec, attribution: str) -> ReplayScenario:
    """Build the replay document of a scenario run.

    Sensors, instruments and wind are 60 s means (``window_means`` and ``window_wind`` with a
    60 s window; a missing mean is ``None``). Key frames are drawn every 120 s from the truth
    coefficients (``TruthConfig().coeff``) and the 60 s wind at that time, with the scenario
    sources active at that time. The document holds no inversion result.

    Args:
        run: A scenario run.
        spec: The facility spec of the run.
        attribution: The weather snapshot attribution (the real data credit); the fixed
            real-versus-synthetic label ``DATA_LABEL`` is added after it.

    Returns:
        The validated replay document.

    Raises:
        pydantic.ValidationError: If a value is not finite (NaN is a missing sample, anything
            else non-finite is refused) or the document is inconsistent.
    """
    grid = GridSpec()
    series, units = _series_and_units(run)
    speed, from_deg, stability = _minute_wind(run)
    sensors, events = _sensors_and_events(run)
    definition = run.definition
    return ReplayScenario(
        schema_version=REPLAY_SCHEMA_VERSION,
        scenario_id=definition.id,
        title=definition.title,
        sim_start_utc=run.sim_start_utc.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        duration_s=definition.duration_h * 3600.0,
        step_s=REPLAY_STEP_S,
        sensors=sensors,
        series=series,
        units=units,
        wind_speed_m_s=[float(v) for v in speed],
        wind_from_deg=[float(v) for v in from_deg],
        stability=[c.value for c in stability],
        events=events,
        log=[
            ReplayLogEntry(t_s=e.t_s, kind=e.kind, tag=e.tag, text=e.text) for e in definition.log
        ],
        grid=_grid_model(grid),
        keyframes=_keyframes(run, spec, grid),
        attribution=f"{attribution} {DATA_LABEL}",
        simulated=True,
    )


def replay_bytes(replay: ReplayScenario) -> bytes:
    """Serialise a replay document: compact JSON, sorted keys, UTF-8, one trailing LF.

    Args:
        replay: The document.

    Returns:
        The file bytes; the same document always gives the same bytes.

    Raises:
        ValueError: If the file is over ``MAX_REPLAY_BYTES``; the message is
            ``"<scenario_id> replay is <n> bytes, budget <MAX_REPLAY_BYTES>"``.
    """
    text = json.dumps(
        replay.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    data = text.encode("utf-8") + b"\n"
    if len(data) > MAX_REPLAY_BYTES:
        raise ValueError(
            f"{replay.scenario_id} replay is {len(data)} bytes, budget {MAX_REPLAY_BYTES}"
        )
    return data


def build_index(definitions: Iterable[ScenarioDefinition]) -> ReplayIndex:
    """Build the replay index: one entry per scenario, sorted by id.

    Args:
        definitions: The scenario definitions to list (for example ``SCENARIOS.values()``).

    Returns:
        The index; every entry has ``is_mvp=True`` because every registered scenario is part of
        the MVP set in this phase.
    """
    entries = [
        ReplayIndexEntry(id=d.id, title=d.title, duration_h=d.duration_h, is_mvp=True)
        for d in sorted(definitions, key=lambda d: d.id)
    ]
    return ReplayIndex(schema_version=REPLAY_SCHEMA_VERSION, scenarios=entries)


def index_bytes(index: ReplayIndex) -> bytes:
    """Serialise the index the way ``replay_bytes`` serialises a scenario (no size check).

    Args:
        index: The index.

    Returns:
        Compact JSON with sorted keys, UTF-8, one trailing LF; the same index always gives the
        same bytes.
    """
    text = json.dumps(
        index.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return text.encode("utf-8") + b"\n"
