"""Install the git pre-commit hook that runs the quick local checks (scripts/ci_local.py)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = (
    "#!/bin/sh\n"
    "# Installed by scripts/install_git_hooks.py: quick local checks before every commit.\n"
    "# GitHub Actions are not used; never bypass this hook with --no-verify.\n"
    "exec python scripts/ci_local.py\n"
)


def main() -> int:
    """Write .git/hooks/pre-commit; refuse to overwrite a different existing hook."""
    hooks = ROOT / ".git" / "hooks"
    if not hooks.is_dir():
        print("not a git repository: run git init first")
        return 1
    target = hooks / "pre-commit"
    if target.exists() and target.read_text(encoding="utf-8") != HOOK:
        print(f"a different pre-commit hook exists; not overwritten: {target}")
        return 1
    target.write_bytes(HOOK.encode("utf-8"))
    target.chmod(0o755)
    print("installed .git/hooks/pre-commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
