# Phase 6 · Task 8 — Full security gate, reviews, evidence → OWNER GATE 6

**Skills:** `plan-execution`, `security-checks` (full gate), `security-review`, `backend-design:security-reviewer`, `verify-and-review`, `testing-strategy`, `superpowers:requesting-code-review`, `project-documentation`.

## Gate items (each recorded with its output in `docs/evidence/2026-11-phase-6-security.md`)
1. `python scripts/ci_local.py --full` from a clean local clone (`git clone <repo path> <scratch>`), local Supabase running, `SUPABASE_DB_URL` = the `plumetrace_app` role → every stage green; paste the summary table.
2. `uv run ruff check --select S backend agents ../scripts` → clean, or each ignore justified inline.
3. The four repo checks: `structure OK`, `no secrets found`, `env OK`, `no slop found`; plus `frontend safety OK`.
4. `security-review` over the whole repository; `backend-design:security-reviewer` over `app/backend/plumetrace/api/` and `app/backend/plumetrace/db/`. Every high/critical finding → fixed in its own commit with a regression test, then re-checked. Medium/low → listed with a decision (fix now / accept with the owner).
5. THREAT_MODEL.md: every threat row has a control and a test that exists and passes (list `Id → test → pass`). A row without a passing test blocks the gate.
6. Manual abuse session on the running backend (no paid calls — agents unconfigured or the scripted LLM): the rate-limit `curl` loop (Task 2), the foreign Host header (Task 3), a 70 KB body (`413`), a WebSocket from `Origin: https://evil.example` (closed 1008; use the browser console on `http://127.0.0.1:5173` with a modified Origin via Playwright `extraHTTPHeaders` or `websocat` if the owner has it — do not install tools). Record each command and output.
7. `superpowers:requesting-code-review` for the phase diff; findings addressed.
8. Spend so far: `select coalesce(sum(cost_usd), 0) from plumetrace.llm_calls` vs the cap (this phase makes no paid calls; the number must equal the Phase 5 end value).

## Steps
- [ ] Items 1–8 (fix → re-run until clean).
- [ ] Evidence file complete; link it from `docs/README.md`.
- [ ] **Docs.** SECURITY.md → "Phase 6 results" summary; Work-log.
- [ ] **Commit** `docs(evidence): record the phase 6 security gate`.
- [ ] `STATUS.md`: "Phase 6 complete — waiting for Gate 6 (security evidence)". **STOP.**
