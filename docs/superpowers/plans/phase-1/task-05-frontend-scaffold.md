# Phase 1 · Task 5 — Frontend scaffold ready for Vercel

**Read first:** design §9, `.ux-profile.md`, `phase-1/README.md` (pinned versions). **Skills:** `plan-execution`, `frontend-structure`, `frontend-design` (+ its `references/anti-slop.md`), `security-checks`, `project-documentation`.

**Goal:** a minimal, clean React app (no template boilerplate) with lint, typecheck, tests and
build working, the design tokens placeholder, and `vercel.json` carrying the security headers.
Do **not** run `npm create vite` — write the files below exactly.

## Files (all under `app/frontend/` unless noted)
| Action | Path |
|---|---|
| Create | `package.json`, `tsconfig.json`, `vite.config.ts`, `eslint.config.js`, `index.html`, `vercel.json` |
| Create | `src/main.tsx`, `src/vite-env.d.ts`, `src/styles/index.css`, `src/app/AppShell.tsx` |
| Create | `src/shared/testing/setup.ts` |
| Create (tests) | `src/app/AppShell.test.tsx`, `src/app/vercelConfig.test.ts` |
| Generated | `package-lock.json`, `node_modules/` (ignored), `dist/` (ignored) |
| Create | `docs/reference/FRONTEND.md`, `docs/reference/DEPLOYMENT.md`; modify `docs/LOCAL_DEVELOPMENT.md` → `## Frontend`, `docs/README.md` |

`src/` may only contain `main.tsx`, `vite-env.d.ts`, `app/`, `features/`, `shared/`, `styles/` (checked by `check_structure.py`).

## Exact file contents

`package.json`:
```json
{
  "name": "plumetrace-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": { "node": ">=22.13.0" },
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit -p tsconfig.json && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit -p tsconfig.json",
    "test": "vitest run",
    "test:coverage": "vitest run --coverage"
  },
  "dependencies": {
    "react": "19.3.1",
    "react-dom": "19.3.1"
  },
  "devDependencies": {
    "@eslint/js": "10.0.1",
    "@tailwindcss/vite": "4.3.5",
    "@testing-library/dom": "10.4.2",
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.3",
    "@types/node": "26.6.6",
    "@types/react": "19.3.0",
    "@types/react-dom": "19.3.0",
    "@vitest/coverage-v8": "5.1.0",
    "@vitejs/plugin-react": "6.3.0",
    "eslint": "10.14.0",
    "eslint-plugin-jsdoc": "65.4.5",
    "eslint-plugin-react-hooks": "7.1.1",
    "eslint-plugin-react-refresh": "0.5.7",
    "globals": "17.14.0",
    "jsdom": "29.1.1",
    "tailwindcss": "4.3.5",
    "typescript": "6.0.3",
    "typescript-eslint": "8.72.2",
    "vite": "8.3.8",
    "vitest": "5.1.0"
  }
}
```

`tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "skipLibCheck": true,
    "noEmit": true,
    "types": ["vite/client", "node"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`vite.config.ts`:
```ts
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/shared/testing/setup.ts"],
    css: false,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/main.tsx",
        "src/shared/types/generated/**",
        "src/shared/testing/**",
        "src/features/station3d/scene/**",
      ],
      thresholds: { lines: 80, functions: 80, branches: 70, statements: 80 },
    },
  },
});
```

`eslint.config.js`:
```js
import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import jsdoc from "eslint-plugin-jsdoc";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig(
  { ignores: ["dist", "node_modules", "src/shared/types/generated"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { ecmaVersion: 2023, globals: globals.browser },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh, jsdoc },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "jsdoc/require-jsdoc": [
        "error",
        {
          publicOnly: true,
          require: { FunctionDeclaration: true, ArrowFunctionExpression: true, ClassDeclaration: true },
        },
      ],
    },
  },
);
```

`index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PlumeTrace</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`vercel.json`:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains" }
      ]
    }
  ]
}
```

`src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />
```

`src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AppShell } from "./app/AppShell";
import "./styles/index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <AppShell />
  </StrictMode>,
);
```

`src/styles/index.css` (placeholder palette — Phase 4 replaces the values, not the names):
```css
@import "tailwindcss";

/* Design tokens (semantic names are stable; values are placeholders until Phase 4).
   Grey surfaces, colour reserved for meaning — see .ux-profile.md. */
:root {
  --surface-0: #16181a;
  --surface-1: #1d2023;
  --surface-2: #25292d;
  --surface-3: #2e3338;
  --border-1: #353a40;
  --border-2: #4a5058;
  --text-1: #e6e8ea;
  --text-2: #a7adb4;
  --accent: #4f8fc0;
  --alarm-high: #d64545;
  --alarm-med: #e0a030;
  --alarm-low: #c9b458;
  --ok: #3f9b6b;
  color-scheme: dark;
}

html,
body,
#root {
  height: 100%;
  margin: 0;
  background: var(--surface-0);
  color: var(--text-1);
}
```

`src/app/AppShell.tsx`:
```tsx
import type { JSX } from "react";

/**
 * Top-level layout of the PlumeTrace control room.
 *
 * Phase 1 renders only the top bar and an empty station region; later phases fill the
 * station view, panels and trends. The "Simulated" label is always visible because every
 * station value is simulated (design section 8).
 *
 * @returns The application shell.
 */
export function AppShell(): JSX.Element {
  return (
    <div className="flex h-full flex-col bg-[var(--surface-0)] text-[var(--text-1)]">
      <header className="flex items-center justify-between border-b border-[var(--border-1)] px-4 py-2">
        <h1 className="text-base font-semibold">PlumeTrace</h1>
        <span className="rounded-sm border border-[var(--border-2)] px-2 py-0.5 text-xs text-[var(--text-2)]">
          Simulated
        </span>
      </header>
      <main aria-label="Station view" className="flex-1" />
    </div>
  );
}
```

`src/shared/testing/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
```

## Tests (full code)

`src/app/AppShell.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("shows the product name and the simulated-data label", () => {
    render(<AppShell />);
    expect(screen.getByRole("heading", { level: 1, name: "PlumeTrace" })).toBeInTheDocument();
    expect(screen.getByText("Simulated")).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Station view" })).toBeInTheDocument();
  });
});
```

`src/app/vercelConfig.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import vercel from "../../vercel.json";

const headersFor = (source: string): Map<string, string> => {
  const block = vercel.headers.find((h) => h.source === source);
  if (!block) throw new Error(`no headers block for ${source}`);
  return new Map(block.headers.map((h) => [h.key, h.value]));
};

describe("vercel.json security headers", () => {
  const h = headersFor("/(.*)");

  it("sets a strict content security policy", () => {
    const csp = h.get("Content-Security-Policy") ?? "";
    for (const part of [
      "default-src 'self'",
      "script-src 'self' 'wasm-unsafe-eval'",
      "worker-src 'self' blob:",
      "connect-src 'self'",
      "img-src 'self' data: blob:",
      "style-src 'self' 'unsafe-inline'",
      "font-src 'self'",
      "frame-ancestors 'none'",
    ]) {
      expect(csp).toContain(part);
    }
  });

  it("sets the other security headers", () => {
    expect(h.get("X-Content-Type-Options")).toBe("nosniff");
    expect(h.get("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
    expect(h.get("Permissions-Policy")).toBe("camera=(), microphone=(), geolocation=()");
    expect(h.get("Strict-Transport-Security")).toBe("max-age=63072000; includeSubDomains");
  });

  it("rewrites unknown paths to the SPA entry", () => {
    expect(vercel.rewrites).toEqual([{ source: "/(.*)", destination: "/index.html" }]);
  });
});
```

## Steps
- [ ] **1.** Create every file above (tests included) exactly as shown.
- [ ] **2.** `cd app/frontend && npm install` → creates `package-lock.json`; no `ERESOLVE` errors. If there is any peer-dependency error, STOP and paste it.
- [ ] **3.** `npm run lint` → no errors; `npm run typecheck` → no errors; `npm run test` → 4 tests pass (1 + 3); `npm run build` → `dist/` created.
- [ ] **4.** From the repo root: `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src` → `no slop found`; plus the three repo checks.
- [ ] **5.** `npm run dev`, open the printed URL in the browser (Playwright or the built-in browser), take a screenshot at 1440×900, save it as `docs/evidence/2026-11-phase-1-shell.png`. It should show a dark grey page with "PlumeTrace" and a small "Simulated" label. Stop the dev server.
- [ ] **6. Docs.**
  - `docs/reference/FRONTEND.md`: stack and pinned versions (link LOCAL_DEVELOPMENT), scripts, folder rules (`src/` children, features via `index.ts`, see `frontend-structure`), design tokens list (names + "placeholder until Phase 4"), anti-slop gate, tests (Vitest + Testing Library, setup file path).
  - `docs/reference/DEPLOYMENT.md`: Vercel project settings — root directory `app/frontend`, install `npm ci`, build `npm run build`, output `dist`, framework preset Vite, **no environment variables**; headers come from `vercel.json` (list them); start the page with "Deployment is a later phase that is not planned yet (owner decision 2026-11-13); nothing is deployed during development." — the settings above are recorded for that later phase only.
  - `docs/LOCAL_DEVELOPMENT.md` → `## Frontend`: `cd app/frontend`, `npm ci`, `npm run dev|lint|typecheck|test|build`.
  - `docs/README.md`: add both reference rows. Work-log row; `STATUS.md` (last 1.5, next 1.6).
- [ ] **7. Commit** `feat(frontend): scaffold React app shell with Vercel security headers` (include `package-lock.json`; never `node_modules/` or `dist/`).

## If something in a config does not work with the pinned versions
Only these adaptations are allowed, and each must be noted in the work log: (a) if `eslint/config`
has no `defineConfig`, use `tseslint.config(...)` with the same blocks; (b) if Vitest rejects
`css: false`, remove that line. Anything else: STOP and report.
