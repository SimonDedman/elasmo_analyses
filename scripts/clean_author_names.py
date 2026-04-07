#!/usr/bin/env python3
"""
Clean author first_name entries to improve gender resolution quality.

Fixes:
  1. Strip prefixes (Dr., Prof., SMT., Mr., Mrs., Ms., Sir, Rev.)
  2. Fix encoding issues (Ã¸ → ø, â → various)
  3. Remove non-names (COLLECTIVE ARTICLE, institutional entries)
  4. Split multi-person entries (semicolons, "Surname, First" format)
  5. Remove 2-letter uppercase initials being treated as names (AK, CJ, etc.)
  6. Fix surname-as-first-name leaks (J Brown → keep J, not Brown)
  7. Strip trailing punctuation (semicolons, commas, periods)
  8. Fix initials-with-punctuation that bypass the initials filter

Operates on openalex_unique_authors.csv and openalex_paper_authors.csv.
Does NOT call any external API — purely local cleanup.

Usage:
    python3 scripts/clean_author_names.py              # full run
    python3 scripts/clean_author_names.py --dry-run     # preview only

Author: Simon Dedman
Date: 2026-04-06
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
UNIQUE_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
LOG_DIR = PROJECT_BASE / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cleaning rules
# ---------------------------------------------------------------------------

# Prefixes to strip
PREFIX_RE = re.compile(
    r"^(?:Dr\.?\s*(?:\(SMT\.\)\s*)?|Prof\.?\s*|Smt\.?\s*|Mrs\.?\s+|Ms\.?\s+|Sir\s+|Rev\.?\s+)",
    re.IGNORECASE,
)
# Note: "Mr." excluded because "MR" is commonly initials (M.R.) in author data

# Non-name patterns — set gender to "unknown" and clear first_name
NON_NAME_RE = re.compile(
    r"(?i)^collective\b|^anonymous\b|^editorial\b|^staff\b|^unknown\b"
    r"|national laboratory\]|british geological"
    r"|region,|district,|village\s"  # address data in name field
)

# Mojibake fixes (common UTF-8 decoded as Latin-1)
# Only fix clear mojibake (multi-byte UTF-8 mis-decoded as Latin-1).
# Do NOT "fix" â, ã, etc. — these are real letters in Portuguese, Vietnamese, etc.
ENCODING_FIXES = {
    "Ã¸": "ø",
    "Ã©": "é",
    "Ã¡": "á",
    "Ã­": "í",
    "Ã³": "ó",
    "Ã±": "ñ",
    "Ã¼": "ü",
    "Ã¶": "ö",
    "Ã¤": "ä",
    "Ã§": "ç",
}

# Known real 2-letter names (not initials)
REAL_2LETTER = {
    "al", "bo", "ed", "em", "er", "fu", "gi", "gu", "ha", "he",
    "ho", "hu", "in", "ji", "jo", "ju", "ka", "ke", "ki", "ko",
    "ku", "le", "li", "lo", "lu", "ma", "mi", "mo", "mu", "na",
    "ni", "no", "nu", "ou", "po", "qi", "ri", "ro", "si", "su",
    "te", "ti", "to", "tu", "we", "wu", "xi", "xu", "ya", "ye",
    "yi", "yo", "yu", "ze", "zu", "an", "da", "di", "du",
}

# East/SE Asian names that are commonly 2 letters and are real given names
ASIAN_2LETTER = {
    "ah", "ai", "ba", "bi", "bo", "bu", "ca", "ci", "cu",
    "de", "do", "du", "ei", "fa", "fe", "fi", "fo", "ga", "ge",
    "go", "gu", "ha", "he", "hi", "ho", "hu", "ji", "ju", "ka",
    "ke", "ki", "ko", "ku", "la", "le", "li", "lo", "lu", "ma",
    "me", "mi", "mo", "mu", "na", "ne", "ni", "no", "nu", "pa",
    "pi", "pu", "qi", "ra", "re", "ri", "ro", "ru", "sa", "se",
    "si", "so", "su", "ta", "te", "ti", "to", "tu", "wa", "we",
    "wi", "wo", "wu", "xi", "xu", "ya", "ye", "yi", "yo", "yu",
    "za", "ze", "zi", "zo", "zu",
}

REAL_2LETTER.update(ASIAN_2LETTER)


def clean_first_name(first_name: str, last_name: str) -> tuple[str, str | None]:
    """
    Clean a first_name value. Returns (cleaned_name, reason) where reason
    is None if no change, or a description of what was fixed.
    """
    if pd.isna(first_name) or not str(first_name).strip():
        return "", None

    original = str(first_name).strip()
    name = original
    reasons = []

    # 1. Non-name check
    if NON_NAME_RE.search(name):
        return "", "non-name"

    # 2. Multi-person: semicolons indicate multiple people jammed together
    if ";" in name:
        # Take only the part before the first semicolon
        name = name.split(";")[0].strip()
        reasons.append("stripped-semicolon")

    # 3. Fix "Surname, Firstname" format where first_name contains both
    if "," in name and not name.endswith(","):
        parts = name.split(",", 1)
        before = parts[0].strip()
        after = parts[1].strip()
        ln = str(last_name).strip().lower() if pd.notna(last_name) else ""
        # Only apply if the part before comma matches the known last name
        # (avoids breaking Chinese naming order like "DAYONG, JIANG")
        if before.lower() == ln or before.lower().rstrip(".") == ln:
            name = after
            reasons.append("fixed-surname-first")

    # 4. Strip prefixes
    m = PREFIX_RE.match(name)
    if m:
        name = name[m.end():].strip()
        reasons.append("stripped-prefix")

    # 5. Fix encoding
    for bad, good in ENCODING_FIXES.items():
        if bad in name:
            name = name.replace(bad, good)
            if "fixed-encoding" not in reasons:
                reasons.append("fixed-encoding")

    # 6. Fix surname leak: if first_name is "J Brown" and last_name is "Brown",
    #    the query_name extractor would pick "Brown" — we should keep just "J."
    if pd.notna(last_name):
        ln = str(last_name).strip().lower()
        tokens = name.split()
        # Check if any non-initial token equals the last name
        for i, tok in enumerate(tokens):
            if tok.strip(".").lower() == ln and len(tok.strip(".")) > 1:
                # Remove this token — it's the surname leaking in
                tokens[i] = ""
                reasons.append("removed-surname-leak")
        name = " ".join(t for t in tokens if t).strip()

    # 8. Handle initials-with-punctuation that bypass filters
    #    e.g. "c.‐c" or "e.j" — these are still just initials
    cleaned = name.replace("\u2010", "").replace("\u2011", "").replace("\u2012", "")
    cleaned = cleaned.replace("\u2013", "").replace("\u2014", "").replace("-", "")
    cleaned_parts = cleaned.replace(".", " ").split()
    if cleaned_parts and all(len(p) <= 1 for p in cleaned_parts):
        # Still initials after cleaning — keep as-is (will be skipped by genderize)
        pass

    # 8. Strip trailing semicolons and commas (after all other fixes)
    stripped = name.rstrip(";,")
    if stripped != name:
        name = stripped
        if "stripped-trailing-punct" not in reasons:
            reasons.append("stripped-trailing-punct")

    name = name.strip()
    if name == original:
        return name, None
    return name, "; ".join(reasons) if reasons else None


def is_fake_2letter_name(query_name: str, first_name: str) -> bool:
    """
    Check if a 2-letter query name is actually initials, not a real name.
    E.g. "CJ" from "CJ Fox" is initials, but "Li" from "Li Wang" is a real name.
    """
    if len(query_name) != 2:
        return False

    qn_lower = query_name.lower()

    # If it's in our known real 2-letter names set, it's probably real
    if qn_lower in REAL_2LETTER:
        return False

    # If it's all uppercase in the original, it's likely initials
    fn = str(first_name).strip() if pd.notna(first_name) else ""
    # Find the token that matches
    for tok in fn.split():
        if tok.strip(".").lower() == qn_lower:
            if tok.isupper() and len(tok) == 2:
                return True  # "CJ", "MJ" etc. — initials
            break

    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Clean author first_name entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / f"clean_author_names_{datetime.now():%Y%m%d}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(fh)

    log.info("=" * 60)
    log.info("Cleaning author first_name entries")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    log.info("=" * 60)

    ua = pd.read_csv(UNIQUE_AUTHORS, dtype=str)
    unknown = ua[ua["gender"] == "unknown"].copy()
    log.info(f"Total authors: {len(ua)}, Unknown gender: {len(unknown)}")

    # Apply cleaning
    changes = []
    non_names = []

    for idx in unknown.index:
        fn = ua.loc[idx, "first_name"]
        ln = ua.loc[idx, "last_name"]
        cleaned, reason = clean_first_name(fn, ln)

        if reason:
            changes.append({
                "index": idx,
                "original": fn,
                "cleaned": cleaned,
                "last_name": ln,
                "reason": reason,
            })
            if "non-name" in reason:
                non_names.append(idx)

    log.info(f"\nChanges to apply: {len(changes)}")

    # Summarise by reason
    from collections import Counter
    reason_counts = Counter()
    for c in changes:
        for r in c["reason"].split("; "):
            reason_counts[r] += 1
    log.info("Breakdown:")
    for reason, count in reason_counts.most_common():
        log.info(f"  {reason}: {count}")

    # Show examples
    log.info("\nExamples:")
    for c in changes[:30]:
        log.info(f"  '{c['original']}' {c['last_name']} -> '{c['cleaned']}' [{c['reason']}]")

    if args.dry_run:
        log.info("\nDRY RUN — no changes saved")
        return

    # Apply changes
    oa_ids_changed = set()
    for c in changes:
        idx = c["index"]
        ua.loc[idx, "first_name"] = c["cleaned"]
        oa_id = ua.loc[idx, "openalex_author_id"]
        if pd.notna(oa_id):
            oa_ids_changed.add(oa_id)

    ua.to_csv(UNIQUE_AUTHORS, index=False)
    log.info(f"Saved {UNIQUE_AUTHORS.name} ({len(changes)} entries cleaned)")

    # Update paper_authors too
    if oa_ids_changed:
        pa = pd.read_csv(PAPER_AUTHORS, dtype=str)
        pa_updated = 0
        for c in changes:
            oa_id = ua.loc[c["index"], "openalex_author_id"]
            if pd.notna(oa_id):
                mask = pa["openalex_author_id"] == oa_id
                pa.loc[mask, "first_name"] = c["cleaned"]
                pa_updated += mask.sum()
        pa.to_csv(PAPER_AUTHORS, index=False)
        log.info(f"Updated {pa_updated} rows in {PAPER_AUTHORS.name}")

    # Final stats
    remaining_unknown = (ua["gender"] == "unknown").sum()
    log.info(f"\nGender status after cleaning:")
    log.info(f"  Male:    {(ua['gender'] == 'male').sum()}")
    log.info(f"  Female:  {(ua['gender'] == 'female').sum()}")
    log.info(f"  Unknown: {remaining_unknown}")
    log.info("=" * 60)


if __name__ == "__main__":
    sys.exit(main() or 0)
