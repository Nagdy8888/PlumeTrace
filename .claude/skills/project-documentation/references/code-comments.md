# Code comments and docstrings standard (PlumeTrace)

Python uses **Google-style docstrings** (Google Python Style Guide, section 3.8). TypeScript uses
**TSDoc** comments with the same sections. Both are enforced by linters and reviewed for depth.

## Python — Google style

Every module, class, function and method (public, private and nested) has a docstring.

### Module docstring
First line: one-sentence summary. Then a paragraph on purpose, the model/assumptions used, and
the main public names. Physics modules also state validity limits and references.

```python
"""Gaussian plume dispersion for continuous point sources at ground level and elevated release.

Implements the steady-state Gaussian plume with total ground reflection, using
Pasquill-Gifford rural dispersion coefficients for stability classes A-F.

Assumptions:
    Steady wind and emission over the averaging period; flat terrain; downwind
    distance 100 m - 10 km for the coefficient fits; no plume rise for vents.

References:
    Turner, D. B. (1994). Workbook of Atmospheric Dispersion Estimates, 2nd ed.
    Seinfeld & Pandis (2016). Atmospheric Chemistry and Physics, 3rd ed., ch. 18.
"""
```

### Function / method docstring
Sections in this order, each only when it applies: summary line, blank line, extended
description, `Args:`, `Returns:` (or `Yields:`), `Raises:`, `Examples:`, `Note:`.

```python
def ground_level_concentration(
    rate_kg_s: float, u_m_s: float, x_m: float, y_m: float,
    release_height_m: float, stability: StabilityClass,
) -> float:
    """Return the ground-level methane concentration downwind of a point source.

    Uses the Gaussian plume equation with total reflection at the ground
    (image source at -H). Upwind receptors (``x_m <= 0``) return 0.0.

    Args:
        rate_kg_s: Emission rate in kg/s. Must be >= 0.
        u_m_s: Mean wind speed at release height in m/s. Must be > 0.5; lower
            speeds violate the plume model's assumptions.
        x_m: Downwind distance from the source along the wind axis, in m.
        y_m: Crosswind distance from the plume centreline, in m.
        release_height_m: Effective release height above ground, in m.
        stability: Pasquill-Gifford stability class used for sigma_y / sigma_z.

    Returns:
        Concentration above background in kg/m3 at z = 0.

    Raises:
        ValueError: If ``rate_kg_s`` < 0 or ``u_m_s`` <= 0.5.

    Examples:
        Upwind receptors see no plume:

        >>> ground_level_concentration(0.005, 3.0, -50.0, 0.0, 2.0, StabilityClass.D)
        0.0
    """
```

### Class docstring
Summary, extended description of what an instance represents and its lifecycle, then an
`Attributes:` section for public attributes (with units). Document `__init__` arguments in the
class docstring or in `__init__` — pick one per project: **PlumeTrace documents them in the class
docstring** and leaves `__init__` with a one-line docstring.

```python
class InversionResult(BaseModel):
    """Posterior over candidate leak sources and emission rate for one event.

    Produced by :func:`invert_event`. Immutable; agents copy its numbers into
    drafts verbatim and never recompute them.

    Attributes:
        candidates: Candidate sources sorted by descending posterior probability.
        rate_kg_h: Posterior median emission rate of the top candidate, in kg/h.
        rate_p05_kg_h: 5th percentile of the rate posterior, in kg/h.
        rate_p95_kg_h: 95th percentile of the rate posterior, in kg/h.
        inconclusive: True when the top posterior is below the decision threshold.
    """
```

### Generators, tests, LangGraph nodes
- Generators use `Yields:` instead of `Returns:`.
- Test functions: a one-line docstring saying what behaviour is proven and, for physics tests,
  the reference value's source.
- LangGraph node functions document: which state keys they read, which they write, which tools
  they call, and side effects (must be none before `interrupt()` in the approval node).

### What to write in comments (inside function bodies)
Explain **why**, not what: the equation being implemented, a unit conversion, a non-obvious
numerical choice, a workaround with a link. Do not narrate obvious code. Keep `# TODO` only with
an owner/plan task reference.

### Enforcement (app/pyproject.toml workspace root, inherited by app/backend and app/agents)
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "D", "S", "ANN"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ANN"]   # asserts are fine in tests
```
Do **not** ignore `D417` (all parameters documented). Verify the exact keys against the pinned
Ruff version's docs before committing the config.

## TypeScript — TSDoc

Every exported function, component, hook, store, class and type has a `/** ... */` comment with a
summary line and, as they apply, `@param`, `@returns`, `@throws`, `@example`, `@remarks`.
Components document their props on the props type (one comment per prop, with units).

```ts
/**
 * Streams sensor readings for the active scenario from the current data source.
 *
 * @param scenarioId - Scenario to subscribe to, e.g. `"s1_rod_packing"`.
 * @returns A ref-backed reader; values change every tick without re-rendering.
 * @remarks Read inside `useFrame` for the 3D scene; never copy into React state per tick.
 */
export function useSensorStream(scenarioId: ScenarioId): SensorReader { … }
```
Enforce with `eslint-plugin-jsdoc` (require on exports) or `eslint-plugin-tsdoc` (syntax),
pinned in `app/frontend/package.json`.

Docstring examples must be real: run them as doctests (`uv run pytest --doctest-modules plumetrace`)
and never paste a number you did not compute.

## Depth checklist (apply to every non-trivial definition)
- Purpose, in domain words.
- Every input: meaning, **unit**, valid range, and what happens outside it.
- Output: meaning, unit, and special values (`inconclusive`, `None`, empty list).
- Side effects (I/O, state writes, network, LLM calls) — or "none".
- Errors raised and when.
- Assumptions and references for physics; the design section for agent behaviour.
- Never restate the signature; never claim a guarantee the code does not enforce.
