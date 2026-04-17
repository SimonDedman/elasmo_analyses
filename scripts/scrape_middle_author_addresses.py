#!/usr/bin/env python3
"""
Extract middle/last-author affiliations from PDFs using superscript number matching.

For authors who appear only as middle/last authors in our corpus (and are missing
institution data), try up to 5 of their most recent papers until one yields a
successful geocode.

Usage:
    python scripts/scrape_middle_author_addresses.py [--limit N] [--resume]
"""

import argparse
import csv
import json
import re
import subprocess
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

# Minimum PDF size to skip supplementary-only files
MIN_PDF_BYTES = 100_000  # 100 KB
# Number of candidate papers to try per author before giving up
MAX_PAPERS_PER_AUTHOR = 5
# How many chars from the start of the PDF to search for affiliations
AFFILIATION_SEARCH_CHARS = 10_000

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from extract_schema_columns import (
    build_pdf_index, _first_surname, _pick_best_pdf, extract_text_from_pdf
)


def extract_raw_front_matter(pdf_path: Path, max_chars: int = AFFILIATION_SEARCH_CHARS) -> str | None:
    """Extract raw (unstripped) text from the first pages of a PDF.

    Unlike extract_text_from_pdf, this does NOT strip the front matter —
    we need the header/affiliation block that appears before the Abstract.
    We request only the first 3 pages to keep it fast.
    """
    try:
        # -l 3 = last page to extract is page 3 (first 3 pages)
        result = subprocess.run(
            ["pdftotext", "-l", "3", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout:
            # Fall back to full extraction (some PDFs only have one page)
            result = subprocess.run(
                ["pdftotext", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return None
        text = result.stdout
        if not text or len(text) < 100:
            return None
        return text[:max_chars]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


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


def strip_accents(s) -> str:
    """Strip accents but keep alphabetic structure (accent-insensitive matching)."""
    if s is None:
        return ""
    try:
        import math
        if isinstance(s, float) and math.isnan(s):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(s)
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def make_name_patterns(first_name: str, last_name: str, display_name: str) -> list[tuple[str, str]]:
    """Build a list of (regex_pattern, description) pairs to try for name matching.

    Strategies:
    - Full display_name (e.g. "María García-López")
    - Surname only (accent-stripped)
    - "Firstname Lastname" (accent-stripped)
    - "F. Lastname" abbreviated first name
    - Hyphenated surname parts (e.g. "Garcia" and "Lopez" separately)
    """
    patterns = []

    ln = strip_accents(last_name or "").strip()
    fn = strip_accents(first_name or "").strip()
    dn = strip_accents(display_name or "").strip()

    if len(ln) < 3:
        return patterns

    # Pattern helper: build a word-boundary regex
    def _pat(name: str, desc: str) -> tuple[str, str]:
        return (r"\b" + re.escape(name) + r"\b", desc)

    # 1. Surname only (most reliable in headers)
    patterns.append(_pat(ln, "surname"))

    # 2. Full "Firstname Lastname" from display_name
    if dn and dn != ln:
        # Extract just the name part (strip trailing institutional text)
        dn_parts = dn.split()
        if len(dn_parts) >= 2:
            patterns.append(_pat(dn, "display_name_full"))

    # 3. "Firstname Lastname" from first_name + last_name
    if fn and fn != ln:
        full = f"{fn} {ln}"
        if full.strip() != ln:
            patterns.append(_pat(full, "first_last"))

    # 4. Abbreviated first name: "F. Lastname" or "F Lastname"
    if fn:
        initial = fn.split()[0][0] if fn.split() else ""
        if initial:
            patterns.append((_pat(f"{initial}[.]? {ln}", f"initial_{initial}")[0], f"initial_{initial}"))
            # Also try without space: "F.Lastname"
            patterns.append((_pat(f"{initial}[.]{ln}", f"initial_nospace_{initial}")[0], f"initial_nospace_{initial}"))

    # 5. Hyphenated surname parts (try each part)
    if "-" in ln:
        for part in ln.split("-"):
            if len(part) >= 4:
                patterns.append(_pat(part, f"surname_part_{part}"))

    return patterns


def find_author_affiliation(text: str, first_name: str, last_name: str, display_name: str = "") -> tuple[str, str]:
    """Find the affiliation for a specific author in a PDF header.

    Improvements over v1:
    - Searches up to AFFILIATION_SEARCH_CHARS (10 000) chars instead of 5 000
    - Also looks for "Author affiliations", "Correspondence", "Address" blocks
    - Uses multiple name patterns (display_name, abbreviated first, hyphenated parts)
    - Relaxed affiliation line filter (country tail no longer required)

    Returns: (affiliation_text, strategy_used)
    """
    # ---- Build search region ----
    header_raw = text[:AFFILIATION_SEARCH_CHARS]

    # Also search in any dedicated affiliation block regardless of position
    extra_blocks = []
    for kw in (
        r"Author\s+[Aa]ffiliations?",
        r"AUTHORS?\s+[Aa]FFILIATIONS?",
        r"Correspondence",
        r"CORRESPONDENCE",
        r"Address(?:es)?",
        r"ADDRESSES?",
        r"Present\s+[Aa]ddress",
    ):
        for m in re.finditer(kw, text):
            start = m.start()
            extra_blocks.append(text[start: start + 2000])

    combined_raw = header_raw + "\n".join(extra_blocks)
    combined = strip_accents(combined_raw)

    # ---- Name matching ----
    name_patterns = make_name_patterns(first_name, last_name, display_name)
    if not name_patterns:
        return ("", "surname_too_short")

    all_matches = []
    matched_pattern_desc = ""
    for pat, desc in name_patterns:
        ms = list(re.finditer(pat, combined, re.IGNORECASE))
        if ms:
            all_matches.extend(ms)
            if not matched_pattern_desc:
                matched_pattern_desc = desc

    if not all_matches:
        return ("", "name_not_found")

    # ---- Superscript extraction ----
    superscripts = set()
    for m in all_matches:
        tail = combined[m.end(): m.end() + 50]
        num_match = re.match(r"[\s]*([\d]{1,3}(?:[,\-\s]+\d{1,3})*)", tail)
        if num_match:
            nums = re.findall(r"\d{1,3}", num_match.group(1))
            superscripts.update(nums)
        else:
            sym_match = re.match(r"[\s]*([\*\†\‡\§\¶#a-z]{1,3})", tail)
            if sym_match:
                superscripts.add(sym_match.group(1).strip())

    # ---- Affiliation block detection ----
    aff_keywords = (
        r"(?:University|Universidad|Università|Universität|Universidade|Université"
        r"|Institut|Institute|Laboratory|Laboratoire|Department|Departamento"
        r"|School|Center|Centre|Centro|Station|Museum|Museo|Fisheries|Oceans"
        r"|NOAA|CSIRO|CNRS|IFREMER|Research|Academy|College|Aquarium"
        r"|Marine Lab|Biological Station|Conservation|Foundation|Trust"
        r"|Government|Federal|National|Ministry|Agency|Authority)"
    )

    country_tail = re.compile(
        r"(?:USA|U\.S\.A\.|United States|United Kingdom|UK|Canada|Australia"
        r"|Germany|France|Spain|Italy|Japan|China|Brazil|Mexico|South Africa"
        r"|New Zealand|Netherlands|Portugal|India|Norway|Sweden|Greece|Israel"
        r"|Ireland|Chile|Argentina|Singapore|Korea|Indonesia|Thailand|Malaysia"
        r"|Philippines|Vietnam|Egypt|Turkey|Russia|Poland|Belgium|Denmark"
        r"|Finland|Switzerland|Austria|Hungary|Czech|Slovakia|Croatia|Romania"
        r"|Bulgaria|Hong Kong|Taiwan|Colombia|Peru|Ecuador|Venezuela|Panama"
        r"|Costa Rica|Cuba|Bahamas|Jamaica|Kenya|Tanzania|Morocco|Tunisia"
        r"|Saudi Arabia|UAE|Qatar|Nigeria|Ghana|Senegal|Madagascar|Mauritius"
        r"|Iceland|Fiji|Papua New Guinea|Solomon Islands|Uruguay|Bolivia"
        r"|Paraguay|Dominican Republic|Namibia|Zimbabwe|Mozambique|Ethiopia"
        r"|Uganda|Rwanda|Cameroon|Ivory Coast|Benin|Togo|Gabon|Angola"
        r"|Pakistan|Bangladesh|Sri Lanka|Nepal|Myanmar|Cambodia|Laos"
        r"|Mongolia|Kazakhstan|Uzbekistan|Azerbaijan|Georgia|Armenia"
        r"|Albania|Serbia|Montenegro|Bosnia|Macedonia|Slovenia|Latvia"
        r"|Lithuania|Estonia|Cyprus|Malta|Luxembourg|Liechtenstein"
        r"|Monaco|Andorra|San Marino|Vatican)\b",
        re.IGNORECASE,
    )

    affiliation_lines = []
    for line in combined.split("\n"):
        line = line.strip()
        if not line or len(line) < 15 or len(line) > 500:
            continue
        if not re.search(aff_keywords, line, re.IGNORECASE):
            continue
        # Accept line if it has a country-like token OR ends with a 2-letter code
        # OR has a comma structure typical of addresses (relaxed vs v1)
        looks_institutional = (
            country_tail.search(line)
            or re.search(r",\s*[A-Z]{2,}\s*$", line)
            or line.count(",") >= 2   # e.g. "Dept X, University Y, City, Country"
        )
        if not looks_institutional:
            continue

        # Numbered or symbol-led lines
        lead_match = re.match(r"^[\(\[]?(\d{1,3})[\)\]\.]?\s+(.+)", line)
        if lead_match:
            affiliation_lines.append((lead_match.group(1), lead_match.group(2)))
            continue

        sup_map = {"¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
                   "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁰": "0"}
        if line and line[0] in sup_map:
            num = ""
            rest = line
            while rest and rest[0] in sup_map:
                num += sup_map[rest[0]]
                rest = rest[1:]
            affiliation_lines.append((num, rest.strip()))
            continue

        # Letter-coded: "a University...", "b Institute..."
        letter_match = re.match(r"^([a-e])\s+([A-Z].+)", line)
        if letter_match:
            affiliation_lines.append((letter_match.group(1), letter_match.group(2)))
            continue

        # Unnumbered / single-institution
        affiliation_lines.append(("", line))

    if not affiliation_lines:
        return ("", "no_affiliations_found")

    # ---- Match superscripts to affiliations ----
    if superscripts:
        for num, aff in affiliation_lines:
            if num in superscripts:
                return (aff, f"matched_superscript_{num}_via_{matched_pattern_desc}")

    # No superscript match — if single unique affiliation, use it
    unique_affs = list(set(aff for _, aff in affiliation_lines))
    if len(unique_affs) == 1:
        return (unique_affs[0], f"single_affiliation_via_{matched_pattern_desc}")

    # Fallback: first numbered affiliation
    numbered = [(n, a) for n, a in affiliation_lines if n]
    if numbered:
        return (numbered[0][1], f"first_numbered_fallback_via_{matched_pattern_desc}")

    return (affiliation_lines[0][1], f"first_affiliation_fallback_via_{matched_pattern_desc}")


def geocode(affiliation: str, country_hint: str | None = None) -> dict | None:
    """Geocode an affiliation string via Nominatim."""
    time.sleep(1.1)  # strict 1 req/sec rate limit
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
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process first N authors only")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    print("Loading CSVs...")
    authors = pd.read_csv(AUTHORS_CSV)
    authors["aid"] = authors["openalex_author_id"].apply(strip_prefix)
    # Build lookup: aid -> display_name (for better name matching)
    aid_to_display = dict(zip(authors["aid"], authors["display_name"].fillna("")))

    li = pd.read_csv(LAST_INST_CSV)
    li["aid"] = li["openalex_author_id"].apply(strip_prefix)
    enriched = set(li[li["last_institution_name"].notna()]["aid"])

    # Also count already-scraped authors from previous runs
    if OUT_CSV.exists():
        prev = pd.read_csv(OUT_CSV)
        prev["aid"] = prev["openalex_author_id"].apply(strip_prefix)
        enriched |= set(prev[prev["last_institution_name"].notna()]["aid"])

    missing = set(authors["aid"]) - enriched
    print(f"  Still-missing authors: {len(missing)}")

    pa = pd.read_csv(PAPER_AUTHORS_CSV)
    pa["aid"] = pa["openalex_author_id"].apply(strip_prefix)
    # Middle or last only (first-author scrape is handled elsewhere)
    mid_last = pa[(pa["aid"].isin(missing)) & (pa["author_position"] != "first")].copy()

    # Load year + title from parquet
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

    # Restrict to post-2010 where numbered affiliations are standard
    mid_last = mid_last[mid_last["year"] >= 2010].copy()

    # Sort newest-first so top-N picks are most recent papers
    mid_last = mid_last.sort_values(["aid", "year"], ascending=[True, False])

    # For each author, keep up to MAX_PAPERS_PER_AUTHOR candidates
    author_papers: dict[str, list[dict]] = {}
    for _, row in mid_last.iterrows():
        aid = str(row["aid"])
        if aid not in author_papers:
            author_papers[aid] = []
        if len(author_papers[aid]) < MAX_PAPERS_PER_AUTHOR:
            author_papers[aid].append(row.to_dict())

    print(f"  Target authors: {len(author_papers)} (post-2010, up to {MAX_PAPERS_PER_AUTHOR} papers each)")

    # Build PDF index
    pdf_index = build_pdf_index(PDF_DIR)
    print(f"  PDF index: {sum(len(v) for v in pdf_index.values())} PDFs")

    # Resume support
    processed = set()
    if args.resume and PROGRESS.exists():
        with open(PROGRESS) as f:
            processed = set(json.load(f).get("processed", []))
        print(f"  Resuming: {len(processed)} already done")

    # Apply limit to author list (not rows)
    aid_list = [aid for aid in author_papers if aid not in processed]
    if args.limit:
        aid_list = aid_list[:args.limit]

    out_rows = []
    debug_rows = []
    n_processed = 0
    n_geocoded = 0

    for aid in aid_list:
        papers = author_papers[aid]
        display_name = aid_to_display.get(aid, "")

        # Try each candidate paper in order
        resolved = False
        for paper_idx, row in enumerate(papers):
            first = row.get("first_name") or ""
            last = row.get("last_name") or ""
            year = int(row["year"]) if pd.notna(row.get("year")) else None
            title = row.get("title_paper") or row.get("title") or ""
            lit_id = row.get("lit_id", "")

            if not year:
                continue
            first_author_surname = _first_surname(row.get("authors", "") or "")
            if not first_author_surname:
                continue

            candidates = pdf_index.get((first_author_surname, year), [])
            if not candidates:
                continue

            # Filter out small PDFs (likely supplementary-only)
            candidates = [p for p in candidates if p.stat().st_size >= MIN_PDF_BYTES]
            if not candidates:
                continue

            best_pdf = _pick_best_pdf(candidates, title)
            if not best_pdf:
                continue

            # Use raw front-matter text (no stripping) so affiliations are preserved
            text = extract_raw_front_matter(best_pdf)
            if not text or len(text) < 200:
                continue

            aff, strategy = find_author_affiliation(text, first, last, display_name)
            if not aff:
                # Record failure for this paper attempt and try the next
                debug_rows.append({
                    "aid": aid,
                    "lit_id": lit_id,
                    "paper_attempt": paper_idx + 1,
                    "result": strategy,
                    "first": first,
                    "last": last,
                    "display_name": display_name,
                    "pdf": str(best_pdf.name),
                })
                continue

            geo = geocode(aff)
            if not geo:
                debug_rows.append({
                    "aid": aid,
                    "lit_id": lit_id,
                    "paper_attempt": paper_idx + 1,
                    "result": "geocode_failed",
                    "affiliation": aff[:200],
                    "strategy": strategy,
                    "pdf": str(best_pdf.name),
                })
                continue

            # Success
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
                "aid": aid,
                "lit_id": lit_id,
                "paper_attempt": paper_idx + 1,
                "result": "ok",
                "affiliation": aff[:200],
                "strategy": strategy,
                "geocoded_to": geo["display_name"][:100],
                "pdf": str(best_pdf.name),
            })
            n_geocoded += 1
            resolved = True
            break  # No need to try more papers for this author

        if not resolved:
            # All paper attempts exhausted without a result; record a summary failure
            debug_rows.append({
                "aid": aid,
                "lit_id": papers[0].get("lit_id", "") if papers else "",
                "paper_attempt": len(papers),
                "result": "all_papers_exhausted",
                "first": papers[0].get("first_name", "") if papers else "",
                "last": papers[0].get("last_name", "") if papers else "",
                "display_name": display_name,
            })

        processed.add(aid)
        n_processed += 1

        if n_processed % 50 == 0:
            print(f"  Progress: {n_processed} / {len(aid_list)} (geocoded: {n_geocoded}, "
                  f"rate: {100*n_geocoded/n_processed:.1f}%)")
            with open(PROGRESS, "w") as f:
                json.dump({"processed": sorted(processed)}, f)
            pd.DataFrame(out_rows).to_csv(OUT_CSV, index=False)
            pd.DataFrame(debug_rows).to_csv(DEBUG_CSV, index=False)

    # Final save
    with open(PROGRESS, "w") as f:
        json.dump({"processed": sorted(processed)}, f)
    pd.DataFrame(out_rows).to_csv(OUT_CSV, index=False)
    pd.DataFrame(debug_rows).to_csv(DEBUG_CSV, index=False)

    print(f"\nDone. Processed {n_processed} authors, geocoded {n_geocoded} "
          f"({100*n_geocoded/max(n_processed, 1):.1f}%)")


if __name__ == "__main__":
    main()
