#!/usr/bin/env python3
"""
FAST Parallel FULL PDF Extraction

Extracts techniques + researcher data using all CPU cores.
- Techniques and disciplines
- Author names from filenames
- Researcher records and collaborations
- Countries (basic extraction from text)
- Shark species (from predefined list)
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
from collections import defaultdict

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
SHARK_SPECIES = None
COUNTRIES = None

def init_worker():
    """Initialize each worker process with techniques and reference data."""
    global TECHNIQUES, SHARK_SPECIES, COUNTRIES

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

    # Load shark species (common names and scientific names)
    # This is a simplified list - expand as needed
    SHARK_SPECIES = [
        'white shark', 'great white', 'Carcharodon carcharias',
        'tiger shark', 'Galeocerdo cuvier',
        'bull shark', 'Carcharhinus leucas',
        'hammerhead', 'Sphyrna',
        'whale shark', 'Rhincodon typus',
        'basking shark', 'Cetorhinus maximus',
        'mako', 'Isurus',
        'blue shark', 'Prionace glauca',
        'reef shark', 'Carcharhinus',
        'blacktip', 'grey reef', 'whitetip',
        'nurse shark', 'Ginglymostoma',
        'lemon shark', 'Negaprion',
        'sand tiger', 'Carcharias taurus',
        'thresher', 'Alopias',
        'goblin shark', 'Mitsukurina',
        'megamouth', 'Megachasma',
        'Port Jackson', 'Heterodontus',
        'wobbegong', 'Orectolobus',
        'dogfish', 'Squalus',
        'catshark', 'Scyliorhinus',
        'sawshark', 'Pristiophorus',
        'angel shark', 'Squatina',
        'frilled shark', 'Chlamydoselachus',
        'Carcharhinidae', 'Lamnidae', 'Sphyrnidae'
    ]

    # Compile species patterns
    SHARK_SPECIES = [re.compile(r'\b' + re.escape(sp) + r'\b', re.IGNORECASE) for sp in SHARK_SPECIES]

    # Load countries (simplified list - top 50 countries)
    COUNTRIES = [
        'Australia', 'United States', 'USA', 'Canada', 'Mexico', 'Brazil', 'Argentina', 'Chile',
        'United Kingdom', 'UK', 'France', 'Germany', 'Spain', 'Italy', 'Portugal', 'Netherlands',
        'South Africa', 'Egypt', 'Kenya', 'Tanzania', 'Madagascar', 'Mozambique',
        'China', 'Japan', 'Korea', 'India', 'Indonesia', 'Malaysia', 'Philippines', 'Thailand',
        'New Zealand', 'Fiji', 'Papua New Guinea',
        'Saudi Arabia', 'UAE', 'Oman', 'Qatar',
        'Norway', 'Sweden', 'Denmark', 'Iceland', 'Russia',
        'Costa Rica', 'Ecuador', 'Peru', 'Colombia', 'Venezuela',
        'Ireland', 'Greece', 'Turkey', 'Israel'
    ]

    COUNTRIES = [re.compile(r'\b' + re.escape(c) + r'\b', re.IGNORECASE) for c in COUNTRIES]

def extract_authors_from_filename(filename):
    """Extract author surnames from PDF filename.

    Expected format: Surname.etal.YEAR.Title.pdf or Surname1.Surname2.YEAR.Title.pdf
    """
    authors = []

    # Remove .pdf extension
    name = filename.replace('.pdf', '')

    # Split by dots
    parts = name.split('.')

    if len(parts) < 2:
        return []

    # First part is usually lead author
    lead = parts[0].strip()
    if lead and not lead.isdigit() and len(lead) > 1:
        authors.append({
            'surname': lead,
            'is_lead': True
        })

    # Check for "etal" or additional authors
    for part in parts[1:]:
        part = part.strip()

        # Stop at year (4 digits)
        if re.match(r'^\d{4}$', part):
            break

        # Skip "etal" or common words
        if part.lower() in ['etal', 'et', 'al', 'and', 'the']:
            continue

        # Add if looks like a name
        if part and not part.isdigit() and len(part) > 1 and not re.match(r'^\d', part):
            authors.append({
                'surname': part,
                'is_lead': False
            })

    return authors

def process_single_pdf(pdf_path):
    """Process one PDF - extract everything."""
    global TECHNIQUES, SHARK_SPECIES, COUNTRIES

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

        # Extract year from folder
        year = int(pdf_path.parent.name) if pdf_path.parent.name.isdigit() else None

        # Extract authors from filename
        authors = extract_authors_from_filename(pdf_path.name)

        # Search for techniques
        techniques_found = []
        for tech in TECHNIQUES:
            matches = tech['pattern'].findall(text)
            if matches:
                # Get context sample
                match_pos = text.find(matches[0])
                context_start = max(0, match_pos - CONTEXT_CHARS)
                context_end = min(len(text), match_pos + len(matches[0]) + CONTEXT_CHARS)
                context = text[context_start:context_end].replace('\n', ' ')

                techniques_found.append({
                    'technique_name': tech['name'],
                    'discipline': tech['discipline'],
                    'counts_for_data': tech['counts_for_data'],
                    'mention_count': len(matches),
                    'context': context[:200]  # Limit context to 200 chars
                })

        if not techniques_found:
            return None

        # Calculate disciplines
        disciplines = {}
        for tech in techniques_found:
            disc = tech['discipline']
            if disc not in disciplines:
                disciplines[disc] = {'count': 0, 'type': 'primary'}
            disciplines[disc]['count'] += 1

            # Cross-cutting DATA
            if tech['counts_for_data'] and disc != 'DATA':
                if 'DATA' not in disciplines:
                    disciplines['DATA'] = {'count': 0, 'type': 'cross_cutting'}
                disciplines['DATA']['count'] += 1

        # Search for shark species
        species_found = set()
        for sp_pattern in SHARK_SPECIES:
            if sp_pattern.search(text):
                species_found.add(sp_pattern.pattern.replace(r'\b', '').replace('\\', ''))

        # Search for countries
        countries_found = set()
        for country_pattern in COUNTRIES:
            if country_pattern.search(text):
                countries_found.add(country_pattern.pattern.replace(r'\b', '').replace('\\', ''))

        return {
            'paper_id': pdf_path.name,
            'year': year,
            'authors': authors,
            'techniques': techniques_found,
            'disciplines': disciplines,
            'species': list(species_found),
            'countries': list(countries_found)
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

        # Write techniques
        for tech in result['techniques']:
            cursor.execute(
                """INSERT OR REPLACE INTO paper_techniques
                   (paper_id, technique_name, primary_discipline, mention_count,
                    context_sample, extraction_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (paper_id, tech['technique_name'], tech['discipline'],
                 tech['mention_count'], tech['context'], datetime.now().isoformat())
            )

        # Write disciplines
        for disc, info in result['disciplines'].items():
            cursor.execute(
                """INSERT OR REPLACE INTO paper_disciplines
                   (paper_id, year, discipline_code, assignment_type, technique_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (paper_id, year, disc, info['type'], info['count'])
            )

        # Write authors and build researcher records
        for i, author in enumerate(result['authors']):
            surname = author['surname']
            is_lead = author['is_lead']

            # Create or update researcher record
            cursor.execute(
                """INSERT OR IGNORE INTO researchers (surname, first_paper_year, last_paper_year)
                   VALUES (?, ?, ?)""",
                (surname, year, year)
            )

            # Update year range if needed
            if year:
                cursor.execute(
                    """UPDATE researchers
                       SET first_paper_year = MIN(first_paper_year, ?),
                           last_paper_year = MAX(last_paper_year, ?)
                       WHERE surname = ?""",
                    (year, year, surname)
                )

            # Get researcher_id
            cursor.execute("SELECT researcher_id FROM researchers WHERE surname = ?", (surname,))
            researcher_id = cursor.fetchone()[0]

            # Link paper to author
            cursor.execute(
                """INSERT OR IGNORE INTO paper_authors
                   (paper_id, researcher_id, author_position, is_lead_author)
                   VALUES (?, ?, ?, ?)""",
                (paper_id, researcher_id, i + 1, is_lead)
            )

            # Link researcher to techniques
            for tech in result['techniques']:
                cursor.execute(
                    """INSERT OR IGNORE INTO researcher_techniques
                       (researcher_id, technique_name, first_used_year, last_used_year)
                       VALUES (?, ?, ?, ?)""",
                    (researcher_id, tech['technique_name'], year, year)
                )

                # Update year range
                if year:
                    cursor.execute(
                        """UPDATE researcher_techniques
                           SET first_used_year = MIN(first_used_year, ?),
                               last_used_year = MAX(last_used_year, ?),
                               usage_count = usage_count + 1
                           WHERE researcher_id = ? AND technique_name = ?""",
                        (year, year, researcher_id, tech['technique_name'])
                    )

            # Link researcher to disciplines
            for disc in result['disciplines'].keys():
                cursor.execute(
                    """INSERT OR IGNORE INTO researcher_disciplines
                       (researcher_id, discipline_code, first_year, last_year)
                       VALUES (?, ?, ?, ?)""",
                    (researcher_id, disc, year, year)
                )

                # Update year range
                if year:
                    cursor.execute(
                        """UPDATE researcher_disciplines
                           SET first_year = MIN(first_year, ?),
                               last_year = MAX(last_year, ?),
                               paper_count = paper_count + 1
                           WHERE researcher_id = ? AND discipline_code = ?""",
                        (year, year, researcher_id, disc)
                    )

        # Build collaboration network
        if len(result['authors']) > 1:
            # Get all researcher IDs for this paper
            author_ids = []
            for author in result['authors']:
                cursor.execute("SELECT researcher_id FROM researchers WHERE surname = ?",
                             (author['surname'],))
                row = cursor.fetchone()
                if row:
                    author_ids.append(row[0])

            # Create collaboration edges (all pairs)
            for i, id1 in enumerate(author_ids):
                for id2 in author_ids[i+1:]:
                    # Ensure consistent ordering (smaller ID first)
                    r1, r2 = (id1, id2) if id1 < id2 else (id2, id1)

                    cursor.execute(
                        """INSERT OR IGNORE INTO collaborations
                           (researcher_1_id, researcher_2_id, first_collaboration_year,
                            last_collaboration_year)
                           VALUES (?, ?, ?, ?)""",
                        (r1, r2, year, year)
                    )

                    # Update collaboration
                    if year:
                        cursor.execute(
                            """UPDATE collaborations
                               SET first_collaboration_year = MIN(first_collaboration_year, ?),
                                   last_collaboration_year = MAX(last_collaboration_year, ?),
                                   collaboration_count = collaboration_count + 1
                               WHERE researcher_1_id = ? AND researcher_2_id = ?""",
                            (year, year, r1, r2)
                        )

        # Log success
        cursor.execute(
            """INSERT OR REPLACE INTO extraction_log
               (paper_id, status, techniques_found, authors_found, extraction_date)
               VALUES (?, 'success', ?, ?, ?)""",
            (paper_id, len(result['techniques']), len(result['authors']),
             datetime.now().isoformat())
        )

    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Fast parallel FULL PDF extraction')
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    num_workers = args.workers or max(1, cpu_count() - 1)

    print("=" * 80)
    print("FAST PARALLEL FULL PDF EXTRACTION")
    print("=" * 80)
    print(f"\n🚀 Using {num_workers} CPU cores\n")

    # Get all PDFs
    all_pdfs = sorted(PDF_BASE.glob("*/*.pdf"))

    # Load already processed
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check what's already been extracted
    cursor.execute("SELECT paper_id FROM extraction_log WHERE status = 'success'")
    processed = {row[0] for row in cursor.fetchall()}
    conn.close()

    # Filter to unprocessed
    unprocessed = [p for p in all_pdfs if p.name not in processed]

    print(f"Total PDFs: {len(all_pdfs):,}")
    print(f"Already done: {len(processed):,}")
    print(f"To process: {len(unprocessed):,}\n")

    if not unprocessed:
        print("✅ All PDFs already processed!")
        return

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

    # Print final statistics
    if not args.dry_run:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        print("\n" + "=" * 80)
        print("EXTRACTION STATISTICS")
        print("=" * 80)

        cursor.execute("SELECT COUNT(*) FROM researchers")
        print(f"Unique researchers: {cursor.fetchone()[0]:,}")

        cursor.execute("SELECT COUNT(*) FROM collaborations")
        print(f"Collaboration pairs: {cursor.fetchone()[0]:,}")

        cursor.execute("SELECT COUNT(DISTINCT technique_name) FROM researcher_techniques")
        print(f"Techniques used: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM paper_techniques")
        print(f"Total technique mentions: {cursor.fetchone()[0]:,}")

        conn.close()

if __name__ == "__main__":
    main()
