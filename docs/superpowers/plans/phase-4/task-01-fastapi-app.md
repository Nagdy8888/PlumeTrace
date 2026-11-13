# Phase 4 · Task 1 — FastAPI application (scenarios and replay endpoint)

**Skills:** `plan-execution`, `fastapi`, `security-checks` (API hardening checklist §C), `project-documentation`.

**Design choice (fixed):** in live mode the frontend loads a scenario's full time series from the
backend (`GET /api/scenarios/{id}/replay`, computed on demand with the truth model) and plays it
with its own clock. The WebSocket arrives in Phase 5 for agent runs.

## Files
| Action | Path |
|---|---|
| Modify | `app/backend/pyproject.toml` → add `"fastapi==0.162.5"`, `"uvicorn[standard]==0.54.0"` |
| Create | `app/backend/plumetrace/api/main.py`, `app/backend/plumetrace/api/schemas.py`, `app/backend/plumetrace/api/routes/__init__.py`, `app/backend/plumetrace/api/routes/health.py`, `app/backend/plumetrace/api/routes/scenarios.py`, `app/backend/plumetrace/api/scenario_cache.py` |
| Create | `app/backend/tests/api/test_api.py` |
| Modify | `app/frontend/vite.config.ts` → add the dev proxy (below) |
| Create | `docs/reference/API.md`; modify `docs/LOCAL_DEVELOPMENT.md` → "Running the backend" |

## Interface
`api/schemas.py`:
- `class Health(BaseModel): status: Literal["ok"]; version: str`
- `class ScenarioSummary(BaseModel): id: str; title: str; duration_h: int; is_mvp: bool`

`api/scenario_cache.py`:
- `@functools.lru_cache(maxsize=8) def replay_for(scenario_id: str) -> ReplayScenario` — `run_scenario(get_scenario(id), load_facility(), load_snapshot())` → `build_replay(..., load_snapshot().attribution)`. Unknown id propagates `KeyError`.

`api/routes/health.py`: `router = APIRouter(prefix="/api", tags=["health"])`; `GET /api/health` → `Health(status="ok", version=plumetrace.__version__)`.

`api/routes/scenarios.py`: `router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])`:
- `GET /api/scenarios` → `list[ScenarioSummary]` from the registry (sorted by id; `is_mvp=True` for all three).
- `GET /api/scenarios/{scenario_id}/replay` → `ReplayScenario`; unknown id → `404` with `{"detail": "unknown scenario"}` (never echo the id back unescaped).

`api/main.py`:
- `ALLOWED_ORIGINS: Final = ("http://localhost:5173", "http://127.0.0.1:5173")`
- `def create_app() -> FastAPI` — title "PlumeTrace API", `docs_url="/api/docs"`, `openapi_url="/api/openapi.json"`, `redoc_url=None`; `CORSMiddleware(allow_origins=list(ALLOWED_ORIGINS), allow_methods=["GET", "POST"], allow_headers=["Content-Type"], allow_credentials=False)`; include both routers.
- `app = create_app()`
- Run: `cd app && uv run uvicorn plumetrace.api.main:app --host 127.0.0.1 --port 8000 --reload`.

`vite.config.ts` → add inside `defineConfig({...})`:
```ts
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
```

## Tests (full code) — `app/backend/tests/api/test_api.py`
```python
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
    assert [s["id"] for s in r.json()] == ["s1_rod_packing", "s4_planned_blowdown",
                                           "s5_sensor_drift"]


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
```

## Steps
- [ ] Add deps; `uv sync`. Tests → FAIL → implement → full checks green.
- [ ] Start the server (command above) and `curl -s http://127.0.0.1:8000/api/health` → `{"status":"ok","version":"0.1.0"}`. Stop it.
- [ ] **Docs.** `docs/reference/API.md` (template sections): every endpoint, method, response schema (field list), errors, CORS, bind address, OpenAPI URL. LOCAL_DEVELOPMENT → "Running the backend". SECURITY.md → "API" (localhost bind, CORS allowlist, no echo, generic errors). Work-log; `STATUS.md` (last 4.1, next 4.2).
- [ ] **Commit** `feat(api): add FastAPI app with scenario and replay endpoints`.
