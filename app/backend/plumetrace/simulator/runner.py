"""Run a scenario: truth-physics sensors, instruments, window means and detection events.

Pure simulation: no network and no database. The weather snapshot is passed in, and the run is
deterministic for the seed of the definition (one ``numpy`` generator, drawn in a fixed order).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

import numpy as np
import numpy.typing as npt

from plumetrace.engineering.averaging import (
    WINDOW_S,
    window_means,
    window_mode_class,
    window_wind,
)
from plumetrace.engineering.detection import DetectionEvent, detect_events
from plumetrace.engineering.geometry import Sensor
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.truth_faults import SensorFault
from plumetrace.engineering.truth_model import TrueSource, TruthSeries, simulate_sensors
from plumetrace.engineering.truth_weather import HourlyWeather
from plumetrace.facility.candidates import emission_candidates, methane_sensors
from plumetrace.facility.obstacles import facility_obstacles
from plumetrace.facility.spec import FacilitySpec
from plumetrace.simulator.instruments import simulate_instruments
from plumetrace.simulator.scenario import ScenarioDefinition
from plumetrace.simulator.weather import WeatherSnapshot, slice_hours

DT_S: Final = 10.0


@dataclass(frozen=True)
class ScenarioRun:
    """Everything a scenario run produced.

    ``series.times_s`` and ``series.wind_from_deg`` are the 10 s wind series: callers that build
    an inversion input from the windows compute the within-window direction spread from them with
    ``plumetrace.engineering.averaging.window_direction_sd_deg(series.times_s,
    series.wind_from_deg)``, one value per window.

    Attributes:
        definition: The scenario that was run.
        sim_start_utc: UTC time of scenario second 0.
        sensors: The methane sensors, in column order of ``series.ppm``.
        series: The 10 s methane readings and wind of the truth model.
        instruments: Instrument tag to its 10 s series.
        window_start_s: Start of each complete 10-minute window in s.
        window_means_ppm: Window means in ppm, shape ``(W, S)``.
        window_wind_speed_m_s: Mean wind speed per window in m/s.
        window_wind_from_deg: Circular mean wind direction per window in degrees.
        window_stability: Most frequent stability class per window.
        events: Detection events, sorted by window and sensor.
    """

    definition: ScenarioDefinition
    sim_start_utc: datetime
    sensors: list[Sensor]
    series: TruthSeries
    instruments: dict[str, npt.NDArray[np.float64]]
    window_start_s: npt.NDArray[np.float64]
    window_means_ppm: npt.NDArray[np.float64]
    window_wind_speed_m_s: npt.NDArray[np.float64]
    window_wind_from_deg: npt.NDArray[np.float64]
    window_stability: list[StabilityClass]
    events: list[DetectionEvent]


def site_center_xy(spec: FacilitySpec) -> tuple[float, float]:
    """Return the centre of the site bounds as ``(x_m, y_m)``."""
    b = spec.site.bounds
    return ((b.x_min_m + b.x_max_m) / 2.0, (b.y_min_m + b.y_max_m) / 2.0)


def _true_sources(definition: ScenarioDefinition, spec: FacilitySpec) -> list[TrueSource]:
    """Turn the source specs into truth sources at their anchors.

    Raises:
        KeyError: If a source names an anchor that is not an emission point of the facility.
    """
    position = {c.id: c.position for c in emission_candidates(spec)}
    out: list[TrueSource] = []
    for s in definition.sources:
        if s.anchor_id not in position:
            raise KeyError(f"unknown anchor {s.anchor_id}")
        out.append(TrueSource(position[s.anchor_id], s.rate_kg_h, s.start_s, s.end_s))
    return out


def _require_weather(definition: ScenarioDefinition, snapshot: WeatherSnapshot) -> None:
    """Check the snapshot covers ``weather_offset_h + duration_h + 1`` hours.

    Raises:
        ValueError: If it does not; the message names the scenario and the hours needed.
    """
    need_h = definition.weather_offset_h + definition.duration_h + 1
    if len(snapshot.hours) < need_h:
        raise ValueError(
            f"scenario {definition.id} needs {need_h} weather hours "
            f"(offset {definition.weather_offset_h} + {definition.duration_h} h + 1), "
            f"snapshot has {len(snapshot.hours)}"
        )


def _simulate_series(
    definition: ScenarioDefinition,
    spec: FacilitySpec,
    sensors: list[Sensor],
    weather: list[HourlyWeather],
    rng: np.random.Generator,
) -> TruthSeries:
    """Run the truth model for the sources and faults of the definition."""
    faults = [SensorFault(f.sensor_id, f.drift_ppm_per_h, f.start_s) for f in definition.faults]
    return simulate_sensors(
        _true_sources(definition, spec),
        sensors,
        weather,
        DT_S,
        definition.duration_h * 3600.0,
        rng,
        spec.site.ambient_pressure_pa,
        obstacles=facility_obstacles(spec),
        faults=faults,
    )


def run_scenario(
    definition: ScenarioDefinition, spec: FacilitySpec, snapshot: WeatherSnapshot
) -> ScenarioRun:
    """Simulate one scenario against the weather snapshot.

    The generator is seeded with ``definition.seed``. It draws first for the methane sensors
    (inside ``simulate_sensors``), then for the instruments, so the instrument series do not
    depend on the sources. Detection runs on the absolute 10-minute window means.

    Args:
        definition: The scenario.
        spec: The facility spec.
        snapshot: The weather snapshot; the scenario uses ``duration_h + 1`` hours from
            ``weather_offset_h``.

    Returns:
        The run.

    Raises:
        KeyError: If a source names an unknown anchor.
        ValueError: If the snapshot is too short (the message names the scenario and the hours
            needed) or a fault names an unknown sensor.
    """
    _require_weather(definition, snapshot)
    rng = np.random.default_rng(definition.seed)
    weather = slice_hours(snapshot, definition.weather_offset_h, definition.duration_h + 1)
    sensors = methane_sensors(spec)
    series = _simulate_series(definition, spec, sensors, weather, rng)
    instruments = simulate_instruments(
        series.times_s, [e.to_effect() for e in definition.instrument_effects], rng
    )
    starts, means = window_means(series.times_s, series.ppm)
    speed, direction = window_wind(series.times_s, series.wind_speed_m_s, series.wind_from_deg)
    stability = window_mode_class(series.stability, int(WINDOW_S / DT_S), len(starts))
    events = detect_events(starts, means, sensors, site_center_xy(spec), direction)
    return ScenarioRun(
        definition,
        snapshot.start_utc + timedelta(hours=definition.weather_offset_h),
        sensors,
        series,
        instruments,
        starts,
        means,
        speed,
        direction,
        stability,
        events,
    )
