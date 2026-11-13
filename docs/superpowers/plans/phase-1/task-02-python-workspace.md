# Phase 1 · Task 2 — Python uv workspace and package skeletons

**Read first:** `phase-1/README.md` (pinned versions). **Skills:** `plan-execution`, `repo-structure`, `project-documentation`.

**Goal:** one uv workspace rooted at `app/` with two installable packages — backend `plumetrace`
(depends on the agents package) and agents `plumetrace_agents` (depends on no project package) —
plus ruff, mypy and pytest configured exactly once at the workspace root.

## Files
| Action | Path |
|---|---|
| Create | `app/pyproject.toml`, `app/.python-version` |
| Create | `app/backend/pyproject.toml`, `app/backend/plumetrace/__init__.py`, `app/backend/plumetrace/py.typed` (empty) |
| Create | `app/agents/pyproject.toml`, `app/agents/plumetrace_agents/__init__.py`, `app/agents/plumetrace_agents/py.typed` (empty) |
| Create | `app/backend/tests/test_package.py`, `app/agents/tests/test_package.py` |
| Generated | `app/uv.lock`, `app/.venv/` (ignored) |

**Important:** test folders have **no** `__init__.py` (pytest runs with `--import-mode=importlib`,
so two `tests/test_package.py` files can coexist).

## Exact file contents

`app/.python-version`:
```text
3.12
```

`app/pyproject.toml`:
```toml
[project]
name = "plumetrace-workspace"
version = "0.1.0"
description = "PlumeTrace uv workspace root (not a package)."
requires-python = ">=3.12,<3.13"
dependencies = ["plumetrace", "plumetrace-agents"]

[tool.uv]
package = false

[tool.uv.workspace]
members = ["backend", "agents"]

[tool.uv.sources]
plumetrace = { workspace = true }
plumetrace-agents = { workspace = true }

[dependency-groups]
dev = [
    "pytest==9.2.0",
    "ruff==0.17.5",
    "mypy==2.4.1",
    "types-PyYAML==6.0.12.20261111",
    "pip-audit==2.10.1",
    "hypothesis==6.170.14",
    "pytest-cov==7.1.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "D", "S", "ANN", "N"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.isort]
known-first-party = ["plumetrace", "plumetrace_agents", "evals"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101", "ANN"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
packages = ["plumetrace", "plumetrace_agents"]

[tool.pytest.ini_options]
testpaths = ["backend/tests", "agents/tests"]
addopts = "--import-mode=importlib"
pythonpath = ["backend"]
markers = [
    "db: needs the local Supabase Postgres (see docs/LOCAL_DEVELOPMENT.md)",
    "slow: longer than ~5 s; skipped by the quick local checks (scripts/ci_local.py)",
    "fuzz: Schemathesis API fuzzing (Phase 6); full local checks only",
]

[tool.coverage.run]
branch = true
source = ["plumetrace", "plumetrace_agents"]

[tool.coverage.report]
exclude_also = ["if __name__ == .__main__.:", "raise NotImplementedError"]
```

`app/backend/pyproject.toml`:
```toml
[project]
name = "plumetrace"
version = "0.1.0"
description = "PlumeTrace backend: engineering core, facility, simulator, data access and API."
requires-python = ">=3.12,<3.13"
dependencies = [
    "pydantic==2.14.3",
    "pydantic-settings==2.16.2",
    "pyyaml==6.0.3",
    "psycopg[binary,pool]==3.3.9",
    "psycopg-pool==3.3.3",
    "plumetrace-agents",
]

[tool.uv.sources]
plumetrace-agents = { workspace = true }

[build-system]
requires = ["hatchling==1.33.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["plumetrace"]
```

`app/agents/pyproject.toml`:
```toml
[project]
name = "plumetrace-agents"
version = "0.1.0"
description = "PlumeTrace LangGraph agents. Never imports the backend package."
requires-python = ">=3.12,<3.13"
dependencies = ["pydantic==2.14.3"]

[build-system]
requires = ["hatchling==1.33.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["plumetrace_agents"]
```

`app/backend/plumetrace/__init__.py`:
```python
"""PlumeTrace backend package.

Holds the engineering core (pure physics), the KS-07 facility spec, the simulator, database
access, the agent-tool implementations and the FastAPI application. The agents package
(``plumetrace_agents``) is a dependency; it never imports this package.
"""

__version__ = "0.1.0"
```

`app/agents/plumetrace_agents/__init__.py`:
```python
"""PlumeTrace agents package (LangGraph).

Builds the agent graph from injected tools, chat model and checkpointer. It never imports the
backend package ``plumetrace``; the backend depends on this package, not the other way round.
"""

__version__ = "0.1.0"
```

## Tests (full code)

`app/backend/tests/test_package.py`:
```python
"""Smoke tests for the backend package installation."""


def test_backend_package_imports_and_has_version() -> None:
    """The backend package is installed in the workspace and exposes its version."""
    import plumetrace

    assert plumetrace.__version__ == "0.1.0"


def test_backend_can_import_agents_package() -> None:
    """The dependency direction backend -> agents is installable."""
    import plumetrace_agents

    assert plumetrace_agents.__version__ == "0.1.0"
```

`app/agents/tests/test_package.py`:
```python
"""Smoke tests for the agents package installation."""


def test_agents_package_imports_and_has_version() -> None:
    """The agents package is installed in the workspace and exposes its version."""
    import plumetrace_agents

    assert plumetrace_agents.__version__ == "0.1.0"
```

## Steps
- [ ] **1.** Create the two test files first, then all other files above with exactly the shown content.
- [ ] **2.** `cd app && uv sync` → creates `.venv` and `uv.lock` without errors.
- [ ] **3.** `uv run pytest -q` → `3 passed`.
- [ ] **4.** `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → no changes needed (run `uv run ruff format .` once if it reports files, then re-check).
- [ ] **5.** `uv run mypy` → `Success: no issues found`.
- [ ] **6.** Repo checks (from repo root): `check_structure.py` → `structure OK`; `check_env.py` → `env OK`; `secret_scan.py` → `no secrets found`.
- [ ] **7. Docs.** In `docs/LOCAL_DEVELOPMENT.md` → `## Python`: `cd app`, `uv sync`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format .`, `uv run mypy`; note "tests use `--import-mode=importlib`; test folders have no `__init__.py`". Work-log row; `STATUS.md` (last 1.2, next 1.3).
- [ ] **8. Commit** `feat(workspace): add uv workspace with backend and agents packages` (stage `app/` files and docs; `uv.lock` included; `.venv` must not be staged).

## Done when
3 tests pass; ruff, ruff format, mypy and the repo checks are clean.
