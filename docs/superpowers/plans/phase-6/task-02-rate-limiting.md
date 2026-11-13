# Phase 6 · Task 2 — Rate limiting and connection limits

**Skills:** `plan-execution`, `fastapi`, `security-checks` (§C), `backend-design:security-discipline`, `superpowers:test-driven-development`, `project-documentation`.
**Docs to check first (Context7):** FastAPI 0.162.5 / Starlette 1.10.0 — `@app.middleware("http")`, `Request.client.host`, `JSONResponse(headers=...)`, `WebSocket.client`, `websocket.close(code=..., reason=...)`.

## Fixed decisions
- **No new dependency.** A small in-process token bucket (the backend is one local process; no Redis).
- Client key = `request.client.host` (WebSocket: `websocket.client.host`). `X-Forwarded-For` and similar headers are **ignored** (no proxy is trusted; the Vite dev proxy connects from `127.0.0.1`, so all browser tabs share one bucket — intended).
- Route classes and limits (capacity = burst; refill evenly over the window):
  | Class | Matches | Limit |
  |---|---|---|
  | `start_run` | `POST /api/runs` | 5 per 60 s |
  | `decision` | `POST /api/runs/{run_id}/decision` | 20 per 60 s |
  | `ws_connect` | WebSocket `/api/runs/{run_id}/ws` connect | 10 per 60 s |
  | `read` | every other `/api/...` request (all methods) | 240 per 60 s |
  `/api/health` is **not** limited (liveness checks).
- Concurrent WebSocket connections per client host: at most **3**; a 4th is closed with code `1013` (try again later) before `accept()`.
- Over the limit → `429` JSON `{"detail": "rate limit exceeded"}` with header `Retry-After: <ceil(seconds)>` (integer ≥ 1). WebSocket over the connect limit → close `1008` before `accept()`.
- Memory bound: at most 1024 client keys per class (least recently used evicted).
- Each rejection logs one `WARNING` on `plumetrace.security` (`"rate limit: <class> <host>"`), but at most **once per client and class per 60 s** (T15: a flood does not flood `app_logs`).
- The limiter lives in `app.state.rate_limiter`; tests inject a fake clock.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/api/rate_limit.py` |
| Create | `app/backend/plumetrace/api/rate_limit_middleware.py` |
| Modify | `app/backend/plumetrace/api/main.py` → `create_app(..., rate_limiter: RateLimiter | None = None)`; registers the middleware (after the request log, before CORS, so CORS stays outermost) |
| Modify | `app/backend/plumetrace/api/routes/run_ws.py` → connect limit + concurrency counter before `accept()` |
| Create (tests) | `app/backend/tests/api/test_rate_limit.py` (pure), `app/backend/tests/security/test_rate_limits.py` (TestClient; test folders have **no** `__init__.py` — Phase 1 Task 2) |

## Interfaces
`api/rate_limit.py`:
- `@dataclass(frozen=True) class Rule: capacity: int; window_s: float` → `refill_per_s = capacity / window_s`.
- `RULES: Final[Mapping[str, Rule]] = {"start_run": Rule(5, 60.0), "decision": Rule(20, 60.0), "ws_connect": Rule(10, 60.0), "read": Rule(240, 60.0)}`
- `MAX_KEYS: Final = 1024`; `MAX_WS_PER_CLIENT: Final = 3`; `LOG_EVERY_S: Final = 60.0`.
- `class RateLimiter`: `__init__(self, rules: Mapping[str, Rule] = RULES, clock: Callable[[], float] = time.monotonic)`; per class an `OrderedDict[str, tuple[float, float]]` (tokens, updated); `def check(self, cls: str, key: str) -> float | None` — refill (`min(capacity, tokens + elapsed × refill)`), take 1 token → `None`; not enough → seconds until one token (`(1 − tokens) / refill`), nothing taken; move key to the end; evict the oldest above `MAX_KEYS`. `def should_log(self, cls: str, key: str) -> bool` — `True` at most once per `LOG_EVERY_S` per `(cls, key)`. A `threading.Lock` guards all state (the graph runs in worker threads).
- `class WsCounter`: `acquire(key) -> bool` (`False` when `MAX_WS_PER_CLIENT` are open), `release(key)`; lock-guarded.
- `def route_class(method: str, path: str) -> str | None` — `None` for `/api/health` and for paths outside `/api/`; `POST` + `^/api/runs/?$` → `start_run`; `POST` + `^/api/runs/[^/]+/decision/?$` → `decision`; else `read`.

`api/rate_limit_middleware.py`:
- `def rate_limit_middleware(limiter: RateLimiter) -> Callable` returns the `async def (request, call_next)` function: `cls = route_class(...)`; `cls is None` → pass; `wait = limiter.check(cls, host)`; `wait is not None` → log (if `should_log`) and return the `429` with `Retry-After = str(max(1, math.ceil(wait)))`; else `await call_next(request)`.

`routes/run_ws.py` order before `accept()`: (1) Origin check (existing), (2) `limiter.check("ws_connect", host)` → close `1008`, (3) `ws_counter.acquire(host)` → close `1013`; `release` in `finally` after the socket ends.

## Tests (full code)
`app/backend/tests/api/test_rate_limit.py`:
```python
"""Token bucket: bursts, refill, retry-after, key bound, log throttle."""

import pytest

from plumetrace.api import rate_limit as rl
from plumetrace.api.rate_limit import RateLimiter, Rule, WsCounter, route_class


class Clock:
    """Manual clock for deterministic tests."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_burst_then_refill() -> None:
    """5 per 60 s: 5 pass, the 6th waits 12 s; after 12 s one more passes."""
    clock = Clock()
    lim = RateLimiter({"start_run": Rule(5, 60.0)}, clock=clock)
    assert [lim.check("start_run", "h") for _ in range(5)] == [None] * 5
    wait = lim.check("start_run", "h")
    assert wait == pytest.approx(12.0)
    clock.t += 12.0
    assert lim.check("start_run", "h") is None


def test_clients_are_independent() -> None:
    """One client's burst does not limit another."""
    lim = RateLimiter({"read": Rule(1, 60.0)}, clock=Clock())
    assert lim.check("read", "a") is None and lim.check("read", "a") is not None
    assert lim.check("read", "b") is None


def test_key_count_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Above MAX_KEYS the least recently used key is evicted."""
    monkeypatch.setattr(rl, "MAX_KEYS", 3)
    lim = RateLimiter({"read": Rule(1, 60.0)}, clock=Clock())
    for key in ("a", "b", "c", "d"):
        lim.check("read", key)
    assert lim.check("read", "a") is None  # "a" was evicted, so it starts with a full bucket


def test_log_throttle() -> None:
    """A rejection is logged at most once per minute per client and class."""
    clock = Clock()
    lim = RateLimiter({"read": Rule(1, 60.0)}, clock=clock)
    assert lim.should_log("read", "h") is True and lim.should_log("read", "h") is False
    clock.t += 60.0
    assert lim.should_log("read", "h") is True


def test_ws_counter() -> None:
    """Three sockets per client; releasing one frees a slot."""
    counter = WsCounter()
    assert all(counter.acquire("h") for _ in range(3)) and counter.acquire("h") is False
    counter.release("h")
    assert counter.acquire("h") is True


@pytest.mark.parametrize(("method", "path", "expected"), [
    ("POST", "/api/runs", "start_run"), ("POST", "/api/runs/", "start_run"),
    ("POST", "/api/runs/abc/decision", "decision"), ("GET", "/api/runs/abc", "read"),
    ("GET", "/api/scenarios", "read"), ("GET", "/api/health", None), ("GET", "/", None),
])
def test_route_class(method: str, path: str, expected: str | None) -> None:
    """Routes map to the fixed classes."""
    assert route_class(method, path) == expected
```

`app/backend/tests/security/test_rate_limits.py` (no DB needed: unconfigured app → run endpoints answer `503`, which still passes through the limiter first):
```python
"""Rate limits on the real app: 429 + Retry-After, health unlimited, WS limit, log throttle."""

import logging

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from plumetrace.api.main import create_app
from plumetrace.api.rate_limit import RateLimiter, Rule

BASE = "http://127.0.0.1"
ORIGIN = {"origin": "http://localhost:5173"}


def _client(rules: dict[str, Rule]) -> TestClient:
    return TestClient(create_app(rate_limiter=RateLimiter(rules)), base_url=BASE)


def test_start_run_burst_gets_429() -> None:
    """The 6th start within a minute gets 429 with Retry-After; never 500."""
    with _client({"start_run": Rule(5, 60.0), "read": Rule(240, 60.0)}) as client:
        codes = [client.post("/api/runs", json={"scenario_id": "s1_rod_packing"}).status_code
                 for _ in range(6)]
        assert 500 not in codes and codes[-1] == 429
        last = client.post("/api/runs", json={"scenario_id": "s1_rod_packing"})
        assert int(last.headers["retry-after"]) >= 1
        assert last.json() == {"detail": "rate limit exceeded"}


def test_health_is_not_limited() -> None:
    """Liveness checks never get 429."""
    with _client({"read": Rule(1, 60.0)}) as client:
        assert {client.get("/api/health").status_code for _ in range(20)} == {200}


def test_ws_connect_limit() -> None:
    """With the connect bucket empty the socket is closed with 1008 before accept."""
    limiter = RateLimiter({"ws_connect": Rule(1, 60.0), "read": Rule(240, 60.0)})
    assert limiter.check("ws_connect", "testclient") is None  # TestClient's client host
    with TestClient(create_app(rate_limiter=limiter), base_url=BASE) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/runs/00000000-0000-0000-0000-000000000000/ws",
                                          headers=ORIGIN) as ws:
                ws.receive_json()
        assert exc.value.code == 1008


def test_rejected_requests_are_logged_once_per_window(caplog: pytest.LogCaptureFixture) -> None:
    """Twenty rejected requests produce one security log line."""
    caplog.set_level(logging.WARNING, logger="plumetrace.security")
    with _client({"read": Rule(1, 60.0)}) as client:
        for _ in range(21):
            client.get("/api/scenarios")
    lines = [r for r in caplog.records if r.name == "plumetrace.security"]
    assert len(lines) == 1 and lines[0].getMessage().startswith("rate limit: read ")
```
(Starlette's `TestClient` reports the client host as `"testclient"` for HTTP and WebSocket; check it in the pinned Starlette 1.10.0 source and adjust the key in this test only if it differs.)

## Steps
- [ ] Tests → FAIL → implement → `uv run pytest app/backend -q` green (all earlier API tests still pass with the default `RULES`; if one fails because of a limit, the test makes more requests than a real client should — report it, do not raise a limit).
- [ ] Manual check: backend running; `for i in $(seq 1 7); do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/api/runs -H "Content-Type: application/json" -d '{"scenario_id":"s1_rod_packing"}'; done` → the 6th and 7th print `429` (with agents unconfigured the first five print `503`; this makes **no** paid call). Record the output.
- [ ] Repo checks; `uv run ruff check --select S`.
- [ ] **Docs.** API.md → "Rate limits" (table above, client key, 429 format, WebSocket codes 1008 / 1013, why in-process); SECURITY.md → "Rate limiting"; THREAT_MODEL.md rows T01, T02, T15 → test names confirmed. Work-log; `STATUS.md` (last 6.2, next 6.3).
- [ ] **Commit** `feat(api): add per-client rate limits and WebSocket connection limits`.
