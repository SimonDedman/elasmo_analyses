# Proposed Schema: Depth

**Status:** Active — regex extraction from full PDF text; evidence rows added 2026-04-16; regex tightened 2026-04-21
**Column prefix:** `depth_`
**Team lead:** Chris Mull
**Source:** Regex patterns and evidence-row emission in `scripts/extract_schema_columns.py` (moved here 2026-04-21 from the separate secondary pass)

## Purpose

Capture the study depth range reported in each paper. Enables analyses like "are deep-water species systematically under-studied?" or "how does technique choice vary across depth zones?" Three columns are produced: a human-readable text summary, and parsed numeric minimum and maximum depths in metres.

## Columns

| Column | Type | Description |
|--------|------|-------------|
| `depth_range` | `str` | Stated depth range as extracted text, e.g., `"10–200 m"`, `">500 m"`, `"150 m"` |
| `depth_min_m` | `float` | Smallest depth value found (metres). `NaN` if no depth stated. |
| `depth_max_m` | `float` | Largest depth value found (metres). `NaN` if no depth stated. |

For single-value statements (e.g., "depth of 500 m"), both `depth_min_m` and `depth_max_m` are set to that value.

## Extraction Method

### Script

`scripts/extract_schema_columns.py` (regex extraction); `scripts/extract_species_techniques_from_pdfs.py` (evidence row writing, added 2026-04-16).

### Regex Patterns (tightened 2026-04-21)

Both range and single-value patterns now require a bathymetric-context word within ~60 characters before the numeric match. The prior permissive prefix `[><~≈]?\s*` was empty-matchable and captured body measurements (e.g., basking-shark total length "5–8 m") as depth values.

**Context prefix** (required before every match):

```
depth(s)?|bathym(etric|etry)?|benthic|demersal zone|water column|
sea floor|below (the) surface|
caught (at|in)|captured (at|in)|collected (at|in|from)|
sampled (at|in|from)|tagged (at|in)|set (at|to)|fished (at|in)|
deployed (at|to|in)|submerged|lowered to|down to|
recorded (at|to|from)|hook(s|ed) (at|to|in)|
longline (at|to)|trawl(ed) (at|between|from)|dive(s|d) to|
CTD|vertical profile|descended to
```

**Range pattern:** `<CONTEXT>[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*(-|–|—|\s+to\s+)\s*(\d+(?:\.\d+)?)\s*(m\b|meters?\b|metres?\b)`

**Single pattern** (only attempted if range failed, to avoid double-counting endpoints): `<CONTEXT>[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*(m\b|meters?\b|metres?\b)`

When multiple depth values are found in a paper, `depth_min_m` takes the smallest and `depth_max_m` takes the largest across all matches. `depth_range` is set to the corresponding `"min–max m"` text (or a single value if min = max).

**Smoke-test cases (2026-04-21):**

| Text | Extracted |
|---|---|
| "Basking sharks reaching 5 to 8 m in total length" | — (body measurement rejected) |
| "CTD casts deployed at depths of 50–200 m" | 50–200 m |
| "7 m basking shark diving to a maximum depth of 350 m" | 350 m (body size rejected, depth captured) |

## Evidence

Since 2026-04-16, every paper with a depth match generates a row in `outputs/schema_extraction_evidence.csv`:

| Field | Content |
|-------|---------|
| `literature_id` | Paper identifier |
| `column` | `depth_range`, `depth_min_m`, or `depth_max_m` |
| `matched_terms` | The regex-matched text fragment |
| `frequency` | Number of depth expressions found in the paper |
| `context` | Sentence containing the first depth match, for manual verification |

## Known Issues and Limitations

1. **Residual ambiguous "m":** The tightened 2026-04-21 regex requires a bathymetric-context word but false positives can still occur when a depth-sounding verb (e.g. "deployed at 10 m") refers to transect position rather than water depth. Review the evidence `context` sentence to confirm. Older papers using fathoms are not converted (see (5) below).
2. **Depth not always stated:** Many papers do not report a study depth explicitly. These papers will have `NaN` in all three columns. A `NaN` does not imply a shallow-water study.
3. **Relative qualifiers:** Statements like ">200 m" are captured in `depth_range` as text but `depth_min_m` and `depth_max_m` are set to the numeric value (200) without the qualifier. The qualifier is preserved only in the `depth_range` string.
4. **Multiple study sites at different depths:** The current pipeline takes the global minimum and maximum across all depth mentions in a paper. A paper comparing 10 m and 800 m sites will yield `depth_min_m = 10`, `depth_max_m = 800` — which faithfully represents the range studied but does not distinguish between a gradient study and a comparison of discrete sites.
5. **Unit conversion:** All depths are assumed to be in metres. Fathom or foot units are not currently converted. These are rare in modern elasmobranch literature but may occur in older papers.

## Relationship to `eco_` Depth Zone Columns

The `eco_` schema contains categorical depth zone columns (`eco_epipelagic`, `eco_mesopelagic`, `eco_bathypelagic`, `eco_deepwater`) derived from keyword matching. The `depth_*` columns complement these with precise numeric values where reported. Both are useful:

- Use `depth_min_m` / `depth_max_m` for continuous depth analyses and scatterplots.
- Use `eco_deepwater`, `eco_mesopelagic` etc. for quick categorical filters, including papers that mention a depth zone without stating an explicit depth in metres.

## Coverage Expectations

Based on the elasmobranch literature:

- Tagging, telemetry, and habitat use papers routinely report depth ranges — expected high `depth_*` coverage (~30–50% of papers).
- Fisheries and bycatch papers often report gear set depth rather than species depth — these will be captured but represent gear depth, not habitat depth.
- Taxonomy, genetics, and review papers often do not report a study depth — `NaN` is expected for these.

## Validation

Evidence review pages for depth extraction are linked from the extraction review dashboard:

**<https://simondedman.github.io/elasmo_analyses/validate/>**

Review pages show context sentences for all depth matches, flagged cases where the "m" unit appears in a non-depth context, and the distribution of `depth_min_m` and `depth_max_m` values across the corpus.

## Discussion Points

1. **Elasmobranch proximity check:** Other schema columns (e.g., `eco_pelagic`) include a proximity check requiring an elasmobranch term within N words of the matched keyword. Adding a similar check to depth extraction would reduce false positives from methods sections reporting transect lengths or tank dimensions.
2. **Gear depth vs. habitat depth disambiguation:** Consider adding a `depth_context` text column to flag whether the matched depth appears to describe gear set depth, habitat depth, or dive depth. This would require a small keyword-context classifier.
3. **Fathom/foot conversion:** A pre-processing step to convert imperial depth units in older papers would improve coverage for pre-1980 literature.

---
*Draft created: 2026-04-16. Evidence row writing added 2026-04-16 via `extract_species_techniques_from_pdfs.py`.*
