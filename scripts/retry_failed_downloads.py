#!/usr/bin/env python3
"""
retry_failed_downloads.py

Retry failed PDF downloads with adjusted settings.

Features:
- Retry timeouts with increased timeout (60s)
- Retry errors (HTML instead of PDF - might be publisher redirects)
- Support session cookies for institutional access
- Update database with new results

Usage:
    # Retry only timeouts
    python3 retry_failed_downloads.py --status timeout

    # Retry timeouts and errors
    python3 retry_failed_downloads.py --status timeout error

    # Use session cookies for authentication
    python3 retry_failed_downloads.py --status forbidden --cookies cookies.txt

Author: Simon Dedman
Date: 2025-10-21
Version: 1.0
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
import argparse
import logging
from tqdm import tqdm
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from download_pdfs_from_database import (
    download_pdf,
    get_pdf_filename,
    setup_logging,
    OUTPUT_DIR,
    LOG_FILE
)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
RETRY_LOG = BASE_DIR / "logs/pdf_retry_log.csv"
FAILURE_REPORT = BASE_DIR / "docs/database/pdf_download_failures.csv"

# Updated settings for retry
TIMEOUT = 60  # Increased from 30s
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1.5  # Slightly slower to avoid rate limiting

# ============================================================================
# MAIN RETRY LOGIC
# ============================================================================

def load_session_cookies(cookie_file):
    """
    Load session cookies from Netscape format cookie file.

    Can be exported from browser using extensions like:
    - Chrome: "Get cookies.txt" extension
    - Firefox: "cookies.txt" extension

    Args:
        cookie_file: Path to cookies.txt file

    Returns:
        requests.Session with cookies loaded
    """
    session = requests.Session()

    if not cookie_file or not Path(cookie_file).exists():
        return session

    with open(cookie_file, 'r') as f:
        for line in f:
            # Skip comments and empty lines
            if line.startswith('#') or not line.strip():
                continue

            try:
                # Netscape format: domain flag path secure expiration name value
                parts = line.strip().split('\t')
                if len(parts) == 7:
                    domain, _, path, secure, expiration, name, value = parts
                    session.cookies.set(name, value, domain=domain, path=path)
            except Exception as e:
                logging.warning(f"Error parsing cookie line: {e}")
                continue

    logging.info(f"Loaded {len(session.cookies)} cookies from {cookie_file}")
    return session

def retry_failed_downloads(statuses_to_retry, cookie_file=None, max_papers=None, domain_filter=None):
    """
    Retry failed downloads with updated settings.

    Args:
        statuses_to_retry: List of status codes to retry (e.g., ['timeout', 'error'])
        cookie_file: Optional path to browser cookies for authentication
        max_papers: Optional limit on number to retry (for testing)
        domain_filter: Optional domain to filter (e.g., 'sciencedirect.com')
    """
    logger = setup_logging()

    print("="*80)
    print("PDF DOWNLOAD RETRY")
    print("="*80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load previous download log
    if not LOG_FILE.exists():
        logger.error(f"Download log not found: {LOG_FILE}")
        return

    log_df = pd.read_csv(LOG_FILE)
    logger.info(f"Loaded download log: {len(log_df)} entries")

    # Filter to papers with specified statuses
    retry_df = log_df[log_df['status'].isin(statuses_to_retry)].copy()
    logger.info(f"Papers to retry: {len(retry_df)} ({', '.join(statuses_to_retry)})")

    # Filter by domain if specified
    if domain_filter:
        from urllib.parse import urlparse
        retry_df['domain'] = retry_df['url'].apply(lambda x: urlparse(x).netloc if pd.notna(x) else '')
        retry_df = retry_df[retry_df['domain'].str.contains(domain_filter, case=False, na=False)]
        logger.info(f"Filtered to domain '{domain_filter}': {len(retry_df)} papers")

    if len(retry_df) == 0:
        logger.info("No papers to retry!")
        return

    # Limit for testing
    if max_papers:
        retry_df = retry_df.head(max_papers)
        logger.info(f"Limited to {max_papers} papers for testing")

    # Load database to get metadata
    db_df = pd.read_parquet(DATABASE_PARQUET)

    # Fix type mismatch
    retry_df['literature_id'] = pd.to_numeric(retry_df['literature_id'], errors='coerce').astype('Int64')
    db_df['literature_id'] = pd.to_numeric(db_df['literature_id'], errors='coerce').astype('Int64')

    # Merge to get full metadata (but preserve year from log if it exists)
    if 'year' not in retry_df.columns:
        retry_df = retry_df.merge(
            db_df[['literature_id', 'authors', 'title', 'year', 'pdf_url']],
            left_on='literature_id',
            right_on='literature_id',
            how='left'
        )
    else:
        # year already in retry_df from log, just get authors/title/pdf_url
        retry_df = retry_df.merge(
            db_df[['literature_id', 'authors', 'title', 'pdf_url']],
            left_on='literature_id',
            right_on='literature_id',
            how='left',
            suffixes=('', '_db')
        )

    # Load session with cookies if provided
    session = load_session_cookies(cookie_file) if cookie_file else None

    # Retry downloads
    print(f"\nRetrying {len(retry_df)} PDFs...")
    print(f"Timeout: {TIMEOUT}s (was 30s)")
    print(f"Rate limit: {RATE_LIMIT_DELAY}s")
    if cookie_file:
        print(f"Using cookies from: {cookie_file}")

    results = []

    for idx, row in tqdm(retry_df.iterrows(), total=len(retry_df), desc="Retrying"):
        # Get output path
        year = row['year']
        year_dir = OUTPUT_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        filename = get_pdf_filename(row['authors'], row['title'], year)
        output_path = year_dir / filename

        # Skip if already exists (from previous retry)
        if output_path.exists():
            results.append({
                'literature_id': row['literature_id'],
                'filename': f"{year}/{filename}",
                'status': 'skipped',
                'message': 'Already downloaded',
                'file_size': output_path.stat().st_size,
                'url': row['pdf_url'],
                'year': year,
                'previous_status': row['status'],
                'retry_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            continue

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

        # Download with updated settings
        result = download_pdf(
            row['pdf_url'],
            output_path,
            row['literature_id'],
            timeout=TIMEOUT,
            retries=MAX_RETRIES
        )

        results.append({
            'literature_id': row['literature_id'],
            'filename': f"{year}/{filename}",
            'status': result['status'],
            'message': result['message'],
            'file_size': result['file_size'],
            'url': row['pdf_url'],
            'year': year,
            'previous_status': row['status'],
            'retry_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        # Log non-success
        if result['status'] not in ['success', 'skipped']:
            logger.warning(f"{row['literature_id']}: {result['status']} - {result['message']}")

    # Save retry log
    results_df = pd.DataFrame(results)
    RETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(RETRY_LOG, index=False)
    logger.info(f"Retry log saved: {RETRY_LOG}")

    # Summary
    status_counts = results_df['status'].value_counts()
    success_count = status_counts.get('success', 0)
    total_size = results_df[results_df['status'] == 'success']['file_size'].sum()

    print("\n" + "="*80)
    print("RETRY SUMMARY")
    print("="*80)
    print(f"\nTotal papers retried: {len(results)}")
    print(f"\nRetry results:")
    for status, count in status_counts.items():
        print(f"  • {status}: {count} ({count/len(results)*100:.1f}%)")

    if success_count > 0:
        print(f"\n✅ Successfully recovered: {success_count} PDFs")
        print(f"   Total size: {total_size / 1024 / 1024:.2f} MB")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

def generate_failure_report():
    """
    Generate CSV report of all failures for shark-references.

    Groups failures by error type and provides summary statistics.
    """
    logger = setup_logging()

    print("\n" + "="*80)
    print("GENERATING FAILURE REPORT FOR SHARK-REFERENCES")
    print("="*80)

    # Load download log
    if not LOG_FILE.exists():
        logger.error(f"Download log not found: {LOG_FILE}")
        return

    log_df = pd.read_csv(LOG_FILE)

    # Filter to failures only
    failure_df = log_df[~log_df['status'].isin(['success', 'skipped'])].copy()

    # Create structured report (log already has all key info)
    report_df = failure_df[[
        'literature_id', 'filename', 'year', 'url', 'status', 'message', 'download_date'
    ]].copy()

    # Clean literature_id for readability
    report_df['literature_id'] = report_df['literature_id'].astype(float).astype(int)

    # Sort by status then year
    report_df = report_df.sort_values(['status', 'year'], ascending=[True, False])

    # Save
    FAILURE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(FAILURE_REPORT, index=False)

    # Summary by status
    print(f"\nTotal failures: {len(report_df)}")
    print("\nFailure breakdown:")
    for status, count in report_df['status'].value_counts().items():
        print(f"  • {status}: {count} ({count/len(report_df)*100:.1f}%)")

    # Top error messages
    print("\nTop 10 error messages:")
    for msg, count in report_df['message'].value_counts().head(10).items():
        print(f"  • {msg[:80]}: {count}")

    print(f"\n✅ Failure report saved: {FAILURE_REPORT}")
    print("="*80)

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Retry failed PDF downloads',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--status',
        nargs='+',
        choices=['timeout', 'error', 'forbidden', 'not_found'],
        default=['timeout'],
        help='Status codes to retry (default: timeout)'
    )

    parser.add_argument(
        '--cookies',
        type=str,
        help='Path to browser cookies file (Netscape format) for institutional access'
    )

    parser.add_argument(
        '--max-papers',
        type=int,
        help='Maximum number of papers to retry (for testing)'
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only generate failure report, do not retry downloads'
    )

    parser.add_argument(
        '--domain',
        type=str,
        help='Filter to specific domain (e.g., "sciencedirect.com", "wiley.com")'
    )

    args = parser.parse_args()

    if args.report_only:
        generate_failure_report()
    else:
        retry_failed_downloads(args.status, args.cookies, args.max_papers, args.domain)

        # Generate failure report after retry
        print("\n")
        generate_failure_report()

if __name__ == "__main__":
    main()
