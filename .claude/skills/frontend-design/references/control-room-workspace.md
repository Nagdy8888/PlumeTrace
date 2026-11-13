# Control-room workspace design (PlumeTrace)

PlumeTrace is a methane leak control-room application for a (simulated) gas compressor station.
Its audience is process, operations and emissions engineers, and LinkedIn viewers who judge it
in a few seconds. It must read as a real industrial product, not a demo. The layout is set in the
design doc (`docs/superpowers/specs/2026-11-12-plumetrace-design.md`, section 9): 3D station in the
centre, events/alarms left, agent timeline right, trends bottom, KPIs top, approval dialog.

## Expression and working surfaces
The 3D station is the one expressive surface: lighting, plumes, the camera fly-to on a located
leak. Everything around it (alarm list, agent panel, trends, approval dialog) is a working surface:
dense, calm and legible at a glance, like good HMI design (ISA-101 spirit: grey-scale base, colour
reserved for abnormal states and alarms).
- Colour carries meaning. Reserve saturated colour for alarm priorities, methane concentration and
  AI-located candidates. Never use colour as decoration on working surfaces.
- Alarm priority and state always have a non-colour signal too (icon, shape or text).
- Numbers are first-class: tabular figures, units always shown (kg/h, ppm, m/s), consistent precision.
- Tag names (K-202, PIC-101) and real engineering vocabulary everywhere; no lorem ipsum or generic
  "AI insights" copy.
- Simulated vs real data is labelled plainly (station simulated; Open-Meteo / Carbon Mapper real,
  attributed). Replay mode is labelled "Replay of a recorded AI run".
Choose typography intentionally and verify licensing. Use shadcn's semantic tokens and theme
structure rather than a second token system.

## 3D rules
- One React Three Fiber canvas. Lazy-load it; provide a static fallback image and respect
  reduced motion (no auto camera flights, plumes still visible).
- Performance budget: 60 fps at 1080p on integrated graphics. Instance repeated parts, cap pixel
  ratio, provide a quality setting. Check the budget for every new scene feature.
- Plume visuals must match the plume model's numbers (direction, extent, density). Never draw
  a plume the physics did not produce.

## States and interactions
Design initial, loading, empty, live, replay, paused, pending-approval, approved, rejected,
redrafting, escalated and error states for the main tasks.
- The agent panel streams steps as they happen; show which tool produced each number.
- The approval dialog shows the exact draft, its evidence and deadline; Approve / Edit / Reject
  (reject requires a reason). Never show "Approved" or "Issued" optimistically — that state comes
  from the graph after resume.
- Preserve the operator's edits and reason after a failure and offer a safe next action.
- Use motion to explain cause and effect (an alarm arrives, the camera moves to the candidate).
  Avoid repetitive decorative choreography on working panels.

## Accessibility and verification
Keyboard completion, visible focus, labelled controls, dialog focus management, non-colour status
signals, live regions for new alarms and agent steps, desktop-first but not broken on mobile.
Inspect desktop and narrow-screen states plus reduced-motion and 3D-fallback states in a real
browser. Code review alone is not visual verification.
Use impeccable for focused refinement, shadcn for component APIs and web-design-guidelines
for accessibility review. Keep this shared direction across all of them.
