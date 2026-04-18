#!/usr/bin/env python3
"""
Deep resolution of initials-only author names before NamSor enrichment.

Strategies (applied in order):
  1. OpenAlex author profiles — display_name_alternatives (recovers ~72%)
  2. CrossRef DOI lookup — full author names from publication metadata
  3. Semantic Scholar — author profiles with full names

Updates openalex_unique_authors_cleaned.csv in place.
Generates a report of what was resolved and what remains.

Usage:
    python3 scripts/resolve_initials_deep.py              # full run
    python3 scripts/resolve_initials_deep.py --dry-run     # preview only
    python3 scripts/resolve_initials_deep.py --limit 50    # test with fewer
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
UNIQUE_AUTHORS_CLEANED = PROJECT_BASE / "outputs/openalex_unique_authors_cleaned.csv"
UNIQUE_AUTHORS_RAW = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
LOG_DIR = PROJECT_BASE / "outputs/logs"
REPORT_PATH = PROJECT_BASE / "outputs/initials_resolution_report.csv"

OPENALEX_API = "https://api.openalex.org/authors"
CROSSREF_API = "https://api.crossref.org/works"
S2_API = "https://api.semanticscholar.org/graph/v1/author/search"

BATCH_SIZE = 50  # OpenAlex max per request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_initials_only(s: str) -> bool:
    """Check if string is all initials (e.g. 'J.', 'J. A.', 'JA', 'J.A.C.')."""
    if not s or not s.strip():
        return True
    parts = s.replace(" ", ".").split(".")
    return all(len(p.strip()) <= 1 for p in parts if p.strip())


def extract_initials(s: str) -> str:
    """Extract initials from a name string: 'J. A.' -> 'JA', 'John' -> 'J'."""
    if not s:
        return ""
    parts = s.replace(".", " ").split()
    return "".join(p[0].upper() for p in parts if p)


def initials_match(initials: str, full_name: str) -> bool:
    """Check if initials match the start of a full name.

    'J. A.' should match 'John Andrew' but not 'Peter John'.
    """
    if not initials or not full_name:
        return False
    init = extract_initials(initials)
    full_parts = full_name.replace(".", " ").split()
    full_init = "".join(p[0].upper() for p in full_parts if p and len(p) > 0)

    # Initials must match from the start
    return full_init.startswith(init) or init.startswith(full_init)


def name_quality_score(name: str) -> int:
    """Score a name by how 'full' it is. Higher = better."""
    if not name:
        return 0
    parts = name.replace(".", " ").split()
    score = 0
    for p in parts:
        p = p.strip()
        if len(p) <= 1:
            score += 1  # initial
        elif len(p) == 2 and p.isupper():
            score += 1  # likely initials like 'JA'
        else:
            score += len(p)  # real name part
    return score


def _fix_camelcase(s: str) -> str:
    """Split CamelCase names: 'CarlA' -> 'Carl A.', 'EleanorJane' -> 'Eleanor Jane'."""
    if not s or " " in s or "." in s:
        return s
    # Insert space before uppercase letters that follow lowercase
    fixed = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return fixed


def _has_real_name_part(s: str) -> bool:
    """Check that at least one word in s is a real name (>1 char, not initials)."""
    parts = s.replace(".", " ").split()
    return any(len(p.strip()) > 1 and not (len(p) == 2 and p.isupper()) for p in parts)


def extract_best_first_name(alternatives: list[str], last_name: str,
                            current_initials: str) -> str | None:
    """From OpenAlex alternatives, extract the best first name matching initials."""
    if not alternatives or not last_name:
        return None

    ln_lower = last_name.strip().lower()
    candidates = []

    for alt in alternatives:
        alt = str(alt).strip()
        if not alt:
            continue

        # Reject co-author contamination (commas in non-"Surname, First" positions)
        if "," in alt:
            parts = alt.split(",", 1)
            if parts[0].strip().lower() == ln_lower:
                first = parts[1].strip()
                # Reject if after-comma part also has commas (multiple people)
                if "," in first:
                    continue
            else:
                continue  # Skip — comma but not in "Surname, First" form
        else:
            words = alt.split()
            first_words = []
            found_ln = False
            for w in words:
                if w.strip().lower() == ln_lower and not found_ln:
                    found_ln = True
                    break
                first_words.append(w)

            if not found_ln:
                if words and words[-1].strip().lower() == ln_lower:
                    first_words = words[:-1]
                else:
                    continue

            first = " ".join(first_words).strip()

        if not first:
            continue

        # Fix CamelCase merges (e.g. "CarlA" -> "Carl A.")
        first = _fix_camelcase(first)

        # Reject if too short (garbage like "DD")
        if len(first.replace(".", "").replace(" ", "")) < 3:
            continue

        # Check if it's still just initials
        if is_initials_only(first):
            continue

        # Must have at least one real name part (not just initials)
        if not _has_real_name_part(first):
            continue

        # Check initials match
        if current_initials and not initials_match(current_initials, first):
            continue

        score = name_quality_score(first)
        candidates.append((first, score))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


# ---------------------------------------------------------------------------
# Strategy 1: OpenAlex author profiles
# ---------------------------------------------------------------------------

def resolve_via_openalex(authors_df: pd.DataFrame) -> dict[int, str]:
    """Query OpenAlex author profiles for full names."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "mailto:simondedman@gmail.com (EEA Data Panel research)",
    })

    # Build ID list
    author_ids = []
    id_to_idx = {}
    for idx, row in authors_df.iterrows():
        oa_url = str(row.get("openalex_author_id", ""))
        if oa_url.startswith("http"):
            aid = oa_url.replace("https://openalex.org/", "").strip()
            if aid:
                author_ids.append(aid)
                id_to_idx[aid] = idx

    log.info("[OpenAlex] Querying %d author profiles...", len(author_ids))

    oa_data = {}
    for i in range(0, len(author_ids), BATCH_SIZE):
        batch = author_ids[i:i + BATCH_SIZE]
        id_filter = "|".join(batch)

        try:
            resp = session.get(
                OPENALEX_API,
                params={
                    "filter": f"ids.openalex:{id_filter}",
                    "per_page": BATCH_SIZE,
                    "select": "id,display_name,display_name_alternatives,orcid",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for author in data.get("results", []):
                aid = author["id"].replace("https://openalex.org/", "")
                oa_data[aid] = {
                    "display_name": author.get("display_name", ""),
                    "alternatives": author.get("display_name_alternatives", []),
                    "orcid": author.get("orcid"),
                }
        except Exception as e:
            log.warning("OpenAlex batch %d failed: %s", i // BATCH_SIZE + 1, e)

        if i + BATCH_SIZE < len(author_ids):
            time.sleep(0.2)

        if (i // BATCH_SIZE + 1) % 10 == 0:
            log.info("  Fetched %d/%d", min(i + BATCH_SIZE, len(author_ids)),
                     len(author_ids))

    log.info("[OpenAlex] Received %d profiles", len(oa_data))

    # Extract full names
    resolved = {}
    for aid, profile in oa_data.items():
        idx = id_to_idx.get(aid)
        if idx is None:
            continue

        row = authors_df.loc[idx]
        last_name = str(row["last_name"]) if pd.notna(row["last_name"]) else ""
        current_fn = str(row["first_name"]) if pd.notna(row["first_name"]) else ""

        # Also check the display_name itself (sometimes it has the full name)
        dn = profile["display_name"]
        alternatives = profile["alternatives"]
        if dn:
            alternatives = [dn] + alternatives

        full_first = extract_best_first_name(alternatives, last_name, current_fn)
        if full_first:
            resolved[idx] = full_first

    log.info("[OpenAlex] Resolved %d / %d", len(resolved), len(authors_df))
    return resolved


# ---------------------------------------------------------------------------
# Strategy 2: CrossRef DOI lookup
# ---------------------------------------------------------------------------

def resolve_via_crossref(authors_df: pd.DataFrame,
                         paper_authors: pd.DataFrame) -> dict[int, str]:
    """Look up full author names from CrossRef using DOIs."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "mailto:simondedman@gmail.com (EEA Data Panel research)",
    })

    # For each initials-only author, find their DOIs
    author_dois = {}
    for idx, row in authors_df.iterrows():
        oa_id = str(row.get("openalex_author_id", ""))
        if not oa_id:
            continue
        pa_rows = paper_authors[paper_authors["openalex_author_id"] == oa_id]
        dois = pa_rows["doi"].dropna().unique()
        dois = [d for d in dois if d and str(d).strip()]
        if dois:
            author_dois[idx] = {
                "dois": list(dois[:3]),  # limit to 3 DOIs per author
                "last_name": str(row["last_name"]),
                "first_name": str(row["first_name"]),
            }

    log.info("[CrossRef] Looking up %d authors via %d DOIs...",
             len(author_dois),
             sum(len(v["dois"]) for v in author_dois.values()))

    resolved = {}
    total_queries = 0

    for idx, info in author_dois.items():
        if idx in resolved:
            continue

        for doi in info["dois"]:
            doi = doi.strip()
            if not doi.startswith("10."):
                # Try extracting from URL
                if "doi.org/" in doi:
                    doi = doi.split("doi.org/", 1)[1]
                else:
                    continue

            try:
                resp = session.get(
                    f"{CROSSREF_API}/{doi}",
                    timeout=15,
                )
                total_queries += 1

                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json().get("message", {})

                # Search author list for matching last name
                for author in data.get("author", []):
                    cr_family = author.get("family", "").strip()
                    cr_given = author.get("given", "").strip()

                    if not cr_family or not cr_given:
                        continue

                    # Match by last name
                    if cr_family.lower() != info["last_name"].lower():
                        continue

                    # Check initials match
                    if not initials_match(info["first_name"], cr_given):
                        continue

                    # Check it's actually a full name
                    if is_initials_only(cr_given):
                        continue

                    # Found a full name!
                    resolved[idx] = cr_given
                    break

                if idx in resolved:
                    break

            except requests.RequestException:
                continue

            time.sleep(0.05)  # polite delay for CrossRef

        # Progress
        if total_queries % 100 == 0 and total_queries > 0:
            log.info("  CrossRef: %d queries, %d resolved so far",
                     total_queries, len(resolved))

    log.info("[CrossRef] Resolved %d / %d (%d API queries)",
             len(resolved), len(author_dois), total_queries)
    return resolved


# ---------------------------------------------------------------------------
# Strategy 3: Semantic Scholar search
# ---------------------------------------------------------------------------

def resolve_via_semantic_scholar(authors_df: pd.DataFrame) -> dict[int, str]:
    """Search Semantic Scholar for author profiles with full names."""
    session = requests.Session()

    resolved = {}
    queries = 0

    for idx, row in authors_df.iterrows():
        fn = str(row["first_name"]).strip()
        ln = str(row["last_name"]).strip()
        if not ln:
            continue

        # Search by "initials + last name"
        query = f"{fn} {ln}"
        try:
            resp = session.get(
                S2_API,
                params={"query": query, "limit": 5},
                timeout=15,
            )
            queries += 1

            if resp.status_code == 429:
                log.warning("Semantic Scholar rate limited, waiting 60s...")
                time.sleep(60)
                resp = session.get(
                    S2_API,
                    params={"query": query, "limit": 5},
                    timeout=15,
                )
                queries += 1

            if resp.status_code != 200:
                continue

            data = resp.json()
            for author in data.get("data", []):
                s2_name = author.get("name", "")
                if not s2_name:
                    continue

                # Extract first name portion
                parts = s2_name.split()
                if len(parts) < 2:
                    continue

                # Check last name matches
                if parts[-1].lower() != ln.lower():
                    continue

                s2_first = " ".join(parts[:-1])
                if is_initials_only(s2_first):
                    continue

                if initials_match(fn, s2_first):
                    resolved[idx] = s2_first
                    break

        except requests.RequestException:
            continue

        # Semantic Scholar has stricter rate limits
        time.sleep(0.5)

        if queries % 50 == 0 and queries > 0:
            log.info("  S2: %d queries, %d resolved so far", queries, len(resolved))

    log.info("[Semantic Scholar] Resolved %d / %d (%d queries)",
             len(resolved), len(authors_df), queries)
    return resolved


# ---------------------------------------------------------------------------
# Title-case cleanup
# ---------------------------------------------------------------------------

def clean_resolved_name(name: str) -> str:
    """Clean up a resolved name: normalise case, strip junk."""
    if not name:
        return name

    # Fix ALL CAPS
    if name == name.upper() and len(name) > 2:
        name = name.title()

    # Fix trailing dots/commas
    name = name.strip(" ,;.")

    # Collapse whitespace
    name = re.sub(r"\s{2,}", " ", name)

    return name


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deep resolution of initials-only author names"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--limit", type=int, default=None, help="Limit authors")
    parser.add_argument(
        "--skip-crossref", action="store_true",
        help="Skip CrossRef lookups (slow)",
    )
    parser.add_argument(
        "--skip-s2", action="store_true",
        help="Skip Semantic Scholar lookups",
    )
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(LOG_DIR / f"resolve_initials_deep_{today}.log")
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    ))
    log.addHandler(fh)

    log.info("=" * 60)
    log.info("Deep initials resolution")
    log.info("Mode: %s", "DRY RUN" if args.dry_run else "LIVE")
    log.info("=" * 60)

    # Load data
    ua = pd.read_csv(UNIQUE_AUTHORS_CLEANED, dtype=str).fillna("")
    pa = pd.read_csv(PAPER_AUTHORS, dtype=str).fillna("")

    # Find initials-only authors
    mask = ua["first_name"].apply(is_initials_only)
    initials_df = ua[mask].copy()

    if args.limit:
        initials_df = initials_df.head(args.limit)

    log.info("Total authors: %d", len(ua))
    log.info("Initials-only: %d", len(initials_df))

    if initials_df.empty:
        log.info("No initials-only authors to resolve!")
        return

    if args.dry_run:
        log.info("DRY RUN — would query OpenAlex, CrossRef, Semantic Scholar")
        print(f"\nInitials-only authors: {len(initials_df)}")
        print("Would query: OpenAlex, CrossRef, Semantic Scholar")
        return

    # Track all resolutions with source
    all_resolved: dict[int, tuple[str, str]] = {}  # idx -> (name, source)
    remaining = initials_df

    # --- Strategy 1: OpenAlex ---
    oa_resolved = resolve_via_openalex(remaining)
    for idx, name in oa_resolved.items():
        all_resolved[idx] = (clean_resolved_name(name), "openalex")
    remaining = remaining[~remaining.index.isin(oa_resolved.keys())]
    log.info("After OpenAlex: %d resolved, %d remaining",
             len(all_resolved), len(remaining))

    # --- Strategy 2: CrossRef ---
    if not args.skip_crossref and len(remaining) > 0:
        cr_resolved = resolve_via_crossref(remaining, pa)
        for idx, name in cr_resolved.items():
            all_resolved[idx] = (clean_resolved_name(name), "crossref")
        remaining = remaining[~remaining.index.isin(cr_resolved.keys())]
        log.info("After CrossRef: %d resolved, %d remaining",
                 len(all_resolved), len(remaining))

    # --- Strategy 3: Semantic Scholar ---
    if not args.skip_s2 and len(remaining) > 0:
        s2_resolved = resolve_via_semantic_scholar(remaining)
        for idx, name in s2_resolved.items():
            all_resolved[idx] = (clean_resolved_name(name), "semantic_scholar")
        remaining = remaining[~remaining.index.isin(s2_resolved.keys())]
        log.info("After Semantic Scholar: %d resolved, %d remaining",
                 len(all_resolved), len(remaining))

    # --- Apply updates ---
    log.info("\n%s", "=" * 60)
    log.info("RESULTS")
    log.info("%s", "=" * 60)
    log.info("Total resolved: %d / %d (%.1f%%)",
             len(all_resolved), len(initials_df),
             100 * len(all_resolved) / len(initials_df) if initials_df.shape[0] else 0)

    # Source breakdown
    sources = {}
    for _, (_, src) in all_resolved.items():
        sources[src] = sources.get(src, 0) + 1
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        log.info("  %-20s %d", src, count)
    log.info("  %-20s %d", "unresolved", len(remaining))

    # Show examples
    examples = list(all_resolved.items())[:20]
    if examples:
        log.info("\nExamples:")
        for idx, (name, src) in examples:
            row = initials_df.loc[idx] if idx in initials_df.index else ua.loc[idx]
            log.info("  %s %s -> %s [%s]",
                     row["first_name"], row["last_name"], name, src)

    # Update the cleaned CSV
    update_count = 0
    for idx, (name, src) in all_resolved.items():
        ua.at[idx, "first_name"] = name
        update_count += 1

    ua.to_csv(UNIQUE_AUTHORS_CLEANED, index=False)
    log.info("\nUpdated %d first names in %s", update_count,
             UNIQUE_AUTHORS_CLEANED.name)

    # Also update the raw unique authors CSV
    ua_raw = pd.read_csv(UNIQUE_AUTHORS_RAW, dtype=str).fillna("")
    raw_updates = 0
    for idx, (name, src) in all_resolved.items():
        if idx < len(ua_raw):
            ua_raw.at[idx, "first_name"] = name
            raw_updates += 1
    ua_raw.to_csv(UNIQUE_AUTHORS_RAW, index=False)
    log.info("Updated %d first names in %s", raw_updates,
             UNIQUE_AUTHORS_RAW.name)

    # Generate report
    report_rows = []
    for idx in initials_df.index:
        row = initials_df.loc[idx]
        if idx in all_resolved:
            name, src = all_resolved[idx]
            report_rows.append({
                "openalex_author_id": row["openalex_author_id"],
                "display_name": row["display_name"],
                "original_first_name": row["first_name"],
                "resolved_first_name": name,
                "last_name": row["last_name"],
                "source": src,
                "status": "resolved",
            })
        else:
            report_rows.append({
                "openalex_author_id": row["openalex_author_id"],
                "display_name": row["display_name"],
                "original_first_name": row["first_name"],
                "resolved_first_name": "",
                "last_name": row["last_name"],
                "source": "",
                "status": "unresolved",
            })

    report = pd.DataFrame(report_rows)
    report.to_csv(REPORT_PATH, index=False)
    log.info("Report saved: %s", REPORT_PATH)

    # Final count of remaining initials
    ua_final = pd.read_csv(UNIQUE_AUTHORS_CLEANED, dtype=str).fillna("")
    still_initials = ua_final["first_name"].apply(is_initials_only).sum()
    log.info("\nFinal initials-only count: %d (was %d)", still_initials,
             len(initials_df))

    print(f"\nResolved: {len(all_resolved)} / {len(initials_df)}")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")
    print(f"  unresolved: {len(remaining)}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    sys.exit(main() or 0)
