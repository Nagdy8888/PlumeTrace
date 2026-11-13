---
name: engineering-core
description: Write or change PlumeTrace engineering code in app/backend/plumetrace/engineering - Gaussian plume dispersion, source inversion, flare combustion, emission-factor inventory, mass balance, OGMP 2.0 reconciliation, unit conversions, and the inversion benchmark. Use for any physics or calculation change, and before exposing a calculation as an agent tool.
---

# Engineering core (PlumeTrace)

The engineering core is the credibility of the whole project. Engineers on LinkedIn will check it.
Design reference: `docs/superpowers/specs/2026-11-12-plumetrace-design.md`, section 5.

## Rules

1. **Pure functions.** No LLM, no network, no file I/O, no global state, no randomness without an
   explicit seeded `numpy.random.Generator` argument. Inputs and outputs are typed (Pydantic
   models or dataclasses) and returned values carry their units in field names.
2. **SI units inside.** Convert at the edges only. Name every quantity with its unit:
   `rate_kg_h`, `rate_kg_s`, `u_m_s`, `conc_ppm`, `conc_kg_m3`, `x_m`, `stack_height_m`,
   `temp_k`. Conversion helpers live in `units.py` and are tested.
3. **Test first (TDD).** Write the failing test, then the code. Physics tests use published
   worked examples or reference values; cite the source (book/standard, edition, page/table) in
   the test docstring. Use `pytest.approx` with an explicit, justified tolerance.
4. **Property and sanity tests** for every model: concentration falls with distance downwind,
   is zero upwind beyond the plume, scales linearly with rate, is symmetric across the plume axis,
   and mass is conserved within tolerance; inversion recovers a known source on clean data.
5. **Uncertainty is part of the answer.** Inversion returns ranked candidates with posterior
   probabilities, a rate estimate with a 90% interval, and an explicit `inconclusive` result when
   evidence is weak. Never return a bare point estimate to an agent.
6. **Cite every constant.** Dispersion coefficients (stability classes A–F), emission factors,
   GWP values (IPCC AR6), methane density and molar mass: each has a source comment and a single
   definition in `constants.py`.
7. **Benchmark with model mismatch.** `benchmark/` generates test leaks with different physics
   from the inversion (other dispersion-coefficient set, wind meander, building wakes, off-list
   sources, sensor faults) and reports top-1/top-3 accuracy, rate error (median, P90),
   inconclusive rate and false-call rate, split by stability class and leak size. Seeded and
   reproducible. Results go to `docs/benchmark.md` exactly as produced — never edit numbers by hand.
8. **Agent tools are thin wrappers.** Tool implementations in `app/backend/plumetrace/agent_tools/` validate
   input, call one engineering function, and map its typed result 1:1 into the `plumetrace_agents.schemas.tool_io` result model. No calculation
   logic in tools or prompts.
9. **Performance:** vectorise with numpy; the inversion for one event must finish in under
   ~2 s on a laptop so live mode feels responsive.
10. Before marking a task done: `uv run pytest app/backend/tests/engineering -q` (from `app/`), `uv run ruff check`,
    `uv run ty check` (or the configured type checker) — and show the output.
