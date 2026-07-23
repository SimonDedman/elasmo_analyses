# Validation Meetings Agenda — 2026-04-21 (Tue) & 2026-04-22 (Wed)

**Reading list before the meeting:**
1. [`2026-04-20_validation_synthesis.md`](./2026-04-20_validation_synthesis.md) — full synthesis of Alex McInturf's & David Ruiz-García's submissions, with §2 covering the 27 rules item-by-item
2. [`2026-04-20_schema_systematic_review.md`](./2026-04-20_schema_systematic_review.md) — per-schema inventory: thresholds, anchors, case-sensitive sets, prerequisite gating, full term lists. Confirms TITLE/KEYWORDS coverage by schema.
3. [`ruiz_garcia_validation_master.md`](./ruiz_garcia_validation_master.md) — David's 27 rule proposals in full
4. [`2026-04-20_validation_ui_mockup.html`](./2026-04-20_validation_ui_mockup.html) — open in browser; click any [?] icon for the proposed per-column rule popover

---

## What's already done (no discussion needed unless someone disagrees)

These were implemented over commits `da257dd91` → `f38ecefd0` → today's commit. Re-extraction is **deferred** until the meeting confirms the rule set.

| # | Change | File(s) |
|---|---|---|
| 1 | Worker `GITHUB_PAT` repaired (Contents:write) | Cloudflare dashboard |
| 2 | `gear_mit_ghost` → `gear_ghost`; "ghost fishing" added | extract_schema_columns.py + rules.json |
| 3 | `eco_deepwater`: added "deepwater", "deep water" variants | extract_schema_columns.py + rules.json |
| 4 | `d_fisheries`: added bycatch/discard*/retention/non-target species/non-target catch | extract_schema_columns.py + rules.json |
| 5 | *Aetomylaeus bovinus* added to species lookup + `sp_` columns | data/species_common_lookup_cleaned.csv + options.json |
| 6 | `imp_biomass` document-level anchors (response-language) | extract_schema_columns.py + rules.json |
| 7 | `pr_aquaculture` threshold 1 → 2 | extract_schema_columns.py + rules.json |
| 8 | `d_biology` 8 → 20 terms (vertebral count*, band pair*, gonadosomatic index, hepatosomatic index, GSI, HSI with prereq gating, "Le Cren", "Fulton's K", morphometric analysis, total/precaudal length, disc width) | extract_schema_columns.py + rules.json |
| 9 | `d_physiology` 10 → 28 terms (SMR/RMR/MMR/Ucrit/TMAO/Q10 case-sensitive + plasma chemistry + critical swimming etc.) | extract_schema_columns.py + rules.json |
| 10 | New `prerequisite_terms` feature on BinaryColumn (acronym disambiguation) | extract_schema_columns.py |
| 11 | TITLE + KEYWORDS sections injected, weight 2.0 across all 7 weighted schemas | extract_schema_columns.py + rules.json + validate.js + style.css |
| 12 | Validation UI: per-schema palette now shows section-weights table + 📄 proposal link | rules.json (`_section_weights`, `_proposal_url`) + validate.js + style.css |
| 13 | NamSor labels asterisked, footer attribution clarified | validate.js |
| 14 | receive-validation workflow Python rewritten to match real submit.js schema; renders author_corrections | .github/workflows/receive-validation.yml |
| 15 | Cloudflare Worker comment corrected | scripts/cloudflare-worker/worker.js |
| 16 | Elena E1 — `imp_community_composition` anchors widened to wildcards so verb tenses fire (`chang*/shift*/impact*/alter*`) | extract_schema_columns.py + rules.json |
| 17 | Elena E2 — `imp_biodiversity` anchors widened to wildcards + `decreas*/extinct*` added; `extinction*` also added as a term | extract_schema_columns.py + rules.json |
| 18 | Elena E3 — `pr_ocean_acidification` threshold 1 → 2 (same class as pr_aquaculture) | extract_schema_columns.py + rules.json |
| 19 | NamSor gender normaliser — page generator maps NamSor "male"/"female" → dropdown codes "M"/"F" so validators don't submit phantom gender corrections | generate_validation_pages.py |
| 20 | **A1** — synthetic-section pollution fix: TITLE and KEYWORDS injections now terminate with an OTHER marker; `OTHER` pattern added to `_SECTION_PATTERNS`; OTHER weight zeroed across all 7 schemas; Springer-style affiliation paragraphs stripped from PDF text before labelling. Closes the `d_conservation` false-positive on 27537 where author affiliation text scored 6.0 in TITLE. | extract_schema_columns.py |
| 21 | **C** — `study_type` classifier replaces hardcoded `"empirical"` default: TITLE + KEYWORDS scanned for review / synthesis / conceptual / corrigendum / letter signals, priority-ordered, mutually exclusive. | extract_schema_columns.py |
| 22 | **D** — depth-extraction regex tightened to require a bathymetric-context word; depth evidence rows now written to `schema_extraction_evidence.csv` with ±context snippet (previously 0 depth rows of 260K). Closes Alex's basking-shark body-length-as-depth bug. | extract_schema_columns.py |

---

## Tuesday agenda — items needing decisions for re-extraction

### 1. Mediterranean sub-basin scheme (item §2.7) — IMPLEMENTATION CONFIRMATION

Simon already resolved the trade-offs:
- **Keep both** the existing 8 sub-basin columns AND add 5 GFCM grouping columns
- **`sb_black_sea` retained** as own column (not folded into Eastern Med)
- **`sb_sea_of_marmara` removed**; "Sea of Marmara" / "Marmara" / "Bosphorus" become keywords for `sb_black_sea`

**Question for the meeting:** can David confirm the proposed GFCM column set covers everything researchers ask for? Proposed columns:
- `sb_western_mediterranean` (Alboran, Balearic, Sardinian, Ligurian, Tyrrhenian, Catalan, Gulf of Lions)
- `sb_central_mediterranean` (Strait of Sicily, Sicilian Channel, Ionian, Libyan Sea, Gulf of Sirte, Gulf of Gabès)
- `sb_eastern_mediterranean` (Aegean, Sea of Crete, Levantine Sea, Cilician Sea, Cyprus, Iskenderun Bay)
- (`sb_adriatic_sea` and `sb_black_sea` already exist; Marmara folded into latter)

If endorsed → implement and include in re-extraction.

### 2. Conditional dependency for `imp_direction`/`quantified`/`confidence` (item §2.10)

**Need definition:** what counts as "pressure/threat detected"? Four options on the table:
- **(a)** Any `pr_*` column = 1 (broad)
- **(b)** Any `pr_*` ≥ 1.5 × threshold (strong signal)
- **(c)** ≥ 2 `pr_*` columns = 1 (multi-stressor confirmation)
- **(d)** Any `pr_*` = 1 OR any `imp_*` = 1 (David's suggestion)

Cost of each: low (post-processing rule). Pick one and document.

### 3. Coastal definition (item §2.11)

Simon's framing: ecosystem is location-as-ecosystem, not process-as-ecosystem. So `eco_coastal` should fire on sampling-location evidence; current rule is approximately right.

**Action for meeting:** confirm location-not-process framing; document in `ecosystem_component_proposal.md`. Decide whether `eco_*` should aim for mutual exclusivity (every paper assigned ≥ 1 ecosystem) — has knock-on effects for analysis.

### 4. SP_ and A_ section weighting (new question raised by systematic review)

Currently `sp_` (1,309 cols, integer counts) and `a_` (215 cols, integer counts) do NOT use section weighting at all. After today's TITLE/KEYWORDS work, these schemas don't benefit.

**Question:** should the integer-count schemas adopt weighted scoring with TITLE/KEYWORDS at 2.0? Authors typically list focal species and primary techniques in title/keywords; promoting these mentions could substantially improve precision (currently a passing mention of *Carcharodon* in a citation contributes the same as the focal-species mention in the title).

Cost: small — same matcher path, just add `_SECTION_WEIGHTS["sp_"]` and `_SECTION_WEIGHTS["a_"]` entries.

### 5. Per-column [?] disclosure UI (item §2.14, option 2)

Mockup ready ([`2026-04-20_validation_ui_mockup.html`](./2026-04-20_validation_ui_mockup.html)). Click any [?] in the right pane.

**Question:** ship as a follow-up commit, or wait for further feedback?

---

## Wednesday agenda — broader strategy & open questions

### 6. Wider species-list audit (item §2.4)

The *Aetomylaeus bovinus* miss was caused by a 2016 taxonomic revision (was *Pteromylaeus*) not propagating. The fresh-audit candidates are:
- 133 species in 2022 Sharkipedia snapshot but absent from our `sp_` columns
- An unknown number of species named since 2022 (we don't have a current snapshot)

**Action for the meeting:** assign owner to refresh the species list against current Shark References + live Sharkipedia + IUCN Red List. Estimated work: 2-4 hours one-off.

### 7. Section-weighted disciplines (item §2.8)

Still partially open. Keyword expansion done in this commit. The remaining question is whether `d_biology`/`d_physiology` should require Methods+Results co-occurrence (not just any-section-with-weight). David's suggestion. Cost: medium (matcher change to support per-column required-section sets).

### 8. Chemical pollution false positives (item §2.13)

Recommended: wait for re-extraction with TITLE+KEYWORDS active before deciding whether to add the specific-compound anchor. If false positives persist, add anchors `["heavy metal*", "mercury", "PCB", "PFAS", "pesticide*", "contaminant*", "microplastic*"]`. **TO REVIEW** post-extraction.

### 9. IMP structural merge (item §2 item 15)

David's proposal to merge `imp_injury` + `imp_physiology_stress` → `imp_health_assessment`. Schema-breaking. Simon said "Existing analyses are all moot and will be re-run before the presentation. Note that we'll review this point at the meeting." So it's open.

If adopted, would also need to consider similar consolidations (e.g. `imp_genetic` + `imp_biodiversity`?).

### 10. Re-extraction scheduling

The infrastructure now supports running extraction now AND again after the meeting decisions land — both runs are auto-snapshotted under `outputs/extraction_runs/<run_id>/` and can be diffed with `scripts/diff_extraction_runs.py`. So:

- **Option A — extract now, then again post-meeting:** captures the impact of today's rule changes (TITLE+KEYWORDS, GSI/HSI prereq, expanded biology/physiology vocabulary, anchored imp_biomass, raised pr_aquaculture threshold, deepwater/d_fisheries/sp_aetomylaeus_bovinus) BEFORE we layer in the meeting decisions. Then a second post-meeting run shows the marginal impact of THOSE changes on top.
- **Option B — wait, single extraction post-meeting:** simpler, but loses the intermediate audit point.

**Recommendation: Option A.** Today's commit is a meaningful rule-set on its own; bundling it with the meeting decisions makes the diff harder to reason about. Two runs gives a clear before/after for each layer. Measured runtime from `run_id 20260421T050413_5ca94a22d`: **1h 23m** for the full 30,558-paper corpus (wall-clock between `rules_snapshot.json` and `binary_classifications.parquet`). Subsequent runs should land in the same order of magnitude; an incremental run restricted to paper subsets runs in minutes.

**What the audit gives you:**
- Per-column firing-count delta between any two runs
- Per-paper sampling for top-changed columns
- Per-schema "papers with any match" totals
- Versioned `rules_snapshot.json` + `run_summary.json` committed to git for every run

See `outputs/extraction_runs/README.md` for usage.

After re-extraction:
- Refresh `outputs/literature_review_enriched.parquet` and `outputs/schema_extraction_evidence.csv` (auto)
- Regenerate `extraction_review_reference.md` per-schema HTML pages (manual step)
- Update validation pages (auto-deploys on next push to main)

---

## Outstanding from earlier (not blocking the meeting)

- Audit NamSor `origin_country` for other rare-surname mis-classifications (low score + US institution = high-likelihood candidates)
- Add Alex McInturf's `author_corrections` to `outputs/author_location_overrides.csv` once PR #11 merges
- Reconsider the validation UI's labelling of "Origin country" vs "Ethnicity" to reduce conflation (Alex's submission set both to "United States")
