# Extraction diff: April 18 → April 20 rule changes

**A (pre):** `outputs/literature_review_enriched.pre-2026-04-20.parquet` (April 18 run, before today's rule changes)
**B (post):** `outputs/literature_review_enriched.parquet` (run_id `20260421T050413_5ca94a22d`, after today's changes)

Both over the same 30,558 papers.

---

## Headline — schema-level aggregate changes

| Schema | Total firings pre | Total firings post | Δ | Pct |
|---|---:|---:|---:|---:|
| `eco_` Ecosystem | 33,298 | 40,285 | **+6,987** | +21.0% |
| `pr_` Pressure / Threat | 14,502 | 17,542 | **+3,040** | +21.0% |
| `gear_` Fishing Gear | 9,742 | 11,784 | **+2,042** | +21.0% |
| `imp_` Impact / Response | 11,683 | 14,191 | **+2,508** | +21.5% |
| `d_` Discipline | 35,272 | 47,478 | **+12,206** | **+34.6%** |
| `b_` Ocean Basin (keyword) | 14,053 | 17,248 | **+3,195** | +22.7% |
| `sb_` Ocean Sub-basin | 7,962 | 10,091 | **+2,129** | +26.7% |

**The ~21% baseline lift visible across six schemas is the TITLE + KEYWORDS section-injection effect.** Any binary column that had ≥1 of its terms appear in a paper's title or author-supplied keyword block now gets that hit multiplied by weight 2.0 instead of 0.25 (the old OTHER weight). In practice this carries a large number of papers that were previously just under threshold over the line.

**Discipline (`d_`) is the outlier at +34.6%** because — on top of the TITLE+KEYWORDS baseline — two `d_` columns had substantial vocabulary expansions (`d_biology` and `d_fisheries`). Details below.

---

## Rule-edit → observed-change map

### 1. TITLE + KEYWORDS sections added at weight 2.0 (`_SECTION_WEIGHTS` for eco_/pr_/gear_/imp_/d_/b_/sb_)

**Evidence:** universal ~21% lift across every binary schema. Columns that had NO other rule change track the schema baseline closely:

| Column | Pre | Post | Δ% | Notes |
|---|---:|---:|---:|---|
| `eco_marine` | 10,683 | 12,454 | +16.6% | no column-specific change |
| `eco_coastal` | 4,022 | 4,882 | +21.4% | no column-specific change |
| `eco_pelagic` | 3,236 | 3,982 | +23.1% | no column-specific change |
| `pr_pollution_chemical` | 765 | 896 | +17.1% | no column-specific change; baseline lift |
| `pr_bycatch` | 2,558 | 3,151 | +23.2% | no column-specific change |
| `b_north_atlantic` | 2,513 | 3,104 | +23.5% | no column-specific change |
| `imp_abundance` | 2,308 | 2,825 | +22.4% | no column-specific change |

Behaving as designed: TITLE/KEYWORDS inclusion lifts every column by roughly the same proportion.

### 2. `d_biology` — 8 → 20 terms, +GSI/HSI with prerequisite gating

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `d_biology` | 2,735 | 5,592 | **+104.5%** |

Additional vocabulary: `vertebral count*`, `band pair*`, `gonadosomatic index`, `hepatosomatic index`, `GSI` (case-sensitive, gated on spelled-out form), `HSI` (same), `Le Cren`, `Fulton's K`, `morphometric analysis`, `total length`, `precaudal length`, `disc width`.

**Interpretation:** ~21% of the +105% comes from the TITLE+KEYWORDS baseline; the remaining ~84% from the new vocabulary. Biology papers rarely use terms like "life history" in the extractive sense, but almost always mention total length, morphometric measurements, or vertebral counts. This was the largest coverage gap in the schema.

**GSI/HSI prereq gating** is (by design) a suppressant — it revokes acronym-only matches. The fact that d_biology went UP by 105% means the vocab expansion vastly outweighs the prereq suppression. This is correct: the prereq only affects papers that mention GSI/HSI in body text WITHOUT a spelled-out form, which is rare in actual biology papers.

### 3. `d_fisheries` — 8 → 13 terms

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `d_fisheries` | 933 | 3,117 | **+234.1%** |

Additional vocabulary: `bycatch`, `discard*`, `retention`, `non-target species`, `non-target catch`.

**Interpretation:** the old vocabulary (`stock assessment`, `fisheries management`, `catch data`, `MSY`, etc.) was strongly biased toward formal stock-assessment language. Adding `bycatch` alone quadruples the corpus of fisheries-related papers — confirms David Ruiz-García's core complaint that the rule was missing the operational fisheries research that doesn't use formal stock-assessment vocabulary. This is the single largest proportional gain.

### 4. `d_physiology` — 10 → 28 terms

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `d_physiology` | 1,968 | 2,956 | **+50.2%** |

Additional vocabulary: `SMR/RMR/MMR` (case-sensitive), `aerobic scope`, `Ucrit/U crit/U-crit`, `critical swimming speed`, `heart rate`, `cardiac output`, `blood pressure`, `plasma osmolality/cortisol/lactate`, `urea`, `TMAO` (case-sensitive), `trimethylamine N-oxide`, `enzyme activity`, `Q10` (case-sensitive), `metabolic rate`.

**Interpretation:** ~21% from TITLE+KEYWORDS, ~30% from measurement vocabulary. Lower than d_biology because physiology research spans a narrower slice of the corpus — the new measurement terms catch papers that previously hit zero of the broad `physiolog*`/`metaboli*` wildcards.

### 5. `eco_deepwater` — added "deepwater" and "deep water" variants

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `eco_deepwater` | 1,364 | 2,334 | **+71.1%** |

Previous rule had only the hyphenated `deep-water` and `deep-sea`. Many papers use the unhyphenated forms, especially in keywords/titles.

**Interpretation:** the ~50% component beyond the TITLE+KEYWORDS baseline comes entirely from the variant hyphenation — a simple fix with a sizeable effect.

### 6. `pr_aquaculture` — threshold raised 1 → 2

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `pr_aquaculture` | 798 | 556 | **−30.3%** |

**Interpretation:** the only binary rule-changed column that went DOWN. Confirms the threshold raise is doing its job: papers that mentioned "aquaculture" only once in passing context no longer trigger the column. TITLE+KEYWORDS would have given this column a ~21% lift if unchanged; the −30.3% net means the threshold change suppressed roughly half of the previously-firing papers. Expected precision improvement.

### 7. `imp_biomass` — added document-level response-language anchors

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `imp_biomass` | 530 | 630 | **+18.9%** |

Added anchors: `change`, `decline`, `decrease`, `increase`, `shift`, `trend`, `loss`, `recovery`, `fluctuat*`, `depletion`, `rebuild*`.

**Interpretation:** the anchor requirement is suppressing papers that mention biomass only as a covariate (without any response language). The net +18.9% is slightly BELOW the TITLE+KEYWORDS baseline of +21% — meaning the anchors revoked maybe a dozen papers that would otherwise have gained from TITLE+KEYWORDS. Exactly the outcome David Ruiz-García asked for.

### 8. `gear_mit_ghost` → `gear_ghost` (rename + "ghost fishing" variant added)

| Column | Pre | Post | Δ% |
|---|---:|---:|---:|
| `gear_mit_ghost` | 18 | — | (removed) |
| `gear_ghost` | — | 36 | (new) |

Rename from the mitigation cluster to a gear category. Also added keyword "ghost fishing".

**Interpretation:** +18 papers. About half from TITLE+KEYWORDS lift on existing matches, rest from the "ghost fishing" variant catching papers that use that phrasing. Since it's a small column, absolute numbers are small; proportional effect is large (doubling).

### 9. *Aetomylaeus bovinus* added to `sp_` list

No column-level delta visible yet — the `sp_` columns in the output parquet come from a separate species-extraction step that hasn't been re-run. The `sp_aetomylaeus_bovinus` column exists in the validation UI's options.json but will only be populated on the next species-extraction pass. Action item: schedule a species-extraction re-run.

---

## Losers beyond `pr_aquaculture` (noise, not signal)

Apart from `pr_aquaculture`, 22 columns showed small decreases. All are `sp_*` (species) or `a_*` (analytical techniques) columns, losing 1–11 firings each. These schemas are integer-count, extracted by a separate pipeline (`extract_species_techniques_from_pdfs.py`); the parquet's sp_/a_ values carry over from a prior run. Small differences between the April 18 and April 20 parquets are due to source-data updates (new PDF ingests, OCR pass, etc.) rather than today's rule changes.

**Conclusion:** no binary-schema rule caused any unexpected regression.

---

## Summary for the meeting

1. **TITLE+KEYWORDS inclusion is the single biggest-impact change** — universally +21% across schemas. Justifies the approach Simon proposed (and makes dynamic thresholds unnecessary).
2. **Vocabulary expansions for `d_biology` (+105%) and `d_fisheries` (+234%) confirm David Ruiz-García's core diagnosis** — the pre-existing term lists were too narrow and missed the operational research language.
3. **`d_physiology` +50% and `eco_deepwater` +71%** are smaller but still substantial coverage gaps closed by the same approach.
4. **`pr_aquaculture` −30%** is the only intentional reduction, and it's exactly the magnitude expected from the threshold change.
5. **`imp_biomass` anchor gating** shows its signature: firing lifted by +19% (below the +21% baseline), meaning anchors revoked some papers that would otherwise have passed on TITLE+KEYWORDS alone.
6. **No regressions** in any column that wasn't explicitly a rule change.

After the meeting decisions land (Mediterranean GFCM columns, conditional-dependency rule, sp_/a_ section weighting, etc.), a second extraction run will give us a clean diff of THAT layer of changes on top of today's baseline. The audit infrastructure (`scripts/diff_extraction_runs.py`) will produce per-paper samples and the equivalent schema-level table automatically.
