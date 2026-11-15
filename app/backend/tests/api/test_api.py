"""Tests for the FastAPI application."""

from fastapi.testclient import TestClient

from plumetrace.api.main import create_app

client = TestClient(create_app())


def test_health() -> None:
    """Health reports ok and the package version."""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "0.1.0"}


def test_scenario_list() -> None:
    """The three MVP scenarios are listed, sorted by id."""
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [
        "s1_rod_packing",
        "s4_planned_blowdown",
        "s5_sensor_drift",
    ]


def test_scenario_replay() -> None:
    """The replay endpoint returns the documented format."""
    r = client.get("/api/scenarios/s5_sensor_drift/replay")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_id"] == "s5_sensor_drift" and body["simulated"] is True
    assert len(body["wind_speed_m_s"]) == 360


def test_unknown_scenario_is_404_without_echo() -> None:
    """Unknown ids give a generic 404."""
    r = client.get("/api/scenarios/<script>/replay")
    assert r.status_code == 404
    assert r.json() == {"detail": "unknown scenario"}


def test_cors_allows_only_the_dev_origin() -> None:
    """The Vite dev origin is allowed; any other origin is not."""
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
