"""The replay file format: one JSON document per scenario for the static replay build.

The document is built by ``plumetrace.simulator.export`` and read by the frontend through the
generated TypeScript types. Every model rejects unknown fields and non-finite numbers, so a file
that loads is complete and consistent. The file holds the simulated station only: it contains no
inversion result and no AI output. ``ReplaySource.rate_kg_h`` is the simulation input (the
truth), never a measurement or an estimate. See ``docs/reference/REPLAY.md``.
"""

import base64
from collections.abc import Sequence
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

REPLAY_SCHEMA_VERSION: Final = 1
REPLAY_STEP_S: Final = 60.0
KEYFRAME_STEP_S: Final = 120.0
MAX_REPLAY_BYTES: Final = 5_000_000


class _Strict(BaseModel):
    """Base of the replay models: no unknown fields, no NaN or infinite numbers."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ReplaySensor(_Strict):
    """A methane sensor and where it stands.

    Attributes:
        id: Instrument tag, for example ``AT-101``; a key of ``ReplayScenario.series``.
        x_m: East position in m.
        y_m: North position in m.
        z_m: Height in m.
    """

    id: str
    x_m: float
    y_m: float
    z_m: float


class ReplayEvent(_Strict):
    """One detection event on one sensor (10-minute detection window).

    Attributes:
        sensor_id: Instrument tag.
        window_index: Index of the 10-minute window in which the alarm fired.
        window_start_s: Start of that window in scenario seconds.
        mean_ppm: Window mean in ppm.
        baseline_ppm: Rolling baseline in ppm.
        downwind_of_site: Whether the sensor lay downwind of the site centre.
    """

    sensor_id: str
    window_index: int
    window_start_s: float
    mean_ppm: float
    baseline_ppm: float
    downwind_of_site: bool


class ReplaySource(_Strict):
    """A true simulated emission, used only to draw the plume.

    This is the simulation input, not a measurement and not an estimate: the interface must not
    show it as a result.

    Attributes:
        anchor_id: Emission-point anchor, for example ``VS-250.tip``.
        rate_kg_h: Simulated methane rate in kg/h.
    """

    anchor_id: str
    rate_kg_h: float


class PlumeKeyframe(_Strict):
    """The ground concentration grid at one time, with the wind that shaped it.

    Attributes:
        t_s: Time in scenario seconds.
        wind_speed_m_s: 60 s mean wind speed in m/s.
        wind_from_deg: 60 s circular mean wind direction in degrees.
        stability: Pasquill class (A to F).
        sources: Sources active at ``t_s``.
        grid_b64: Base64 of ``encode_log_u8`` of the grid (``ny * nx`` bytes, row-major).
    """

    t_s: float
    wind_speed_m_s: float
    wind_from_deg: float
    stability: str
    sources: list[ReplaySource]
    grid_b64: str


class ReplayGrid(_Strict):
    """Geometry and encoding of every key-frame grid of the file.

    Attributes:
        x0_m: West edge in m.
        y0_m: South edge in m.
        dx_m: Cell width in m.
        dy_m: Cell height in m.
        nx: Cells in x.
        ny: Cells in y.
        encoding: Byte encoding of the grids (0.1 to 1000 ppm, logarithmic).
    """

    x0_m: float
    y0_m: float
    dx_m: float = Field(gt=0)
    dy_m: float = Field(gt=0)
    nx: int = Field(ge=1)
    ny: int = Field(ge=1)
    encoding: Literal["log_u8_0.1_1000ppm"]


class ReplayLogEntry(_Strict):
    """One line of the station log.

    Attributes:
        t_s: Time in scenario seconds.
        kind: Entry type (permit, gauging, maintenance, shift_note, calibration).
        tag: Equipment or instrument tag the entry is about, if any.
        text: Entry text.
    """

    t_s: float
    kind: str
    tag: str | None
    text: str


class ReplayScenario(_Strict):
    """A complete replayable scenario (simulated station).

    Every list is sampled every ``step_s`` seconds (60 s means; a missing mean is ``None``).
    ``series`` holds the methane sensors (ppm) and every non-methane instrument tag, each with its
    unit in ``units``. The weather is real public data (see ``attribution``); the station, the
    sensor readings and the instruments are synthetic. The file holds no inversion result.

    Attributes:
        schema_version: Format version, 1.
        scenario_id: For example ``s1_rod_packing``.
        title: Display title.
        sim_start_utc: UTC time of scenario second 0, ISO 8601 with ``Z``.
        duration_s: Scenario length in s.
        step_s: Sampling step in s.
        sensors: The methane sensors.
        series: Tag to samples; ``None`` marks a missing sample.
        units: Tag to unit.
        wind_speed_m_s: 60 s mean wind speed in m/s.
        wind_from_deg: 60 s circular mean wind direction in degrees.
        stability: Most frequent Pasquill class in each 60 s sample.
        events: Detection events.
        log: Station log.
        grid: Grid geometry shared by all key frames.
        keyframes: Plume key frames, in time order.
        attribution: Data-source attribution and the real-versus-synthetic label.
        simulated: Always true: the station is fictional and simulated.
    """

    schema_version: Literal[1]
    scenario_id: str
    title: str
    sim_start_utc: str
    duration_s: float
    step_s: float
    sensors: list[ReplaySensor]
    series: dict[str, list[float | None]]
    units: dict[str, str]
    wind_speed_m_s: list[float]
    wind_from_deg: list[float]
    stability: list[str]
    events: list[ReplayEvent]
    log: list[ReplayLogEntry]
    grid: ReplayGrid
    keyframes: list[PlumeKeyframe]
    attribution: str
    simulated: Literal[True]

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Check the sampling, the lists, the units, the key frames and the attribution.

        Raises:
            ValueError: If any of them is inconsistent; the message says which.
        """
        self._check_samples()
        self._check_keyframes()
        if not self.attribution.strip():
            raise ValueError("attribution must not be blank")
        return self

    def _check_samples(self) -> None:
        """Require ``step_s > 0``, equal list lengths and one unit per series."""
        if not self.step_s > 0.0:
            raise ValueError("step_s must be > 0")
        n = len(self.wind_speed_m_s)
        if n != int(self.duration_s // self.step_s):
            raise ValueError(f"{n} samples do not fit duration_s / step_s")
        lists: dict[str, Sequence[object]] = {
            "wind_from_deg": self.wind_from_deg,
            "stability": self.stability,
        }
        lists.update({f"series {tag}": values for tag, values in self.series.items()})
        for name, values in lists.items():
            if len(values) != n:
                raise ValueError(f"{name} has {len(values)} samples, expected {n}")
        if set(self.units) != set(self.series):
            raise ValueError("units and series must have the same tags")

    def _check_keyframes(self) -> None:
        """Require strictly increasing times and ``nx * ny`` bytes of valid base64 per grid."""
        cells = self.grid.nx * self.grid.ny
        times = [k.t_s for k in self.keyframes]
        if any(b <= a for a, b in zip(times, times[1:], strict=False)):
            raise ValueError("keyframe times must be strictly increasing")
        for frame in self.keyframes:
            size = len(base64.b64decode(frame.grid_b64, validate=True))
            if size != cells:
                raise ValueError(
                    f"keyframe at {frame.t_s} s has {size} grid bytes, expected {cells}"
                )


class ReplayIndexEntry(_Strict):
    """One scenario in ``index.json`` (same shape as the live API's ``ScenarioSummary``).

    Attributes:
        id: Scenario id, for example ``s1_rod_packing``; the file is ``<id>.json``.
        title: Display title.
        duration_h: Scenario length in hours.
        is_mvp: Whether the scenario is part of the MVP set.
    """

    id: str
    title: str
    duration_h: int
    is_mvp: bool


class ReplayIndex(_Strict):
    """The list of replay files the static build ships (``scenarios/index.json``).

    Attributes:
        schema_version: Format version, 1.
        scenarios: One entry per scenario, sorted by ``id``.
    """

    schema_version: Literal[1]
    scenarios: list[ReplayIndexEntry]
