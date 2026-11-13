# Frontend

## Purpose

`app/frontend/` is the PlumeTrace control-room web app: React + TypeScript + Vite. Phase 1 Task 5
delivers only the scaffold: a top bar with the product name and a "Simulated" label, an empty
station region, the design tokens, lint, type-check, tests, build and the Vercel security headers
(recorded for a later phase; see [DEPLOYMENT.md](DEPLOYMENT.md)). Design reference: section 9;
visual rules: `.ux-profile.md`.

## Stack and pinned versions

Exact versions are in `app/frontend/package.json` and `package-lock.json`; the full table is in
[LOCAL_DEVELOPMENT.md](../LOCAL_DEVELOPMENT.md#pinned-versions).

| Package | Version |
|---|---|
| react, react-dom | 19.3.1 |
| vite, @vitejs/plugin-react | 8.3.8, 6.3.0 |
| tailwindcss, @tailwindcss/vite | 4.3.5 |
| typescript | 6.0.3 (not 7.x: typescript-eslint 8.72.2 needs `<6.1`) |
| eslint, typescript-eslint | 10.14.0, 8.72.2 |
| vitest, @vitest/coverage-v8 | 5.1.0 (the two must match) |
| jsdom | 29.1.1 (30+ needs Node 22.22 or newer) |
| @testing-library/react, dom, jest-dom | 16.3.3, 10.4.2, 7.0.1 |

Node `>=22.13.0` (`engines` in `package.json`).

## Scripts

Run from `app/frontend/`.

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server on `http://localhost:5173` |
| `npm run build` | Type-check, then `vite build` into `dist/` (git-ignored) |
| `npm run preview` | Serve `dist/` locally |
| `npm run lint` | ESLint (typescript-eslint, react-hooks, react-refresh, jsdoc) |
| `npm run typecheck` | `tsc --noEmit` (strict, `noUncheckedIndexedAccess`) |
| `npm run test` | Vitest, one run |
| `npm run test:coverage` | Vitest with v8 coverage; thresholds lines 80, functions 80, branches 70, statements 80 |
| `npm run gen:types` | `json2ts` (json-schema-to-typescript 16.0.0): `contract.schema.json` to `contract.ts` (see Type contract) |

## Folder rules

`src/` may contain only `main.tsx`, `vite-env.d.ts`, `app/`, `features/`, `shared/` and `styles/`.
`check_structure.py` enforces it, together with the size limits (TS/TSX file at most 250 lines,
tests at most 400). A feature folder is used through its `index.ts` only. The full rules are in the
`frontend-structure` skill.

- `src/app/` holds `AppShell.tsx`, the top-level layout.
- `src/shared/testing/setup.ts` is the Vitest setup file (jest-dom matchers, cleanup after each test).
- `src/styles/index.css` imports Tailwind and defines the design tokens.

## Design tokens

CSS custom properties on `:root` in `src/styles/index.css`. The names are stable; the values are
**placeholders until Phase 4**.

`--surface-0`, `--surface-1`, `--surface-2`, `--surface-3`, `--border-1`, `--border-2`, `--text-1`,
`--text-2`, `--accent`, `--alarm-high`, `--alarm-med`, `--alarm-low`, `--ok`.

Surfaces are grey; colour is reserved for meaning (alarm, ok, accent).

## Anti-slop gate

Every UI task runs `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src`,
which must print `no slop found`, and records a screenshot critique in `docs/WORK_LOG.md`.
Rules: `.ux-profile.md` and `.claude/skills/frontend-design/references/anti-slop.md`.

## Tests

Vitest with the `jsdom` environment and Testing Library. Setup: `src/shared/testing/setup.ts`.
Tests live beside the code as `*.test.ts(x)`. `src/app/vercelConfig.test.ts` reads `vercel.json`
and pins the security headers and the SPA rewrite.

## Type contract

The Pydantic models in `app/backend/plumetrace/facility/` are the source of truth. The frontend
never hand-copies a type or the facility data; it uses three generated files:

| File | Produced by |
|---|---|
| `src/shared/types/generated/contract.schema.json` | `scripts/export_contract.py` (`FacilitySpec.model_json_schema()`) |
| `src/shared/types/generated/contract.ts` | `npm run gen:types` (from the schema) |
| `src/shared/facility/ks07.json` | `scripts/export_contract.py` (`load_facility()` as JSON) |

Regenerate, in this order:

```
cd app && uv run python ../scripts/export_contract.py
cd frontend && npm run gen:types
```

Never edit the generated files by hand; change the Pydantic model or `ks07.yaml` and regenerate.
Output is deterministic: UTF-8, LF line endings, sorted keys, trailing newline (bytes are written,
so Windows does not add CRLF; `.gitattributes` also forces LF). The generated folder is excluded
from ESLint. Drift check: `python scripts/ci_local.py --full`, stage `contract-drift` (Task 8),
re-runs both commands and fails if `git diff` is not empty.
