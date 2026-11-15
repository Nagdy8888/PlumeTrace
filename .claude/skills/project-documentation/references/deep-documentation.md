# Deep implementation documentation standard

This is the user's project requirement, shared by the documentation skill and
root AGENTS.md. The goal is that another developer can explain, operate and safely
extend a feature from its documentation and source. A work log or architectural
summary alone is insufficient. Depth follows the changed responsibility, not a
fixed number of documents, headings, lines or comments.

## Start from the actual implementation

Read `docs/README.md`, the affected focused reference and relevant definitions,
callers, schemas, migrations, configuration and tests. Inspect current behavior
before writing guarantees. Retain approved scope and existing historical evidence.
Do not document a planned API, UI control or provider contract as implemented.

Use the PlumeTrace guide homes listed in the skill's SKILL.md (engineering,
simulator, agents, rules, frontend, replay) under `docs/reference/`. Extend those homes as responsibilities evolve; create another
focused guide only when it has a distinct reader/job. Keep the index and affected
setup/API/runbook links current. Do not freeze today's file inventory as a limit
on future features or duplicate every guide into every skill.

Write each reference page with the "Deep documentation page template" in SKILL.md (purpose, inline
diagram, module-by-module reference, worked example with real values, edge cases with the pinning
test, how to run, how to extend, related links). A new or changed behaviour without its section and
diagram is an unfinished task, and the reviewer fails it.

## Explain affected contracts

Cover the dimensions that actually apply to the change:

- **Purpose and ownership:** the engineering/operational problem, actors (operator,
  agents, simulator), responsible modules and their public seams; what must be true
  before callers use the interface.
- **Inputs and results:** meaningful fields, types, **units**, bounds, validity
  limits of the physics, null/missing behavior and the meaning of returned states
  (including `inconclusive`).
- **Flow and state:** important call order, graph transitions, checkpointed versus
  transient state, and when a draft is merely proposed versus approved.
- **Data and reproducibility:** seeds, scenario versions, trace versions, what the
  replay build contains, and idempotency of export.
- **Authority:** only the operator approves; model output never grants approval or
  produces engineering numbers; regulatory claims come only from the rules table.
- **Resources and external effects:** OpenAI/LangSmith calls, token cost, latency,
  timeouts and retry policy; Open-Meteo/Carbon Mapper fetches and their licences.
- **Failures and recovery:** errors visible to users/operators, uncertain outcomes,
  crash/restart/cancellation behavior, reconciliation and preservation boundaries.
- **Operation and extension:** safe configuration names/defaults/precedence, commands,
  prerequisites and the invariants a future change must preserve.
- **Proof and limits:** relevant tests and their assertions, actual invocation/result
  artifacts, simulated/local/live scope, unrun checks and unfinished capabilities.

Explain why consequential invariants exist. For example, document why the approval
node does nothing before `interrupt()` (it re-runs on resume), rather than merely
writing that approval is safe. Distinguish a plume drawn by the 3D scene from the
plume the model computed, and a simulated reading from real public data.

Do not invent details to fill these dimensions. A dimension that does not apply
to a small pure helper does not need a paragraph or a fabricated dependency.

For relationships, architecture and nontrivial flow/state explanations, follow
[the visual standard](visual-documentation.md) and maintain source-backed Mermaid
views alongside these contracts. Professional documentation requires readable,
visually reviewed output rather than decorative or merely parse-valid diagrams.

## Adjacent function and class contracts

Every authored Python module, function and class, including private and nested
definitions, needs a **Google-style docstring** as defined in
[code-comments.md](code-comments.md). Named TypeScript functions, classes, hooks,
components and nontrivial callbacks need adjacent TSDoc; small callbacks may be
explained at their containing expression when clearer. Generated declarations and unmodified
vendor source remain labeled; document owned wrappers and behavioral changes.

For nontrivial definitions, explain purpose, meaningful input/result semantics,
caller obligations, state/units, side effects, authorization/invariants and error
behavior as relevant. State who owns commit, resource cleanup or retry when that
matters. A class contract explains the meaning/lifecycle of its state, not just
that it is a class. Avoid restating signatures or inventing guarantees. Keep simple
contracts concise and place cross-module reasoning in the focused reference.

## Finish each coherent step

Update affected inline/reference/setup/runbook documentation before starting the
next step. Append changed paths, purpose, actual verification and remaining gaps
to `docs/WORK_LOG.md`; that same entry covers documentation changes. Updating the
log does not require another recursive entry. Put owner-dependent prerequisites
(accounts, keys, licence checks) in `docs/OWNER_ACTIONS.md`, with evidence in `docs/evidence/`.

Review new, modified, renamed and removed paths against those documentation homes.
Check local links/anchors, machine-readable examples and safe command examples;
run applicable architecture/inline checks and feature verification when behavior
changed. Presence checks and navigation coverage are not proof of explanation
quality: manually compare important claims with source and observed results.

For documentation-only work, do not claim previous integration/browser/provider
results ran again. Static checks and, where useful, an executable-code comparison
can establish that comment/docstring edits preserved behavior. Do not perform paid
calls, account changes or deployment solely to validate documentation.

Keep credentials, populated environment files and raw LangSmith traces
out of prose/evidence. Installing a skill or adding this rule does not establish
compliance. Report unresolved documentation gaps honestly; do not call an affected
implementation step complete while its meaningful contracts remain undocumented.
