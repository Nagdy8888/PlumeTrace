"""The secret scanner skips only the Supabase CLI cache and still detects key patterns."""

import importlib.util
from pathlib import Path
from types import ModuleType

from plumetrace.config import REPO_ROOT

# Built at run time so this file never matches the scanner itself.
FAKE_KEY = "sk-" + "Q7" * 12


def _load_scanner() -> ModuleType:
    """Import the security-checks secret_scan.py script as a module."""
    path = REPO_ROOT / ".claude/skills/security-checks/scripts/secret_scan.py"
    spec = importlib.util.spec_from_file_location("secret_scan", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: str) -> Path:
    """Create a file holding a fake key under ``root``."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"OPENAI={FAKE_KEY}\n", encoding="utf-8")
    return path


def test_supabase_cli_cache_is_skipped(tmp_path: Path) -> None:
    """app/supabase/.temp holds the CLI's public local keys and is the only skipped .temp."""
    mod = _load_scanner()
    cache = _write(tmp_path, "app/supabase/.temp/cli-latest")
    assert cache not in set(mod.iter_files([tmp_path]))


def test_other_temp_folders_and_docs_are_scanned(tmp_path: Path) -> None:
    """A .temp folder anywhere else, and normal docs, are still scanned."""
    mod = _load_scanner()
    wanted = [
        _write(tmp_path, "app/frontend/.temp/x.txt"),
        _write(tmp_path, ".temp/x.txt"),
        _write(tmp_path, "docs/notes.md"),
    ]
    assert set(wanted) <= set(mod.iter_files([tmp_path]))


def test_key_is_reported_without_its_value(tmp_path: Path) -> None:
    """A finding names the detector and never contains the key."""
    mod = _load_scanner()
    findings = mod.scan_file(_write(tmp_path, "docs/notes.md"), {})
    assert any("openai-key" in f for f in findings)
    assert not any(FAKE_KEY in f for f in findings)
