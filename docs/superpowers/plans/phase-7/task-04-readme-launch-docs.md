# Phase 7 · Task 4 — README with results, architecture diagram, launch post drafts

**Skills:** `plan-execution`, `project-documentation` (+ `references/visual-documentation.md`), `writing-guidelines`, `social-media-skills:linkedin-post-writer` (drafts only), `anthropic-skills:humanizer` (final pass on the posts), `contribution-workflow`.

## Owner questions first (STOP until answered)
1. Will the repository be public on GitHub? If yes: the exact repository URL (it fills `about.json.repository_url` and the README links). The executor does **not** create the repository or push.
2. The author line for the README (`Built by <name>` with an optional LinkedIn URL) — the owner writes it; never infer it.

## README (`README.md`, replaces the Phase 1 stub; sections in this order)
1. Title + one sentence: `PlumeTrace — AI methane leak detection for a simulated gas compressor station.`
2. Labels line: `Station, sensors and leaks are simulated. Weather is real (Open-Meteo, CC BY 4.0). The public site replays recorded agent runs.`
3. Screenshot (`docs/evidence/…` hero image, 1600 px wide max) and links: demo video (no live URL — deployment is a later phase that is not planned yet; do not add a placeholder) (`app/frontend/public/media/plumetrace-demo.mp4`).
4. `The problem` (4–6 sentences, plain; why leaks matter and why they are hard to find from a few sensors — no statistics unless cited with a link).
5. `What it does` — the pipeline in 6 bullets (detect, triage, locate & quantify, rules, drafts, human approval).
6. `Results` — generated block between `<!-- results:start -->` / `<!-- results:end -->` by `scripts/export_readme_results.py` from `docs/evidence/*.json`: the inversion benchmark (model mismatch, top-source accuracy, rate-in-interval, inconclusive rate) and the agent evaluation (AI vs rule-based baseline triage accuracy per family, provenance pass rate, cost and latency per run). Each table states its case count and date.
7. `Why an LLM at all` — design §6 "What the AI decides", 4 bullets, and the one-line provenance rule.
8. `Architecture` — a Mermaid flowchart (frontend ↔ FastAPI ↔ LangGraph ↔ Supabase ↔ LangSmith; replay path: recorded traces → static replay build) + 6 lines.
9. `Run it locally` — prerequisites with pinned versions (Python 3.12 + uv, Node 22.13+, Docker, Supabase CLI 3.1.0 via npx, Blender 4.5.16 only for regenerating the model), the commands from `docs/LOCAL_DEVELOPMENT.md`, the single root `.env` (names from `.env.example`, no values).
10. `Honest limits` — the model-mismatch result, MVP scope (S1/S4/S5), the simplifications (OGMP badge, VRU always online, no OGI data), the regulation framing.
11. `Credits and licences` — MIT for code; Open-Meteo CC BY 4.0; Poly Haven CC0; emission-factor and GWP sources; IBM Plex (OFL); every source from ASSETS.md and RULES.md.
12. Author line (owner's text).
`scripts/export_readme_results.py`: deterministic, LF; test `app/backend/tests/test_export_readme_results.py` (fixture evidence JSON → exact Markdown; missing file → `FileNotFoundError`).

## Launch drafts (`docs/launch/linkedin-posts.md`; written for LinkedIn readers — engineers and hiring managers in oil & gas and AI)
Five drafts following the design's series: (1) the problem, (2) the 3D twin, (3) the physics + benchmark (with the honest mismatch result), (4) the agents and why a human approves, (5) the demo video + link. Each draft: ≤ 1300 characters, a first line that states something concrete (no hook clichés), numbers only from the evidence files (cite the file in an HTML comment under each draft), no emoji, none of the banned words in `.ux-profile.md`, 3 hashtags max at the end. Run `linkedin-post-writer` for structure and `humanizer` for the final pass. The owner posts; the executor never posts or sends anything.

## Steps
- [ ] Owner questions; record the answers in STATUS.md.
- [ ] `export_readme_results.py` + test → FAIL → implement → run; write the README; set `repository_url` in the about export (`export_about.py --repository-url <url>` flag, add it) and regenerate `about.json`.
- [ ] Check every README number against the evidence files (list each number and its source in the work log).
- [ ] Post drafts; show them to the owner.
- [ ] Repo checks; secret scan (README and drafts).
- [ ] **Docs.** `docs/README.md` index links the launch folder. Work-log; `STATUS.md` (last 7.4, next 7.5).
- [ ] **Commit** `docs: add README with results and launch drafts`.
