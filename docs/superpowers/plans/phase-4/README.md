# Phase 4 — Backend API, control-room UI and the 3D station

> **For agentic workers:** load `plan-execution`, `frontend-structure`, `frontend-design`,
> `frontend-3d` (3D tasks) first. **Start only after Owner Gate 3** (scenario scripts) is signed
> off in STATUS.md. Task 5 ends with an owner review of the Blender spike screenshot: STOP there.

**Goal:** a local FastAPI backend serving scenarios, the dark control-room UI (top bar, alarms,
trends, playback) built on one data-source interface (live API or static replay), and the 3D
station generated in Blender from `ks07.yaml`, loaded by React Three Fiber with plumes, heat-map,
highlights and camera — all within the 60 fps budget and the anti-slop rules.

**Spec:** design §9, §10; `.ux-profile.md`; skills `frontend-3d` (+ `references/blender-pipeline.md`), `frontend-structure`, `frontend-design` (+ `references/control-room-workspace.md`, `anti-slop.md`).

## Task order
| # | File | Delivers |
|---|---|---|
| 1 | `task-01-fastapi-app.md` | FastAPI app: health, scenario list, scenario replay endpoint, CORS |
| 2 | `task-02-design-system.md` | final tokens, IBM Plex fonts, shadcn init, base UI primitives |
| 3 | `task-03-data-layer.md` | `DataSource` interface, `ReplaySource`, `LiveSource`, playback clock and run stores |
| 4 | `task-04-panels.md` | top bar, alarm list, trends (uPlot), playback bar, scenario picker; layout |
| 5 | `task-05-blender-spike.md` | Blender spike (one skid + VS-250) → **owner gate** |
| 5b | `task-05b-fallback-procedural.md` | only if the owner rejects the spike: approach A |
| 6 | `task-06-bpy-equipment.md` | bpy parts + all equipment types |
| 7 | `task-07-bpy-site-bake-export.md` | piping, ground, materials, bake, glTF export + optimise + validation |
| 8 | `task-08-r3f-station.md` | canvas, model loading, node index, hit proxies, camera, quality tiers |
| 9 | `task-09-plume-effects.md` | plume particles, ground heat-map, wind indicator, sensor markers, candidate highlight |
| 10 | `task-10-accessibility-mobile.md` | DOM equipment list, WebGL fallback, reduced motion, mobile video page |
| 11 | `task-11-e2e-performance.md` | Playwright flows, visual baseline, fps measurement, phase evidence |

## Pinned additions (checked 2026-11-13)
| Package / tool | Version | Where |
|---|---|---|
| fastapi | 0.162.5 | backend |
| uvicorn[standard] | 0.54.0 | backend |
| three, @types/three | 0.187.0 | frontend |
| @react-three/fiber | 9.8.2 | frontend (peer: react `>=19 <19.4` — React 19.3.1 OK) |
| @react-three/drei | 10.7.9 | frontend |
| @react-three/postprocessing | 3.2.2 | frontend |
| postprocessing | 6.39.6 | frontend |
| @react-three/test-renderer | 9.1.1 | frontend dev |
| @react-three/eslint-plugin | 0.1.2 | frontend dev |
| zustand | 5.1.0 | frontend |
| uplot | 1.6.32 | frontend |
| shadcn (CLI) | 4.23.0 | `npx --yes shadcn@4.23.0 …` |
| lucide-react | 1.72.0 | frontend |
| clsx / tailwind-merge / class-variance-authority | 2.1.1 / 3.7.0 / 0.7.1 | frontend |
| @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono | 5.3.0 | frontend |
| @playwright/test | 1.65.0 | frontend dev |
| @axe-core/playwright | 4.14.0 | frontend dev |
| r3f-perf | 7.2.3 | frontend dev (dev builds only) |
| @gltf-transform/cli | 4.5.1 | `npx --yes @gltf-transform/cli@4.5.1 …` |
| Blender | **4.5.16 LTS** | installed by the owner (blender.org); `blender --version` must print 4.5.16 |
| Poly Haven CC0 assets | ids in `task-05-blender-spike.md` | `scripts/blender/polyhaven_manifest.json` (SHA-256 recorded on first download) |

## Global constraints
- Everything in earlier phases applies; frontend rules: `frontend-structure` (feature folders, `index.ts` entries, data only via `shared/data`), anti-slop (`check_slop.py` + screenshot critique for every UI task), TSDoc on exports, ≤ 250 lines per TS/TSX file.
- The frontend calls only relative URLs (`/api/...`, `/replay/...`); Vite proxies `/api` to `http://127.0.0.1:8000` in dev. No backend URL in code, no env files.
- Backend binds `127.0.0.1:8000`; CORS allows only `http://localhost:5173` and `http://127.0.0.1:5173`.
- Replay-only build: `vite build --mode replay`. Code paths for the live API are reached only through `import.meta.env.MODE !== "replay"` so they are dropped from the replay bundle.
- 3D: approach B (Blender-baked) unless the owner rejects the spike; budgets from `frontend-3d`.
- After Task 5 the path forks: owner **go** → Tasks 6, 7, 8 …; owner **no-go** → Task 5b, then 8 … (6 and 7 skipped). STATUS.md records the answer.
- Downloads (Poly Haven assets, the Playwright browser) need the owner's yes in chat first.

## Review focus
1. Backend down while the UI runs in live mode → panels show a clear "Backend not reachable — start it with …" state, no crash (Task 3).
2. Scenario switch during playback → clock resets, old data never mixes with new (Task 3).
3. WebGL unavailable / context lost → static fallback image + equipment list, panels still work (Task 10).
4. `prefers-reduced-motion` → no automatic camera flights, slower plume (Tasks 8–10).
5. Narrow / touch viewport → mobile video page, no 3D download (Task 10).

## Phase exit — Owner Gate 4 (UI review)
`docs/evidence/2026-11-phase-4-ui.md` with screenshots (1440×900, S1 at the event time), fps measurements (hardware named), glb size, draw calls/triangles, `check_slop.py` output and the critique summary. `STATUS.md`: "Phase 4 complete — waiting for Gate 4 (UI review)". STOP.
