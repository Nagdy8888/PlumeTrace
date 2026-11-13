# Phase 5 · Task 2 — Schemas (tool I/O, agent outputs, drafts, decisions) and the provenance guard

**Skills:** `plan-execution`, `langgraph`, `fastapi` (Pydantic), `project-documentation`.
**Docs to check first (Context7):** Pydantic 2.14 (`ConfigDict(extra="forbid", frozen=True)`, `Field` constraints, `model_validator`, discriminated unions are **not** used).

**Why:** design §6 "Number provenance": every numeric field an agent outputs is a `SourcedNumber`
pointing at the tool call that produced it, and a **code guard** rejects any mismatch. Tool inputs
never carry free numbers from the LLM: a tool that needs an engineering number takes a
`SourcedNumber` (checked by the same guard) or a tool-call id.

## Files (all in `app/agents/plumetrace_agents/schemas/`; every model `extra="forbid"`, `frozen=True`)
| File | Top-level definitions (≤ 12 each) |
|---|---|
| `common.py` | `Quantity`, `OperatorOverride`, `SourcedNumber`, `TagSummary`, `LogEntryOut`, `NoArgsIn`, `TimeRangeIn`, `WindowRangeIn` |
| `tool_call.py` | `ToolCallRecord` |
| `tool_io_triage.py` | `SensorHistoryIn`, `SensorSeries`, `SensorHistoryOut`, `WeatherOut`, `PermitLogOut`, `ProcessTagsIn`, `ProcessTagsOut`, `SensorHealthIn`, `SensorHealthOut` |
| `tool_io_locate.py` | `CandidateProbability`, `RateInterval`, `InversionOut`, `FuseIn`, `FusionOut`, `AreaIn`, `OgiFinding`, `OgiResultsOut`, `OgiRequestIn`, `OgiRequestOut` |
| `tool_io_process.py` | `VentHeaderOut`, `PackingTempsOut`, `FlareStatusOut`, `TankStatusOut`, `InventoryIn`, `InventoryRow`, `InventoryOut` |
| `tool_io_compliance.py` | `RuleQueryIn`, `RuleRef`, `RulesOut`, `Co2eIn`, `Co2eOut`, `BlowdownIn`, `BlowdownOut` |
| `outputs.py` | `TriageOutput`, `LocateOutput`, `ComplianceOutput`, `VentedVolumeOutput` |
| `drafts.py` | `WorkOrderDraft`, `ShiftLogDraft`, `ReportLineDraft`, `DraftBundle` |
| `decisions.py` | `DraftEdits`, `OperatorDecision`, `EvidenceRef`, `ApprovalPayload` |
| `provenance.py` | `ProvenanceError`, `resolve_path`, `check_number`, `iter_sourced`, `check_output`, `check_text`, `enforce` |
Tests: `app/agents/tests/schemas/test_common.py`, `test_decisions.py`, `test_provenance.py`.

## Model definitions (exact field names and constraints)
`common.py`:
- `Quantity(value: float, unit: str)` — `unit` one of `UNITS = ("ppm", "ppm/h", "kg/h", "kg", "m3", "t CO2e", "t CO2e/d", "m/s", "deg", "degC", "kPa", "kPag", "Sm3/h", "1", "d", "h", "%")`; `value` finite (validator rejects NaN/inf).
- `OperatorOverride(value: float, unit: str, reason: str = Field(min_length=3, max_length=300))`
- `SourcedNumber(value: float, unit: str, source_tool_call_id: str = Field(pattern=r"^call_[0-9]{3}$"), source_path: str = Field(min_length=1, max_length=120), override: OperatorOverride | None = None)` — `source_path` points at a `Quantity` inside the tool output (`resolve_path` syntax below).
- `TagSummary(tag: str, before: Quantity, after: Quantity, change: Quantity)` — means of 60 s values before / after the event window start.
- `LogEntryOut(t_s: float, kind: str, tag: str | None, text: str)`
- `NoArgsIn()` (empty); `TimeRangeIn(start_s: float = Field(ge=0), end_s: float = Field(ge=0))` (validator `end_s ≥ start_s`); `WindowRangeIn(start_window: int = Field(ge=0), end_window: int = Field(ge=0))` (validator `end ≥ start`, span ≤ 36).

`tool_call.py`: `ToolCallRecord(call_id: str (pattern as above), node: str, tool: str, input: dict[str, Any], output: dict[str, Any] | None, error: str | None, duration_ms: int = Field(ge=0))` — exactly one of `output` / `error` is set (validator).

`tool_io_triage.py`:
- `SensorHistoryIn(sensor_ids: list[str] = Field(min_length=1, max_length=8), start_window: int, end_window: int)` (same validators as `WindowRangeIn`)
- `SensorSeries(sensor_id: str, window_start_s: list[float], mean_ppm: list[float | None], baseline: Quantity)`
- `SensorHistoryOut(series: list[SensorSeries])`
- `WeatherOut(mean_wind_speed: Quantity, mean_wind_from: Quantity, stability_mode: str, windows: int, attribution: str)`
- `PermitLogOut(entries: list[LogEntryOut])`
- `ProcessTagsIn(tags: list[str] = Field(min_length=1, max_length=10))`; `ProcessTagsOut(tags: list[TagSummary])`
- `SensorHealthIn(sensor_id: str)`; `SensorHealthOut(sensor_id: str, agreeing_sensors: list[str], wind_consistent: bool, drift_rate: Quantity, verdict_hint: Literal["consistent", "suspect_drift", "suspect_stuck"])`

`tool_io_locate.py`:
- `CandidateProbability(anchor_id: str, probability: Quantity)` (unit `"1"`)
- `RateInterval(p05: Quantity, p50: Quantity, p95: Quantity)` (unit `"kg/h"`)
- `InversionOut(top_id: str, top_probability: Quantity, candidates: list[CandidateProbability], rate: RateInterval | None, inconclusive: bool, reason: str | None, windows_used: int)` — `candidates` = top 5 incl. `NONE`.
- `FuseIn(inversion_call_id: str (pattern))` — the backend reads that call's recorded output; the LLM passes no numbers.
- `FusionOut(probabilities: list[CandidateProbability], top_id: str, top_probability: Quantity, applied: list[str])` (`applied` = evidence reasons, text)
- `AreaIn(area_tag: str)`; `OgiFinding(component: str, rate: Quantity, note: str)`; `OgiResultsOut(area_tag: str, last_survey_utc: str | None, findings: list[OgiFinding])`
- `OgiRequestIn(area_tag: str, reason: str = Field(min_length=10, max_length=300))`; `OgiRequestOut(request_id: str, status: Literal["requested"])`

`tool_io_process.py`:
- `VentHeaderOut(header: TagSummary, uncertainty: Quantity)` (FT-250)
- `PackingTempsOut(units: list[TagSummary], hottest_unit: str)` (TT-201P/202P/203P; `hottest_unit` is the unit tag, e.g. `K-202`)
- `FlareStatusOut(flow: TagSummary, tip_temperature: TagSummary, pilot_lit: bool)`
- `TankStatusOut(tanks: list[TagSummary], vru_online: bool)`
- `InventoryIn(tags: list[str] = Field(min_length=1, max_length=10))`; `InventoryRow(tag: str, valves: int, connectors: int, open_ended_lines: int, pressure_relief_valves: int, bottom_up: Quantity)`; `InventoryOut(rows: list[InventoryRow], source: str)`

`tool_io_compliance.py`:
- `RuleQueryIn(event_class: Literal["leak_to_repair", "venting", "flaring", "instrument_fault"], emission_source: Literal["vent", "component_leak", "flare", "tank", "none"])`
- `RuleRef(rule_id: str, title: str, citation: str, url: str, basis: str, repair_deadline: Quantity | None, applies_to_site: Literal["policy", "reporting", "import_context"])`
- `RulesOut(rules: list[RuleRef], table_version: str)`
- `Co2eIn(ch4: SourcedNumber, per: Literal["day", "event"])` — `ch4` in `kg/h` for `day` (result unit `t CO2e/d`) or `kg` for `event` (result unit `t CO2e`); a unit that does not fit `per` → validation error.
- `Co2eOut(co2e: Quantity, gwp100: Quantity, gwp_source: str)`
- `BlowdownIn(unit_tag: str)`; `BlowdownOut(unit_tag: str, volume: Quantity, vented_ch4: Quantity, gas_mass: Quantity)`

`outputs.py`:
- `TriageOutput(classification: Literal["leak", "sensor_fault", "planned_venting", "inconclusive"], rationale: str = Field(min_length=20, max_length=600), evidence_call_ids: list[str] = Field(min_length=1), cited_log_t_s: list[float] = [], suspect_sensor: str | None = None, permit_reference: str | None = None)` — validators: `sensor_fault` ⇒ `suspect_sensor` set; `planned_venting` ⇒ `permit_reference` set.
- `LocateOutput(status: Literal["located", "inconclusive"], top_anchor: str | None, attributed_unit: str | None, attribution_probability: SourcedNumber | None, rate_p05: SourcedNumber | None, rate_p50: SourcedNumber | None, rate_p95: SourcedNumber | None, ogi_request_id: str | None, rationale: str = Field(min_length=20, max_length=600))` — `located` ⇒ `top_anchor`, `rate_p50`, `rate_p05`, `rate_p95` set; `inconclusive` ⇒ `ogi_request_id` set.
- `ComplianceOutput(event_class: Literal["leak_to_repair", "venting", "flaring", "instrument_fault"], rule_ids: list[str] = Field(min_length=1), repair_deadline: SourcedNumber | None, co2e_per_day: SourcedNumber | None, super_emitter: bool, rationale: str = Field(min_length=20, max_length=600))`
- `VentedVolumeOutput(vented_ch4: SourcedNumber, co2e: SourcedNumber, permit_reference: str, rationale: str = Field(min_length=20, max_length=400))`

`drafts.py`:
- `WorkOrderDraft(title: str = Field(max_length=80), equipment_tag: str, priority: Literal["P1", "P2", "P3"], due_within: SourcedNumber | None, description: str = Field(max_length=1200), actions: list[str] = Field(min_length=1, max_length=6), numbers: list[SourcedNumber] = [])`
- `ShiftLogDraft(text: str = Field(min_length=20, max_length=600), numbers: list[SourcedNumber] = [])`
- `ReportLineDraft(source_category: str, ch4_rate: SourcedNumber, quantification: Literal["level_4_site_measurement"], text: str = Field(max_length=400), numbers: list[SourcedNumber] = [])`
- `DraftBundle(revision: int = Field(ge=0, le=1), work_order: WorkOrderDraft | None, shift_log: ShiftLogDraft, report_line: ReportLineDraft | None, rationale: str = Field(max_length=400))`

`decisions.py`:
- `DraftEdits(work_order_description: str | None = None, work_order_actions: list[str] | None = None, shift_log_text: str | None = None, report_line_text: str | None = None, overrides: dict[str, OperatorOverride] = {})` — `overrides` keys are field paths inside `DraftBundle` such as `work_order.due_within` or `report_line.ch4_rate`; only paths that hold a `SourcedNumber` are allowed (validated in `nodes/finalize.py`, Task 6).
- `OperatorDecision(interrupt_id: str, action: Literal["approve", "edit", "reject"], reason: str | None = None, edits: DraftEdits | None = None)` — validators: `reject` ⇒ `reason` with 3–500 chars after strip; `edit` ⇒ `edits` set; `approve` ⇒ `edits is None`.
- `EvidenceRef(call_id: str, tool: str, summary: str)`
- `ApprovalPayload(interrupt_id: str, run_id: str, revision: int, bundle: DraftBundle, evidence: list[EvidenceRef], preset_reject_reason: str | None)`

## Provenance guard — `provenance.py`
- `class ProvenanceError(ValueError)` — `errors: list[str]`; `str()` joins them with `"; "`.
- `resolve_path(obj: Any, path: str) -> Any` — dotted keys and `[n]` indices (`rate.p50`, `candidates[0].probability`, `units[1].after`); a missing key / index → `KeyError(path)`.
- `check_number(n: SourcedNumber, calls: Mapping[str, ToolCallRecord]) -> str | None` — returns an error text or `None`:
  1. `n.override is not None` → `None` (operator overrides are excluded, design §6).
  2. call id unknown → `"unknown tool call call_123"`; call has `error` → `"tool call call_123 failed"`.
  3. `resolve_path(call.output, n.source_path)` must be a dict with `value` and `unit` (a `Quantity`) → else `"call_123:rate.p50 is not a quantity"`.
  4. unit must be equal → else `"unit kg/h does not match source unit ppm"`.
  5. value: let `d` = number of decimals in `repr(n.value)` capped at 6 (`14.2` → 1, `14.0` → 1, `14` (int-valued float shown as `14.0`) → 1); allowed if `abs(n.value − src) ≤ 0.5·10^(−d) + 1e-9`; else `"value 14.9 does not match source 14.23 (call_123:rate.p50)"`.
- `iter_sourced(model: BaseModel) -> Iterator[tuple[str, SourcedNumber]]` — every `SourcedNumber` anywhere in the model (fields, lists, nested models), with its dotted path.
- `check_output(model: BaseModel, calls) -> list[str]` — `check_number` for each; error texts prefixed with the field path.
- `check_text(text: str, sourced: Sequence[SourcedNumber]) -> list[str]`:
  1. Remove protected tokens (in this order, each regex replaced by a space): ISO dates `\b\d{4}-\d{2}-\d{2}\b`; times `\b\d{1,2}:\d{2}(?::\d{2})?\b`; regulation numbers `\b\d{4}/\d{3,4}\b`; article references `\b(?:Art\.|Article|Section|§)\s*\d+[a-z]?(?:\(\d+[a-z]?\))*`; `OGMP 2\.0`; `\bLevel\s+[1-5]\b`; priorities `\bP[1-3]\b`; equipment / instrument / permit tags with optional anchor `\b[A-Z]{1,4}-\d{2,4}[A-Z]?(?:\.[a-z_]+)?\b`; rule ids `\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}\b`.
  2. Every remaining number token `(?<![\w.])\d+(?:\.\d+)?` must equal one of the allowed strings: for each sourced number `v` (and `100·v` when the unit is `"1"`): `f"{v:.0f}"`, `f"{v:.1f}"`, `f"{v:.2f}"`, `f"{v:.3f}"`.
  3. Errors: `"number 42 in text is not from a tool"`.
- `enforce(model: BaseModel, calls) -> None` — `check_output` + `check_text` over every `str` field named `rationale`, `description`, `text`, every item of `actions`, using all `SourcedNumber`s of the same model; raises `ProvenanceError` if any error.

## Tests (full code) — `app/agents/tests/schemas/test_provenance.py`
```python
"""Tests for the number-provenance guard (design section 6)."""

import pytest

from plumetrace_agents.schemas.common import OperatorOverride, SourcedNumber
from plumetrace_agents.schemas.drafts import ShiftLogDraft
from plumetrace_agents.schemas.provenance import (
    ProvenanceError,
    check_number,
    check_text,
    enforce,
    resolve_path,
)
from plumetrace_agents.schemas.tool_call import ToolCallRecord

CALL = ToolCallRecord(
    call_id="call_001",
    node="locate_quantify",
    tool="run_plume_inversion",
    input={"start_window": 12, "end_window": 15},
    output={
        "rate": {"p05": {"value": 7.81, "unit": "kg/h"}, "p50": {"value": 14.23, "unit": "kg/h"},
                 "p95": {"value": 26.0, "unit": "kg/h"}},
        "candidates": [{"anchor_id": "VS-250.tip", "probability": {"value": 0.874, "unit": "1"}}],
    },
    error=None,
    duration_ms=12,
)
CALLS = {"call_001": CALL}


def sn(value: float, path: str = "rate.p50", unit: str = "kg/h") -> SourcedNumber:
    """Build a sourced number pointing at CALL."""
    return SourcedNumber(value=value, unit=unit, source_tool_call_id="call_001", source_path=path)


def test_resolve_path() -> None:
    """Dotted keys and list indices resolve; missing parts raise KeyError."""
    assert resolve_path(CALL.output, "candidates[0].probability")["value"] == 0.874
    with pytest.raises(KeyError):
        resolve_path(CALL.output, "rate.p99")


@pytest.mark.parametrize("value", [14.23, 14.2, 14.0 + 0.2])
def test_rounding_to_shown_precision_is_allowed(value: float) -> None:
    """A value rounded to fewer decimals still matches its source."""
    assert check_number(sn(value), CALLS) is None


def test_invented_value_unit_and_call_are_rejected() -> None:
    """Wrong value, wrong unit, unknown call, non-quantity path."""
    assert "does not match source" in (check_number(sn(14.9), CALLS) or "")
    assert "unit" in (check_number(sn(14.23, unit="ppm"), CALLS) or "")
    bad_call = SourcedNumber(value=1.0, unit="kg/h", source_tool_call_id="call_009", source_path="rate.p50")
    assert check_number(bad_call, CALLS) == "unknown tool call call_009"
    assert "is not a quantity" in (check_number(sn(1.0, path="rate"), CALLS) or "")


def test_operator_override_is_excluded() -> None:
    """An explicit operator override is not checked against the tool."""
    n = SourcedNumber(value=99.0, unit="kg/h", source_tool_call_id="call_001", source_path="rate.p50",
                      override=OperatorOverride(value=99.0, unit="kg/h", reason="Field meter reading"))
    assert check_number(n, CALLS) is None


def test_text_may_only_repeat_sourced_numbers() -> None:
    """Tags, times, articles and percentages of probabilities are fine; a new number is not."""
    nums = [sn(14.2), sn(0.874, path="candidates[0].probability", unit="1")]
    ok = ("K-202 rod packing via VS-250.tip at 09:10, about 14.2 kg/h (87% probable); "
          "repair under the operator policy modelled on EU 2024/1787 Art. 14(1), priority P2, PTW-0412.")
    assert check_text(ok, nums) == []
    assert check_text("Estimated 42 kg/h at K-202.", nums) == ["number 42 in text is not from a tool"]


def test_enforce_raises_with_all_errors() -> None:
    """enforce collects field and text errors into one ProvenanceError."""
    draft = ShiftLogDraft(text="Leak at VS-250 estimated 31 kg/h, see work order.", numbers=[sn(14.9)])
    with pytest.raises(ProvenanceError) as exc:
        enforce(draft, CALLS)
    assert len(exc.value.errors) == 2
```
`test_common.py`: `Quantity` rejects `nan`, `inf` and an unknown unit; `TimeRangeIn(start_s=10, end_s=5)` fails; `WindowRangeIn(0, 40)` fails (span > 36); `ToolCallRecord` with both `output` and `error` fails; `SourcedNumber` with `source_tool_call_id="x"` fails.
`test_decisions.py`: reject without reason fails, reject with `"  ab "` fails (strip → 2 chars), reject with `"Wrong unit tagged"` passes; edit without edits fails; approve with edits fails; `TriageOutput(classification="sensor_fault", …)` without `suspect_sensor` fails; `LocateOutput(status="located", …)` without rates fails.

## Steps
- [ ] Tests → FAIL → implement the models, then the guard → `uv run pytest app/agents -q` green; mypy strict clean.
- [ ] Repo checks (each file ≤ 300 lines and ≤ 12 top-level definitions — the table above is designed for that).
- [ ] **Docs.** AGENTS.md → "Schemas" (every model, field meaning, units list) and "Number provenance" (the guard's rules 1–5, text rule with every protected pattern, override exclusion). Work-log; `STATUS.md` (last 5.2, next 5.3).
- [ ] **Commit** `feat(agents): add tool, output, draft and decision schemas with the provenance guard`.
