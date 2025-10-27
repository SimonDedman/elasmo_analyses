#!/usr/bin/env python3
"""
PHASE 1: Extract Authors from PDF Filenames (Parallel Processing)
==================================================================
Extract first author, year, and title from standardized PDF filenames.
Uses multiprocessing for fast processing of all 4,545 papers.

Output:
    - outputs/researchers/researchers_from_filenames.csv
    - outputs/researchers/paper_first_authors.csv
    - outputs/researchers/filename_parsing_report.txt

Author: EEA 2025 Data Panel
Date: 2025-10-26
"""

import re
import csv
import sqlite3
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get all paper files from data_science_segmentation.csv
SEGMENTATION_FILE = "outputs/analysis/data_science_segmentation.csv"
OUTPUT_DIR = Path("outputs/researchers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Parallel processing
NUM_WORKERS = 11  # Match system CPU count

# ============================================================================
# FILENAME PARSING
# ============================================================================

def parse_pdf_filename(filename):
    """
    Parse standardized PDF filename to extract metadata.

    Format variations:
        FirstAuthor.etal.YEAR.Title.pdf
        FirstAuthor.YEAR.Title.pdf
        FirstAuthor.etal.YEAR.Title (without .pdf)

    Returns:
        dict with keys: filename, first_author, year, title, has_etal
        or None if parsing fails
    """
    # Remove .pdf extension if present
    name = filename
    if name.endswith('.pdf'):
        name = name[:-4]

    # Try pattern with etal
    pattern_etal = r'^(?P<first_author>[^.]+)\.etal\.(?P<year>\d{4})\.(?P<title>.+)$'
    match = re.match(pattern_etal, name)

    if match:
        return {
            'filename': filename,
            'first_author': match.group('first_author').strip(),
            'year': int(match.group('year')),
            'title': match.group('title').replace('.', ' ').strip(),
            'has_etal': True
        }

    # Try pattern without etal
    pattern_no_etal = r'^(?P<first_author>[^.]+)\.(?P<year>\d{4})\.(?P<title>.+)$'
    match = re.match(pattern_no_etal, name)

    if match:
        return {
            'filename': filename,
            'first_author': match.group('first_author').strip(),
            'year': int(match.group('year')),
            'title': match.group('title').replace('.', ' ').strip(),
            'has_etal': False
        }

    # Parsing failed
    return None

def process_batch(filenames):
    """Process a batch of filenames in parallel."""
    results = []
    failed = []

    for filename in filenames:
        parsed = parse_pdf_filename(filename)
        if parsed:
            results.append(parsed)
        else:
            failed.append(filename)

    return results, failed

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("PHASE 1: AUTHOR EXTRACTION FROM FILENAMES (PARALLEL)")
    print("=" * 80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Workers: {NUM_WORKERS}")

    # Load paper list from segmentation file
    print(f"\n=== Loading paper list from {SEGMENTATION_FILE} ===")

    all_filenames = []
    with open(SEGMENTATION_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_filenames.append(row['paper_id'])

    print(f"Total papers to process: {len(all_filenames):,}")

    # Split into batches for parallel processing
    batch_size = max(1, len(all_filenames) // NUM_WORKERS)
    batches = [all_filenames[i:i + batch_size]
               for i in range(0, len(all_filenames), batch_size)]

    print(f"Batches: {len(batches)} (size: ~{batch_size})")

    # Process in parallel
    print("\n=== Processing filenames in parallel ===")

    all_parsed = []
    all_failed = []

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_batch, batch): i
                   for i, batch in enumerate(batches)}

        completed = 0
        for future in as_completed(futures):
            batch_idx = futures[future]
            parsed, failed = future.result()
            all_parsed.extend(parsed)
            all_failed.extend(failed)
            completed += 1

            if completed % 2 == 0 or completed == len(batches):
                print(f"  Progress: {completed}/{len(batches)} batches "
                      f"({len(all_parsed):,} parsed, {len(all_failed)} failed)")

    print(f"\n✓ Parsing complete!")
    print(f"  Success: {len(all_parsed):,} ({100*len(all_parsed)/len(all_filenames):.1f}%)")
    print(f"  Failed: {len(all_failed)} ({100*len(all_failed)/len(all_filenames):.1f}%)")

    # ========================================================================
    # AGGREGATE RESEARCHER DATA
    # ========================================================================

    print("\n=== Aggregating researcher data ===")

    researcher_stats = defaultdict(lambda: {
        'surname': '',
        'first_year': 9999,
        'last_year': 0,
        'paper_count': 0,
        'years_active': set(),
        'titles': []
    })

    for paper in all_parsed:
        surname = paper['first_author']
        year = paper['year']

        stats = researcher_stats[surname]
        stats['surname'] = surname
        stats['first_year'] = min(stats['first_year'], year)
        stats['last_year'] = max(stats['last_year'], year)
        stats['paper_count'] += 1
        stats['years_active'].add(year)
        stats['titles'].append(paper['title'])

    # Convert to list and calculate years active
    researchers = []
    for surname, stats in researcher_stats.items():
        researchers.append({
            'surname': stats['surname'],
            'first_year': stats['first_year'],
            'last_year': stats['last_year'],
            'years_active': len(stats['years_active']),
            'paper_count': stats['paper_count'],
            'avg_papers_per_year': round(stats['paper_count'] /
                                         max(1, stats['last_year'] - stats['first_year'] + 1), 2)
        })

    # Sort by paper count
    researchers.sort(key=lambda x: x['paper_count'], reverse=True)

    print(f"✓ Identified {len(researchers):,} unique first authors")

    # ========================================================================
    # SAVE OUTPUTS
    # ========================================================================

    print("\n=== Saving outputs ===")

    # 1. Researchers list
    researchers_file = OUTPUT_DIR / "researchers_from_filenames.csv"
    with open(researchers_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'surname', 'first_year', 'last_year', 'years_active',
            'paper_count', 'avg_papers_per_year'
        ])
        writer.writeheader()
        writer.writerows(researchers)

    print(f"✓ Saved: {researchers_file} ({len(researchers):,} researchers)")

    # 2. Paper-author linkages
    paper_authors_file = OUTPUT_DIR / "paper_first_authors.csv"
    # Convert 'filename' key to 'paper_id' for output
    papers_output = []
    for p in all_parsed:
        papers_output.append({
            'paper_id': p['filename'],
            'first_author': p['first_author'],
            'year': p['year'],
            'title': p['title'],
            'has_etal': p['has_etal']
        })

    with open(paper_authors_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'paper_id', 'first_author', 'year', 'title', 'has_etal'
        ])
        writer.writeheader()
        writer.writerows(papers_output)

    print(f"✓ Saved: {paper_authors_file} ({len(all_parsed):,} papers)")

    # 3. Parsing report
    report_file = OUTPUT_DIR / "filename_parsing_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("FILENAME PARSING REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("PARSING STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total files: {len(all_filenames):,}\n")
        f.write(f"Successfully parsed: {len(all_parsed):,} ({100*len(all_parsed)/len(all_filenames):.1f}%)\n")
        f.write(f"Failed to parse: {len(all_failed)} ({100*len(all_failed)/len(all_filenames):.1f}%)\n\n")

        f.write("RESEARCHER STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Unique first authors: {len(researchers):,}\n")
        f.write(f"Average papers per author: {sum(r['paper_count'] for r in researchers) / len(researchers):.1f}\n")
        f.write(f"Median papers per author: {sorted([r['paper_count'] for r in researchers])[len(researchers)//2]}\n\n")

        # Year distribution
        year_counts = Counter(p['year'] for p in all_parsed)
        f.write("PAPERS BY DECADE\n")
        f.write("-" * 80 + "\n")
        for decade in range(1950, 2030, 10):
            count = sum(c for y, c in year_counts.items() if decade <= y < decade + 10)
            if count > 0:
                f.write(f"{decade}s: {count:,} papers\n")
        f.write("\n")

        # Top authors
        f.write("TOP 20 MOST PROLIFIC FIRST AUTHORS\n")
        f.write("-" * 80 + "\n")
        for i, r in enumerate(researchers[:20], 1):
            f.write(f"{i:2d}. {r['surname']:30s} {r['paper_count']:3d} papers "
                   f"({r['first_year']}-{r['last_year']}, {r['years_active']} years active)\n")
        f.write("\n")

        # Has etal distribution
        etal_count = sum(1 for p in all_parsed if p['has_etal'])
        f.write("AUTHOR FORMAT\n")
        f.write("-" * 80 + "\n")
        f.write(f"Papers with 'etal' (multiple authors): {etal_count:,} ({100*etal_count/len(all_parsed):.1f}%)\n")
        f.write(f"Papers without 'etal' (single author): {len(all_parsed)-etal_count:,} ({100*(len(all_parsed)-etal_count)/len(all_parsed):.1f}%)\n\n")

        # Failed parsing examples
        if all_failed:
            f.write("FAILED PARSING EXAMPLES\n")
            f.write("-" * 80 + "\n")
            for filename in all_failed[:20]:
                f.write(f"  {filename}\n")
            if len(all_failed) > 20:
                f.write(f"  ... and {len(all_failed) - 20} more\n")
            f.write("\n")

    print(f"✓ Saved: {report_file}")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n" + "=" * 80)
    print("PHASE 1 COMPLETE - SUMMARY")
    print("=" * 80 + "\n")

    print(f"Papers processed: {len(all_parsed):,} / {len(all_filenames):,} "
          f"({100*len(all_parsed)/len(all_filenames):.1f}% success rate)")
    print(f"Unique first authors: {len(researchers):,}")
    print(f"Year range: {min(p['year'] for p in all_parsed)} - {max(p['year'] for p in all_parsed)}")
    print(f"\nTop 5 most prolific authors:")
    for i, r in enumerate(researchers[:5], 1):
        print(f"  {i}. {r['surname']:20s} {r['paper_count']:3d} papers "
              f"({r['first_year']}-{r['last_year']})")

    print(f"\nFiles created:")
    print(f"  {researchers_file}")
    print(f"  {paper_authors_file}")
    print(f"  {report_file}")

    print(f"\n✓ Phase 1 complete! Ready for Phase 2 (PDF extraction)")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
