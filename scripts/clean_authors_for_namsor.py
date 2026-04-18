#!/usr/bin/env python3
"""
Pre-NamSor cleaning pass for openalex_unique_authors.csv.

Identifies and fixes systemic data quality issues that would waste NamSor
credits or produce bad results. Generates a review spreadsheet with original
vs cleaned values and issue flags.

Issues addressed:
  1. Empty first_name — recover from display_name where possible
  2. Junk / non-person entries — flag for exclusion
  3. Broken name splits (1-char last names) — re-split from display_name
  4. Contaminated first_names — parentheticals, suffixes, daggers, digits
  5. Comma-reversed names — "Surname, First" in first_name field
  6. Non-Latin characters — Cyrillic/Greek homoglyphs → Latin equivalents
  7. Pure Cyrillic names — transliterate or use Latin from display_name
  8. Garbled first_names — institution text, co-author lists in name field
  9. Case normalisation — ALL CAPS → Title Case
 10. Greek epsilon/alpha homoglyphs — replace with Latin equivalents
 11. Trailing/leading punctuation cleanup
 12. Honorific/suffix stripping (Jr., III, Dr., etc.)
 13. Mononym handling — mark Indonesian/single-name authors appropriately
 14. Duplicate display_name flagging (for awareness, not auto-fixed)

Does NOT modify the source CSV. Outputs:
  - outputs/namsor_author_review.xlsx — spreadsheet with before/after + flags
  - outputs/openalex_unique_authors_cleaned.csv — cleaned version ready for NamSor

Usage:
    python3 scripts/clean_authors_for_namsor.py              # full run
    python3 scripts/clean_authors_for_namsor.py --dry-run     # preview counts only
"""

from __future__ import annotations

import argparse
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
UNIQUE_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
OUTPUT_DIR = PROJECT_BASE / "outputs"
LOG_DIR = PROJECT_BASE / "outputs/logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Homoglyph maps ────────────────────────────────────────────────────────

# Greek letters commonly confused with Latin
GREEK_TO_LATIN = {
    "\u0391": "A",  # Α → A
    "\u0392": "B",  # Β → B
    "\u0395": "E",  # Ε → E
    "\u0396": "Z",  # Ζ → Z
    "\u0397": "H",  # Η → H
    "\u0399": "I",  # Ι → I
    "\u039A": "K",  # Κ → K
    "\u039C": "M",  # Μ → M
    "\u039D": "N",  # Ν → N
    "\u039F": "O",  # Ο → O
    "\u03A1": "P",  # Ρ → P
    "\u03A4": "T",  # Τ → T
    "\u03A5": "Y",  # Υ → Y
    "\u03A7": "X",  # Χ → X
    "\u03B1": "a",  # α → a (in mixed context)
    "\u03B5": "e",  # ε → e
    "\u03B9": "i",  # ι → i
    "\u03BA": "k",  # κ → k
    "\u03BF": "o",  # ο → o
    "\u03C1": "p",  # ρ → p (context-dependent)
    "\u03C5": "u",  # υ → u
}

# Cyrillic letters commonly confused with Latin
CYRILLIC_TO_LATIN = {
    "\u0410": "A",  # А → A
    "\u0412": "V",  # В → V  (NOT B — В is "Ve" in Cyrillic)
    "\u0415": "E",  # Е → E
    "\u041A": "K",  # К → K
    "\u041C": "M",  # М → M
    "\u041D": "H",  # Н → H  (Cyrillic Н = Latin H sound)
    "\u041E": "O",  # О → O
    "\u0420": "P",  # Р → P  (Cyrillic Р = Latin R sound, but looks like P)
    "\u0421": "C",  # С → C
    "\u0422": "T",  # Т → T
    "\u0423": "U",  # У → U
    "\u0425": "X",  # Х → X
    "\u0430": "a",  # а → a
    "\u0435": "e",  # е → e
    "\u043E": "o",  # о → o
    "\u0440": "p",  # р → p
    "\u0441": "c",  # с → c
    "\u0443": "u",  # у → u
    "\u0445": "x",  # х → x
    "\u04AF": "y",  # ү → y (Cyrillic barred u, used in Kazakh etc.)
    "\u04E7": "o",  # ӧ → ö → o
}

# Full Cyrillic transliteration (for pure-Cyrillic names)
CYRILLIC_TRANSLIT = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E",
    "Ё": "Yo", "Ж": "Zh", "З": "Z", "И": "I", "Й": "Y", "К": "K",
    "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R",
    "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts",
    "Ч": "Ch", "Ш": "Sh", "Щ": "Shch", "Ъ": "", "Ы": "Y", "Ь": "",
    "Э": "E", "Ю": "Yu", "Я": "Ya",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
    "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
    # Ukrainian
    "І": "I", "і": "i", "Ї": "Yi", "ї": "yi", "Є": "Ye", "є": "ye",
    "Ґ": "G", "ґ": "g",
}


# ─── Junk detection ────────────────────────────────────────────────────────

JUNK_DISPLAY_PATTERNS = re.compile(
    r"(?i)^collective\s+article|^anonymous\b|^editorial\b|^staff\b|^unknown\b"
    r"|^ESA$|^ICES$|^FAO$|^NOAA$|^NMFS$|^CSIRO$|^IUCN$|^CITES$"
    r"|^committee\b|^commission\b|^society\b|^association\b|^council\b"
    r"|^foundation\b|^institute\b|^organi[sz]ation\b|^agency\b|^ministry\b"
    r"|^department\b|^SEAFDEC|^ICCAT"
)

# ─── Helpers ───────────────────────────────────────────────────────────────

_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")


def is_pure_cyrillic(s: str) -> bool:
    """Check if string is entirely Cyrillic (plus spaces/dots)."""
    return bool(s) and all(
        "\u0400" <= c <= "\u04FF" or c in " .\u2010\u2011-" for c in s if c.strip()
    )


def is_pure_latin(s: str) -> bool:
    """Check if string is Latin-script (plus accented, spaces, punctuation)."""
    if not s:
        return False
    for c in s:
        if c.isalpha():
            name = unicodedata.name(c, "")
            if "LATIN" not in name and "MODIFIER" not in name:
                return False
    return True


def has_cyrillic(s: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", s))


def has_greek(s: str) -> bool:
    return bool(re.search(r"[\u0370-\u03FF]", s))


def has_nonlatin_alpha(s: str) -> bool:
    for c in s:
        if c.isalpha():
            name = unicodedata.name(c, "")
            if "LATIN" not in name and "MODIFIER" not in name:
                return True
    return False


def transliterate_cyrillic(s: str) -> str:
    """Transliterate Cyrillic text to Latin."""
    return "".join(CYRILLIC_TRANSLIT.get(c, c) for c in s)


def fix_homoglyphs(s: str) -> str:
    """Replace Greek/Cyrillic homoglyphs with Latin equivalents in mixed-script strings."""
    result = []
    for c in s:
        if c in GREEK_TO_LATIN:
            result.append(GREEK_TO_LATIN[c])
        elif c in CYRILLIC_TO_LATIN:
            result.append(CYRILLIC_TO_LATIN[c])
        else:
            result.append(c)
    return "".join(result)


def extract_parenthetical_name(s: str) -> str | None:
    """Extract a full name from parenthetical: 'Q. (Quentin)' → 'Quentin'."""
    m = re.search(r"\(([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]+)\)", s)
    if m:
        inner = m.group(1).strip()
        # Must be a real name (not Jr., III, author, etc.)
        if len(inner) > 2 and not re.match(r"(?i)^(Jr|Sr|III|II|IV|author|SMT)\b", inner):
            return inner
    return None


def titlecase_name(s: str) -> str:
    """Title-case a name, respecting particles (de, van, von, di, etc.)."""
    particles = {"de", "da", "do", "dos", "das", "van", "von", "der", "di", "del", "la", "le", "el", "al"}
    words = s.split()
    result = []
    for i, w in enumerate(words):
        if w.lower() in particles and i > 0:
            result.append(w.lower())
        elif w.isupper() and len(w) > 2:
            result.append(w.capitalize())
        else:
            result.append(w)
    return " ".join(result)


def is_initials_only(s: str) -> bool:
    """Check if string is all initials (e.g. 'J.', 'J. A.', 'JA', 'J.A.C.')."""
    if not s:
        return True
    parts = s.replace(" ", ".").split(".")
    return all(len(p.strip()) <= 1 for p in parts if p.strip())


# ─── Main cleaning logic ──────────────────────────────────────────────────


def clean_author(row: pd.Series) -> dict:
    """Clean a single author row. Returns dict of cleaned fields + issue flags."""
    dn = str(row.get("display_name", "")).strip()
    fn = str(row.get("first_name", "")).strip()
    ln = str(row.get("last_name", "")).strip()
    country = str(row.get("institution_country", "")).strip()

    # Handle actual NaN
    if fn == "nan":
        fn = ""
    if ln == "nan":
        ln = ""
    if country == "nan":
        country = ""

    issues = []
    c_fn = fn  # cleaned first name
    c_ln = ln  # cleaned last name

    # ── 1. Junk / non-person ───────────────────────────────────────────
    if JUNK_DISPLAY_PATTERNS.search(dn):
        return {
            "clean_first_name": "",
            "clean_last_name": c_ln,
            "issues": "junk_nonperson",
            "exclude_from_namsor": True,
            "notes": f"Non-person entry: {dn}",
        }

    # ── 2. Institution/co-author list in first_name ────────────────────
    if len(c_fn) > 50:
        # Try to recover a real name from display_name
        dn_parts = dn.strip().split()
        if len(dn_parts) >= 2:
            # display_name should be authoritative
            c_fn = " ".join(dn_parts[:-1])
            c_ln = dn_parts[-1]
            issues.append("garbled_fn_recovered_from_display")
        else:
            issues.append("garbled_fn_unrecoverable")
            return {
                "clean_first_name": "",
                "clean_last_name": c_ln,
                "issues": "; ".join(issues),
                "exclude_from_namsor": True,
                "notes": f"Institution/co-author text in first_name",
            }

    # ── 3. Empty first_name — recover from display_name ────────────────
    if not c_fn:
        dn_parts = dn.strip().split()
        if len(dn_parts) >= 2:
            # Check for "Name Name" (duplicated mononym)
            if len(dn_parts) == 2 and dn_parts[0].lower() == dn_parts[1].lower():
                c_fn = dn_parts[0]
                c_ln = dn_parts[1] if c_ln else dn_parts[1]
                issues.append("mononym_duplicated")
            else:
                c_fn = " ".join(dn_parts[:-1])
                if not c_ln or len(c_ln) <= 1:
                    c_ln = dn_parts[-1]
                issues.append("empty_fn_recovered_from_display")
        elif len(dn_parts) == 1:
            # True mononym
            issues.append("mononym")
            return {
                "clean_first_name": dn,
                "clean_last_name": c_ln if c_ln and c_ln != dn else "",
                "issues": "mononym",
                "exclude_from_namsor": False,
                "notes": f"Single-name author (mononym): {dn}",
            }
        else:
            issues.append("empty_fn_unrecoverable")
            return {
                "clean_first_name": "",
                "clean_last_name": c_ln,
                "issues": "empty_fn_unrecoverable",
                "exclude_from_namsor": True,
                "notes": "No name data available",
            }

    # ── 4. Broken name split (1-char last name) ───────────────────────
    if len(c_ln) <= 1 and c_ln != ".":
        dn_parts = dn.strip().split()
        if len(dn_parts) >= 2:
            # The last_name got a single letter that should be an initial.
            # Use display_name to find the longest word (likely real surname),
            # then everything else becomes the first name portion.
            # Find the longest non-initial word as the likely surname
            candidates = [(i, p) for i, p in enumerate(dn_parts) if len(p) > 2]
            if candidates:
                # Take the LAST long word as surname (matches Western name order
                # and Portuguese/Spanish multi-part given names)
                surname_idx, surname = candidates[-1]
                others = [p for i, p in enumerate(dn_parts) if i != surname_idx]
                c_fn = " ".join(others)
                c_ln = surname
                issues.append("broken_split_fixed")
            else:
                issues.append("broken_split_unresolved")

    # ── 5. Contaminated first_name ─────────────────────────────────────

    # 5a. Extract name from parenthetical: "Q. (Quentin)" → "Quentin"
    paren_name = extract_parenthetical_name(c_fn)
    if paren_name:
        c_fn = paren_name
        issues.append("extracted_from_parenthetical")

    # 5b. Remove daggers, death marks, numbered footnotes
    if re.search(r"[†‡✝]", c_fn):
        c_fn = re.sub(r"[†‡✝]", "", c_fn).strip()
        issues.append("removed_dagger")

    if re.search(r"\d", c_fn) and not re.match(r"^[A-Z]\d", c_fn):
        # Remove trailing digits/footnote markers (e.g. "MAGDALENA5")
        c_fn = re.sub(r"\d+$", "", c_fn).strip()
        if re.search(r"\d", c_fn):
            # Still has digits — more aggressive: remove digit sequences
            c_fn = re.sub(r"\(\d+\)", "", c_fn).strip()  # e.g. "(699617)"
        issues.append("removed_digits")

    # 5c. Strip honorifics/suffixes
    c_fn = re.sub(r"\b(?:Dr|Prof|Mr|Mrs|Ms|Sir|Rev)\.?\s*", "", c_fn, flags=re.IGNORECASE).strip()
    c_fn = re.sub(r",?\s*\b(?:Jr|Sr|III|II|IV)\b\.?\s*", "", c_fn).strip()
    c_fn = re.sub(r"\(author\)", "", c_fn, flags=re.IGNORECASE).strip()
    if c_fn != fn and "stripped_honorific" not in issues:
        # Only flag if we actually changed something
        clean_check = re.sub(r"\b(?:Dr|Prof|Mr|Mrs|Ms|Sir|Rev)\.?\s*", "", fn, flags=re.IGNORECASE).strip()
        clean_check = re.sub(r",?\s*\b(?:Jr|Sr|III|II|IV)\b\.?\s*", "", clean_check).strip()
        clean_check = re.sub(r"\(author\)", "", clean_check, flags=re.IGNORECASE).strip()
        if clean_check != fn:
            issues.append("stripped_honorific")

    # ── 6. Comma in first_name (reversed name or co-author junk) ───────
    if "," in c_fn:
        parts = c_fn.split(",", 1)
        before = parts[0].strip()
        after = parts[1].strip()

        # Case: "Surname, Firstname" where before matches last_name
        if before.lower().rstrip(".") == c_ln.lower().rstrip("."):
            c_fn = after
            issues.append("fixed_reversed_name")
        # Case: "Firstname, garbage" — keep just before the comma
        elif len(after) > 30 or re.search(r"\d{4}", after):
            # Likely dates or junk after comma
            c_fn = before
            issues.append("stripped_comma_junk")
        # Case: "Walther Baumann, Dr." — just strip the suffix
        elif re.match(r"(?i)^(Dr|Prof|Mr|Mrs|Ms)\.?$", after):
            c_fn = before
            issues.append("stripped_comma_honorific")
        else:
            # Generic: take the part that looks most like a first name
            # If 'after' is a plausible first name, use it; otherwise keep 'before'
            if len(after.split()) <= 2 and not has_nonlatin_alpha(after):
                c_fn = after
                issues.append("fixed_reversed_name")
            else:
                c_fn = before
                issues.append("stripped_comma_junk")

    # ── 7. Non-Latin character handling ────────────────────────────────

    # 7a. Greek homoglyphs in otherwise Latin names
    if has_greek(c_fn) and not is_pure_cyrillic(c_fn):
        c_fn = fix_homoglyphs(c_fn)
        issues.append("fixed_greek_homoglyphs")
    if has_greek(c_ln) and not is_pure_cyrillic(c_ln):
        c_ln = fix_homoglyphs(c_ln)
        issues.append("fixed_greek_homoglyphs_ln")

    # 7b. Cyrillic homoglyphs in otherwise Latin names
    if has_cyrillic(c_fn) and not is_pure_cyrillic(c_fn):
        c_fn = fix_homoglyphs(c_fn)
        issues.append("fixed_cyrillic_homoglyphs")
    if has_cyrillic(c_ln) and not is_pure_cyrillic(c_ln):
        c_ln = fix_homoglyphs(c_ln)
        issues.append("fixed_cyrillic_homoglyphs_ln")

    # 7c. Pure Cyrillic names — try to get Latin version from first_name
    #     (OpenAlex sometimes stores Latin transliteration in first_name
    #      while display_name/last_name are Cyrillic)
    if is_pure_cyrillic(c_ln):
        # Check if first_name already has a Latin version hidden in it
        # e.g. fn="Malyshkina, Tatiana" ln="Малышкина"
        if is_pure_latin(c_fn):
            # first_name is already Latin — just transliterate last_name
            c_ln = transliterate_cyrillic(c_ln)
            issues.append("transliterated_cyrillic_ln")
        elif is_pure_cyrillic(c_fn):
            # Both Cyrillic — transliterate both
            c_fn = transliterate_cyrillic(c_fn)
            c_ln = transliterate_cyrillic(c_ln)
            issues.append("transliterated_cyrillic_both")
        else:
            # Mixed — try homoglyph fix first
            c_ln = transliterate_cyrillic(c_ln)
            issues.append("transliterated_cyrillic_ln")

    if is_pure_cyrillic(c_fn) and not is_pure_cyrillic(c_ln):
        c_fn = transliterate_cyrillic(c_fn)
        issues.append("transliterated_cyrillic_fn")

    # ── 8. Case normalisation ──────────────────────────────────────────
    if c_fn and c_fn == c_fn.upper() and len(c_fn) > 2:
        c_fn = titlecase_name(c_fn)
        issues.append("case_normalised_fn")
    if c_ln and c_ln == c_ln.upper() and len(c_ln) > 2:
        c_ln = titlecase_name(c_ln)
        issues.append("case_normalised_ln")

    # Also fix all-lowercase
    if c_fn and c_fn == c_fn.lower() and len(c_fn) > 2 and not any(c_fn.startswith(p) for p in ["de ", "van ", "von "]):
        c_fn = titlecase_name(c_fn.title())
        issues.append("case_normalised_fn")
    if c_ln and c_ln == c_ln.lower() and len(c_ln) > 2:
        c_ln = c_ln.capitalize()
        issues.append("case_normalised_ln")

    # ── 9. Trailing/leading punctuation ────────────────────────────────
    c_fn = c_fn.strip(" ,;")
    c_ln = c_ln.strip(" ,;")
    # Strip leading/trailing dots only if not part of initials
    # Use unicode letter class to catch accented initials (Ø., Á., etc.)
    if c_fn.endswith(".") and not re.search(r"\p{L}\.$" if False else r"(?u)\w\.$", c_fn):
        c_fn = c_fn.rstrip(".")
    if c_fn.startswith("."):
        c_fn = c_fn.lstrip(".")
    if c_ln == ".":
        c_ln = ""
    elif c_ln.endswith(".") and not re.search(r"(?u)\w\.$", c_ln):
        c_ln = c_ln.rstrip(".")

    # ── 10. Final cleanup ──────────────────────────────────────────────
    c_fn = re.sub(r"\s{2,}", " ", c_fn).strip()
    c_ln = re.sub(r"\s{2,}", " ", c_ln).strip()

    # Determine if this should be excluded from NamSor
    exclude = False
    notes_parts = []

    if not c_fn and not c_ln:
        exclude = True
        notes_parts.append("No usable name data")
    elif is_initials_only(c_fn):
        # NamSor can still work with initials + last name, but less accurate
        notes_parts.append("Initials only — NamSor may produce low-confidence results")

    return {
        "clean_first_name": c_fn,
        "clean_last_name": c_ln,
        "issues": "; ".join(issues) if issues else "",
        "exclude_from_namsor": exclude,
        "notes": "; ".join(notes_parts) if notes_parts else "",
    }


# ─── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-NamSor author name cleaning")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts only")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(LOG_DIR / f"clean_authors_namsor_{today}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(fh)

    log.info("=== Pre-NamSor author cleaning: %s ===", today)

    ua = pd.read_csv(UNIQUE_AUTHORS, dtype=str).fillna("")
    # Also replace literal "nan" strings left from prior float→str conversion
    for col in ["first_name", "last_name", "display_name", "institution_country"]:
        ua[col] = ua[col].replace("nan", "")
    log.info("Loaded %d unique authors", len(ua))

    # Process every row
    results = []
    for idx, row in ua.iterrows():
        cleaned = clean_author(row)
        results.append({
            "row_index": idx,
            "openalex_author_id": row.get("openalex_author_id", ""),
            "display_name": row.get("display_name", ""),
            "orig_first_name": row.get("first_name", ""),
            "orig_last_name": row.get("last_name", ""),
            "clean_first_name": cleaned["clean_first_name"],
            "clean_last_name": cleaned["clean_last_name"],
            "institution_country": row.get("institution_country", ""),
            "gender": row.get("gender", ""),
            "issues": cleaned["issues"],
            "exclude_from_namsor": cleaned["exclude_from_namsor"],
            "notes": cleaned["notes"],
            "fn_changed": row.get("first_name", "") != cleaned["clean_first_name"],
            "ln_changed": row.get("last_name", "") != cleaned["clean_last_name"],
        })

    df = pd.DataFrame(results)

    # ── Summary statistics ─────────────────────────────────────────────
    changed = df[df["fn_changed"] | df["ln_changed"]]
    excluded = df[df["exclude_from_namsor"]]
    issues_any = df[df["issues"] != ""]

    log.info("\n%s", "=" * 60)
    log.info("SUMMARY")
    log.info("%s", "=" * 60)
    log.info("Total authors:         %d", len(df))
    log.info("Authors with changes:  %d (%.1f%%)", len(changed), len(changed) / len(df) * 100)
    log.info("Authors with issues:   %d (%.1f%%)", len(issues_any), len(issues_any) / len(df) * 100)
    log.info("Excluded from NamSor:  %d", len(excluded))
    log.info("Ready for NamSor:      %d", len(df) - len(excluded))

    # Issue breakdown
    from collections import Counter
    issue_counts = Counter()
    for issues_str in df["issues"]:
        if issues_str:
            for issue in issues_str.split("; "):
                issue_counts[issue.strip()] += 1

    log.info("\nIssue breakdown:")
    for issue, count in issue_counts.most_common():
        log.info("  %-45s %d", issue, count)

    if args.dry_run:
        log.info("\nDRY RUN — no files written")
        # Print summary to stdout too
        print(f"\nAuthors with changes:  {len(changed)}")
        print(f"Excluded from NamSor:  {len(excluded)}")
        print(f"Ready for NamSor:      {len(df) - len(excluded)}")
        print("\nIssue breakdown:")
        for issue, count in issue_counts.most_common():
            print(f"  {issue}: {count}")
        return

    # ── Write cleaned CSV ──────────────────────────────────────────────
    cleaned_df = ua.copy()
    for _, r in df.iterrows():
        idx = r["row_index"]
        cleaned_df.at[idx, "first_name"] = r["clean_first_name"]
        cleaned_df.at[idx, "last_name"] = r["clean_last_name"]

    cleaned_path = OUTPUT_DIR / "openalex_unique_authors_cleaned.csv"
    cleaned_df.to_csv(cleaned_path, index=False)
    log.info("Cleaned CSV saved: %s", cleaned_path)

    # ── Write review spreadsheet ───────────────────────────────────────
    # Only include rows with changes or issues for review
    review_df = df[df["fn_changed"] | df["ln_changed"] | (df["issues"] != "")].copy()
    # Sort: excluded first, then by issue type
    review_df = review_df.sort_values(
        ["exclude_from_namsor", "issues", "display_name"],
        ascending=[False, True, True],
    )

    xlsx_path = OUTPUT_DIR / "namsor_author_review.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Sheet 1: All changes for review
        review_cols = [
            "display_name", "orig_first_name", "clean_first_name",
            "orig_last_name", "clean_last_name", "institution_country",
            "gender", "issues", "exclude_from_namsor", "notes",
            "openalex_author_id",
        ]
        review_df[review_cols].to_excel(writer, sheet_name="Changes", index=False)

        # Sheet 2: All rows going to NamSor (cleaned names + country codes)
        ready_df = df[~df["exclude_from_namsor"]].copy()
        ready_cols = [
            "display_name", "clean_first_name", "clean_last_name",
            "institution_country", "gender", "issues", "notes",
            "openalex_author_id",
        ]
        ready_df[ready_cols].sort_values("display_name").to_excel(
            writer, sheet_name="Ready for NamSor", index=False,
        )

        # Sheet 3: Excluded entries
        excl_df = df[df["exclude_from_namsor"]].copy()
        excl_df[review_cols].to_excel(writer, sheet_name="Excluded", index=False)

        # Sheet 4: Summary stats
        summary_data = [
            ["Total authors", len(df)],
            ["Authors with changes", len(changed)],
            ["Authors with issues", len(issues_any)],
            ["Excluded from NamSor", len(excluded)],
            ["Ready for NamSor", len(df) - len(excluded)],
            ["", ""],
            ["Issue", "Count"],
        ]
        for issue, count in issue_counts.most_common():
            summary_data.append([issue, count])
        summary_df = pd.DataFrame(summary_data, columns=["Metric", "Value"])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col_idx, col in enumerate(ws.columns, 1):
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

    log.info("Review spreadsheet saved: %s", xlsx_path)
    print(f"\nDone. Review: {xlsx_path}")
    print(f"Cleaned CSV: {cleaned_path}")
    print(f"Changes: {len(changed)}, Excluded: {len(excluded)}, Ready: {len(df) - len(excluded)}")


if __name__ == "__main__":
    main()
