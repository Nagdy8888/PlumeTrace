# Phase 7 · Task 2 — Performance pass: bundle, model loading, compression, fps with agents running

**Skills:** `plan-execution`, `frontend-3d` (+ `performance-and-testing.md`), `vercel-react-best-practices` (only the SPA-relevant rules), `project-documentation`.
**Docs to check first (Context7):** Vite 8 `build.rollupOptions.output.manualChunks`, `modulePreload`; drei `useGLTF.preload`.

## Targets (record before and after in `docs/evidence/2026-11-performance.md`)
| Metric | Target | How measured |
|---|---|---|
| main JS chunk (gzip) | ≤ 250 KB | `vite build --mode replay` output |
| 3D chunk (gzip) | loaded after first paint; record size | build output + network log |
| first contentful paint (desktop, cold cache, local `vite preview`) | ≤ 1.5 s | Chromium Performance panel, 3 runs, median |
| time to interactive 3D (glb loaded, first frame) | ≤ 4 s on the local `npm run preview:replay` server with Chromium network throttling "Fast 4G" | Performance panel |
| fps at the review camera, S1 playing, agent timeline streaming | ≥ 58 avg (`e2e:fps`) | `npm run e2e:fps` with a replay run active |
| `ks07.glb` transfer | ≤ 15 MB; served with long cache headers | `curl -sI http://127.0.0.1:4173/models/ks07.glb` against the local preview (headers from `vercel.json` via `preview.headers`) |

## Changes (only these; anything else → ask)
1. `vite.config.ts` → `build.rollupOptions.output.manualChunks`: `three` + `@react-three/*` + `postprocessing` → chunk `three`; `uplot` → chunk `charts`. The station chunk stays lazy (`StationView`'s `React.lazy`).
2. `StationView`: call `useGLTF.preload("/models/ks07.glb", false, true)` when the scenario index has loaded (not at module import), so the model download starts while the panels render.
3. `vercel.json` → two new header entries: `/assets/(.*)` (Vite's hashed files) → `Cache-Control: public, max-age=31536000, immutable`; `/(models|textures|images|media)/(.*)` (unhashed files) → `Cache-Control: public, max-age=86400`. Update `src/app/vercelConfig.test.ts` to assert both entries; mirror the two entries in `preview.headers` per path (Vite preview applies one header set — use a small preview middleware plugin `cacheHeadersPreview()` in `vite.config.ts` that sets `Cache-Control` by path from the same `vercel.json` blocks) and test it.
4. Agent timeline: render at most the last 200 steps (older ones collapsed under `Show <n> earlier steps`) — prevents long runs from growing the DOM.
5. `e2e/fps.spec.ts` → second test: same measurement while a replay run streams steps (`Show all steps` not pressed).

## Steps
- [ ] Measure "before" (table). Apply changes 1–5 with their tests. Measure "after".
- [ ] If a target fails after the changes, record the numbers and the cause; do not add new tooling or dependencies — report to the owner.
- [ ] All frontend checks + `e2e` + `e2e:fps` (owner's machine).
- [ ] **Docs.** FRONTEND.md → "Performance" (targets, chunks, preload, caching, timeline cap). Work-log; `STATUS.md` (last 7.2, next 7.3).
- [ ] **Commit** `perf(frontend): split chunks, preload the station model and cache static assets`.
