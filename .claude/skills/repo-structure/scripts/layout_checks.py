"""Folder allowlist and file-placement checks for the PlumeTrace structure checker."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from structure_config import (
    ALLOWED_CHILDREN,
    BANNED_DIRS,
    BANNED_NAMES,
    CACHE_DIRS,
    SKIP_TOP,
)


def is_skipped(rel: Path) -> bool:
    """Tell whether a path is inside a skipped, cache or vendored folder.

    Args:
        rel: Path relative to the repository root.

    Returns:
        bool: True when the path must not be checked.
    """
    parts = rel.parts
    return bool(parts) and (parts[0] in SKIP_TOP or any(p in CACHE_DIRS for p in parts))


def walk_files(root: Path) -> Iterator[Path]:
    """Yield every checkable file under ``root``.

    Args:
        root: Repository root directory.

    Yields:
        Path: Each file path outside skipped and cache folders.
    """
    for path in root.rglob("*"):
        if path.is_file() and not is_skipped(path.relative_to(root)):
            yield path


def check_levels(root: Path) -> list[str]:
    """Check the allowed children of every structural folder.

    Args:
        root: Repository root directory.

    Returns:
        list[str]: Human-readable problems; empty when every entry is allowed.
    """
    problems: list[str] = []
    for folder, allowed in ALLOWED_CHILDREN.items():
        path = root / folder
        if not path.is_dir():
            continue
        for child in path.iterdir():
            if child.name in allowed or child.name in CACHE_DIRS:
                continue
            where = "repository root" if folder == "." else f"{folder}/"
            problems.append(f"unexpected entry in {where}: {child.name}")
    return problems


def _placement_problem(posix: str, path: Path) -> str | None:
    """Return the home-folder problem for one file, if any.

    Args:
        posix: Path relative to the repository root, with forward slashes.
        path: The file path (used for its name and suffix).

    Returns:
        str | None: A message when the file is outside its home, else None.
    """
    if path.suffix == ".py" and not posix.startswith(("app/backend/", "app/agents/", "scripts/")):
        return f"Python file outside app/backend, app/agents or scripts: {posix}"
    if path.suffix in {".ts", ".tsx"} and not posix.startswith("app/frontend/"):
        return f"TypeScript file outside app/frontend: {posix}"
    if path.suffix == ".sql" and not posix.startswith("app/supabase/"):
        return f"SQL file outside app/supabase: {posix}"
    if path.suffix == ".md" and "/" in posix and path.name != "README.md":
        homes = ("docs/", "app/agents/plumetrace_agents/prompts/")
        if not posix.startswith(homes):
            return f"Markdown file outside docs/ (or agent prompts): {posix}"
    return None


def check_placement(root: Path) -> list[str]:
    """Check that files live in their homes and avoid catch-all names.

    Args:
        root: Repository root directory.

    Returns:
        list[str]: Human-readable problems; empty when placement is valid.
    """
    problems: list[str] = []
    for path in walk_files(root):
        rel = path.relative_to(root)
        posix = rel.as_posix()
        if path.name in BANNED_NAMES:
            problems.append(f"catch-all module name not allowed: {posix}")
        if any(part in BANNED_DIRS for part in rel.parts[:-1]):
            problems.append(f"catch-all folder not allowed: {posix}")
        problem = _placement_problem(posix, path)
        if problem:
            problems.append(problem)
    return problems
