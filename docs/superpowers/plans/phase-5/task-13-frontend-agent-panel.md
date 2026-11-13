# Phase 5 · Task 13 — Frontend: agent runs in the data layer, agent timeline panel, candidate highlight

**Skills:** `plan-execution`, `frontend-structure`, `frontend-design` (+ `control-room-workspace.md` → "States and interactions"), `shadcn` (tooltip, tabs), `impeccable`, `project-documentation`. Read `.ux-profile.md`.
**Docs to check first (Context7):** browser `WebSocket` API; Vitest 5 fake timers (`vi.useFakeTimers`, `vi.advanceTimersByTime`); Radix Tooltip via the shadcn wrapper.

## Fixed decisions
- Run messages and decision types are **generated** from the backend models: `scripts/export_contract.py` gains `run_message: RunMessageUnion` (a `RootModel` union of the five message models, field `type` as discriminator), `operator_decision: OperatorDecision`, `approval_payload: ApprovalPayload`. Never hand-write these TS types.
- Live: the run starts automatically when the playback clock passes the first alarm (window close) of the scenario; the clock pauses while the run is `running` and resumes (stays paused, play enabled) at `awaiting_approval` or the end — design §6 "Simulation time pauses while the agents work".
- Replay: the same, driven by the recorded trace; steps appear with their original `t_ms` timing; a `Show all steps` button flushes the waiting steps up to the next approval.
- The panel shows what the run produced, nothing else: no spinner animations, no invented progress, state words only (`Investigating`, `Waiting for operator approval`, `Completed`, `Failed`, `Stopped: budget exceeded`, `Stopped: spend cap reached` — the last one when the error message detail is `"spend cap reached"`).

## Files (`app/frontend/src/` unless noted)
| Action | Path |
|---|---|
| Modify | `scripts/export_contract.py` + `app/backend/tests/test_export_contract.py` (3 new keys); regenerate types |
| Modify | `shared/data/DataSource.ts` (run API), `shared/data/LiveSource.ts`, `shared/data/ReplaySource.ts`, `shared/data/index.ts` |
| Create | `shared/data/liveRun.ts`, `shared/data/liveRun.test.ts`, `shared/data/replayRun.ts`, `shared/data/replayRun.test.ts`, `shared/data/runMessages.ts` (type guard `isRunMessage`), `shared/testing/traceFixture.ts`, `shared/testing/FakeWebSocket.ts` |
| Create | `features/agentPanel/index.ts`, `store.ts`, `store.test.ts`, `useAutoRun.ts`, `useAutoRun.test.ts`, `nodeLabels.ts`, `components/AgentPanel.tsx`, `components/AgentTimeline.tsx`, `components/AgentTimeline.test.tsx`, `components/StepRow.tsx`, `components/SourcedValue.tsx`, `components/SourcedValue.test.tsx`, `components/RunStatusLine.tsx`, `candidates.ts`, `candidates.test.ts` |
| Modify | `app/AppShell.tsx` (right column tabs `Agent` / `Station log`), `features/scenarios/components/PlaybackBar.tsx` (`lockedReason` prop), `features/station3d/model/StationScene.tsx` (mount `CandidateHighlight` with `useCandidates()`) |

## Interfaces
`DataSource.ts` additions:
```ts
import type { OperatorDecision, RunMessageUnion } from "@/shared/types/generated/contract";

/** A started agent run: messages in order, decisions out. */
export interface RunHandle {
  readonly runId: string;
  /** Edits and free-text reasons are possible only in live mode. */
  readonly canEdit: boolean;
  subscribe(listener: (message: RunMessageUnion) => void): () => void;
  decide(decision: OperatorDecision): Promise<void>;
  close(): void;
}

export interface DataSource {
  // …existing members…
  /** Start (live) or begin replaying (replay) the agent run for a scenario. */
  startRun(scenarioId: string, signal?: AbortSignal): Promise<RunHandle>;
}
```
`liveRun.ts` — `export async function startLiveRun(scenarioId, signal): Promise<RunHandle>`: `POST /api/runs` (JSON body `{scenario_id}`) → `run_id` (409 → `DataSourceError("invalid", "a run is already active")`; 503 → `DataSourceError("unreachable", "agents are not configured")`); WebSocket URL `` `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/runs/${runId}/ws` ``; messages parsed with `JSON.parse` + `isRunMessage` (others dropped with one `console.warn`); `seq` de-duplication (keep the highest seen `seq ≥ 0`, drop repeats); on an unexpected close while the run is not final, reconnect **once** after 1 s; `decide` → `POST /api/runs/{id}/decision` (409 → `DataSourceError("invalid", detail)`); `canEdit = true`.
`replayRun.ts` — `export class ReplayRun implements RunHandle` with `canEdit = false`; constructor `(scenarioId, loadTrace: (branch) => Promise<ReplayTrace>, timer = { setTimeout, clearTimeout })`:
- `start()` loads `approve`; schedules each step at its `t_ms`; emits `StatusMessage("running")` first; emits the first `TraceApproval` as `ApprovalMessage` at its `t_ms` and `StatusMessage("awaiting_approval")`, then stops scheduling.
- `decide(approve)` → continue the **current** trace after the approval point to the next approval or the end (`FinalMessage` + `StatusMessage("completed", outcome)`).
- `decide(reject)` with `reason === payload.preset_reject_reason` → load `reject_redraft`, continue it from its first decision point; any other reason → `DataSourceError("invalid", "Replay uses the recorded rejection reason")`.
- `decide(edit)` → `DataSourceError("invalid", "Edits work in local live mode")`.
- `flush()` → emit every step scheduled before the next approval immediately (for `Show all steps`).
- S4 (no approval) runs straight to the final.
`ReplaySource.startRun` → `new ReplayRun(...)` loading `/replay/traces/<id>/<branch>.json` (validated: `schema_version === 1`, `simulated === true`, `label === "Replay of a recorded AI run"`, `scenario_id` match); also exposes `startSimS` for `useAutoRun`.

`features/agentPanel/store.ts` (Zustand): state `handle: RunHandle | null`, `status: "idle" | "starting" | "running" | "awaiting_approval" | "completed" | "failed" | "aborted_budget"`, `steps: StepMessage[]`, `approval: ApprovalPayload | null`, `final: { outcome: string; final: Record<string, unknown> } | null`, `error: string | null`, `scenarioId: string | null`. Actions: `start(source, scenarioId)`, `receive(message)` (pure reducer exported as `reduceRun(state, message)` for tests), `reset()` (closes the handle). `useScenarioStore` subscription: scenario change → `reset()`.
`useAutoRun()` (mounted once in AppShell): when `status === "idle"`, the scenario is ready and `tSeconds ≥ firstAlarmS` (`min(window_start_s) + 600` of the scenario's events; replay: the trace's `start_sim_s`) → `pause()` and `start(...)`. While `status` is `starting` or `running`, PlaybackBar gets `lockedReason = "Agents investigating"` (play disabled, text shown in place of the time readout's left part).
`nodeLabels.ts`: `detect_event → "Event"`, `triage → "Triage"`, `locate_quantify → "Locate and quantify"`, `compliance → "Compliance"`, `draft_outputs → "Drafting"`, `approval → "Operator approval"`, `redraft → "Redraft"`, `finalize → "Finalize"`, `escalate → "Escalated"`, `log_vented_volume → "Vented volume"`.
`candidates.ts`: `candidatesFromSteps(steps): { anchorId; label; probability }[]` — from the **last** `tool_result` of `run_plume_inversion` (`payload.output.candidates`, skip `NONE`); `label` = tag + anchor name (`"VS-250.tip"` → `"VS-250 tip"`, underscores → spaces); `useCandidates()` hook for the 3D view.
**AgentTimeline**: steps grouped under node headers (in order of first appearance); rows: `tool_call` hidden (the `tool_result` row carries the tool name), `tool_result` → tool name (mono) + `ok` / error text, `submit_rejected` → "Output rejected by the checks: <summary>" with `AlertTriangle` icon, `submitted` → the node's key fields (below), `approval`/`decision`/`final` → one line each. `aria-live="polite"` region announces only new node headers.
**Key fields of `submitted` rows** (from `payload.output`): triage → classification word + rationale; locate → top anchor, attributed unit, `SourcedValue`s for probability (as %) and rate p05–p50–p95; compliance → event class, rule ids, `SourcedValue` for repair deadline and CO2e/day; vented volume → `SourcedValue`s. Never re-compute a number; only format.
**SourcedValue** (`{ number: SourcedNumber; steps }`): text `14.6 kg/h` (`formatNumber`: unit `"1"` → `Math.round(v·100) + "%"`; others: value as given + unit); wrapped in a shadcn Tooltip whose content is `run_plume_inversion · call_003 · rate.p50` (tool name looked up from the step with that `call_id`); unknown call id → text plus `(source missing)` in `--alarm-high` — this should never happen and is visible if it does. Override present → suffix `operator override` badge.
**RunStatusLine**: status words above, plus cost/time only in live mode when present in the final status (`$0.18 · 41 s`, from the backend's numbers).

## Tests (key cases; full code for the replay run)
`shared/data/replayRun.test.ts`:
```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeTrace } from "@/shared/testing/traceFixture";

import { ReplayRun } from "./replayRun";

describe("ReplayRun", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("plays steps on their recorded timing and waits at the approval", async () => {
    const run = new ReplayRun("s1_rod_packing", async (b) => makeTrace(b));
    const seen: string[] = [];
    run.subscribe((m) => seen.push(m.type === "step" ? `step:${m.seq}` : m.type));
    await run.start();
    await vi.advanceTimersByTimeAsync(999);
    expect(seen).toEqual(["status", "step:0"]);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(seen.slice(-2)).toEqual(["approval", "status"]);
  });

  it("approve continues the same trace to the final", async () => {
    const run = new ReplayRun("s1_rod_packing", async (b) => makeTrace(b));
    const seen: string[] = [];
    run.subscribe((m) => seen.push(m.type));
    await run.start();
    await vi.advanceTimersByTimeAsync(20_000);
    await run.decide({ interrupt_id: "rec:r0", action: "approve" });
    await vi.advanceTimersByTimeAsync(20_000);
    expect(seen).toContain("final");
  });

  it("reject needs the recorded reason and switches branch; edits are refused", async () => {
    const run = new ReplayRun("s1_rod_packing", async (b) => makeTrace(b));
    await run.start();
    await vi.advanceTimersByTimeAsync(20_000);
    await expect(run.decide({ interrupt_id: "rec:r0", action: "edit", edits: {} })).rejects.toMatchObject({ kind: "invalid" });
    await expect(run.decide({ interrupt_id: "rec:r0", action: "reject", reason: "Other" })).rejects.toMatchObject({ kind: "invalid" });
    await run.decide({ interrupt_id: "rec:r0", action: "reject", reason: "Work order must name the isolation steps and state the gas-test requirement before work starts." });
  });
});
```
`traceFixture.ts`: `makeTrace(branch)` — 3 steps at `t_ms` 0, 1000, 2000, approval at 3000 with `interrupt_id "rec:r0"` and the preset reason; `approve` continues with a `final` step at 4000 and `final.outcome "approved"`; `reject_redraft` has a decision at 3500, redraft step at 5000, second approval `rec:r1` at 6000, final at 7000.
`liveRun.test.ts` (with `FakeWebSocket` stubbed globally and `fetch` mocked): `POST` body and URL; WS URL uses `ws://` + current host; duplicated `seq` delivered once after a simulated reconnect; 409 on start → `kind "invalid"`.
`store.test.ts`: `reduceRun` for each message type (status transitions, approval stored, final stored, error stored, steps appended in order).
`useAutoRun.test.ts`: with a fake source, the run starts once when `tSeconds` passes `firstAlarmS`, the clock is paused, and it does not start again after `completed`.
`AgentTimeline.test.tsx`: groups under node labels; a `submit_rejected` row shows the warning text; a `submitted` locate row shows `14.6 kg/h`.
`SourcedValue.test.tsx`: tooltip content names tool, call id and path (open with `userEvent.hover`); unknown call id shows `(source missing)`.
`candidates.test.ts`: last inversion wins; `NONE` skipped; label `VS-250 tip`.

## Steps
- [ ] Contract update + types. Tests → FAIL → implement data layer, then store/hooks, then components.
- [ ] `npm run lint && npm run typecheck && npm run test && npm run build && npm run build:replay && npm run check:replay-bundle`.
- [ ] Browser (replay build, no backend): S1 → alarm → clock pauses → steps appear with timing → candidate glow on VS-250 → approval payload received (dialog arrives in Task 14; for now the panel says `Waiting for operator approval`). Live (backend + key, owner's yes for one run): same flow on a real run.
- [ ] `check_slop.py`; `impeccable` critique of the panel (density, hierarchy, status words, tooltip); fixes recorded; repo checks.
- [ ] **Docs.** FRONTEND.md → "Agent runs" (RunHandle, live vs replay behaviour, auto-start, clock lock, timeline rules, sourced values). Work-log; `STATUS.md` (last 5.13, next 5.14).
- [ ] **Commit** `feat(frontend): add agent run data source and timeline panel`.
