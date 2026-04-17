#!/usr/bin/env python3
"""
Supplementary extraction for gear_target_species, imp_quantified, imp_is_bycatch.

Replaces the previous derived-without-evidence behaviour with:
- gear_target_species: filtered to real target species/groups (exclusions for
  gear/habitat modifiers that are captured by gear_* and eco_* elsewhere),
  with evidence rows for every capture (accepted and rejected) so reviewers
  can audit the filter.
- imp_quantified: still boolean, but now with evidence rows containing the
  actual quantitative statements (value, unit, direction, context) found.
- imp_is_bycatch: recomputed from the corrected gear_target_species.

Reuses the PDF index from extract_schema_columns.py.

Usage:
    python scripts/extract_target_species_quantified.py            # full run
    python scripts/extract_target_species_quantified.py --limit 50 # test
    python scripts/extract_target_species_quantified.py --resume   # continue
"""

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
EVIDENCE_PATH = PROJECT_ROOT / "outputs" / "schema_extraction_evidence.csv"
PDF_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PROGRESS_PATH = PROJECT_ROOT / "outputs" / ".target_quant_progress.json"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from extract_schema_columns import (
    build_pdf_index,
    _first_surname,
    _pick_best_pdf,
    extract_text_from_pdf,
    infer_is_bycatch,
)


# ---------------------------------------------------------------------------
# gear_target_species filters
# ---------------------------------------------------------------------------

_TARGET_CAPTURE_RE = re.compile(
    r"(?:targeting|target(?:ed)?\s+(?:species|catch)|"
    r"(\w+)\s+fishery|(\w+)\s+longline|(\w+)\s+trawl|"
    r"directed\s+at\s+(\w+))",
    re.IGNORECASE,
)

# Words already captured by gear_* columns
_GEAR_MODIFIER_EXCLUSIONS = {
    "bottom", "otter", "beam", "midwater", "surface",
    "drift", "set", "fixed", "passive", "active",
    "longline", "trawl", "gillnet", "seine", "purse",
    "trap", "hook", "handline",
    "commercial", "artisanal", "recreational", "sport", "industrial",
    "subsistence", "traditional",
}

# Words already captured by eco_* columns
_HABITAT_EXCLUSIONS = {
    "pelagic", "demersal", "deepwater", "coastal", "reef",
    "epipelagic", "mesopelagic", "bathypelagic", "abyssal",
    "mangrove", "seagrass", "kelp", "estuarine", "riverine",
    "intertidal", "inshore", "offshore", "nearshore", "neritic",
}

_COMMON_WORDS = {
    "the", "and", "for", "was", "were", "with", "from", "this", "that",
    "each", "all", "its", "our", "their", "using", "during", "research",
    "scientific", "important", "local", "historic", "line", "net", "fish",
    "water", "some", "other", "both", "these", "those", "there", "which",
    "atlantic", "pacific", "mediterranean", "caribbean",
    "new", "old", "first", "second", "large", "small",
}

_EXCLUSIONS = _GEAR_MODIFIER_EXCLUSIONS | _HABITAT_EXCLUSIONS | _COMMON_WORDS

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
    "bream", "cernier", "wreckfish", "eel", "eels", "conger",
    "sablefish", "halibut", "rockfish", "rockfishes", "flatfish",

    # Elasmobranch target groups
    "shark", "sharks", "ray", "rays", "skate", "skates",
    "dogfish", "catshark", "catsharks",
    "hammerhead", "hammerheads", "mako", "makos", "thresher", "threshers",
    "porbeagle", "spurdog",

    # Elasmobranch genus names
    "carcharhinus", "prionace", "isurus", "galeorhinus", "mustelus",
    "triakis", "squalus", "centrophorus", "scyliorhinus", "lamna",
    "alopias", "sphyrna", "rhinobatos", "raja", "dipturus", "amblyraja",
    "leucoraja", "bathyraja", "beringraja",

    # Broad target categories
    "groundfish", "pelagics", "demersals", "whitefish",
    "elasmobranchs", "chondrichthyans", "teleosts",
}


def _classify_rejection(word: str) -> str:
    """Return a reason code for why a word was rejected."""
    if word in _GEAR_MODIFIER_EXCLUSIONS:
        return "rejected:gear_modifier"
    if word in _HABITAT_EXCLUSIONS:
        return "rejected:habitat"
    if word in _COMMON_WORDS:
        return "rejected:common_word"
    if len(word) < 3:
        return "rejected:too_short"
    return "rejected:unknown"


def _context_around(text: str, start: int, window: int = 120) -> str:
    """Extract ~sentence-bounded context around a match."""
    lo = max(0, start - window)
    hi = min(len(text), start + window)
    while lo > 0 and text[lo] not in ".\n":
        lo -= 1
    while hi < len(text) and text[hi] not in ".\n":
        hi += 1
    return text[lo:hi].replace("\n", " ").strip()[:250]


def extract_target_species_evidence(text: str, lit_id: str) -> tuple[str | None, list[dict]]:
    """Extract target species with filtering and evidence rows.

    Returns:
        (gear_target_species value, list of evidence rows)
    """
    accepted: set[str] = set()
    evidence: list[dict] = []

    for m in _TARGET_CAPTURE_RE.finditer(text):
        for g in m.groups():
            if not g:
                continue
            word = g.lower()
            if len(word) < 2:
                continue

            context = _context_around(text, m.start())

            if word in _VALID_TARGET_GROUPS:
                accepted.add(word)
                evidence.append({
                    "literature_id": lit_id,
                    "title": "",
                    "column": "gear_target_species",
                    "binary": 1,
                    "total_freq": "1",
                    "raw_freq": "1",
                    "section": "accepted",
                    "term_count": "1",
                    "threshold": "1",
                    "matched_terms": word,
                    "matched_anchors": "",
                    "context": context,
                })
            else:
                evidence.append({
                    "literature_id": lit_id,
                    "title": "",
                    "column": "gear_target_species",
                    "binary": 0,
                    "total_freq": "0",
                    "raw_freq": "1",
                    "section": _classify_rejection(word),
                    "term_count": "1",
                    "threshold": "1",
                    "matched_terms": word,
                    "matched_anchors": "",
                    "context": context,
                })

    return (", ".join(sorted(accepted)) if accepted else None, evidence)


# ---------------------------------------------------------------------------
# imp_quantified patterns
# ---------------------------------------------------------------------------

_QUANT_PATTERNS = [
    # Percentages: "32%", "32.5 %"
    (re.compile(r"\b(?P<value>\d+\.?\d*)\s*(?P<unit>%)", re.IGNORECASE), "percentage"),
    # p-values: "p < 0.05", "p = 0.01"
    (re.compile(r"\bp\s*(?P<op>[<>=])\s*(?P<value>0?\.\d+)", re.IGNORECASE), "p-value"),
    # Confidence intervals: must have % prefix or "confidence interval" in full to avoid "ci." citation matches
    (re.compile(r"(?:95\s*%\s*CI|confidence interval)\s*[:=]?\s*(?P<value>[\d\.\-\s,]+)", re.IGNORECASE), "CI"),
    # Plus-minus: "mean ± SE"
    (re.compile(r"(?P<value>\d+\.?\d*)\s*±\s*(?P<error>\d+\.?\d*)\s*(?P<unit>\w+)?", re.IGNORECASE), "mean±error"),
    # Fold changes: "3-fold increase", "2.5 fold decrease"
    (re.compile(r"(?P<value>\d+\.?\d*)[-\s]*fold\s+(?P<direction>increase|decrease|higher|lower|change|reduction)", re.IGNORECASE), "fold_change"),
]


def extract_quantified_evidence(text: str, lit_id: str) -> tuple[bool, list[dict]]:
    """Extract quantified impact statements with evidence rows.

    Returns:
        (imp_quantified bool, list of evidence rows)
    """
    evidence: list[dict] = []
    for pattern, metric_type in _QUANT_PATTERNS:
        for m in pattern.finditer(text):
            context = _context_around(text, m.start())
            gd = m.groupdict()
            value = gd.get("value", "")
            unit = gd.get("unit", "") or ""
            direction = gd.get("direction", "") or ""
            op = gd.get("op", "") or ""
            error = gd.get("error", "") or ""

            matched = m.group(0).strip()
            if len(matched) > 50:
                matched = matched[:50] + "..."

            evidence.append({
                "literature_id": lit_id,
                "title": "",
                "column": "imp_quantified",
                "binary": 1,
                "total_freq": "1",
                "raw_freq": "1",
                "section": metric_type,
                "term_count": "1",
                "threshold": "1",
                "matched_terms": matched,
                "matched_anchors": (op + error + direction).strip(),
                "context": context,
            })

    return (len(evidence) > 0, evidence)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process first N papers only")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    print("Building PDF index...")
    pdf_index = build_pdf_index(PDF_DIR)
    print(f"  {sum(len(v) for v in pdf_index.values())} PDFs indexed")

    print("Loading parquet...")
    df = pd.read_parquet(
        PARQUET_PATH,
        columns=["literature_id", "year", "authors", "title", "pr_bycatch"],
    )

    processed = set()
    if args.resume and PROGRESS_PATH.exists():
        with open(PROGRESS_PATH) as f:
            processed = set(json.load(f).get("processed", []))
        print(f"  Resuming: {len(processed)} already done")

    # Map papers to PDFs
    paper_pdfs: list[tuple[str, Path, int]] = []
    for _, row in df.iterrows():
        lid_raw = row.get("literature_id")
        if lid_raw is None or (isinstance(lid_raw, float) and math.isnan(lid_raw)):
            continue
        lit_id = str(int(float(lid_raw)))
        if lit_id in processed:
            continue
        authors = row.get("authors")
        year_raw = row.get("year")
        title = row.get("title") or ""
        pr_bycatch = int(row.get("pr_bycatch") or 0)
        if not authors or pd.isna(year_raw):
            continue
        year = int(year_raw)
        surname = _first_surname(authors)
        if not surname:
            continue
        candidates = pdf_index.get((surname, year), [])
        best_pdf = _pick_best_pdf(candidates, title)
        if best_pdf:
            paper_pdfs.append((lit_id, best_pdf, pr_bycatch))

    if args.limit:
        paper_pdfs = paper_pdfs[: args.limit]

    print(f"Processing {len(paper_pdfs)} papers...")

    # Collect updates keyed by lit_id
    target_updates: dict[str, str | None] = {}
    quant_updates: dict[str, bool] = {}
    bycatch_updates: dict[str, bool | None] = {}
    all_evidence: list[dict] = []
    count = 0

    for lit_id, pdf_path, pr_bycatch in paper_pdfs:
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            continue

        # Extract
        target_value, target_ev = extract_target_species_evidence(text, lit_id)
        quant_bool, quant_ev = extract_quantified_evidence(text, lit_id)

        # Recompute is_bycatch with filtered target
        is_bycatch = infer_is_bycatch(pr_bycatch, target_value)

        target_updates[lit_id] = target_value
        quant_updates[lit_id] = quant_bool
        bycatch_updates[lit_id] = is_bycatch

        all_evidence.extend(target_ev)
        all_evidence.extend(quant_ev)

        processed.add(lit_id)
        count += 1

        if count % 500 == 0:
            print(f"  {count}/{len(paper_pdfs)} papers, {len(all_evidence)} evidence rows")
            with open(PROGRESS_PATH, "w") as f:
                json.dump({"processed": sorted(processed)}, f)

    with open(PROGRESS_PATH, "w") as f:
        json.dump({"processed": sorted(processed)}, f)

    print(f"\nProcessed {count} papers.")
    sp_ev = sum(1 for e in all_evidence if e["column"] == "gear_target_species")
    sp_accepted = sum(1 for e in all_evidence if e["column"] == "gear_target_species" and e["binary"] == 1)
    q_ev = sum(1 for e in all_evidence if e["column"] == "imp_quantified")
    print(f"  gear_target_species: {sp_ev} evidence rows ({sp_accepted} accepted, {sp_ev - sp_accepted} rejected)")
    print(f"  imp_quantified: {q_ev} evidence rows")
    print(f"  Papers with accepted target: {sum(1 for v in target_updates.values() if v)}")
    print(f"  Papers with imp_quantified=True: {sum(1 for v in quant_updates.values() if v)}")
    print(f"  Papers with imp_is_bycatch=True: {sum(1 for v in bycatch_updates.values() if v is True)}")

    # --- Update parquet ---
    print("\nUpdating parquet...")
    table = pq.read_table(PARQUET_PATH)
    lit_ids = []
    for v in table.column("literature_id"):
        raw = v.as_py()
        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            lit_ids.append("")
        else:
            lit_ids.append(str(int(float(raw))))

    # gear_target_species (string)
    if "gear_target_species" in table.column_names:
        new_vals = []
        for i, lid in enumerate(lit_ids):
            if lid in target_updates:
                new_vals.append(target_updates[lid])
            else:
                new_vals.append(table.column("gear_target_species")[i].as_py())
        idx = table.column_names.index("gear_target_species")
        table = table.set_column(idx, "gear_target_species", pa.array(new_vals, type=pa.string()))

    # imp_quantified (bool)
    if "imp_quantified" in table.column_names:
        new_vals = []
        for i, lid in enumerate(lit_ids):
            if lid in quant_updates:
                new_vals.append(quant_updates[lid])
            else:
                new_vals.append(table.column("imp_quantified")[i].as_py())
        idx = table.column_names.index("imp_quantified")
        table = table.set_column(idx, "imp_quantified", pa.array(new_vals, type=pa.bool_()))

    # imp_is_bycatch (bool, nullable)
    if "imp_is_bycatch" in table.column_names:
        new_vals = []
        for i, lid in enumerate(lit_ids):
            if lid in bycatch_updates:
                new_vals.append(bycatch_updates[lid])
            else:
                new_vals.append(table.column("imp_is_bycatch")[i].as_py())
        idx = table.column_names.index("imp_is_bycatch")
        table = table.set_column(idx, "imp_is_bycatch", pa.array(new_vals, type=pa.bool_()))

    pq.write_table(table, PARQUET_PATH)
    print(f"  Parquet updated.")

    # --- Append evidence ---
    if all_evidence:
        print(f"Appending {len(all_evidence)} evidence rows to {EVIDENCE_PATH}...")
        cols = [
            "literature_id", "title", "column", "binary", "total_freq",
            "raw_freq", "section", "term_count", "threshold",
            "matched_terms", "matched_anchors", "context",
        ]
        with open(EVIDENCE_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            for ev in all_evidence:
                w.writerow(ev)

    print("\nDone. Run generate_validation_pages.py to update the UI.")


if __name__ == "__main__":
    main()
