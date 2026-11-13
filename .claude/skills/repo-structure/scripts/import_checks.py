"""Dependency-direction checks for the ``plumetrace`` and ``plumetrace_agents`` packages."""

from __future__ import annotations

import ast
from pathlib import Path

from structure_config import AGENTS_ALLOWED, BACKEND_ALLOWED, BACKEND_MAY_IMPORT_AGENTS, CACHE_DIRS


def internal_imports(source: str, package: str) -> set[str]:
    """Return the first-level sub-modules of ``package`` that a source file imports.

    Args:
        source: Python source code.
        package: Top-level package name, e.g. ``"plumetrace"``.

    Returns:
        set[str]: Sub-module names, e.g. ``{"engineering", "db"}``. A bare
        ``import package`` yields ``{"__init__"}``.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            parts = name.split(".")
            if parts[0] == package:
                found.add(parts[1] if len(parts) > 1 else "__init__")
    return found


def _owner(rel_to_package: Path) -> str:
    """Return the sub-package or module name that owns a file inside a package.

    Args:
        rel_to_package: File path relative to the package folder.

    Returns:
        str: ``"engineering"`` for ``engineering/plume.py``, ``"graph"`` for ``graph.py``.
    """
    first = rel_to_package.parts[0]
    return first[:-3] if first.endswith(".py") else first


def _file_problems(source: str, package: str, owner: str, shown: str,
                   allowed: dict[str, set[str] | None]) -> list[str]:
    """Return the import violations of one module.

    Args:
        source: Python source of the module.
        package: Package being checked (``plumetrace`` or ``plumetrace_agents``).
        owner: Sub-package or module that owns the file.
        shown: Repository-relative path for messages.
        allowed: Allowed internal imports per owner; None means unrestricted.

    Returns:
        list[str]: One message per violation.
    """
    problems: list[str] = []
    own = internal_imports(source, package)
    if package == "plumetrace_agents" and internal_imports(source, "plumetrace"):
        problems.append(f"forbidden import: plumetrace_agents must not import plumetrace ({shown})")
    if (package == "plumetrace" and internal_imports(source, "plumetrace_agents")
            and owner not in BACKEND_MAY_IMPORT_AGENTS):
        problems.append(f"forbidden import: plumetrace.{owner} -> plumetrace_agents ({shown}); "
                        f"only api and agent_tools may")
    rule = allowed.get(owner, set())
    if rule is not None:
        for bad in sorted(own - rule - {owner}):
            problems.append(f"forbidden import: {package}.{owner} -> {package}.{bad} ({shown})")
    return problems


def _check_package(root: Path, package_dir: Path, package: str,
                   allowed: dict[str, set[str] | None]) -> list[str]:
    """Check internal and cross-package imports for one package.

    Args:
        root: Repository root directory (for readable paths).
        package_dir: Folder of the package being checked.
        package: Its import name (``plumetrace`` or ``plumetrace_agents``).
        allowed: Allowed internal imports per owner; None means unrestricted.

    Returns:
        list[str]: One message per violation; empty when the package is absent.
    """
    problems: list[str] = []
    if not package_dir.is_dir():
        return problems
    for path in package_dir.rglob("*.py"):
        rel = path.relative_to(package_dir)
        if any(part in CACHE_DIRS for part in rel.parts):
            continue
        shown = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            problems += _file_problems(source, package, _owner(rel), shown, allowed)
        except SyntaxError as exc:
            problems.append(f"cannot parse {shown}: {exc}")
    return problems


def check_imports(root: Path) -> list[str]:
    """Check the dependency direction for both Python packages.

    Args:
        root: Repository root directory.

    Returns:
        list[str]: One problem per forbidden import; empty when the direction holds.
    """
    return (_check_package(root, root / "app/backend/plumetrace", "plumetrace", BACKEND_ALLOWED)
            + _check_package(root, root / "app/agents/plumetrace_agents", "plumetrace_agents",
                             AGENTS_ALLOWED))
