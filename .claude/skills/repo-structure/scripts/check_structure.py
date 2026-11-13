"""Check that the PlumeTrace repository follows the layout in the repo-structure skill.

The checker enforces five things, each in its own module next to this one:

1. ``layout_checks``: only allowed entries exist at each structural level (repository root,
   ``app/``, the backend/agents packages, ``app/frontend/src`` and its features).
2. ``layout_checks``: source files live only in their homes (Python in the backend, agents
   or scripts; TypeScript in the frontend; SQL in ``app/supabase``) and no catch-all names
   such as ``utils.py``, ``manager.py`` or ``misc/`` are used.
3. ``import_checks``: ``plumetrace_agents`` never imports the backend package ``plumetrace``;
   only ``plumetrace.api`` and ``plumetrace.agent_tools`` import ``plumetrace_agents``.
4. ``import_checks``: imports inside both packages follow the documented dependency direction.
5. ``size_checks``: no god files, i.e. line limits per file type plus function, class and
   top-level-definition limits for Python modules.

All rules are data in ``structure_config``.

Usage:
    python -I .claude/skills/repo-structure/scripts/check_structure.py <repo_root>

Exit code 0 and ``structure OK`` when the layout is valid; exit code 1 and one line per
problem otherwise. Folders that do not exist yet are skipped, so the checker can run from
the first commit onward.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ``python -I`` does not put the script's folder on sys.path; add it so the sibling
# check modules (and only they) can be imported.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_checks import check_imports  # noqa: E402
from layout_checks import check_levels, check_placement  # noqa: E402
from size_checks import check_sizes  # noqa: E402


def main(argv: list[str]) -> int:
    """Run all checks and print the result.

    Args:
        argv: Command-line arguments; ``argv[1]`` is the repository root.

    Returns:
        int: 0 when the structure is valid, 1 otherwise.
    """
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    problems = (check_levels(root) + check_placement(root) + check_imports(root)
                + check_sizes(root))
    if problems:
        for problem in problems:
            print(problem)
        return 1
    print("structure OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
