# Phase 5 · Task 12 — Replay trace format, export, and recorded traces for S1 / S4 / S5

**Skills:** `plan-execution`, `langgraph` (trace export), `security-checks` (no secrets in public files), `project-documentation`.

**Why:** the public Vercel site replays recorded agent runs with their original timing (design §6
"Recording and replay"). Each approval point has two recorded branches: **approve** and
**reject with the preset reason → redraft → approve**. LangSmith is not the replay source.

## Files
| Action | Path |
|---|---|
| Create | `app/agents/plumetrace_agents/schemas/trace.py`, `app/agents/plumetrace_agents/export_trace.py` |
| Create (tests) | `app/agents/tests/test_export_trace.py` |
| Create | `scripts/record_traces.py` (backend + agents; live OpenAI) |
| Modify | `scripts/export_contract.py` → `Contract` gains `replay_trace: ReplayTrace` and `replay_trace_index: ReplayTraceIndex`; `test_export_contract.py` assertion adds both keys |
| Generated | `app/replay/traces/s1_rod_packing/approve.json`, `…/reject_redraft.json`, `app/replay/traces/s5_sensor_drift/approve.json`, `…/reject_redraft.json`, `app/replay/traces/s4_planned_blowdown/approve.json`, `app/replay/traces/index.json`; regenerated contract files |

## `schemas/trace.py` (`extra="forbid"`, `frozen=True`)
- `TRACE_SCHEMA_VERSION: Final = 1`; `MAX_TRACE_BYTES: Final = 1_000_000`; `REPLAY_LABEL: Final = "Replay of a recorded AI run"`
- `TraceStep(t_ms: int = Field(ge=0), seq: int, node: str, kind: str, call_id: str | None, tool: str | None, summary: str, input: dict[str, Any] | None, output: dict[str, Any] | None)` — `input`/`output` only on `tool_result` steps (the source of every hover).
- `TraceApproval(t_ms: int, payload: dict[str, Any])`; `TraceDecision(t_ms: int, decision: dict[str, Any])`
- `TraceUsage(prompt_tokens: int, completion_tokens: int, cost_usd: str)`
- `ReplayTrace(schema_version: Literal[1], scenario_id: str, branch: Literal["approve", "reject_redraft"], label: Literal["Replay of a recorded AI run"], recorded_at: str, models: dict[str, str], start_sim_s: float, steps: list[TraceStep], approvals: list[TraceApproval], decisions: list[TraceDecision], final: dict[str, Any], outcome: str, usage: TraceUsage, simulated: Literal[True])` — `start_sim_s` = the event's `window_start_s + 600` (when the alarm appears and the agents start).
- `ReplayTraceIndex(schema_version: Literal[1], traces: dict[str, list[Literal["approve", "reject_redraft"]]])`

## `export_trace.py`
- `SECRET_PATTERNS: Final` — compiled regexes for `sk-[A-Za-z0-9_-]{16,}`, `lsv2_[A-Za-z0-9_]{16,}`, `postgres(?:ql)?://`, `Bearer\s+[A-Za-z0-9._-]{16,}`.
- `def assert_no_secrets(obj: Any) -> None` — walks every string; a match → `ValueError("trace contains a secret-like value")` (fail loudly; never strip silently).
- `def build_trace(*, scenario_id: str, branch: str, started_at: datetime, start_sim_s: float, steps: Sequence[dict], decisions: Sequence[dict], final: dict, outcome: str, usage: TraceUsage, models: Mapping[str, str], recorded_at: str) -> ReplayTrace` — `steps` are `agent_steps` rows (`created_at`, `seq`, `node`, `kind`, `call_id`, `tool`, `summary`, `payload`); `t_ms = int((created_at − started_at).total_seconds() · 1000)`; approval rows (`kind="approval"`) become `TraceApproval` with their payload; decision rows become `TraceDecision` (from `decisions` rows matched by `decided_at`); tool payloads become `input` / `output`; then `assert_no_secrets`.
- `def trace_bytes(trace: ReplayTrace) -> bytes` — same deterministic JSON as replay files; over `MAX_TRACE_BYTES` → `ValueError(f"{scenario_id}/{branch} trace is {n} bytes, budget {MAX_TRACE_BYTES}")`.
`export_trace.py` may import only `schemas` and `state` (structure rule); timestamps arrive as `datetime` objects from the caller.

## Tests (full code) — `app/agents/tests/test_export_trace.py`
```python
"""Trace export: timing, structure, secret guard, budget."""

from datetime import UTC, datetime, timedelta

import pytest

from plumetrace_agents.export_trace import assert_no_secrets, build_trace, trace_bytes
from plumetrace_agents.schemas.trace import TraceUsage

T0 = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)


def _row(seq: int, kind: str, ms: int, **kw: object) -> dict:
    return {"seq": seq, "kind": kind, "node": kw.get("node", "triage"), "call_id": kw.get("call_id"),
            "tool": kw.get("tool"), "summary": kw.get("summary", kind), "payload": kw.get("payload"),
            "created_at": T0 + timedelta(milliseconds=ms)}


def _trace(steps: list[dict]) -> object:
    return build_trace(scenario_id="s1_rod_packing", branch="approve", started_at=T0, start_sim_s=8400.0,
                       steps=steps, decisions=[], final={"status": "approved"}, outcome="approved",
                       usage=TraceUsage(prompt_tokens=10, completion_tokens=2, cost_usd="0.0100"),
                       models={"fast": "m-fast", "reasoning": "m-reason"}, recorded_at="2026-11-27")


def test_timing_and_tool_payloads() -> None:
    """t_ms is relative to the run start; tool results keep input and output."""
    trace = _trace([_row(0, "event", 0, node="detect_event"),
                    _row(1, "tool_result", 1250, call_id="call_001", tool="get_weather",
                         payload={"input": {"start_window": 1, "end_window": 2},
                                  "output": {"windows": 2}})])
    assert [s.t_ms for s in trace.steps] == [0, 1250]
    assert trace.steps[1].output == {"windows": 2}
    assert trace.label == "Replay of a recorded AI run" and trace.simulated is True


def test_secret_like_values_fail_loudly() -> None:
    """A key or connection string anywhere in the trace is an error."""
    with pytest.raises(ValueError, match="secret-like"):
        assert_no_secrets({"a": ["ok", {"b": "postgresql://u:p@h/db"}]})
    with pytest.raises(ValueError, match="secret-like"):
        _trace([_row(0, "tool_result", 5, payload={"input": {}, "output": {"x": "sk-" + "a" * 20}})])


def test_trace_bytes_is_deterministic() -> None:
    """Same trace, same bytes, trailing newline."""
    trace = _trace([_row(0, "event", 0)])
    assert trace_bytes(trace) == trace_bytes(trace) and trace_bytes(trace).endswith(b"\n")
```

## `scripts/record_traces.py` (paid — owner's yes first)
- Plan: S1 × {approve, reject_redraft}, S5 × {approve, reject_redraft}, S4 × {approve} (planned venting has no approval) = 5 live runs (mode `record`, `branch` set on the run row, tags `branch:<branch>`).
- Setup: `export_tracing_env` + `require_tracing` (exit 2 when tracing is off); `RunnerDeps(mode="record")` with the `OpenAIAgentLLM`, the `DbSpendLedger` (purpose `record`) and the **Postgres** checkpointer. Before the first run: `remaining_usd(ledger, cap) < Decimal("0.25")` (Task 11's `RECORDING_RESERVE_USD`) → exit 3 with `not enough of the spend cap left for 5 recordings` and do nothing.
- For each: call the graph-runner functions directly (no HTTP), wait for `awaiting_approval`; `approve` branch → approve; `reject_redraft` → reject with `PRESET_REJECT_REASON`, wait, approve revision 1. Wait for `completed`. Load the run's steps, decisions, final and usage from the DB (usage = sums over the run's `llm_calls` rows) → `build_trace` → write `app/replay/traces/<scenario>/<branch>.json` with `trace_bytes`. Print `<scenario>/<branch>: <bytes> bytes, $<cost>, <seconds> s`.
- Then write `index.json` (`ReplayTraceIndex`).
- A run that ends in `failed` / `aborted_budget` or a provenance failure → stop the script with exit code 1, write nothing for that branch, report it.
- Before running: state the 5 runs, the estimated cost (≈ 5 × $0.03 = $0.15; redraft branches make a second drafting pass), the spend so far and the cap; wait for the owner's yes. A `SpendCapReached` stop → exit 3, keep the files already written, report which branches are missing.

## Steps
- [ ] Tests → FAIL → implement → `uv run pytest app/agents -q` green.
- [ ] Contract update → `uv run python ../scripts/export_contract.py` → `npm run gen:types` → frontend checks green.
- [ ] Paid recording run (owner's yes). Check each file by eye: steps in order, approval payload present, no internal error text, numbers as expected for the scenario.
- [ ] `python -I .claude/skills/security-checks/scripts/secret_scan.py .` → `no secrets found` (covers `app/replay/`).
- [ ] Repo checks.
- [ ] **Docs.** REPLAY.md → "Agent traces" (format field by field, branches, timing, label, secret guard, size budget, how to re-record and what it costs against the $4 cap). Work-log; `STATUS.md` (last 5.12, next 5.13).
- [ ] **Commit** `feat(replay): add trace export and recorded agent traces for S1, S4 and S5`.
