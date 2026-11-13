# Phase 5 · Task 14 — Approval dialog, queued alarms, end-to-end flows, phase evidence

**Skills:** `plan-execution`, `frontend-design` (+ `control-room-workspace.md` → approval rules), `shadcn` (dialog, tooltip), `vectorlab-ux-skills:forms`, `vectorlab-ux-skills:errors`, `impeccable`, `playwright-cli`, `verify-and-review` (phase end), `security-checks` (full gate), `project-documentation`.
**Docs to check first (Context7):** shadcn Dialog (Radix: focus trap, `onOpenChange`, `DialogTitle` / `DialogDescription` required for a11y).

## Rules (design §6 "Operator approval", control-room reference)
- One dialog for the whole bundle (work order, shift-log entry, report line).
- **Never optimistic:** after a decision the dialog shows `Decision sent. Waiting for the agents…`; "issued" / "filed" appear only when the `final` message arrives.
- Numbers are locked to their sources. In live mode an operator may enter an explicit **override** (value + reason), shown as `Operator override` in the dialog and the final record.
- Reject requires a reason (3–500 characters). In replay the recorded preset reason is filled in and read-only, with the note `Replay: the recorded rejection reason is used. Free-text reasons and edits work in local live mode.`
- If sending fails, the operator's edits and reason are kept and a retry is offered.
- Second rejection: the dialog states before sending `A second rejection is final: the event is escalated to an engineer and no further AI drafts are made.`

## Files (`app/frontend/src/features/approval/` unless noted)
| Action | Path |
|---|---|
| Create | `index.ts`, `ApprovalDialog.tsx`, `ApprovalDialog.test.tsx`, `BundleView.tsx`, `WorkOrderSection.tsx`, `ShiftLogSection.tsx`, `ReportLineSection.tsx`, `LockedNumber.tsx`, `OverrideForm.tsx`, `RejectForm.tsx`, `EditFields.tsx`, `EvidenceList.tsx`, `useApprovalFlow.ts`, `useApprovalFlow.test.ts`, `buildDecision.ts`, `buildDecision.test.ts` |
| Create | `features/agentPanel/components/FinalSummary.tsx`, `FinalSummary.test.tsx`; modify `AgentPanel.tsx` (`Review drafts` button reopens the dialog while approval is pending) |
| Modify | `features/alarms/components/AlarmRow.tsx` + test (status badge `Investigating` / `Queued`) |
| Create | `app/frontend/e2e/agent-replay.spec.ts` |
| Create | `docs/evidence/2026-11-phase-5-agents.md` |

## Behaviour
**ApprovalDialog** opens when `approval` becomes non-null (and on `Review drafts`). Title `Review drafts: <work order title or "Planned venting log">`; description `Revision <n> · drafted by the agents for operator approval. Numbers are locked to the tool results that produced them.` Body = `BundleView` + `EvidenceList` (collapsed `<details>` `Evidence (<n> tool results)` listing tool name, call id, summary). Footer buttons in this order: `Reject` (secondary), `Edit` (secondary; disabled with tooltip `Edits work in local live mode` when `!handle.canEdit`), `Approve` (primary, `--accent`). `Esc` / close keeps the approval pending.
**LockedNumber**: `Lock` icon (14 px, `aria-hidden`) + `14.6 kg/h` (mono) + Tooltip `From run_plume_inversion · call_003 · rate.p50`; in edit mode (live) an `Override` text button opens `OverrideForm` (number input with the unit as a suffix label, reason textarea, `Apply override` / `Cancel`); an applied override shows `Operator override: 3 d — "Site manager instruction"` and the original value struck through.
**EditFields** (edit mode): textareas for work-order description, actions (one per line, 1–6 lines), shift-log text, report-line text; character counters against the schema limits (1200 / 6 / 600 / 400).
**RejectForm**: textarea `Reason for rejection` (required, 3–500 chars after trim, error text `Enter a reason of at least 3 characters.`), `Send rejection` button.
**useApprovalFlow** state machine: `reviewing → editing | rejecting → sending → waiting` and `sending → error` (keeps the form values; `Retry` re-sends; `Back` returns to the form). `waiting` ends when the store receives the next `approval` (new revision → `reviewing`) or `final` (dialog closes).
**buildDecision**: `approve(interruptId)`, `edit(interruptId, fields, overrides)` (only changed text fields are sent; override keys are bundle paths such as `work_order.due_within`), `reject(interruptId, reason)` → `OperatorDecision` (generated type).
**FinalSummary** (agent panel, after `final`): `approved` → `Work order issued (simulated). Report filed (simulated).`; `edited` → same + ` Approved with operator edits.`; `escalated` → `Escalated to an engineer after the second rejection. No further AI drafts.`; `logged` → `Planned venting logged: <vented CH4 SourcedValue> (<CO2e SourcedValue>).`; `failed` → `The agent run failed. See the backend log.` Each with the run's outcome word as a `StatusBadge` (`ok` / `ok` / `med` / `neutral` / `high`).
**AlarmRow** badge: the run's event → `Investigating` (while `running` / `awaiting_approval`); later events in the same scenario while a run is active → `Queued`; nothing otherwise.

## Tests (key cases; full code for `buildDecision` and one dialog test)
`buildDecision.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { approve, edit, reject } from "./buildDecision";

describe("buildDecision", () => {
  it("approves without edits", () => {
    expect(approve("r1:r0")).toEqual({ interrupt_id: "r1:r0", action: "approve" });
  });
  it("sends only changed text fields and explicit overrides", () => {
    const d = edit("r1:r0", { shift_log_text: "New text" }, {
      "work_order.due_within": { value: 3, unit: "d", reason: "Site manager instruction" },
    });
    expect(d).toEqual({
      interrupt_id: "r1:r0",
      action: "edit",
      edits: { shift_log_text: "New text", overrides: { "work_order.due_within": { value: 3, unit: "d", reason: "Site manager instruction" } } },
    });
  });
  it("trims the rejection reason and refuses a short one", () => {
    expect(reject("r1:r0", "  Missing gas test  ")).toEqual({ interrupt_id: "r1:r0", action: "reject", reason: "Missing gas test" });
    expect(() => reject("r1:r0", " ab ")).toThrow("Enter a reason of at least 3 characters.");
  });
});
```
`ApprovalDialog.test.tsx` (excerpt to copy; build the payload with a fixture `makeApproval()` in `shared/testing/approvalFixture.ts`):
```tsx
it("never shows an approved state before the final message", async () => {
  const decide = vi.fn().mockResolvedValue(undefined);
  render(<ApprovalDialog payload={makeApproval()} canEdit={false} onDecide={decide} />);
  await userEvent.click(screen.getByRole("button", { name: "Approve" }));
  expect(decide).toHaveBeenCalledWith({ interrupt_id: "r1:r0", action: "approve" });
  expect(screen.getByText("Decision sent. Waiting for the agents…")).toBeInTheDocument();
  expect(screen.queryByText(/issued/i)).not.toBeInTheDocument();
});
```
More dialog tests: replay reject shows the preset reason read-only and the replay note; `Edit` disabled in replay with the tooltip text; a failed `onDecide` (rejected promise) shows `Decision not sent: the backend did not accept it. Your text is kept.` and keeps the reason; locked number tooltip names tool, call id and path; revision 1 shows the second-rejection warning in the reject form; focus moves into the dialog on open and returns to `Review drafts` on close.
`FinalSummary.test.tsx`: each outcome's exact sentence.
`AlarmRow` test: `Investigating` / `Queued` badges by store state.

`e2e/agent-replay.spec.ts` (no-webgl project, replay build):
```ts
import { expect, test } from "@playwright/test";

import { openScenario, seekTo } from "./helpers";

test("S1 replay: agents run, approve, work order issued (simulated)", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await seekTo(page, 9_000);
  await page.getByRole("button", { name: "Play" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 120_000 });
  await dialog.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Work order issued (simulated). Report filed (simulated).")).toBeVisible({ timeout: 120_000 });
});

test("S1 replay: reject with the recorded reason leads to a redraft", async ({ page }) => {
  await openScenario(page, "s1_rod_packing");
  await seekTo(page, 9_000);
  await page.getByRole("button", { name: "Play" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 120_000 });
  await dialog.getByRole("button", { name: "Reject" }).click();
  await dialog.getByRole("button", { name: "Send rejection" }).click();
  await expect(dialog.getByText(/Revision 1/)).toBeVisible({ timeout: 120_000 });
});

test("S5 replay: sensor drift becomes an instrument ticket, not a leak", async ({ page }) => {
  await openScenario(page, "s5_sensor_drift");
  await seekTo(page, 5_000);
  await page.getByRole("button", { name: "Play" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 120_000 });
  await expect(dialog.getByText("AT-106")).toBeVisible();
  await expect(dialog.getByText(/report line/i)).toHaveCount(0);
});
```
(Use `Show all steps` in the specs if the recorded timing makes them slower than 2 minutes: click it once after `Play`.)

## Phase evidence — `docs/evidence/2026-11-phase-5-agents.md`
1. Evaluation summary (copy the Gate 5b tables) and the owner's sign-off date.
2. Screenshots (1920×1080): agent panel mid-run (S1), approval dialog (S1 revision 0 and revision 1), sourced-value tooltip, final summary, S5 instrument ticket, S4 vented-volume log.
3. Trace files: sizes, cost and time of each recording.
4. Live-run sample: one `runs` row (tokens, cost, wall time — no URL secrets) and the LangSmith run URL (owner's workspace; private).
5. Gates: backend + agents `pytest`, frontend `vitest`, `npm run e2e`, ruff, mypy, typecheck, `check_structure.py`, `secret_scan.py`, `check_env.py`, `check_slop.py`, the **full** security gate, `verify-and-review` against design §6 and the Phase 5 review focus list.

## Steps
- [ ] Tests → FAIL → implement → `npm run lint && npm run typecheck && npm run test && npm run build:replay && npm run check:replay-bundle && npm run e2e` green.
- [ ] Live check with the backend (owner's yes; one run): approve, then a new run with edit + override, then a run rejected twice → escalated. Confirm the `decisions`, `work_orders`, `reports` rows.
- [ ] `check_slop.py`; `impeccable` + `design-skills:design-critique` on the dialog; `vectorlab-ux-skills:forms` / `errors` review of edit/reject/override; record fixes.
- [ ] Full security gate (phase end) and `verify-and-review`; fix every high/critical.
- [ ] Evidence file. **Docs.** FRONTEND.md → "Approval" (dialog rules, states, replay limits, overrides); AGENTS.md → "Operator approval end to end". Work-log.
- [ ] **Commit** `feat(frontend): add approval dialog with locked numbers, overrides and replay branches`.
- [ ] `STATUS.md` (last 5.14, next 5.15).
