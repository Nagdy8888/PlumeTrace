---
name: langgraph
description: Write or change LangGraph code in app/agents/plumetrace_agents - graph state, nodes, routing, interrupt() approval and resume, the ToolProvider contract, the Postgres (local Supabase) checkpointer, threads, and the replay trace export. Use for any agent-graph change in PlumeTrace.
---

# LangGraph (PlumeTrace)

One entry point for three upstream LangChain skills, kept unchanged (pinned upstream commit
`126c384d8552dcb476b226c244172186cc3f4328`) as references. Read only the part you need:

- [fundamentals](references/fundamentals/GUIDE.md): StateGraph, state schemas, nodes, edges, Command, streaming.
- [human-in-the-loop](references/human-in-the-loop/GUIDE.md): `interrupt`, validated resume input, replay and idempotency.
- [persistence](references/persistence/GUIDE.md): checkpointers, threads, durable state.

The references show several languages; PlumeTrace uses **Python only**.
Design: `docs/superpowers/specs/2026-11-12-plumetrace-design.md` (section 6). Layout: `repo-structure` skill.

## Where the agents live

`app/agents/` is its own uv workspace member with the package `plumetrace_agents`:
`graph.py` (`build_graph`), `state.py`, `routing.py`, `llm.py`, `checkpoint.py`, `tracing.py`,
`export_trace.py`, and the sub-packages `nodes/` (one module per node), `tools/`
(`protocol.py`, `registry.py`, `fakes.py`), `schemas/` (`tool_io.py`, `outputs.py`,
`decisions.py`) and `prompts/` (one `.md` per LLM node). Evaluations in `app/agents/evals/`,
tests in `app/agents/tests/`.

## Project rules that override the examples

- **Check the docs first.** Verify every API against the pinned `langgraph`,
  `langgraph-checkpoint-postgres` and `langchain-openai` versions in `app/uv.lock` with the
  Context7 docs tool before use.
- **No backend imports.** `plumetrace_agents` never imports `plumetrace`. Everything external is
  injected: `build_graph(tools: ToolProvider, llm: BaseChatModel, checkpointer: BaseCheckpointSaver)`.
  The backend implements `ToolProvider` in `app/backend/plumetrace/agent_tools/` and runs the
  graph from `app/backend/plumetrace/api/graph_runner.py`. `check_structure.py` enforces this.
- **Tool contract.** `tools/protocol.py` defines `ToolProvider` (a `typing.Protocol`) with one method
  per tool; inputs and results are Pydantic models in `schemas/tool_io.py`. `tools/registry.py`
  wraps the provider's methods as LangChain tools. `tools/fakes.py` is a deterministic provider
  for tests. Changing a tool means changing the schema, the protocol, the fake and the backend
  implementation in one change.
- **Graph shape is fixed by the design.** `detect_event → triage → (locate_quantify → compliance)
  → draft_outputs → approval → finalize | redraft | escalate`, plus `log_vented_volume` for planned
  venting. Conditional edges live in `routing.py` and exist only after `triage`
  (leak / sensor_fault / planned_venting) and after `approval` (approve-edit / reject-1st / reject-2nd).
  No free-roaming supervisor agent.
- **State** is one typed schema in `state.py`: event, evidence, tool results, drafts, operator
  decisions, `revision_count`. Use reducers deliberately; use `Overwrite` to replace a value.
- **Approval node:** `interrupt()` is called only in `nodes/approval.py`. The node does nothing
  before `interrupt()` except build the JSON payload, because **the node re-runs from its start
  on resume**: no LLM calls, no DB writes, no side effects before it. Resume only with
  `Command(resume=<decision>)` on the same `thread_id`; validate the decision with
  `schemas/decisions.py` (`approve | edit | reject`, reason, edited draft, interrupt id).
- **Redraft once:** reject #1 → `redraft` → `approval`; reject #2 → `escalate` → END.
  `revision_count` enforces it in code, never in a prompt.
- **Checkpointer:** `checkpoint.py` builds a `PostgresSaver` (sync) or `AsyncPostgresSaver` from a
  connection string **passed in by the backend** (local Supabase Postgres); call `.setup()` once
  at backend start-up (it creates the checkpoint tables). Tests use `InMemorySaver`.
  One run = one `thread_id` = the PlumeTrace `run_id`. Checkpoints are graph state, **not** the
  approval record: the backend writes operator decisions to `plumetrace.decisions` in Supabase.
- **Numbers come from tools.** LLM output is a Pydantic model whose numeric fields are copied from
  tool results; never let the model produce a rate, concentration or deadline itself.
- **Structured output:** every LLM node returns a validated Pydantic model; invalid → retry once →
  fail the node visibly.
- **Bounded runs:** `llm.py` sets `max_tokens`, `timeout`, `max_retries=1`; the backend invokes the
  graph with a `recursion_limit`.
- **Tests:** every graph change has a test that runs the compiled graph with a fake chat model
  and `tools/fakes.py` (no network, no DB, `LANGSMITH_TRACING=false`) through every branch,
  including interrupt + resume, redraft and escalate.
- **Tracing:** `tracing.py` builds the run config; see the `langsmith-trace` skill.
- **Trace export:** `export_trace.py` turns the graph event stream into
  `app/replay/traces/<scenario>/<branch>.json`; it strips secrets and never includes keys.
