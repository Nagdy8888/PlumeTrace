---
name: verify-and-review
description: Decide whether PlumeTrace work is correct, documented and done. Use for code review of a diff or branch, before calling a task, phase or release complete, before ticking a plan checkbox, and for the engineering coverage ledger.
---

# Verify and Review (PlumeTrace)

One entry point for "is this right, and is it done?". Three guides as references:

- [review-plumetrace-code](references/review-plumetrace-code/GUIDE.md): code review against the design and PlumeTrace invariants.
- [verify-plumetrace-release](references/verify-plumetrace-release/GUIDE.md): completion/readiness evidence.
- [engineering-coverage](references/engineering-coverage/GUIDE.md): the 42-concept ledger and its validator
  (`references/engineering-coverage/scripts/check_coverage.py`).

## Pick the job

| Job | Do this |
|---|---|
| Review a diff, branch or working tree | Follow review-plumetrace-code. Report confirmed defects first, with scenario, consequence, file:line and the smallest fix. |
| Claim a task, phase or release is done | Follow verify-plumetrace-release. Every check is Passed, Failed, Blocked or Not Run, with evidence paths. |
| Tick a plan checkbox | Link an evidence file (test output, screenshot, benchmark report) on the same line; its label must match the item. |
| Phase end or before going public | Update `docs/engineering/coverage.json`; run `check_coverage.py docs/engineering/coverage.json` (add `--release` before the public launch). |

## Hard rules

- Evidence labels are only `local`, `synthetic` (simulated station / benchmark), `replay` (static build), `live-api` (real OpenAI/LangSmith calls) and `public-data` (Open-Meteo, Carbon Mapper).
- Benchmark scoring rules and scenario expected answers are committed before the run they score; later changes are labelled `post-hoc`.
- "All checks pass" means one complete run of backend tests + lint + type-check and frontend lint + typecheck + tests + build on the final tree.
- A skill, a passing presence check, or a mocked test is not proof that behavior works.
- Review does not commit, publish or change code unless the owner asked for that.
