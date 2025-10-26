#!/usr/bin/env python3
"""
download_pdfs_from_database.py

Download PDFs from the literature review database.

Reads PDF URLs from the literature_review database and downloads them
to the specified output directory with proper error handling, rate limiting,
and resume capability.

Input:
    - outputs/literature_review.parquet (or .duckdb)

Output:
    - PDFs saved to: /media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/
    - Download log: logs/pdf_download_log.csv
    - Summary report: docs/database/pdf_download_report.md

Features:
    - Parallel downloads (configurable threads)
    - Rate limiting (avoid server blocks)
    - Resume capability (skip already downloaded)
    - Error handling (paywalls, timeouts, etc.)
    - Progress tracking

Author: Simon Dedman
Date: 2025-10-21
Version: 1.0
"""

import pandas as pd
import requests
from pathlib import Path
from datetime import datetime
import time
from urllib.parse import urlparse
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from tqdm import tqdm

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
BASE_DIR = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DATABASE_PARQUET = BASE_DIR / "outputs/literature_review.parquet"
OUTPUT_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
LOG_FILE = BASE_DIR / "logs/pdf_download_log.csv"
REPORT_FILE = BASE_DIR / "docs/database/pdf_download_report.md"

# Download settings
MAX_WORKERS = 4  # Number of parallel downloads
RATE_LIMIT_DELAY = 1.0  # Seconds between requests (per thread)
TIMEOUT = 30  # Request timeout in seconds
MAX_RETRIES = 3  # Number of retry attempts
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ============================================================================
# SETUP LOGGING
# ============================================================================

def setup_logging():
    """Setup logging configuration."""
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'pdf_download.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_filename(text, max_length=200):
    """
    Create a safe filename from text.

    Args:
        text: Input text (e.g., paper title)
        max_length: Maximum filename length

    Returns:
        Safe filename string
    """
    # Remove problematic characters
    safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_'))
    # Collapse multiple spaces
    safe = " ".join(safe.split())
    # Truncate
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe.strip()

def extract_first_author(authors_str):
    """
    Extract first author surname from authors string.

    Args:
        authors_str: Full author string (e.g., "Smith, J.A., Jones, B.C.")

    Returns:
        First author surname
    """
    if pd.isna(authors_str) or authors_str == '':
        return 'Unknown'

    # Split by common separators
    if ',' in authors_str:
        # Format: "Lastname, Firstname" or "Lastname, F."
        first_author = authors_str.split(',')[0].strip()
    elif ';' in authors_str:
        first_author = authors_str.split(';')[0].strip()
    elif ' and ' in authors_str.lower():
        first_author = authors_str.split(' and ')[0].strip()
    elif '&' in authors_str:
        first_author = authors_str.split('&')[0].strip()
    else:
        # Single author or unusual format - take first word
        first_author = authors_str.split()[0].strip()

    # Remove any remaining punctuation
    first_author = ''.join(c for c in first_author if c.isalnum())

    return first_author if first_author else 'Unknown'

def has_multiple_authors(authors_str):
    """Check if there are multiple authors."""
    if pd.isna(authors_str) or authors_str == '':
        return False

    # Check for common multi-author indicators
    indicators = [',', ';', ' and ', '&', ' et al']
    return any(ind in authors_str.lower() for ind in indicators)

def abbreviate_title(title, max_length=60):
    """
    Abbreviate title for filename.

    Removes common words and truncates long words while maintaining readability.

    Args:
        title: Full paper title
        max_length: Maximum length for abbreviated title

    Returns:
        Abbreviated title string
    """
    if pd.isna(title) or title == '':
        return 'untitled'

    # Common words to remove
    stop_words = {
        'the', 'a', 'an', 'in', 'of', 'for', 'with', 'from', 'to', 'and',
        'or', 'by', 'at', 'on', 'is', 'are', 'was', 'were', 'be', 'been',
        'as', 'this', 'that', 'these', 'those', 'their', 'its'
    }

    # Split into words and clean
    words = title.split()
    abbreviated = []

    for word in words:
        # Remove punctuation except hyphens
        clean_word = ''.join(c if c.isalnum() or c == '-' else ' ' for c in word)
        clean_word = clean_word.strip()

        if not clean_word:
            continue

        # Skip stop words (but keep if it's a significant part of a phrase)
        if clean_word.lower() in stop_words and len(clean_word) <= 3:
            continue

        # Truncate very long words (>10 chars) but keep important ones intact
        if len(clean_word) > 10:
            # Keep certain important words intact
            important_patterns = ['shark', 'chondrichth', 'elasmo', 'popul', 'conserv', 'manage']
            if not any(pattern in clean_word.lower() for pattern in important_patterns):
                clean_word = clean_word[:8]  # Truncate

        abbreviated.append(clean_word)

        # Stop if we're getting too long
        if len(' '.join(abbreviated)) > max_length:
            break

    result = ' '.join(abbreviated)

    # Final length check and truncate if needed
    if len(result) > max_length:
        result = result[:max_length].rsplit(' ', 1)[0]  # Cut at last word boundary

    return result if result else 'untitled'

def get_pdf_filename(authors, title, year):
    """
    Generate PDF filename from paper metadata.

    Format: FirstAuthor.etal.YYYY.Abbreviated Title.pdf
            or FirstAuthor.YYYY.Abbreviated Title.pdf (single author)

    Args:
        authors: Authors string
        title: Paper title
        year: Publication year

    Returns:
        Filename string
    """
    first_author = extract_first_author(authors)
    abbreviated_title = abbreviate_title(title, max_length=60)

    # Add .etal if multiple authors
    if has_multiple_authors(authors):
        author_part = f"{first_author}.etal"
    else:
        author_part = first_author

    # Sanitize the abbreviated title for filename
    safe_title = sanitize_filename(abbreviated_title, max_length=60)

    return f"{author_part}.{year}.{safe_title}.pdf"

def is_valid_pdf_url(url):
    """Check if URL looks like a valid PDF link."""
    if pd.isna(url) or url == '':
        return False

    url_lower = url.lower()
    # Check for common PDF indicators
    if url_lower.endswith('.pdf'):
        return True
    if 'pdf' in url_lower:
        return True
    if any(domain in url_lower for domain in ['doi.org', 'sciencedirect', 'springer', 'wiley']):
        return True

    return False

# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

def download_pdf(url, output_path, paper_id, timeout=TIMEOUT, retries=MAX_RETRIES):
    """
    Download a single PDF with retry logic.

    Args:
        url: PDF URL
        output_path: Where to save the PDF
        paper_id: Literature ID (for logging)
        timeout: Request timeout
        retries: Number of retry attempts

    Returns:
        dict with status, message, and file_size
    """
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/pdf,application/octet-stream,*/*'
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)

            # Check status code
            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('Content-Type', '').lower()

                # Write to file
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                file_size = output_path.stat().st_size

                # Verify it's actually a PDF (check magic bytes)
                with open(output_path, 'rb') as f:
                    header = f.read(4)
                    if header != b'%PDF':
                        output_path.unlink()  # Delete non-PDF file
                        return {
                            'status': 'error',
                            'message': f'Not a valid PDF (got {content_type})',
                            'file_size': 0
                        }

                return {
                    'status': 'success',
                    'message': 'Downloaded successfully',
                    'file_size': file_size
                }

            elif response.status_code == 403:
                return {
                    'status': 'forbidden',
                    'message': 'Access forbidden (paywall/authentication)',
                    'file_size': 0
                }
            elif response.status_code == 404:
                return {
                    'status': 'not_found',
                    'message': 'PDF not found (404)',
                    'file_size': 0
                }
            else:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'file_size': 0
                }

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {
                'status': 'timeout',
                'message': f'Timeout after {timeout}s',
                'file_size': 0
            }

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {
                'status': 'error',
                'message': f'Request error: {str(e)[:100]}',
                'file_size': 0
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected error: {str(e)[:100]}',
                'file_size': 0
            }

    return {
        'status': 'error',
        'message': f'Failed after {retries} attempts',
        'file_size': 0
    }

def download_paper(row, output_dir, existing_files, rate_limit_delay):
    """
    Download a single paper's PDF.

    Args:
        row: DataFrame row with paper metadata
        output_dir: Output directory path (base, will create year subfolders)
        existing_files: Dict mapping year -> set of filenames
        rate_limit_delay: Delay between requests

    Returns:
        dict with download result
    """
    paper_id = row['literature_id']
    pdf_url = row['pdf_url']
    title = row['title']
    authors = row['authors']
    year = row['year']

    # Create year subfolder
    year_dir = output_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = get_pdf_filename(authors, title, year)
    output_path = year_dir / filename

    # Check if already downloaded (check in year subfolder)
    if year in existing_files and filename in existing_files[year]:
        return {
            'literature_id': paper_id,
            'filename': f"{year}/{filename}",
            'status': 'skipped',
            'message': 'Already downloaded',
            'file_size': output_path.stat().st_size if output_path.exists() else 0,
            'url': pdf_url
        }

    # Rate limiting
    time.sleep(rate_limit_delay)

    # Download
    result = download_pdf(pdf_url, output_path, paper_id)

    return {
        'literature_id': paper_id,
        'filename': f"{year}/{filename}",
        'status': result['status'],
        'message': result['message'],
        'file_size': result['file_size'],
        'url': pdf_url,
        'year': year
    }

# ============================================================================
# MAIN DOWNLOAD PIPELINE
# ============================================================================

def main():
    """Main download pipeline."""
    print("="*80)
    print("PDF DOWNLOAD FROM LITERATURE DATABASE")
    print("="*80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {OUTPUT_DIR}")

    # Load database
    print("\nLoading database...")
    if not DATABASE_PARQUET.exists():
        logger.error(f"Database not found: {DATABASE_PARQUET}")
        return

    df = pd.read_parquet(DATABASE_PARQUET)
    logger.info(f"Loaded {len(df):,} papers")

    # Filter papers with PDF URLs
    df_with_pdfs = df[df['pdf_url'].notna() & (df['pdf_url'] != '')].copy()
    logger.info(f"Papers with PDF URLs: {len(df_with_pdfs):,} ({len(df_with_pdfs)/len(df)*100:.1f}%)")

    # Further filter to valid-looking URLs
    df_with_pdfs['valid_url'] = df_with_pdfs['pdf_url'].apply(is_valid_pdf_url)
    df_valid = df_with_pdfs[df_with_pdfs['valid_url']].copy()
    logger.info(f"Papers with valid PDF URLs: {len(df_valid):,}")

    if len(df_valid) == 0:
        logger.warning("No papers with valid PDF URLs to download")
        return

    # Check existing files (scan year subfolders)
    existing_files = {}  # year -> set of filenames
    total_existing = 0

    for year_dir in OUTPUT_DIR.glob("*"):
        if year_dir.is_dir() and year_dir.name.isdigit():
            year = int(year_dir.name)
            existing_files[year] = set(f.name for f in year_dir.glob("*.pdf"))
            total_existing += len(existing_files[year])

    logger.info(f"Already downloaded: {total_existing} PDFs across {len(existing_files)} year folders")

    # Papers to download (check if file exists in year subfolder)
    df_valid['filename'] = df_valid.apply(
        lambda row: get_pdf_filename(row['authors'], row['title'], row['year']),
        axis=1
    )
    df_valid['already_exists'] = df_valid.apply(
        lambda row: row['year'] in existing_files and row['filename'] in existing_files[row['year']],
        axis=1
    )
    df_to_download = df_valid[~df_valid['already_exists']]

    logger.info(f"Papers to download: {len(df_to_download):,}")

    if len(df_to_download) == 0:
        logger.info("All PDFs already downloaded!")
        return

    # Download PDFs
    print(f"\nDownloading {len(df_to_download):,} PDFs using {MAX_WORKERS} threads...")
    print(f"Rate limit: {RATE_LIMIT_DELAY}s per request")
    print(f"Estimated time: {len(df_to_download) * RATE_LIMIT_DELAY / MAX_WORKERS / 60:.0f}-{len(df_to_download) * RATE_LIMIT_DELAY / MAX_WORKERS / 60 * 2:.0f} minutes")

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all download tasks
        future_to_paper = {
            executor.submit(
                download_paper,
                row,
                OUTPUT_DIR,
                existing_files,
                RATE_LIMIT_DELAY
            ): idx
            for idx, row in df_to_download.iterrows()
        }

        # Process completed downloads with progress bar
        with tqdm(total=len(df_to_download), desc="Downloading PDFs") as pbar:
            for future in as_completed(future_to_paper):
                result = future.result()
                results.append(result)
                pbar.update(1)

                # Log errors
                if result['status'] not in ['success', 'skipped']:
                    logger.warning(f"{result['literature_id']}: {result['status']} - {result['message']}")

    # Save download log
    print("\nSaving download log...")
    results_df = pd.DataFrame(results)
    results_df['download_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(LOG_FILE, index=False)
    logger.info(f"Download log saved: {LOG_FILE}")

    # Generate summary statistics
    status_counts = results_df['status'].value_counts()
    total_size = results_df[results_df['status'] == 'success']['file_size'].sum()

    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    print(f"\nTotal papers processed: {len(results):,}")
    print(f"\nDownload results:")
    for status, count in status_counts.items():
        print(f"  • {status}: {count:,} ({count/len(results)*100:.1f}%)")

    print(f"\nTotal size downloaded: {total_size / 1024 / 1024 / 1024:.2f} GB")
    print(f"Average PDF size: {total_size / max(status_counts.get('success', 1), 1) / 1024 / 1024:.2f} MB")

    # Generate report
    print("\nGenerating download report...")
    generate_report(results_df, df_valid, total_size)

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

def generate_report(results_df, df_valid, total_size):
    """Generate markdown report of download results."""

    status_counts = results_df['status'].value_counts()
    success_count = status_counts.get('success', 0)

    report = f"""# PDF Download Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source:** Literature Review Database
**Output:** {OUTPUT_DIR}

---

## Summary

**Total papers in database:** {len(df_valid):,}
**Papers attempted:** {len(results_df):,}

### Download Results

| Status | Count | Percentage |
|--------|-------|------------|
"""

    for status, count in status_counts.items():
        report += f"| {status} | {count:,} | {count/len(results_df)*100:.1f}% |\n"

    report += f"""
### Storage

- **Total downloaded:** {total_size / 1024 / 1024 / 1024:.2f} GB
- **Average PDF size:** {total_size / max(success_count, 1) / 1024 / 1024:.2f} MB
- **Output directory:** `{OUTPUT_DIR}`

---

## Common Issues

"""

    # Top error messages
    error_df = results_df[results_df['status'].isin(['error', 'forbidden', 'not_found', 'timeout'])]
    if len(error_df) > 0:
        error_summary = error_df.groupby('message').size().sort_values(ascending=False).head(10)
        report += "**Top 10 error types:**\n\n"
        for message, count in error_summary.items():
            report += f"- {message}: {count:,} papers\n"

    report += f"""

---

## Next Steps

### Successful Downloads ({success_count:,} PDFs)
- Ready for full text extraction
- Can extract author affiliations
- Can search for subtechniques

### Failed Downloads ({len(error_df):,} papers)
- **Paywalls:** {status_counts.get('forbidden', 0):,} papers - require institutional access
- **Not Found:** {status_counts.get('not_found', 0):,} papers - broken links
- **Timeouts:** {status_counts.get('timeout', 0):,} papers - retry later
- **Other Errors:** {status_counts.get('error', 0):,} papers - check log for details

### Recommendations

1. **Re-run for timeouts:** Some papers may succeed on retry
2. **Institutional access:** Use VPN/proxy for paywalled papers
3. **Manual download:** For critical papers, download manually
4. **Alternative sources:** Check ResearchGate, author websites, etc.

---

**Log file:** `{LOG_FILE}`
**Report generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report)
    logger.info(f"Report saved: {REPORT_FILE}")

if __name__ == "__main__":
    main()
