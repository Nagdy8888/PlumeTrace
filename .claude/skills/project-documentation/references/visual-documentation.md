# Professional Mermaid documentation

Read the root `CLAUDE.md`, the affected guide and its actual code before drawing.
Use the bundled mermaid-diagrams reference for syntax/type guidance. Documentation
owns the factual claims and completion evidence; imported examples do not override
the actual implementation status.

Use focused flow views for branching (the agent graph), sequences for participant
order (operator ↔ frontend ↔ API ↔ graph ↔ OpenAI), and state views for lifecycle
behavior (draft → pending approval → approved / redraft / escalated).
Show the human-approval boundary and the live-versus-replay boundary where consequential.
Do not draw planned integrations as live or equate drafted with approved.

Keep canonical `.mmd` sources under `docs/diagrams/` with generated SVG previews next
to them. Link through the documentation index. Explain each view's purpose/scope near
its embed and retain detailed prose/inline contracts. Use descriptive accessible titles,
short labels, readable contrast in light and dark themes, consistent styling and
explicit source links. Split crowded views instead of shrinking them to unreadable text.

Render locally with a pinned `@mermaid-js/mermaid-cli` dev dependency (add the render
script to `app/frontend/package.json` or `scripts/` when the first diagram is created).
Inspect the actual SVG for clipped labels, stray nodes, misleading edges and
readability. Syntax checks cannot establish correctness. Record results/gaps in
`docs/WORK_LOG.md`. Ordinary small prose changes need no new diagram.

Do not upload project diagrams to public renderers, install global tools or run
paid model calls for diagram validation. Keep secrets out of source/assets.
