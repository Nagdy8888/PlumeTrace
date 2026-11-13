"""Add or change variables in the root ``.env`` without ever printing a secret value.

The executor (any agent) changes ``.env`` **only** through this script. Opening ``.env`` with a
file-read or file-edit tool would load every secret into the conversation, so that is never done.
Every write keeps ``.env.example`` in sync (the name, with an empty value).

Commands (run from the repository root):

    python -I .claude/skills/security-checks/scripts/env_set.py names
        List every name in .env with "set" or "empty". Never prints a value.
    python -I .claude/skills/security-checks/scripts/env_set.py get NAME
        Print the value of a non-secret setting (NAME in NON_SECRET_SETTINGS only).
    python -I .claude/skills/security-checks/scripts/env_set.py set NAME VALUE
        Write a non-secret setting (NAME in NON_SECRET_SETTINGS), or SUPABASE_DB_URL back to the
        public local default. Refused for every other name: a secret never goes on a command line.
    python -I .claude/skills/security-checks/scripts/env_set.py add NAME [--comment TEXT]
        Add NAME with an empty value, for a secret only the owner can supply (an API key). The
        owner pastes the value into .env themselves.
    python -I .claude/skills/security-checks/scripts/env_set.py generate NAME [--bytes N]
        Write a new random secret (``secrets.token_urlsafe(N)``, default 32 bytes). The value is
        never printed; use it for secrets the project creates itself (local passwords, tokens).

Owner-only names (``OWNER_ONLY``) are refused by every write command, whatever the value.

Other code can import ``write_value(root, name, value)`` (see ``scripts/set_app_role_password.py``).

Exit code 0 prints one line naming what changed (names only); exit code 1 prints the reason.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path

NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
# Non-secret settings: their values may be shown and passed on the command line. When you add a
# new non-secret setting, add its name here AND to NON_SECRET_NAMES in secret_scan.py.
NON_SECRET_SETTINGS = frozenset(
    {
        "LANGSMITH_TRACING",
        "LANGSMITH_PROJECT",
        "OPENAI_MODEL_FAST",
        "OPENAI_MODEL_REASONING",
    }
)
# Only the owner changes these (CLAUDE.md rule 23: the executor never changes the spend cap).
OWNER_ONLY = frozenset({"PLUMETRACE_SPEND_CAP_USD"})
# Publicly documented Supabase CLI local default; the only value `set` accepts for this name.
PUBLIC_DEFAULTS = {"SUPABASE_DB_URL": "postgresql://postgres:postgres@127.0.0.1:54322/postgres"}


class EnvEditError(ValueError):
    """A refused or invalid ``.env`` change. The message names variables only, never values."""


def _check_name(name: str) -> None:
    """Refuse malformed and owner-only names.

    Args:
        name: Variable name to check.

    Raises:
        EnvEditError: The name is malformed or owner-only.
    """
    if not NAME_RE.fullmatch(name):
        raise EnvEditError(f"invalid variable name {name!r} (use UPPER_SNAKE_CASE)")
    if name in OWNER_ONLY:
        raise EnvEditError(f"{name} is owner-only: ask the owner to change it in the root .env")


def _read_lines(path: Path) -> tuple[list[str], str]:
    """Read a dotenv file as lines, keeping its line ending style.

    Args:
        path: File to read. A missing file yields no lines.

    Returns:
        tuple[list[str], str]: The lines without endings, and the newline in use.
    """
    if not path.is_file():
        return [], "\n"
    text = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.splitlines(), newline


def _line_name(line: str) -> str | None:
    """Return the variable name a dotenv line assigns, or ``None`` for comments and blanks."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.partition("=")[0].strip().removeprefix("export ").strip()


def _write_lines(path: Path, lines: list[str], newline: str) -> None:
    """Write lines atomically (temporary file in the same folder, then replace).

    Args:
        path: Target file.
        lines: Lines without endings.
        newline: Line ending to use.
    """
    data = (newline.join(lines) + newline).encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".envtmp-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _upsert(path: Path, name: str, value: str, comment: str | None) -> bool:
    """Set ``name=value`` in a dotenv file, replacing an existing line or appending one.

    Args:
        path: Dotenv file.
        name: Variable name.
        value: New value (written as is).
        comment: Optional comment line written above a newly appended name.

    Returns:
        bool: True when the name was added, False when an existing line was replaced.
    """
    lines, newline = _read_lines(path)
    for index, line in enumerate(lines):
        if _line_name(line) == name:
            lines[index] = f"{name}={value}"
            _write_lines(path, lines, newline)
            return False
    if comment:
        lines.append(f"# {comment}")
    lines.append(f"{name}={value}")
    _write_lines(path, lines, newline)
    return True


def write_value(root: Path, name: str, value: str, comment: str | None = None) -> bool:
    """Write one variable to the root ``.env`` and make sure ``.env.example`` lists its name.

    Args:
        root: Repository root (holds ``.env`` and ``.env.example``).
        name: Variable name (UPPER_SNAKE_CASE, not owner-only).
        value: Value to store; never printed or logged by this function.
        comment: Optional comment for a newly added name.

    Returns:
        bool: True when the name was new in ``.env``.

    Raises:
        EnvEditError: The name is refused or the value spans lines.
    """
    _check_name(name)
    if "\n" in value or "\r" in value:
        raise EnvEditError(f"the value for {name} must be a single line")
    added = _upsert(root / ".env", name, value, comment)
    example = root / ".env.example"
    if name not in {_line_name(line) for line in _read_lines(example)[0]}:
        _upsert(example, name, "", comment)
    return added


def _names(root: Path) -> list[str]:
    """List ``.env`` names with their state ("set" or "empty"), never values."""
    out = []
    for line in _read_lines(root / ".env")[0]:
        name = _line_name(line)
        if name is not None:
            value = line.partition("=")[2].strip().strip("'\"")
            out.append(f"{name} {'set' if value else 'empty'}")
    return out


def _get(root: Path, name: str) -> str:
    """Return a non-secret setting's value from ``.env``.

    Raises:
        EnvEditError: The name is not a non-secret setting or is not in ``.env``.
    """
    if name not in NON_SECRET_SETTINGS:
        raise EnvEditError(f"{name} is not a non-secret setting; its value is never printed")
    for line in _read_lines(root / ".env")[0]:
        if _line_name(line) == name:
            return line.partition("=")[2].strip().strip("'\"")
    raise EnvEditError(f"{name} is not in .env")


def _run(args: argparse.Namespace, root: Path) -> str:
    """Execute one parsed command and return the line to print (names only)."""
    if args.command == "names":
        return "\n".join(_names(root)) or ".env has no variables"
    if args.command == "get":
        return _get(root, args.name)
    _check_name(args.name)
    if args.command == "set":
        allowed = args.name in NON_SECRET_SETTINGS or PUBLIC_DEFAULTS.get(args.name) == args.value
        if not allowed:
            raise EnvEditError(
                f"{args.name} may hold a secret: use 'add' (owner fills it) or 'generate'"
            )
        added = write_value(root, args.name, args.value, args.comment)
    elif args.command == "add":
        if args.name in {line.split(" ")[0] for line in _names(root)}:
            return f"{args.name} is already in .env (unchanged)"
        write_value(root, args.name, "", args.comment)
        return f"added {args.name} (empty) to .env and .env.example: ask the owner to fill it"
    else:
        if not 16 <= args.bytes <= 64:
            raise EnvEditError("--bytes must be between 16 and 64")
        added = write_value(root, args.name, secrets.token_urlsafe(args.bytes), args.comment)
    return f"{'added' if added else 'updated'} {args.name} in .env (value not shown)"


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description="Change the root .env without printing secrets.")
    parser.add_argument("--root", default=".", help="repository root (default: current folder)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("names")
    sub.add_parser("get").add_argument("name")
    for command in ("set", "add", "generate"):
        cmd = sub.add_parser(command)
        cmd.add_argument("name")
        if command == "set":
            cmd.add_argument("value")
        if command == "generate":
            cmd.add_argument("--bytes", type=int, default=32)
        cmd.add_argument("--comment", default=None)
    return parser


def main(argv: list[str]) -> int:
    """Run the command given on the command line.

    Args:
        argv: Arguments without the program name.

    Returns:
        int: 0 on success, 1 when the change was refused.
    """
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        print(_run(args, root))
    except EnvEditError as error:
        print(f"refused: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
