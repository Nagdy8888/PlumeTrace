"""Scenario definitions: sources, faults, instrument effects, log entries and the expected outcome.

Plain frozen Pydantic models, no I/O. Times are seconds from the scenario start (``t_s``); a
scenario starts ``weather_offset_h`` hours into the weather snapshot. The simulator runs a
definition with ``plumetrace.simulator.runner.run_scenario``.
"""

import math
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from plumetrace.simulator.instruments import BASELINES, InstrumentEffect


class _Frozen(BaseModel):
    """Base of the scenario models: immutable, no unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceSpec(_Frozen):
    """A true methane emission at an anchor, active from ``start_s`` to ``end_s`` (exclusive).

    Attributes:
        anchor_id: Id of an emission-point anchor of the facility, for example ``VS-250.tip``.
        rate_kg_h: Methane rate in kg/h (>= 0, finite).
        start_s: Start in scenario seconds (>= 0, finite).
        end_s: End in scenario seconds, after ``start_s``; infinite by default.
    """

    anchor_id: str
    rate_kg_h: float = Field(ge=0)
    start_s: float = Field(ge=0)
    end_s: float = float("inf")

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Reject an infinite rate or start, and an end that is not after the start."""
        if not (math.isfinite(self.rate_kg_h) and math.isfinite(self.start_s)):
            raise ValueError("source rate_kg_h and start_s must be finite")
        if not self.end_s > self.start_s:
            raise ValueError("source end_s must be after start_s")
        return self


class FaultSpec(_Frozen):
    """A linear drift on one methane sensor.

    Attributes:
        sensor_id: Tag of the faulty sensor, for example ``AT-106``.
        drift_ppm_per_h: Drift in ppm per hour (finite, may be negative).
        start_s: Start in scenario seconds (>= 0, finite).
    """

    sensor_id: str
    drift_ppm_per_h: float
    start_s: float = Field(ge=0)

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Reject a non-finite drift or start."""
        if not (math.isfinite(self.drift_ppm_per_h) and math.isfinite(self.start_s)):
            raise ValueError("fault drift_ppm_per_h and start_s must be finite")
        return self


class InstrumentEffectSpec(_Frozen):
    """A scripted change to one non-methane instrument (see ``InstrumentEffect``).

    Attributes:
        tag: Instrument tag; a key of ``plumetrace.simulator.instruments.BASELINES``.
        kind: ``"offset"`` adds ``value``; ``"set"`` replaces the level with ``value``.
        value: Offset or target level in the instrument's unit (finite).
        start_s: Start in scenario seconds (finite).
        end_s: End in scenario seconds (exclusive), after ``start_s``; infinite by default.
        ramp_s: Linear ramp length in seconds (finite, >= 0).
    """

    tag: str
    kind: Literal["offset", "set"]
    value: float
    start_s: float
    end_s: float = float("inf")
    ramp_s: float = 0.0

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Reject an unknown tag, non-finite numbers, an empty window or a bad ramp."""
        if self.tag not in BASELINES:
            raise ValueError(f"effect names unknown instrument {self.tag}")
        if not (math.isfinite(self.value) and math.isfinite(self.start_s)):
            raise ValueError(f"effect on {self.tag}: value and start_s must be finite")
        if not self.end_s > self.start_s:
            raise ValueError(f"effect on {self.tag}: end_s must be after start_s")
        if not (math.isfinite(self.ramp_s) and self.ramp_s >= 0.0):
            raise ValueError(f"effect on {self.tag}: ramp_s must be finite and >= 0")
        return self

    def to_effect(self) -> InstrumentEffect:
        """Return the matching ``InstrumentEffect`` for ``simulate_instruments``."""
        return InstrumentEffect(
            self.tag, self.kind, self.value, self.start_s, self.end_s, self.ramp_s
        )


class LogEntry(_Frozen):
    """One line of the station log (permit, gauging, maintenance, shift note, calibration).

    Attributes:
        t_s: Time in scenario seconds (>= 0, finite).
        kind: Entry type.
        tag: Equipment or instrument tag the entry is about, if any.
        text: Entry text (not blank).
    """

    t_s: float = Field(ge=0)
    kind: Literal["permit", "gauging", "maintenance", "shift_note", "calibration"]
    tag: str | None = None
    text: str

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Reject an infinite time or a blank text."""
        if not math.isfinite(self.t_s):
            raise ValueError("log t_s must be finite")
        if not self.text.strip():
            raise ValueError("log text must not be blank")
        return self


class ExpectedOutcome(_Frozen):
    """What the scenario is designed to show; used by tests and evaluations, never shown as truth.

    The leak rate is stored only as an interval (``rate_min_kg_h`` to ``rate_max_kg_h``), both or
    neither, so no single point rate can be displayed.

    Attributes:
        triage: Expected triage class.
        top_candidate: Anchor id the inversion should rank first, if any.
        attributed_unit: Equipment tag the leak should be attributed to, if any.
        rate_min_kg_h: Lower end of the expected rate interval in kg/h.
        rate_max_kg_h: Upper end of the expected rate interval in kg/h.
        rule_ids: Ids of the rules expected to apply.
    """

    triage: Literal["leak", "sensor_fault", "planned_venting"]
    top_candidate: str | None = None
    attributed_unit: str | None = None
    rate_min_kg_h: float | None = None
    rate_max_kg_h: float | None = None
    rule_ids: list[str] = []

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Require both rate bounds or neither, finite and ``0 <= min <= max``."""
        lo, hi = self.rate_min_kg_h, self.rate_max_kg_h
        if (lo is None) != (hi is None):
            raise ValueError("expected rate needs both rate_min_kg_h and rate_max_kg_h")
        if lo is not None and hi is not None:
            if not (math.isfinite(lo) and math.isfinite(hi) and 0.0 <= lo <= hi):
                raise ValueError("expected rate must be finite with 0 <= min <= max")
        return self


class ScenarioDefinition(_Frozen):
    """A complete scripted scenario.

    Attributes:
        id: Scenario id, ``s<digits>_<lowercase words>``, for example ``s1_rod_packing``.
        title: Display title.
        seed: Seed of the random generator (>= 0); the same seed gives the same run.
        weather_offset_h: Hours from the start of the weather snapshot to the scenario start.
        duration_h: Scenario length in hours, 1 to 24.
        sources: True emissions.
        faults: Sensor drift faults.
        instrument_effects: Scripted changes to the non-methane instruments, applied in order.
        log: Station log, sorted by ``t_s``.
        expected: The designed outcome.
        variant_index: Index of the variant within a scenario family, if any.
    """

    id: str = Field(pattern=r"^s[0-9]+_[a-z0-9_]+$")
    title: str
    seed: int
    weather_offset_h: int = Field(ge=0)
    duration_h: int = Field(ge=1, le=24)
    sources: list[SourceSpec] = []
    faults: list[FaultSpec] = []
    instrument_effects: list[InstrumentEffectSpec] = []
    log: list[LogEntry] = []
    expected: ExpectedOutcome
    variant_index: int | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Require a non-negative seed, a sorted log and everything inside the duration."""
        if self.seed < 0:
            raise ValueError("seed must be >= 0")
        times = [e.t_s for e in self.log]
        if times != sorted(times):
            raise ValueError("log entries must be sorted by t_s")
        end_s = self.duration_h * 3600.0
        starts = [
            *(s.start_s for s in self.sources),
            *(f.start_s for f in self.faults),
            *(e.start_s for e in self.instrument_effects),
        ]
        if any(t >= end_s for t in starts) or any(t > end_s for t in times):
            raise ValueError(f"every start and log time must lie inside the {end_s} s duration")
        return self
