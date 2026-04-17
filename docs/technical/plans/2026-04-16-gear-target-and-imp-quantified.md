# Plan: Fix gear_target_species and Upgrade imp_quantified

**Goal:** Replace the two derived-without-evidence columns with properly-logged extractions. Stop capturing junk in `gear_target_species`; start capturing values+context for `imp_quantified`.

**Context:** These are two of three "ticked without (i)" issues from the validation UI. The third (`imp_is_bycatch`) is derived from `gear_target_species` + `pr_bycatch`, so it'll improve automatically once (1) is fixed.

---

## Part 1: Fix `gear_target_species`

### Current behaviour

In `scripts/extract_schema_columns.py` line ~694:

```python
_TARGET_SPECIES_RE = re.compile(
    r"(?:targeting|target(?:ed)?\s+(?:species|catch)|"
    r"(\w+)\s+fishery|(\w+)\s+longline|(\w+)\s+trawl|"
    r"directed\s+at\s+(\w+))",
    re.IGNORECASE,
)
```

The `(\w+)` capture groups grab any word before "fishery/longline/trawl", producing noise like `bottom`, `otter`, `commercial`, `using`, `during`, `research`.

### Fix

Two changes:

**1.1 — Exclusion list for gear and habitat modifiers.** These words are already captured by `gear_*` and `eco_*` columns, so they should not appear in `gear_target_species`:

```python
_GEAR_MODIFIER_EXCLUSIONS = {
    "bottom", "otter", "beam", "pelagic", "demersal", "deepwater",
    "midwater", "surface", "drift", "set", "fixed", "passive", "active",
    "longline", "trawl", "gillnet", "seine", "purse", "trap", "hook",
    "commercial", "artisanal", "recreational", "sport", "industrial",
    "subsistence", "traditional", "handline",
}

_COMMON_WORDS = {
    "the", "and", "for", "was", "were", "with", "from", "this", "that",
    "each", "all", "its", "our", "their", "using", "during", "research",
    "scientific", "important", "local", "historic", "line", "net", "fish",
    "water", "some",
}

_EXCLUSIONS = _GEAR_MODIFIER_EXCLUSIONS | _COMMON_WORDS
```

**1.2 — Inclusion list (curated target-group vocabulary).** Only accept captures that match known target groups:

```python
_VALID_TARGET_GROUPS = {
    # Teleost target species / groups
    "tuna", "tunas", "swordfish", "marlin", "billfish", "billfishes",
    "mahi", "dorado", "dolphinfish", "wahoo", "snapper", "snappers",
    "grouper", "groupers", "cod", "haddock", "hake", "pollock",
    "mackerel", "herring", "sardine", "anchovy", "anchovies",
    "salmon", "halibut", "sole", "flounder", "plaice",
    "monkfish", "anglerfish", "shrimp", "prawn", "prawns",
    "lobster", "crab", "squid", "octopus", "scallop",
    "grenadier", "orange roughy", "toothfish", "patagonian toothfish",
    "bream", "sea bream", "cernier", "wreckfish",

    # Elasmobranch target groups (when sharks/rays are the target, not bycatch)
    "shark", "sharks", "ray", "rays", "skate", "skates",
    "dogfish", "catshark", "catsharks",
    "hammerhead", "hammerheads", "mako", "makos", "thresher", "threshers",
    "porbeagle", "spiny dogfish", "spurdog",

    # Elasmobranch genus names (valid targets for directed fisheries)
    "carcharhinus", "prionace", "isurus", "galeorhinus", "mustelus",
    "triakis", "squalus", "centrophorus", "scyliorhinus", "lamna",
    "alopias", "sphyrna", "rhinobatos", "raja", "dipturus", "amblyraja",
    "leucoraja", "bathyraja", "beringraja",

    # Broad target categories
    "groundfish", "pelagics", "demersals", "whitefish",
    "elasmobranchs", "chondrichthyans", "teleosts",
}
```

Simon to review and expand after first-run output. DRG to review Mediterranean/European targets specifically.

### Updated extraction function

```python
def extract_target_species(text: str) -> str | None:
    """Extract target species/group names from gear-related context.

    Filters out gear type modifiers (captured by gear_*) and habitat
    modifiers (captured by eco_*), keeping only recognised target groups.

    Returns:
        Comma-separated target names, or None.
    """
    found: set[str] = set()
    for m in _TARGET_SPECIES_RE.finditer(text):
        for g in m.groups():
            if not g or len(g) < 3:
                continue
            w = g.lower()
            if w in _EXCLUSIONS:
                continue
            if w in _VALID_TARGET_GROUPS:
                found.add(w)
    return ", ".join(sorted(found)) if found else None
```

### Evidence logging (accepted + rejected)

Emit evidence rows for **every capture**, not just accepted ones. This lets reviewers see what we're filtering out and propose additions to the inclusion list.

Each match produces an evidence row:
- `column`: `gear_target_species`
- `matched_terms`: the captured word
- `context`: surrounding sentence
- `binary`: 1 if accepted (in `_VALID_TARGET_GROUPS`), 0 if rejected
- `section`: "accepted" or "rejected:gear_modifier" or "rejected:common_word" or "rejected:unknown"

This makes the filter inspectable. A reviewer looking at the validation page sees both the accepted targets and a separate "candidates rejected" panel showing what was filtered and why. They can then propose moving specific words from the exclusion list to the inclusion list (or vice versa) via the rule feedback controls.

This addresses the false-negative problem: without this, any word not in the inclusion list would silently disappear, making it impossible to audit whether the filter is too strict.

### Impact

Expected results based on current data:
- Drops junk values like `bottom (391×)`, `otter (154×)`, `pelagic (86×)` — these go to zero
- Keeps useful values: `shrimp`, `tuna`, `shark`, `prawn`, `tuna`, `snapper`, `mackerel`, etc.
- Expected non-null count drops from ~6,750 to ~1,000-1,500 papers

### Downstream: `imp_is_bycatch`

No code change needed. The `infer_is_bycatch()` function already checks whether `gear_target_species` contains non-elasmobranch words. With the filtered list, it will now work correctly:
- `pr_bycatch=1` + `gear_target_species="tuna"` → `imp_is_bycatch=True` (sharks are bycatch)
- `pr_bycatch=1` + `gear_target_species="shark"` → `imp_is_bycatch=None` (sharks are target)

---

## Part 2: Upgrade `imp_quantified` to capture values

### Current behaviour

In `extract_schema_columns.py` line ~791:

```python
_QUANT_RE = re.compile(
    r"\d+\.?\d*\s*%|"
    r"\d+\.\d+|"
    r"(?:CI|confidence interval)\s*[:=]|"
    r"p\s*[<>=]\s*0\.\d+|"
    r"±\s*\d+",
    re.IGNORECASE,
)

def assess_impact_quantified(text: str) -> bool:
    return bool(_QUANT_RE.search(text))
```

Returns True for 17,249 papers — trivially true for most empirical papers. No values, no units, no context stored.

### Fix

**2.1 — Enrich the regex with named groups for value/unit/metric:**

```python
_QUANT_PATTERNS = [
    # Percentages
    re.compile(r"\b(?P<value>\d+\.?\d*)\s*(?P<unit>%)", re.IGNORECASE),
    # p-values
    re.compile(r"\bp\s*(?P<op>[<>=])\s*(?P<value>0?\.\d+)", re.IGNORECASE),
    # Confidence intervals
    re.compile(r"(?:CI|confidence interval)\s*[:=]?\s*(?P<value>[\d\.\-\s,%]+)", re.IGNORECASE),
    # Plus-minus (mean ± SE)
    re.compile(r"(?P<value>\d+\.?\d*)\s*±\s*(?P<error>\d+\.?\d*)\s*(?P<unit>\w+)?", re.IGNORECASE),
    # Fold changes
    re.compile(r"(?P<value>\d+\.?\d*)[-\s]*fold\s+(?P<direction>increase|decrease|higher|lower|change)", re.IGNORECASE),
]
```

**2.2 — New function returning list of structured quants with context:**

```python
def extract_quantified_impacts(text: str) -> list[dict]:
    """Extract quantitative impact statements from text.

    Returns:
        List of dicts with keys: value, unit, metric, direction, context.
    """
    results = []
    for pattern in _QUANT_PATTERNS:
        for m in pattern.finditer(text):
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 100)
            context = text[start:end].replace("\n", " ").strip()
            # Extend to sentence boundaries
            results.append({
                "value": m.groupdict().get("value", ""),
                "unit": m.groupdict().get("unit", ""),
                "direction": m.groupdict().get("direction", ""),
                "matched": m.group(0),
                "context": context[:250],
            })
    return results
```

**2.3 — Keep `imp_quantified` as boolean** (True if any quantified statement found) **but emit evidence rows** for each value found. Each evidence row: column=`imp_quantified`, matched_terms=`value unit direction` (e.g. "32 % decrease"), context=sentence.

### Impact

- Validators can now see and correct specific quantitative claims, not just a flag
- Downstream analysis (e.g. meta-analysis of effect sizes) has structured inputs
- Evidence CSV grows by ~100-200K rows (estimate: ~10-15 quant mentions per paper × 17K papers)

---

## Part 3: Implementation approach

Both fixes are in-script extraction changes, not requiring database schema migration. Can be applied in one of two ways:

**Option A — Re-run full schema extraction:**
Modify `extract_schema_columns.py`, run the full pipeline on 18,065 PDFs. Takes ~25-40 minutes. Risks: re-extraction may slightly change other Tier 1 results if any state changed.

**Option B — Supplementary pass (preferred):**
Write a new script that only re-extracts these two columns, using the existing PDF text extraction. Leaves other Tier 1 columns untouched. Takes ~15-25 minutes. Safer.

Recommend **Option B**. Write `scripts/extract_target_species_quantified.py` that:
1. Loads parquet
2. For each paper with a PDF: extract text, run updated `extract_target_species()` and `extract_quantified_impacts()`
3. Updates `gear_target_species`, `imp_quantified`, `imp_is_bycatch` columns in parquet
4. Appends evidence rows to `schema_extraction_evidence.csv`

Then regenerate validation pages.

---

## Deliverables

1. `scripts/extract_target_species_quantified.py` — new script
2. Updated `outputs/literature_review_enriched.parquet` — 3 columns refreshed
3. Extended `outputs/schema_extraction_evidence.csv` — ~100-200K new rows
4. Regenerated validation pages (28,952 files)
5. Updated `docs/schema_proposals/gear_proposal.md` and `impact_proposal.md` with new behaviour

---

## Validation

- Sample 20 papers with previously-junk `gear_target_species`: verify new values are real target groups
- Sample 20 papers with previously-True `imp_quantified`: verify evidence rows have plausible value/unit/context
- Check `imp_is_bycatch` flips in sensible ways for bycatch studies
