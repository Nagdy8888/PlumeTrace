# Owner actions

- [x] Install Docker Desktop.
- [x] Add `SUPABASE_DB_URL` and `LANGSMITH_PROJECT` to the root `.env`.
- [x] Gate 1: review `app/backend/plumetrace/facility/data/ks07.yaml` (layout, coordinates,
      fictional location), the gas composition, `component_counts.yaml` and the emission sources.
      All of them are tabulated in `docs/reference/SIMULATOR.md` (section "Facility KS-07"); the
      component-count source and the proxy caveat are in `component_counts.yaml` and that page.
      Signed off 2026-11-13 (see STATUS.md).
- [x] Push the repository to GitHub (done 2026-11-13: private repo github.com/Nagdy8888/PlumeTrace). GitHub Actions stay **off**: billing; all checks run locally with `python scripts/ci_local.py` and the pre-commit hook; install the hook once per clone with `python scripts/install_git_hooks.py`).
- [ ] Verify the Subpart W Table W-1B counts in `component_counts.yaml` against the primary CFR 2023 text (govinfo CFR-2023-title40-vol23) before Gate 2; report any mismatch.
- [ ] Install Blender (LTS) before Phase 4.
- [ ] Deployment of the replay site: a later phase, not planned yet (no Vercel project now).
