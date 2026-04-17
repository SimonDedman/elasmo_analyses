#!/usr/bin/env python3
"""
Extract middle/last-author affiliations from PDFs using superscript number matching.

For authors who appear only as middle/last authors in our corpus (and are missing
institution data), use the most recent paper where they appear. Match their name
to a superscript number, then look up the numbered affiliation in the paper.

Usage:
    python scripts/scrape_middle_author_addresses.py [--limit N] [--resume]
"""

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"
PAPER_AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_paper_authors.csv"
LAST_INST_CSV = PROJECT_ROOT / "outputs" / "openalex_authors_last_institution.csv"
PARQUET = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
OUT_CSV = PROJECT_ROOT / "outputs" / "scraped_middle_author_addresses.csv"
DEBUG_CSV = PROJECT_ROOT / "outputs" / "scraped_middle_author_addresses_debug.csv"
PROGRESS = PROJECT_ROOT / "outputs" / ".scrape_middle_progress.json"
PDF_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "elasmo_analyses/1.0 (simondedman@gmail.com)"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from extract_schema_columns import (
    build_pdf_index, _first_surname, _pick_best_pdf, extract_text_from_pdf
)


def strip_prefix(s: str) -> str:
    if isinstance(s, str) and s.startswith("https://openalex.org/"):
        return s[len("https://openalex.org/"):]
    return str(s) if s else ""


def normalise(s: str) -> str:
    """Lowercase, strip accents and punctuation."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", s.lower())


def strip_accents(s: str) -> str:
    """Strip accents but keep alphabetic structure (for accent-insensitive matching)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def find_author_affiliation(text: str, first_name: str, last_name: str) -> tuple[str, str]:
    """Find the affiliation for a specific author in a PDF header.

    Strategy:
    1. Find the author name in the first ~5000 chars (accent-insensitive)
    2. Look for superscript numbers/symbols near the name
    3. Find the numbered/symboled affiliation in the following block
    4. If no numbering found, return single-affiliation paper's sole affiliation

    Returns: (affiliation_text, strategy_used)
    """
    header_raw = text[:5000]
    # Strip accents from both the search target and the header for matching
    header = strip_accents(header_raw)
    ln_nfc = strip_accents(last_name or "")

    if len(ln_nfc) < 3:
        return ("", "surname_too_short")

    # Find surname in accent-stripped header (allow word boundary)
    ln_pattern = re.escape(ln_nfc)
    matches = list(re.finditer(r"\b" + ln_pattern + r"\b", header, re.IGNORECASE))
    if not matches:
        return ("", "name_not_found")

    # For each match, look for a superscript-like number/symbol in the next ~30 chars
    # Superscripts in PDF text often appear as digits or symbols directly after the name
    # Common patterns: "Lastname1", "Lastname 1", "Lastname¹", "Lastname*", "Lastname^1"
    sup_pattern = re.compile(
        r"(?:[\s]*)(?:[\*\†\‡\§\¶#])?[\s]*([\d¹²³⁴⁵⁶⁷⁸⁹⁰,\-]+|[a-z]{1,2})(?=[\s,;.])",
        re.IGNORECASE
    )
    superscripts = set()
    for m in matches:
        # Look in the 40 chars following the match
        tail = header[m.end():m.end() + 40]
        # Find the first group of digits/symbols right after the name
        num_match = re.match(r"[\s]*([\d]{1,3}(?:[,\-\s]+\d{1,3})*)", tail)
        if num_match:
            nums = re.findall(r"\d{1,3}", num_match.group(1))
            superscripts.update(nums)
        else:
            # Look for symbol markers
            sym_match = re.match(r"[\s]*([\*\†\‡\§\¶#a-z]{1,3})", tail)
            if sym_match:
                superscripts.add(sym_match.group(1).strip())

    # Find the affiliation block (usually after author list)
    aff_keywords = r"(?:University|Universidad|Università|Universität|Universidade|Université|Institut|Institute|Laboratory|Laboratoire|Department|Departamento|School|Center|Centre|Centro|Station|Museum|Museo|Fisheries|Oceans|NOAA|CSIRO|CNRS|IFREMER|Research|Academy|College|Aquarium|Marine Lab|Biological Station)"
    # Common country/geographic markers at end of affiliation
    country_tail = re.compile(
        r"(?:USA|U\.S\.A\.|United States|United Kingdom|UK|Canada|Australia|Germany|France|Spain|Italy|Japan|China|Brazil|Mexico|South Africa|New Zealand|Netherlands|Portugal|India|Norway|Sweden|Greece|Israel|Ireland|Chile|Argentina|Singapore|Korea|Indonesia|Thailand|Malaysia|Philippines|Vietnam|Egypt|Turkey|Russia|Poland|Belgium|Denmark|Finland|Switzerland|Austria|Hungary|Czech|Slovakia|Croatia|Romania|Bulgaria|Hong Kong|Taiwan|Colombia|Peru|Ecuador|Venezuela|Panama|Costa Rica|Cuba|Bahamas|Jamaica|Kenya|Tanzania|Morocco|Tunisia|Saudi Arabia|UAE|Qatar|Nigeria|Ghana|Senegal|Madagascar|Mauritius|Iceland|Fiji|Papua New Guinea|Solomon Islands)\b",
        re.IGNORECASE
    )

    # Numbered affiliations: "1 University...", "²University...", "(1) University..."
    affiliation_lines = []
    for line in header.split("\n"):
        line = line.strip()
        if not line or len(line) < 20 or len(line) > 400:
            continue
        if not re.search(aff_keywords, line, re.IGNORECASE):
            continue
        # Must also contain a country-like token OR look institutional
        if not (country_tail.search(line) or re.search(r",\s*[A-Z]{2,}\s*$", line)):
            continue
        # Check if line starts with a number or common affiliation marker
        lead_match = re.match(r"^[\(\[]?(\d{1,3})[\)\]\.]?\s+(.+)", line)
        if lead_match:
            affiliation_lines.append((lead_match.group(1), lead_match.group(2)))
        elif re.match(r"^[¹²³⁴⁵⁶⁷⁸⁹⁰]", line):
            # Superscript-led line
            sup_map = {"¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9","⁰":"0"}
            num = ""
            rest = line
            while rest and rest[0] in sup_map:
                num += sup_map[rest[0]]
                rest = rest[1:]
            affiliation_lines.append((num, rest.strip()))
        else:
            # Unnumbered affiliation (single-author-institution paper)
            affiliation_lines.append(("", line))

    if not affiliation_lines:
        return ("", "no_affiliations_found")

    # If we have superscript numbers for our author, match to numbered affiliations
    if superscripts:
        for num, aff in affiliation_lines:
            if num in superscripts:
                return (aff, f"matched_superscript_{num}")

    # No superscripts found OR no match — if only one unique affiliation, use it
    unique_affs = list(set(aff for _, aff in affiliation_lines))
    if len(unique_affs) == 1:
        return (unique_affs[0], "single_affiliation")

    # Fallback: take the first numbered affiliation (often the corresponding author's)
    return (affiliation_lines[0][1], "first_affiliation_fallback")


def geocode(affiliation: str, country_hint: str | None = None) -> dict | None:
    """Geocode an affiliation string via Nominatim."""
    time.sleep(1.1)  # strict 1 req/sec rate limit
    # Truncate and clean
    q = affiliation[:200]
    if country_hint:
        q = f"{q}, {country_hint}"
    try:
        r = requests.get(NOMINATIM, params={
            "q": q, "format": "json", "limit": 1, "addressdetails": 1
        }, headers={"User-Agent": UA}, timeout=20)
        if r.status_code != 200:
            return None
        results = r.json()
        if not results:
            return None
        hit = results[0]
        addr = hit.get("address", {})
        return {
            "lat": float(hit["lat"]),
            "lon": float(hit["lon"]),
            "display_name": hit.get("display_name", ""),
            "country": (addr.get("country_code") or "").upper(),
            "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "region": addr.get("state") or addr.get("region") or "",
        }
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process first N authors only")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    print("Loading CSVs...")
    authors = pd.read_csv(AUTHORS_CSV)
    authors["aid"] = authors["openalex_author_id"].apply(strip_prefix)

    li = pd.read_csv(LAST_INST_CSV)
    li["aid"] = li["openalex_author_id"].apply(strip_prefix)
    enriched = set(li[li["last_institution_name"].notna()]["aid"])
    missing = set(authors["aid"]) - enriched
    print(f"  Still-missing authors: {len(missing)}")

    pa = pd.read_csv(PAPER_AUTHORS_CSV)
    pa["aid"] = pa["openalex_author_id"].apply(strip_prefix)
    # Middle or last only (first-author scrape is handled elsewhere)
    mid_last = pa[(pa["aid"].isin(missing)) & (pa["author_position"] != "first")].copy()

    # Load year + title
    t = pd.read_parquet(PARQUET, columns=["literature_id", "year", "title", "authors"])
    t["literature_id"] = t["literature_id"].apply(
        lambda v: str(int(float(v))) if pd.notna(v) else ""
    )
    t = t[t["literature_id"] != ""]

    mid_last["lit_id"] = mid_last["literature_id"].apply(
        lambda v: str(int(float(v))) if pd.notna(v) else ""
    )
    mid_last = mid_last.merge(t, left_on="lit_id", right_on="literature_id", how="left",
                               suffixes=("", "_paper"))

    # Most recent paper per missing author, prefer 2010+ (where numbered affiliations standard)
    mid_last = mid_last.sort_values(["aid", "year"], ascending=[True, False])
    picks = mid_last.drop_duplicates(subset="aid", keep="first").copy()

    pre_2010 = (picks["year"] < 2010).sum()
    print(f"  Target authors: {len(picks)} (post-2010: {(picks['year'] >= 2010).sum()}, pre-2010: {pre_2010})")
    # Restrict to post-2010 where numbered affiliations are standard
    picks = picks[picks["year"] >= 2010].copy()
    print(f"  After year filter: {len(picks)}")

    # Build PDF index
    pdf_index = build_pdf_index(PDF_DIR)
    print(f"  PDF index: {sum(len(v) for v in pdf_index.values())} PDFs")

    # Resume support
    processed = set()
    if args.resume and PROGRESS.exists():
        with open(PROGRESS) as f:
            processed = set(json.load(f).get("processed", []))
        print(f"  Resuming: {len(processed)} already done")

    if args.limit:
        picks = picks.head(args.limit)

    out_rows = []
    debug_rows = []
    n_processed = 0
    n_geocoded = 0

    for _, row in picks.iterrows():
        aid = row["aid"]
        if aid in processed:
            continue

        first = row.get("first_name") or ""
        last = row.get("last_name") or ""
        year = int(row["year"]) if pd.notna(row["year"]) else None
        title = row.get("title_paper") or row.get("title") or ""
        lit_id = row["lit_id"]
        doi = row.get("doi", "")

        # Find PDF
        if not year:
            debug_rows.append({"aid": aid, "lit_id": lit_id, "result": "no_year"})
            processed.add(aid)
            continue
        first_author_surname = _first_surname(row.get("authors", "") or "")
        if not first_author_surname:
            debug_rows.append({"aid": aid, "lit_id": lit_id, "result": "no_first_author"})
            processed.add(aid)
            continue
        candidates = pdf_index.get((first_author_surname, year), [])
        best_pdf = _pick_best_pdf(candidates, title)
        if not best_pdf:
            debug_rows.append({"aid": aid, "lit_id": lit_id, "result": "no_pdf"})
            processed.add(aid)
            continue

        text = extract_text_from_pdf(best_pdf)
        if not text or len(text) < 500:
            debug_rows.append({"aid": aid, "lit_id": lit_id, "result": "no_text"})
            processed.add(aid)
            continue

        aff, strategy = find_author_affiliation(text, first, last)
        if not aff:
            debug_rows.append({
                "aid": aid, "lit_id": lit_id, "result": strategy,
                "first": first, "last": last
            })
            processed.add(aid)
            continue

        geo = geocode(aff)
        if not geo:
            debug_rows.append({
                "aid": aid, "lit_id": lit_id, "result": "geocode_failed",
                "affiliation": aff[:200], "strategy": strategy
            })
            processed.add(aid)
            continue

        out_rows.append({
            "openalex_author_id": f"https://openalex.org/{aid}",
            "last_institution_id": "",
            "last_institution_name": aff[:200],
            "last_institution_country": geo["country"],
            "last_institution_city": geo["city"],
            "last_institution_region": geo["region"],
            "last_institution_lat": geo["lat"],
            "last_institution_lon": geo["lon"],
            "last_institution_type": "scraped_middle",
        })
        debug_rows.append({
            "aid": aid, "lit_id": lit_id, "result": "ok",
            "affiliation": aff[:200], "strategy": strategy,
            "geocoded_to": geo["display_name"][:100]
        })
        processed.add(aid)
        n_geocoded += 1

        n_processed += 1
        if n_processed % 50 == 0:
            print(f"  Progress: {n_processed} / {len(picks)} (geocoded: {n_geocoded})")
            with open(PROGRESS, "w") as f:
                json.dump({"processed": sorted(processed)}, f)
            # Incremental save
            pd.DataFrame(out_rows).to_csv(OUT_CSV, index=False)
            pd.DataFrame(debug_rows).to_csv(DEBUG_CSV, index=False)

    with open(PROGRESS, "w") as f:
        json.dump({"processed": sorted(processed)}, f)
    pd.DataFrame(out_rows).to_csv(OUT_CSV, index=False)
    pd.DataFrame(debug_rows).to_csv(DEBUG_CSV, index=False)

    print(f"\nDone. Processed {n_processed}, geocoded {n_geocoded} ({100*n_geocoded/max(n_processed,1):.1f}%)")


if __name__ == "__main__":
    main()
