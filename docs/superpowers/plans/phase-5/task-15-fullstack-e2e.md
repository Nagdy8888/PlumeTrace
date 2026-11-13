# Phase 5 · Task 15 — Full-stack end-to-end test in live mode with the scripted model (no cost)

**Skills:** `plan-execution`, `testing-strategy`, `playwright-cli`, `fastapi`, `frontend-structure`, `project-documentation`.
**Docs to check first (Context7):** @playwright/test 1.65.0 `webServer` as an **array** (`command`, `url`, `reuseExistingServer`, `timeout`, `cwd`, `env`), `defineConfig({ testDir, projects })`.

**Why:** the unit, component, integration (DB) and API tests cover each layer, and Task 14's
Playwright tests cover the **replay** build. Nothing yet proves the **live** path end to end:
browser → Vite proxy → FastAPI → graph runner → LangGraph → Postgres → WebSocket → approval
dialog → decision → work order row. This task adds that test with the **scripted** model and fake
tools, so it costs nothing and is deterministic.

## Fixed decisions
- A test-only server `scripts/e2e_live_server.py` builds the real app with
  `create_app(runner_deps=RunnerDeps(llm=ScriptedLLM(S1_SCRIPT), checkpointer=PostgresSaver from open_checkpointer(...), ledger=MemorySpendLedger(), settings=get_settings(), pool=create_pool(...), mode="live"))`
  and patches `plumetrace.api.graph_runner.ScenarioToolProvider` to return `FakeToolProvider("s1")`.
  It **never** calls `build_agent_llm` and never sets tracing (it runs `os.environ["LANGSMITH_TRACING"] = "false"` first). It refuses to start unless the host is `127.0.0.1` and port `8000`.
- The S1 script is a copy of Phase 5 Task 7's `s1_script` fixture (tests cannot import fixtures);
  the copy lives in `scripts/e2e_live_server.py` as `S1_SCRIPT` with a docstring naming its source.
  When Task 7's fixture changes, this copy changes in the same commit.
- Real database (local Supabase, `plumetrace_app` or the current role) and the real Postgres checkpointer, so persistence and resume are covered too.
- Playwright config `app/frontend/playwright.live.config.ts`, project `live-fake`, two web servers: the e2e server (`cd ../ && uv run python ../scripts/e2e_live_server.py`, url `http://127.0.0.1:8000/api/health`) and Vite dev (`npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`, url `http://127.0.0.1:5173`); `reuseExistingServer: false` for both (a running dev backend on 8000 makes the test fail visibly instead of silently using a paid backend).
- New npm script `"e2e:live": "playwright test --config playwright.live.config.ts"`; new `ci_local.py` stage `e2e-live` (full only).

## Files
| Action | Path |
|---|---|
| Create | `scripts/e2e_live_server.py` |
| Create | `app/frontend/playwright.live.config.ts`, `app/frontend/e2e-live/live-approve.spec.ts`, `app/frontend/e2e-live/live-reject-redraft.spec.ts` |
| Modify | `app/frontend/package.json` (script), `app/frontend/tsconfig.json` (`include` adds `e2e-live`, `playwright.live.config.ts`), `app/frontend/eslint.config.js` (lint `e2e-live/**` like `e2e/**`) |
| Modify | `scripts/ci_local.py` → `Stage("e2e-live", (("app/frontend", ("npm", "run", "e2e:live")),), modes=FULL, env=(("PLUMETRACE_REQUIRE_DB", "1"),))`; then `uv run ruff format ../scripts`; extend `test_ci_local.py` (`"e2e-live"` in full only) |

## Test content (`live-approve.spec.ts`, full code)
```ts
import { expect, test } from "@playwright/test";

test("live S1 run: agents investigate, operator approves, run completes", async ({ page }) => {
  await page.goto("/?scenario=s1_rod_packing");
  await expect(page.getByText("Live · local backend")).toBeVisible();
  await page.getByRole("button", { name: "Play" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 60_000 });
  await expect(dialog.getByText("14.6 kg/h").first()).toBeVisible();
  await dialog.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Completed")).toBeVisible({ timeout: 30_000 });
});
```
`live-reject-redraft.spec.ts`: same start; `Reject` → the preset reason is offered → `Send rejection` → a second dialog shows revision 1 with the action `Gas test before work` → `Approve` → `Completed`. (Button names are those of Phase 5 Task 14; if a name differs in the built UI, use the built name and note it in the work log — never add test-only ids.)

After both specs the test asserts nothing in the DB directly; `test_runs_api.py` already covers the rows. The value here is the whole wire path through a real browser.

## Steps
- [ ] Write the server and the specs → `npm run e2e:live` green twice in a row (deterministic).
- [ ] Prove no paid client: run once with the network disabled for Python (`$env:HTTPS_PROXY="http://127.0.0.1:9"` in the shell that starts Playwright, PowerShell syntax) → still green.
- [ ] `python scripts/ci_local.py --full --only e2e-live` green; runner test green.
- [ ] Repo checks.
- [ ] Add the `e2e:live` output to `docs/evidence/2026-11-phase-5-agents.md` (section "Tests and gates").
- [ ] **Docs.** `docs/reference/TESTING.md` → "Full-stack live e2e" (what it covers, why scripted, how to run, the port rule); FRONTEND.md → "Testing" link. Work-log; `STATUS.md`: "Phase 5 complete — waiting for owner review".
- [ ] **Commit** `test(e2e): add a full-stack live-mode test with the scripted model`.
