# Phase 5 · Task 4 — Curated, cited rules table and CO2e → OWNER GATE 5a

**Skills:** `plan-execution`, `engineering-core` (pure, cited, test-first), `security-checks`, `project-documentation`.

**CLAUDE.md rule 8 applies in full.** Every rule is transcribed from the official text, with the
article/section and a link. Nothing comes from memory. The site is outside the EU and exports to the
EU: the operator's own LDAR policy is **modelled on** Regulation (EU) 2024/1787; the EU articles do
not bind the site. Import-related articles are context (`applies_to_site="import_context"`).
If a source text cannot be opened, **STOP and ask** — never fill a rule without its text.

## Sources (open these; record the access date)
| Id | Document | Official location |
|---|---|---|
| `EU-2024-1787` | Regulation (EU) 2024/1787 on the reduction of methane emissions in the energy sector | `https://eur-lex.europa.eu/eli/reg/2024/1787/oj` (English HTML) |
| `OGMP-2.0` | OGMP 2.0 Reporting Framework (UNEP IMEO) | the framework PDF linked from `https://ogmpartnership.org` (record the exact PDF URL you used) |
| `IPCC-AR6-WG1-7` | IPCC AR6 WG1 Chapter 7, Table 7.15 (GWP100 of methane) | `https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-7/` (record the table) |
Reading the HTML pages is fine. Downloading a PDF to disk needs the owner's yes (state file name, source, size).

## Rules to transcribe (candidate list — the **text decides** what each says)
| rule_id | What to look for | `applies_to_site` |
|---|---|---|
| `POLICY-LDAR-REPAIR` | the article on leak detection and repair: when a leak must be repaired / replaced, the first-attempt and completion deadlines (days) | `policy` |
| `POLICY-LDAR-DEFINITIONS` | the definitions article: "leak", "venting", "flaring" (needed to classify a rod-packing release routed to a vent stack) | `policy` |
| `POLICY-VENTING` | the article restricting venting: the allowed cases (emergency, malfunction, unavoidable / strictly necessary maintenance …) | `policy` |
| `POLICY-VENT-FLARE-REPORT` | the article on reporting venting and flaring events: which events, thresholds (duration / volume), deadline | `policy` |
| `POLICY-FLARING` | the article on flaring efficiency / pilot requirements, if present | `policy` |
| `OGMP-SOURCE-L4` | OGMP 2.0: what Level 4 (source-level measurement-based quantification) requires, and that levels apply per source category | `reporting` |
| `IMPORT-INFO` | the article(s) on information importers must provide about producers / exporters, and the equivalence timeline | `import_context` |
| `POLICY-INSTRUMENT-FAULT` | **not a regulation**: the fictional operator's instrument-maintenance policy — the owner provides the wording and the ticket deadline (ask in chat); citation `PlumeTrace operator policy (fictional)`; no URL | `policy` |
A super-emitter flag exists only if one of the texts defines a threshold; then add `POLICY-SUPER-EMITTER` with that threshold and citation. If no text defines one, `ComplianceOutput.super_emitter` is always `False` and AGENTS.md says why.

## Files
| Action | Path |
|---|---|
| Create | `app/backend/plumetrace/rules/__init__.py`, `rules/model.py`, `rules/table.py`, `rules/applicability.py`, `rules/lookup.py`, `rules/gwp.py` |
| Create (tests) | `app/backend/tests/rules/test_table.py`, `test_lookup.py`, `test_gwp.py` |
| Modify | `app/backend/plumetrace/simulator/scenarios/s1_rod_packing.py`, `s4_planned_blowdown.py`, `s5_sensor_drift.py` → `expected.rule_ids` (after the gate) |
| Create | `docs/reference/RULES.md` (generated section + hand-written context) and `scripts/export_rules_md.py` |

## Interfaces
`rules/model.py`:
- `class Rule(BaseModel)` (`frozen`, `extra="forbid"`): `rule_id: str` (pattern `^[A-Z][A-Z0-9]*(-[A-Z0-9]+){1,}$`), `title: str`, `source_id: Literal["EU-2024-1787", "OGMP-2.0", "OPERATOR-POLICY"]`, `citation: str` (e.g. `"Regulation (EU) 2024/1787, Article 14(1)"`), `url: str | None` (required unless `OPERATOR-POLICY`), `basis_quote: str` (verbatim excerpt ≤ 400 chars, the sentence(s) the rule rests on), `policy_text: str` (our operator-policy wording, ≤ 400 chars, starts "Operator policy (modelled on …):" for `policy` rules), `applies_to_site: Literal["policy", "reporting", "import_context"]`, `first_attempt_days: float | None`, `repair_deadline_days: float | None`, `threshold_kg_h: float | None`, `accessed_on: date`, `owner_verified: bool = False`.
`rules/table.py`: `RULES: Final[tuple[Rule, ...]]`; `TABLE_VERSION: Final = "2026-11-<dd>"` (date of transcription).
`rules/applicability.py`: `APPLIES: Final[Mapping[tuple[EventClass, EmissionSource], tuple[str, ...]]]` — which rule ids answer each `(event_class, emission_source)` query; written from the texts (e.g. `("leak_to_repair", "component_leak")` → the repair rule (+ OGMP L4); `("venting", "vent")` → venting + reporting rules; `("instrument_fault", "none")` → `POLICY-INSTRUMENT-FAULT`). Every rule id in `APPLIES` exists in `RULES` (test).
`rules/lookup.py`: `def lookup(event_class: str, emission_source: str) -> list[Rule]` — unknown pair → `[]` (the agent then states no rule applies). `def rule_by_id(rule_id: str) -> Rule` (`KeyError`).
`rules/gwp.py`: `CH4_FOSSIL_GWP100: Final[float]` and `GWP_SOURCE: Final[str]` — value and table citation from AR6 WG1 Table 7.15 (fossil methane, because the gas is fossil natural gas); `def co2e_t(ch4_kg: float) -> float` → `ch4_kg · GWP / 1000` (`ValueError` for negative).

## Tests
`test_table.py` (full code):
```python
"""The curated rules table is complete, cited and internally consistent."""

from plumetrace.rules.applicability import APPLIES
from plumetrace.rules.table import RULES


def test_rule_ids_are_unique() -> None:
    """No duplicate rule ids."""
    ids = [r.rule_id for r in RULES]
    assert len(ids) == len(set(ids))


def test_every_regulatory_rule_is_cited() -> None:
    """Regulation and OGMP rules carry a citation, a link and a verbatim basis."""
    for r in RULES:
        assert r.citation and r.basis_quote and r.policy_text
        if r.source_id != "OPERATOR-POLICY":
            assert r.url is not None and r.url.startswith("https://")


def test_policy_rules_never_claim_eu_law_binds_the_site() -> None:
    """Policy wording is 'modelled on' the regulation (CLAUDE.md rule 8)."""
    for r in RULES:
        if r.applies_to_site == "policy" and r.source_id == "EU-2024-1787":
            assert r.policy_text.startswith("Operator policy (modelled on")


def test_applicability_refers_to_existing_rules() -> None:
    """Every rule id used by lookup exists."""
    known = {r.rule_id for r in RULES}
    for ids in APPLIES.values():
        assert set(ids) <= known
```
`test_lookup.py`: `lookup("instrument_fault", "none")` returns exactly `POLICY-INSTRUMENT-FAULT`; an unknown pair → `[]`; `rule_by_id("NOPE")` raises `KeyError`; plus one test per `APPLIES` entry asserting the exact rule-id list you transcribed (docstring cites the article).
`test_gwp.py`: `co2e_t(1000.0) == CH4_FOSSIL_GWP100` (docstring: the AR6 table row and value); negative → `ValueError`.

## `scripts/export_rules_md.py`
Writes the "Rules table" section of `docs/reference/RULES.md` between the markers `<!-- rules:start -->` and `<!-- rules:end -->`: one row per rule (id, title, citation as a link, basis quote, policy text, deadlines/threshold, applies-to, accessed on, owner verified). LF endings, deterministic (sorted by id). The hand-written part of RULES.md explains: the outside-EU framing, import context, OGMP levels per source category (the UI badge is a simplification), and the classification question below.

## Owner Gate 5a (STOP after the steps)
Write in `docs/evidence/2026-11-gate-5a-rules.md`:
1. The table (from RULES.md) with every quote next to its link.
2. **The classification question:** "By the definitions article, is a rod-packing release routed through the common vent header to VS-250 a *leak* (repair under the LDAR rule) or *venting*?" — quote both definitions, give your reading, ask the owner. The answer sets S1's `ComplianceOutput.event_class` and `expected.rule_ids` (design §6: the regulation text wins over the scenario's intended answer).
3. The expected `rule_ids` you propose for S1, S4, S5.
4. The super-emitter outcome (threshold found or not).
Then `STATUS.md`: "Phase 5 Task 4 done — waiting for Gate 5a (rules table)". **STOP.** After the owner signs off: set `owner_verified=True` on the approved rules, update the three scenarios' `expected.rule_ids` (and S1's expected class in AGENTS.md), rerun the tests and the export script, commit `chore(rules): record owner verification of the rules table`, and only then move to Task 5.

## Steps
- [ ] Open the three sources; transcribe; ask the owner for the instrument-fault policy wording and deadline.
- [ ] Tests → FAIL → implement → `uv run pytest app/backend -q` green.
- [ ] `cd app && uv run python ../scripts/export_rules_md.py`; review RULES.md by eye.
- [ ] Repo checks; secret scan.
- [ ] **Docs.** RULES.md (above), AGENTS.md → "Compliance" (how `lookup_regulation_rule` maps to `APPLIES`), ENGINEERING.md → "CO2e" (GWP value + citation). Work-log.
- [ ] **Commit** `feat(rules): add curated, cited rules table and CO2e conversion`.
- [ ] Gate 5a document; STOP.
