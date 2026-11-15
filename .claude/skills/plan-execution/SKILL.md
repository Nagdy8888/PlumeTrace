---
name: plan-execution
description: How the implementing agent executes PlumeTrace plans without deviating - read order, one task at a time, exact interfaces, test-first, when to stop and ask, what never to change, verification and the STATUS.md update. Load before starting or resuming any task from docs/superpowers/plans/.
---

# Executing PlumeTrace plans (rules for the implementing agent)

You implement a plan written by someone else. The plan holds decisions you cannot see the
reasons for: file names, signatures, constants, coefficient values, thresholds. **Your job is to
implement exactly those decisions, test-first, and to stop when the plan does not decide
something that matters.** A creative improvement that changes an interface breaks later tasks.

## Before each session
1. Read `CLAUDE.md`, `docs/superpowers/plans/STATUS.md`, the roadmap, the current phase's
   `README.md` (pinned versions, global constraints, review focus) and then **only** the task
   file named as "Next task" (`docs/superpowers/plans/phase-N/task-NN-*.md`).
2. Read the design sections the task names. Load the skills the task lists.
3. Work on exactly one task file. Task files are self-contained: exact file contents are copied
   verbatim, full test code is copied verbatim, interfaces are implemented with exactly the names
   and types given, and pinned versions are used as listed.

## While doing a task
1. **Follow the steps in order.** Write the failing test first, run it and see it fail for the
   expected reason, then implement, then run it green.
2. **Use the exact names in the Interfaces block** (module paths, function and class names,
   parameter names and order, return types, constant names and values). Do not rename, merge,
   split differently, add parameters, or change defaults.
3. **Copy specified values exactly** (coefficients, thresholds, ids, coordinates, file paths).
   If a value looks wrong, do not "fix" it: stop and report (see below).
4. **Check library docs** (Context7) for every third-party API you call; note the version.
5. **Stay in scope.** Create only the files the task lists, plus their tests and the docs the
   task names. No extra features, refactors, dependencies, config or "nice to have" changes.
   Something worth doing outside the task goes into `STATUS.md` → "Blockers / questions".
6. **Never weaken a check to pass it:** do not edit, skip, xfail or loosen a test written in an
   earlier step or task; do not add `# noqa`, `type: ignore`, `slop-ok`, size exceptions, lint
   ignores or `--no-verify` unless the plan step says so. Fix the code instead.
7. **No god files:** respect the size limits; split by responsibility as `repo-structure` says.
8. **Docs move with the code:** Google docstrings, the `docs/reference/*.md` page (the named one,
   plus any page whose behaviour you changed) in the deep-documentation structure with its inline
   Mermaid diagram, the `docs/README.md` row for a new page, and the `docs/WORK_LOG.md` entry — in
   the same task. Load `project-documentation` for the template and the checklist.

## Stop and ask (write it in STATUS.md, then end your turn with the question)
Stop instead of guessing when:
- a step is ambiguous in a way that changes behaviour, an interface or a stored value;
- a specified value contradicts the spec, a cited source, or another task;
- a test the plan specifies cannot pass with the specified implementation;
- a library API in the plan no longer exists in the pinned version;
- the task needs a file, dependency, secret, account or tool the plan does not list;
- anything would need a secret only the owner has (an API key), the spend cap, global git config,
  the database by hand, or a deploy. (`.env` entries themselves you add and update with
  `python -I .claude/skills/security-checks/scripts/env_set.py` — see the Never list.)
Report: what you tried, the exact error/output, the options you see, and which you recommend.

## Finishing a task (all must be true before you say "done")
1. The task's tests pass (every test layer the `testing-strategy` skill requires for this kind of
   change), and the local checks pass: `python scripts/ci_local.py` (from Phase 1 Task 8 on; before
   that, the individual commands of the task). Before a phase gate: `python scripts/ci_local.py --full`
   with local Supabase running. There is **no GitHub Actions CI** — the local run is the proof.
2. `python -I .claude/skills/repo-structure/scripts/check_structure.py .` → `structure OK`
3. `python -I .claude/skills/security-checks/scripts/check_env.py .` → `env OK`
4. `python -I .claude/skills/security-checks/scripts/secret_scan.py .` → `no secrets found`
5. UI tasks: `python -I .claude/skills/frontend-design/scripts/check_slop.py app/frontend/src`
   → `no slop found`, plus the screenshot critique.
6. Docs updated per CLAUDE.md rule 17: docstrings/TSDoc; the reference page has purpose, diagram,
   module-by-module explanation, worked example with real values, edge cases with their pinning
   tests, how to run and extend; every Mermaid block in a changed page parses (local parse, nothing
   uploaded); `docs/README.md` row added for a new page; `docs/WORK_LOG.md` entry added.
7. Commit exactly the task's files (read `git status` and the staged list first); the pre-commit
   hook (`scripts/install_git_hooks.py`) runs the quick checks and must pass — never `--no-verify`; message
   `<type>(<area>): <what>` ending with the attribution lines your harness provides.
8. Update `STATUS.md`: last completed task, next task, task-log row with evidence paths.
Paste the real command output in your report. "Should pass" is not done.

## Never
- Never print, read aloud, copy or commit `.env` values; never pass keys on a command line.
- Never open `.env` with Read/Edit/Write, `cat`, `type`, `Get-Content` or `grep`. Change it only with
  `python -I .claude/skills/security-checks/scripts/env_set.py` (`names`, `get`, `set`, `add`, `generate`); it keeps `.env.example`
  in sync and never prints a secret. Never change `PLUMETRACE_SPEND_CAP_USD` (owner-only).
- Never push, deploy, publish, or change repository settings unless the owner asks in chat.
- Never deploy at all: no Vercel project, no `vercel` command, no live URL — deployment is a later
  phase that is not planned yet (owner decision 2026-11-13).
- Never create `.github/` or any GitHub Actions workflow (owner decision 2026-11-13, billing).
- Never make a paid OpenAI call outside a step the plan marks as paid **and** the owner approved in
  chat for that step; never raise `PLUMETRACE_SPEND_CAP_USD`; never bypass `BudgetedLLM` or the ledger.
- Never edit the design doc or a plan file (except checking boxes `- [x]` in the current task file).
- Never change a pinned version, a test written in a task file, or a value given in a task file.
- Never start the next phase; phase plans 3+ are written by the planner at the owner's gate.

## Orchestrator mode (running a phase with subagents)
Use it when the owner says "run the phase with subagents". The main session becomes the
**orchestrator**; it writes no code itself. Two project agents do the work:
`.claude/agents/plumetrace-implementer.md` (one task, Sonnet, no commits, cannot spawn agents) and
`.claude/agents/plumetrace-reviewer.md` (read-only, Sonnet).

**Who owns what (this is what prevents overlap):**
| Who | May change | Never |
|---|---|---|
| Orchestrator | `STATUS.md`, `git add`/`git commit`, messages to the owner, relaying a paid-step yes | code, tests, docs, task files |
| Implementer (one at a time) | the current task's files, their tests, named docs, one `WORK_LOG.md` entry, its own task checkboxes | `STATUS.md`, git commits, other tasks, spawning agents |
| Reviewer | nothing (reads, reruns checks) | any write, `db reset`, servers left running |

**Overlap rules:**
1. **One orchestrator at a time.** `STATUS.md` has an `In progress` line. At start: if it is not
   `none`, stop and tell the owner (another session is running, or one crashed — the owner decides).
   Otherwise set it to `<task path> — orchestrator started <YYYY-MM-DD>` before dispatching anything.
2. **One implementer at a time, in task order.** Never dispatch two implementers together, never
   in git worktrees. Tasks build on each other and share one git index, `uv.lock`,
   `package-lock.json`, `WORK_LOG.md`, `docs/reference/*`, one local Supabase (`db reset` wipes
   it) and fixed ports (8000, 5173, 4173, 54321–54323).
3. **Parallel work only if it writes nothing and starts nothing:** a docs lookup, reading files.
   The reviewer runs after the implementer, not alongside it.
4. **Review before commit, commit before the next task.** The tree is clean (`git status` empty)
   before each dispatch; a dirty tree at start → stop and ask the owner.
5. The owner does not edit the repo or run a second session while the orchestrator runs.

**The loop (one task per pass):**
1. Read `STATUS.md` → the Next task path. Set `In progress` (rule 1). `git status` must be clean.
2. Dispatch `plumetrace-implementer` and wait for its report. Prompt:
   `Implement docs/superpowers/plans/phase-N/task-NN-*.md. Follow your agent instructions and return the report.`
   The implementer's DONE includes the docs deliverable: reference page (deep structure) with its
   Mermaid diagram updated and parsed, README index row, work-log entry (see its agent file).
3. Act on `RESULT`:
   - `DONE` → step 4.
   - `BLOCKED` / `OWNER_STEP` → write the question to `STATUS.md` → Blockers, set `In progress` to
     `<task> — waiting for owner`, ask the owner, end your turn. When the owner answers, send the
     answer to the **same** implementer (SendMessage to its id), then continue at step 3.
   - `PAID_STEP` → tell the owner: runs, estimated cost, spend so far (`plumetrace.llm_calls`), cap
     ($4.00); wait for an explicit yes in chat; then message the implementer
     `The owner approved <step> in chat on <date>.` A no → treat as BLOCKED.
4. Dispatch `plumetrace-reviewer` with the task path and the implementer's FILES list. The reviewer
   FAILs a missing or stale deep-doc section or diagram for a changed behaviour, a diagram that
   disagrees with the code or does not parse, or a "validated / accurate / production ready" claim.
   - `FAIL` → send the FINDINGS to the same implementer, wait for its new report, review again.
     After **2** failed fix rounds: stop, put the findings in Blockers, ask the owner.
   - `PASS` → step 5.
5. Update `STATUS.md` (last completed, next task, task-log row with the check output, `In progress: none`),
   stage exactly FILES + `STATUS.md` (compare with `git status`), commit with the task's commit message
   (the pre-commit hook runs the quick checks; never `--no-verify`). Hook fails → send the output to the
   implementer as a finding (step 4 rules).
6. The task was the phase's last, or the next step is a gate (Gate 6a, phase gate) →
   `python scripts/ci_local.py --full`, `verify-and-review`, `superpowers:requesting-code-review`;
   report to the owner and **stop**. Otherwise go to step 1 with the next task.

Start a fresh orchestrator session per phase (keeps context small). Owner's start prompt
(Claude Code on Sonnet: `claude --model sonnet` or `/model sonnet`):
`Load plan-execution. Run the current phase in orchestrator mode until the phase gate.`
