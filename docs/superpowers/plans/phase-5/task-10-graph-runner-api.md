# Phase 5 · Task 10 — Graph runner, run and decision endpoints, WebSocket stream, budgets, $4 spend cap, tracing guard

**Skills:** `plan-execution`, `fastapi`, `langgraph`, `security-checks` (§C API hardening, LLM/agent risks), `backend-design:idempotency-and-side-effects`, `project-documentation`.
**Docs to check first (Context7):** FastAPI 0.162.5 (`WebSocket`, `websocket.headers`, `close(code=1008)`, lifespan, `BackgroundTasks` is **not** used), LangGraph 1.2.18 (`stream(..., stream_mode=["updates", "custom"], version="v2")`, `get_stream_writer`, `get_state(config).interrupts`, `Command(resume=...)`), langgraph-checkpoint-postgres 3.2.0 (`PostgresSaver(conn=pool)` with a `psycopg_pool.ConnectionPool`, `setup()`), psycopg 3.3 (`dict_row`, `ConnectionPool(kwargs=...)`).

## Fixed decisions
- One active agent run at a time (design: "one event at a time"). `POST /api/runs` while a run is `running` or `awaiting_approval` → `409 {"detail": "a run is already active"}`.
- The graph runs in a worker thread (`asyncio.to_thread`) and talks to the event loop through a thread-safe queue per run (`janus` is **not** added — use `loop.call_soon_threadsafe(queue.put_nowait, msg)`).
- Every message sent over the WebSocket is first persisted (`agent_steps`, `drafts`, …) so a client that (re)connects receives the backlog from the database, then live messages.
- Simulation time is paused by the frontend while the run status is `running` (Task 13); the backend does not move time.
- Budgets per run (owner decision 2026-11-13): hard stop at `$0.10` or `180 s` wall time → status `aborted_budget`. Over `$0.05` / `90 s` is recorded (`runs` row) but not stopped.
- **Total spend cap** (owner decision 2026-11-13): every billed OpenAI call is written to `plumetrace.llm_calls` (Task 8) **before** the next call is allowed; before each call the wrapper checks `total_spend_usd + STEP_RESERVE_USD ≤ PLUMETRACE_SPEND_CAP_USD` (default `$4.00`; the owner's `.env` sets `4.00`), else `SpendCapReached`. A run does not start when less than `RUN_START_MIN_USD` is left. The executor **never** raises the cap; only the owner edits the root `.env`.
- **Every paid run is traced:** the OpenAI-backed `AgentLLM` is built only when `require_tracing(settings)` passes; otherwise the run endpoints answer `503`. The same guard runs in every paid script (`smoke_llm.py`, `run_evals.py`, `record_traces.py`).
- **Tests and test servers never build the OpenAI client.** `create_app(runner_deps: RunnerDeps | None = None)`: when `runner_deps` is given, the lifespan stores it in `app.state` and builds **nothing** (no OpenAI client, no checkpointer pool). `app/backend/tests/conftest.py` gains an autouse fixture that monkeypatches `plumetrace.api.openai_llm.build_agent_llm` (and the name the lifespan imports it under) to raise `ConfigurationError("agents are disabled in tests")` — `get_settings()` reads the root `.env` file directly, so deleting environment variables alone does not stop a paid client from being built. The lifespan treats **any** `ConfigurationError` while building the agents as "agents are not configured" (run endpoints answer `503`, one log line with the error text, which never contains a value). Test `test_tests_cannot_build_openai_client` (in `tests/api/test_runs_api.py`) asserts that calling `build_agent_llm(get_settings())` inside a test raises that error.
- **Every run uses the Postgres checkpointer** (live, eval, record): checkpoints of all paid runs are in the `langgraph` schema. `memory_checkpointer()` is for unit tests only.

## Files (`app/backend/plumetrace/api/`)
| Action | Path |
|---|---|
| Create | `checkpointer.py`, `budget.py`, `spend.py`, `run_messages.py`, `run_registry.py`, `graph_runner.py`, `routes/runs.py`, `routes/run_ws.py`, `origin.py` |
| Modify | `app/backend/plumetrace/config.py` → `export_tracing_env(settings)` and `require_tracing(settings)` (moved here from Task 11 so the first paid call is already traced); tests in `test_config.py` |
| Modify | `scripts/smoke_llm.py` (Task 5) → goes through `BudgetedLLM` with `DbSpendLedger` (purpose `smoke`, no run) and `require_tracing` |
| Modify | `main.py` (lifespan: app pool + checkpointer + `export_tracing_env` + `require_tracing` + `DbSpendLedger`; include the two routers), `schemas.py` (`StartRunIn`, `StartRunOut`, `RunView`) |
| Modify | `app/frontend/vite.config.ts` → proxy `"/api": { target: "http://127.0.0.1:8000", changeOrigin: false, ws: true }` |
| Modify (tests) | `app/backend/tests/conftest.py` → the autouse `build_agent_llm` guard above |
| Create (tests) | `app/backend/tests/api/test_budget.py`, `test_spend.py`, `test_origin.py`, `test_runs_api.py` (fake LLM + fake checkpointer), `test_run_ws.py` |

## Interfaces
`checkpointer.py`:
- `def open_checkpointer(db_url: str) -> tuple[ConnectionPool, PostgresSaver]` — `ConnectionPool(conninfo=db_url, min_size=1, max_size=4, kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row, "options": f"-c search_path={CHECKPOINT_SCHEMA}"}, open=True)`; `saver = PostgresSaver(pool)`; `saver.setup()`; returns both (the lifespan closes the pool on shutdown). The connection string is never logged.

`config.py` (additions):
- `def export_tracing_env(settings: Settings) -> None`: sets `os.environ["LANGSMITH_TRACING"]` to `"true"` only when `settings.langsmith_tracing` **and** a key is present (else `"false"`); sets `LANGSMITH_API_KEY` (from the `SecretStr`) and `LANGSMITH_PROJECT` only in that case. Returns nothing, logs nothing about values.
- `def require_tracing(settings: Settings) -> None` → `ConfigurationError("LANGSMITH_TRACING=true and LANGSMITH_API_KEY are required for paid runs (see docs/reference/AGENTS.md)")` unless both are set. Tests: tracing on but no key → `export_tracing_env` writes `"false"` and `require_tracing` raises; both set → `"true"`, the project is set, `require_tracing` passes; the error text never contains the key (use `monkeypatch` on `os.environ`).

`spend.py`:
- `STEP_RESERVE_USD: Final = Decimal("0.01")` — upper bound of one step (≈ 40 k uncached input × $0.125 / 1 M + 4 000 output × $0.50 / 1 M ≈ $0.007), so the last allowed call can never take the total over the cap.
- `RUN_START_MIN_USD: Final = Decimal("0.05")` — a run starts only when at least this much is left.
- `@dataclass(frozen=True) class LlmCallRecord: run_id: str | None; purpose: Literal["smoke", "live", "eval", "record"]; node: str; role: str; model: str; reasoning_effort: str; prompt_tokens: int; cached_tokens: int; completion_tokens: int; reasoning_tokens: int; cost_usd: Decimal; latency_ms: int`
- `class SpendLedger(Protocol)`: `def spent_usd(self) -> Decimal`; `def record(self, call: LlmCallRecord) -> None`.
- `class DbSpendLedger` — `__init__(self, pool: ConnectionPool)`; `spent_usd` → `llm_calls.total_spend_usd`; `record` → `llm_calls.record_llm_call` (each in its own `pool.connection()`, committed at once).
- `class MemorySpendLedger` — `__init__(self, spent_usd: Decimal = Decimal(0))`; keeps `self.calls: list[LlmCallRecord]`; for tests and `--dry-run` only.
- `class BudgetExceeded(RuntimeError)` and `class SpendCapReached(BudgetExceeded)` (message `"spend cap reached"`) are defined **here**; `budget.py` imports them (one import direction, no cycle).
- `def remaining_usd(ledger: SpendLedger, cap_usd: Decimal) -> Decimal` → `cap_usd − ledger.spent_usd()` (may be negative).
- `def ensure_can_start(ledger: SpendLedger, cap_usd: Decimal) -> None` → `SpendCapReached` when `remaining_usd < RUN_START_MIN_USD`.

`budget.py`:
- `HARD_COST_USD: Final = Decimal("0.10")`; `SOFT_COST_USD: Final = Decimal("0.05")`; `HARD_SECONDS: Final = 180.0`; `SOFT_SECONDS: Final = 90.0`.
- `BudgetExceeded` and `SpendCapReached` are imported from `spend.py` (re-exported, so `from plumetrace.api.budget import BudgetExceeded` works).
- `class BudgetedLLM` (implements `AgentLLM`): `__init__(self, inner: AgentLLM, *, ledger: SpendLedger, cap_usd: Decimal, purpose: str, run_id: str | None = None, efforts: Mapping[str, str] = REASONING_EFFORT)` (`REASONING_EFFORT` from `openai_llm.py`); stores `started = time.monotonic()`. Before each `step`, in this order: elapsed > `HARD_SECONDS` → `BudgetExceeded("time budget exceeded")`; run cost > `HARD_COST_USD` → `BudgetExceeded("cost budget exceeded")`; `ledger.spent_usd() + STEP_RESERVE_USD > cap_usd` → `SpendCapReached("spend cap reached")`. Then `turn = inner.step(...)`; on `NoToolCallError` record `err.usage` first, then re-raise. After the step: `cost = cost_usd(usage.model, usage.prompt_tokens, usage.cached_tokens, usage.completion_tokens)`; `ledger.record(LlmCallRecord(..., reasoning_effort=efforts[role], reasoning_tokens=usage.reasoning_tokens, latency_ms=usage.latency_ms))` **before** returning; add to the run totals. Exposes `prompt_tokens`, `completion_tokens`, `cost_usd`, `elapsed_s`, `over_soft` (`cost_usd > SOFT_COST_USD or elapsed_s > SOFT_SECONDS`). Unknown model price → `KeyError` propagates (fails visibly). `run_id` can be set after construction (`budget.run_id = ...`) because the run row is created first.

`run_messages.py` (Pydantic, `extra="forbid"`): the WebSocket protocol — every message has `type` and `seq` (step seq or `-1`):
- `StepMessage(type="step", seq, node, kind, call_id, tool, summary, payload: dict | None)` (`payload` = tool input/output on `tool_result`, used for "source on hover")
- `ApprovalMessage(type="approval", seq, payload: dict)` (an `ApprovalPayload` dump)
- `StatusMessage(type="status", seq=-1, status: RunStatus, outcome: str | None)`
- `FinalMessage(type="final", seq, final: dict)`
- `ErrorMessage(type="error", seq=-1, detail: str)` — generic text only (`"the agent run failed"`, `"budget exceeded"`, `"spend cap reached"`); the exception goes to the server log, never to the client.

`run_registry.py` — `class RunRegistry` (module singleton `REGISTRY`): `active_run_id: str | None`, `subscribers: dict[str, set[asyncio.Queue]]`, `lock: asyncio.Lock`; `publish(run_id, msg)` (thread-safe via `call_soon_threadsafe`), `subscribe(run_id) -> asyncio.Queue`, `unsubscribe(...)`.

`graph_runner.py`:
- `@dataclass(frozen=True) class RunnerDeps: llm: AgentLLM; checkpointer: BaseCheckpointSaver; ledger: SpendLedger; settings: Settings; pool: ConnectionPool; mode: Literal["live", "eval", "record"] = "live"` — `pool` is the app's DB pool (`create_pool`, max 4) used for every repository call of the runner; the scripts build their own `RunnerDeps` with `mode="eval"` / `"record"`.
- `async def start_run(scenario_id: str, deps: RunnerDeps) -> str` — under the lock: refuse if active; `run = replay cache run` (`api/scenario_cache.py` gains `scenario_run_for(id)` returning the `ScenarioRun`); `ensure_can_start(deps.ledger, deps.settings.plumetrace_spend_cap_usd)` (→ `SpendCapReached`, mapped to `429` by the route); `save_scenario_run(conn, run, mode=deps.mode)` → `run_id` (`deps.mode` is `live` for the API, `eval` / `record` for the scripts); `make_context`; mark other events of the run `queued` (`events.status`), the first `investigating`; build `ScenarioToolProvider`, `BudgetedLLM(deps.llm, ledger=deps.ledger, cap_usd=deps.settings.plumetrace_spend_cap_usd, purpose=deps.mode, run_id=run_id)`, `graph = build_graph(provider, budgeted, deps.checkpointer)`; launch `_drive(run_id, graph, {"run_id": run_id, "scenario_id": scenario_id})` as a task; return `run_id`.
- `def _consume(run_id, graph, input_or_command, cfg, budget) -> None` (runs in the thread): `for chunk in graph.stream(input_or_command, cfg, stream_mode=["updates", "custom"], version="v2")`:
  - `custom` with `data["type"] == "step"` → `append_step(..., payload=data["payload"])` → publish `StepMessage`;
  - `updates`: `drafts` in a node update → `save_draft`; `final` → write work order (`issue_work_order` when the bundle has one) and report (`file_report` when there is a report line) only for outcomes `approved` / `edited`; `set_outcome`;
  - after the loop: `snap = graph.get_state(cfg)`; `snap.interrupts` non-empty → `set_run_status("awaiting_approval")`, `append_step(kind="approval")`, publish `ApprovalMessage(payload=snap.interrupts[0].value)`; else → `set_run_status("completed")`, publish `FinalMessage` + `StatusMessage`, clear `active_run_id`.
  - `SpendCapReached` (check it **before** `BudgetExceeded`, it is a subclass) → status `aborted_budget`, `outcome = "failed"`, step `kind="error"` summary `"spend cap reached"`, publish `ErrorMessage("spend cap reached")`, log `WARNING` with `extra={"run_id": run_id}`, clear active. `BudgetExceeded` → status `aborted_budget`, `outcome = "failed"`, step `kind="error"` summary `"budget exceeded"`, publish `ErrorMessage("budget exceeded")`, clear active. Any other exception → status `failed`, `ErrorMessage("the agent run failed")`, `logger.exception("agent run failed", extra={"run_id": run_id})` (stored in `app_logs` by Task 9b, redacted), clear active.
  - After the loop also: `add_usage(conn, run_id, …)` from the budget wrapper.
- `async def submit_decision(run_id: str, decision: OperatorDecision, deps) -> None` — run must be `awaiting_approval` (else `409 {"detail": "no approval is pending"}`); `pending = graph.get_state(cfg).interrupts[0].value["interrupt_id"]`; `decision.interrupt_id != pending` → `409 {"detail": "decision does not match the pending approval"}`; `record_decision(...)` returns `False` → `409 {"detail": "decision already recorded"}`; append step `kind="decision"`; status `running`; `_consume(run_id, graph, Command(resume=decision.model_dump(mode="json")), cfg, budget)` in the thread.
- The compiled graph and budget per run are kept in the registry while the run is active (rebuilt from the checkpointer if the backend restarted: `build_graph` again with the same `thread_id` — the checkpoint holds the state).

`routes/runs.py` (`prefix="/api/runs"`):
- `POST /api/runs` body `StartRunIn(scenario_id: str)` → `201 StartRunOut(run_id)`; unknown scenario → `404 {"detail": "unknown scenario"}`; active run → `409`; spend cap reached → `429 {"detail": "spend cap reached: see docs/reference/AGENTS.md"}`; missing model settings, key or tracing → `503 {"detail": "agents are not configured: see docs/reference/AGENTS.md"}` (no variable values in the message).
- `GET /api/runs/{run_id}` → `RunView(run_id, scenario_id, status, outcome, steps: list[StepMessage], pending_approval: dict | None, final: dict | None)`; unknown / malformed id → `404 {"detail": "unknown run"}`.
- `POST /api/runs/{run_id}/decision` body `OperatorDecision` → `202 {"status": "accepted"}` or the `409`s above; body validation errors → FastAPI `422` (default).

`routes/run_ws.py`: `@router.websocket("/api/runs/{run_id}/ws")`:
1. `origin_allowed(websocket.headers.get("origin"))` (exact match against `ALLOWED_ORIGINS`) — else `await websocket.close(code=1008)` **before** `accept()`.
2. Unknown run → accept, send `ErrorMessage("unknown run")`, close 1008.
3. `accept()`; subscribe **first**, then send the backlog (`list_steps` → `StepMessage`s, pending approval, final/status) and then queued live messages with `seq` greater than the last backlog `seq` (dedupe).
4. Client messages are ignored (decisions go through `POST`); on disconnect unsubscribe.
`origin.py`: `def origin_allowed(origin: str | None) -> bool` — `None` → `False`.

`main.py` lifespan (extends Task 9b's function; move the agent part to `api/agent_lifespan.py` if the function would pass 50 lines): `export_tracing_env(settings)`; if `SUPABASE_DB_URL`, the model settings, the OpenAI key **and** `require_tracing` all pass: open the checkpointer, build `OpenAIAgentLLM`, `DbSpendLedger(pool)`; store them in `app.state` (`RunnerDeps(llm, checkpointer, ledger, settings, mode="live")`); otherwise leave them `None` (the scenario endpoints keep working; run endpoints answer `503`). Log one line per missing setting **name**. Log one `INFO` line at start-up: `spend so far $<x> of $<cap>` (numbers only).

## Tests (key cases; full code for budget and origin)
`test_budget.py`:
```python
"""Budget wrapper: costs add up, every call is in the ledger, the limits stop the run."""

from decimal import Decimal

import pytest

from plumetrace.api import budget as budget_mod
from plumetrace.api import model_prices
from plumetrace.api.budget import BudgetedLLM, BudgetExceeded
from plumetrace.api.model_prices import ModelPrice
from plumetrace.api.spend import MemorySpendLedger, SpendCapReached
from plumetrace_agents.llm import ScriptedLLM, submit

PRICE = {"scripted": ModelPrice(Decimal(500), Decimal(0), Decimal(500))}  # 120 tokens -> $0.06
EFFORTS = {"fast": "low", "reasoning": "medium"}


def _llm(ledger: MemorySpendLedger, n: int, cap: str = "1.00") -> BudgetedLLM:
    script = {"n": [submit(a=i) for i in range(n)]}
    return BudgetedLLM(ScriptedLLM(script), ledger=ledger, cap_usd=Decimal(cap), purpose="live",
                       run_id="r1", efforts=EFFORTS)


def _step(llm: BudgetedLLM) -> None:
    llm.step(node="n", role="fast", messages=[], tools=[], output_model=object)


def test_cost_accumulates_is_recorded_and_hard_limit_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each step adds $0.06 and one ledger row; over $0.10 the next step raises."""
    monkeypatch.setattr(model_prices, "PRICES", PRICE)
    ledger = MemorySpendLedger()
    llm = _llm(ledger, 3)
    _step(llm)
    assert llm.cost_usd == Decimal("0.06") and llm.over_soft is True
    _step(llm)
    assert ledger.spent_usd() == Decimal("0.12") and len(ledger.calls) == 2
    assert ledger.calls[0].reasoning_effort == "low" and ledger.calls[0].run_id == "r1"
    with pytest.raises(BudgetExceeded, match="cost budget exceeded"):
        _step(llm)


def test_spend_cap_stops_before_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """With $0.995 spent of $1.00 the reserve does not fit: no call is made."""
    monkeypatch.setattr(model_prices, "PRICES", PRICE)
    ledger = MemorySpendLedger(spent_usd=Decimal("0.995"))
    llm = _llm(ledger, 1)
    with pytest.raises(SpendCapReached, match="spend cap reached"):
        _step(llm)
    assert ledger.calls == []


def test_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wall time over the hard limit stops the run."""
    monkeypatch.setattr(model_prices, "PRICES", PRICE)
    llm = _llm(MemorySpendLedger(), 1)
    monkeypatch.setattr(budget_mod.time, "monotonic", lambda: llm.started + budget_mod.HARD_SECONDS + 1)
    with pytest.raises(BudgetExceeded, match="time budget exceeded"):
        _step(llm)
```
(`ScriptedLLM` returns `Usage("scripted", 100, 0, 20)`: 120 tokens × $500 / 1 M = $0.06. `MemorySpendLedger.spent_usd()` = initial value + the sum of recorded calls.)
`test_spend.py`: `ensure_can_start` passes with `$0.95` spent of `$1.00` and raises `SpendCapReached` with `$0.96` spent (`$0.04` left < `$0.05`); `remaining_usd` can be negative; with the DB fixture, `DbSpendLedger.record` then `spent_usd` grows by exactly the recorded cost.
`test_origin.py`: `origin_allowed("http://localhost:5173") is True`; `"http://localhost:5173.evil.example"`, `"null"`, `None`, `"https://evil.example"` → `False`.
`test_runs_api.py` (TestClient on `create_app(runner_deps=RunnerDeps(...))`, i.e. `ScriptedLLM` (S1-like script built for the **fake** provider) and `memory_checkpointer()`, and a monkeypatched `ScenarioToolProvider` → `FakeToolProvider("s1")`; DB fixture required): start → `201`; second start → `409`; `GET` shows `awaiting_approval` with a pending payload; decision with a wrong interrupt id → `409`; correct approve → `202`, then status `completed`, outcome `approved`, one `work_orders` row and one `reports` row; posting the same decision again → `409 decision already recorded`; unconfigured app → `503` with no setting value in the body; tracing off but everything else set → `503`; a `MemorySpendLedger(spent_usd=cap − Decimal("0.04"))` (`cap = deps.settings.plumetrace_spend_cap_usd`; never assume its value — the owner's `.env` sets it) in the `RunnerDeps` → start → `429 spend cap reached`; after a completed run the ledger holds one record per scripted step with `purpose="live"` and the run id.
`test_run_ws.py`: connecting with `Origin: https://evil.example` is rejected (the TestClient raises `WebSocketDisconnect` with code 1008); with the dev origin the backlog arrives in `seq` order, then the approval message; a reconnect gets the same backlog without duplicates.

## First paid calls (owner's yes first; total ≈ $0.02 + $0.001)
1. State in chat: smoke test (≈ $0.001) + one live S1 run (≈ $0.02, Task 1 estimate) and the current spend (`select coalesce(sum(cost_usd), 0) from plumetrace.llm_calls`). Wait for yes.
2. Smoke: `cd app && uv run python ../scripts/smoke_llm.py` → prints the tool name, token counts and `spend $<total> of $<cap>`; the LangSmith project shows the trace.
3. Live run: backend + frontend running; `POST /api/runs {"scenario_id": "s1_rod_packing"}` via `curl`; watch the WebSocket with the browser console (`new WebSocket("ws://localhost:5173/api/runs/<id>/ws")`); approve via `curl`.
4. Check in the database: the `runs` row (tokens, cost, wall time), its `llm_calls` rows (one per LLM step; the sum equals `runs.cost_usd` within rounding), its `agent_steps`, its `app_logs` lines, and its checkpoints (`select count(*) from langgraph.checkpoints where thread_id = '<run_id>'` — names per the pinned langgraph-checkpoint-postgres; check them with `\dt langgraph.*`). Check the LangSmith trace by eye (Task 11 adds the URL column value). Record cost, time and the spend total in the work log.

## Steps
- [ ] Tests → FAIL → implement → `PLUMETRACE_REQUIRE_DB=1 uv run pytest app/backend -q` green.
- [ ] `security-checks` §C review of the new endpoints (input validation, generic errors, no echo, Origin check, no secrets in logs); `backend-design:security-reviewer` on `routes/` and `graph_runner.py`; fix every finding.
- [ ] First paid calls (above), with the owner's yes.
- [ ] Repo checks.
- [ ] **Docs.** API.md → runs endpoints, WebSocket protocol (every message type with fields), error codes, Origin rule; AGENTS.md → "Running the graph in the backend" (thread, queue, persistence-before-publish, budgets, the spend ledger and cap (how to read the total, what happens at the cap, who may raise it), the tracing guard, the Postgres checkpointer for every mode, restart behaviour); SECURITY.md → "Agent runs" and "Spend cap". Work-log; `STATUS.md` (last 5.10, next 5.11).
- [ ] **Commit** `feat(api): run the agent graph with approval endpoints and a WebSocket stream`.
