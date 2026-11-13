# Phase 7 · Task 3 — Demo video: storyboard, scripted capture, MP4 + poster, mobile page

**Skills:** `plan-execution`, `video-shotcraft:video-shotcraft` (storyboard only), `playwright-cli`, `frontend-design`, `project-documentation`.
**Docs to check first:** @playwright/test 1.65.0 `recordVideo` (context option, `size`), FFmpeg 8.1 `libx264`, `-movflags +faststart`.

## Storyboard (60–90 s, silent, 1920×1080, captured from the replay build at the review camera)
| Time | Shot | Action in the app |
|---|---|---|
| 0–6 s | Landing | Fresh load: station at golden hour, top bar with `Replay of a recorded AI run` and `Simulated` |
| 6–20 s | The release | S1 at 120×: heat-map grows downwind of VS-250, wind readout, first alarms arrive in the list |
| 20–40 s | Agents work | Clock pauses (`Agents investigating`); timeline fills (Triage → Locate and quantify → Compliance → Drafting); candidate glow on VS-250; camera flies to VS-250 (click the alarm) |
| 40–55 s | Human decides | Approval dialog; hover the locked `kg/h` value → source tooltip; click `Approve` |
| 55–68 s | Result | `Work order issued (simulated). Report filed (simulated).` |
| 68–80 s | Not every alarm is a leak | Switch to S5: `Show all steps`; instrument ticket for AT-106, no report line |
| 80–88 s | Honesty | Open `About this demo`, rest on the `Accuracy` section; end |
Write it to `docs/launch/video-storyboard.md` (this table + one sentence per shot on why it is there). Run the `video-shotcraft` skill on it for pacing and shot order; apply only changes that keep every shot real (no edited UI, no fake numbers).

## Files
| Action | Path |
|---|---|
| Create | `docs/launch/video-storyboard.md` |
| Create | `app/frontend/e2e/capture-demo.spec.ts` (run only by `npm run capture:demo`) |
| Modify | `app/frontend/playwright.config.ts` → new project `capture` (`testMatch: ["**/capture-demo.spec.ts"]`, same `use` as `webgl`); `no-webgl` `testIgnore` gains `"**/capture-demo.spec.ts"` (`webgl` already matches only its three specs); `package.json` → script `"capture:demo": "playwright test --project=capture"` |
| Create | `scripts/encode_demo.sh` |
| Generated | `app/frontend/public/media/plumetrace-demo.mp4` (≤ 20 MB), `app/frontend/public/media/plumetrace-poster.jpg` (≤ 250 KB), `build/video/plumetrace-demo-4x5.mp4` (LinkedIn crop, not deployed) |
| Modify | `app/frontend/src/app/MobilePage.tsx` (+ test) — the video |

`capture-demo.spec.ts`: a single test that creates its own context with `recordVideo: { dir: "../../build/video/raw", size: { width: 1920, height: 1080 } }`, viewport 1920×1080, and performs the storyboard actions with fixed waits (`page.waitForTimeout`) matching the shot lengths; closes the context so the video file is written; logs the file path.
`scripts/encode_demo.sh` (exact):
```bash
#!/usr/bin/env bash
# Encode the captured demo (webm) to web MP4 + poster + a 4:5 LinkedIn crop. Run from the repo root.
set -euo pipefail
ffmpeg -version | head -n 1 | grep -q "^ffmpeg version 8\.1" || { echo "FFmpeg 8.1 required"; exit 2; }
RAW="$(ls -t build/video/raw/*.webm | head -n 1)"
mkdir -p app/frontend/public/media build/video
ffmpeg -y -i "$RAW" -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -movflags +faststart -an \
  app/frontend/public/media/plumetrace-demo.mp4
ffmpeg -y -ss 00:00:44 -i app/frontend/public/media/plumetrace-demo.mp4 -frames:v 1 -q:v 3 \
  app/frontend/public/media/plumetrace-poster.jpg
ffmpeg -y -i app/frontend/public/media/plumetrace-demo.mp4 -vf "crop=864:1080:528:0,scale=1080:1350" \
  -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -movflags +faststart -an build/video/plumetrace-demo-4x5.mp4
ls -l app/frontend/public/media build/video/plumetrace-demo-4x5.mp4
```
**MobilePage** gains, under the heading and paragraph: `<video controls muted playsInline preload="metadata" poster="/media/plumetrace-poster.jpg" width="1920" height="1080" aria-describedby="demo-caption"><source src="/media/plumetrace-demo.mp4" type="video/mp4" /></video>` and the caption `<p id="demo-caption">A 90-second recording of the replay: a simulated leak, the agents' investigation and an operator approval.</p>`; the fallback image moves below. Test: the `video` element has the poster and source, `muted` and `playsInline` set, and the caption is linked.

## Steps
- [ ] Storyboard + `video-shotcraft` review. Show the storyboard to the owner; wait for an OK before capturing.
- [ ] `npm run capture:demo` (owner's machine, high quality tier forced in the spec) → `scripts/encode_demo.sh`.
- [ ] Watch the MP4 end to end. Re-capture if anything stutters, a label is cut off, or a number differs from the evidence. Check file sizes against the limits.
- [ ] MobilePage change + test; `e2e` mobile spec still passes (the video must not trigger a `.glb` request).
- [ ] Repo checks; `check_slop.py`.
- [ ] **Docs.** `docs/launch/video-storyboard.md` (final), FRONTEND.md → "Mobile page" (video), ASSETS.md (the video and poster are generated from this repo). Work-log; `STATUS.md` (last 7.3, next 7.4).
- [ ] **Commit** `feat(launch): add demo video, poster and mobile video page`.
