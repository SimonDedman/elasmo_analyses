#!/usr/bin/env python3
"""
FAST Parallel PDF Technique Extraction

Uses all CPU cores for 10x+ speedup.
Simplified version - just extracts and writes, no researcher scaffolding yet.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import subprocess
import re
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import argparse

# Configuration
PROJECT_BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
DATABASE = PROJECT_BASE / "database/technique_taxonomy.db"
OUTPUT_DIR = PROJECT_BASE / "outputs/technique_extraction"

CONTEXT_CHARS = 100
TEXT_TIMEOUT = 10
MAX_TEXT_LENGTH = 500000

# Global variables (loaded once per worker)
TECHNIQUES = None
PROCESSED_PAPERS = None

def init_worker():
    """Initialize each worker process with techniques."""
    global TECHNIQUES

    # Load techniques
    df = pd.read_excel(
        PROJECT_BASE / "data/Techniques DB for Panel Review_UPDATED.xlsx",
        sheet_name='Full_List'
    )

    # Filter
    df['remove_reason_str'] = df['remove_reason'].astype(str)
    keep_mask = (
        df['remove_reason'].isna() |
        df['remove_reason_str'].str.startswith('1') |
        df['remove_reason_str'].str.startswith('2')
    )
    df = df[keep_mask]

    # Build technique list
    TECHNIQUES = []
    for _, row in df.iterrows():
        TECHNIQUES.append({
            'name': row['technique_name'],
            'discipline': row['discipline'],
            'pattern': re.compile(r'\b' + re.escape(row['technique_name']) + r'\b', re.IGNORECASE),
            'counts_for_data': (
                row['discipline'] == 'DATA' or
                row['statistical_model'] or
                row['analytical_algorithm'] or
                row['inference_framework']
            )
        })

def process_single_pdf(pdf_path):
    """Process one PDF - designed for parallel execution."""
    global TECHNIQUES

    try:
        # Extract text
        result = subprocess.run(
            ['pdftotext', str(pdf_path), '-'],
            capture_output=True,
            text=True,
            timeout=TEXT_TIMEOUT
        )

        if result.returncode != 0:
            return None

        text = result.stdout

        if not text or len(text) > MAX_TEXT_LENGTH:
            return None

        # Search for techniques
        found = []
        for tech in TECHNIQUES:
            matches = tech['pattern'].findall(text)
            if matches:
                found.append({
                    'technique_name': tech['name'],
                    'discipline': tech['discipline'],
                    'counts_for_data': tech['counts_for_data'],
                    'mention_count': len(matches)
                })

        # Calculate disciplines even if no techniques found
        # (we want to log ALL papers, including those with zero techniques)
        disciplines = {}
        for tech in found if found else []:
            disc = tech['discipline']
            if disc not in disciplines:
                disciplines[disc] = {'count': 0, 'type': 'primary'}
            disciplines[disc]['count'] += 1

            # Cross-cutting DATA
            if tech['counts_for_data'] and disc != 'DATA':
                if 'DATA' not in disciplines:
                    disciplines['DATA'] = {'count': 0, 'type': 'cross_cutting'}
                disciplines['DATA']['count'] += 1

        return {
            'paper_id': pdf_path.name,
            'year': int(pdf_path.parent.name) if pdf_path.parent.name.isdigit() else None,
            'techniques': found,
            'disciplines': disciplines
        }

    except Exception as e:
        return None

def write_results_to_db(results, dry_run=False):
    """Write batch of results to database."""
    if dry_run or not results:
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for result in results:
        if not result:
            continue

        paper_id = result['paper_id']
        year = result['year']

        # Log the extraction (even if zero techniques)
        cursor.execute(
            """INSERT OR REPLACE INTO extraction_log
               (paper_id, status, techniques_found, extraction_date)
               VALUES (?, 'success', ?, ?)""",
            (paper_id, len(result.get('techniques', [])), datetime.now().isoformat())
        )

        # Write techniques (if any)
        for tech in result.get('techniques', []):
            cursor.execute(
                """INSERT OR REPLACE INTO paper_techniques
                   (paper_id, technique_name, primary_discipline, mention_count, extraction_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (paper_id, tech['technique_name'], tech['discipline'],
                 tech['mention_count'], datetime.now().isoformat())
            )

        # Write disciplines (if any)
        for disc, info in result.get('disciplines', {}).items():
            cursor.execute(
                """INSERT OR REPLACE INTO paper_disciplines
                   (paper_id, year, discipline_code, assignment_type, technique_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (paper_id, year, disc, info['type'], info['count'])
            )

    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Fast parallel PDF extraction')
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    num_workers = args.workers or max(1, cpu_count() - 1)

    print("=" * 80)
    print("FAST PARALLEL PDF EXTRACTION")
    print("=" * 80)
    print(f"\n🚀 Using {num_workers} CPU cores\n")

    # Get all PDFs
    all_pdfs = sorted(PDF_BASE.glob("*/*.pdf"))

    # Load already processed
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT paper_id FROM extraction_log WHERE status = 'success'")
    processed = {row[0] for row in cursor.fetchall()}
    conn.close()

    unprocessed = [p for p in all_pdfs if p.name not in processed]

    print(f"Total PDFs: {len(all_pdfs):,}")
    print(f"Already done: {len(processed):,}")
    print(f"To process: {len(unprocessed):,}\n")

    # Process in parallel
    start_time = time.time()
    batch = []
    batch_size = 100

    with Pool(processes=num_workers, initializer=init_worker) as pool:
        for result in tqdm(pool.imap_unordered(process_single_pdf, unprocessed),
                          total=len(unprocessed),
                          desc="Extracting"):
            if result:
                batch.append(result)

            if len(batch) >= batch_size:
                write_results_to_db(batch, args.dry_run)
                batch = []

        # Final batch
        if batch:
            write_results_to_db(batch, args.dry_run)

    elapsed = time.time() - start_time

    print(f"\n✅ Complete in {elapsed/60:.1f} minutes")
    print(f"   Speed: {len(unprocessed)/elapsed:.1f} PDFs/second")

if __name__ == "__main__":
    main()
