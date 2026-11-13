# Deployment

Deployment is a later phase that is not planned yet (owner decision 2026-11-13); nothing is
deployed during development. The settings below are recorded for that later phase only. Do not
create a Vercel project or run a `vercel` command now.

## Vercel project settings (for the later phase)

| Setting | Value |
|---|---|
| Root directory | `app/frontend` |
| Framework preset | Vite |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Environment variables | **none**: Vercel holds no secrets; the frontend reads no env file |

## Headers and rewrites

`app/frontend/vercel.json` carries the security headers for every path (`/(.*)`) and rewrites all
paths to `/index.html` (single-page app). `src/app/vercelConfig.test.ts` pins every value.

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` |

`connect-src 'self'` means the public build calls no other origin: it plays recorded replay data
only and never reaches Supabase or OpenAI.
