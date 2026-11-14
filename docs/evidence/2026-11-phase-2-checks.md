# Phase 2 checks

Date: 2026-11-14. Git revision: `a3c12c5` (Phase 2 Task 14 commit; the runs below were made on this committed tree, and only documentation files changed afterwards). Run from the repository root with local Supabase running. No GitHub Actions: every check is local. Evidence label: **local / synthetic** (local machine, Windows 11, Python 3.12; the benchmark data are simulated).

## Quick run: `python scripts/ci_local.py`

```text
stage                  result  seconds
structure              pass        5.3
env                    pass        0.4
secrets                pass        1.8
slop                   pass        0.1
ruff                   pass        0.2
ruff-format            pass        0.1
mypy                   pass        0.8
python-tests           pass        8.8
frontend-lint          pass        2.6
frontend-typecheck     pass        1.7
frontend-test          pass        3.6
all stages passed
```

Python tests in this run: 547 passed (`uv run pytest -q -m "not slow and not fuzz"`); frontend: 4 passed; frontend lint: 0 errors, 4 warnings (Phase 1 code, unchanged).

## Full run: `python scripts/ci_local.py --full`

```text
stage                  result  seconds
structure              pass        4.7
env                    pass        0.3
secrets                pass        1.6
slop                   pass        0.1
ruff                   pass        0.2
ruff-format            pass        0.1
mypy                   pass        0.5
python-tests-full      pass       13.8
frontend-lint          pass        2.4
frontend-typecheck     pass        1.8
frontend-coverage      pass        3.9
frontend-build         pass        2.3
contract-drift         pass        1.1
all stages passed
```

`python-tests-full`: 547 passed, total Python coverage 99.14 % (gate 85 %).

## Repository checks

| Command | Output |
|---|---|
| `python -I .claude/skills/repo-structure/scripts/check_structure.py .` | `structure OK` |
| `python -I .claude/skills/security-checks/scripts/check_env.py .` | `env OK` |
| `python -I .claude/skills/security-checks/scripts/secret_scan.py .` | `no secrets found` |
| `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src` | `no slop found` |

## Dependency audits (by hand; they become stages in Phase 6 Task 6)

`cd app && uv run pip-audit`

```text
No known vulnerabilities found
Name              Skip Reason
----------------- --------------------------------------------------------------------------------
plumetrace        Dependency not found on PyPI and could not be audited: plumetrace (0.1.0)
plumetrace-agents Dependency not found on PyPI and could not be audited: plumetrace-agents (0.1.0)
```

`cd app/frontend && npm audit --audit-level=high` (exit code 0)

```text
10 moderate severity vulnerabilities
```

No high or critical finding. The moderate findings are one `minimatch` denial-of-service advisory (GHSA-g3hv-75wg-m249) reached through the eslint toolchain (`eslint`, `@eslint/config-array`, `@typescript-eslint/typescript-estree` and plugins that depend on them): dev dependencies, not changed in Phase 2 (Phase 1 reported 11), to be handled in the Phase 6 audit. `numpy==2.5.4` is pinned in `app/uv.lock`.

## Tests by module (Phase 2 engineering core and benchmark)

Counts come from `uv run pytest backend/tests --collect-only -q` (parametrised cases count separately).

| Module | Tests | Files |
|---|---|---|
| units | 6 | `test_units.py` |
| gas | 9 | `test_gas.py` |
| stability | 30 | `test_stability.py` |
| dispersion | 17 | `test_dispersion.py` |
| plume | 9 | `test_plume.py` |
| averaging | 12 | `test_averaging.py`, `test_averaging_edges.py` |
| detection | 21 | `test_detection.py`, `test_detection_edges.py` |
| inversion | 47 | `test_inversion.py`, `test_inversion_edges.py` |
| fusion | 55 | `test_fusion.py`, `test_fusion_edges.py` |
| flare | 30 | `test_flare.py`, `test_flare_edges.py` |
| blowdown | 28 | `test_blowdown.py`, `test_blowdown_edges.py` |
| inventory | 38 | `test_inventory.py`, `test_inventory_edges.py` |
| intensity | 20 | `test_intensity.py`, `test_intensity_edges.py` |
| truth model (and weather, wake, faults) | 134 | `test_truth_model.py`, `test_truth_model_edges.py`, `test_truth_model_physics_edges.py`, `test_truth_weather_edges.py` |
| physical laws (Hypothesis, 200 examples each) | 11 | `test_properties.py` |
| benchmark | 22 | `test_benchmark.py`, `test_benchmark_edges.py` |
| **Total (engineering and benchmark)** | **489** | |

The whole Python suite has 547 tests (the other 58 are facility, database, configuration, contract and tooling tests).

## Coverage of the engineering core and benchmark

`cd app && uv run pytest backend/tests/engineering backend/tests/benchmark --cov=plumetrace.engineering --cov=benchmark --cov-report=term-missing -q` (489 passed in 9.9 s; branch coverage on):

```text
Name                                                 Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------------------------------------
backend/benchmark/__init__.py                            0      0      0      0   100%
backend/benchmark/__main__.py                           39      1      2      1    95%   42
backend/benchmark/cases.py                              59      0      0      0   100%
backend/benchmark/metrics.py                            55      0      6      0   100%
backend/benchmark/report.py                             33      0      0      0   100%
backend/benchmark/runner.py                             39      0      0      0   100%
backend/plumetrace/engineering/__init__.py               0      0      0      0   100%
backend/plumetrace/engineering/averaging.py             41      0      8      0   100%
backend/plumetrace/engineering/blowdown.py              36      0     14      0   100%
backend/plumetrace/engineering/constants.py             20      0      0      0   100%
backend/plumetrace/engineering/detection.py             68      1     20      1    98%   90
backend/plumetrace/engineering/dispersion.py            29      0      2      0   100%
backend/plumetrace/engineering/emission_factors.py       4      0      0      0   100%
backend/plumetrace/engineering/flare.py                 13      0      4      0   100%
backend/plumetrace/engineering/fusion.py               107      0     40      0   100%
backend/plumetrace/engineering/gas.py                   42      1      8      1    96%   42
backend/plumetrace/engineering/geometry.py              15      0      0      0   100%
backend/plumetrace/engineering/intensity.py             13      0      6      0   100%
backend/plumetrace/engineering/inventory.py             50      2     16      2    94%   96, 128
backend/plumetrace/engineering/inversion.py            130      0     26      0   100%
backend/plumetrace/engineering/inversion_model.py       27      0      4      0   100%
backend/plumetrace/engineering/plume.py                 32      0      4      0   100%
backend/plumetrace/engineering/stability.py             28      0      6      0   100%
backend/plumetrace/engineering/truth_faults.py          19      0      4      0   100%
backend/plumetrace/engineering/truth_model.py          105      0     32      0   100%
backend/plumetrace/engineering/truth_turbulence.py      18      0      2      0   100%
backend/plumetrace/engineering/truth_wake.py            28      0      6      0   100%
backend/plumetrace/engineering/truth_weather.py         87      0     14      0   100%
backend/plumetrace/engineering/units.py                 22      0      0      0   100%
------------------------------------------------------------------------------------------------
TOTAL                                                 1159      5    224      5    99%
```

Uncovered lines: `benchmark/__main__.py` 42, `detection.py` 90, `gas.py` 42, `inventory.py` 96 and 128. This is line and branch coverage; it does not show that the assertions are strong (no mutation testing on Windows, see `docs/reference/TESTING.md`).

## Benchmark determinism check

The benchmark was rerun at the published revision label into files outside the repository:
`cd app && uv run python -m benchmark --revision 23b8703 --out-md <scratchpad>/bench.md --out-json <scratchpad>/bench.json`
and compared with `cmp` / `diff` against `docs/benchmark.md` and `docs/evidence/benchmark-2026-11-13.json`.
The only difference in each file is the `date` field (`2026-11-14` in the rerun, `2026-11-13` in the committed file), which the program takes from the clock; every number, case and id is byte-identical. `git diff 23b8703 -- app/backend/benchmark app/backend/plumetrace/engineering` is empty, so the published revision stays valid. The committed benchmark files were not regenerated.

## Benchmark headline (copied from `docs/benchmark.md`, run of 2026-11-13, revision `23b8703`, synthetic)

| Metric | Value |
|---|---|
| Top-1 accuracy (all leak cases) | 0.4 |
| Top-1 accuracy (conclusive leak cases) | 0.491 |
| Top-3 accuracy (all leak cases) | 0.62 |
| Rate error, median (relative) | 1.13 |
| Rate error, 90th percentile (relative) | 26.7 |
| Inconclusive rate (leak cases) | 0.185 |
| False-call rate (no-leak cases) | 0 |

The false-call rate counts only the 50 no-leak cases. A post-hoc reading of the leak cases (9 conclusive "no leak" calls on real leaks; the posterior is as confident when wrong as when right) is in `docs/reference/ENGINEERING.md`, Benchmark, "Post-hoc reading of the committed evidence". It is not part of the published scoring.

## Gate 2 inputs (owner review)

Phase 2 is complete. Waiting for Gate 2 (physics assumptions and benchmark). Please review the assumptions index in `docs/reference/ENGINEERING.md` section 4, the benchmark in `docs/benchmark.md` and the post-hoc reading above.
