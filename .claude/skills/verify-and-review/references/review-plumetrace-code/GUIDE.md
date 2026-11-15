---
name: review-plumetrace-code
description: Review PlumeTrace changes against the approved design and project invariants. Use for branches, working-tree changes, or focused pre-release code review.
---

# Review PlumeTrace Code

Establish the actual review scope from the request and repository state. Include staged, unstaged, and new files for working-tree reviews; for branch reviews, use the appropriate merge base and commits.
Read the design (`docs/superpowers/specs/2026-11-12-plumetrace-design.md`), the root `CLAUDE.md`, the plan task being reviewed and its acceptance criteria. If the spec is absent, report that limitation and review the observable contract.
Apply [project-documentation](../../../project-documentation/SKILL.md) to affected contracts and focused references; report material documentation gaps before calling the implementation complete.
Apply [verify-engineering-coverage](../engineering-coverage/GUIDE.md) to substantive review scope.
For frontend changes, use frontend-structure for code ownership and frontend-design's control-room reference for UI. Contribution mechanics belong to contribution-workflow.

## Prioritise concrete defects in
- **Physics correctness:** wrong equations, unit mix-ups (kg/h vs kg/s, ppm vs kg/m³), wrong dispersion coefficients, sign or direction errors with wind, missing ground reflection, uncited constants, tolerances that hide errors.
- **Benchmark honesty:** the same model used to generate and invert, leaks always on the candidate list, numbers edited by hand, seeds missing.
- **Numbers-from-tools:** any number in an agent draft, UI or report that did not come from a tool result in the same run.
- **LangGraph:** side effects or LLM calls before `interrupt()` in the approval node, missing checkpointer or `thread_id`, redraft limit enforced in a prompt instead of code, untested branches, unvalidated resume payloads.
- **Compliance claims:** regulatory text not from the rules table, EU articles presented as binding the non-EU site.
- **Secrets:** keys in code, frontend bundle, traces, logs, tests or command lines.
- **Honest labelling:** simulated data shown as real, replay shown as live.
- **3D:** plume visuals that disagree with the plume model, per-frame React state updates, missing instancing, budget regressions.

## Documentation and diagrams (FAIL criteria)
A change fails review when any of these holds for a changed behaviour, data flow or structure:
- the matching `docs/reference/*.md` section is missing or stale, or lacks the deep-documentation parts that apply (purpose, diagram, module-by-module explanation, worked example with real values, edge cases with the pinning test, how to run and extend, links);
- its Mermaid diagram is missing, disagrees with the code (compare names and edges with the source), draws a planned part as built, exceeds about 15 nodes, has no caption, or does not parse (parse every block locally in a scratch folder; never upload a project diagram);
- a new reference page has no `docs/README.md` index row, or a relative link does not resolve;
- the page claims "validated", "accurate" or "production ready", states a number with no evidence, shows an inversion rate outside rule R1 to R4, or presents simulated data as real;
- the `docs/WORK_LOG.md` entry or the docstrings/TSDoc are missing.

Trace a proposed finding through callers, state, and tests. Give the triggering scenario, consequence, precise source location, and smallest effective correction.
Separate confirmed defects from questions and optional improvements. Do not claim an audit or integration validation from source inspection alone.
Use independent reviewers only when delegation is authorized and adds value.
Do not commit, publish a review, or change code as a review side effect unless the owner requested that action.
