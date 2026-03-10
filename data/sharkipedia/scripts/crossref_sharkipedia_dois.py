"""Cross-reference Sharkipedia references against EEA literature database.

Matches on DOI (where available) and fuzzy title matching for references
without DOIs. Produces overlap and Sharkipedia-only CSVs plus summary stats.
"""

import csv
import re
import unicodedata
from pathlib import Path

import duckdb
import openpyxl

# -----------------------------------------------------------------
# Paths
# -----------------------------------------------------------------
BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
SHARKIPEDIA_XLSX = BASE / "data/sharkipedia/Sharkipedia-References-v1.2-22-06-17.xlsx"
DUCKDB_PATH = BASE / "outputs/literature_review.duckdb"
OUT_DIR = BASE / "data/sharkipedia"

OUT_OVERLAP = OUT_DIR / "doi_crossref_overlap.csv"
OUT_SHARK_ONLY = OUT_DIR / "doi_crossref_sharkipedia_only.csv"
OUT_SUMMARY = OUT_DIR / "doi_crossref_summary.txt"

DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s,;)\]]+)")


# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------
def normalise_doi(raw: str) -> str:
    """Lowercase, strip whitespace, trailing dots/slashes."""
    d = raw.strip().lower()
    d = d.rstrip("./")
    return d


def normalise_title(title: str) -> str:
    """Strip to lowercase ASCII alphanumerics for fuzzy comparison."""
    t = title.lower()
    # Decompose unicode and drop combining marks
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    # Keep only alphanumeric and spaces
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_title_from_source(source: str) -> str | None:
    """Extract title from Sharkipedia-style formatted reference string.

    Expected format: AUTHOR(S) (YEAR) Title. Journal/Publisher ...
    """
    if not source:
        return None
    # Match up to the year in parentheses, then grab text until next period
    # that is followed by a space and uppercase or end-of-string
    m = re.match(r"^[^(]+\(\d{4}[a-z]?\)\s*(.+)", source)
    if not m:
        return None
    rest = m.group(1)
    # Title typically ends at first sentence-ending period
    # But titles can contain parenthetical species names with periods
    # Use first period followed by space + uppercase or journal-style pattern
    # Simple heuristic: split on ". " and take first segment
    parts = re.split(r"\.\s+(?=[A-Z])", rest, maxsplit=1)
    title = parts[0].rstrip(".")
    return title if len(title) > 10 else None


def extract_year_from_source(source: str) -> int | None:
    """Extract publication year from reference string."""
    if not source:
        return None
    m = re.search(r"\((\d{4})[a-z]?\)", source)
    return int(m.group(1)) if m else None


# -----------------------------------------------------------------
# 1. Load Sharkipedia references
# -----------------------------------------------------------------
print("Loading Sharkipedia references...")
wb = openpyxl.load_workbook(SHARKIPEDIA_XLSX, read_only=True)
ws = wb["Sheet1"]

shark_refs: list[dict] = []
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0:
        continue  # skip header
    ref_id, source = row
    doi_match = DOI_RE.search(source or "")
    doi = normalise_doi(doi_match.group(1)) if doi_match else ""
    title = extract_title_from_source(source)
    year = extract_year_from_source(source)
    shark_refs.append({
        "reference_id": ref_id,
        "source": source or "",
        "doi": doi,
        "title_raw": title or "",
        "title_norm": normalise_title(title) if title else "",
        "year": year,
    })

wb.close()
print(f"  Loaded {len(shark_refs)} Sharkipedia references")
print(f"  With DOI: {sum(1 for r in shark_refs if r['doi'])}")
print(f"  With extractable title: {sum(1 for r in shark_refs if r['title_norm'])}")

# Build lookup structures for Sharkipedia
shark_doi_set = {r["doi"] for r in shark_refs if r["doi"]}

# -----------------------------------------------------------------
# 2. Load our literature database
# -----------------------------------------------------------------
print("\nLoading EEA literature database...")
con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
our_papers = con.execute(
    "SELECT doi, title, year, authors, literature_id FROM literature_review"
).fetchall()
con.close()

print(f"  Loaded {len(our_papers)} papers")

# Build DOI lookup (doi -> paper info)
our_doi_map: dict[str, dict] = {}
# Build title lookup (normalised_title -> list of paper info, keyed by year)
our_title_map: dict[str, list[dict]] = {}

for doi_raw, title, year, authors, lit_id in our_papers:
    doi = normalise_doi(doi_raw) if doi_raw else ""
    info = {
        "doi": doi,
        "title": title or "",
        "year": year,
        "authors": authors or "",
        "literature_id": lit_id or "",
    }
    if doi:
        our_doi_map[doi] = info
    if title:
        tn = normalise_title(title)
        if tn and len(tn) > 15:  # skip very short titles to avoid false matches
            our_title_map.setdefault(tn, []).append(info)

print(f"  Unique DOIs: {len(our_doi_map)}")
print(f"  Unique normalised titles: {len(our_title_map)}")

# -----------------------------------------------------------------
# 3. Cross-reference
# -----------------------------------------------------------------
print("\nCross-referencing...")
overlap: list[dict] = []
sharkipedia_only: list[dict] = []

for ref in shark_refs:
    matched = False
    match_method = ""
    matched_paper: dict = {}

    # Try DOI match first
    if ref["doi"] and ref["doi"] in our_doi_map:
        matched = True
        match_method = "doi"
        matched_paper = our_doi_map[ref["doi"]]

    # Try title match
    if not matched and ref["title_norm"] and len(ref["title_norm"]) > 15:
        candidates = our_title_map.get(ref["title_norm"], [])
        if candidates:
            # If year matches too, strong match
            year_matches = [c for c in candidates if c["year"] == ref["year"]]
            if year_matches:
                matched = True
                match_method = "title+year"
                matched_paper = year_matches[0]
            elif len(candidates) == 1:
                matched = True
                match_method = "title_only"
                matched_paper = candidates[0]

    if matched:
        overlap.append({
            "sharkipedia_id": ref["reference_id"],
            "sharkipedia_source": ref["source"],
            "sharkipedia_doi": ref["doi"],
            "match_method": match_method,
            "our_doi": matched_paper.get("doi", ""),
            "our_title": matched_paper.get("title", ""),
            "our_year": matched_paper.get("year", ""),
            "our_authors": matched_paper.get("authors", ""),
            "our_literature_id": matched_paper.get("literature_id", ""),
        })
    else:
        sharkipedia_only.append({
            "sharkipedia_id": ref["reference_id"],
            "sharkipedia_source": ref["source"],
            "sharkipedia_doi": ref["doi"],
            "extracted_title": ref["title_raw"],
            "extracted_year": ref["year"] or "",
        })

# -----------------------------------------------------------------
# 4. Write outputs
# -----------------------------------------------------------------
print("\nWriting outputs...")

# Overlap CSV
with open(OUT_OVERLAP, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "sharkipedia_id", "sharkipedia_source", "sharkipedia_doi",
        "match_method", "our_doi", "our_title", "our_year",
        "our_authors", "our_literature_id",
    ])
    writer.writeheader()
    writer.writerows(overlap)
print(f"  Overlap: {OUT_OVERLAP}")

# Sharkipedia-only CSV
with open(OUT_SHARK_ONLY, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "sharkipedia_id", "sharkipedia_source", "sharkipedia_doi",
        "extracted_title", "extracted_year",
    ])
    writer.writeheader()
    writer.writerows(sharkipedia_only)
print(f"  Sharkipedia-only: {OUT_SHARK_ONLY}")

# Summary
doi_matches = sum(1 for r in overlap if r["match_method"] == "doi")
title_year_matches = sum(1 for r in overlap if r["match_method"] == "title+year")
title_only_matches = sum(1 for r in overlap if r["match_method"] == "title_only")

summary_lines = [
    "Sharkipedia vs EEA Literature Database: Cross-Reference Summary",
    "=" * 65,
    "",
    f"Sharkipedia references:           {len(shark_refs):>6}",
    f"  - with extractable DOI:         {sum(1 for r in shark_refs if r['doi']):>6}",
    f"  - with extractable title:       {sum(1 for r in shark_refs if r['title_norm']):>6}",
    "",
    f"EEA database papers:              {len(our_papers):>6}",
    f"  - unique DOIs:                  {len(our_doi_map):>6}",
    "",
    f"Overlap (in both databases):      {len(overlap):>6}  "
    f"({100 * len(overlap) / len(shark_refs):.1f}% of Sharkipedia)",
    f"  - matched by DOI:               {doi_matches:>6}",
    f"  - matched by title + year:      {title_year_matches:>6}",
    f"  - matched by title only:        {title_only_matches:>6}",
    "",
    f"Sharkipedia-only (not in EEA):    {len(sharkipedia_only):>6}  "
    f"({100 * len(sharkipedia_only) / len(shark_refs):.1f}% of Sharkipedia)",
    "",
    "Output files:",
    f"  Overlap:          {OUT_OVERLAP.name}",
    f"  Sharkipedia-only: {OUT_SHARK_ONLY.name}",
    f"  This summary:     {OUT_SUMMARY.name}",
]
summary_text = "\n".join(summary_lines) + "\n"

with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
    f.write(summary_text)

print(f"  Summary: {OUT_SUMMARY}")
print()
print(summary_text)
