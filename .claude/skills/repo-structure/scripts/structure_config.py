"""Allowlists, dependency rules and size limits for the PlumeTrace structure checker.

Every rule the checker enforces is data in this module, so changing the repository layout
means changing this file and the repo-structure skill together (rule 2 of the skill).
"""

from __future__ import annotations

CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "node_modules", "dist",
              ".mypy_cache", ".vercel", ".temp", ".branches", ".hypothesis", ".coverage",
              "htmlcov", "coverage", "test-results", "playwright-report"}

SKIP_TOP = {".git", "skills", ".claude"}

# Allowed children per structural folder (relative to repo root). Cache folders are always allowed.
# No ".github": GitHub Actions are not used (owner decision 2026-11-13, billing); every check runs
# locally with scripts/ci_local.py and the git pre-commit hook.
ALLOWED_CHILDREN: dict[str, set[str]] = {
    ".": {".claude", ".git", ".gitignore", ".gitattributes", ".env", ".env.example",
          ".vscode",
          ".ux-profile.md", "CLAUDE.md", "README.md", "LICENSE", "app", "docs", "scripts",
          "skills", "build"},
    "app": {"pyproject.toml", "uv.lock", ".python-version", "README.md",
            "backend", "agents", "frontend", "supabase", "replay"},
    "app/backend": {"pyproject.toml", "README.md", "plumetrace", "benchmark", "tests"},
    "app/backend/plumetrace": {"__init__.py", "config.py", "py.typed", "engineering", "facility",
                               "simulator", "rules", "data_sources", "db", "agent_tools",
                               "reports", "api"},
    "app/agents": {"pyproject.toml", "README.md", "plumetrace_agents", "evals", "tests"},
    "app/agents/plumetrace_agents": {"__init__.py", "py.typed", "graph.py", "state.py",
                                     "routing.py", "llm.py", "checkpoint.py", "tracing.py",
                                     "export_trace.py", "nodes", "tools", "schemas", "prompts"},
    "app/frontend/src": {"main.tsx", "vite-env.d.ts", "app", "features", "shared", "styles"},
    "app/frontend/src/features": {"station3d", "alarms", "agentPanel", "trends", "kpis",
                                  "approval", "scenarios", "reports"},
    "app/replay": {"scenarios", "traces"},
}

BANNED_NAMES = {"utils.py", "helpers.py", "misc.py", "common.py", "utils.ts", "helpers.ts",
                "manager.py", "service.py", "core.py", "handlers.py", "Main.tsx"}
BANNED_DIRS = {"misc", "common", "temp", "tmp", "helpers", "utils"}

# Allowed internal imports per backend sub-package (None = anything).
BACKEND_ALLOWED: dict[str, set[str] | None] = {
    "engineering": set(),
    "facility": {"engineering"},
    "simulator": {"engineering", "facility"},
    "rules": {"engineering", "facility"},
    "data_sources": {"engineering", "facility", "config"},
    "reports": {"engineering", "facility"},
    "db": {"config", "engineering"},
    "agent_tools": {"engineering", "facility", "simulator", "rules", "db", "config"},
    "api": None,
}
BACKEND_MAY_IMPORT_AGENTS = {"api", "agent_tools"}

# Allowed internal imports per agents sub-package / module (None = anything).
AGENTS_ALLOWED: dict[str, set[str] | None] = {
    "schemas": {"schemas"},
    "tools": {"schemas", "tools"},
    "nodes": {"schemas", "state", "tools", "nodes", "llm", "prompts"},
    "state": {"schemas"},
    "routing": {"schemas", "state"},
    "llm": {"schemas"},
    "prompts": set(),
    "checkpoint": set(),
    "tracing": set(),
    "export_trace": {"schemas", "state"},
    "graph": None,
    "__init__": None,
}

# "No god files" limits. Lines are physical lines, docstrings included.
LIMITS = {
    "py_source": 300, "py_test": 500, "py_function": 50, "py_class": 200, "py_top_level_defs": 12,
    "ts_source": 250, "ts_test": 400, "sql": 300, "prompt_md": 200,
}
# Owner-approved exceptions: {"relative/posix/path": (limit, "reason, YYYY-MM-DD")}.
SIZE_EXCEPTIONS: dict[str, tuple[int, str]] = {}
GENERATED_PREFIXES = ("app/frontend/src/shared/types/generated/", "app/replay/",
                      "app/frontend/public/models/")
