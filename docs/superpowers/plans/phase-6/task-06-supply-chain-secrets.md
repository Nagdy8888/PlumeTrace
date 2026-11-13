# Phase 6 · Task 6 — Secrets in history, dependency audit, licences, lockfile checks

**Skills:** `plan-execution`, `security-checks` (§A, §F, §G), `superpowers:test-driven-development`, `project-documentation`.

## Fixed decisions
- `secret_scan.py` gains a **stdin mode** (`-`): it scans text piped in (for `git log -p --all` and `git diff --cached`). Same patterns and `.env`-value matching as the file mode; findings print `<stdin>:<line>: <rule>` and never the matched value.
- New `ci_local.py` stages (Phase 1 Task 8 runner):
  - `history-secrets` (full only): `git log -p --all` piped into the scanner.
  - `audit` (full only): `uv run pip-audit` (from `app/`) and `npm audit --omit=dev --audit-level=high` (from `app/frontend/`). High or critical → stage fails; the executor reports and never upgrades pins on its own.
  - `lockfiles` (quick and full): `uv lock --check` (from `app/`) and `npm ci --dry-run --ignore-scripts` (from `app/frontend/`); both must succeed without changing a file.
  - `licences` (full only): `scripts/list_licences.py` writes `docs/reference/LICENCES.md`; a runtime dependency whose licence is unknown or in the deny list fails the stage.
- Deny list for **runtime** dependencies: any licence string containing `AGPL`, `GPL-3`, `SSPL`, `BUSL`, `Commons Clause`. LGPL and dev-only tools are reported, not failed. An unknown licence → fails with the package name; the owner decides (accepted ones go into `LICENCE_ACCEPTED` in the script with the owner's date).
- `npm ci` and `npm install` never run lifecycle scripts of new packages unnoticed: `app/frontend/.npmrc` gets `ignore-scripts=false` **unchanged** (esbuild needs its script); instead the `lockfiles` stage prints every package in the lockfile with `"hasInstallScript": true` and the stage fails when that list differs from `scripts/install_scripts_allowlist.txt` (created in this task from the current lockfile, reviewed by the owner).

## Files
| Action | Path |
|---|---|
| Modify | `.claude/skills/security-checks/scripts/secret_scan.py` (stdin mode) + its test file (create `app/backend/tests/test_secret_scan_stdin.py` if the skill has no tests) |
| Create | `scripts/list_licences.py` + test `app/backend/tests/test_list_licences.py` |
| Create | `scripts/install_scripts_allowlist.txt` |
| Modify | `scripts/ci_local.py` (four stages above) + its test |
| Generated | `docs/reference/LICENCES.md` |

## Interfaces
`secret_scan.py -`: reads `sys.stdin` as UTF-8 with `errors="replace"`; exit 1 with findings, 0 with `no secrets found`.
`scripts/list_licences.py [--out docs/reference/LICENCES.md]`:
- Python: `importlib.metadata.distributions()` in the uv environment; licence = `License-Expression`, else `License` (first line), else the `License ::` classifiers joined; runtime set = the transitive closure of `app/backend` + `app/agents` dependencies from `uv.lock` (parse the TOML with `tomllib`; packages under `[package.dev-dependencies]` / the dev group are dev-only).
- npm: `app/frontend/package-lock.json` → `packages` entries; `license` field; `"dev": true` → dev-only.
- Output: one Markdown table per ecosystem `Package | Version | Licence | Runtime/dev`, sorted by name; deterministic (LF, no dates except the lockfile hashes' short form in a header line).
- Exit 1 listing each denied or unknown runtime licence.

## Tests (key cases)
- stdin: piping `"x = sk-" + "a"*24` gives exit 1 and output without the key text; piping plain text gives `no secrets found`.
- `list_licences`: with a fixture `uv.lock` + fake distributions (monkeypatched `importlib.metadata.distributions`) and a fixture `package-lock.json`: an `AGPL-3.0` runtime package → exit 1 naming it; the same package as dev-only → exit 0, reported; output is identical on two runs.

## Steps
- [ ] Tests → FAIL → implement → green.
- [ ] Run `python scripts/ci_local.py --full --only history-secrets,audit,lockfiles,licences` → paste the output. A history hit → STOP, the owner decides (never rewrite history). An audit hit → STOP, report.
- [ ] Show `LICENCES.md` and the install-script allowlist to the owner; record their OK in STATUS.md.
- [ ] Repo checks.
- [ ] **Docs.** SECURITY.md → "Supply chain" (stages, deny list, install-script allowlist, how to accept a licence); THREAT_MODEL.md T12, T13 confirmed. Work-log; `STATUS.md` (last 6.6, next 6.7).
- [ ] **Commit** `feat(security): scan git history, audit dependencies and licences locally`.
