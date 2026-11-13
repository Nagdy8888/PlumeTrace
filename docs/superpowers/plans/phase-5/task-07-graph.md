# Phase 5 · Task 7 — Routing, `build_graph`, checkpointer, all-branch tests

**Skills:** `plan-execution`, `langgraph` (+ `references/fundamentals/GUIDE.md`, `references/persistence/GUIDE.md`, `references/human-in-the-loop/GUIDE.md`), `project-documentation`.
**Docs to check first (Context7):** LangGraph 1.2.18 — `StateGraph`, `START`, `END`, `add_conditional_edges(source, path, path_map)`, `compile(checkpointer=...)`, `InMemorySaver` (`langgraph.checkpoint.memory`), `invoke` returning `__interrupt__`, `Command(resume=...)` (`langgraph.types`), `get_state(config).interrupts`, `recursion_limit`.

## Graph (design §6; code-defined edges; conditional only after `triage` and `approval`)
```text
START → detect_event → triage ─┬─ leak | inconclusive → locate_quantify → compliance → draft_outputs → approval
                               ├─ sensor_fault ───────────────────────────────────────→ draft_outputs
                               └─ planned_venting → log_vented_volume → finalize → END
approval ─┬─ approve | edit → finalize → END
          ├─ reject, revision_count == 0 → redraft → approval
          └─ reject, revision_count ≥ 1 → escalate → END
```

## Files (`app/agents/plumetrace_agents/`)
| Action | Path |
|---|---|
| Create | `routing.py`, `graph.py`, `checkpoint.py` |
| Create (tests) | `app/agents/tests/graph/conftest.py` (scripts), `test_routing.py`, `test_graph_branches.py`, `test_graph_shape.py` |
| Modify | `.claude/skills/langgraph/SKILL.md` → checkpointer paragraph: "`checkpoint.py` provides `memory_checkpointer()` for tests and `CHECKPOINT_SCHEMA = "langgraph"`; the backend builds the `PostgresSaver` (Task 10) in that schema and injects it." |

## Interfaces
`routing.py`:
- `def route_after_triage(state: AgentState) -> Literal["locate_quantify", "draft_outputs", "log_vented_volume"]` — `leak`/`inconclusive` → `locate_quantify`; `sensor_fault` → `draft_outputs`; `planned_venting` → `log_vented_volume`.
- `def route_after_approval(state: AgentState) -> Literal["finalize", "redraft", "escalate"]` — last decision `approve`/`edit` → `finalize`; `reject` with `revision_count == 0` → `redraft`; `reject` with `revision_count >= 1` → `escalate`. Missing decision → `ValueError("approval finished without a decision")`.
`graph.py`:
- `NODE_NAMES: Final = ("detect_event", "triage", "locate_quantify", "compliance", "draft_outputs", "approval", "redraft", "finalize", "escalate", "log_vented_volume")`
- `RECURSION_LIMIT: Final = 40`
- `def build_graph(tools: ToolProvider, llm: AgentLLM, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph` — `checkpointer is None` → `TypeError("a checkpointer is required (CLAUDE.md rule 6)")`; nodes from the Task 6 factories with `NodeDeps(tools, llm)`; edges exactly as drawn; `compile(checkpointer=checkpointer)`.
- `def run_config(run_id: str, *, tags: Sequence[str] = (), metadata: Mapping[str, str] = {}) -> dict[str, Any]` → `{"configurable": {"thread_id": run_id}, "recursion_limit": RECURSION_LIMIT, "tags": list(tags), "metadata": dict(metadata)}` (Task 11 fills tags/metadata).
`checkpoint.py`: `CHECKPOINT_SCHEMA: Final = "langgraph"`; `def memory_checkpointer() -> InMemorySaver`.

## Test scripts — `app/agents/tests/graph/conftest.py` (full code)
```python
"""Scripted model turns for full graph runs against the fake tool profiles."""

from typing import Any

import pytest

from plumetrace_agents.llm import ToolRequest, call, submit
from plumetrace_agents.nodes.approval import PRESET_REJECT_REASON


def sn(value: float, unit: str, call_id: str, path: str) -> dict[str, Any]:
    """A SourcedNumber as the model would send it."""
    return {"value": value, "unit": unit, "source_tool_call_id": call_id, "source_path": path}


RATE = sn(14.6, "kg/h", "call_003", "rate.p50")
DUE = sn(5.0, "d", "call_005", "rules[0].repair_deadline")


def s1_bundle(revision: int, actions: list[str]) -> dict[str, Any]:
    """S1 drafts (revision 0 or 1)."""
    return {
        "revision": revision,
        "work_order": {"title": "Repair K-202 rod packing (vent to VS-250)", "equipment_tag": "K-202",
                       "priority": "P2", "due_within": DUE,
                       "description": "Rod packing leak on K-202 routed to VS-250, estimated 14.6 kg/h.",
                       "actions": actions, "numbers": [RATE]},
        "shift_log": {"text": "Methane rise at AT-104; inversion located VS-250 with K-202 attributed. "
                              "Repair work order drafted.", "numbers": []},
        "report_line": {"source_category": "Reciprocating compressor rod packing vent", "ch4_rate": RATE,
                        "quantification": "level_4_site_measurement",
                        "text": "K-202 rod packing via VS-250: 14.6 kg/h.", "numbers": []},
        "rationale": "Drafted from the location and compliance results.",
    }


@pytest.fixture
def s1_script() -> dict[str, list[ToolRequest]]:
    """Leak path: triage, locate, compliance, drafts, one redraft."""
    return {
        "triage": [call("check_sensor_health", sensor_id="AT-104"),
                   call("get_permit_log", start_s=0, end_s=7800),
                   submit(classification="leak", evidence_call_ids=["call_001", "call_002"],
                          rationale="AT-104 agrees with AT-103 and AT-105 downwind; no permit covers it.")],
        "locate_quantify": [call("run_plume_inversion", start_window=10, end_window=16),
                            call("fuse_evidence", inversion_call_id="call_003"),
                            submit(status="located", top_anchor="VS-250.tip", attributed_unit="K-202",
                                   attribution_probability=sn(0.82, "1", "call_004", "probabilities[0].probability"),
                                   rate_p05=sn(8.1, "kg/h", "call_003", "rate.p05"), rate_p50=RATE,
                                   rate_p95=sn(27.3, "kg/h", "call_003", "rate.p95"), ogi_request_id=None,
                                   rationale="The inversion is conclusive and the header flow and K-202 packing agree.")],
        "compliance": [call("lookup_regulation_rule", event_class="leak_to_repair", emission_source="vent"),
                       call("compute_co2e", ch4=RATE, per="day"),
                       submit(event_class="leak_to_repair", rule_ids=["TEST-LDAR-REPAIR"], repair_deadline=DUE,
                              co2e_per_day=sn(10.4, "t CO2e/d", "call_006", "co2e"), super_emitter=False,
                              rationale="TEST-LDAR-REPAIR applies to a component leak found by monitoring.")],
        "draft_outputs": [submit(**s1_bundle(0, ["Isolate K-202", "Replace the rod packing", "Verify with OGI"]))],
        "redraft": [submit(**s1_bundle(1, ["Isolate and depressurise K-202", "Gas test before work",
                                           "Replace the rod packing", "Verify with OGI"]))],
    }


@pytest.fixture
def s5_script() -> dict[str, list[ToolRequest]]:
    """Sensor-fault path."""
    return {
        "triage": [call("check_sensor_health", sensor_id="AT-106"),
                   call("get_permit_log", start_s=0, end_s=5400),
                   submit(classification="sensor_fault", suspect_sensor="AT-106",
                          evidence_call_ids=["call_001", "call_002"],
                          rationale="AT-106 rises alone, against the wind, and its bump test is overdue.")],
        "draft_outputs": [submit(revision=0, work_order={
            "title": "Inspect and recalibrate AT-106", "equipment_tag": "AT-106", "priority": "P3",
            "due_within": None, "description": "AT-106 drifts at 0.6 ppm/h with no agreeing sensors.",
            "actions": ["Bump test AT-106", "Recalibrate or replace the sensor head"],
            "numbers": [sn(0.6, "ppm/h", "call_001", "drift_rate")]},
            shift_log={"text": "AT-106 alarm assessed as sensor drift; instrument ticket drafted.", "numbers": []},
            report_line=None, rationale="Instrument fault, so no emission report line.")],
    }


@pytest.fixture
def s4_script() -> dict[str, list[ToolRequest]]:
    """Planned-venting path."""
    return {
        "triage": [call("get_permit_log", start_s=0, end_s=7200),
                   call("check_sensor_health", sensor_id="AT-108"),
                   submit(classification="planned_venting", permit_reference="PTW-0412",
                          evidence_call_ids=["call_001", "call_002"],
                          rationale="PTW-0412 covers a K-201 blowdown to VS-250 in this window.")],
        "log_vented_volume": [call("compute_blowdown_mass", unit_tag="K-201"),
                              call("compute_co2e", ch4=sn(70.2, "kg", "call_003", "vented_ch4"), per="event"),
                              submit(vented_ch4=sn(70.2, "kg", "call_003", "vented_ch4"),
                                     co2e=sn(2.09, "t CO2e", "call_004", "co2e"), permit_reference="PTW-0412",
                                     rationale="PTW-0412 covers the K-201 blowdown and the release matched it.")],
    }


@pytest.fixture
def preset_reason() -> str:
    """The replay's preset rejection reason."""
    return PRESET_REJECT_REASON
```

## Tests (full code) — `test_graph_branches.py`
```python
"""Every branch of the graph with the scripted model, fake tools and an in-memory checkpointer."""

from typing import Any

import pytest
from langgraph.types import Command

from plumetrace_agents.checkpoint import memory_checkpointer
from plumetrace_agents.graph import build_graph, run_config
from plumetrace_agents.llm import ScriptedLLM
from plumetrace_agents.tools.fakes import FakeToolProvider

START = {"run_id": "r1", "scenario_id": "s1_rod_packing"}


def _graph(profile: str, script: dict) -> tuple[Any, ScriptedLLM, FakeToolProvider]:
    llm, tools = ScriptedLLM(script), FakeToolProvider(profile)
    return build_graph(tools, llm, memory_checkpointer()), llm, tools


def test_leak_approve(s1_script: dict) -> None:
    """Leak path pauses at approval and finishes approved after resume."""
    g, llm, tools = _graph("s1", s1_script)
    cfg = run_config("r1")
    first = g.invoke(START, cfg)
    payload = first["__interrupt__"][0].value
    assert payload["interrupt_id"] == "r1:r0" and payload["preset_reject_reason"]
    calls_before = list(tools.calls)
    done = g.invoke(Command(resume={"interrupt_id": "r1:r0", "action": "approve"}), cfg)
    assert done["outcome"] == "approved"
    assert tools.calls == calls_before          # resume re-ran approval without tool calls
    assert "approval" not in llm.seen           # and without an LLM call


def test_reject_once_then_approve(s1_script: dict, preset_reason: str) -> None:
    """First rejection triggers exactly one redraft and a second approval."""
    g, _, _ = _graph("s1", s1_script)
    cfg = run_config("r1")
    g.invoke(START, cfg)
    second = g.invoke(Command(resume={"interrupt_id": "r1:r0", "action": "reject", "reason": preset_reason}), cfg)
    assert second["__interrupt__"][0].value["interrupt_id"] == "r1:r1"
    assert second["__interrupt__"][0].value["bundle"]["revision"] == 1
    done = g.invoke(Command(resume={"interrupt_id": "r1:r1", "action": "approve"}), cfg)
    assert done["outcome"] == "approved" and done["revision_count"] == 1


def test_second_rejection_escalates(s1_script: dict, preset_reason: str) -> None:
    """A second rejection is final: escalate, no third draft."""
    g, _, _ = _graph("s1", s1_script)
    cfg = run_config("r1")
    g.invoke(START, cfg)
    g.invoke(Command(resume={"interrupt_id": "r1:r0", "action": "reject", "reason": preset_reason}), cfg)
    done = g.invoke(Command(resume={"interrupt_id": "r1:r1", "action": "reject",
                                    "reason": "Still missing the permit number."}), cfg)
    assert done["outcome"] == "escalated"
    assert done["final"]["status"] == "escalated_to_engineer"


def test_edit_with_override(s1_script: dict) -> None:
    """Edits change text; an override on a sourced number is kept and marked."""
    g, _, _ = _graph("s1", s1_script)
    cfg = run_config("r1")
    g.invoke(START, cfg)
    edits = {"shift_log_text": "Methane rise at AT-104; repair planned for the next shift.",
             "overrides": {"work_order.due_within": {"value": 3.0, "unit": "d", "reason": "Site manager instruction"}}}
    done = g.invoke(Command(resume={"interrupt_id": "r1:r0", "action": "edit", "edits": edits}), cfg)
    assert done["outcome"] == "edited"
    assert done["final"]["bundle"]["work_order"]["due_within"]["override"]["value"] == 3.0


def test_sensor_fault_path(s5_script: dict) -> None:
    """Sensor fault skips locate and compliance and drafts an instrument ticket."""
    g, llm, _ = _graph("s5", s5_script)
    cfg = run_config("r5")
    first = g.invoke({"run_id": "r5", "scenario_id": "s5_sensor_drift"}, cfg)
    assert first["__interrupt__"][0].value["bundle"]["report_line"] is None
    assert "locate_quantify" not in llm.seen and "compliance" not in llm.seen
    done = g.invoke(Command(resume={"interrupt_id": "r5:r0", "action": "approve"}), cfg)
    assert done["outcome"] == "approved"


def test_planned_venting_logs_without_approval(s4_script: dict) -> None:
    """Planned venting is logged with the vented mass; no interrupt."""
    g, _, _ = _graph("s4", s4_script)
    done = g.invoke({"run_id": "r4", "scenario_id": "s4_planned_blowdown"}, run_config("r4"))
    assert "__interrupt__" not in done
    assert done["outcome"] == "logged"
    assert done["final"]["vented"]["vented_ch4"]["value"] == 70.2


def test_stale_decision_is_refused(s1_script: dict) -> None:
    """A decision for another interrupt id is an error."""
    g, _, _ = _graph("s1", s1_script)
    cfg = run_config("r1")
    g.invoke(START, cfg)
    with pytest.raises(ValueError, match="does not match the pending approval"):
        g.invoke(Command(resume={"interrupt_id": "r1:r9", "action": "approve"}), cfg)


def test_checkpointer_is_required() -> None:
    """Compiling without a checkpointer is refused."""
    with pytest.raises(TypeError, match="checkpointer is required"):
        build_graph(FakeToolProvider("s1"), ScriptedLLM({}), None)  # type: ignore[arg-type]
```
`test_routing.py`: each mapping of both routers incl. the missing-decision `ValueError`.
`test_graph_shape.py`: `build_graph(...).get_graph()` has exactly the `NODE_NAMES` (+ `__start__`, `__end__`) and exactly these conditional sources: `triage`, `approval` (inspect edges with `conditional=True`).

Note for the executor: in `test_leak_approve`, `ScriptedLLM.seen` keys are only nodes that called the model; `detect_event`, `approval`, `finalize` never appear.

## Steps
- [ ] Tests → FAIL → implement → `uv run pytest app/agents -q` green (no network: the conftest from Task 1 is active).
- [ ] Draw the graph: `uv run python -c "…get_graph().draw_mermaid()…"` → save the Mermaid text into `docs/reference/AGENTS.md` (not a PNG — no network renderer).
- [ ] Repo checks; mypy strict.
- [ ] **Docs.** AGENTS.md → "Graph" (diagram, routing tables, recursion limit, checkpointer rule). Work-log; `STATUS.md` (last 5.7, next 5.8).
- [ ] **Commit** `feat(agents): add LangGraph graph with approval, one redraft and escalation`.
