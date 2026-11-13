# No AI slop (PlumeTrace frontend)

"AI slop" is UI that looks generated: generic SaaS gradients, glowing purple "AI" accents, glass
panels, emoji, identical rounded cards, filler copy and fake numbers. Engineers spot it in a
second and stop trusting the product. PlumeTrace must look like it was designed by people who
build control-room software. The project profile is `.ux-profile.md` at the repo root.

## Hard bans (enforced by `scripts/check_slop.py` where a pattern can be detected)
1. Gradients on buttons, cards, panels or text (`bg-gradient-*`, `bg-clip-text` + `text-transparent`,
   multi-stop `linear-gradient`, `conic-gradient`, `radial-gradient` blobs). Allowed only for data
   colour ramps (heat-map legend) and the 3D sky.
2. Glassmorphism: `backdrop-filter` / `backdrop-blur-*` on product UI.
3. Neon glow shadows (`shadow-[0_0_…]`, coloured `drop-shadow` glows) outside the 3D candidate highlight.
4. Emoji and "AI sparkle" iconography (✨ 🤖 🚀 🔥 💡, Sparkles/Wand/Bot icons) anywhere in the UI.
5. Marketing filler copy (see the list in `.ux-profile.md`) and lorem ipsum / placeholder names.
6. Purple/violet/fuchsia as accent or decoration (`purple-*`, `violet-*`, `fuchsia-*` utilities).
7. Decorative infinite animations (`animate-pulse`/`animate-bounce`/`animate-ping`) except one
   approved live-alarm indicator component.
8. Hard-coded numbers in UI components. Every value shown comes from the data source (live or
   replay) — there is no "demo number" in a `.tsx` file.

## Required instead
- **Surfaces:** 3–4 neutral grey levels separated by 1px borders and spacing, not shadows. Radius
  small and consistent (e.g. 4–6px panels, 2–4px controls); no pill containers on static text.
- **Colour:** semantic tokens only (`--alarm-high`, `--alarm-med`, `--alarm-low`, `--ok`,
  `--accent`, `--ch4-ramp-*`). ISA-101 spirit: grey base, colour = abnormal or actionable.
- **Typography:** a deliberate pairing chosen for this product (licensed/free), tabular numbers for
  all values, units always shown in a quieter weight, tags (K-202, AT-104) in the monospace face.
- **Data density done right:** aligned columns, consistent precision, timestamps in one format,
  real engineering vocabulary.
- **Icons:** one icon set, monochrome, only where they add meaning (alarm priority, state,
  navigation). No icon-in-every-heading.
- **Empty / loading / error states:** plain sentence + next action; skeletons matched to layout.
- **AI presence without slop:** the agent panel shows *what the agent did* (step, tool, source,
  result, timing) in plain typography. "AI" is shown by the work, not by sparkles or gradients.
- **Motion:** only for cause and effect; respects reduced motion.

## Review gate (every UI task)
1. `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src` prints `no slop found`.
2. Screenshot the changed screen (Playwright) at 1440×900 and run a critique with the `impeccable`
   skill (critique/audit) or `design-skills:design-critique` against `.ux-profile.md`; fix findings.
3. The "squint test": at a glance, does the screen look like a control-room product or like a
   SaaS template? If template — redo, don't decorate.
4. Record the screenshot in `docs/evidence/` and the critique result in `docs/WORK_LOG.md`.
