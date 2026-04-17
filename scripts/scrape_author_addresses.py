#!/usr/bin/env python3
"""
Scrape institutional affiliations from PDFs for first authors missing from
openalex_authors_last_institution.csv, then geocode via Nominatim.

Usage:
    python scripts/scrape_author_addresses.py
    python scripts/scrape_author_addresses.py --limit 10
    python scripts/scrape_author_addresses.py --resume
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")

PAPER_AUTHORS_CSV  = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
UNIQUE_AUTHORS_CSV = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
LAST_INST_CSV      = PROJECT_BASE / "outputs/openalex_authors_last_institution.csv"
PARQUET            = PROJECT_BASE / "outputs/literature_review_enriched.parquet"

OUTPUT_CSV       = PROJECT_BASE / "outputs/scraped_author_addresses.csv"
DEBUG_CSV        = PROJECT_BASE / "outputs/scraped_author_addresses_debug.csv"
PROGRESS_JSON    = PROJECT_BASE / "outputs/.scrape_author_addresses_progress.json"

NOMINATIM_URL  = "https://nominatim.openstreetmap.org/search"
USER_AGENT     = "elasmo_analyses/1.0 (simondedman@gmail.com)"
RATE_LIMIT_SEC = 1.1  # strictly >1 s between Nominatim requests

TEXT_TIMEOUT   = 10   # seconds for pdftotext
MAX_TEXT_BYTES = 500_000

AFFIL_KEYWORDS = re.compile(
    r"University|Universit[eéà]|Universidad|Université|Universidade|Universiteit"
    r"|Institute|Institut[eo]?|Instituto"
    r"|Laboratory|Laborator[yi]|Laboratorio"
    r"|Department|Departamento|Département"
    r"|School|Escola|École"
    r"|Center|Centre|Centro"
    r"|College|Faculty|Facult[eé]|Facultad"
    r"|Museum|Museu[m]?"
    r"|Foundation|Fundaci[oó]n"
    r"|Research|Sciences|Sciences",
    re.IGNORECASE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers borrowed / adapted from extract_schema_columns.py
# ---------------------------------------------------------------------------

def _normalise_name(s: str) -> str:
    """Strip accents, hyphens, apostrophes, spaces; lowercase."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace("-", "").replace(" ", "").replace("'", "").replace("ʼ", "")


def build_pdf_index(pdf_dir: Path) -> dict[tuple[str, int], list[Path]]:
    """Build lookup from (normalised_first_author_surname, year) to PDF paths."""
    index: dict[tuple[str, int], list[Path]] = {}
    for year_dir in sorted(pdf_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for pdf in year_dir.glob("*.pdf"):
            parts = pdf.stem.split(".")
            if len(parts) >= 2:
                surname = _normalise_name(parts[0])
            else:
                surname = _normalise_name(pdf.stem.split("_")[0])
            key = (surname, year)
            index.setdefault(key, []).append(pdf)
    return index


def _title_words(title: str) -> set[str]:
    stops = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "or", "s",
        "that", "the", "to", "was", "were", "will", "with",
    }
    words = set(re.findall(r"[a-z]{3,}", title.lower()))
    return words - stops


def _pick_best_pdf(candidates: list[Path], title: str | None) -> Path | None:
    if not candidates:
        return None
    if len(candidates) == 1 or not title:
        return candidates[0]
    paper_words = _title_words(title)
    if not paper_words:
        return candidates[0]
    best_path = candidates[0]
    best_overlap = 0
    for pdf_path in candidates:
        parts = pdf_path.stem.split(".")
        title_parts = [p for p in parts if p.lower() not in ("etal",) and not p.isdigit()]
        if len(title_parts) > 1:
            title_parts = title_parts[1:]
        file_words: set[str] = set()
        for p in title_parts:
            file_words |= set(re.findall(r"[a-z]{3,}", p.lower()))
        overlap = len(paper_words & file_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_path = pdf_path
    return best_path


def extract_raw_text_from_pdf(pdf_path: Path) -> str | None:
    """Extract raw text (no section stripping) from a PDF — we need the header."""
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=TEXT_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        text = result.stdout
        if not text:
            return None
        if len(text.encode("utf-8", errors="ignore")) > MAX_TEXT_BYTES:
            text = text[:MAX_TEXT_BYTES]
        return text if text.strip() else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


# ---------------------------------------------------------------------------
# Affiliation extraction
# ---------------------------------------------------------------------------

# Patterns that indicate a line is NOT an affiliation (watermarks, headers, etc.)
_REJECT_PATTERNS = re.compile(
    r"BioOne|Copyright|All rights reserved|RESEARCH ARTICLE|ORIGINAL RESEARCH"
    r"|LETTER|REPORT|ARTICLE|COMMUNICATION"
    r"|This article|Downloaded from|eBooks|nonprofit societies|Please cite"
    r"|connecting authors|nonprofit publishers|academic institutions"
    r"|open.access|Creative Commons|doi\.org|^\s*Abstract\s*$"
    r"|^\s*ABSTRACT\s*$|journal homepage|correspondence to"
    r"|^Received|^Accepted|^Published|^Revised",
    re.IGNORECASE,
)


def _clean_line(line: str) -> str:
    """Strip superscript markers, emails, URLs, and excess whitespace."""
    # Remove common superscript notations: ¹²³ ¹ a,b 1,2,3 *
    line = re.sub(r"^\s*[¹²³⁴⁵⁶⁷⁸⁹⁰\d,;\*†‡§∥#]+\s*", "", line)
    # Remove email addresses
    line = re.sub(r"\S+@\S+", "", line)
    # Remove URLs
    line = re.sub(r"https?://\S+", "", line)
    # Strip leading punctuation remnants
    line = re.sub(r"^[\s,;.:\-\*]+", "", line)
    return line.strip()


def _is_affil_line(line: str) -> bool:
    """Return True if a cleaned line looks like an affiliation (not a false positive)."""
    if len(line) < 10:
        return False
    if _REJECT_PATTERNS.search(line):
        return False
    return bool(AFFIL_KEYWORDS.search(line))


def _join_affil_lines(lines: list[str], start_idx: int, max_lines: int = 3) -> str:
    """
    Join continuation lines of an affiliation (multi-line affiliations are common).

    Stops when a line looks like a new affiliation (numbered footnote), an
    abstract header, or is empty.  Capped at max_lines to avoid joining multiple
    institutions from a long footnote block.
    """
    parts: list[str] = []
    for line in lines[start_idx : start_idx + max_lines]:
        cleaned = _clean_line(line)
        if not cleaned:
            break
        # Stop if this looks like a new numbered/superscript footnote (new affiliation)
        if re.match(r"^[²³⁴⁵⁶⁷⁸⁹]", cleaned):
            break
        if re.match(r"^\d+\s+[A-Z]", cleaned):  # "2 Department of ..."
            break
        # Stop at abstract/keywords headers
        if re.match(r"^(Abstract|ABSTRACT|Keywords?|KEYWORDS?|Introduction|INTRODUCTION)\b", cleaned):
            break
        # Stop at clear rejection patterns
        if _REJECT_PATTERNS.search(cleaned):
            break
        parts.append(cleaned)
    return ", ".join(p for p in parts if p)


def extract_affiliation(text: str, author_last_name: str) -> str | None:
    """
    Heuristic extraction of the first author's affiliation from PDF header text.

    Strategies (tried in order):
    1. Numbered/superscript footnote block: look for ¹ or "1 " followed by
       affiliation keywords in the first 3,000 chars.
    2. Find the author name line, then scan the next ~25 lines for the first
       affiliation-like line.
    3. Fallback: return the first keyword-matching line in the first 3,000 chars.
    """
    header = text[:3000]
    lines = header.splitlines()

    # Strategy 1: numbered footnote block (most reliable for modern papers)
    footnote_re = re.compile(
        r"^[\s]*([¹¹²³⁴⁵⁶⁷⁸⁹⁰]|1[\s\.])\s*(.{10,})$",
        re.MULTILINE,
    )
    for m in footnote_re.finditer(header):
        candidate = _clean_line(m.group(2))
        if _is_affil_line(candidate):
            # Find line index so we can try to join continuation lines
            start = header[:m.start()].count("\n")
            return _join_affil_lines(lines, start)

    # Strategy 2: find author name line, look after it
    norm_last = _normalise_name(author_last_name)
    author_line_idx: int | None = None
    for i, line in enumerate(lines):
        norm_line = _normalise_name(line)
        if norm_last and norm_last in norm_line and len(norm_last) >= 3:
            author_line_idx = i
            break

    if author_line_idx is not None:
        for j in range(author_line_idx + 1, min(author_line_idx + 30, len(lines))):
            cleaned = _clean_line(lines[j])
            if _is_affil_line(cleaned):
                return _join_affil_lines(lines, j)

    # Strategy 3: fallback — first keyword-matching non-rejected line
    for i, line in enumerate(lines):
        cleaned = _clean_line(line)
        if _is_affil_line(cleaned) and len(cleaned) > 15:
            return _join_affil_lines(lines, i)

    return None


# ---------------------------------------------------------------------------
# Geocoding via Nominatim
# ---------------------------------------------------------------------------

def _nominatim_lookup(query: str) -> dict | None:
    """Single Nominatim request; returns parsed result dict or None."""
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": "1",
                                     "addressdetails": "1"})
    url = f"{NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Nominatim error for %r: %s", query, exc)
        return None

    if not data:
        return None

    hit = data[0]
    address = hit.get("address", {})
    lat = float(hit.get("lat", 0)) or None
    lon = float(hit.get("lon", 0)) or None

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("county")
        or address.get("municipality")
        or ""
    )
    region = (
        address.get("state")
        or address.get("region")
        or address.get("province")
        or ""
    )
    country = address.get("country_code", "").upper() or address.get("country", "")

    return {
        "lat": lat,
        "lon": lon,
        "display_name": hit.get("display_name", ""),
        "country": country,
        "city": city,
        "region": region,
    }


def _simplify_affiliation(affiliation: str) -> list[str]:
    """
    Generate progressively simpler Nominatim query strings from an affiliation.

    Returns a list of queries to try in order (most specific first).

    Examples:
        "Department of Life Sciences, University of Cagliari, 09126, Cagliari, Italy"
        →  ["University of Cagliari, Italy",
            "Cagliari, Italy"]

        "Sun Yat-sen University, Guangzhou, China"
        →  ["Sun Yat-sen University, China",
            "Guangzhou, China"]
    """
    queries: list[str] = []

    # Split on commas; clean each part
    parts = [p.strip().rstrip(".,;") for p in affiliation.split(",") if p.strip()]

    # Remove very short parts, postcodes, street numbers, and non-affiliation phrases
    def _keep_part(p: str) -> bool:
        if len(p) <= 3:
            return False
        if re.match(r"^\d[\d\s\-]+$", p):  # postcode / number
            return False
        if re.search(r"correspondence|address|email|tel:|fax:|zip", p, re.IGNORECASE):
            return False
        return True
    parts = [p for p in parts if _keep_part(p)]

    # Try to identify the country (last meaningful part that looks like a country)
    country_candidates = parts[-2:] if len(parts) >= 2 else parts
    country = ""
    for c in reversed(country_candidates):
        # Heuristic: country tends to be short, no digits, all alpha+space
        c_clean = c.strip().rstrip(".")
        if len(c_clean) <= 40 and re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s\-]+$", c_clean):
            country = c_clean
            break

    # Find institution-keyword parts
    inst_parts = [p for p in parts if AFFIL_KEYWORDS.search(p)]

    if inst_parts:
        inst = inst_parts[0]
        # Try: institution + country
        if country and country != inst:
            queries.append(f"{inst}, {country}")
        # Try: institution alone
        queries.append(inst)

    # Try: last two parts (typically "City, Country")
    if len(parts) >= 2:
        queries.append(", ".join(parts[-2:]))
    # Try: last part only (country / city)
    if parts:
        queries.append(parts[-1])

    # Deduplicate, preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        if q not in seen and len(q) > 3:
            seen.add(q)
            unique.append(q)
    return unique


def geocode(affiliation: str, rate_limiter: list[float]) -> dict | None:
    """
    Geocode an affiliation string via Nominatim with progressive fallback.

    ``rate_limiter`` is a 1-element list containing the timestamp of the last
    Nominatim request; updated in place so the caller doesn't need to track it.

    Returns dict with keys: lat, lon, display_name, country, city, region.
    """
    queries = _simplify_affiliation(affiliation)
    if not queries:
        queries = [affiliation[:200]]  # last-resort: raw truncated string

    for query in queries:
        elapsed = time.time() - rate_limiter[0]
        if elapsed < RATE_LIMIT_SEC:
            time.sleep(RATE_LIMIT_SEC - elapsed)
        result = _nominatim_lookup(query)
        rate_limiter[0] = time.time()
        if result:
            return result

    return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape affiliations from PDFs for missing first authors.")
    parser.add_argument("--limit", type=int, default=None, help="Process only N authors (for testing)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress JSON")
    args = parser.parse_args()

    # --- Load data -----------------------------------------------------------
    logger.info("Loading CSVs …")
    paper_authors = pd.read_csv(PAPER_AUTHORS_CSV)
    unique_authors = pd.read_csv(UNIQUE_AUTHORS_CSV)
    last_inst      = pd.read_csv(LAST_INST_CSV)

    all_ids = set(unique_authors["openalex_author_id"].dropna().unique())

    # "Missing" = present in last_institution but with no institution name/lat data.
    # These are authors that OpenAlex returned but without any institution record.
    has_name = last_inst["last_institution_name"].notna() & (last_inst["last_institution_name"] != "")
    missing_ids = set(last_inst.loc[~has_name, "openalex_author_id"].dropna().unique())
    enriched_count = len(all_ids) - len(missing_ids)
    logger.info(
        "Total authors: %d | With institution: %d | Missing institution: %d",
        len(all_ids), enriched_count, len(missing_ids),
    )

    # --- Filter to first-author appearances only ----------------------------
    first_author_rows = paper_authors[
        (paper_authors["author_position"] == "first")
        & (paper_authors["openalex_author_id"].isin(missing_ids))
    ].copy()
    logger.info("First-author rows for missing authors: %d", len(first_author_rows))

    # --- Attach year from parquet -------------------------------------------
    logger.info("Loading parquet for year/title lookup …")
    parquet_df = pd.read_parquet(
        PARQUET, columns=["literature_id", "year", "title", "authors"]
    )
    # Normalise literature_id to string (strip .0)
    parquet_df["literature_id"] = parquet_df["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    paper_authors["literature_id"] = paper_authors["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    first_author_rows["literature_id"] = first_author_rows["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)

    first_author_rows = first_author_rows.merge(
        parquet_df[["literature_id", "year", "title", "authors"]],
        on="literature_id",
        how="left",
    )

    # Keep only rows where year is known
    first_author_rows = first_author_rows.dropna(subset=["year"])
    first_author_rows["year"] = first_author_rows["year"].apply(lambda y: int(y))

    # For each missing author, take the most recent first-author paper
    idx_latest = first_author_rows.sort_values("year", ascending=False).groupby("openalex_author_id").head(1)
    logger.info("Target authors (with ≥1 first-author paper): %d", len(idx_latest))

    # Build name lookup: openalex_author_id → last_name
    name_lookup = unique_authors.set_index("openalex_author_id")["last_name"].to_dict()

    # --- Build PDF index ----------------------------------------------------
    logger.info("Building PDF index …")
    pdf_index = build_pdf_index(PDF_BASE)
    logger.info("PDF index has %d (surname, year) keys", len(pdf_index))

    # --- Resume handling ----------------------------------------------------
    progress: dict[str, dict] = {}
    if args.resume and PROGRESS_JSON.exists():
        with open(PROGRESS_JSON) as f:
            progress = json.load(f)
        logger.info("Resuming: %d authors already processed", len(progress))

    # --- Process -------------------------------------------------------------
    target_rows = idx_latest.to_dict("records")
    if args.limit:
        # Only process authors not yet in progress when limiting
        unprocessed = [r for r in target_rows if r["openalex_author_id"] not in progress]
        target_rows = unprocessed[: args.limit]
        logger.info("Testing with --limit %d", args.limit)

    output_rows: list[dict] = []
    debug_rows:  list[dict] = []
    rate_limiter = [0.0]  # shared rate limiter for geocode()

    for i, row in enumerate(target_rows):
        oa_id    = row["openalex_author_id"]
        year     = int(row["year"])
        title    = row.get("title") or ""
        last_name = name_lookup.get(oa_id) or row.get("last_name") or ""
        display_name = row.get("display_name") or ""

        if oa_id in progress:
            continue  # already done (resume mode)

        if (i + 1) % 50 == 0:
            logger.info("Progress: %d / %d authors processed", i + 1, len(target_rows))

        # --- Find PDF -------------------------------------------------------
        norm_surname = _normalise_name(last_name) if last_name else None
        pdf_path: Path | None = None
        if norm_surname:
            candidates = pdf_index.get((norm_surname, year), [])
            pdf_path = _pick_best_pdf(candidates, title)

        if pdf_path is None:
            debug_rows.append({
                "openalex_author_id": oa_id,
                "display_name": display_name,
                "last_name": last_name,
                "year": year,
                "literature_id": row.get("literature_id"),
                "pdf_found": False,
                "affiliation_extracted": None,
                "geocode_success": False,
                "geocode_display_name": None,
                "note": "no PDF found",
            })
            progress[oa_id] = {"status": "no_pdf"}
            continue

        # --- Extract raw text (header) ---------------------------------------
        raw_text = extract_raw_text_from_pdf(pdf_path)
        if raw_text is None:
            debug_rows.append({
                "openalex_author_id": oa_id,
                "display_name": display_name,
                "last_name": last_name,
                "year": year,
                "literature_id": row.get("literature_id"),
                "pdf_found": True,
                "pdf_path": str(pdf_path),
                "affiliation_extracted": None,
                "geocode_success": False,
                "geocode_display_name": None,
                "note": "pdftotext failed / scanned image",
            })
            progress[oa_id] = {"status": "pdf_no_text"}
            continue

        # --- Extract affiliation --------------------------------------------
        affiliation = extract_affiliation(raw_text, last_name)

        if not affiliation:
            debug_rows.append({
                "openalex_author_id": oa_id,
                "display_name": display_name,
                "last_name": last_name,
                "year": year,
                "literature_id": row.get("literature_id"),
                "pdf_found": True,
                "pdf_path": str(pdf_path),
                "affiliation_extracted": None,
                "geocode_success": False,
                "geocode_display_name": None,
                "note": "affiliation not found in header",
            })
            progress[oa_id] = {"status": "no_affiliation"}
            continue

        # --- Geocode --------------------------------------------------------
        geo = geocode(affiliation, rate_limiter)

        debug_rows.append({
            "openalex_author_id": oa_id,
            "display_name": display_name,
            "last_name": last_name,
            "year": year,
            "literature_id": row.get("literature_id"),
            "pdf_found": True,
            "pdf_path": str(pdf_path),
            "affiliation_extracted": affiliation,
            "geocode_success": geo is not None,
            "geocode_display_name": geo["display_name"] if geo else None,
            "note": "ok" if geo else "geocode failed",
        })

        if geo:
            output_rows.append({
                "openalex_author_id": oa_id,
                "last_institution_id": "",
                "last_institution_name": affiliation,
                "last_institution_country": geo["country"],
                "last_institution_city": geo["city"],
                "last_institution_region": geo["region"],
                "last_institution_lat": geo["lat"],
                "last_institution_lon": geo["lon"],
                "last_institution_type": "scraped",
            })
            progress[oa_id] = {"status": "ok", "affiliation": affiliation}
        else:
            progress[oa_id] = {"status": "geocode_failed", "affiliation": affiliation}

    # --- Save outputs -------------------------------------------------------
    logger.info("Writing output CSV: %d rows", len(output_rows))
    out_df = pd.DataFrame(output_rows, columns=[
        "openalex_author_id",
        "last_institution_id",
        "last_institution_name",
        "last_institution_country",
        "last_institution_city",
        "last_institution_region",
        "last_institution_lat",
        "last_institution_lon",
        "last_institution_type",
    ])
    out_df.to_csv(OUTPUT_CSV, index=False)

    logger.info("Writing debug CSV: %d rows", len(debug_rows))
    debug_df = pd.DataFrame(debug_rows)
    debug_df.to_csv(DEBUG_CSV, index=False)

    # Save progress
    with open(PROGRESS_JSON, "w") as f:
        json.dump(progress, f, indent=2)

    # --- Summary ------------------------------------------------------------
    total_processed = len(target_rows)
    geocoded        = len(output_rows)
    no_pdf          = sum(1 for r in debug_rows if r["note"] == "no PDF found")
    no_text         = sum(1 for r in debug_rows if "pdftotext" in (r.get("note") or ""))
    no_affil        = sum(1 for r in debug_rows if r["note"] == "affiliation not found in header")
    geo_failed      = sum(1 for r in debug_rows if r["note"] == "geocode failed")

    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("  Processed this run : %d", total_processed)
    logger.info("  Geocoded (output)  : %d  (%.1f%%)", geocoded,
                100 * geocoded / total_processed if total_processed else 0)
    logger.info("  No PDF             : %d", no_pdf)
    logger.info("  PDF unreadable     : %d", no_text)
    logger.info("  Affiliation missed : %d", no_affil)
    logger.info("  Geocode failed     : %d", geo_failed)
    logger.info("=" * 60)

    if args.limit:
        logger.info("Test run complete. Review %s and %s", OUTPUT_CSV, DEBUG_CSV)
    else:
        logger.info("Full run complete.")


if __name__ == "__main__":
    main()
