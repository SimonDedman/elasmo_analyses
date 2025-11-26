#!/usr/bin/env python3
"""
Lookup Open Access status for papers using the Unpaywall API.

Unpaywall API documentation: https://unpaywall.org/products/api
Rate limit: 100,000 requests per day, polite limit ~10 requests/second

OA Status values returned:
- gold: Published in a fully OA journal (DOAJ-indexed)
- green: Toll-access on publisher site, but free copy in repository
- hybrid: Free under open license in toll-access journal
- bronze: Free to read on publisher site, no open license
- closed: No free copy found
"""

import requests
import pandas as pd
import sqlite3
import time
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
EMAIL = "simon.dedman@ucd.ie"  # Required by Unpaywall API
API_BASE = "https://api.unpaywall.org/v2"
RATE_LIMIT_DELAY = 0.15  # 150ms between requests (~6.6 req/sec, well under limit)
BATCH_SIZE = 100  # Save progress every N requests
MAX_RETRIES = 3

# Paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "database" / "technique_taxonomy.db"
CSV_PATH = PROJECT_DIR / "outputs" / "shark_references_bulk" / "shark_references_complete_2025_to_1950_20251021.csv"
OUTPUT_DIR = PROJECT_DIR / "outputs"
LOG_DIR = PROJECT_DIR / "logs"

# Create directories if needed
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


def setup_database():
    """Add open_access columns to paper_geography table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check existing columns
    cur.execute("PRAGMA table_info(paper_geography)")
    existing_cols = {row[1] for row in cur.fetchall()}

    new_columns = [
        ("oa_status", "TEXT"),  # gold, green, hybrid, bronze, closed, unknown
        ("oa_url", "TEXT"),  # Best OA URL
        ("oa_is_oa", "BOOLEAN"),  # Is it open access?
        ("oa_journal_is_oa", "BOOLEAN"),  # Is the journal fully OA?
        ("oa_journal_is_in_doaj", "BOOLEAN"),  # Is journal in DOAJ?
        ("oa_host_type", "TEXT"),  # publisher, repository
        ("oa_license", "TEXT"),  # cc-by, cc-by-nc, etc.
        ("oa_version", "TEXT"),  # publishedVersion, acceptedVersion, submittedVersion
        ("oa_checked_date", "DATE"),  # When we checked
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            print(f"Adding column: {col_name}")
            cur.execute(f"ALTER TABLE paper_geography ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print("Database schema updated.")


def load_papers_with_dois():
    """Load papers that have DOIs from the CSV."""
    df = pd.read_csv(CSV_PATH)

    # Filter to papers with DOIs
    df_with_doi = df[df['doi'].notna() & (df['doi'] != '')].copy()

    # Clean DOIs
    df_with_doi['doi_clean'] = df_with_doi['doi'].str.strip()

    print(f"Total papers: {len(df)}")
    print(f"Papers with DOI: {len(df_with_doi)}")

    return df_with_doi


def get_already_checked():
    """Get DOIs that have already been checked."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT paper_id FROM paper_geography
            WHERE oa_checked_date IS NOT NULL
        """)
        checked = {row[0] for row in cur.fetchall()}
    except sqlite3.OperationalError:
        checked = set()

    conn.close()
    return checked


def lookup_unpaywall(doi):
    """Query Unpaywall API for a single DOI."""
    url = f"{API_BASE}/{doi}?email={EMAIL}"

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # DOI not found in Unpaywall
                return {"error": "not_found", "doi": doi}
            elif response.status_code == 429:
                # Rate limited - wait and retry
                print(f"Rate limited, waiting 60s...")
                time.sleep(60)
                continue
            else:
                print(f"Error {response.status_code} for DOI {doi}")
                return {"error": f"http_{response.status_code}", "doi": doi}

        except requests.exceptions.Timeout:
            print(f"Timeout for DOI {doi}, attempt {attempt + 1}")
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Request error for DOI {doi}: {e}")
            time.sleep(5)

    return {"error": "max_retries", "doi": doi}


def extract_oa_info(data):
    """Extract relevant OA information from Unpaywall response."""
    if "error" in data:
        return {
            "oa_status": "unknown",
            "oa_url": None,
            "oa_is_oa": False,
            "oa_journal_is_oa": None,
            "oa_journal_is_in_doaj": None,
            "oa_host_type": None,
            "oa_license": None,
            "oa_version": None,
        }

    # Get best OA location
    best_oa = data.get("best_oa_location", {}) or {}

    return {
        "oa_status": data.get("oa_status", "unknown"),
        "oa_url": best_oa.get("url") or best_oa.get("url_for_pdf"),
        "oa_is_oa": data.get("is_oa", False),
        "oa_journal_is_oa": data.get("journal_is_oa"),
        "oa_journal_is_in_doaj": data.get("journal_is_in_doaj"),
        "oa_host_type": best_oa.get("host_type"),
        "oa_license": best_oa.get("license"),
        "oa_version": best_oa.get("version"),
    }


def save_results_to_db(results):
    """Save OA results to database."""
    if not results:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    for paper_id, oa_info in results.items():
        cur.execute("""
            UPDATE paper_geography SET
                oa_status = ?,
                oa_url = ?,
                oa_is_oa = ?,
                oa_journal_is_oa = ?,
                oa_journal_is_in_doaj = ?,
                oa_host_type = ?,
                oa_license = ?,
                oa_version = ?,
                oa_checked_date = ?
            WHERE paper_id = ?
        """, (
            oa_info["oa_status"],
            oa_info["oa_url"],
            oa_info["oa_is_oa"],
            oa_info["oa_journal_is_oa"],
            oa_info["oa_journal_is_in_doaj"],
            oa_info["oa_host_type"],
            oa_info["oa_license"],
            oa_info["oa_version"],
            today,
            paper_id
        ))

    conn.commit()
    conn.close()


def save_results_to_csv(all_results, filename="unpaywall_oa_results.csv"):
    """Save all results to CSV for backup."""
    if not all_results:
        return

    rows = []
    for paper_id, oa_info in all_results.items():
        row = {"paper_id": paper_id, **oa_info}
        rows.append(row)

    df = pd.DataFrame(rows)
    output_path = OUTPUT_DIR / filename
    df.to_csv(output_path, index=False)
    print(f"Saved results to {output_path}")


def create_doi_to_paperid_mapping():
    """Create mapping from DOI to paper_id (filename)."""
    # Load shark-references CSV
    df = pd.read_csv(CSV_PATH)
    df_with_doi = df[df['doi'].notna()].copy()

    # Load paper_geography to get paper_ids
    conn = sqlite3.connect(DB_PATH)
    paper_ids = pd.read_sql("SELECT paper_id FROM paper_geography", conn)
    conn.close()

    # Create mapping based on matching authors/year/title
    # The paper_id format is: "Author.etal.Year.Title_truncated.pdf"

    # For now, we'll create a separate table to store DOI lookups
    # and then join them to paper_geography

    return df_with_doi


def main(max_papers=None, test_mode=False):
    """Main function to run Unpaywall lookups."""
    print("=" * 60)
    print("UNPAYWALL OPEN ACCESS LOOKUP")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    print(f"Email: {EMAIL}")

    # Setup database
    setup_database()

    # Load papers with DOIs
    df = load_papers_with_dois()

    if max_papers:
        df = df.head(max_papers)
        print(f"Limited to {max_papers} papers for testing")

    # Get papers already in paper_geography
    conn = sqlite3.connect(DB_PATH)
    existing_papers = pd.read_sql("SELECT paper_id FROM paper_geography", conn)
    conn.close()
    existing_set = set(existing_papers['paper_id'])

    # Get already checked
    checked = get_already_checked()
    print(f"Already checked: {len(checked)} papers")

    # We need to match DOIs to paper_ids
    # The shark-references CSV doesn't have paper_id (filename)
    # Let's store results in a separate CSV first, then merge

    results_file = OUTPUT_DIR / "unpaywall_oa_by_doi.csv"

    # Load existing results if any
    if results_file.exists():
        existing_results = pd.read_csv(results_file)
        checked_dois = set(existing_results['doi'].dropna())
        print(f"Already have results for {len(checked_dois)} DOIs")
    else:
        existing_results = pd.DataFrame()
        checked_dois = set()

    # Filter to unchecked DOIs
    df_to_check = df[~df['doi_clean'].isin(checked_dois)]
    print(f"DOIs to check: {len(df_to_check)}")

    if len(df_to_check) == 0:
        print("All DOIs already checked!")
        return

    # Process in batches
    all_results = []
    start_time = time.time()

    for i, (idx, row) in enumerate(df_to_check.iterrows()):
        doi = row['doi_clean']

        if test_mode and i >= 10:
            print("Test mode: stopping after 10 DOIs")
            break

        # Progress
        if i > 0 and i % 100 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (len(df_to_check) - i) / rate / 60
            print(f"Progress: {i}/{len(df_to_check)} ({i/len(df_to_check)*100:.1f}%) - "
                  f"{rate:.1f} req/s - ~{remaining:.0f} min remaining")

        # Lookup
        data = lookup_unpaywall(doi)
        oa_info = extract_oa_info(data)
        oa_info['doi'] = doi
        oa_info['literature_id'] = row['literature_id']
        oa_info['year'] = row['year']
        oa_info['title'] = row['title'][:100] if pd.notna(row['title']) else None

        all_results.append(oa_info)

        # Save periodically
        if len(all_results) % BATCH_SIZE == 0:
            batch_df = pd.DataFrame(all_results)
            if existing_results.empty:
                combined = batch_df
            else:
                combined = pd.concat([existing_results, batch_df], ignore_index=True)
            combined.to_csv(results_file, index=False)
            print(f"Saved checkpoint: {len(combined)} total results")

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    # Final save
    if all_results:
        final_df = pd.DataFrame(all_results)
        if existing_results.empty:
            combined = final_df
        else:
            combined = pd.concat([existing_results, final_df], ignore_index=True)
        combined.to_csv(results_file, index=False)
        print(f"\nFinal save: {len(combined)} total results")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if results_file.exists():
        results_df = pd.read_csv(results_file)
        print(f"Total DOIs checked: {len(results_df)}")
        print("\nOA Status distribution:")
        print(results_df['oa_status'].value_counts())
        print(f"\nOpen Access: {results_df['oa_is_oa'].sum()} ({results_df['oa_is_oa'].mean()*100:.1f}%)")

    print(f"\nCompleted: {datetime.now()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lookup OA status via Unpaywall")
    parser.add_argument("--max", type=int, help="Maximum papers to process")
    parser.add_argument("--test", action="store_true", help="Test mode (10 DOIs only)")
    args = parser.parse_args()

    main(max_papers=args.max, test_mode=args.test)
