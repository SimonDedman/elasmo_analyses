#!/usr/bin/env python3
"""Match journals from our elasmobranch literature database to SCImago rankings.

Reads SCImago Journal Rank (SJR) data (semicolon-delimited, European comma
decimals) and fuzzy-matches our journal names to extract quality indicators
(SJR score, quartile, H-index, subject areas, open access status).

Usage:
    python scripts/lookup_scimago_journals.py

Prerequisites:
    - Download SCImago data manually from https://www.scimagojr.com/journalrank.php?out=xls
    - Save as data/journal_quality/scimagojr.csv (semicolon-delimited)
    - pip install duckdb pandas

Outputs:
    - data/journal_quality/scimago_match.csv
    - data/journal_quality/scimago_unmatched.csv  (with best fuzzy match columns)
    - data/journal_quality/scimago_book_chapters.csv
    - data/journal_quality/scimago_theses.csv
    - data/journal_quality/scimago_grey_literature.csv
    - data/journal_quality/scimago_summary.txt
"""

from __future__ import annotations

import csv
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
DB_PATH = BASE_DIR / "outputs" / "literature_review.duckdb"
QUALITY_DIR = BASE_DIR / "data" / "journal_quality"
SCIMAGO_PATH = QUALITY_DIR / "scimagojr.csv"

OUTPUT_MATCHED = QUALITY_DIR / "scimago_match.csv"
OUTPUT_UNMATCHED = QUALITY_DIR / "scimago_unmatched.csv"
OUTPUT_BOOK_CHAPTERS = QUALITY_DIR / "scimago_book_chapters.csv"
OUTPUT_THESES = QUALITY_DIR / "scimago_theses.csv"
OUTPUT_GREY_LIT = QUALITY_DIR / "scimago_grey_literature.csv"
OUTPUT_SUMMARY = QUALITY_DIR / "scimago_summary.txt"

# ---------------------------------------------------------------------------
# Known journal aliases: our name -> SCImago title
# Journals renamed, merged, or commonly abbreviated differently.
# ---------------------------------------------------------------------------
JOURNAL_ALIASES: dict[str, str] = {
    # Renamed journals
    "copeia": "ichthyology and herpetology",
    # Truncated names (our DB has short form, SCImago has full)
    "palaeogeography": "palaeogeography palaeoclimatology palaeoecology",
    "mitochondrial dna": "mitochondrial dna part a dna mapping sequencing and analysis",
    "mitochondrial dna part b": "mitochondrial dna part b resources",
    "american journal of physiology regulatory":
        "american journal of physiology regulatory integrative and comparative physiology",
    "journal of comparative physiology b biochemical":
        "journal of comparative physiology b biochemical systemic and environmental physiology",
    "journal of comparative physiology a neuroethology":
        "journal of comparative physiology a neuroethology sensory neural and behavioral physiology",
    "comparative biochemistry and physiology":
        "comparative biochemistry and physiology part a molecular and integrative physiology",
    # Partial names for CBP sub-journals (en-dash stripped to space)
    "comparative biochemistry and physiology part a":
        "comparative biochemistry and physiology part a molecular and integrative physiology",
    "comparative biochemistry and physiology part b":
        "comparative biochemistry and physiology part b biochemistry and molecular biology",
    "comparative biochemistry and physiology part c":
        "comparative biochemistry and physiology part c toxicology and pharmacology",
    # German journal with umlaut variations
    "neues jahrbuch fur geologie und palaontologie":
        "neues jahrbuch fur geologie und palaontologie abhandlungen",
    # Society proceedings (not in SCImago but commonly cited)
    # Marine biodiversity records was merged into Marine Biodiversity
    "marine biodiversity records": "marine biodiversity",
    # Renames / historical titles
    "journal du conseil international pour lexploration de la mer": "ices journal of marine science",
    "journal du conseil": "ices journal of marine science",
    "senckenbergiana maritima": "marine biodiversity",
    # Acronyms
    "jmba": "journal of the marine biological association of the united kingdom",
}

# ---------------------------------------------------------------------------
# Abbreviation expansions for normalisation
# ---------------------------------------------------------------------------
ABBREVIATIONS: dict[str, str] = {
    "j.": "journal",
    "j ": "journal ",
    "proc.": "proceedings",
    "proc ": "proceedings ",
    "trans.": "transactions",
    "trans ": "transactions ",
    "bull.": "bulletin",
    "bull ": "bulletin ",
    "ann.": "annals",
    "ann ": "annals ",
    "rev.": "review",
    "rev ": "review ",
    "sci.": "science",
    "sci ": "science ",
    "res.": "research",
    "res ": "research ",
    "int.": "international",
    "int ": "international ",
    "natl.": "national",
    "nat.": "natural",
    "biol.": "biology",
    "biol ": "biology ",
    "ecol.": "ecology",
    "ecol ": "ecology ",
    "zool.": "zoology",
    "zool ": "zoology ",
    "mar.": "marine",
    "mar ": "marine ",
    "fish.": "fisheries",
    "environ.": "environmental",
    "environ ": "environmental ",
    "conserv.": "conservation",
    "conserv ": "conservation ",
    "comp.": "comparative",
    "comp ": "comparative ",
    "physiol.": "physiology",
    "physiol ": "physiology ",
    "biochem.": "biochemistry",
    "biochem ": "biochemistry ",
    "soc.": "society",
    "soc ": "society ",
    "amer.": "american",
    "am.": "american",
    "brit.": "british",
    "aust.": "australian",
    "acad.": "academy",
    "univ.": "university",
    "dept.": "department",
    "dev.": "development",
    "dev ": "development ",
    "exp.": "experimental",
    "exp ": "experimental ",
    "gen.": "general",
    "gen ": "general ",
    "mus.": "museum",
    "hist.": "history",
    "lett.": "letters",
    "lett ": "letters ",
    "mol.": "molecular",
    "mol ": "molecular ",
    "chem.": "chemistry",
    "chem ": "chemistry ",
    "phys.": "physics",
    "phys ": "physics ",
    "tech.": "technology",
    "tech ": "technology ",
    "appl.": "applied",
    "appl ": "applied ",
    "syst.": "systematic",
    "syst ": "systematic ",
    "vet.": "veterinary",
    "vet ": "veterinary ",
    "aquat.": "aquatic",
    "freshw.": "freshwater",
    "oceanogr.": "oceanography",
    "palaeontol.": "palaeontology",
    "paleontol.": "paleontology",
    "ichthyol.": "ichthyology",
    "herpetol.": "herpetology",
}


def normalise(name: str) -> str:
    """Normalise a journal name for matching.

    Lowercases, strips leading 'the ', expands abbreviations,
    normalises ampersands and whitespace, and removes punctuation.
    """
    s = name.lower().strip()
    # Strip leading "the "
    if s.startswith("the "):
        s = s[4:]
    # Replace & with "and"
    s = s.replace("&", "and")
    # Replace en-dash / em-dash / regular hyphens with space
    s = s.replace("\u2013", " ").replace("\u2014", " ").replace("-", " ")
    # Normalise common unicode characters to ASCII equivalents
    unicode_map = {
        "\u00fc": "u",  # ü -> u
        "\u00e4": "a",  # ä -> a
        "\u00f6": "o",  # ö -> o
        "\u00e9": "e",  # é -> e
        "\u00e8": "e",  # è -> e
        "\u00ea": "e",  # ê -> e
        "\u00e0": "a",  # à -> a
        "\u00e2": "a",  # â -> a
        "\u00f4": "o",  # ô -> o
        "\u00e7": "c",  # ç -> c
        "\u00f1": "n",  # ñ -> n
        "\u00df": "ss", # ß -> ss
        "\u00e6": "ae", # æ -> ae
        "\u00f8": "o",  # ø -> o
        "\u00e5": "a",  # å -> a
    }
    for char, repl in unicode_map.items():
        s = s.replace(char, repl)
    # Strip parenthetical suffixes like (Stockholm), (London), etc.
    s = re.sub(r"\([^)]*\)\s*$", "", s)
    # Expand abbreviations (order matters: do dotted first)
    for abbr, full in sorted(ABBREVIATIONS.items(), key=lambda x: -len(x[0])):
        s = s.replace(abbr, full)
    # Remove remaining punctuation except hyphens
    s = re.sub(r"[^\w\s-]", "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_comma_decimal(value: str) -> Optional[float]:
    """Parse a European-format decimal (comma as separator) to float.

    Args:
        value: String like '145,004' meaning 145.004, or empty/NaN.

    Returns:
        Float value or None if unparseable.
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value or value.lower() == "nan":
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def is_book_chapter(journal_name: str) -> bool:
    """Check if a journal name is actually a book chapter reference.

    Book chapters in the database start with 'In ' followed by an
    author name, book title, or conference proceedings.
    """
    stripped = journal_name.strip()
    if not stripped.startswith("In "):
        return False
    # "In " followed by uppercase letter (author/title) is a book chapter.
    # Exclude actual journal names that happen to start with "In" (rare).
    rest = stripped[3:]
    if not rest:
        return True
    # Check if what follows looks like a journal name vs an author/book
    # Actual journals: "Integrative...", "Insects" etc. would not match
    # because they don't start with "In " (space after In).
    return True


# ---------------------------------------------------------------------------
# Thesis patterns (case-insensitive)
# ---------------------------------------------------------------------------
THESIS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bthesis\b",
        r"\bph\.?d\.?\s*thesis\b",
        r"\bdoctoral\s+thesis\b",
        r"\bmasters?\s+thesis\b",
        r"\bm\.?sc\.?\s*thesis\b",
        r"\bdissertation\b",
        r"\btesis\s+doctoral\b",
        r"\btesis\s+de\s+maestria\b",
        r"\bhonours?\s+thesis\b",
    ]
]

# ---------------------------------------------------------------------------
# Grey literature patterns (case-insensitive)
# ---------------------------------------------------------------------------
GREY_LIT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"NOAA\s+Technical\s+Memorandum",
        r"NOAA\s+Tech\.?\s+Memo",
        r"\bSEDAR\b",
        r"\bAFMA\b",
        r"\bDAFF\b",
        r"SPC\s+Fisheries\s+Newsletter",
        r"FAO\s+Fisheries",
        r"FAO\s+Fish",
        r"\bTechnical\s+Report\b",
        r"\bWorking\s+Paper\b",
        r"\bFossilien\b",
    ]
]


def is_thesis(journal_name: str) -> bool:
    """Check if a journal name is actually a thesis or dissertation.

    Args:
        journal_name: Raw journal name string.

    Returns:
        True if the entry matches any thesis pattern.
    """
    return any(pat.search(journal_name) for pat in THESIS_PATTERNS)


def is_grey_literature(journal_name: str) -> bool:
    """Check if a journal name is grey literature (reports, tech docs).

    Args:
        journal_name: Raw journal name string.

    Returns:
        True if the entry matches any grey literature pattern.
    """
    return any(pat.search(journal_name) for pat in GREY_LIT_PATTERNS)


def extract_our_journals(db_path: Path) -> pd.DataFrame:
    """Extract unique journal names and paper counts from the database."""
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute(
        """
        SELECT journal, COUNT(*) AS paper_count
        FROM literature_review
        WHERE journal IS NOT NULL AND journal != ''
        GROUP BY journal
        ORDER BY paper_count DESC
        """
    ).fetchdf()
    con.close()
    return df


def load_scimago(path: Path) -> pd.DataFrame:
    """Load SCImago CSV (semicolon-delimited).

    Tries UTF-8 first, falls back to latin-1.
    """
    for encoding in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, sep=";", dtype=str, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError(f"Could not read {path} with UTF-8 or latin-1 encoding")

    # Standardise column names to lowercase with underscores
    df.columns = [c.strip() for c in df.columns]
    return df


def build_scimago_lookup(
    scimago_df: pd.DataFrame,
) -> dict[str, dict]:
    """Build a normalised-name -> row lookup from SCImago data.

    Also indexes by substring (journal name before colon/dash) for
    partial matching.
    """
    lookup: dict[str, dict] = {}
    for _, row in scimago_df.iterrows():
        title = str(row.get("Title", "")).strip()
        if not title:
            continue
        norm = normalise(title)

        # Parse SJR score (European comma decimal)
        sjr_raw = str(row.get("SJR", "")).strip()
        sjr_float = parse_comma_decimal(sjr_raw)

        record = {
            "scimago_title": title,
            "sjr_score": sjr_float,
            "quartile": str(row.get("SJR Best Quartile", "")).strip(),
            "h_index": str(row.get("H index", "")).strip(),
            "subject_areas": str(row.get("Areas", "")).strip(),
            "open_access": str(row.get("Open Access", "")).strip(),
            "categories": str(row.get("Categories", "")).strip(),
            "normalised": norm,
        }
        lookup[norm] = record
    return lookup


def build_substring_index(scimago_lookup: dict[str, dict]) -> dict[str, str]:
    """Build an index of shortened names -> full normalised keys.

    For SCImago titles like "Aquatic Conservation: Marine and Freshwater
    Ecosystems", also indexes "aquatic conservation" to help match our
    truncated journal names.
    """
    sub_index: dict[str, str] = {}
    for norm_key, record in scimago_lookup.items():
        title = record["scimago_title"]
        # Split on colon, dash, or parenthesis and use the first part
        for sep in [":", " - ", " — ", " – ", "("]:
            if sep in title:
                prefix = title.split(sep)[0].strip()
                prefix_norm = normalise(prefix)
                if prefix_norm and prefix_norm != norm_key and len(prefix_norm) >= 5:
                    # Don't overwrite if already present (keep first/best)
                    if prefix_norm not in sub_index:
                        sub_index[prefix_norm] = norm_key
    return sub_index


def _build_word_index(keys: list[str]) -> dict[str, list[str]]:
    """Build an index from first word to list of normalised keys.

    This dramatically reduces the search space for fuzzy matching.
    """
    index: dict[str, list[str]] = {}
    for key in keys:
        first_word = key.split()[0] if key.split() else ""
        if first_word:
            index.setdefault(first_word, []).append(key)
    return index


def _build_two_word_index(keys: list[str]) -> dict[str, list[str]]:
    """Build an index from first two words to list of normalised keys.

    Supplements the single-word index for more precise candidate selection.
    """
    index: dict[str, list[str]] = {}
    for key in keys:
        words = key.split()
        if len(words) >= 2:
            two_word = f"{words[0]} {words[1]}"
            index.setdefault(two_word, []).append(key)
    return index


def find_best_fuzzy_match(
    norm: str,
    scimago_keys: list[str],
    word_index: dict[str, list[str]],
    two_word_index: dict[str, list[str]],
    paper_count: int,
) -> tuple[Optional[str], float]:
    """Find the best fuzzy match for a normalised journal name.

    Returns (best_key, best_score). Score will be 0.0 if no match found.
    """
    best_score = 0.0
    best_key: Optional[str] = None

    words = norm.split()
    first_word = words[0] if words else ""

    # Pass A: candidates sharing the same first word (fast)
    candidates = set(word_index.get(first_word, []))

    # Also add two-word index candidates
    if len(words) >= 2:
        two_word = f"{words[0]} {words[1]}"
        candidates.update(two_word_index.get(two_word, []))

    for skey in candidates:
        len_ratio = len(norm) / max(len(skey), 1)
        if len_ratio < 0.3 or len_ratio > 3.0:
            continue
        score = SequenceMatcher(None, norm, skey).ratio()
        if score > best_score:
            best_score = score
            best_key = skey

    # Pass B: brute-force only for high-value journals (>=10 papers)
    # that didn't get a good match from the word index
    if best_score < 0.85 and paper_count >= 10:
        norm_len = len(norm)
        for skey in scimago_keys:
            skey_len = len(skey)
            if abs(norm_len - skey_len) > max(norm_len, skey_len) * 0.4:
                continue
            score = SequenceMatcher(None, norm, skey).ratio()
            if score > best_score:
                best_score = score
                best_key = skey
                if score >= 0.95:
                    break  # good enough, stop searching

    return best_key, best_score


def match_journals(
    our_journals: pd.DataFrame,
    scimago_lookup: dict[str, dict],
    fuzzy_threshold: float = 0.85,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Match our journal names against SCImago entries.

    Uses a multi-pass strategy:
      0a. Filter out book chapters (starting with "In ")
      0b. Filter out theses and dissertations
      0c. Filter out grey literature (reports, tech docs)
      1. Exact normalised match
      2. Check known journal aliases
      3. Substring/prefix match (e.g. truncated journal names)
      4. Fuzzy match with two passes (first-word index, then brute force)

    For unmatched journals, always records the best fuzzy match and score.

    Returns (matched, unmatched, book_chapters, theses, grey_literature).
    """
    matched: list[dict] = []
    unmatched: list[dict] = []
    book_chapters: list[dict] = []
    theses: list[dict] = []
    grey_literature: list[dict] = []

    scimago_keys = list(scimago_lookup.keys())
    word_index = _build_word_index(scimago_keys)
    two_word_index = _build_two_word_index(scimago_keys)
    sub_index = build_substring_index(scimago_lookup)

    total = len(our_journals)
    exact_count = 0
    alias_count = 0
    substring_count = 0
    fuzzy_count = 0
    t0 = time.time()

    for i, (_, row) in enumerate(our_journals.iterrows()):
        our_name = str(row["journal"]).strip()
        paper_count = int(row["paper_count"])
        norm = normalise(our_name)

        # 0a. Filter out book chapters
        if is_book_chapter(our_name):
            book_chapters.append({
                "our_journal_name": our_name,
                "paper_count": paper_count,
            })
            continue

        # Also filter bare "In"
        if our_name.strip() == "In":
            book_chapters.append({
                "our_journal_name": our_name,
                "paper_count": paper_count,
            })
            continue

        # 0b. Filter out theses and dissertations
        if is_thesis(our_name):
            theses.append({
                "our_journal_name": our_name,
                "paper_count": paper_count,
            })
            continue

        # 0c. Filter out grey literature
        if is_grey_literature(our_name):
            grey_literature.append({
                "our_journal_name": our_name,
                "paper_count": paper_count,
            })
            continue

        if not norm:
            unmatched.append({
                "our_journal_name": our_name,
                "paper_count": paper_count,
                "best_scimago_match": "",
                "best_match_score": 0.0,
                "best_match_quartile": "",
            })
            continue

        # 1. Exact normalised match
        if norm in scimago_lookup:
            rec = scimago_lookup[norm]
            matched.append({
                "our_journal_name": our_name,
                "scimago_title": rec["scimago_title"],
                "sjr_score": rec["sjr_score"],
                "quartile": rec["quartile"],
                "h_index": rec["h_index"],
                "subject_areas": rec["subject_areas"],
                "open_access": rec["open_access"],
                "match_type": "exact",
                "match_score": 1.0,
                "paper_count": paper_count,
            })
            exact_count += 1
            continue

        # 2. Known alias lookup
        alias_target = JOURNAL_ALIASES.get(norm)
        if alias_target and alias_target in scimago_lookup:
            rec = scimago_lookup[alias_target]
            matched.append({
                "our_journal_name": our_name,
                "scimago_title": rec["scimago_title"],
                "sjr_score": rec["sjr_score"],
                "quartile": rec["quartile"],
                "h_index": rec["h_index"],
                "subject_areas": rec["subject_areas"],
                "open_access": rec["open_access"],
                "match_type": "alias",
                "match_score": 1.0,
                "paper_count": paper_count,
            })
            alias_count += 1
            continue

        # 3. Substring/prefix match (our name is a prefix of SCImago title)
        if norm in sub_index:
            full_key = sub_index[norm]
            if full_key in scimago_lookup:
                rec = scimago_lookup[full_key]
                matched.append({
                    "our_journal_name": our_name,
                    "scimago_title": rec["scimago_title"],
                    "sjr_score": rec["sjr_score"],
                    "quartile": rec["quartile"],
                    "h_index": rec["h_index"],
                    "subject_areas": rec["subject_areas"],
                    "open_access": rec["open_access"],
                    "match_type": "substring",
                    "match_score": 0.95,
                    "paper_count": paper_count,
                })
                substring_count += 1
                continue

        # 4. Fuzzy match (always find best, even if below threshold)
        best_key, best_score = find_best_fuzzy_match(
            norm, scimago_keys, word_index, two_word_index, paper_count
        )

        if best_key is not None and best_score >= fuzzy_threshold:
            rec = scimago_lookup[best_key]
            matched.append({
                "our_journal_name": our_name,
                "scimago_title": rec["scimago_title"],
                "sjr_score": rec["sjr_score"],
                "quartile": rec["quartile"],
                "h_index": rec["h_index"],
                "subject_areas": rec["subject_areas"],
                "open_access": rec["open_access"],
                "match_type": "fuzzy",
                "match_score": round(best_score, 4),
                "paper_count": paper_count,
            })
            fuzzy_count += 1
        else:
            # Record unmatched with best fuzzy match for review
            if best_key is not None:
                rec = scimago_lookup[best_key]
                unmatched.append({
                    "our_journal_name": our_name,
                    "paper_count": paper_count,
                    "best_scimago_match": rec["scimago_title"],
                    "best_match_score": round(best_score, 4),
                    "best_match_quartile": rec["quartile"],
                })
            else:
                unmatched.append({
                    "our_journal_name": our_name,
                    "paper_count": paper_count,
                    "best_scimago_match": "",
                    "best_match_score": 0.0,
                    "best_match_quartile": "",
                })

        # Progress reporting every 500 journals
        if (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (total - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i + 1:,}/{total:,}] "
                f"{exact_count} exact + {alias_count} alias + "
                f"{substring_count} substring + {fuzzy_count} fuzzy matched, "
                f"~{remaining:.0f}s remaining"
            )

    return matched, unmatched, book_chapters, theses, grey_literature


def write_summary(
    matched: list[dict],
    unmatched: list[dict],
    book_chapters: list[dict],
    theses: list[dict],
    grey_literature: list[dict],
    total_papers: int,
    output_path: Path,
) -> None:
    """Write a summary of the matching results."""
    n_matched = len(matched)
    n_unmatched = len(unmatched)
    n_book_chapters = len(book_chapters)
    n_theses = len(theses)
    n_grey_lit = len(grey_literature)
    n_total = n_matched + n_unmatched + n_book_chapters + n_theses + n_grey_lit

    papers_matched = sum(m["paper_count"] for m in matched)
    papers_unmatched = sum(u["paper_count"] for u in unmatched)
    papers_book_chapters = sum(b["paper_count"] for b in book_chapters)
    papers_theses = sum(t["paper_count"] for t in theses)
    papers_grey_lit = sum(g["paper_count"] for g in grey_literature)

    exact_count = sum(1 for m in matched if m["match_type"] == "exact")
    alias_count = sum(1 for m in matched if m["match_type"] == "alias")
    substring_count = sum(1 for m in matched if m["match_type"] == "substring")
    fuzzy_count = sum(1 for m in matched if m["match_type"] == "fuzzy")

    # Quartile distribution
    quartile_counts: dict[str, int] = {}
    quartile_papers: dict[str, int] = {}
    for m in matched:
        q = str(m["quartile"]).strip() or "Unknown"
        quartile_counts[q] = quartile_counts.get(q, 0) + 1
        quartile_papers[q] = quartile_papers.get(q, 0) + m["paper_count"]

    # Mean SJR
    sjr_values = [m["sjr_score"] for m in matched if m["sjr_score"] is not None]
    mean_sjr = sum(sjr_values) / len(sjr_values) if sjr_values else 0.0
    median_sjr = sorted(sjr_values)[len(sjr_values) // 2] if sjr_values else 0.0

    # Open access distribution
    oa_counts: dict[str, int] = {}
    for m in matched:
        oa = str(m["open_access"]).strip() or "Unknown"
        oa_counts[oa] = oa_counts.get(oa, 0) + 1

    # Denominator for match % excludes filtered-out categories
    matchable = n_matched + n_unmatched

    lines = [
        "SCImago Journal Matching Summary",
        "=" * 60,
        "",
        f"Total unique journals in database:     {n_total:,}",
        f"Book chapters (filtered out):          {n_book_chapters:,} ({papers_book_chapters:,} papers)",
        f"Theses / dissertations (filtered out): {n_theses:,} ({papers_theses:,} papers)",
        f"Grey literature (filtered out):        {n_grey_lit:,} ({papers_grey_lit:,} papers)",
        "",
        f"Matched to SCImago:                    {n_matched:,} ({100 * n_matched / max(matchable, 1):.1f}%)",
        f"  - Exact matches:                     {exact_count:,}",
        f"  - Alias matches:                     {alias_count:,}",
        f"  - Substring matches:                 {substring_count:,}",
        f"  - Fuzzy matches (>=0.85):            {fuzzy_count:,}",
        f"Unmatched (excl. filtered):            {n_unmatched:,} ({100 * n_unmatched / max(matchable, 1):.1f}%)",
        "",
        f"Total papers in database:              {total_papers:,}",
        f"Papers with matched journals:          {papers_matched:,} ({100 * papers_matched / total_papers:.1f}%)",
        f"Papers with unmatched journals:        {papers_unmatched:,} ({100 * papers_unmatched / total_papers:.1f}%)",
        f"Papers in book chapters:               {papers_book_chapters:,} ({100 * papers_book_chapters / total_papers:.1f}%)",
        f"Papers in theses:                      {papers_theses:,} ({100 * papers_theses / total_papers:.1f}%)",
        f"Papers in grey literature:             {papers_grey_lit:,} ({100 * papers_grey_lit / total_papers:.1f}%)",
        "",
        f"SJR Score (matched journals)",
        "-" * 60,
        f"  Mean:   {mean_sjr:.3f}",
        f"  Median: {median_sjr:.3f}",
        "",
        "Quartile Distribution (matched journals)",
        "-" * 60,
    ]
    for q in sorted(quartile_counts.keys()):
        jcount = quartile_counts[q]
        pcount = quartile_papers[q]
        lines.append(f"  {q:>8s}:  {jcount:>5,} journals  ({pcount:>6,} papers)")

    lines.extend([
        "",
        "Open Access Distribution (matched journals)",
        "-" * 60,
    ])
    for oa in sorted(oa_counts.keys()):
        lines.append(f"  {oa:>12s}:  {oa_counts[oa]:>5,} journals")

    # Top 20 matched journals by paper count
    lines.extend([
        "",
        "Top 20 Matched Journals (by paper count)",
        "-" * 60,
    ])
    top_matched = sorted(matched, key=lambda x: -x["paper_count"])[:20]
    for m in top_matched:
        sjr_str = f"{m['sjr_score']:.3f}" if m["sjr_score"] is not None else "N/A"
        lines.append(
            f"  {m['paper_count']:>5d}  {m['quartile']:>3s}  "
            f"SJR {sjr_str:>7s}  {m['our_journal_name']}"
            + (f"  [via {m['match_type']}]" if m["match_type"] != "exact" else "")
        )

    # Top 20 unmatched by paper count (with best fuzzy match)
    lines.extend([
        "",
        "Top 20 Unmatched Journals (by paper count)",
        "-" * 60,
    ])
    top_unmatched = sorted(unmatched, key=lambda x: -x["paper_count"])[:20]
    for u in top_unmatched:
        best = u.get("best_scimago_match", "")
        score = u.get("best_match_score", 0.0)
        if best:
            lines.append(
                f"  {u['paper_count']:>5d}  {u['our_journal_name']}"
                f"  -> {best} ({score:.3f})"
            )
        else:
            lines.append(f"  {u['paper_count']:>5d}  {u['our_journal_name']}  (no match)")

    summary_text = "\n".join(lines) + "\n"
    output_path.write_text(summary_text, encoding="utf-8")
    print(summary_text)


def main() -> None:
    """Run the journal matching pipeline."""
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)

    # Check SCImago file exists
    if not SCIMAGO_PATH.exists():
        print(
            f"ERROR: SCImago data not found at {SCIMAGO_PATH}\n"
            "Please download from https://www.scimagojr.com/journalrank.php?out=xls\n"
            f"and save to {SCIMAGO_PATH}"
        )
        sys.exit(1)

    # Validate it's not HTML (Cloudflare block)
    with open(SCIMAGO_PATH, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
    if first_line.strip().startswith("<!DOCTYPE") or "<html" in first_line[:200]:
        print(
            f"ERROR: {SCIMAGO_PATH} appears to be HTML (Cloudflare block).\n"
            "Please download manually from your browser:\n"
            "  https://www.scimagojr.com/journalrank.php?out=xls\n"
            f"and save to {SCIMAGO_PATH}"
        )
        sys.exit(1)

    print("Loading our journal data from DuckDB...")
    our_journals = extract_our_journals(DB_PATH)
    total_papers = int(our_journals["paper_count"].sum())
    print(f"  Found {len(our_journals):,} unique journals across {total_papers:,} papers")

    print(f"\nLoading SCImago data from {SCIMAGO_PATH}...")
    scimago_df = load_scimago(SCIMAGO_PATH)
    print(f"  Found {len(scimago_df):,} SCImago entries")

    print("\nBuilding normalised lookup...")
    scimago_lookup = build_scimago_lookup(scimago_df)
    print(f"  {len(scimago_lookup):,} unique normalised entries")

    print("\nMatching journals (this may take a few minutes for fuzzy matching)...")
    t0 = time.time()
    matched, unmatched, book_chapters, theses, grey_literature = match_journals(
        our_journals, scimago_lookup
    )
    elapsed = time.time() - t0
    print(f"  Matching completed in {elapsed:.1f}s")

    # Write matched
    print(f"\nWriting {len(matched):,} matched journals to {OUTPUT_MATCHED}")
    matched_df = pd.DataFrame(matched)
    if not matched_df.empty:
        matched_df = matched_df.sort_values("paper_count", ascending=False)
    matched_df.to_csv(OUTPUT_MATCHED, index=False, quoting=csv.QUOTE_ALL)

    # Write unmatched (with best fuzzy match columns)
    print(f"Writing {len(unmatched):,} unmatched journals to {OUTPUT_UNMATCHED}")
    unmatched_df = pd.DataFrame(unmatched)
    if not unmatched_df.empty:
        unmatched_df = unmatched_df.sort_values("paper_count", ascending=False)
    # Ensure column order
    unmatched_cols = [
        "our_journal_name", "paper_count",
        "best_scimago_match", "best_match_score", "best_match_quartile",
    ]
    for col in unmatched_cols:
        if col not in unmatched_df.columns:
            unmatched_df[col] = ""
    unmatched_df = unmatched_df[unmatched_cols]
    unmatched_df.to_csv(OUTPUT_UNMATCHED, index=False, quoting=csv.QUOTE_ALL)

    # Write book chapters
    print(f"Writing {len(book_chapters):,} book chapters to {OUTPUT_BOOK_CHAPTERS}")
    book_df = pd.DataFrame(book_chapters)
    if not book_df.empty:
        book_df = book_df.sort_values("paper_count", ascending=False)
    book_df.to_csv(OUTPUT_BOOK_CHAPTERS, index=False, quoting=csv.QUOTE_ALL)

    # Write theses
    print(f"Writing {len(theses):,} theses to {OUTPUT_THESES}")
    theses_df = pd.DataFrame(theses)
    if not theses_df.empty:
        theses_df = theses_df.sort_values("paper_count", ascending=False)
    theses_df.to_csv(OUTPUT_THESES, index=False, quoting=csv.QUOTE_ALL)

    # Write grey literature
    print(f"Writing {len(grey_literature):,} grey literature entries to {OUTPUT_GREY_LIT}")
    grey_df = pd.DataFrame(grey_literature)
    if not grey_df.empty:
        grey_df = grey_df.sort_values("paper_count", ascending=False)
    grey_df.to_csv(OUTPUT_GREY_LIT, index=False, quoting=csv.QUOTE_ALL)

    # Write summary
    print(f"Writing summary to {OUTPUT_SUMMARY}\n")
    write_summary(
        matched, unmatched, book_chapters, theses, grey_literature,
        total_papers, OUTPUT_SUMMARY,
    )

    print("Done.")


if __name__ == "__main__":
    main()
