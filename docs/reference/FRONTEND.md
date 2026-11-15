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
| @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono | 5.3.0 |
| clsx, tailwind-merge, class-variance-authority | 2.1.1, 3.7.0, 0.7.1 |
| lucide-react, radix-ui | 1.72.0, 1.8.1 |
| shadcn CLI (run with `npx`, not installed) | 4.23.0 |

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
- `src/shared/lib/` holds `cn.ts` (class merging) and `format.ts` (units and time formatting).
- `src/shared/ui/` holds the shadcn primitives (lower-case file names, generated) and our own
  shared primitives `Panel.tsx` and `StatusBadge.tsx` (PascalCase).
- `src/styles/index.css` imports Tailwind and defines the design tokens.
- The `@/` alias points to `src/` (`tsconfig.json` `paths`, `vite.config.ts` `resolve.alias`).

## Design system

Final since Phase 4 Task 2. Everything lives in `src/styles/index.css`; components use token
classes (`bg-surface-1`, `text-text-2`, `border-border-1`), never raw hex or `bg-[var(--x)]`.

### Colour tokens

Surfaces are grey in four levels, separated by 1 px borders rather than shadows. Colour is
reserved for meaning (ISA-101 spirit). Contrast ratios are computed (WCAG 2.x relative luminance).

| Token | Value | Meaning | Contrast on surface-0 / surface-1 |
|---|---|---|---|
| `--surface-0` | `#15171a` | App background, 3D view surround | n/a |
| `--surface-1` | `#1c1f23` | Panel body | n/a |
| `--surface-2` | `#24282d` | Raised controls, dialogs | n/a |
| `--surface-3` | `#2d3238` | Hover and selected rows | n/a |
| `--border-1` | `#343a41` | Panel and divider lines | 1.4 on surface-1 (decorative) |
| `--border-2` | `#4a515a` | Control outlines | 2.1 on surface-1 |
| `--text-1` | `#e8eaed` | Primary text and values | 14.9 / 13.7 |
| `--text-2` | `#a9b0b8` | Secondary text, units, panel titles | 8.2 / 7.6 |
| `--text-3` | `#7c848d` | Tertiary, disabled | 4.7 / 4.4 |
| `--accent` | `#5b8db8` | The one action hue (primary buttons) | 5.1 / 4.7 |
| `--accent-contrast` | `#0f1b26` | Text on `--accent` | 4.9 on accent |
| `--focus` | `#8fb8de` | Focus ring (`:focus-visible`, 2 px, offset 2 px) | 8.6 / 7.9 |
| `--alarm-high` | `#d9534f` | Alarm priority high | 4.5 / 4.2 |
| `--alarm-med` | `#e8a33d` | Alarm priority medium | 8.3 / 7.7 |
| `--alarm-low` | `#c8b44a` | Alarm priority low | 8.6 / 7.9 |
| `--ok` | `#4e9f70` | Normal, approved, healthy | 5.6 / 5.1 |
| `--candidate` | `#f0a202` | AI-located leak candidate | 8.4 / 7.8 |
| `--ch4-0` to `--ch4-4` | `#f6e8a6`, `#f3c063`, `#e8893a`, `#d4502e`, `#a61e22` | Methane concentration ramp, low to high, colour-blind safe, sequential | data colours |
| `--plume-tint` | `#cbc3b2` | Plume particle tint; methane is invisible, so the overlay is a labelled visualisation | data colour |

Rules that follow from the numbers:

- `--text-3` falls below 4.5:1 on surface-1 and below. Use it only for non-essential or disabled
  text on surface-0, never for a value, unit or label an operator must read.
- `--alarm-high` as text is 4.2:1 on surface-1. State and priority are carried by the marker shape
  and the word (see `StatusBadge`), the colour only reinforces them.
- `--ch4-3` and `--alarm-high` are both red-orange. A concentration colour must never be the only
  sign of an alarm, and an alarm must never be shown as a concentration colour.

Tailwind classes come from the `@theme` block: `bg-surface-0..3`, `border-border-1|2`,
`text-text-1|2|3`, `bg-accent`, `bg-alarm-high|med|low`, `bg-ok`, `bg-candidate`. The `--ch4-*` and
`--plume-tint` tokens are read by the 3D and chart code through `var()`.

### Typography

IBM Plex Sans (interface) and IBM Plex Mono (tags such as K-202 and PIC-101, values, timestamps),
chosen as an engineering-drawing family with true tabular figures. Licence: SIL Open Font
License 1.1 (package licence `OFL-1.1`, @fontsource 5.3.0). Files come from the npm packages
`@fontsource/ibm-plex-sans` (400, 500, 600) and `@fontsource/ibm-plex-mono` (400, 500), imported in
`src/main.tsx` and bundled by Vite: no font is fetched from a network at run time.

| Class | Size / line height | Use |
|---|---|---|
| `text-xs` | 12 / 16 | Units, badges, table meta |
| `text-sm` | 13 / 18 | Panel titles, table cells |
| `text-base` | 14 / 20 | Body (set on `html`) |
| `text-md` | 16 / 22 | Section headings |
| `text-lg` | 20 / 26 | Dialog titles |
| `text-xl` | 24 / 30 | KPI values |

Numbers use `font-mono` or `tabular-nums` and always carry their unit in a quieter weight.

### Shape, focus, motion

- Radius: `--radius` 4 px (`rounded-sm`, also `rounded-md`); dialogs and tab lists 6 px
  (`rounded-lg`). No larger radius on product surfaces.
- Focus: every `:focus-visible` gets a 2 px `--focus` outline with a 2 px offset.
- Reduced motion: under `prefers-reduced-motion: reduce` animation and transition durations
  drop to 0.01 ms.

### shadcn primitives

Config: `app/frontend/components.json` (style `new-york`, Radix, Tailwind v4, no `tailwind.config`,
icons `lucide`). Aliases map components and ui to `@/shared/ui`, utils to `@/shared/lib/cn`.
Added with the pinned CLI: `npx --yes shadcn@4.23.0 add <name>` run from `app/frontend`. Present:
`button`, `dialog`, `tooltip`, `tabs`, `separator`, `scroll-area`.

Rules:

- shadcn's semantic names are mapped onto our tokens in the `@theme inline` block of `index.css`
  (`background` is surface-2, `foreground` text-1, `muted` surface-3, `muted-foreground` text-2,
  `primary` accent, `primary-foreground` accent-contrast, `secondary` surface-3, `destructive`
  alarm-high, `border` border-1, `input` border-2, `ring` focus). There is no second palette.
- `--color-accent` stays our action hue, so the shadcn "hover surface" role is not `accent`:
  `button.tsx` (outline, ghost), `dialog.tsx` (close button) and `tooltip.tsx` use `surface-3`
  directly. Re-adding a component with `--overwrite` loses these edits; redo them from this list.
- Edits to generated files are limited to token classes, import paths and a TSDoc line per
  export (the lint rule requires it). The CLI wrote `from "cn"` and added an npm package `cn`
  for the `utils` alias; the imports were changed to `@/shared/lib/cn` and the package removed.
- Lucide icons only, monochrome. `TooltipProvider` must wrap the app when the first tooltip is used.

### Shared primitives

- `Panel({ title, actions?, children, className? })`: `<section aria-labelledby>` with a 32 px
  header, 1 px `border-border-1` border, `bg-surface-1`, scrolling body.
- `StatusBadge({ tone, children })`: tones `high`, `med`, `low`, `ok`, `neutral`; a 6 px square
  marker plus text, never colour alone.

### Formatting helpers (`src/shared/lib/format.ts`)

| Function | Result |
|---|---|
| `formatPpm(v)` | `"4.2 ppm"` below 100, `"123 ppm"` from 100; `"—"` for null or non-finite |
| `formatRate(kgPerHour)` | `"14.2 kg/h"`; `"—"` for null or non-finite |
| `formatUtc(simStartUtc, t)` | `"HH:MM:SS UTC"`; `"—"` for an invalid start or non-finite `t` |
| `formatClock(t)` | `"+HH:MM"` elapsed; `"—"` for non-finite `t` |
| `compass16(fromDeg)` | one of 16 compass names, 22.5 degree sectors centred on the point |

Display rules owned by the callers (Gate 3 owner decisions, 2026-11-15):

- Every clock shows a zone label. `formatUtc` always ends in `UTC`. A station-local time gets its
  own label `UTC+5 station time`. `formatClock` is an elapsed duration, not a time of day, and must
  be labelled as elapsed.
- A leak rate is shown only as an interval, `p05-p95 kg/h (median p50)`, 2 significant figures,
  labelled `model estimate`. `formatRate` formats one number to one decimal and cannot enforce
  that; components call it per interval bound and add the interval and the label (a later task
  owns that component). Never show a bare rate.
- Replay `keyframes[].sources` drives the plume visual only and is never rendered as text.

### Evidence

`docs/evidence/2026-11-phase-4-tokens.png`: 1440x900 screenshot of the dev server with a token
and type-scale specimen injected into the DOM for the screenshot only (no specimen code is in the
repo).

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

Fixed-length tuples (for example a position `[x, y, z]`) reach the schema as JSON Schema 2020-12
`prefixItems`, which json-schema-to-typescript 16.0.0 ignores and types as `unknown`.
`scripts/export_contract.py` therefore rewrites every `prefixItems` to the draft-07 `items` array
(with `minItems` and `maxItems`), so the generated type is `[number, number, number]`. A node that
has both keywords is an error. `app/backend/tests/test_contract_types.py` checks the rewrite, the
schema and the committed `contract.ts`.
