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

**Project standard: inline.** Embed each diagram as a fenced `mermaid` block in the
`docs/reference/*.md` page it explains (GitHub renders it natively). Keep a `.mmd` source under
`docs/diagrams/` with a generated SVG next to it only for a diagram reused in several pages, the
README or the video; link it through the documentation index. Put a one-line caption under every
diagram and explain its purpose/scope in the surrounding prose; retain the detailed prose/inline
contracts. Use short labels and consistent styling; keep to 6 to 15 nodes and split crowded views
instead of shrinking them to unreadable text. Choose the type by the question: flowchart (process,
data flow), sequence (interactions over time), ER (tables), class (types), state (lifecycles),
C4-style container flowchart (architecture).

Validate every block with the real Mermaid parser in a throwaway folder outside the repo (`npm i
mermaid jsdom` in the scratchpad, parse each extracted block); see the Diagram standard in
SKILL.md. Where practical also inspect a render for clipped labels, stray nodes and misleading edges.
Syntax checks cannot establish correctness: compare the diagram with the code. Record results/gaps
in `docs/WORK_LOG.md`. Ordinary small prose changes need no new diagram; a change to behaviour,
data flow or structure always updates the affected one.

Do not upload project diagrams to public renderers, install global tools, add a repository
dependency or run paid model calls for diagram validation. Keep secrets out of source/assets.
