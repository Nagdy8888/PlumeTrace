"""Enforce the single-.env rule for PlumeTrace without ever printing a value.

Checks:

1. **One env file.** The only env files in the repository are the root ``.env`` (local,
   git-ignored) and the root ``.env.example`` (committed, names only). Any other ``.env*``
   file anywhere (``app/backend/.env``, ``app/frontend/.env.local``, ``app/supabase/.env``,
   a ``.env.local`` pulled by ``vercel env pull`` ...) is a finding.
2. **Names in sync.** Every variable name in ``.env`` is listed in ``.env.example`` and vice
   versa, so a new secret can never exist only on one machine.
3. **Example holds no secrets.** Values in ``.env.example`` are empty, except an allowlist of
   non-secret defaults (``LANGSMITH_TRACING``, ``LANGSMITH_PROJECT`` and the public local
   Supabase default URL).
4. **Required values present.** Every variable listed in ``.env.example`` has a non-empty value
   in ``.env`` (reported by name only).

Usage:
    python -I .claude/skills/security-checks/scripts/check_env.py <repo_root>

Exit code 0 prints ``env OK``; exit code 1 lists findings (names and paths only).
"""

from __future__ import annotations

import sys
from pathlib import Path

ALLOWED_ENV_FILES = {".env", ".env.example"}
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "skills"}
NON_SECRET_EXAMPLE_VALUES = {
    "LANGSMITH_TRACING": None,  # any value allowed
    "LANGSMITH_PROJECT": None,
    "SUPABASE_DB_URL": "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
}


def parse_env(path: Path) -> dict[str, str]:
    """Parse ``NAME=value`` lines of a dotenv file.

    Args:
        path: Dotenv file to read. A missing file yields an empty mapping.

    Returns:
        dict[str, str]: Variable name to stripped value (quotes removed).
    """
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip().removeprefix("export ").strip()] = value.strip().strip("'\"")
    return values


def stray_env_files(root: Path) -> list[str]:
    """Find env files other than the root ``.env`` and ``.env.example``.

    Args:
        root: Repository root directory.

    Returns:
        list[str]: One finding per stray env file.
    """
    findings: list[str] = []
    for path in root.rglob(".env*"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        if len(rel.parts) > 1 or rel.name not in ALLOWED_ENV_FILES:
            findings.append(f"stray env file (move its variables to the root .env): {rel.as_posix()}")
    return findings


def example_problems(example: dict[str, str]) -> list[str]:
    """Check that ``.env.example`` holds names only, apart from allowed defaults.

    Args:
        example: Parsed ``.env.example``.

    Returns:
        list[str]: One finding per variable whose example value looks like a secret.
    """
    findings: list[str] = []
    for name, value in example.items():
        if not value or name in NON_SECRET_EXAMPLE_VALUES and (
                NON_SECRET_EXAMPLE_VALUES[name] in (None, value)):
            continue
        findings.append(f".env.example must not contain a value for {name}")
    return findings


def sync_problems(env: dict[str, str], example: dict[str, str]) -> list[str]:
    """Compare variable names between ``.env`` and ``.env.example`` and check required values.

    Args:
        env: Parsed local ``.env``.
        example: Parsed ``.env.example``.

    Returns:
        list[str]: Findings naming variables only, never values.
    """
    findings = [f"{name} is in .env but missing from .env.example" for name in sorted(env.keys() - example.keys())]
    findings += [f"{name} is in .env.example but missing from .env" for name in sorted(example.keys() - env.keys())]
    findings += [f"{name} is empty in .env" for name in sorted(example.keys() & env.keys()) if not env[name]]
    return findings


def main(argv: list[str]) -> int:
    """Run all env checks for the repository root given on the command line.

    Args:
        argv: Command-line arguments; ``argv[1]`` is the repository root.

    Returns:
        int: 0 when every check passes, 1 otherwise.
    """
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    env = parse_env(root / ".env")
    example = parse_env(root / ".env.example")
    findings = stray_env_files(root) + example_problems(example)
    if not (root / ".env.example").is_file():
        findings.append(".env.example is missing at the repository root")
    if (root / ".env").is_file():
        findings += sync_problems(env, example)
    for finding in findings:
        print(finding)
    if findings:
        return 1
    print("env OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
