---
name: frontend-structure
description: Organize and implement React/TypeScript code in the PlumeTrace Vite frontend - feature boundaries, imports, hooks, live/replay data sources, Zustand stores, React Three Fiber scene structure and rendering performance. Use for any frontend code change that is not purely visual design.
---

# Frontend Structure (PlumeTrace)

One entry point for how frontend code is organized. Upstream guidance kept as references:

- [react-feature-structure](references/react-feature-structure/GUIDE.md): feature folders, public entries, dependency direction.
- [react-best-practices](references/react-best-practices/GUIDE.md): rendering and bundle performance (upstream Vercel guidance; ignore Next.js-only and server-component rules — this is a Vite SPA).

Visual direction belongs to `frontend-design`; component mechanics to `shadcn`; everything inside
the 3D canvas (`features/station3d`) to `frontend-3d`. File size limits ("no god files") are in
`repo-structure`.

## Rules

- Layout: `app/frontend/src/app` composes the shell and providers; `app/frontend/src/features/<feature>`
  owns its UI, hooks and state behind a small `index.ts` public entry. Features:
  `station3d`, `alarms`, `agentPanel`, `trends`, `kpis`, `approval`, `scenarios`, `reports`.
  `app/frontend/src/shared` holds business-independent code only (UI primitives, units formatting,
  types generated from backend schemas). Shared code never imports a feature.
- **One data-source interface, two implementations:** `LiveSource` (relative `/api/...` REST
  calls and, from Phase 5, the `/api/runs/{id}/ws` WebSocket to FastAPI) and `ReplaySource`
  (fetches `/replay/scenarios/*.json` + `/replay/traces/*/*.json`, copied from `app/replay/` into
  `public/replay/` by `npm run copy:replay`). Code in `shared/data/`. Features consume the interface,
  never the transport. The public build ships only `ReplaySource`; no backend URL or key in it.
- State: Zustand stores per concern (simulation clock, sensor stream, agent run, selection).
  High-frequency sensor/plume data never goes through React state per tick — use refs or store
  subscriptions read inside `useFrame`.
- 3D: the R3F canvas lives in `features/station3d`; the static station is the Blender-baked
  `public/models/ks07.glb` generated from the spec (approach B; fallback A builds equipment as
  procedural R3F components). Tags, positions and anchors come from `shared/facility/ks07.json`
  (generated from the backend spec). Local assets only; no runtime downloads. See `frontend-3d`.
- Types for events, traces and drafts are generated from the backend Pydantic schemas; never
  hand-copy them.
- Never show Approved / Issued / Filed optimistically; those states come from the graph result.
- Every exported function, component, hook and store has a short doc comment stating its contract.
- Checks: `npm run lint`, `npm run typecheck`, `npm run test` (Vitest); browser flows with
  Playwright. Run them and show the output before calling a task done.
