"""Download the pinned Poly Haven CC0 assets listed in ``scripts/blender/polyhaven_manifest.json``.

Textures go to the git-ignored ``build/polyhaven/<id>/``; the HDRI used at runtime goes to
``app/frontend/public/textures/env/`` (committed). Only ``https://dl.polyhaven.org/`` URLs are
accepted. Files that already exist with the recorded SHA-256 are skipped.

Run it from the repo root::

    cd app && uv run python ../scripts/fetch_polyhaven.py --record   # first time: records hashes
    cd app && uv run python ../scripts/fetch_polyhaven.py            # later: verifies hashes

Assets: Poly Haven (polyhaven.com), licence CC0.
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

import httpx

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
MANIFEST: Final[Path] = ROOT / "scripts" / "blender" / "polyhaven_manifest.json"
API: Final = "https://api.polyhaven.com/files"
ALLOWED_PREFIX: Final = "https://dl.polyhaven.org/"
HEADERS: Final = {"User-Agent": "PlumeTrace-asset-fetch/1.0"}
TEXTURE_DIR: Final[Path] = ROOT / "build" / "polyhaven"
HDRI_DIR: Final[Path] = ROOT / "app" / "frontend" / "public" / "textures" / "env"


class FetchError(Exception):
    """A download was refused or a recorded hash did not match."""


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_downloads(client: httpx.Client, manifest: dict[str, Any]) -> list[tuple[str, Path]]:
    """Resolve every manifest entry to a ``(url, target path)`` pair via the Poly Haven API.

    Args:
        client: HTTP client.
        manifest: The parsed manifest.

    Returns:
        The downloads, textures first, then HDRIs.

    Raises:
        FetchError: If a URL is not on ``dl.polyhaven.org``.
    """
    res = manifest["resolution"]
    jobs: list[tuple[str, Path]] = []
    for asset, maps in manifest["textures"].items():
        files = client.get(f"{API}/{asset}").raise_for_status().json()
        jobs += [(files[m][res]["jpg"]["url"], TEXTURE_DIR / asset) for m in maps]
    for asset, fmt in manifest["hdris"].items():
        files = client.get(f"{API}/{asset}").raise_for_status().json()
        jobs.append((files["hdri"][res][fmt]["url"], HDRI_DIR))
    for url, _ in jobs:
        if not url.startswith(ALLOWED_PREFIX):
            raise FetchError(f"refusing URL outside {ALLOWED_PREFIX}: {url}")
    return [(url, folder / url.rsplit("/", 1)[1]) for url, folder in jobs]


def fetch_one(client: httpx.Client, url: str, target: Path, recorded: str | None) -> str:
    """Download one file unless it already matches its recorded hash; verify the hash.

    Args:
        client: HTTP client.
        url: Source URL (already checked).
        target: Destination file.
        recorded: Recorded SHA-256, or ``None`` when none is recorded yet.

    Returns:
        The SHA-256 of the file on disk.

    Raises:
        FetchError: If the file's hash differs from the recorded one.
    """
    rel = target.relative_to(ROOT).as_posix()
    if not (target.exists() and recorded and sha256_of(target) == recorded):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(client.get(url).raise_for_status().content)
    digest = sha256_of(target)
    if recorded and digest != recorded:
        raise FetchError(f"hash mismatch: {rel}")
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    """Fetch the assets; with ``--record`` write their hashes into the manifest.

    Args:
        argv: Command-line arguments (default: ``sys.argv``).

    Returns:
        0 on success, 1 on a refused URL, a hash mismatch or a failed request.
    """
    parser = argparse.ArgumentParser(description="Fetch the pinned Poly Haven CC0 assets.")
    parser.add_argument(
        "--record", action="store_true", help="write SHA-256 values to the manifest"
    )
    args = parser.parse_args(argv)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    hashes: dict[str, str] = dict(manifest["sha256"])
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=60.0) as client:
            for url, target in plan_downloads(client, manifest):
                rel = target.relative_to(ROOT).as_posix()
                known = None if args.record else hashes.get(rel)
                digest = fetch_one(client, url, target, known)
                hashes[rel] = digest
                print(f"ok {rel}")
    except (FetchError, httpx.HTTPError) as exc:
        print(f"fetch failed: {exc}", file=sys.stderr)
        return 1
    if args.record:
        manifest["sha256"] = dict(sorted(hashes.items()))
        text = json.dumps(manifest, indent=2) + "\n"
        MANIFEST.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
