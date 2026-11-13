""""No god files" checks: line limits per file type and Python definition limits."""

from __future__ import annotations

import ast
from pathlib import Path

from layout_checks import walk_files
from structure_config import GENERATED_PREFIXES, LIMITS, SIZE_EXCEPTIONS


def _is_test(posix: str, name: str) -> bool:
    """Tell whether a file is a test module.

    Args:
        posix: Path relative to the repository root, with forward slashes.
        name: The file name.

    Returns:
        bool: True for ``test_*.py``, ``*.test.ts(x)``, files under ``tests/`` or ``e2e/``.
    """
    return (name.startswith("test_") or ".test." in name
            or "/tests/" in f"/{posix}" or "/e2e/" in f"/{posix}")


def file_limit(posix: str, path: Path) -> int | None:
    """Return the line limit that applies to a file, or None when no limit applies.

    Args:
        posix: Path relative to the repository root, with forward slashes.
        path: The file path (used for its name and suffix).

    Returns:
        int | None: The maximum number of lines, or None for unlimited files.
    """
    if posix.startswith(GENERATED_PREFIXES):
        return None
    if posix in SIZE_EXCEPTIONS:
        return SIZE_EXCEPTIONS[posix][0]
    test = _is_test(posix, path.name)
    if path.suffix == ".py":
        return LIMITS["py_test"] if test else LIMITS["py_source"]
    if path.suffix in {".ts", ".tsx"}:
        return LIMITS["ts_test"] if test else LIMITS["ts_source"]
    if path.suffix == ".sql":
        return LIMITS["sql"]
    if path.suffix == ".md" and "/prompts/" in posix:
        return LIMITS["prompt_md"]
    return None


def python_definition_problems(source: str, posix: str) -> list[str]:
    """Check function, class and top-level-definition limits in one Python module.

    Args:
        source: Python source code.
        posix: Path relative to the repository root, for messages.

    Returns:
        list[str]: One message per definition that exceeds a limit.

    Raises:
        SyntaxError: If ``source`` is not valid Python.
    """
    problems: list[str] = []
    tree = ast.parse(source)
    definition_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    top_defs = [n for n in tree.body if isinstance(n, definition_types)]
    if not _is_test(posix, posix.rsplit("/", 1)[-1]) and len(top_defs) > LIMITS["py_top_level_defs"]:
        problems.append(f"god file: {posix} has {len(top_defs)} top-level functions/classes "
                        f"(limit {LIMITS['py_top_level_defs']}); split by responsibility")
    for node in ast.walk(tree):
        if not isinstance(node, definition_types):
            continue
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        is_class = isinstance(node, ast.ClassDef)
        limit = LIMITS["py_class"] if is_class else LIMITS["py_function"]
        if length > limit:
            kind = "class" if is_class else "function"
            problems.append(f"god {kind}: {node.name} in {posix} is {length} lines (limit {limit})")
    return problems


def check_sizes(root: Path) -> list[str]:
    """Enforce the "no god files" limits on every checked file.

    Args:
        root: Repository root directory.

    Returns:
        list[str]: One message per file, function or class over its limit.
    """
    problems: list[str] = []
    for path in walk_files(root):
        posix = path.relative_to(root).as_posix()
        limit = file_limit(posix, path)
        if limit is None:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = len(text.splitlines())
        if lines > limit:
            problems.append(f"god file: {posix} is {lines} lines (limit {limit}); split it")
        if path.suffix == ".py":
            try:
                problems += python_definition_problems(text, posix)
            except SyntaxError:
                pass  # parse errors in package files are reported by import_checks
    return problems
