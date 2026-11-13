# Phase 2 · Task 14 — Property-based and metamorphic tests of the engineering core

**Skills:** `plan-execution`, `engineering-core`, `testing-strategy`, `superpowers:test-driven-development`, `project-documentation`.
**Docs to check first:** Hypothesis 6.170.14 — `@given`, `settings(max_examples=..., derandomize=..., deadline=..., database=...)`, `strategies.floats/sampled_from/lists/builds/fixed_dictionaries/randoms`.

**Why:** the example tests of Tasks 1–11 prove the formulas at hand-calculated points. These tests
prove the **laws** the physics must obey for every valid input — linearity of the plume in the rate,
1/u scaling, nothing upwind, crosswind symmetry, rotation invariance, unit round trips, the circular
mean rotating with the data, fusion being a proper probability update, flare slip ordering and
physical gas properties. A law that breaks shows a real bug that point tests can miss.

**Verified by the planner (2026-11-13):** this exact file passes (11 tests) against a reference
implementation written from the Task 1–10 interfaces, and is clean under the project's ruff
rules and formatter. If a test fails against your implementation, the implementation deviates
from its task file — fix the implementation, never the test; if you believe the law itself is
wrong, STOP and report.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/tests/engineering/test_properties.py` (full code below, copy verbatim) |
| Modify | `docs/reference/ENGINEERING.md` → "Physical laws tested" (one line per test: the law and its source) |

`hypothesis==6.170.14` is already a dev dependency (Phase 1 Task 2). The settings use
`derandomize=True` and `database=None`, so every run tests the same inputs and writes no
`.hypothesis/` folder.

## Test (full code) — `app/backend/tests/engineering/test_properties.py`
```python
"""Property-based and metamorphic tests of the engineering core (Hypothesis).

Each test states a law the physics must obey for every valid input, not one worked example:
linearity of the Gaussian plume in the source rate (Turner 1994, eq. 1-1), inverse proportion to
wind speed, zero concentration upwind, crosswind mirror symmetry, invariance under rotating the
whole scene with the wind, unit round trips, rotation of a circular mean, and the probability
laws of evidence fusion (a Bayesian update: non-negative, sums to one, order-independent).
"""

import math

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from plumetrace.engineering.averaging import circular_mean_deg
from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.flare import flare_ch4_slip_kg_h
from plumetrace.engineering.fusion import EvidenceItem, fuse
from plumetrace.engineering.gas import GasComposition, ch4_mass_fraction, z_factor_papay
from plumetrace.engineering.geometry import Point3
from plumetrace.engineering.plume import concentration_kg_m3
from plumetrace.engineering.stability import StabilityClass
from plumetrace.engineering.units import kg_m3_to_ppm, ppm_to_kg_m3

LAW = settings(max_examples=200, derandomize=True, deadline=None, database=None)

rates = st.floats(1e-5, 5.0)
speeds = st.floats(0.5, 20.0)
bearings = st.floats(0.0, 360.0, exclude_max=True)
classes = st.sampled_from(list(StabilityClass))
coeffs = st.sampled_from(list(CoefficientSet))
heights = st.floats(0.0, 30.0)
along_m = st.floats(1.0, 1500.0)
cross_m = st.floats(-300.0, 300.0)
receptor_z = st.floats(0.0, 10.0)


def _receptor(
    source: Point3, wind_from_deg: float, along: float, cross: float, z: float
) -> np.ndarray:
    """Place a receptor at given downwind / crosswind offsets from the source."""
    theta = math.radians(wind_from_deg + 180.0)
    x = source.x_m + along * math.sin(theta) + cross * math.cos(theta)
    y = source.y_m + along * math.cos(theta) - cross * math.sin(theta)
    return np.array([[x, y, z]])


@LAW
@given(
    rates,
    st.floats(0.1, 10.0),
    speeds,
    bearings,
    heights,
    along_m,
    cross_m,
    receptor_z,
    classes,
    coeffs,
)
def test_plume_is_linear_in_rate(
    q: float,
    k: float,
    u: float,
    w: float,
    h: float,
    a: float,
    c: float,
    z: float,
    sc: StabilityClass,
    cs: CoefficientSet,
) -> None:
    """C(k·Q) = k·C(Q): the Gaussian plume is linear in the emission rate."""
    src = Point3(10.0, 20.0, h)
    rec = _receptor(src, w, a, c, z)
    base = concentration_kg_m3(q, u, w, src, rec, sc, cs)[0]
    scaled = concentration_kg_m3(k * q, u, w, src, rec, sc, cs)[0]
    assert math.isclose(scaled, k * base, rel_tol=1e-9, abs_tol=1e-300)


@LAW
@given(rates, speeds, speeds, bearings, heights, along_m, cross_m, receptor_z, classes, coeffs)
def test_plume_scales_inversely_with_wind_speed(
    q: float,
    u1: float,
    u2: float,
    w: float,
    h: float,
    a: float,
    c: float,
    z: float,
    sc: StabilityClass,
    cs: CoefficientSet,
) -> None:
    """C·u is the same for any wind speed (no plume rise for vents)."""
    src = Point3(0.0, 0.0, h)
    rec = _receptor(src, w, a, c, z)
    c1 = concentration_kg_m3(q, u1, w, src, rec, sc, cs)[0]
    c2 = concentration_kg_m3(q, u2, w, src, rec, sc, cs)[0]
    assert math.isclose(c1 * u1, c2 * u2, rel_tol=1e-9, abs_tol=1e-300)


@LAW
@given(
    rates,
    speeds,
    bearings,
    heights,
    st.floats(-1500.0, -0.01),
    cross_m,
    receptor_z,
    classes,
    coeffs,
)
def test_nothing_upwind(
    q: float,
    u: float,
    w: float,
    h: float,
    a: float,
    c: float,
    z: float,
    sc: StabilityClass,
    cs: CoefficientSet,
) -> None:
    """Receptors behind the source (along < 0) see zero concentration."""
    src = Point3(0.0, 0.0, h)
    rec = _receptor(src, w, a, c, z)
    assert concentration_kg_m3(q, u, w, src, rec, sc, cs)[0] == 0.0


@LAW
@given(rates, speeds, bearings, heights, along_m, cross_m, receptor_z, classes, coeffs)
def test_crosswind_mirror_symmetry_and_finiteness(
    q: float,
    u: float,
    w: float,
    h: float,
    a: float,
    c: float,
    z: float,
    sc: StabilityClass,
    cs: CoefficientSet,
) -> None:
    """Mirroring a receptor across the plume axis gives the same, finite, non-negative value."""
    src = Point3(-5.0, 7.0, h)
    left = concentration_kg_m3(q, u, w, src, _receptor(src, w, a, c, z), sc, cs)[0]
    right = concentration_kg_m3(q, u, w, src, _receptor(src, w, a, -c, z), sc, cs)[0]
    assert math.isfinite(left) and left >= 0.0
    assert math.isclose(left, right, rel_tol=1e-7, abs_tol=1e-300)


@LAW
@given(rates, speeds, bearings, bearings, heights, along_m, cross_m, receptor_z, classes, coeffs)
def test_rotating_the_scene_with_the_wind_changes_nothing(
    q: float,
    u: float,
    w: float,
    phi: float,
    h: float,
    a: float,
    c: float,
    z: float,
    sc: StabilityClass,
    cs: CoefficientSet,
) -> None:
    """Rotate source, receptor and wind direction together by φ: the concentration is unchanged."""
    src = Point3(30.0, -40.0, h)
    rec = _receptor(src, w, a, c, z)
    r = math.radians(phi)

    def rot(x: float, y: float) -> tuple[float, float]:
        return (x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r))

    sx, sy = rot(src.x_m, src.y_m)
    rx, ry = rot(float(rec[0, 0]), float(rec[0, 1]))
    before = concentration_kg_m3(q, u, w, src, rec, sc, cs)[0]
    after = concentration_kg_m3(
        q, u, (w + phi) % 360.0, Point3(sx, sy, h), np.array([[rx, ry, z]]), sc, cs
    )[0]
    assert math.isclose(before, after, rel_tol=1e-6, abs_tol=1e-300)


@LAW
@given(st.floats(0.0, 1.0), st.floats(230.0, 330.0), st.floats(80_000.0, 110_000.0))
def test_ppm_round_trip(conc_kg_m3: float, temp_k: float, pressure_pa: float) -> None:
    """kg/m³ → ppm → kg/m³ returns the input (ideal-gas conversion is exactly invertible)."""
    back = ppm_to_kg_m3(kg_m3_to_ppm(conc_kg_m3, temp_k, pressure_pa), temp_k, pressure_pa)
    assert math.isclose(back, conc_kg_m3, rel_tol=1e-12, abs_tol=1e-18)


@LAW
@given(bearings, bearings, st.lists(st.floats(-40.0, 40.0), min_size=1, max_size=30))
def test_circular_mean_rotates_with_the_data(base: float, phi: float, offsets: list[float]) -> None:
    """Rotating every direction by φ rotates the circular mean by φ; the result is in [0, 360)."""
    dirs = np.array([(base + o) % 360.0 for o in offsets])
    m1 = circular_mean_deg(dirs)
    m2 = circular_mean_deg((dirs + phi) % 360.0)
    assert 0.0 <= m1 < 360.0 and 0.0 <= m2 < 360.0
    diff = (m2 - m1 - phi + 180.0) % 360.0 - 180.0
    assert abs(diff) < 1e-6


evidence_items = st.lists(
    st.builds(
        EvidenceItem,
        candidate_id=st.sampled_from(["A", "B", "C", "Z"]),
        likelihood_ratio=st.floats(0.001, 1000.0),
        source_tag=st.just("T"),
        reason=st.just("property test"),
    ),
    max_size=8,
)
priors = st.fixed_dictionaries({k: st.floats(0.01, 10.0) for k in ("A", "B", "C")})


@LAW
@given(priors, evidence_items, st.randoms(use_true_random=False))
def test_fusion_is_a_probability_and_order_free(
    prior: dict[str, float], items: list[EvidenceItem], rnd: object
) -> None:
    """Posterior ≥ 0, sums to 1, and does not depend on the order of the evidence."""
    out = fuse(prior, items)
    assert all(p >= 0.0 for p in out.probabilities.values())
    assert math.isclose(sum(out.probabilities.values()), 1.0, rel_tol=0, abs_tol=1e-12)
    shuffled = list(items)
    rnd.shuffle(shuffled)  # type: ignore[attr-defined]
    again = fuse(prior, shuffled)
    for key, value in out.probabilities.items():
        assert math.isclose(again.probabilities[key], value, rel_tol=1e-9, abs_tol=1e-15)


@LAW
@given(priors)
def test_neutral_evidence_keeps_the_prior(prior: dict[str, float]) -> None:
    """Likelihood ratio 1 everywhere: the posterior is the normalised prior."""
    items = [
        EvidenceItem(candidate_id=k, likelihood_ratio=1.0, source_tag="T", reason="neutral")
        for k in prior
    ]
    out = fuse(prior, items)
    total = sum(prior.values())
    for key, value in prior.items():
        assert math.isclose(out.probabilities[key], value / total, rel_tol=1e-12)


@LAW
@given(st.floats(0.0, 5000.0), st.floats(0.0, 1.0))
def test_unlit_flare_never_slips_less_than_lit(flared_kg_h: float, w: float) -> None:
    """With the pilot out, all CH4 slips; lit, only (1 − DE) of it — never more."""
    lit = flare_ch4_slip_kg_h(flared_kg_h, w, pilot_lit=True)
    unlit = flare_ch4_slip_kg_h(flared_kg_h, w, pilot_lit=False)
    assert 0.0 <= lit <= unlit


compositions = st.tuples(st.floats(0.85, 1.0), st.floats(0.0, 1.0)).map(
    lambda t: GasComposition(
        mole_fractions={"CH4": t[0], "C2H6": (1 - t[0]) * t[1], "C3H8": (1 - t[0]) * (1 - t[1])}
    )
)


@LAW
@given(compositions, st.floats(1.0e5, 8.0e6), st.floats(260.0, 330.0))
def test_pipeline_gas_properties_stay_physical(
    comp: GasComposition, pressure_pa: float, temp_k: float
) -> None:
    """Pipeline-quality gas (CH4 ≥ 85 %): 0 < Z ≤ 1.05 and the CH4 mass fraction is in [0, 1]."""
    z = z_factor_papay(pressure_pa, temp_k, comp)
    assert 0.0 < z <= 1.05
    assert 0.0 <= ch4_mass_fraction(comp) <= 1.0
```

## Steps
- [ ] Copy the file → `cd app && uv run pytest backend/tests/engineering/test_properties.py -q` → `11 passed`.
- [ ] Full checks (`python scripts/ci_local.py`); ruff, ruff format, mypy clean.
- [ ] **Docs.** ENGINEERING.md → "Physical laws tested"; `docs/reference/TESTING.md` → "Property-based tests" row for this file. Work-log; `STATUS.md`: "Phase 2 complete — waiting for Gate 2 (physics assumptions + benchmark). Improvement round: not started."
- [ ] **Commit** `test(engineering): add property-based and metamorphic tests of the physics`.
