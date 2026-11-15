"""Scenario variants: randomised families of a base scenario for the agent evaluation.

Design section 6 ("Agent evaluation") asks for about 20 randomised variants per scenario so the
evaluation is statistically meaningful. A variant changes the weather window, the leak rate (and
the FT-250 signature with it), the timing, the distractor log entries and the noise seed. It never
changes what the scenario is about: the expected triage, top candidate and unit stay as in the
base, and the expected rate interval scales with the leak rate, so the expected outcome follows
from the scenario physics and never from running the inversion.

Pure and deterministic: the draws come only from a seeded ``numpy`` generator, so the same base,
seed and count give the same variants. The ranges and the distractor texts are Task 6 values (no
cited source). The station and every entry are simulated.
"""

import hashlib
import math
from dataclasses import dataclass
from typing import Final

import numpy as np

from plumetrace.simulator.scenario import (
    ExpectedOutcome,
    InstrumentEffectSpec,
    LogEntry,
    ScenarioDefinition,
    SourceSpec,
)

VARIANTS_PER_SCENARIO: Final = 20
VARIANT_SEED: Final = 20261120
RATE_SCALE_RANGE: Final = (0.5, 2.0)
TIME_SHIFT_RANGE_S: Final = (-1800.0, 1800.0)
SNAPSHOT_HOURS: Final = 168

DISTRACTOR_LOG: Final[tuple[LogEntry, ...]] = (
    LogEntry(t_s=0.0, kind="shift_note", text="Radio check with the dispatch centre completed."),
    LogEntry(
        t_s=0.0,
        kind="maintenance",
        tag="E-232",
        text="Fin-fan E-232 belt tension checked; no action needed.",
    ),
    LogEntry(
        t_s=0.0, kind="gauging", tag="TK-401", text="TK-401 gauged; hatch closed and latched."
    ),
    LogEntry(t_s=0.0, kind="calibration", tag="AT-102", text="AT-102 bump test passed."),
    LogEntry(
        t_s=0.0,
        kind="shift_note",
        text="Contractor vehicle entered the site for scaffolding inspection.",
    ),
    LogEntry(
        t_s=0.0,
        kind="maintenance",
        tag="FG-501",
        text="Fuel gas filter differential pressure logged at 0.3 bar.",
    ),
)

_SCALED_TAG: Final = "FT-250"


@dataclass(frozen=True)
class _Draws:
    """The random choices of one variant, in draw order."""

    offset_h: int
    scale: float
    shift_s: float
    distractors: list[LogEntry]
    seed: int


def _base_hash(scenario_id: str) -> int:
    """Return a stable 32-bit integer for a scenario id (not Python's salted ``hash``)."""
    return int.from_bytes(hashlib.sha256(scenario_id.encode()).digest()[:4], "big")


def _draw(rng: np.random.Generator, base: ScenarioDefinition) -> _Draws:
    """Draw one variant's choices in the order the module documents."""
    offset_h = int(rng.integers(0, SNAPSHOT_HOURS - base.duration_h - 1 + 1))
    scale = math.exp(rng.uniform(math.log(RATE_SCALE_RANGE[0]), math.log(RATE_SCALE_RANGE[1])))
    shift_s = float(rng.uniform(*TIME_SHIFT_RANGE_S))
    k = int(rng.integers(0, 3))
    picks = rng.choice(len(DISTRACTOR_LOG), size=k, replace=False)
    distractors = [
        DISTRACTOR_LOG[int(i)].model_copy(
            update={"t_s": float(rng.uniform(0, base.duration_h * 3600))}
        )
        for i in picks
    ]
    return _Draws(offset_h, scale, shift_s, distractors, int(rng.integers(2**31)))


def _source(s: SourceSpec, scale: float, shift: float) -> SourceSpec:
    """Scale the rate and move the window (clamped at 0; an infinite end stays infinite)."""
    return s.model_copy(
        update={
            "rate_kg_h": s.rate_kg_h * scale,
            "start_s": max(0.0, s.start_s + shift),
            "end_s": max(0.0, s.end_s + shift),
        }
    )


def _effect(e: InstrumentEffectSpec, scale: float, shift: float) -> InstrumentEffectSpec:
    """Move the window; scale the FT-250 offset with the leak rate."""
    value = e.value * scale if e.tag == _SCALED_TAG and e.kind == "offset" else e.value
    return e.model_copy(
        update={"value": value, "start_s": e.start_s + shift, "end_s": e.end_s + shift}
    )


def _log(entries: list[LogEntry], shift: float, duration_s: float) -> list[LogEntry]:
    """Move every base log entry by the shift, clamped to the scenario; distractors stay."""
    return [e.model_copy(update={"t_s": min(max(0.0, e.t_s + shift), duration_s)}) for e in entries]


def _expected(x: ExpectedOutcome, scale: float) -> ExpectedOutcome:
    """Scale the expected rate interval (when there is one) with the leak rate."""
    if x.rate_min_kg_h is None or x.rate_max_kg_h is None:
        return x
    return x.model_copy(
        update={"rate_min_kg_h": x.rate_min_kg_h * scale, "rate_max_kg_h": x.rate_max_kg_h * scale}
    )


def _build(base: ScenarioDefinition, index: int, d: _Draws) -> ScenarioDefinition:
    """Build one variant from the base and its draws, then validate it again."""
    log = _log(base.log, d.shift_s, base.duration_h * 3600.0) + d.distractors
    variant = base.model_copy(
        update={
            "weather_offset_h": d.offset_h,
            "seed": d.seed,
            "variant_index": index,
            "sources": [_source(s, d.scale, d.shift_s) for s in base.sources],
            "instrument_effects": [_effect(e, d.scale, d.shift_s) for e in base.instrument_effects],
            "faults": [
                f.model_copy(update={"start_s": max(0.0, f.start_s + d.shift_s)})
                for f in base.faults
            ],
            "log": sorted(log, key=lambda e: e.t_s),
            "expected": _expected(base.expected, d.scale),
        }
    )
    # model_copy skips validation; re-validate so every scenario rule also holds for a variant.
    return ScenarioDefinition.model_validate(variant.model_dump())


def generate_variants(
    base: ScenarioDefinition, n: int = VARIANTS_PER_SCENARIO, seed: int = VARIANT_SEED
) -> list[ScenarioDefinition]:
    """Generate ``n`` randomised variants of a base scenario.

    Per variant the generator draws, in this order: the weather offset (the whole run must fit the
    168 h snapshot), a rate scale (log-uniform in ``RATE_SCALE_RANGE``), a time shift (uniform in
    ``TIME_SHIFT_RANGE_S``), 0 to 2 distractor log entries with their times, and the noise seed.
    The leak rate, the FT-250 offset and the expected rate interval are multiplied by the scale;
    source, effect and fault times and the base log entries move by the shift (the distractors stay
    where they were drawn). Every variant keeps the
    base ``id`` and gets ``variant_index`` 0 to ``n - 1``; the pair is its unique, stable key.

    Args:
        base: The base scenario; it is not changed.
        n: Number of variants (>= 0).
        seed: Seed of the family; the generator also mixes in a stable hash of ``base.id``.

    Returns:
        The variants, each re-validated as a ``ScenarioDefinition``.

    Raises:
        ValueError: If ``n`` is negative, or a variant breaks a scenario rule (for example a
            start pushed past the end of the scenario); the error is a ``pydantic.ValidationError``.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = np.random.default_rng([seed, _base_hash(base.id)])
    return [_build(base, i, _draw(rng, base)) for i in range(n)]
