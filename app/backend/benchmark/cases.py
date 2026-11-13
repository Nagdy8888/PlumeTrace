"""Deterministic benchmark cases: on-list leaks, off-list leaks and no-leak controls.

The truth model (Task 12) later turns each case into sensor data. Every constant here is a
Phase 2 Task 13 value (project choices, not published coefficients).
"""

import math
from dataclasses import dataclass
from typing import Final, Literal

import numpy as np

from plumetrace.engineering.geometry import Candidate, Point3
from plumetrace.engineering.truth_model import TrueSource
from plumetrace.facility.candidates import emission_candidates
from plumetrace.facility.spec import FacilitySpec

BENCHMARK_SEED: Final = 20261112
N_ON_LIST: Final = 160
N_OFF_LIST: Final = 40
N_NO_LEAK: Final = 50
OFF_LIST_MIN_M: Final = 2.0
OFF_LIST_MAX_M: Final = 10.0
RATE_MIN_KG_H: Final = 0.5
RATE_MAX_KG_H: Final = 100.0
CASE_HOURS: Final = 6
DT_S: Final = 10.0

_SEED_LIMIT: Final = 2**31


@dataclass(frozen=True)
class BenchmarkCase:
    """One test case of the benchmark.

    Attributes:
        case_id: Id such as ``on_list-007``.
        kind: ``on_list`` (source at a candidate), ``off_list`` (source 2 to 10 m from one) or
            ``no_leak`` (no source).
        source: The true emission, or None for a no-leak case.
        true_candidate_id: The candidate the source is at (on-list) or was offset from
            (off-list); None for a no-leak case.
        start_hour_of_day: Local clock hour at the start of the case, 0 to 23.
        seed: Seed of the generator that draws the weather and the sensor data.
    """

    case_id: str
    kind: Literal["on_list", "off_list", "no_leak"]
    source: TrueSource | None
    true_candidate_id: str | None
    start_hour_of_day: int
    seed: int


def _rate_kg_h(rng: np.random.Generator) -> float:
    """Draw a leak rate, log-uniform between the minimum and maximum rate."""
    return math.exp(rng.uniform(math.log(RATE_MIN_KG_H), math.log(RATE_MAX_KG_H)))


def _source(position: Point3, rate_kg_h: float) -> TrueSource:
    """Make a source that is active for the whole case."""
    return TrueSource(position, rate_kg_h, 0.0, CASE_HOURS * 3600.0)


def _on_list(i: int, cands: list[Candidate], rng: np.random.Generator) -> BenchmarkCase:
    """Draw one on-list case: candidate, rate, start hour, seed."""
    cand = cands[int(rng.integers(len(cands)))]
    rate = _rate_kg_h(rng)
    hour = int(rng.integers(24))
    seed = int(rng.integers(_SEED_LIMIT))
    return BenchmarkCase(
        f"on_list-{i:03d}", "on_list", _source(cand.position, rate), cand.id, hour, seed
    )


def _off_list(
    i: int, cands: list[Candidate], spec: FacilitySpec, rng: np.random.Generator
) -> BenchmarkCase:
    """Draw one off-list case: candidate, angle, radius, rate, start hour, seed."""
    cand = cands[int(rng.integers(len(cands)))]
    angle = rng.uniform(0.0, 2.0 * math.pi)
    radius = rng.uniform(OFF_LIST_MIN_M, OFF_LIST_MAX_M)
    rate = _rate_kg_h(rng)
    hour = int(rng.integers(24))
    seed = int(rng.integers(_SEED_LIMIT))
    b = spec.site.bounds
    x = min(max(cand.position.x_m + radius * math.cos(angle), b.x_min_m), b.x_max_m)
    y = min(max(cand.position.y_m + radius * math.sin(angle), b.y_min_m), b.y_max_m)
    return BenchmarkCase(
        f"off_list-{i:03d}",
        "off_list",
        _source(Point3(x, y, cand.position.z_m), rate),
        cand.id,
        hour,
        seed,
    )


def _no_leak(i: int, rng: np.random.Generator) -> BenchmarkCase:
    """Draw one no-leak control: start hour and seed."""
    hour = int(rng.integers(24))
    seed = int(rng.integers(_SEED_LIMIT))
    return BenchmarkCase(f"no_leak-{i:03d}", "no_leak", None, None, hour, seed)


def generate_cases(spec: FacilitySpec, seed: int = BENCHMARK_SEED) -> list[BenchmarkCase]:
    """Generate all benchmark cases from one seeded generator.

    Order: all on-list cases, then off-list, then no-leak. Ids are ``<kind>-<i:03d>`` with ``i``
    counting from 0 within each kind. An off-list source is clipped into the site bounds.

    Args:
        spec: The facility spec (candidates and site bounds).
        seed: Seed of the one generator that draws everything.

    Returns:
        ``N_ON_LIST + N_OFF_LIST + N_NO_LEAK`` cases.
    """
    rng = np.random.default_rng(seed)
    cands = emission_candidates(spec)
    cases = [_on_list(i, cands, rng) for i in range(N_ON_LIST)]
    cases += [_off_list(i, cands, spec, rng) for i in range(N_OFF_LIST)]
    cases += [_no_leak(i, rng) for i in range(N_NO_LEAK)]
    return cases
