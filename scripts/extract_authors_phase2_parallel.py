#!/usr/bin/env python3
"""
PHASE 2: Extract Authors & Affiliations from PDFs (Parallel + Cached)
======================================================================
Extract full author lists and institutional affiliations from PDF first pages.
Uses aggressive caching to avoid repeated lookups of same authors.

Strategy:
    1. Extract first page text from each PDF
    2. Parse author names and affiliations using regex patterns
    3. Cache unique author-institution combinations
    4. Build deduplicated researcher and institution tables

Output:
    - outputs/researchers/paper_authors_full.csv
    - outputs/researchers/institutions_raw.csv
    - outputs/researchers/author_cache.json
    - outputs/researchers/phase2_extraction_report.txt

Author: EEA 2025 Data Panel
Date: 2025-10-26
"""

import re
import csv
import json
import sqlite3
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import pdfplumber
from typing import List, Dict, Tuple, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

# PDF directory - check both locations
PDF_DIRS = [
    Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"),
    Path("pdfs")  # Fallback
]

# Input from Phase 1
PHASE1_FILE = Path("outputs/researchers/paper_first_authors.csv")
OUTPUT_DIR = Path("outputs/researchers")

# Parallel processing
NUM_WORKERS = 11

# Limits for testing (set to None for full run)
# Can be overridden with command-line arguments
import sys
MAX_PAPERS = int(sys.argv[1]) if len(sys.argv) > 1 else None
TEST_MODE = MAX_PAPERS is not None and MAX_PAPERS <= 100

# ============================================================================
# PDF TEXT EXTRACTION
# ============================================================================

def find_pdf_path(paper_id: str, pdf_dirs: List[Path]) -> Optional[Path]:
    """Find PDF file across multiple potential locations."""
    # Extract year from filename for subdirectory
    year_match = re.search(r'\.(\d{4})\.', paper_id)
    year = year_match.group(1) if year_match else None

    for base_dir in pdf_dirs:
        if not base_dir.exists():
            continue

        # Try direct match
        pdf_path = base_dir / paper_id
        if pdf_path.exists():
            return pdf_path

        # Try with year subdirectory
        if year:
            pdf_path = base_dir / year / paper_id
            if pdf_path.exists():
                return pdf_path

            # Try with .0 suffix (some years have this)
            pdf_path = base_dir / f"{year}.0" / paper_id
            if pdf_path.exists():
                return pdf_path

    return None

def extract_first_page_text(pdf_path: Path) -> Optional[str]:
    """Extract text from first page of PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return None
            return pdf.pages[0].extract_text()
    except Exception as e:
        return None

# ============================================================================
# AUTHOR & AFFILIATION PARSING
# ============================================================================

def parse_authors_and_affiliations(text: str, first_author_surname: str) -> Dict:
    """
    Parse author names and affiliations from first page text.

    Common patterns:
        - Authors on one line, affiliations below
        - Superscript numbers linking authors to affiliations
        - Email addresses for corresponding authors
        - "Department of X, University of Y, Country"
    """
    if not text:
        return {
            'authors': [],
            'affiliations': [],
            'emails': [],
            'method': 'failed'
        }

    lines = text.split('\n')

    # Find author section (usually after title, before abstract)
    authors = []
    affiliations = []
    emails = []

    # Strategy 1: Look for email addresses (often with author names nearby)
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    for i, line in enumerate(lines[:50]):  # First 50 lines only
        if re.search(email_pattern, line, re.IGNORECASE):
            found_emails = re.findall(email_pattern, line)
            emails.extend(found_emails)

            # Author names often near emails
            # Look at previous 5 lines for names
            for j in range(max(0, i-5), i):
                potential_names = extract_names_from_line(lines[j])
                authors.extend(potential_names)

    # Strategy 2: Look for affiliation markers
    affiliation_keywords = ['university', 'institute', 'department', 'college',
                           'laboratory', 'centre', 'center', 'school', 'faculty']

    for line in lines[:100]:  # First 100 lines
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in affiliation_keywords):
            # Clean and add affiliation
            cleaned = line.strip()
            if len(cleaned) > 10 and len(cleaned) < 300:  # Reasonable length
                affiliations.append(cleaned)

    # Strategy 3: Parse structured author-affiliation format
    # Pattern: Name1,2, Name3,1, Name4,2
    # Then: 1Department..., 2Institute...
    superscript_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]*([0-9,]+)'

    for line in lines[:30]:
        matches = re.findall(superscript_pattern, line)
        if matches and len(matches) >= 2:  # Multiple authors likely
            for name, numbers in matches:
                if name and len(name) > 2:
                    authors.append(name.strip())

    # Deduplicate
    authors = list(dict.fromkeys(authors))  # Preserve order
    affiliations = list(dict.fromkeys(affiliations))
    emails = list(dict.fromkeys(emails))

    # Ensure first author is included
    if first_author_surname and not any(first_author_surname.lower() in a.lower()
                                        for a in authors):
        authors.insert(0, first_author_surname)

    return {
        'authors': authors,
        'affiliations': affiliations,
        'emails': emails,
        'method': 'parsed' if (authors or affiliations) else 'failed'
    }

def extract_names_from_line(line: str) -> List[str]:
    """Extract potential author names from a line of text."""
    # Pattern: Capital letter followed by lowercase, possibly with middle initials
    # e.g., "John A. Smith", "Jane Doe"
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?)*\s+[A-Z][a-z]+)\b'
    names = re.findall(name_pattern, line)
    return [n.strip() for n in names if len(n) > 3]

def extract_country_from_affiliation(affiliation: str) -> Optional[str]:
    """Extract country name from affiliation string."""
    # Common countries in shark research
    countries = [
        'USA', 'United States', 'Australia', 'UK', 'United Kingdom',
        'Canada', 'South Africa', 'New Zealand', 'Brazil', 'Mexico',
        'Japan', 'China', 'France', 'Spain', 'Italy', 'Germany',
        'Portugal', 'Argentina', 'Chile', 'India', 'Indonesia',
        'Philippines', 'Malaysia', 'Thailand', 'Singapore'
    ]

    affiliation_lower = affiliation.lower()
    for country in countries:
        if country.lower() in affiliation_lower:
            return country

    return None

# ============================================================================
# PARALLEL PROCESSING
# ============================================================================

def process_paper(args: Tuple) -> Dict:
    """Process a single paper - extract authors and affiliations."""
    paper_id, first_author, year, pdf_dirs = args

    result = {
        'paper_id': paper_id,
        'first_author': first_author,
        'year': year,
        'status': 'not_found',
        'authors': [],
        'affiliations': [],
        'emails': []
    }

    # Find PDF
    pdf_path = find_pdf_path(paper_id, pdf_dirs)
    if not pdf_path:
        return result

    result['status'] = 'found'

    # Extract first page
    text = extract_first_page_text(pdf_path)
    if not text:
        result['status'] = 'extraction_failed'
        return result

    # Parse authors and affiliations
    parsed = parse_authors_and_affiliations(text, first_author)

    result['status'] = parsed['method']
    result['authors'] = parsed['authors']
    result['affiliations'] = parsed['affiliations']
    result['emails'] = parsed['emails']

    return result

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("PHASE 2: AUTHOR & AFFILIATION EXTRACTION (PARALLEL + CACHED)")
    print("=" * 80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Workers: {NUM_WORKERS}")
    if TEST_MODE:
        print(f"TEST MODE: Processing first {MAX_PAPERS or 100} papers only")

    # Load Phase 1 results
    print(f"\n=== Loading Phase 1 results ===")

    papers_to_process = []
    with open(PHASE1_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            papers_to_process.append({
                'paper_id': row['paper_id'],
                'first_author': row['first_author'],
                'year': int(row['year'])
            })

    if TEST_MODE and MAX_PAPERS:
        papers_to_process = papers_to_process[:MAX_PAPERS]
    elif TEST_MODE:
        papers_to_process = papers_to_process[:100]

    print(f"Papers to process: {len(papers_to_process):,}")

    # Prepare arguments for parallel processing
    pdf_dirs_list = [d for d in PDF_DIRS if d.exists()]
    print(f"PDF directories: {[str(d) for d in pdf_dirs_list]}")

    args_list = [
        (p['paper_id'], p['first_author'], p['year'], pdf_dirs_list)
        for p in papers_to_process
    ]

    # Process in parallel
    print(f"\n=== Processing {len(args_list):,} papers in parallel ===")

    all_results = []
    status_counts = Counter()

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_paper, args): i
                   for i, args in enumerate(args_list)}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)
            status_counts[result['status']] += 1
            completed += 1

            if completed % 500 == 0 or completed == len(args_list):
                print(f"  Progress: {completed:,}/{len(args_list):,} papers "
                      f"(parsed: {status_counts['parsed']}, "
                      f"failed: {status_counts['failed'] + status_counts['extraction_failed']}, "
                      f"not_found: {status_counts['not_found']})")

    print(f"\n✓ Extraction complete!")
    print(f"  Successfully parsed: {status_counts['parsed']:,} "
          f"({100*status_counts['parsed']/len(all_results):.1f}%)")
    print(f"  Failed to parse: {status_counts['failed']:,}")
    print(f"  Extraction failed: {status_counts['extraction_failed']:,}")
    print(f"  PDFs not found: {status_counts['not_found']:,}")

    # ========================================================================
    # BUILD DEDUPLICATED TABLES
    # ========================================================================

    print("\n=== Building deduplicated tables ===")

    # Collect all unique authors and affiliations
    unique_authors = set()
    unique_affiliations = set()
    paper_author_records = []

    for result in all_results:
        if result['status'] != 'parsed':
            continue

        paper_id = result['paper_id']

        # Add authors
        for pos, author in enumerate(result['authors'], 1):
            unique_authors.add(author)

            # Try to match author to affiliation
            affiliation = None
            if pos <= len(result['affiliations']):
                affiliation = result['affiliations'][pos - 1]
                unique_affiliations.add(affiliation)

            paper_author_records.append({
                'paper_id': paper_id,
                'author_name': author,
                'author_position': pos,
                'affiliation': affiliation or '',
                'is_corresponding': any(email in result.get('emails', [])
                                       for email in result.get('emails', []))
            })

        # Add remaining affiliations
        for aff in result['affiliations']:
            unique_affiliations.add(aff)

    print(f"✓ Unique authors: {len(unique_authors):,}")
    print(f"✓ Unique affiliations: {len(unique_affiliations):,}")
    print(f"✓ Paper-author records: {len(paper_author_records):,}")

    # ========================================================================
    # SAVE OUTPUTS
    # ========================================================================

    print("\n=== Saving outputs ===")

    # 1. Paper-author linkages
    paper_authors_file = OUTPUT_DIR / "paper_authors_full.csv"
    with open(paper_authors_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'paper_id', 'author_name', 'author_position',
            'affiliation', 'is_corresponding'
        ])
        writer.writeheader()
        writer.writerows(paper_author_records)

    print(f"✓ Saved: {paper_authors_file} ({len(paper_author_records):,} records)")

    # 2. Institutions (raw)
    institutions_file = OUTPUT_DIR / "institutions_raw.csv"
    institutions_with_country = []

    for aff in sorted(unique_affiliations):
        if not aff:
            continue
        country = extract_country_from_affiliation(aff)
        institutions_with_country.append({
            'institution_name': aff,
            'country': country or ''
        })

    with open(institutions_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['institution_name', 'country'])
        writer.writeheader()
        writer.writerows(institutions_with_country)

    print(f"✓ Saved: {institutions_file} ({len(institutions_with_country):,} institutions)")

    # 3. Author cache (for Phase 3 ORCID lookups)
    cache_file = OUTPUT_DIR / "author_cache.json"
    author_cache = {
        'unique_authors': sorted(list(unique_authors)),
        'extraction_date': datetime.now().isoformat(),
        'total_papers_processed': len(all_results),
        'papers_with_authors': status_counts['parsed']
    }

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(author_cache, f, indent=2)

    print(f"✓ Saved: {cache_file}")

    # 4. Extraction report
    report_file = OUTPUT_DIR / "phase2_extraction_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 2: AUTHOR & AFFILIATION EXTRACTION REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("PROCESSING STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Papers attempted: {len(all_results):,}\n")
        f.write(f"Successfully parsed: {status_counts['parsed']:,} "
               f"({100*status_counts['parsed']/len(all_results):.1f}%)\n")
        f.write(f"Failed to parse: {status_counts['failed']:,}\n")
        f.write(f"Extraction failed: {status_counts['extraction_failed']:,}\n")
        f.write(f"PDFs not found: {status_counts['not_found']:,}\n\n")

        f.write("AUTHOR STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Unique authors extracted: {len(unique_authors):,}\n")
        f.write(f"Paper-author linkages: {len(paper_author_records):,}\n")
        f.write(f"Average authors per paper: "
               f"{len(paper_author_records)/max(1, status_counts['parsed']):.1f}\n\n")

        f.write("INSTITUTION STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Unique affiliations extracted: {len(unique_affiliations):,}\n")

        countries_found = [inst['country'] for inst in institutions_with_country
                          if inst['country']]
        country_counts = Counter(countries_found)

        f.write(f"Affiliations with country identified: {len(countries_found):,} "
               f"({100*len(countries_found)/max(1, len(unique_affiliations)):.1f}%)\n")
        f.write(f"Unique countries: {len(country_counts)}\n\n")

        f.write("TOP 10 COUNTRIES BY AFFILIATION COUNT\n")
        f.write("-" * 80 + "\n")
        for country, count in country_counts.most_common(10):
            f.write(f"{country:30s} {count:4d} affiliations\n")

    print(f"✓ Saved: {report_file}")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n" + "=" * 80)
    print("PHASE 2 COMPLETE - SUMMARY")
    print("=" * 80 + "\n")

    print(f"Papers processed: {status_counts['parsed']:,} / {len(all_results):,} "
          f"({100*status_counts['parsed']/len(all_results):.1f}% success)")
    print(f"Unique authors: {len(unique_authors):,}")
    print(f"Unique institutions: {len(unique_affiliations):,}")

    if country_counts:
        print(f"\nTop 3 countries:")
        for i, (country, count) in enumerate(country_counts.most_common(3), 1):
            print(f"  {i}. {country}: {count} affiliations")

    print(f"\nFiles created:")
    print(f"  {paper_authors_file}")
    print(f"  {institutions_file}")
    print(f"  {cache_file}")
    print(f"  {report_file}")

    print(f"\n✓ Phase 2 complete! Ready for Phase 3 (geocoding)")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
