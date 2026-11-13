# Phase 6 · Task 3 — Request hardening: body limit, trusted hosts, security headers, generic errors, strict inputs

**Skills:** `plan-execution`, `fastapi`, `security-checks` (§C), `backend-design:error-handling-as-design`, `superpowers:test-driven-development`, `project-documentation`.
**Docs to check first (Context7):** Starlette 1.10.0 `TrustedHostMiddleware(allowed_hosts=...)` (does it strip the port?), pure ASGI middleware (`scope`, `receive`, `send`), `@app.exception_handler(Exception)`; FastAPI 0.162.5 middleware order (last added = outermost); Pydantic 2.14.3 `Field(max_length=..., pattern=...)`, `ConfigDict(extra="forbid")`; uvicorn 0.54.0 `--ws-max-size`, `--limit-concurrency`, `--timeout-keep-alive`.

## Fixed decisions
- **Body limit 64 KiB** (`MAX_BODY_BYTES = 65_536`) on every HTTP request: `Content-Length` above → `413 {"detail": "request body too large"}` without reading; a body without `Content-Length` is counted while it streams and cut off at the limit with the same `413`.
- **WebSocket message limit 64 KiB** and connection limits via uvicorn flags in the documented run command: `--ws-max-size 65536 --limit-concurrency 64 --timeout-keep-alive 5`.
- **Trusted hosts:** `localhost`, `127.0.0.1` (DNS-rebinding defence, threat T03). Any other `Host` → `400` (Starlette's response). Tests use `base_url="http://127.0.0.1"`.
- **Security headers on every API response:** `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Cross-Origin-Resource-Policy: same-origin`, `Cache-Control: no-store` (all `/api/runs` paths); `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` on every response **except** `/api/docs` (Swagger UI needs its own scripts; it is local only — accepted risk in THREAT_MODEL.md).
- **Generic 500:** any unhandled exception → `500 {"detail": "internal error"}`; the traceback goes only to `logger.exception` (stored redacted in `app_logs`). FastAPI `debug=False` always.
- **Strict inputs** (threats T04–T06): every request model `extra="forbid"`; lengths below.

## Input limits (change these exact fields)
| Model (file) | Field | New constraint |
|---|---|---|
| `StartRunIn` (`app/backend/plumetrace/api/schemas.py`) | `scenario_id` | `Field(pattern=r"^[a-z0-9_]{1,64}$")`; `model_config = ConfigDict(extra="forbid")` |
| `OperatorDecision` | `interrupt_id` | `Field(max_length=68, pattern=r"^[A-Za-z0-9-]{1,64}:r[01]$")` (live run ids are UUIDs; graph tests use short ids such as `r1:r0` — both pass) |
| `OperatorDecision` | `reason` | `Field(default=None, max_length=500)` (the 3–500-after-strip validator stays) |
| `DraftEdits` (same file) | `work_order_description` | `Field(default=None, max_length=1200)` |
| `DraftEdits` | `work_order_actions` | `Field(default=None, min_length=1, max_length=6)` and each item `≤ 200` chars (`list[Annotated[str, Field(min_length=1, max_length=200)]]`) |
| `DraftEdits` | `shift_log_text` | `Field(default=None, max_length=600)` |
| `DraftEdits` | `report_line_text` | `Field(default=None, max_length=400)` |
| `DraftEdits` | `overrides` | `Field(default_factory=dict, max_length=10)`; keys `pattern=r"^[a-z_]+(\.[a-z0-9_]+){1,3}$"` |
| path params `run_id` (`routes/runs.py`, `routes/run_ws.py`) | — | typed `uuid.UUID` → malformed id is `422` (HTTP) / unknown run (WS); never reaches SQL as text |
All agent schema models already use `extra="forbid"` (Phase 5 Task 2) — confirm with a grep; add it where missing.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/api/body_limit.py` (pure ASGI class), `app/backend/plumetrace/api/security_headers.py`, `app/backend/plumetrace/api/errors.py` (exception handler) |
| Modify | `app/backend/plumetrace/api/main.py` → `create_app(..., allowed_hosts: Sequence[str] = ("localhost", "127.0.0.1"))`; middleware order from outermost: `TrustedHostMiddleware` → `BodySizeLimit` → `CORSMiddleware` → security headers → request log → rate limit → app; `app.add_exception_handler(Exception, internal_error_handler)` |
| Modify | `schemas.py`, `decisions.py`, `routes/runs.py`, `routes/run_ws.py` (limits above) |
| Modify | **every** `TestClient(` in `app/backend/tests/` → add `base_url="http://127.0.0.1"` (`grep -rn "TestClient(" app/backend/tests` lists them; a test that needs another host says so in its name) |
| Modify | `docs/LOCAL_DEVELOPMENT.md` run command → `uv run uvicorn plumetrace.api.main:app --host 127.0.0.1 --port 8000 --ws-max-size 65536 --limit-concurrency 64 --timeout-keep-alive 5 --reload` |
| Create (tests) | `app/backend/tests/security/test_request_hardening.py`, `app/agents/tests/schemas/test_decision_limits.py` |

## Interfaces
- `body_limit.py`: `MAX_BODY_BYTES: Final = 65_536`; `class BodySizeLimit: __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES)`; `async __call__(scope, receive, send)`: non-`http` scopes pass through; `content-length` header > max → send the 413 JSON; otherwise wrap `receive` to sum `len(message["body"])` and, above max, raise an internal `_TooLarge` caught here → 413 (only if the response has not started; if it has, close the connection).
- `security_headers.py`: `API_HEADERS: Final[Mapping[str, str]]` (the four always-on headers), `CSP: Final = "default-src 'none'; frame-ancestors 'none'"`; `async def add_security_headers(request, call_next)`.
- `errors.py`: `async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse` → `logger.exception("unhandled error on %s %s", request.method, request.url.path)`, returns 500 `{"detail": "internal error"}`.

## Tests (full code)
`app/backend/tests/security/test_request_hardening.py`:
```python
"""Body limit, trusted hosts, headers, generic errors and strict inputs on the real app."""

from fastapi import APIRouter
from fastapi.testclient import TestClient

from plumetrace.api.main import create_app

BASE = "http://127.0.0.1"


def test_body_over_limit_gets_413() -> None:
    """A 70 KB body is refused before it reaches the route."""
    with TestClient(create_app(), base_url=BASE) as client:
        r = client.post("/api/runs", content=b"{" + b" " * 70_000 + b"}",
                        headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json() == {"detail": "request body too large"}


def test_foreign_host_header_is_rejected() -> None:
    """DNS rebinding: Host evil.example is refused; localhost with a port is fine."""
    with TestClient(create_app(), base_url=BASE) as client:
        assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 400
        assert client.get("/api/health", headers={"host": "localhost:5173"}).status_code == 200


def test_security_headers_present() -> None:
    """Every API response carries the fixed headers; run paths are not cached."""
    with TestClient(create_app(), base_url=BASE) as client:
        r = client.get("/api/scenarios")
        run = client.get("/api/runs/00000000-0000-0000-0000-000000000000")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert run.headers["cache-control"] == "no-store"


def test_unhandled_error_is_generic() -> None:
    """An exception inside a route returns 500 'internal error' with no detail."""
    app = create_app()
    router = APIRouter()

    @router.get("/api/test-boom")
    def boom() -> None:
        raise RuntimeError("secret detail postgresql://u:p@h/db")

    app.include_router(router)
    with TestClient(app, base_url=BASE, raise_server_exceptions=False) as client:
        r = client.get("/api/test-boom")
    assert r.status_code == 500 and r.json() == {"detail": "internal error"}
    assert "secret" not in r.text and "postgresql" not in r.text


def test_unknown_fields_and_bad_ids_are_422() -> None:
    """extra fields and malformed scenario / run ids never reach the handlers."""
    with TestClient(create_app(), base_url=BASE) as client:
        assert client.post("/api/runs", json={"scenario_id": "s1", "x": 1}).status_code == 422
        assert client.post("/api/runs", json={"scenario_id": "../../etc"}).status_code == 422
        assert client.get("/api/runs/not-a-uuid").status_code == 422
```
`app/agents/tests/schemas/test_decision_limits.py`: a 501-char `reason` → `ValidationError`; `interrupt_id="x"` → `ValidationError`; 7 actions → `ValidationError`; an override key `"__class__"` → `ValidationError`; a valid edit at every maximum length passes.

## Steps
- [ ] Tests → FAIL → implement → `uv run pytest app/backend app/agents -q` green (update earlier tests that relied on the default `testserver` host or on unlimited fields — list each changed test in the work log).
- [ ] Frontend: the approval dialog's text fields get the same `maxLength` values (`ApprovalDialog.tsx`, Phase 5 Task 14) with a visible character counter for `reason` (`<n> / 500`); component test asserts the limits; `check_slop.py`.
- [ ] Manual: `curl -s -o /dev/null -w "%{http_code}\n" -H "Host: evil.example" http://127.0.0.1:8000/api/health` → `400`.
- [ ] Repo checks; `ruff --select S`.
- [ ] **Docs.** API.md → "Limits and errors" (body size, WS message size, uvicorn flags, hosts, headers, error format, field limits table); SECURITY.md → "Request hardening"; THREAT_MODEL.md T03, T04, T06, T07 confirmed. Work-log; `STATUS.md` (last 6.3, next 6.4).
- [ ] **Commit** `feat(api): add body limit, trusted hosts, security headers and strict inputs`.
