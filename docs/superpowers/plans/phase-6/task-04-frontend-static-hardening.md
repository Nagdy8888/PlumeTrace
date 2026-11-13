# Phase 6 · Task 4 — Frontend and static build hardening

**Skills:** `plan-execution`, `security-checks` (§D), `frontend-structure`, `superpowers:test-driven-development`, `project-documentation`.

## Fixed decisions
- No HTML from data: model text, log text, operator text and rule quotes are rendered as React text nodes only. No `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval`, `new Function`, string `setTimeout`/`setInterval`, `javascript:` URLs, and every `target="_blank"` has `rel="noopener noreferrer"`. A stdlib script enforces it (a new `ci_local.py` stage).
- The replay build talks to no backend and no third party (T14): `check:replay-bundle` (Phase 4) stays; this task adds a header check against the **local** preview server.

## Files
| Action | Path |
|---|---|
| Create | `scripts/check_frontend_safety.py` + test `app/backend/tests/test_check_frontend_safety.py` |
| Create | `scripts/check_headers.py` + test `app/backend/tests/test_check_headers.py` (local `http.server` fixture) |
| Modify | `scripts/ci_local.py` → stage `frontend-safety` (quick and full) |
| Modify | `app/frontend/package.json` → `"preview:replay": "vite preview --mode replay --host 127.0.0.1 --port 4173 --strictPort"`; `app/frontend/vite.config.ts` → `preview.headers` = the `/(.*)` header block of `vercel.json` (import the JSON: one source of truth); test `src/app/previewHeaders.test.ts` asserts equality |
| Create (tests) | `app/frontend/src/features/agentPanel/AgentTimeline.test.tsx` → new case `renders model text literally`; `app/frontend/src/features/approval/ApprovalDialog.test.tsx` → new case `renders draft text literally` (paths per Phase 5 Tasks 13–14; use the actual component paths) |

## Interfaces
`scripts/check_frontend_safety.py [root]` (default `app/frontend/src`): scans `*.ts`/`*.tsx` (not `*.test.*`, not generated `src/shared/` contract files); patterns (regex, one finding per line `path:line: <rule>`):
| Rule | Pattern |
|---|---|
| `dangerous-html` | `dangerouslySetInnerHTML` |
| `inner-html` | `\.(innerHTML|outerHTML)\s*=` or `insertAdjacentHTML\(` or `document\.write\(` |
| `eval` | `\beval\(` or `new Function\(` |
| `string-timer` | `set(Timeout|Interval)\(\s*["'\`]` |
| `js-url` | `javascript:` |
| `blank-target` | a line with `target="_blank"` whose JSX element (same line or the next 3 lines) lacks `rel="noopener noreferrer"` |
Exit 1 with the findings; exit 0 printing `frontend safety OK`. No exemption mechanism.

`scripts/check_headers.py --url <base>`: requests `/`, `/replay/scenarios/index.json` and HEAD `/models/ks07.glb`; requires on all: `Content-Security-Policy` equal to the `/(.*)` value in `app/frontend/vercel.json`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`; `Strict-Transport-Security` only when the URL is `https://` (else prints `Strict-Transport-Security: n/a (local http)`); with `--check-cache` (used from Phase 7 Task 2 on, when the cache headers exist) also on the glb: `Cache-Control` containing `max-age=86400`; and that `/api/health` is **not** a JSON health response (the replay build has no backend — the SPA rewrite returns `index.html`). Prints one line per check; exit 1 on any failure. Stdlib `urllib` only; timeout 5 s.

Component test (`AgentTimeline.test.tsx`, new case):
```tsx
it("renders model text literally", () => {
  const evil = '<img src=x onerror="window.__pwned=1">';
  render(<AgentTimeline steps={[stepFixture({ summary: evil })]} />);
  expect(screen.getByText(evil)).toBeInTheDocument();
  expect(document.querySelector("img")).toBeNull();
  expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
});
```
(`stepFixture` = the existing test helper of Phase 5 Task 13; if the component takes steps from the store instead of props, set the store state the same way the existing tests do.)

## Steps
- [ ] Tests → FAIL → implement; run `python -I scripts/check_frontend_safety.py` on the real tree → `frontend safety OK` (a finding in existing code → fix the code, its own commit, never an exemption).
- [ ] `npm run build:replay && npm run preview:replay` → `cd app && uv run python ../scripts/check_headers.py --url http://127.0.0.1:4173` → all lines OK.
- [ ] Playwright (`no-webgl` project): new test `e2e/replay-network.spec.ts` — load the replay build, play 30 s at 60×, collect `page.on("request")` URLs: every URL has the page's origin.
- [ ] Repo checks; `check_slop.py`.
- [ ] **Docs.** FRONTEND.md → "Output safety"; SECURITY.md → "Frontend and static build"; THREAT_MODEL.md T09, T14 confirmed. Work-log; `STATUS.md` (last 6.4, next 6.5).
- [ ] **Commit** `feat(security): enforce frontend output safety and check replay headers locally`.
