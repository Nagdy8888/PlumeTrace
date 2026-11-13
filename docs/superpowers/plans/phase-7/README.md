# Phase 7 — Replay polish, performance, demo video, README, local release gate (no deployment)

> **For agentic workers:** load `plan-execution`, `frontend-structure`, `frontend-design`,
> `security-checks`, `testing-strategy` first. **Start only after Owner Gate 6** (security
> hardening) is signed off in STATUS.md. Nothing is published, posted or pushed without the
> owner's explicit go-ahead in chat for that exact action.
>
> **No deployment in this phase (owner decision 2026-11-13).** Deploying the replay site is a
> later phase that is **not planned yet**. Do not create a Vercel project, do not run any
> `vercel` command, do not log in anywhere, do not write a live URL into any file. The static
> replay build (`npm run build:replay`) is built and checked **locally** only
> (`npm run preview:replay`, served from `127.0.0.1`, added in Phase 6 Task 4).

**Goal:** a static replay build that looks and behaves like the local product (labelled as a
replay), a landing autoplay of S1, the mobile video page with a real demo video, a README that
reports the benchmark and evaluation honestly, and a final local release-readiness gate.

**Spec:** design §1–2 (intent, anti-goals), §8 (labelling), §9 (frontend), §10 (public mode), §11.2 (video, gates); skills `security-checks` (release gate), `verify-and-review` (`verify-plumetrace-release`), `testing-strategy`.

## Task order
| # | File | Delivers |
|---|---|---|
| 1 | `task-01-replay-polish.md` | replay label, landing autoplay of S1, "About this demo" panel with every attribution |
| 2 | `task-02-performance-pass.md` | bundle split, model preload, compression check, fps with agents running, budgets table |
| 3 | `task-03-demo-video.md` | storyboard, scripted capture of the replay, MP4 + poster, mobile page video |
| 4 | `task-04-readme-launch-docs.md` | README with results, architecture diagram, LinkedIn post drafts (owner posts later) |
| 5 | `task-05-release-gate.md` | local release-readiness gate: every test layer, security gate, final review against the design — **no deploy** |

## Pinned additions (checked 2026-11-13)
| Tool | Version | Use |
|---|---|---|
| FFmpeg | 8.1 (already installed by the owner, WinGet build) | video conversion only; `ffmpeg -version` first line must start `ffmpeg version 8.1` |

## Global constraints
- The replay build is `npm run build:replay`; `check:replay-bundle` must pass; the static output and `app/replay/` pass `secret_scan.py`.
- Local preview only: `npm run preview:replay` (Phase 6 Task 4) over the replay `dist/`. Header checks run against this local server (`check_headers.py --check-cache` from Task 2 on).
- `app/frontend/vercel.json` (Phase 1) stays as the **written record** of the security headers and rewrites the later deployment phase will use; it is checked by its unit test and by `vite.config.ts` `preview.headers` reading the same values. It is not deployed now.
- Every outward action (publish video, post, push) needs the owner's yes in chat for that action.
- Checks run **locally** with `python scripts/ci_local.py` (Phase 1 Task 8); there are no GitHub Actions.
- Labels: station simulated; replay `Replay of a recorded AI run`; Open-Meteo CC BY 4.0; emission factors / GWP / rules cited — no claim that EU articles bind the site.

## Review focus
1. A first-time visitor understands in 10 seconds what they see (landing autoplay, labels) — and nothing claims to be live.
2. No request to `/api`, no third-party request at all in the replay build (CSP holds; check the network log on the local preview).
3. The video and README numbers match the evidence files exactly.

## Phase exit
`docs/evidence/2026-11-phase-7-release.md` (Task 5). `STATUS.md`: "Phase 7 complete — development done; deployment is a later phase (not planned)". STOP.
