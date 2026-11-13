# Phase 7 · Task 5 — Local release-readiness gate and final review (no deployment)

**Skills:** `plan-execution`, `security-checks` (release gate + `references/checklist.md` A–H), `security-review`, `backend-design:security-reviewer`, `verify-and-review` (`verify-plumetrace-release`, `engineering-coverage`), `testing-strategy`, `superpowers:requesting-code-review`, `project-documentation`.

**No deployment (owner decision 2026-11-13).** This gate proves the product is complete and safe
on the owner's machine. It does not create a Vercel project, run `vercel`, push, or publish.
Deployment is a later phase that is not planned yet.

## Release gate (every item recorded with its output in `docs/evidence/2026-11-phase-7-release.md`)
1. **Every test layer, from a clean checkout of the release commit** (`git clone` of the local repo into a scratch folder, then the commands there): `python scripts/ci_local.py --full` — runs, in order, every stage of the test matrix in `docs/reference/TESTING.md` (repo checks, Python unit + property + integration + contract + API fuzz + security tests with local Supabase and `PLUMETRACE_REQUIRE_DB=1`, coverage thresholds, frontend lint / typecheck / component tests / coverage, `build:replay`, `check:replay-bundle`, `e2e` (`no-webgl`), full-stack e2e with the scripted LLM). Then on the owner's machine: `npm run e2e:webgl` and `npm run e2e:fps`. Every stage must pass; paste the summary table `ci_local.py` prints.
2. `check_structure.py` → `structure OK`; `secret_scan.py .` → `no secrets found`; `check_env.py .` → `env OK`; `check_slop.py app/frontend/src` → `no slop found` (also part of item 1; repeat the four lines in the evidence).
3. Secret scan of the **git history**: `git log -p --all | python -I .claude/skills/security-checks/scripts/secret_scan.py -` (Phase 6 Task 6 added stdin support). Any hit → STOP; the owner decides on history rewriting (never do it yourself).
4. Dependency audit: `cd app && uv run pip-audit` (pinned dev dependency since Phase 1) and `cd app/frontend && npm audit --omit=dev --audit-level=high` → no high/critical (report moderate). List `uv.lock` packages and versions in the evidence.
5. `security-review` over the whole repository and `backend-design:security-reviewer` over `app/backend/plumetrace/api/`; compare against `docs/reference/THREAT_MODEL.md` (Phase 6): every threat has its control and its test; every high/critical finding fixed (own commits) and re-checked.
6. `verify-plumetrace-release` + `engineering-coverage` against design §1–15: every MVP item of §11.1 present and verified, every anti-goal of §2 avoided; list deviations (must be none or owner-approved — the owner-approved ones so far: per-run budget $0.05/$0.10, total spend cap, evaluation sized to the cap, no deployment yet).
7. Licences: ASSETS.md and README credits cover every third-party asset and data source; the replay build shows the Open-Meteo attribution.
8. Local replay check: `npm run build:replay && npm run preview:replay`; then `cd app && uv run python ../scripts/check_headers.py --url http://127.0.0.1:4173 --check-cache` (Phase 6 Task 4 script; HSTS is skipped for `http://127.0.0.1` and reported as `n/a (local http)`); network log of the landing page shows only same-origin requests; `Replay of a recorded AI run` visible; About dialog numbers equal the evidence.
9. Spend: `select coalesce(sum(cost_usd), 0) from plumetrace.llm_calls` — record the total against the cap.
10. `superpowers:requesting-code-review` for the diff since Gate 6; findings addressed.

## Steps
- [ ] Gate items 1–10 (fix → re-run until clean). Each fix is its own small commit, with `ci_local.py` green before it.
- [ ] Evidence file complete; show it to the owner.
- [ ] **Docs.** WORK_LOG entry for the release; `docs/reference/DEPLOYMENT.md` → keep only "Deployment is a later phase (not planned yet)" + the replay build and local preview commands + the header source (`vercel.json`); README has no live link.
- [ ] **Commit** `chore(release): record the v1.0 local release evidence` (tag `v1.0.0` only if the owner asks; never push without the owner's go-ahead).
- [ ] `STATUS.md`: "Phase 7 complete — development done; deployment is a later phase (not planned)". **STOP.**
