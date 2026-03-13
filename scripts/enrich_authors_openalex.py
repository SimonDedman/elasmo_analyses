#!/usr/bin/env python3
"""Enrich the paper database with author metadata from OpenAlex.

Queries the OpenAlex API by DOI (in batches of up to 50) to retrieve
structured author information for every paper in the literature review.
Outputs two CSV files:

    1. openalex_paper_authors.csv   -- one row per (paper, author)
    2. openalex_unique_authors.csv  -- deduplicated by OpenAlex author ID

Uses the OpenAlex polite pool (includes mailto in requests) and respects
their rate limits with conservative throttling (max 10 req/s default).

Usage:
    python scripts/enrich_authors_openalex.py
    python scripts/enrich_authors_openalex.py --dry-run 200
    python scripts/enrich_authors_openalex.py --resume
    python scripts/enrich_authors_openalex.py --batch-size 25 --rate-limit 5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
INPUT_PARQUET = PROJECT_BASE / "outputs/literature_review.parquet"
OUTPUT_PAPER_AUTHORS = PROJECT_BASE / "outputs/openalex_paper_authors.csv"
OUTPUT_UNIQUE_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
PROGRESS_FILE = PROJECT_BASE / "outputs/.openalex_progress.json"

# OpenAlex polite pool — include mailto for priority queue.
# No API key required; polite pool gives ~10 req/s.
CONTACT_EMAIL = "simondedman@gmail.com"
OPENALEX_API_BASE = "https://api.openalex.org"

# Rate limiting: OpenAlex polite pool allows ~10 req/s.
# We default to 10 req/s but this is configurable via CLI.
DEFAULT_RATE_LIMIT = 10  # requests per second
DEFAULT_BATCH_SIZE = 50  # max DOIs per batch request (OpenAlex limit)
BACKOFF_BASE = 1.0  # seconds to wait on 429 errors
MAX_RETRIES = 5  # retries per batch on transient errors
SAVE_EVERY = 500  # save progress every N papers processed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AuthorRecord:
    """A single author-paper association extracted from OpenAlex."""

    literature_id: int
    doi: str
    author_position: str  # first, middle, last
    display_name: str
    first_name: str
    last_name: str
    openalex_author_id: str
    institution_name: str
    institution_country: str
    institution_type: str


# ---------------------------------------------------------------------------
# Name parsing
# ---------------------------------------------------------------------------

def parse_author_name(display_name: str) -> tuple[str, str]:
    """Split a display name into (first_name, last_name).

    Handles common patterns:
        - "Jane Smith"        -> ("Jane", "Smith")
        - "Jane A. Smith"     -> ("Jane A.", "Smith")
        - "Smith"             -> ("", "Smith")
        - ""                  -> ("", "")

    Args:
        display_name: Full author name as returned by OpenAlex.

    Returns:
        Tuple of (first_name, last_name).
    """
    if not display_name or not display_name.strip():
        return ("", "")

    parts = display_name.strip().split()
    if len(parts) == 1:
        return ("", parts[0])

    # Last token is surname; everything else is given name(s)
    return (" ".join(parts[:-1]), parts[-1])


# ---------------------------------------------------------------------------
# Institution extraction
# ---------------------------------------------------------------------------

def extract_institution(
    authorship: dict[str, Any],
) -> tuple[str, str, str]:
    """Extract the best institution info from an OpenAlex authorship object.

    Prefers ``last_known_institutions`` (newer API field); falls back to
    ``institutions`` (legacy field). Takes the first institution listed.

    Args:
        authorship: A single entry from the ``authorships`` array.

    Returns:
        Tuple of (institution_name, country_code, institution_type).
    """
    # Try last_known_institutions first (added ~2024)
    institutions = authorship.get("last_known_institutions") or []
    if not institutions:
        # Fall back to legacy institutions field
        institutions = authorship.get("institutions") or []

    if not institutions:
        return ("", "", "")

    inst = institutions[0]  # primary affiliation
    return (
        inst.get("display_name") or "",
        inst.get("country_code") or "",
        inst.get("type") or "",
    )


# ---------------------------------------------------------------------------
# OpenAlex API interaction
# ---------------------------------------------------------------------------

class OpenAlexClient:
    """Thin wrapper around the OpenAlex Works API with rate limiting.

    Attributes:
        session: Reusable requests session with polite pool headers.
        min_interval: Minimum seconds between requests.
        last_request_time: Timestamp of the last request sent.
    """

    def __init__(self, rate_limit: int = DEFAULT_RATE_LIMIT) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                f"EEA-ElasmoAnalyses/1.0 "
                f"(mailto:{CONTACT_EMAIL})"
            ),
            "Accept": "application/json",
        })
        self.min_interval = 1.0 / rate_limit
        self.last_request_time = 0.0

    def _throttle(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.monotonic() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def fetch_works_by_dois(
        self, dois: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch multiple works in a single API call using DOI filter.

        OpenAlex supports pipe-separated DOI filters, e.g.:
            ``filter=doi:10.1234/a|10.1234/b``
        Limited to 50 values per request.

        Args:
            dois: List of DOI strings (without URL prefix).

        Returns:
            List of work objects from the API response.

        Raises:
            requests.HTTPError: On non-retryable HTTP errors.
        """
        if not dois:
            return []

        # OpenAlex expects bare DOIs in the filter (no https://doi.org/ prefix)
        clean_dois = [
            d.replace("https://doi.org/", "").replace("http://doi.org/", "")
            for d in dois
        ]
        doi_filter = "|".join(clean_dois)

        params = {
            "filter": f"doi:{doi_filter}",
            "per_page": len(clean_dois),
            "mailto": CONTACT_EMAIL,
            "select": (
                "doi,authorships,id,title"
            ),
        }

        for attempt in range(MAX_RETRIES):
            self._throttle()
            self.last_request_time = time.monotonic()

            try:
                resp = self.session.get(
                    f"{OPENALEX_API_BASE}/works",
                    params=params,
                    timeout=30,
                )
            except requests.RequestException as exc:
                logger.warning(
                    "Request failed (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, exc,
                )
                time.sleep(BACKOFF_BASE * (2 ** attempt))
                continue

            if resp.status_code == 429:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Rate limited (429). Backing off %.1fs (attempt %d/%d).",
                    wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Server error %d. Retrying in %.1fs (attempt %d/%d).",
                    resp.status_code, wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
                continue

            if resp.status_code == 400 and len(dois) > 1:
                # Likely a DOI with special characters breaking the filter.
                # Fall back to individual lookups for this batch.
                logger.warning(
                    "400 error on batch of %d DOIs — falling back to "
                    "individual lookups.",
                    len(dois),
                )
                all_results = []
                for single_doi in dois:
                    try:
                        single = self.fetch_works_by_dois([single_doi])
                        all_results.extend(single)
                    except Exception:
                        logger.debug(
                            "Skipping DOI that caused error: %s", single_doi
                        )
                return all_results

            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

        logger.error(
            "All %d retries exhausted for batch of %d DOIs.",
            MAX_RETRIES, len(dois),
        )
        return []


# ---------------------------------------------------------------------------
# Processing logic
# ---------------------------------------------------------------------------

def extract_authors_from_work(
    work: dict[str, Any],
    doi_to_litid: dict[str, int],
) -> list[AuthorRecord]:
    """Parse author records from a single OpenAlex work object.

    Args:
        work: A work object from the OpenAlex API.
        doi_to_litid: Mapping from normalised DOI to literature_id.

    Returns:
        List of AuthorRecord instances for each author of the paper.
    """
    raw_doi = (work.get("doi") or "").replace("https://doi.org/", "")
    doi_lower = raw_doi.lower().strip()
    literature_id = doi_to_litid.get(doi_lower, -1)

    if literature_id == -1:
        # Try without http prefix too
        for variant in [raw_doi.strip(), raw_doi.lower()]:
            if variant in doi_to_litid:
                literature_id = doi_to_litid[variant]
                break

    if literature_id == -1:
        logger.debug("Could not map DOI %s to literature_id.", raw_doi)
        return []

    records: list[AuthorRecord] = []
    authorships = work.get("authorships") or []

    for authorship in authorships:
        author_info = authorship.get("author") or {}
        display_name = author_info.get("display_name") or ""
        first_name, last_name = parse_author_name(display_name)

        # OpenAlex author ID (e.g. "https://openalex.org/A5023888391")
        openalex_id = author_info.get("id") or ""

        position = authorship.get("author_position") or "middle"
        inst_name, inst_country, inst_type = extract_institution(authorship)

        records.append(AuthorRecord(
            literature_id=literature_id,
            doi=raw_doi,
            author_position=position,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            openalex_author_id=openalex_id,
            institution_name=inst_name,
            institution_country=inst_country,
            institution_type=inst_type,
        ))

    return records


def build_unique_authors(
    paper_authors: list[dict[str, Any]],
) -> pd.DataFrame:
    """Deduplicate authors by OpenAlex ID and compute summary statistics.

    For each unique author, determines their most common institution
    and counts the number of papers they appear on.

    Args:
        paper_authors: List of author record dicts (from paper_authors CSV).

    Returns:
        DataFrame with one row per unique OpenAlex author ID.
    """
    df = pd.DataFrame(paper_authors)

    if df.empty:
        return pd.DataFrame(columns=[
            "display_name", "first_name", "last_name",
            "openalex_author_id", "most_common_institution",
            "institution_country", "paper_count",
        ])

    # Filter out records without an OpenAlex ID (cannot deduplicate)
    df_with_id = df[df["openalex_author_id"].str.len() > 0].copy()

    if df_with_id.empty:
        return pd.DataFrame(columns=[
            "display_name", "first_name", "last_name",
            "openalex_author_id", "most_common_institution",
            "institution_country", "paper_count",
        ])

    unique_rows: list[dict[str, Any]] = []
    grouped = df_with_id.groupby("openalex_author_id")

    for oa_id, group in grouped:
        # Use the most frequent display name for this author
        name_counts: Counter[str] = Counter(group["display_name"])
        best_name = name_counts.most_common(1)[0][0]
        first_name, last_name = parse_author_name(best_name)

        # Most common institution (excluding blanks)
        institutions = group["institution_name"][
            group["institution_name"].str.len() > 0
        ]
        if len(institutions) > 0:
            inst_counts: Counter[str] = Counter(institutions)
            best_inst = inst_counts.most_common(1)[0][0]
            # Get the country for that institution
            mask = group["institution_name"] == best_inst
            best_country = group.loc[mask, "institution_country"].iloc[0]
        else:
            best_inst = ""
            best_country = ""

        unique_rows.append({
            "display_name": best_name,
            "first_name": first_name,
            "last_name": last_name,
            "openalex_author_id": oa_id,
            "most_common_institution": best_inst,
            "institution_country": best_country,
            "paper_count": len(group["literature_id"].unique()),
        })

    result = pd.DataFrame(unique_rows)
    result.sort_values("paper_count", ascending=False, inplace=True)
    return result


# ---------------------------------------------------------------------------
# Progress / resume
# ---------------------------------------------------------------------------

def load_progress() -> dict[str, Any]:
    """Load saved progress from disk.

    Returns:
        Dict with 'completed_dois' (set of DOIs already processed)
        and 'records' (list of author record dicts).
    """
    if not PROGRESS_FILE.exists():
        return {"completed_dois": set(), "records": []}

    with open(PROGRESS_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return {
        "completed_dois": set(data.get("completed_dois", [])),
        "records": data.get("records", []),
    }


def save_progress(
    completed_dois: set[str],
    records: list[dict[str, Any]],
) -> None:
    """Persist current progress to disk.

    Args:
        completed_dois: Set of DOIs already processed.
        records: List of author record dicts accumulated so far.
    """
    data = {
        "completed_dois": list(completed_dois),
        "records": records,
    }
    # Write to temp file then rename for atomicity
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    tmp.rename(PROGRESS_FILE)
    logger.info(
        "Progress saved: %d DOIs processed, %d author records.",
        len(completed_dois), len(records),
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_papers() -> pd.DataFrame:
    """Load the literature review parquet and return papers with DOIs.

    Returns:
        DataFrame with columns literature_id, doi (both cleaned).
    """
    logger.info("Loading papers from %s", INPUT_PARQUET)
    df = pd.read_parquet(
        INPUT_PARQUET,
        columns=["literature_id", "doi"],
    )

    # literature_id may be float due to NaN — convert to int where possible
    df = df.dropna(subset=["doi"])
    df = df[df["doi"].str.strip().str.len() > 0].copy()
    df = df.dropna(subset=["literature_id"])
    df["literature_id"] = df["literature_id"].astype(int)
    df["doi_clean"] = (
        df["doi"]
        .str.strip()
        .str.replace("https://doi.org/", "", regex=False)
        .str.replace("http://doi.org/", "", regex=False)
    )
    df["doi_lower"] = df["doi_clean"].str.lower()

    logger.info(
        "Loaded %d papers with DOIs (of %d total rows).",
        len(df), len(df),
    )
    return df


def run_pipeline(
    dry_run: int | None = None,
    resume: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
    rate_limit: int = DEFAULT_RATE_LIMIT,
) -> None:
    """Execute the full enrichment pipeline.

    Args:
        dry_run: If set, process only this many papers.
        resume: Whether to resume from saved progress.
        batch_size: Number of DOIs per API request (max 50).
        rate_limit: Maximum requests per second.
    """
    df = load_papers()

    # Build DOI -> literature_id mapping
    doi_to_litid: dict[str, int] = dict(
        zip(df["doi_lower"], df["literature_id"])
    )

    # Resume handling
    if resume:
        progress = load_progress()
        completed_dois = progress["completed_dois"]
        all_records = progress["records"]
        logger.info(
            "Resuming: %d DOIs already done, %d records in memory.",
            len(completed_dois), len(all_records),
        )
    else:
        completed_dois: set[str] = set()
        all_records: list[dict[str, Any]] = []

    # Filter to unprocessed DOIs
    remaining_dois = [
        d for d in df["doi_clean"].tolist()
        if d.lower() not in completed_dois
    ]

    if dry_run is not None:
        remaining_dois = remaining_dois[:dry_run]
        logger.info("Dry-run mode: processing %d papers.", len(remaining_dois))

    if not remaining_dois:
        logger.info("No papers to process. All DOIs already completed.")
    else:
        logger.info(
            "Processing %d papers in batches of %d (rate limit: %d req/s).",
            len(remaining_dois), batch_size, rate_limit,
        )

    client = OpenAlexClient(rate_limit=rate_limit)

    # Process in batches
    papers_since_save = 0
    total_batches = (len(remaining_dois) + batch_size - 1) // batch_size

    with tqdm(total=len(remaining_dois), desc="Papers", unit="paper") as pbar:
        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(remaining_dois))
            batch_dois = remaining_dois[start:end]

            works = client.fetch_works_by_dois(batch_dois)

            # Extract authors from each returned work
            batch_record_count = 0
            returned_dois: set[str] = set()

            for work in works:
                records = extract_authors_from_work(work, doi_to_litid)
                for rec in records:
                    all_records.append({
                        "literature_id": rec.literature_id,
                        "doi": rec.doi,
                        "author_position": rec.author_position,
                        "display_name": rec.display_name,
                        "first_name": rec.first_name,
                        "last_name": rec.last_name,
                        "openalex_author_id": rec.openalex_author_id,
                        "institution_name": rec.institution_name,
                        "institution_country": rec.institution_country,
                        "institution_type": rec.institution_type,
                    })
                    batch_record_count += 1

                raw_doi = (work.get("doi") or "").replace(
                    "https://doi.org/", ""
                )
                returned_dois.add(raw_doi.lower())

            # Mark all DOIs in this batch as completed (even those not
            # found — no point retrying, they likely have no OpenAlex record)
            for d in batch_dois:
                completed_dois.add(d.lower())

            papers_since_save += len(batch_dois)
            pbar.update(len(batch_dois))

            # Log DOIs not found in OpenAlex
            not_found = set(d.lower() for d in batch_dois) - returned_dois
            if not_found:
                logger.debug(
                    "Batch %d: %d DOIs not found in OpenAlex.",
                    batch_idx + 1, len(not_found),
                )

            # Periodic progress save
            if papers_since_save >= SAVE_EVERY:
                save_progress(completed_dois, all_records)
                papers_since_save = 0

    # Final save
    save_progress(completed_dois, all_records)

    # Write output CSVs
    logger.info("Writing %d author-paper records.", len(all_records))
    df_paper_authors = pd.DataFrame(all_records)

    if not df_paper_authors.empty:
        # Sort by literature_id then author_position for readability
        position_order = {"first": 0, "middle": 1, "last": 2}
        df_paper_authors["_pos_sort"] = (
            df_paper_authors["author_position"].map(position_order).fillna(1)
        )
        df_paper_authors.sort_values(
            ["literature_id", "_pos_sort"],
            inplace=True,
        )
        df_paper_authors.drop(columns=["_pos_sort"], inplace=True)

    df_paper_authors.to_csv(OUTPUT_PAPER_AUTHORS, index=False)
    logger.info("Wrote %s", OUTPUT_PAPER_AUTHORS)

    # Build and write unique authors
    df_unique = build_unique_authors(all_records)
    df_unique.to_csv(OUTPUT_UNIQUE_AUTHORS, index=False)
    logger.info(
        "Wrote %d unique authors to %s",
        len(df_unique), OUTPUT_UNIQUE_AUTHORS,
    )

    # Summary statistics
    if not df_paper_authors.empty:
        n_papers = df_paper_authors["literature_id"].nunique()
        n_authors = df_paper_authors["openalex_author_id"].nunique()
        n_with_inst = (
            df_paper_authors["institution_name"].str.len() > 0
        ).sum()
        logger.info(
            "Summary: %d papers, %d unique authors, "
            "%d/%d records with institution data (%.1f%%).",
            n_papers, n_authors,
            n_with_inst, len(df_paper_authors),
            100.0 * n_with_inst / len(df_paper_authors)
            if len(df_paper_authors) > 0 else 0,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Enrich the elasmobranch literature database with author "
            "metadata from OpenAlex."
        ),
    )
    parser.add_argument(
        "--dry-run",
        type=int,
        default=None,
        metavar="N",
        help="Process only N papers (for testing).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved progress file.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Number of workers (default 1). Sequential is recommended "
            "for API politeness; values > 1 are accepted but ignored."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            f"DOIs per API request (default {DEFAULT_BATCH_SIZE}, "
            f"max 50 per OpenAlex)."
        ),
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=DEFAULT_RATE_LIMIT,
        help=(
            f"Max requests per second (default {DEFAULT_RATE_LIMIT}). "
            f"OpenAlex polite pool allows ~10 req/s."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for the OpenAlex author enrichment script."""
    args = parse_args()

    if args.batch_size < 1 or args.batch_size > 50:
        logger.error("Batch size must be between 1 and 50.")
        sys.exit(1)

    if args.rate_limit < 1:
        logger.error("Rate limit must be at least 1 request per second.")
        sys.exit(1)

    if args.workers > 1:
        logger.warning(
            "Multi-worker mode requested (%d) but ignored for API "
            "politeness. Running sequentially.",
            args.workers,
        )

    run_pipeline(
        dry_run=args.dry_run,
        resume=args.resume,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
    )


if __name__ == "__main__":
    main()
