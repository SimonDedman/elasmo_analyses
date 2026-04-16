# Schema Documentation — Master Index

*Comprehensive reference for all extraction schemas, data sources, and team leads.*

*Last updated: 2026-04-16*

---

## Team Leads

Each schema or data source has a designated lead who reviews validator feedback, approves rule changes, and maintains the extraction logic.

| Area | Prefix / Source | Lead |
|------|-----------------|------|
| Species | `sp_` | Chris Mull |
| Analytical techniques | `a_` | Guuske Tiktak |
| Ecosystem | `eco_` | Chris Mull |
| Discipline | `d_` | Guuske Tiktak |
| Ocean basin (extraction) | `b_` | Simon Dedman |
| Ocean basin (geographic pipeline) | `ob_` | Simon Dedman |
| Depth | `depth_` | Chris Mull |
| Pressure / Threat | `pr_` | David Ruiz-Garcia |
| Fishing gear | `gear_` | David Ruiz-Garcia |
| Impact / Response | `imp_` | David Ruiz-Garcia |
| Author enrichment (OpenAlex) | `outputs/openalex_*.csv` | Simon Dedman |
| Author enrichment (NamSor gender/origin) | `outputs/namsor_*.csv` | Elena Fernández-Corredor |
| Altmetric social attention | `outputs/altmetric_scores.csv` | David Shiffman |
| Open access status (Unpaywall) | `outputs/unpaywall_oa_by_doi.csv` | Elena Fernández-Corredor |
| Journal quality (SCImago) | `data/journal_quality/` | Elena Fernández-Corredor |
| Geographic extraction | `database/technique_taxonomy.db` | Simon Dedman |
| Social aggregations (future) | TBD | Alex McInturf, Sophia Pelletier, Deven Guerrero |
| Everything else | — | Simon Dedman |

---

## Schema Documentation

### Rule-based extraction (Tier 1)

These schemas use keyword/threshold matching against full PDF text with section-weighted scoring and an evidence trail in `outputs/schema_extraction_evidence.csv`.

- [Ecosystem](ecosystem_component_proposal.md) — `eco_` (20 cols) — habitat types, zones, depth realms
- [Pressure / Threat](pressure_proposal.md) — `pr_` (26 cols) — fishing, climate, pollution pressures
- [Fishing Gear](gear_proposal.md) — `gear_` (29 cols) — gear types and mitigation measures
- [Impact / Response](impact_proposal.md) — `imp_` (25 cols) — mortality, abundance, behaviour change, etc.
- [Discipline](discipline_proposal.md) — `d_` (19 cols) — research discipline classification
- [Ocean Basin](ocean_basin_proposal.md) — `b_` (9 cols) and `ob_` (9 cols)

### Column-based extraction (Tier 2)

These schemas scan PDF text for a predefined column list with frequency counting.

- [Species](species_proposal.md) — `sp_` (1,308 cols, int16 frequencies)
- [Analytical Techniques](analytical_techniques_proposal.md) — `a_` (215 cols, int16 frequencies)
- [Depth](depth_proposal.md) — `depth_` (3 cols: range, min, max)

### External data sources

- [Author Enrichment](author_enrichment.md) — OpenAlex + NamSor
- [Altmetric](altmetric.md) — social attention scores
- [Open Access Status](open_access.md) — Unpaywall
- [Journal Quality](journal_quality.md) — SCImago rankings
- [Geographic Extraction](geographic_extraction.md) — author/study countries, basins

---

## Rule Palette Reference

All Tier 1 rules follow a common grammar defined in `scripts/extract_schema_columns.py` via the `BinaryColumn` dataclass:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Column identifier (e.g. `eco_marine`) |
| `terms` | list[str] | Keywords, phrases, or wildcards (`*` suffix expands to `\w*`) |
| `threshold` | int | Minimum total mention count (summed across terms) for column=1. Default 2. |
| `anchors` | list[str] or None | Optional co-occurrence terms; if set, at least one must fire in addition to meeting the threshold |
| `case_sensitive_terms` | set[str] | Subset of terms requiring exact case match (for acronyms like `IUU`, `CPUE`, `IUCN`) |

Full rule palette as JSON: [`outputs/extraction_rules.json`](../../outputs/extraction_rules.json) (23 KB, 123 rules)

Rules are also embedded in every validation page as `assets/rules.json` so reviewers can see all rules per schema alongside which ones fired for each paper.

### Section weighting

Papers are split into labelled sections (abstract, introduction, methods, results, discussion, references, acknowledgements). Each schema has a section weight profile — e.g. references and acknowledgements are excluded from `d_`/`eco_` to prevent false positives from citation titles. See [extraction_logic.md](extraction_logic.md) for the full section weight matrix.

### Derived columns (no evidence trail)

Three columns are derived rather than keyword-extracted, and therefore appear ticked on validation pages without an evidence panel:

- `gear_target_species` (string) — captured words around "targeting X" / "X fishery". Currently produces noisy data; fix planned.
- `imp_quantified` (bool) — True if any statistical expression (%, p-value, CI, decimals) appears anywhere in the paper. Planned upgrade: capture the actual values, units, and context.
- `imp_is_bycatch` (bool) — derived from `pr_bycatch` + `gear_target_species`. Downstream of the above fixes.

See [extraction_quality_issues.md](extraction_quality_issues.md) and the planned fixes.

---

## Validation

Every author in the OpenAlex database has a validation page at:

```
https://simondedman.github.io/elasmo_analyses/validate/{openalex_id}.html
```

The landing page at `https://simondedman.github.io/elasmo_analyses/validate/` lets anyone search by name.

Reviewers can:
- See which rules fired for each of their papers
- See the full rule palette (all terms, thresholds, anchors) per schema
- Check/uncheck boxes to correct false positives or negatives
- Suggest rule changes (add terms, remove terms, adjust threshold)
- Rate each category (correct / partially correct / incorrect)
- Add free-text notes
- Submit → auto-created pull request for the team lead to review

---

## Related Documents

- [extraction_logic.md](extraction_logic.md) — technical docs for the extraction pipeline
- [extraction_quality_issues.md](extraction_quality_issues.md) — catalogued false-positive patterns
- [extraction_review_reference.md](extraction_review_reference.md) — full column inventory
- [schiffman_comparison.md](schiffman_comparison.md) — comparison with Schiffman et al. 2020 manual classification
- [../technical/2026-04-16-validation-ui-design.md](../technical/2026-04-16-validation-ui-design.md) — validation UI design spec
