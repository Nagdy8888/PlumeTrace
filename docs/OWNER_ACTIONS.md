# Owner actions

- [x] Install Docker Desktop.
- [x] Add `SUPABASE_DB_URL` and `LANGSMITH_PROJECT` to the root `.env`.
- [x] Gate 1: review `app/backend/plumetrace/facility/data/ks07.yaml` (layout, coordinates,
      fictional location), the gas composition, `component_counts.yaml` and the emission sources.
      All of them are tabulated in `docs/reference/SIMULATOR.md` (section "Facility KS-07"); the
      component-count source and the proxy caveat are in `component_counts.yaml` and that page.
      Signed off 2026-11-13 (see STATUS.md).
- [x] Push the repository to GitHub (done 2026-11-13: private repo github.com/Nagdy8888/PlumeTrace). GitHub Actions stay **off**: billing; all checks run locally with `python scripts/ci_local.py` and the pre-commit hook; install the hook once per clone with `python scripts/install_git_hooks.py`).
- [ ] Before the Phase 7 release gate: check each cited value against its primary source (Briggs rural sigma coefficients; Martin PG fits; EPA 1995 Table 2-4; Subpart W W-1B counts (govinfo CFR-2023-title40-vol23) and W-4; AP-42 13.5; OGMP 2.0 98 %); report any mismatch. Until ticked, README and About say "cited per project plan, not verified against the primary source".
- [x] Gate 2 signed off 2026-11-14 (delegated decision, see STATUS.md).
- [ ] Open-Meteo licence (before any public launch): the free API tier is for non-commercial use only. The data is CC BY 4.0, so keep the attribution plus the ERA5 / Copernicus acknowledgement (the constant `ATTRIBUTION` in `data_sources/open_meteo.py` names Open-Meteo, CC BY 4.0 and ERA5 but not yet Copernicus: add it before launch; the UI links the text to <https://open-meteo.com/>). Confirm that this labelled-simulated portfolio demo counts as non-commercial use, or move to a commercial plan, before the project is made public.
- [ ] Install Blender (LTS) before Phase 4.
- [ ] Deployment of the replay site: a later phase, not planned yet (no Vercel project now).
