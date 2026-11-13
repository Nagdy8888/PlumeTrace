"""Scan files for leaked secrets without ever printing a secret value.

Two detectors run over every text file in the given paths:

1. **Known values:** every value in the repository's ``.env`` that is at least
   12 characters long is searched for literally. A hit means a real key leaked.
2. **Key patterns:** regular expressions for OpenAI keys, LangSmith keys, AWS
   access keys, private-key blocks and ``*_API_KEY=<value>`` assignments.

Only the file path, line number and detector name (or env variable name) are
printed, never the matched text.

Usage:
    python -I .claude/skills/security-checks/scripts/secret_scan.py <path> [<path> ...]

The ``.env`` file is located by walking up from this script to the repository
root (the folder containing ``CLAUDE.md``). Exit code 0 prints ``no secrets
found``; exit code 1 lists findings; exit code 2 means a bad argument.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = {
    # Look-behind: "task-05-..." must not match as "sk-05-...".
    "openai-key": re.compile(r"(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}"),
    "langsmith-key": re.compile(r"(?<![A-Za-z0-9_])lsv2_(?:pt|sk)_[A-Za-z0-9_]{20,}"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private-key-block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "api-key-assignment": re.compile(
        r"(?i)\b[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}"
    ),
}

PLACEHOLDER = re.compile(r"(?i)your[_-]|_here\b|example|placeholder|xxxx|<[^>]*>|\.\.\.")

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    ".coverage",
}
SKIP_FILES = {".env"}
MAX_BYTES = 5_000_000
MIN_VALUE_LEN = 12
# Settings that are not secret and may legitimately appear in docs and .env.example.
NON_SECRET_NAMES = {"LANGSMITH_TRACING", "LANGSMITH_PROJECT"}
# Publicly documented local-development defaults (Supabase CLI local Postgres). A value that
# differs from these (e.g. a hosted database URL with a real password) is still treated as secret.
PUBLIC_DEFAULT_VALUES = {"postgresql://postgres:postgres@127.0.0.1:54322/postgres"}


def find_repo_root(start: Path) -> Path | None:
    """Return the nearest ancestor folder that contains ``CLAUDE.md``.

    Args:
        start: Folder to start searching from.

    Returns:
        Path | None: The repository root, or None when no ``CLAUDE.md`` is found.
    """
    for folder in [start, *start.parents]:
        if (folder / "CLAUDE.md").is_file():
            return folder
    return None


def load_env_values(env_path: Path) -> dict[str, str]:
    """Read ``NAME=value`` pairs from a dotenv file, keeping only long values.

    Args:
        env_path: Path to the ``.env`` file. A missing file yields no values.

    Returns:
        dict[str, str]: Variable name to value, for values of at least
        ``MIN_VALUE_LEN`` characters (short values such as ``true`` would cause
        false positives), excluding ``NON_SECRET_NAMES`` and ``PUBLIC_DEFAULT_VALUES``.
    """
    values: dict[str, str] = {}
    if not env_path.is_file():
        return values
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip("'\"")
        if name in NON_SECRET_NAMES or value in PUBLIC_DEFAULT_VALUES:
            continue
        if len(value) >= MIN_VALUE_LEN:
            values[name] = value
    return values


def iter_files(paths: list[Path]):
    """Yield readable files under the given paths, skipping vendored folders.

    Args:
        paths: Files or folders to scan.

    Yields:
        Path: Each file to scan.
    """
    for base in paths:
        if base.is_file():
            if base.name not in SKIP_FILES:
                yield base
            continue
        for path in base.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.name not in SKIP_FILES and path.stat().st_size <= MAX_BYTES:
                yield path


def scan_file(path: Path, env_values: dict[str, str]) -> list[str]:
    """Scan one file and describe each finding without revealing the secret.

    Args:
        path: File to scan.
        env_values: Real secret values from ``.env`` keyed by variable name.

    Returns:
        list[str]: Findings formatted as ``path:line: detector``.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for name, value in env_values.items():
            if value in line:
                findings.append(f"{path}:{number}: real value of {name} from .env")
        for detector, pattern in PATTERNS.items():
            match = pattern.search(line)
            # Documentation placeholders such as ``lsv2_pt_your_api_key_here`` are not secrets.
            if match and not PLACEHOLDER.search(match.group(0)):
                findings.append(f"{path}:{number}: {detector}")
    return findings


def main(argv: list[str]) -> int:
    """Scan the paths given on the command line.

    Args:
        argv: Command-line arguments; ``argv[1:]`` are files or folders.

    Returns:
        int: 0 when clean, 1 when findings exist, 2 on bad arguments.
    """
    if len(argv) < 2:
        print(__doc__)
        return 2
    paths = [Path(arg).resolve() for arg in argv[1:]]
    missing = [str(p) for p in paths if not p.exists()]
    paths = [p for p in paths if p.exists()]
    root = find_repo_root(Path(__file__).resolve().parent)
    env_values = load_env_values(root / ".env") if root else {}
    findings = [f for path in iter_files(paths) for f in scan_file(path, env_values)]
    for path in missing:
        print(f"skipped (does not exist): {path}")
    if findings:
        for finding in findings:
            print(finding)
        return 1
    print("no secrets found")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
