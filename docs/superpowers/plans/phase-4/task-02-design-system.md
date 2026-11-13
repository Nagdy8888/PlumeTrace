# Phase 4 · Task 2 — Design system: tokens, fonts, shadcn primitives

**Skills:** `plan-execution`, `frontend-design` (+ `references/control-room-workspace.md`, `references/anti-slop.md`), `shadcn`, `impeccable`, `project-documentation`. Read `.ux-profile.md`.

**Goal:** the final visual foundation every later UI task uses: exact colour tokens, IBM Plex type
(local files), a strict type scale, the `@/` path alias, shadcn primitives placed inside the repo
structure, and a few small shared primitives.

## Files (under `app/frontend/` unless noted)
| Action | Path |
|---|---|
| Modify | `package.json` (deps below), `tsconfig.json` (paths), `vite.config.ts` (alias), `src/main.tsx` (font imports), `src/styles/index.css` (final tokens) |
| Create | `components.json` (shadcn config, exact content below) |
| Create (via shadcn CLI) | `src/shared/ui/button.tsx`, `dialog.tsx`, `tooltip.tsx`, `tabs.tsx`, `separator.tsx`, `scroll-area.tsx` |
| Create | `src/shared/lib/cn.ts`, `src/shared/lib/format.ts`, `src/shared/lib/format.test.ts`, `src/shared/ui/Panel.tsx`, `src/shared/ui/Panel.test.tsx`, `src/shared/ui/StatusBadge.tsx` |

## Dependencies (exact)
`dependencies`: `"@fontsource/ibm-plex-sans": "5.3.0"`, `"@fontsource/ibm-plex-mono": "5.3.0"`, `"clsx": "2.1.1"`, `"tailwind-merge": "3.7.0"`, `"class-variance-authority": "0.7.1"`, `"lucide-react": "1.72.0"`. The shadcn CLI adds `@radix-ui/*` packages: after it runs, replace any `^`/`~` range it wrote with the exact installed version (read it from `package-lock.json`).

## Exact contents
`tsconfig.json` → add to `compilerOptions`: `"baseUrl": "."` is **not** used; add `"paths": { "@/*": ["./src/*"] }`.

`vite.config.ts` → add at top `import { fileURLToPath, URL } from "node:url";` and in the config `resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },`.

`components.json`:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": { "config": "", "css": "src/styles/index.css", "baseColor": "neutral", "cssVariables": true },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/shared/ui",
    "ui": "@/shared/ui",
    "utils": "@/shared/lib/cn",
    "lib": "@/shared/lib",
    "hooks": "@/shared/hooks"
  }
}
```

`src/shared/lib/cn.ts`:
```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class names, resolving conflicts (shadcn convention).
 *
 * @param inputs - Class values (strings, arrays, conditional objects).
 * @returns The merged class string.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

`src/main.tsx` → add before the CSS import:
```ts
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
```

`src/styles/index.css` (replace the Phase 1 placeholder block; keep the `@import "tailwindcss";` line first):
```css
@import "tailwindcss";

:root {
  /* Surfaces (grey, 4 levels) */
  --surface-0: #15171a;
  --surface-1: #1c1f23;
  --surface-2: #24282d;
  --surface-3: #2d3238;
  --border-1: #343a41;
  --border-2: #4a515a;
  --text-1: #e8eaed;
  --text-2: #a9b0b8;
  --text-3: #7c848d;
  /* Meaning */
  --accent: #5b8db8;
  --accent-contrast: #0f1b26;
  --focus: #8fb8de;
  --alarm-high: #d9534f;
  --alarm-med: #e8a33d;
  --alarm-low: #c8b44a;
  --ok: #4e9f70;
  --candidate: #f0a202;
  /* Methane concentration ramp (sequential, colour-blind safe; low -> high) */
  --ch4-0: #f6e8a6;
  --ch4-1: #f3c063;
  --ch4-2: #e8893a;
  --ch4-3: #d4502e;
  --ch4-4: #a61e22;
  /* Plume particle tint (methane is invisible; the overlay is a labelled visualisation) */
  --plume-tint: #cbc3b2;
  --radius: 4px;
  color-scheme: dark;
}

@theme {
  --font-sans: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;
  --text-xs: 12px;
  --text-xs--line-height: 16px;
  --text-sm: 13px;
  --text-sm--line-height: 18px;
  --text-base: 14px;
  --text-base--line-height: 20px;
  --text-md: 16px;
  --text-md--line-height: 22px;
  --text-lg: 20px;
  --text-lg--line-height: 26px;
  --text-xl: 24px;
  --text-xl--line-height: 30px;
  --color-surface-0: var(--surface-0);
  --color-surface-1: var(--surface-1);
  --color-surface-2: var(--surface-2);
  --color-surface-3: var(--surface-3);
  --color-border-1: var(--border-1);
  --color-border-2: var(--border-2);
  --color-text-1: var(--text-1);
  --color-text-2: var(--text-2);
  --color-text-3: var(--text-3);
  --color-accent: var(--accent);
  --color-alarm-high: var(--alarm-high);
  --color-alarm-med: var(--alarm-med);
  --color-alarm-low: var(--alarm-low);
  --color-ok: var(--ok);
  --color-candidate: var(--candidate);
  --radius-sm: var(--radius);
}

html,
body,
#root {
  height: 100%;
  margin: 0;
  background: var(--surface-0);
  color: var(--text-1);
  font-family: var(--font-sans);
  font-size: var(--text-base);
}

:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```
Update `AppShell.tsx` to use the token classes (`bg-surface-0`, `text-text-1`, `border-border-1`, …) instead of `bg-[var(--…)]`.

## Interfaces
`src/shared/lib/format.ts` (TSDoc on each):
- `formatPpm(value: number | null): string` → `"—"` for null/NaN, else 1 decimal below 100 (`"4.2 ppm"`), 0 decimals at/above 100 (`"123 ppm"`).
- `formatRate(kgPerHour: number | null): string` → `"—"` or 1 decimal + `" kg/h"`.
- `formatUtc(simStartUtc: string, tSeconds: number): string` → `"HH:MM:SS UTC"` of `simStartUtc + t`.
- `formatClock(tSeconds: number): string` → `"+HH:MM"` elapsed (e.g. `7260 → "+02:01"`).
- `compass16(fromDeg: number): string` → one of `N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW` (sector width 22.5°, centred: `0 → "N"`, `11.24 → "N"`, `11.25 → "NNE"`, `250 → "WSW"`, `359 → "N"`).

`src/shared/ui/Panel.tsx`: `Panel({ title, actions?, children, className? })` — `<section aria-labelledby>` with a 32 px header row (title `text-sm font-medium text-text-2`, optional actions on the right), 1 px `border-border-1` border, `bg-surface-1`, `rounded-sm`; body scrolls.

`src/shared/ui/StatusBadge.tsx`: `StatusBadge({ tone, children })` with `tone: "high" | "med" | "low" | "ok" | "neutral"` — small text label with a 6 px square marker in the tone colour plus the text (never colour alone).

## Tests (full code)
`src/shared/lib/format.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { compass16, formatClock, formatPpm, formatRate, formatUtc } from "./format";

describe("format", () => {
  it("formats ppm with sensible precision", () => {
    expect(formatPpm(4.21)).toBe("4.2 ppm");
    expect(formatPpm(123.4)).toBe("123 ppm");
    expect(formatPpm(null)).toBe("—");
    expect(formatPpm(Number.NaN)).toBe("—");
  });
  it("formats rates", () => {
    expect(formatRate(14.234)).toBe("14.2 kg/h");
    expect(formatRate(null)).toBe("—");
  });
  it("formats simulation time", () => {
    expect(formatUtc("2025-07-15T06:00:00Z", 3725)).toBe("07:02:05 UTC");
    expect(formatClock(7260)).toBe("+02:01");
  });
  it("maps wind direction to 16 compass points", () => {
    expect(compass16(0)).toBe("N");
    expect(compass16(11.24)).toBe("N");
    expect(compass16(11.25)).toBe("NNE");
    expect(compass16(250)).toBe("WSW");
    expect(compass16(359)).toBe("N");
  });
});
```

`src/shared/ui/Panel.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Panel } from "./Panel";

describe("Panel", () => {
  it("labels its region with the title", () => {
    render(<Panel title="Events">content</Panel>);
    expect(screen.getByRole("region", { name: "Events" })).toHaveTextContent("content");
  });
});
```

## Steps
- [ ] Install deps (exact versions); apply the alias, fonts and CSS; write tests → FAIL → implement `cn`, `format`, `Panel`, `StatusBadge`.
- [ ] `npx --yes shadcn@4.23.0 add button dialog tooltip tabs separator scroll-area` from `app/frontend` (answer "no" to overwriting `index.css`; if it insists on changing `index.css`, keep our tokens and only accept added `@layer` rules it needs). Pin the Radix versions it added.
- [ ] `npm run lint && npm run typecheck && npm run test && npm run build`; `check_slop.py` → `no slop found`; repo checks.
- [ ] Screenshot `npm run dev` at 1440×900 → `docs/evidence/2026-11-phase-4-tokens.png`; run the `impeccable` critique against `.ux-profile.md`; record findings and fixes in the work log.
- [ ] **Docs.** FRONTEND.md → "Design system": every token (name, value, meaning), fonts and licence (OFL, local files), type scale, radius, focus style, reduced motion, shadcn location and rules. Work-log; `STATUS.md` (last 4.2, next 4.3).
- [ ] **Commit** `feat(frontend): add design tokens, IBM Plex fonts and shadcn primitives`.
