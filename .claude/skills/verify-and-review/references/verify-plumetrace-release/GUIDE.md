---
name: verify-plumetrace-release
description: Verify PlumeTrace readiness with reproducible evidence. Use before declaring a task, phase or the public launch complete.
---

# Verify PlumeTrace Release

Read the design, the plan's acceptance criteria, the actual implementation, and environment configuration. Do not invent phases, thresholds, or infrastructure.

## Required evidence for implemented scope
Use [project-documentation](../../../project-documentation/SKILL.md) to review changed paths against adjacent contracts and focused references. Missing affected contracts prevent a completion claim.
Apply [verify-engineering-coverage](../engineering-coverage/GUIDE.md) to the whole requested release; run its release-mode ledger check and inspect referenced evidence.
Run applicable lint, type, build, unit, integration, and end-to-end checks with reproducible commands:
- Python (from `app/`): `uv run pytest app/backend app/agents -q`, `uv run ruff check`, type check.
- Frontend (from `app/frontend/`): `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, Playwright flows.

## PlumeTrace checks (as implemented)
- **Engineering:** physics tests pass against cited reference values; property tests pass; benchmark re-runs from its seed and reproduces `docs/benchmark.md`.
- **Scenarios S1–S6:** each runs end to end in live mode; triage outcome, top source, rate interval, cited rule and drafts match the committed expected answers; S4 and S5 are correctly dismissed.
- **Agents:** fake-LLM graph tests cover every branch including interrupt/resume, redraft and escalate; the LangSmith evaluation run on the scenarios dataset is recorded with its experiment link and results.
- **Replay:** every scenario's approve and reject-redraft traces load in the static build; buttons follow the recorded branch; the "Replay of a recorded AI run" label is visible.
- **Secrets:** the secret-scan test passes on `app/frontend/dist/` and `app/replay/`; no backend URL or key in the static build.
- **Labelling and attribution:** simulated/real labels, Open-Meteo and Carbon Mapper attribution, licence checks recorded in `docs/OWNER_ACTIONS.md`.
- **Performance:** measured fps at 1080p on integrated graphics recorded with the hardware used.
- **Accessibility:** keyboard flow through alarms → agent panel → approval dialog; reduced motion; 3D fallback.

Record dependency/model/configuration versions, scenario and trace versions, environment, command results, and artifact paths.
Report missing targets explicitly rather than treating absence as a pass. A local preview is not evidence the public deploy works; a synthetic benchmark is not field validation.

## Report
List Passed, Failed, Blocked, and Not Run with evidence and next action. Do not declare the release ready while mandatory checks are missing or failing.
This skill does not itself authorize deployment or publishing. Complete all authorized preparation and verification before asking the owner for the final go-ahead.
