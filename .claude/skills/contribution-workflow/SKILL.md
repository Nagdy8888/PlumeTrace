---
name: contribution-workflow
description: Prepare scoped commits, branches, pull requests, and release descriptions using the PlumeTrace repository's actual workflow. Use when the owner requests Git or GitHub contribution work.
license: Proprietary - original supplied notices retained in the source archive.
---

# Contribution Workflow (PlumeTrace)

Inspect git status, remotes, branch conventions, CI, hooks, templates, and the owner's authorization before acting. An uninitialized folder does not establish a remote repository or issue tracker (at the time this skill was adapted, the repo was not yet a git repository).

Keep changes reviewable and explain the problem, resulting behavior, validation, and material limitations. Prefer existing conventions; Conventional Commits are a reasonable new convention when needed, not a reason to rewrite history.
Use actual issue references when available. Do not invent ticket IDs, mandatory dev branches, a fixed diff-size ceiling, or one commit per task.
Select a branch strategy suited to this repository. Do not introduce main/dev promotion flows, CODEOWNERS, branch protection, or required reviewers as an installation side effect.

## PlumeTrace specifics
- Never stage or commit `.env`, `app/supabase/.temp/`, database dumps, `node_modules/`, or replay traces that
  were not produced by the replay exporter. Run `git status` and read the staged file list before
  every commit; abort if a secret-looking file is staged.
- Commit messages and PR bodies end with the attribution lines the harness provides.
- Phase-sized PRs follow the implementation plan's phases; each PR lists the plan tasks it closes.

## Boundaries with other skills
- [review-plumetrace-code](../verify-and-review/references/review-plumetrace-code/GUIDE.md) owns substantive code review.
- [verify-engineering-coverage](../verify-and-review/references/engineering-coverage/GUIDE.md) owns engineering coverage and evidence.
- [verify-plumetrace-release](../verify-and-review/references/verify-plumetrace-release/GUIDE.md) owns release verification.
- [project-documentation](../project-documentation/SKILL.md) owns decisions, guides, and release-note content.

Use [PR description prompts](assets/pr-description-prompts.md) when no repository template exists. Report local checks (`python scripts/ci_local.py`; PlumeTrace has no external CI — GitHub Actions are off by owner decision 2026-11-13), and pushed/unpushed state separately. The full local run (`ci_local.py --full`) is the proof of checks.

Parallel sessions: before branching, run `git status`, `git branch -vv` and `git worktree list`; one session per checkout; never switch branches under another session's uncommitted work.

Commit, push, create/publish a PR, change repository settings, or merge only when authorized by the actual task. Preserve the owner's edits, use repository-local configuration when requested, and never change global git settings from this skill.
