"""Scan PlumeTrace frontend source for detectable "AI slop" patterns.

Implements the detectable part of `references/anti-slop.md`: gradients and gradient text,
glassmorphism, neon glows, emoji and "AI sparkle" icons, purple accents, decorative infinite
animations, marketing filler copy and placeholder text. Visual judgement still needs the
screenshot critique described in that reference; this script only catches the obvious tells.

Usage:
    python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src

Exit code 0 prints ``no slop found``; exit code 1 prints ``path:line: rule`` per finding.
A line may opt out of one rule with a trailing comment ``slop-ok: <rule> <reason>`` — only for
the documented exceptions (data colour ramps, 3D sky, the single live-alarm indicator).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCANNED_SUFFIXES = {".ts", ".tsx", ".css", ".html"}
SKIP_PARTS = {"node_modules", "dist", "generated"}

RULES: dict[str, re.Pattern[str]] = {
    "gradient": re.compile(r"bg-gradient-|conic-gradient|radial-gradient|linear-gradient\("),
    "gradient-text": re.compile(r"bg-clip-text|text-transparent"),
    "glassmorphism": re.compile(r"backdrop-filter|backdrop-blur"),
    "neon-glow": re.compile(r"shadow-\[0_0_|drop-shadow-\[0_0_|0 0 \d+px (?:rgba?\(|#)"),
    "purple-accent": re.compile(r"\b(?:purple|violet|fuchsia)-\d{2,3}\b"),
    "infinite-animation": re.compile(r"animate-(?:pulse|bounce|ping)\b"),
    "ai-sparkle-icon": re.compile(r"\b(?:Sparkles?|Wand2?|WandSparkles|Bot|BrainCircuit)\b"),
    "emoji": re.compile("[\U0001F300-\U0001FAFF✨⭐⚡]"),
    "filler-copy": re.compile(
        r"(?i)\b(?:unlock|supercharge|seamless(?:ly)?|revolutioni[sz]e|elevate|harness the power"
        r"|cutting-edge|next-generation|game-?changer|welcome back)\b"
    ),
    "placeholder-text": re.compile(r"(?i)lorem ipsum|john doe|jane doe|acme corp"),
}

OPT_OUT = re.compile(r"slop-ok:\s*([a-z-]+)")


def scan_file(path: Path) -> list[str]:
    """Return slop findings for one source file.

    Args:
        path: File to scan.

    Returns:
        list[str]: Findings formatted as ``path:line: rule``.
    """
    findings: list[str] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for number, line in enumerate(text.splitlines(), start=1):
        allowed = set(OPT_OUT.findall(line))
        for rule, pattern in RULES.items():
            if rule not in allowed and pattern.search(line):
                findings.append(f"{path.as_posix()}:{number}: {rule}")
    return findings


def iter_sources(roots: list[Path]):
    """Yield frontend source files under the given roots.

    Args:
        roots: Files or folders to scan.

    Yields:
        Path: Each ``.ts``, ``.tsx``, ``.css`` or ``.html`` file outside skipped folders.
    """
    for root in roots:
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if (path.is_file() and path.suffix in SCANNED_SUFFIXES
                    and not SKIP_PARTS.intersection(path.parts)):
                yield path


def main(argv: list[str]) -> int:
    """Scan the paths given on the command line.

    Args:
        argv: Command-line arguments; ``argv[1:]`` are files or folders.

    Returns:
        int: 0 when no slop is found, 1 when findings exist, 2 on bad arguments.
    """
    if len(argv) < 2:
        print(__doc__)
        return 2
    roots = [Path(arg) for arg in argv[1:]]
    findings = [f for path in iter_sources(roots) for f in scan_file(path)]
    for finding in findings:
        print(finding)
    if findings:
        return 1
    print("no slop found")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
