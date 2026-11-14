"""Tests for scripts/fetch_weather.py (mock transport; no network, no file overwrite)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import httpx
import pytest

from plumetrace.config import REPO_ROOT


def _load_script() -> ModuleType:
    """Import scripts/fetch_weather.py as a module."""
    path = REPO_ROOT / "scripts" / "fetch_weather.py"
    spec = importlib.util.spec_from_file_location("fetch_weather", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _week(n: int) -> dict[str, dict[str, list[object]]]:
    times = [f"2025-07-{14 + h // 24:02d}T{h % 24:02d}:00" for h in range(n)]
    return {
        "hourly": {
            "time": times,
            "wind_speed_10m": [3.0] * n,
            "wind_direction_10m": [90] * n,
            "shortwave_radiation": [0.0] * n,
            "cloud_cover": [20] * n,
            "temperature_2m": [25.0] * n,
        }
    }


def _setup(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, out: Path, response: httpx.Response
) -> None:
    """Point the script at ``out`` and serve ``response`` instead of the network."""
    transport = httpx.MockTransport(lambda request: response)
    real_client = httpx.Client
    monkeypatch.setattr(mod, "SNAPSHOT_OUT", out)
    monkeypatch.setattr(mod.httpx, "Client", lambda: real_client(transport=transport))


def test_main_writes_a_deterministic_168_hour_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full week is written as UTF-8, LF, sorted keys, with start and attribution."""
    mod = _load_script()
    out = tmp_path / "snap.json"
    _setup(mod, monkeypatch, out, httpx.Response(200, content=json.dumps(_week(168))))
    assert mod.main() == 0
    raw = out.read_bytes()
    doc = json.loads(raw)
    assert b"\r" not in raw and raw.endswith(b"\n")
    assert doc["start_utc"] == "2025-07-14T00:00:00Z"
    assert "Open-Meteo" in doc["attribution"]
    assert [h["hour_index"] for h in doc["hours"]] == list(range(168))
    assert raw.decode() == json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def test_main_fails_on_wrong_hour_count_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A short series is an error with a clear message; no file is created."""
    mod = _load_script()
    out = tmp_path / "snap.json"
    _setup(mod, monkeypatch, out, httpx.Response(200, content=json.dumps(_week(100))))
    assert mod.main() == 1
    assert "168" in capsys.readouterr().err
    assert not out.exists()


def test_main_reports_http_errors_and_keeps_the_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An HTTP error returns 1 with the status; an existing snapshot is untouched."""
    mod = _load_script()
    out = tmp_path / "snap.json"
    out.write_text("old", encoding="utf-8")
    _setup(mod, monkeypatch, out, httpx.Response(503))
    assert mod.main() == 1
    assert "503" in capsys.readouterr().err
    assert out.read_text(encoding="utf-8") == "old"


def test_main_reports_null_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A null in the response stops the script and names the field."""
    mod = _load_script()
    out = tmp_path / "snap.json"
    week = _week(168)
    week["hourly"]["cloud_cover"][5] = None
    _setup(mod, monkeypatch, out, httpx.Response(200, content=json.dumps(week)))
    assert mod.main() == 1
    assert "cloud_cover" in capsys.readouterr().err
    assert not out.exists()


def test_script_does_not_touch_tls_settings() -> None:
    """The script keeps the httpx default (certificates verified)."""
    source = (REPO_ROOT / "scripts" / "fetch_weather.py").read_text(encoding="utf-8")
    assert "verify" not in source
