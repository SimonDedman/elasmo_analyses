#!/usr/bin/env python3
"""Enrich author records with last_known_institutions and coordinates.

For each of the 28,953 unique authors in openalex_unique_authors.csv, queries
the OpenAlex API to retrieve their most recent institution affiliation plus the
institution's geographic coordinates (lat/lon/city/region).

Outputs two CSV files:

    1. openalex_authors_last_institution.csv  -- one row per author
    2. openalex_institutions.csv             -- deduplicated institution records

Uses the OpenAlex polite pool (mailto param) for higher rate limits.
Institution geo data is fetched individually then cached to avoid repeat calls.

Usage:
    python scripts/enrich_author_last_institutions.py
    python scripts/enrich_author_last_institutions.py --limit 20
    python scripts/enrich_author_last_institutions.py --resume
    python scripts/enrich_author_last_institutions.py --batch-size 25 --rate-limit 5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
INPUT_AUTHORS = PROJECT_BASE / "outputs/openalex_unique_authors.csv"
OUTPUT_AUTHORS = PROJECT_BASE / "outputs/openalex_authors_last_institution.csv"
OUTPUT_INSTITUTIONS = PROJECT_BASE / "outputs/openalex_institutions.csv"
PROGRESS_FILE = PROJECT_BASE / "outputs/.enrich_last_inst_progress.json"

CONTACT_EMAIL = "simondedman@gmail.com"
OPENALEX_API_BASE = "https://api.openalex.org"

DEFAULT_RATE_LIMIT = 10   # requests per second (polite pool allows ~10)
DEFAULT_BATCH_SIZE = 50   # max authors per batch request (OpenAlex limit)
BACKOFF_BASE = 2.0        # seconds for first backoff; doubles each retry
MAX_RETRIES = 5
PROGRESS_EVERY = 500      # save/report every N authors processed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenAlex client
# ---------------------------------------------------------------------------

class OpenAlexClient:
    """Thin wrapper around the OpenAlex API with rate limiting and retries.

    Attributes:
        session: Reusable requests session with polite pool headers.
        min_interval: Minimum seconds between requests.
        last_request_time: Timestamp of the most recent request.
    """

    def __init__(self, rate_limit: int = DEFAULT_RATE_LIMIT) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                f"EEA-ElasmoAnalyses/1.0 (mailto:{CONTACT_EMAIL})"
            ),
            "Accept": "application/json",
        })
        self.min_interval = 1.0 / rate_limit
        self.last_request_time = 0.0

    def _throttle(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.monotonic() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _get(
        self,
        url: str,
        params: dict[str, Any],
        context: str = "",
    ) -> dict[str, Any] | None:
        """Issue a GET request with retry/backoff logic.

        Args:
            url: Full URL to request.
            params: Query parameters.
            context: Short description used in log messages.

        Returns:
            Parsed JSON dict, or None after all retries are exhausted.
        """
        for attempt in range(MAX_RETRIES):
            self._throttle()
            self.last_request_time = time.monotonic()

            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as exc:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Request error%s (attempt %d/%d): %s — retrying in %.1fs",
                    f" [{context}]" if context else "",
                    attempt + 1, MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
                continue

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Rate limited (429)%s — backing off %.1fs (attempt %d/%d).",
                    f" [{context}]" if context else "",
                    wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "Server error %d%s — retrying in %.1fs (attempt %d/%d).",
                    resp.status_code,
                    f" [{context}]" if context else "",
                    wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
                continue

            # 404 or other non-retryable client error
            logger.debug(
                "Non-retryable HTTP %d%s — skipping.",
                resp.status_code,
                f" [{context}]" if context else "",
            )
            return None

        logger.error(
            "All %d retries exhausted%s.",
            MAX_RETRIES,
            f" [{context}]" if context else "",
        )
        return None

    def fetch_authors_batch(
        self, openalex_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch last_known_institutions for a batch of author IDs.

        Uses the pipe-separated filter syntax:
            ``/authors?filter=openalex:A123|A456``

        Args:
            openalex_ids: List of full OpenAlex author IDs
                (e.g. ``https://openalex.org/A5003477041``).

        Returns:
            List of author result objects from the API response.
        """
        if not openalex_ids:
            return []

        # Strip URL prefix — filter accepts short IDs (A5003477041)
        short_ids = [
            oid.replace("https://openalex.org/", "")
            for oid in openalex_ids
        ]
        id_filter = "|".join(short_ids)

        params = {
            "filter": f"openalex:{id_filter}",
            "select": "id,last_known_institutions",
            "per_page": len(short_ids),
            "mailto": CONTACT_EMAIL,
        }

        data = self._get(
            f"{OPENALEX_API_BASE}/authors",
            params,
            context=f"authors batch of {len(short_ids)}",
        )
        if data is None:
            return []

        return data.get("results", [])

    def fetch_institution(
        self, institution_id: str
    ) -> dict[str, Any] | None:
        """Fetch geo and metadata for a single institution.

        Args:
            institution_id: Full OpenAlex institution ID
                (e.g. ``https://openalex.org/I12345``).

        Returns:
            Institution object dict, or None on failure.
        """
        short_id = institution_id.replace("https://openalex.org/", "")
        params = {
            "select": "id,display_name,type,geo,country_code",
            "mailto": CONTACT_EMAIL,
        }
        return self._get(
            f"{OPENALEX_API_BASE}/institutions/{short_id}",
            params,
            context=short_id,
        )


# ---------------------------------------------------------------------------
# Progress / resume helpers
# ---------------------------------------------------------------------------

def load_progress() -> dict[str, Any]:
    """Load saved progress from disk.

    Returns:
        Dict with:
            - ``completed_ids``: set of already-processed author IDs
            - ``author_rows``: list of enriched author row dicts
            - ``institutions``: dict mapping institution_id -> institution dict
    """
    if not PROGRESS_FILE.exists():
        return {
            "completed_ids": set(),
            "author_rows": [],
            "institutions": {},
        }

    with open(PROGRESS_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return {
        "completed_ids": set(data.get("completed_ids", [])),
        "author_rows": data.get("author_rows", []),
        "institutions": data.get("institutions", {}),
    }


def save_progress(
    completed_ids: set[str],
    author_rows: list[dict[str, Any]],
    institutions: dict[str, dict[str, Any]],
) -> None:
    """Persist current progress atomically.

    Args:
        completed_ids: Author IDs already processed.
        author_rows: Enriched author records accumulated so far.
        institutions: Institution cache (id -> dict).
    """
    data = {
        "completed_ids": list(completed_ids),
        "author_rows": author_rows,
        "institutions": institutions,
    }
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    tmp.rename(PROGRESS_FILE)
    logger.info(
        "Progress saved: %d authors done, %d institution records cached.",
        len(completed_ids), len(institutions),
    )


# ---------------------------------------------------------------------------
# Institution geo-enrichment
# ---------------------------------------------------------------------------

def enrich_institution(
    inst_obj: dict[str, Any],
    inst_cache: dict[str, dict[str, Any]],
    client: OpenAlexClient,
) -> dict[str, Any]:
    """Return a fully geo-enriched institution dict, fetching if needed.

    If the institution ID is already in ``inst_cache``, returns the cached
    record immediately. Otherwise calls the institutions endpoint and caches
    the result.

    Args:
        inst_obj: Partial institution dict from author's last_known_institutions
            (has id, display_name, country_code, type).
        inst_cache: In-memory institution cache (mutated in place when new
            records are fetched).
        client: OpenAlex API client.

    Returns:
        Dict with keys: institution_id, display_name, country_code, city,
        region, latitude, longitude, type.
    """
    inst_id = inst_obj.get("id") or ""
    if not inst_id:
        return _empty_institution()

    if inst_id in inst_cache:
        return inst_cache[inst_id]

    # Fetch full institution record for geo data
    full = client.fetch_institution(inst_id)

    if full is None:
        # Fall back to partial data from the author record
        record = {
            "institution_id": inst_id,
            "display_name": inst_obj.get("display_name") or "",
            "country_code": inst_obj.get("country_code") or "",
            "type": inst_obj.get("type") or "",
            "city": "",
            "region": "",
            "latitude": None,
            "longitude": None,
        }
    else:
        geo = full.get("geo") or {}
        record = {
            "institution_id": inst_id,
            "display_name": full.get("display_name") or inst_obj.get("display_name") or "",
            "country_code": full.get("country_code") or inst_obj.get("country_code") or "",
            "type": full.get("type") or inst_obj.get("type") or "",
            "city": geo.get("city") or "",
            "region": geo.get("region") or "",
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
        }

    inst_cache[inst_id] = record
    return record


def _empty_institution() -> dict[str, Any]:
    """Return a blank institution record for authors with no affiliation."""
    return {
        "institution_id": "",
        "display_name": "",
        "country_code": "",
        "type": "",
        "city": "",
        "region": "",
        "latitude": None,
        "longitude": None,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    limit: int | None,
    resume: bool,
    batch_size: int,
    rate_limit: int,
) -> None:
    """Execute the full last-institution enrichment pipeline.

    Args:
        limit: If set, process only this many authors (for testing).
        resume: Whether to load and continue from saved progress.
        batch_size: Number of authors per OpenAlex batch request (max 50).
        rate_limit: Maximum requests per second to OpenAlex.
    """
    # ------------------------------------------------------------------
    # Load authors
    # ------------------------------------------------------------------
    logger.info("Loading authors from %s", INPUT_AUTHORS)
    df = pd.read_csv(INPUT_AUTHORS)
    logger.info("Loaded %d authors.", len(df))

    all_ids: list[str] = df["openalex_author_id"].dropna().tolist()
    all_ids = [aid for aid in all_ids if aid.startswith("https://openalex.org/")]
    logger.info("%d authors with valid OpenAlex IDs.", len(all_ids))

    # ------------------------------------------------------------------
    # Resume / init
    # ------------------------------------------------------------------
    if resume:
        progress = load_progress()
        completed_ids: set[str] = progress["completed_ids"]
        author_rows: list[dict[str, Any]] = progress["author_rows"]
        inst_cache: dict[str, dict[str, Any]] = progress["institutions"]
        logger.info(
            "Resuming: %d authors already done, %d institution records cached.",
            len(completed_ids), len(inst_cache),
        )
    else:
        completed_ids = set()
        author_rows = []
        inst_cache = {}

    # ------------------------------------------------------------------
    # Filter to remaining authors
    # ------------------------------------------------------------------
    remaining = [aid for aid in all_ids if aid not in completed_ids]

    if limit is not None:
        remaining = remaining[:limit]
        logger.info("--limit %d: processing %d authors.", limit, len(remaining))
    else:
        logger.info(
            "Processing %d authors in batches of %d (rate limit: %d req/s).",
            len(remaining), batch_size, rate_limit,
        )

    client = OpenAlexClient(rate_limit=rate_limit)

    # ------------------------------------------------------------------
    # Batch author fetching
    # ------------------------------------------------------------------
    total_batches = (len(remaining) + batch_size - 1) // batch_size
    processed_since_save = 0
    n_with_inst = 0
    n_without_inst = 0

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(remaining))
        batch_ids = remaining[start:end]

        results = client.fetch_authors_batch(batch_ids)

        # Build id -> result mapping for this batch
        returned_map: dict[str, dict[str, Any]] = {
            r["id"]: r for r in results if r.get("id")
        }

        for author_id in batch_ids:
            result = returned_map.get(author_id)

            if result is None:
                # Author not found in OpenAlex (deleted/merged record)
                logger.debug("Author not found: %s", author_id)
                author_rows.append({
                    "openalex_author_id": author_id,
                    "last_institution_id": "",
                    "last_institution_name": "",
                    "last_institution_country": "",
                    "last_institution_city": "",
                    "last_institution_region": "",
                    "last_institution_lat": None,
                    "last_institution_lon": None,
                    "last_institution_type": "",
                })
                n_without_inst += 1
                completed_ids.add(author_id)
                continue

            lki: list[dict[str, Any]] = result.get("last_known_institutions") or []

            if not lki:
                inst_data = _empty_institution()
                n_without_inst += 1
            else:
                # Take first entry (most current affiliation per OpenAlex convention)
                inst_data = enrich_institution(lki[0], inst_cache, client)
                n_with_inst += 1

            author_rows.append({
                "openalex_author_id": author_id,
                "last_institution_id": inst_data["institution_id"],
                "last_institution_name": inst_data["display_name"],
                "last_institution_country": inst_data["country_code"],
                "last_institution_city": inst_data["city"],
                "last_institution_region": inst_data["region"],
                "last_institution_lat": inst_data["latitude"],
                "last_institution_lon": inst_data["longitude"],
                "last_institution_type": inst_data["type"],
            })
            completed_ids.add(author_id)

        processed_since_save += len(batch_ids)
        total_done = len(completed_ids)

        if total_done % PROGRESS_EVERY < batch_size or batch_idx == total_batches - 1:
            logger.info(
                "Progress: %d / %d authors processed "
                "(%d with institution, %d without).",
                total_done, len(all_ids), n_with_inst, n_without_inst,
            )

        if processed_since_save >= PROGRESS_EVERY:
            save_progress(completed_ids, author_rows, inst_cache)
            processed_since_save = 0

    # Final save
    save_progress(completed_ids, author_rows, inst_cache)

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    logger.info("Writing author output to %s", OUTPUT_AUTHORS)
    df_out = pd.DataFrame(author_rows)
    df_out.to_csv(OUTPUT_AUTHORS, index=False)
    logger.info(
        "Wrote %d author rows (%d with institution data, %.1f%%).",
        len(df_out),
        n_with_inst,
        100.0 * n_with_inst / len(df_out) if len(df_out) > 0 else 0.0,
    )

    if inst_cache:
        logger.info("Writing institution output to %s", OUTPUT_INSTITUTIONS)
        df_inst = pd.DataFrame(list(inst_cache.values()))
        # Consistent column order
        col_order = [
            "institution_id", "display_name", "country_code",
            "type", "city", "region", "latitude", "longitude",
        ]
        df_inst = df_inst[[c for c in col_order if c in df_inst.columns]]
        df_inst.sort_values("institution_id", inplace=True)
        df_inst.to_csv(OUTPUT_INSTITUTIONS, index=False)
        logger.info("Wrote %d institution records.", len(df_inst))
    else:
        logger.info("No institution records to write.")

    logger.info("Done.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Enrich elasmobranch authors with last_known_institutions "
            "and geographic coordinates from OpenAlex."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only N authors (for testing).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved progress file.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        metavar="N",
        help=f"Authors per API request (default {DEFAULT_BATCH_SIZE}, max 50).",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=DEFAULT_RATE_LIMIT,
        metavar="N",
        help=(
            f"Max requests per second (default {DEFAULT_RATE_LIMIT}). "
            "OpenAlex polite pool allows ~10 req/s."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()

    if args.batch_size < 1 or args.batch_size > 50:
        logger.error("--batch-size must be between 1 and 50.")
        sys.exit(1)

    if args.rate_limit < 1:
        logger.error("--rate-limit must be at least 1.")
        sys.exit(1)

    run_pipeline(
        limit=args.limit,
        resume=args.resume,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
    )


if __name__ == "__main__":
    main()
