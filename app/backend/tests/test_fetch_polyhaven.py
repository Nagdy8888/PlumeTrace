"""Tests for scripts/fetch_polyhaven.py (no network: httpx.MockTransport, files in tmp_path)."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import httpx
import pytest

from plumetrace.config import REPO_ROOT

DL = "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/metal_plate"
BODY = b"not a real jpg"
REAL_CLIENT = httpx.Client  # kept: tests patch httpx.Client in the script module
MANIFEST = {
    "resolution": "1k",
    "textures": {"metal_plate": ["nor_gl", "Rough"]},
    "hdris": {},
    "sha256": {},
}


def _load() -> ModuleType:
    """Import scripts/fetch_polyhaven.py by file path."""
    path = REPO_ROOT / "scripts" / "fetch_polyhaven.py"
    spec = importlib.util.spec_from_file_location("fetch_polyhaven", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _client(host: str = "dl.polyhaven.org") -> httpx.Client:
    """A client whose API answers with two metal_plate maps on ``host`` and whose files are BODY."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.polyhaven.com":
            url = f"https://{host}/file/ph-assets/Textures/jpg/1k/metal_plate"
            files = {
                "nor_gl": {"1k": {"jpg": {"url": f"{url}/metal_plate_nor_gl_1k.jpg"}}},
                "Rough": {"1k": {"jpg": {"url": f"{url}/metal_plate_rough_1k.jpg"}}},
            }
            return httpx.Response(200, json=files)
        return httpx.Response(200, content=BODY)

    return REAL_CLIENT(transport=httpx.MockTransport(handler))


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The script module with every path pointed into ``tmp_path``."""
    m = _load()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "MANIFEST", manifest)
    monkeypatch.setattr(m, "TEXTURE_DIR", tmp_path / "build" / "polyhaven")
    monkeypatch.setattr(m, "HDRI_DIR", tmp_path / "hdri")
    return m


def test_plan_maps_file_names_from_urls(mod: ModuleType) -> None:
    """Each map becomes build/polyhaven/<id>/<file name taken from the URL>."""
    jobs = mod.plan_downloads(_client(), MANIFEST)
    names = [target.relative_to(mod.ROOT).as_posix() for _, target in jobs]
    assert names == [
        "build/polyhaven/metal_plate/metal_plate_nor_gl_1k.jpg",
        "build/polyhaven/metal_plate/metal_plate_rough_1k.jpg",
    ]


def test_url_outside_the_allowed_host_is_refused(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A URL not on dl.polyhaven.org raises FetchError; main exits 1 and writes no file."""
    with pytest.raises(mod.FetchError, match="refusing URL outside"):
        mod.plan_downloads(_client("evil.example.com"), MANIFEST)
    monkeypatch.setattr(mod.httpx, "Client", lambda **_: _client("evil.example.com"))
    assert mod.main(["--record"]) == 1
    assert not mod.TEXTURE_DIR.exists()


def test_hash_mismatch_names_the_file(mod: ModuleType) -> None:
    """A downloaded file whose SHA-256 differs from the recorded one raises, naming the file."""
    target = mod.TEXTURE_DIR / "metal_plate" / "metal_plate_nor_gl_1k.jpg"
    with pytest.raises(mod.FetchError, match="hash mismatch: build/polyhaven/metal_plate/"):
        mod.fetch_one(_client(), f"{DL}/metal_plate_nor_gl_1k.jpg", target, "0" * 64)


def test_matching_hash_skips_the_download(mod: ModuleType) -> None:
    """An existing file with the recorded hash is not fetched again."""
    target = mod.TEXTURE_DIR / "metal_plate" / "metal_plate_nor_gl_1k.jpg"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"already here")
    digest = hashlib.sha256(b"already here").hexdigest()
    assert mod.fetch_one(_client(), f"{DL}/x.jpg", target, digest) == digest
    assert target.read_bytes() == b"already here"


def test_record_writes_sorted_hashes(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """--record stores each file's SHA-256 under its repo-relative path, sorted, LF, indent 2."""
    monkeypatch.setattr(mod.httpx, "Client", lambda **_: _client())
    assert mod.main(["--record"]) == 0
    text = mod.MANIFEST.read_bytes().decode("utf-8")
    assert b"\r" not in mod.MANIFEST.read_bytes() and text.endswith("}\n")
    hashes = json.loads(text)["sha256"]
    digest = hashlib.sha256(BODY).hexdigest()
    assert hashes == {
        "build/polyhaven/metal_plate/metal_plate_nor_gl_1k.jpg": digest,
        "build/polyhaven/metal_plate/metal_plate_rough_1k.jpg": digest,
    }
    assert mod.main([]) == 0  # verify mode accepts the recorded hashes
