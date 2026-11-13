# Phase 5 · Task 5 — `AgentLLM` protocol, OpenAI adapter, scripted fake, bounded tool loop

**Skills:** `plan-execution`, `langgraph`, `langsmith-trace`, `security-checks` (LLM risks), `agentic-council:oracle-prompt-engineering`, `project-documentation`.
**Docs to check first (Context7):** langchain-openai 1.7.3 `ChatOpenAI` (constructor names: `model`, `api_key`, `use_responses_api`, `reasoning_effort` (standard parameter; the older form is `reasoning={"effort": ...}`), `store`, `max_tokens` / `max_completion_tokens` (what it maps to on the Responses API), `timeout`, `max_retries`; `usage_metadata.output_token_details.reasoning`; how an `AIMessage` with `tool_calls` + `ToolMessage` are sent to the Responses API as `function_call` / `function_call_output` items; `bind_tools(..., tool_choice=..., parallel_tool_calls=...)`; `AIMessage.tool_calls`; `usage_metadata` incl. `input_token_details.cache_read`); langchain-core 1.7.3 messages (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`) and `convert_to_openai_tool`; langsmith 0.14.16 `traceable(run_type="tool", name=...)`. OpenAI model page for `gpt-6-luna`: function calling on Chat Completions only with reasoning effort `none` — that is why the adapter uses the Responses API. If a name differs in the pinned version, use the pinned version's documented name and note it in the work log (this is the one place the plan allows that, because the adapter is a thin translation layer).

## Design (fixed)
- Agents never see LangChain or OpenAI types. `plumetrace_agents.llm` defines its own small message
  and turn models and the `AgentLLM` protocol; the backend adapter (`plumetrace/api/openai_llm.py`)
  translates to `ChatOpenAI`. LangSmith traces the LangChain calls automatically when tracing is on.
- Structured output = a final pseudo-tool `submit_result` whose argument schema is the node's
  output model. Every turn must call a tool (`tool_choice="required"`), one at a time
  (`parallel_tool_calls=False`).
- Bounded loop per node: ≤ 6 real tool calls, then the model must submit; invalid submission
  (schema or provenance) → told why → **one** retry → `NodeOutputError` (fails visibly, rule 5).

## Files
| Action | Path |
|---|---|
| Create | `app/agents/plumetrace_agents/llm.py` |
| Create | `app/agents/plumetrace_agents/nodes/__init__.py`, `nodes/react.py`, `nodes/errors.py` |
| Create | `app/backend/plumetrace/api/openai_llm.py` |
| Create (tests) | `app/agents/tests/test_llm_scripted.py`, `app/agents/tests/nodes/test_react.py`, `app/backend/tests/api/test_openai_llm.py` |

## Interfaces
`llm.py`:
- `SUBMIT_TOOL_NAME: Final = "submit_result"`
- `Message(role: Literal["system", "user", "assistant", "tool"], content: str, tool_call_id: str | None = None, tool_calls: list[ToolRequest] = [])`
- `ToolRequest(id: str, name: str, arguments: dict[str, Any])`
- `Usage(model: str, prompt_tokens: int = 0, cached_tokens: int = 0, completion_tokens: int = 0, reasoning_tokens: int = 0, latency_ms: int = 0)` — `completion_tokens` **includes** `reasoning_tokens` (OpenAI bills reasoning as output); `reasoning_tokens` is stored for analysis only and never added to the cost a second time.
- `LLMTurn(requests: list[ToolRequest], usage: Usage)` — `requests` has exactly one item (validator).
- `class AgentLLM(Protocol)`: `def step(self, *, node: str, role: Literal["fast", "reasoning"], messages: Sequence[Message], tools: Sequence[ToolSpec], output_model: type[BaseModel]) -> LLMTurn` (`ToolSpec` from `schemas/tool_spec.py`; `llm.py` imports only `schemas`, as `check_structure.py` enforces)
- `class ScriptedLLM` (implements `AgentLLM`): `__init__(self, script: Mapping[str, Sequence[ToolRequest]], model: str = "scripted")`; each `step(node=…)` pops the next request of that node's list and returns it with `Usage(model, 100, 0, 20)` (reasoning 0, latency 0); records `self.seen[node]` (list of the message lists it received) and `self.roles[node]`; an exhausted list → `AssertionError(f"script for {node} exhausted")`.
- Helpers: `def call(name: str, **arguments: Any) -> ToolRequest` (id `f"req_{n}"` from a module counter) and `def submit(**fields: Any) -> ToolRequest` (`name=SUBMIT_TOOL_NAME`).

`nodes/errors.py`: `class NodeOutputError(RuntimeError)` with `node: str`, `errors: list[str]`; message `f"{node} produced no valid output: {'; '.join(errors)}"`.

`nodes/react.py`:
- `MAX_TOOL_CALLS: Final = 6`; `MAX_TURNS: Final = MAX_TOOL_CALLS + 3`.
- `@dataclass(frozen=True) class StepEvent: node: str; kind: Literal["tool_call", "tool_result", "submit_rejected", "submitted"]; call_id: str | None; tool: str | None; summary: str; payload: dict[str, Any] | None = None` — for `tool_result` events `payload = {"input": record.input, "output": record.output}` (or `{"input": …, "error": record.error}`), taken from the recorder; for `submitted` events `payload = {"output": model.model_dump(mode="json")}`; `None` for the other kinds.
- `def run_bounded(*, node: str, role: Literal["fast", "reasoning"], llm: AgentLLM, tools: Sequence[ToolSpec], output_model: type[T], system_prompt: str, user_prompt: str, recorder: ToolRecorder, on_step: Callable[[StepEvent], None] = lambda e: None) -> tuple[T, list[Usage]]`:
  1. `messages = [system, user]`; `tool_calls = 0`; `rejections = 0`; `usages = []`.
  2. Loop at most `MAX_TURNS` times: `turn = llm.step(...)`; append `turn.usage`; `req = turn.requests[0]`; append the assistant message with that request.
  3. `req.name == SUBMIT_TOOL_NAME`: validate `output_model.model_validate(req.arguments)` then `enforce(model, recorder.records)`. OK → `on_step(submitted)` → return. Error → if `rejections == 0`: append a tool message `"submit_result rejected: <errors joined by '; ', ≤ 800 chars>. Fix only these problems and submit again."`, `rejections = 1`, `on_step(submit_rejected)`; else raise `NodeOutputError(node, errors)`.
  4. Real tool: unknown name → tool message `{"error": "unknown tool <name>"}` (counts as a call). `tool_calls >= MAX_TOOL_CALLS` → tool message `{"error": "tool budget exhausted: call submit_result now"}` without running it. Otherwise `out = traceable(run_type="tool", name=spec.name)(spec.run)(req.arguments)` (`from langsmith import traceable`; a LangSmith tool span per call with its input and output when tracing is on, a plain call when it is off), `tool_calls += 1`, tool message = `json.dumps(out, sort_keys=True)`, `on_step(tool_call)` + `on_step(tool_result)` (summary: tool name + `"ok"` / the error text).
  5. Loop ends without a valid submit → `NodeOutputError(node, ["no submit_result within the turn limit"])`.
- The `submit_result` tool spec passed to the LLM is built here from `output_model` (name `SUBMIT_TOOL_NAME`, description `"Submit the final structured result for this step. Every number must be a SourcedNumber copied from a tool output."`).

`app/backend/plumetrace/api/openai_llm.py`:
- `REASONING_EFFORT: Final[Mapping[str, str]] = {"fast": "low", "reasoning": "medium"}` (owner decision 2026-11-13: one model, two efforts).
- `class OpenAIAgentLLM` (implements `AgentLLM`): `__init__(self, *, fast_model: str, reasoning_model: str, api_key: SecretStr, max_tokens: int = 4000, timeout_s: float = 60.0)`; one `ChatOpenAI` per role, created lazily with `model=<role model>`, `api_key=api_key`, `use_responses_api=True`, `reasoning_effort=REASONING_EFFORT[role]`, `store=False`, `max_tokens=max_tokens` (the output budget includes reasoning tokens — hence 4000, not 1500), `timeout=timeout_s`, `max_retries=1`; **no** `temperature` argument (reasoning models reject it). Reasoning items are **not** sent back between turns (our own `Message` type carries only tool calls), so each turn reasons afresh — accepted cost, documented in AGENTS.md.
- `step(...)`: convert `Message`s (system → `SystemMessage`, user → `HumanMessage`, assistant → `AIMessage(content="", tool_calls=[{"id", "name", "args"}])`, tool → `ToolMessage(content, tool_call_id)`); tools → `convert_to_openai_tool(spec.input_model)` with `name`/`description` replaced by the spec's; the submit tool from `output_model`; `bind_tools(all, tool_choice="required", parallel_tool_calls=False)`; `invoke(messages, config={"run_name": node, "tags": [f"node:{node}", f"role:{role}"], "metadata": {"reasoning_effort": REASONING_EFFORT[role]}})`, timed with `time.monotonic()` → `latency_ms`; map `ai.tool_calls[0]` → `ToolRequest`; usage from `ai.usage_metadata` (`input_tokens`, `output_tokens`, cached = `input_token_details.get("cache_read", 0)`, reasoning = `output_token_details.get("reasoning", 0)`); zero tool calls → the adapter repeats the call **once**; still none → `NoToolCallError("model returned no tool call")` (`class NoToolCallError(ValueError)` in `openai_llm.py`, attribute `usage: Usage` = both calls summed, so Task 10's budget wrapper can still record the billed tokens before re-raising), which propagates out of the node (it fails visibly). Both calls are reported: the `Usage` of a repeated call is the **sum** of both calls (tokens and latency), so the spend ledger sees every billed token.
- `def build_agent_llm(settings: Settings) -> OpenAIAgentLLM` — `require_models` + `require_openai_key`.

## Tests (full code) — `app/agents/tests/nodes/test_react.py`
```python
"""Tests for the bounded tool loop with a scripted model and fake tools."""

import pytest

from plumetrace_agents.llm import ScriptedLLM, call, submit
from plumetrace_agents.nodes.errors import NodeOutputError
from plumetrace_agents.nodes.react import MAX_TOOL_CALLS, run_bounded
from plumetrace_agents.schemas.outputs import TriageOutput
from plumetrace_agents.tools.fakes import FakeToolProvider
from plumetrace_agents.tools.recorder import ToolRecorder
from plumetrace_agents.tools.registry import build_tools

GOOD = {"classification": "leak", "rationale": "Two downwind sensors agree with the wind; no permit open.",
        "evidence_call_ids": ["call_001", "call_002"]}


def _run(script: list, recorder: ToolRecorder | None = None) -> tuple[TriageOutput, ToolRecorder, ScriptedLLM]:
    rec = recorder or ToolRecorder()
    llm = ScriptedLLM({"triage": script})
    out, _ = run_bounded(node="triage", role="fast", llm=llm,
                         tools=build_tools(FakeToolProvider("s1"), rec, "triage"),
                         output_model=TriageOutput, system_prompt="sys", user_prompt="user",
                         recorder=rec)
    return out, rec, llm


def test_tools_then_submit() -> None:
    """Two tool calls are recorded and the validated output is returned."""
    out, rec, _ = _run([call("check_sensor_health", sensor_id="AT-104"),
                        call("get_permit_log", start_s=0, end_s=7800), submit(**GOOD)])
    assert out.classification == "leak"
    assert list(rec.records) == ["call_001", "call_002"]


def test_one_rejected_submit_is_retried() -> None:
    """An invalid submit gets the errors back once; the fixed submit passes."""
    bad = {**GOOD, "rationale": "Leak of 42 kg/h near K-202, very likely real."}
    out, _, llm = _run([call("check_sensor_health", sensor_id="AT-104"),
                        call("get_permit_log", start_s=0, end_s=7800), submit(**bad), submit(**GOOD)])
    assert out.rationale == GOOD["rationale"]
    last_messages = llm.seen["triage"][-1]
    assert "submit_result rejected" in last_messages[-1].content


def test_two_rejected_submits_fail_visibly() -> None:
    """A second invalid submit raises NodeOutputError."""
    bad = {**GOOD, "evidence_call_ids": []}
    with pytest.raises(NodeOutputError, match="triage produced no valid output"):
        _run([submit(**bad), submit(**bad)])


def test_tool_budget_is_enforced() -> None:
    """After six real calls further calls are refused, not executed."""
    script = [call("check_sensor_health", sensor_id="AT-104") for _ in range(MAX_TOOL_CALLS + 1)]
    script.append(submit(**{**GOOD, "evidence_call_ids": ["call_001"]}))
    _, rec, llm = _run(script)
    assert len(rec.records) == MAX_TOOL_CALLS
    assert "tool budget exhausted" in llm.seen["triage"][-1][-1].content


def test_unknown_tool_is_reported_to_the_model() -> None:
    """A made-up tool name returns an error message and runs nothing."""
    _, rec, llm = _run([call("delete_everything"), call("check_sensor_health", sensor_id="AT-104"),
                        submit(**{**GOOD, "evidence_call_ids": ["call_001"]})])
    assert "unknown tool delete_everything" in llm.seen["triage"][1][-1].content
    assert list(rec.records) == ["call_001"]
```
`test_llm_scripted.py`: exhausted script raises `AssertionError`; `seen` records messages; `LLMTurn` with two requests fails validation.
`test_openai_llm.py` (no network): monkeypatch `ChatOpenAI` in the module with a stub class whose `bind_tools(...)` records its kwargs and whose `invoke` returns an `AIMessage` with one tool call and `usage_metadata`; assert the constructor got `use_responses_api=True`, `store=False`, `reasoning_effort="low"` for `fast` and `"medium"` for `reasoning`, and no `temperature`; `tool_choice == "required"`, `parallel_tool_calls is False`, the submit tool is present, usage is mapped (cached and reasoning tokens, `latency_ms >= 0`), the role picks the right model; a stub returning zero tool calls twice → `NoToolCallError` whose `usage` holds both calls' tokens; a stub returning zero tool calls once, then one → the returned `Usage` holds the sum of both calls' tokens.

## Steps
- [ ] Tests → FAIL → implement → `uv run pytest app/backend app/agents -q` green; mypy, ruff.
- [ ] **No live call in this task.** The smoke test `scripts/smoke_llm.py` (build `OpenAIAgentLLM` from settings, ask the fast role to call `submit_result` for a tiny model `{"ok": true}`, print only the tool name and token counts — never the key) is written here but **run first in Task 10**, after the spend ledger and the tracing guard exist, because every paid call must be counted against the $4 cap and traced. Its test is a `--help` run only.
- [ ] Repo checks.
- [ ] **Docs.** AGENTS.md → "Model interface" (protocol, submit pseudo-tool, roles = one model `gpt-6-luna` at reasoning effort low / medium, Responses API and why, `store=False`, reasoning tokens counted as output, no reasoning items carried between turns, why no temperature, tool spans) and "Bounded tool loop" (steps 1–5, limits, retry rule). Work-log; `STATUS.md` (last 5.5, next 5.6).
- [ ] **Commit** `feat(agents): add AgentLLM protocol, OpenAI adapter and bounded tool loop`.
