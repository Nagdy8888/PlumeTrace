# Phase 1 · Task 1 — Repository bootstrap

**Read first:** `CLAUDE.md`, `phase-1/README.md`. **Skills:** `plan-execution`, `project-documentation`, `contribution-workflow`.

**Goal:** turn the folder into a git repository with a licence, line-ending rules and the
documentation homes every later task writes to. No code yet.

## Files
| Action | Path |
|---|---|
| Create | `LICENSE`, `.gitattributes`, `README.md` |
| Create | `docs/README.md`, `docs/WORK_LOG.md`, `docs/OWNER_ACTIONS.md`, `docs/LOCAL_DEVELOPMENT.md`, `docs/reference/STRUCTURE.md` |
| Do NOT change | `.gitignore`, `.env`, `.env.example`, `CLAUDE.md`, `.ux-profile.md`, anything in `.claude/` or `skills/` |

## Steps

- [x] **1. Check git identity (do not change it).** Run `git config user.name` and `git config user.email`. If either prints nothing, STOP and ask the owner to set them. Never run `git config --global`.

- [x] **2. Initialise.** From the repo root: `git init -b main`. Then verify ignores:
  - `git check-ignore .env` → prints `.env`
  - `git check-ignore build/x.glb` → prints `build/x.glb`
  - `git check-ignore .env.example` → prints nothing (exit code 1)

- [x] **3. Write `.gitattributes`** (exact content):
```gitattributes
# Normalise line endings so generated files are identical on Windows and Linux.
* text=auto eol=lf
*.png binary
*.jpg binary
*.glb binary
*.webp binary
*.hdr binary
*.exr binary
*.pdf binary
```

- [x] **4. Write `LICENSE`**: the standard MIT License text (as published at https://opensource.org/license/mit), first line `MIT License`, copyright line `Copyright (c) 2026 PlumeTrace contributors`.

- [x] **5. Write `README.md`** (exact content):
```markdown
# PlumeTrace

PlumeTrace watches a (simulated) natural gas compressor station in an interactive 3D view. When
methane shows up where it should not, a team of AI agents works out whether it is a real leak,
finds the leaking component, estimates how much is escaping (kg/h), checks what the operator's
leak policy requires, and drafts the repair work order and emissions report. A human operator
approves every action.

Status: in development.

- Design: [docs/superpowers/specs/2026-11-12-plumetrace-design.md](docs/superpowers/specs/2026-11-12-plumetrace-design.md)
- Local development: [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)
- Documentation index: [docs/README.md](docs/README.md)

The station "KS-07" and all of its data are fictional and simulated.
```

- [x] **6. Write `docs/README.md`** (exact content; every later task adds its new docs here):
```markdown
# Documentation index

| Document | What it covers |
|---|---|
| [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) | Prerequisites, pinned versions, how to run everything |
| [WORK_LOG.md](WORK_LOG.md) | One entry per completed plan task |
| [OWNER_ACTIONS.md](OWNER_ACTIONS.md) | Things only the owner can do |
| [reference/STRUCTURE.md](reference/STRUCTURE.md) | Repository layout and dependency rules |
| [superpowers/specs/2026-11-12-plumetrace-design.md](superpowers/specs/2026-11-12-plumetrace-design.md) | The approved design |
| [superpowers/plans/2026-11-12-plumetrace-roadmap.md](superpowers/plans/2026-11-12-plumetrace-roadmap.md) | Roadmap and phase plans |
```

- [x] **7. Write `docs/WORK_LOG.md`** (exact content, then add this task's row at the end of the task):
```markdown
# Work log

| Date | Plan task | Changed paths | Purpose | Verification | Gaps |
|---|---|---|---|---|---|
```

- [x] **8. Write `docs/OWNER_ACTIONS.md`** (exact content):
```markdown
# Owner actions

- [x] Install Docker Desktop.
- [x] Add `SUPABASE_DB_URL` and `LANGSMITH_PROJECT` to the root `.env`.
- [ ] Gate 1: review `app/backend/plumetrace/facility/data/ks07.yaml` (layout, coordinates,
      fictional location), the gas composition, `component_counts.yaml` and the emission sources.
- [ ] Push the repository to GitHub when you choose (GitHub Actions stay **off**: billing; all checks run locally with `python scripts/ci_local.py` and the pre-commit hook from Phase 1 Task 8).
- [ ] Install Blender (LTS) before Phase 4.
- [ ] Deployment of the replay site: a later phase, not planned yet (no Vercel project now).
```

- [x] **9. Write `docs/LOCAL_DEVELOPMENT.md`** with these headings (later tasks fill them): `# Local development`, `## Prerequisites` (Python 3.12, uv 0.10.3, Node ≥ 22.13, Docker Desktop, git), `## Pinned versions` (copy the table from `phase-1/README.md`), `## Configuration`, `## Python`, `## Database`, `## Frontend`, `## Checks`. Under `## Checks` put the three repo checks from step 11.

- [x] **10. Write `docs/reference/STRUCTURE.md`**: a heading, one sentence "The authoritative rules are in `.claude/skills/repo-structure/SKILL.md`; this page mirrors them for human readers.", then copy the "The tree", "Dependency direction" and "No god files → Hard limits" sections from that skill verbatim.

- [x] **11. Run the repo checks** (from the repo root) and paste the output:
```bash
python -I .claude/skills/repo-structure/scripts/check_structure.py .
python -I .claude/skills/security-checks/scripts/check_env.py .
python -I .claude/skills/security-checks/scripts/secret_scan.py .
```
Expected: `structure OK`, `env OK`, `no secrets found`.

- [x] **12. Work log + status.** Add a `WORK_LOG.md` row; update `STATUS.md` (last = 1.1, next = 1.2).

- [x] **13. Commit.** `git status` must NOT list `.env`. Then:
```bash
git add -A
git diff --cached --name-only
git commit -m "chore(repo): bootstrap repository, licence and docs skeleton"
```
(Append the attribution lines your harness provides to the message.)

## Done when
`git log` shows one commit; the three checks pass; `.env` is untracked.
