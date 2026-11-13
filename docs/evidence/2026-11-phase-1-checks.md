# Phase 1 checks

Date: 2026-11-13. Git revision: `9a45f2e` (Task 8 commit; the tables below were produced on this committed tree). Run from the repository root with local Supabase running. No GitHub Actions: every check is local.

## Quick run: `python scripts/ci_local.py`

```text
stage                  result  seconds
structure              pass        3.8
env                    pass        0.3
secrets                pass        1.5
slop                   pass        0.1
ruff                   pass        0.2
ruff-format            pass        0.1
mypy                   pass        0.5
python-tests           pass        1.6
frontend-lint          pass        2.4
frontend-typecheck     pass        1.6
frontend-test          pass        3.1
all stages passed
```

## Full run: `python scripts/ci_local.py --full`

```text
stage                  result  seconds
structure              pass        4.2
env                    pass        0.3
secrets                pass        1.5
slop                   pass        0.1
ruff                   pass        0.1
ruff-format            pass        0.1
mypy                   pass        0.5
python-tests-full      pass        2.6
frontend-lint          pass        2.8
frontend-typecheck     pass        1.6
frontend-coverage      pass        3.2
frontend-build         pass        2.2
contract-drift         pass        1.1
all stages passed
```

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

`cd app/frontend && npm audit --audit-level=high`

```text
11 moderate severity vulnerabilities
```

No high or critical finding. The 11 moderate findings are in the eslint toolchain (dev dependencies); they are not changed in Phase 1 and are handled in the Phase 6 audit.

## Gate 1 inputs (owner review)

Phase 1 is complete. Waiting for Gate 1. Please review:

| Item | Path |
|---|---|
| Station layout, coordinates, fictional location, equipment, pipe routes, instruments, emission anchors | `app/backend/plumetrace/facility/data/ks07.yaml` |
| Gas composition (`gas_composition` key) | `app/backend/plumetrace/facility/data/ks07.yaml` |
| Component counts (cited Subpart W W-1B table, with the proxy caveat) | `app/backend/plumetrace/facility/data/component_counts.yaml` |
| Emission sources (the 21 emission candidates: anchors with `emission_point: true`) | `app/backend/plumetrace/facility/data/ks07.yaml`, tabulated in `docs/reference/SIMULATOR.md` section "Emission candidates (21)" |

All of them are tabulated in `docs/reference/SIMULATOR.md` (section "Facility KS-07").
