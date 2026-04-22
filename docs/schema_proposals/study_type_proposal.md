# Proposed Schema: Study Type (Paper Type)

**Status:** Active — banner-first classifier, added 2026-04-22 (replaces 2026-04-20 title-only heuristic)
**Column prefix:** `study_type` (single column, not prefixed like binary schemas)
**Team lead:** Simon Dedman
**Source:** `classify_study_type` in `scripts/extract_schema_columns.py`; incremental re-runner `scripts/rerun_study_type.py`; audit page `docs/study_type_audit.html`

## Purpose

Classify every paper into exactly one mutually-exclusive category so downstream analyses can filter reviews, corrigenda, editorials etc. out of empirical-only summaries (gear, pressure, impact counts etc.) and treat them as their own population when asked.

This replaces the hardcoded `"empirical"` default that previously masked all secondary-literature papers as if they were empirical studies.

## Categories

Priority-ordered. First match wins.

| Label | Meaning | Typical banner / title signals |
|---|---|---|
| `corrigendum` | Correction / erratum / retraction notice | `CORRIGENDUM`, `ERRATUM`, `CORRECTION TO`, `RETRACTION NOTICE`, `PUBLISHER'S NOTE` |
| `letter` | Short-form commentary, reply, news, or brief technical piece | `LETTER TO THE EDITOR`, `TECHNICAL COMMENT`, `MATTERS ARISING`, `NEWS & VIEWS`, `BRIEF COMMUNICATION`, `SHORT COMMUNICATION`, `RAPID COMMUNICATION`, `REPLY TO`, `RESPONSE TO`, `REBUTTAL TO` |
| `review` | Systematic / narrative / literature review, meta-analysis | `REVIEW SUMMARY`, `SYSTEMATIC REVIEW`, `LITERATURE REVIEW`, `NARRATIVE REVIEW`, `COMPREHENSIVE REVIEW`, `SCOPING REVIEW`, `UMBRELLA REVIEW`, `MINI REVIEW`, `COLLECTION REVIEW`, `REVIEW PAPER`, `REVIEW ARTICLE`, `META-ANALYSIS`, `RESEARCH | REVIEW`, plain `REVIEW` standalone in banner zone (title fallback: `A review of …`, `review of …`) |
| `synthesis` | Multi-study synthesis that doesn't call itself a review | `RESEARCH SYNTHESIS`, `A SYNTHESIS`, `SYNTHESIS OF` |
| `conceptual` | Perspective, viewpoint, opinion, policy piece, framework paper | `PERSPECTIVE`, `VIEWPOINT`, `OPINION`, `POLICY FORUM`, `POLICY BRIEF`, `HYPOTHESIS AND THEORY`, `COMMENTARY`, `CONCEPTUAL/METHODOLOGICAL/THEORETICAL FRAMEWORK` |
| `empirical` | Primary-data study (default if a PDF exists and no higher-priority banner fires, or if an explicit empirical banner fires) | `RESEARCH ARTICLE`, `RESEARCH PAPER`, `REGULAR ARTICLE/PAPER`, `ORIGINAL RESEARCH/ARTICLE/PAPER`, `PRIMARY RESEARCH PAPER`, `FULL PAPER`, `CASE REPORT`, `EMPIRICAL STUDY` |

**`ARTICLE` alone is NOT a banner token** for `empirical` — too permissive, fires on generic wording.

## Scope (broad-scope rule, 2026-04-22)

- Papers **with** an extractable PDF: classified as above; `study_type` takes one of the six labels.
- Papers **without** an extractable PDF: `study_type = None`. No fallback, no title-only classification. This matches the rest of the extraction pipeline (no binary-schema values are produced from titles or abstracts either).

## Classification Pipeline

```
                 ┌────────────────────────────┐
                 │ classify_study_type(title, │
                 │   keywords_text, full_text,│
                 │   journal)                 │
                 └──────────┬─────────────────┘
                            │
             full_text empty/missing?
                            │
                ┌───── yes ─┴─ no ─────┐
                ▼                       ▼
     (None, "no_pdf", "")    Normalise banner:
                                  1. First 600 chars of page 1
                                  2. Collapse whitespace
                                  3. Un-space Wiley letter runs
                                     (B R I E F → BRIEF)
                                  4. De-squash Wiley compounds
                                     (REGULARPAPER → REGULAR PAPER)
                                  5. Journal-name suppression
                                     (strip one instance of each word
                                      from the journal field, incl.
                                      singular stem, to stop "Reviews
                                      in Fish Biology" polluting REVIEW)
                                              │
                                              ▼
                          Banner regex library (priority-ordered,
                          first match wins):
                              1. corrigendum
                              2. letter
                              3. review (specific variants)
                              4. review (plain REVIEW in first 300 chars,
                                 negative-lookahead on OF/AUTHORS/BOARD/…)
                              5. synthesis
                              6. conceptual
                              7. empirical (explicit)
                                              │
                                match?  yes ──▶ return (label, "banner", snippet)
                                              │
                                        no ───▼
                          Title + keywords fallback regex:
                              same priority, weaker patterns
                                              │
                                match?  yes ──▶ return (label, "title_kw", snippet)
                                              │
                                        no ───▼
                          return ("empirical", "default_empirical",
                                  first 80 chars of banner)
```

## Why Banner > Title > Keywords

A single occurrence of "review" in body prose is **not** enough to tag a paper as a review — and the title alone is sometimes misleading (paper 33434 *"Ecological roles and importance of sharks in the Anthropocene Ocean"* has no "review" in its title but is the lead Review of its Science issue). The banner — the journal-assigned type label printed on page 1 — is the authoritative signal.

Title fallback exists because some journals (EBF, MEPS, Scientific Reports, IUCN, Fishery Bulletin, Copeia, several smaller journals) don't print a type banner. In those cases we accept the weaker signal of `"A review of …"` or `"A systematic review of …"` in the title. Risk: species-description papers whose titles include a sub-review (e.g. *"A new Myliobatiformes from the Miocene and a review of the fossil Myliobatiformes …"*) can false-positive. Mitigation: the audit page surfaces every title-fallback call so reviewers can manually override.

## Journal-Family Banner Signatures

Tabulated from the 2026-04-22 survey (1,091 banners across 182 journals with ≥20 PDF'd papers). Column "Signature" shows the dominant form per family.

| Publisher family | Example journals | Typical banner signature |
|---|---|---|
| Science (AAAS) | Science | `REVIEW SUMMARY`, `REVIEW`, `RESEARCH ARTICLE`, `RESEARCH \| REVIEW`, `PERSPECTIVE`, `POLICY FORUM` |
| Nature | Nature, Scientific Reports | Usually no banner (just journal header); `MATTERS ARISING`, `NEWS & VIEWS` when applicable |
| Springer | Marine Biology, EBF, Hydrobiologia, Cell and Tissue Research | `ORIGINAL PAPER`, `PRIMARY RESEARCH PAPER`, `REGULAR ARTICLE`, `REVIEW` |
| Wiley | JFB, Mol Ecol Res, Aquatic Conservation, Fish and Fisheries | Spaced letters `R E G U L A R   P A P E R` / squashed `REGULARPAPER`; `REVIEW PAPER`; `MINI REVIEW` |
| Elsevier | Marine Pollution Bulletin, Fisheries Research, GCE | Lowercase-initial `Review` / `Research paper` / `Original research article` after the `Contents lists available …` metadata block |
| Frontiers | Frontiers in Marine Science | All-caps banner on first line: `SYSTEMATIC REVIEW published:`, `REVIEW published:`, `ORIGINAL RESEARCH published:`, `HYPOTHESIS AND THEORY` |
| PLOS | PLoS ONE, PLoS Biology | `RESEARCH ARTICLE`, `COLLECTION REVIEW` |
| Cambridge / OUP | ICES JMS, Parasitology | Usually no banner; editorial metadata only |
| Small / regional | MEPS, Fishery Bulletin, Cybium, Copeia, Zootaxa | Usually no banner; fall through to `default_empirical` |

Full journal-by-journal sample data: `outputs/journal_banner_survey.md`.

## Audit Page

`docs/study_type_audit.html` — DataTables review of all ~18.5k PDF'd papers. Columns: lit_id · year · publisher · journal · type · signal · matched snippet · title (linked to DOI).

Defaults to filter `type != empirical`; clear the search box to see the empirical papers too. Use to:
- Spot banner-vs-title disagreements (audit `signal = "title_kw"` rows).
- Find systematic publisher-family patterns.
- Escalate false positives/negatives for manual correction in the per-author validation pages.

## Validation Workflow

The per-author validation pages at `docs/validate/{openalex_id}.html` will (from commit 2 onward) include a **"Paper Type"** section for each paper:
- Dropdown pre-populated with the classifier's verdict.
- Validator can change it; change is saved into the same per-paper validation state as all other sections (Ocean Basin, Discipline, etc.).
- The banner snippet / title match is shown as evidence, in the same ⓘ-popover format used by other categories.

## Known Limitations

1. **Papers with no banner and no type-word in the title.** Example: Couturier et al. 2012 *"Biology, ecology and conservation of the Mobulidae"* — is actually a review paper but the title reads like a research article. Currently falls through to `default_empirical`. Audit page flags these implicitly (they have `signal = default_empirical`).
2. **Same-family titles masking different types.** A species-description paper whose title includes *"… and a review of …"* will title-fallback to `review` when it's actually primary. Audit page surfaces these under `signal = title_kw`.
3. **PDF OCR quality.** A few PDFs have corrupt font tables; MuPDF occasionally warns but still extracts usable text. Extreme cases fall through to `default_empirical`.
4. **Publisher column on audit page.** ~37% journal→publisher coverage from existing `docs/papers_data.json` + `outputs/by_publisher/*.csv` data; the rest show as `unknown`. Good enough for spotting Wiley/Elsevier/Springer-family patterns but not complete.

## Rerun Commands

```bash
# Rebuild the journal-family banner survey (input for classifier tuning)
python3 scripts/survey_journal_banners.py

# Recompute study_type across the full parquet (banner-aware, PDF-only)
python3 scripts/rerun_study_type.py

# Regenerate the audit page from current parquet state
python3 scripts/generate_study_type_audit.py
```

## Version History

- **2026-04-22** — Replaced title-only heuristic with banner-first classifier (this document's current state). Added journal-name suppression, Wiley spaced-letter normalisation, and broad-scope rule (no extraction from non-PDF papers). Added `study_type_signal` and `study_type_evidence` columns for audit.
- **2026-04-20** — Initial title + KEYWORDS heuristic (`classify_study_type`, fix C in commit 60078568b). Six labels; title-only fallback for non-PDF papers.
- **Before 2026-04-20** — All papers hardcoded to `"empirical"`.
