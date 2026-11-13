# Phase 7 · Task 1 — Replay label, landing autoplay, "About this demo" panel

**Skills:** `plan-execution`, `frontend-design` (+ `anti-slop.md`), `shadcn` (dialog), `vectorlab-ux-skills:labels`, `impeccable`, `project-documentation`. Read `.ux-profile.md`.

## Behaviour (exact)
**Mode label** (top bar, replaces Phase 4's `Replay`): replay builds show `Replay of a recorded AI run` with a 6 px `--text-3` square marker; live shows `Live · local backend` (unchanged).

**Landing autoplay** (replay builds only, desktop): on first load without a `?scenario=` parameter:
1. Select `s1_rod_packing`, seek to `firstAlarmS − 1200` (20 min before the first alarm), speed `60×`, play.
2. Camera: the review camera; a slow idle orbit (0.03 rad/s about the target) runs until the first pointer, wheel or key event anywhere, then stops for the session (frontend-3d rule: "idle auto-orbit only on the landing view, stops on any interaction").
3. When the approval dialog opens during autoplay, nothing is decided automatically — the visitor decides.
4. Reduced motion → no autoplay and no orbit; the scenario is selected and paused at the same time.
5. `sessionStorage["plumetrace.autoplayed"] = "1"` after the first run (try/catch; storage errors ignored) so a reload keeps the visitor's own state.

**About this demo** — a text button `About this demo` in the top bar opens a dialog (shadcn Dialog) with these sections and sentences (copy exactly; numbers come from evidence files, not typed by hand — see below):
- `What this is` — `PlumeTrace is a portfolio project: methane leak detection for Station KS-07, a fictional compressor station. The station, its sensors and its leaks are simulated. The agent runs you see are recordings of real runs of the system.`
- `Real data` — `Weather: Open-Meteo historical data (CC BY 4.0), <site coordinates>, <snapshot dates>.` / `Emission factors: <counts-table source line> and <EPA factor source line>.` / `Global warming potential: <GWP_SOURCE>.` / `Rules: the operator's LDAR policy is modelled on Regulation (EU) 2024/1787; OGMP 2.0 reporting. The EU regulation does not bind the site (outside the EU, exports to the EU).`
- `How it works` — `Fence-line sensors raise an event; AI agents triage it, locate and quantify the source with a dispersion model, check the operator's rules, and draft a work order. An operator approves, edits or rejects every draft. Every number in a draft comes from a calculation tool, never from the language model.`
- `Accuracy` — one line each from the evidence: inversion benchmark (Phase 2 benchmark summary: top-source accuracy and rate-in-interval under model mismatch) and agent evaluation (Phase 5: triage accuracy AI vs baseline, provenance pass rate).
- `Source code and licence` — repository link text `Source code` (URL filled by the owner in Task 4; until then the line is omitted, not shown as a placeholder) · `MIT licence`.
The values in angle brackets are read at build time from generated JSON, never typed into components: add `scripts/export_about.py` that writes `app/replay/about.json` (site coordinates and snapshot dates from the weather snapshot, attribution strings from the facility counts table / factor module / GWP module / rules table version, benchmark and evaluation summary numbers from `docs/evidence/*.json`). The `About` dialog loads `/replay/about.json` (`ReplaySource`) or `GET /api/about` (`LiveSource`, add the endpoint returning the same model).

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/api/about.py` (`AboutInfo` model + `build_about()`), `app/backend/plumetrace/api/routes/about.py`, test `app/backend/tests/api/test_about.py`; `scripts/export_about.py`; contract key `about: AboutInfo` |
| Generated | `app/replay/about.json` |
| Create (frontend) | `src/app/AboutDialog.tsx`, `src/app/AboutDialog.test.tsx`, `src/app/useLandingAutoplay.ts`, `src/app/useLandingAutoplay.test.ts`, `src/features/station3d/scene/IdleOrbit.tsx` |
| Modify | `src/shared/data/DataSource.ts` (`loadAbout()`), both sources, `src/app/TopBar.tsx`, `src/app/AppShell.tsx` |

`AboutInfo` fields: `site_lat_deg`, `site_lon_deg`, `weather_dates: str` (`"2025-07-14 to 2025-07-20"`), `weather_attribution`, `counts_source`, `factor_source`, `gwp_source`, `rules_table_version`, `benchmark: {top_source_accuracy, rate_in_interval, cases}`, `evaluation: {ai_triage_accuracy, baseline_triage_accuracy, provenance_pass_rate, runs}`, `repository_url: str | None`. Missing evidence file → `build_about()` raises `FileNotFoundError` naming it (the export fails visibly).

## Tests (key cases)
- `test_about.py`: `build_about()` reads the evidence JSON files (fixtures in `tmp_path` via a monkeypatched path constant) and returns exact numbers; missing file → `FileNotFoundError`.
- `useLandingAutoplay.test.ts`: plays S1 from `firstAlarmS − 1200` at 60× on first load; does nothing with `?scenario=` set, with reduced motion, or when `sessionStorage` says autoplayed; storage throwing does not break it.
- `AboutDialog.test.tsx`: renders every section heading; the repository line is absent when `repository_url` is null; numbers shown equal the fixture values; no text matches the anti-slop ban list words (`Unlock`, `Seamless`, `AI-powered`, …).

## Steps
- [ ] Tests → FAIL → implement → backend + frontend checks green; `export_about.py` run; `build:replay` + `check:replay-bundle`.
- [ ] Browser: first load autoplays, orbit stops on the first interaction, About dialog content is correct and keyboard-accessible.
- [ ] `check_slop.py`; `impeccable` critique (label clarity, About copy density); repo checks.
- [ ] **Docs.** FRONTEND.md → "Landing and About"; REPLAY.md → `about.json`. Work-log; `STATUS.md` (last 7.1, next 7.2).
- [ ] **Commit** `feat(frontend): add replay label, landing autoplay and About panel`.
