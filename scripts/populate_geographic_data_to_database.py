#!/usr/bin/env python3
"""
Populate Geographic Data into Database

This script imports the REFINED (FIXED) geographic data from CSV files into the database.

Tables updated:
- extraction_log: Add author_country, author_institution columns
- researchers: Populate country field
- institutions: Add institution records with countries
- Create new paper_geography table for comprehensive geographic metadata

Author: Claude Code
Date: 2025-11-24
"""

import sqlite3
import csv
from pathlib import Path
from datetime import datetime

# Paths
DB_PATH = Path("database/technique_taxonomy.db")
CSV_DIR = Path("outputs/researchers")

# CSV files (REFINED FIXED versions)
COUNTRY_MAPPING_CSV = CSV_DIR / "paper_country_mapping_REFINED_FIXED.csv"
AFFILIATIONS_CSV = CSV_DIR / "paper_affiliations_REFINED.csv"
REGIONAL_CSV = CSV_DIR / "papers_by_region_REFINED_FIXED.csv"

# Global North countries (for classification)
GLOBAL_NORTH = {
    'USA', 'Canada', 'UK', 'Germany', 'France', 'Italy', 'Spain', 'Portugal',
    'Netherlands', 'Belgium', 'Switzerland', 'Austria', 'Sweden', 'Norway',
    'Denmark', 'Finland', 'Iceland', 'Ireland', 'Luxembourg', 'Greece',
    'Poland', 'Czech Republic', 'Hungary', 'Slovakia', 'Slovenia', 'Croatia',
    'Romania', 'Bulgaria', 'Australia', 'New Zealand', 'Japan', 'South Korea',
    'Taiwan', 'Hong Kong', 'Singapore', 'Israel', 'United Arab Emirates',
    'Qatar', 'Saudi Arabia', 'Kuwait', 'Palau', 'Bahrain', 'Malta', 'Cyprus',
}

def create_paper_geography_table(cursor):
    """Create comprehensive paper_geography table if it doesn't exist."""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_geography (
            paper_id TEXT PRIMARY KEY,

            -- Author institution data
            first_author_institution TEXT,
            first_author_country TEXT,
            first_author_region TEXT,  -- Global North/South

            -- Study location data (to be populated later - Phase 4)
            study_country TEXT,
            study_ocean_basin TEXT,
            study_latitude REAL,
            study_longitude REAL,
            study_location_text TEXT,  -- Raw text extracted from Methods

            -- Metadata
            has_author_country BOOLEAN DEFAULT 0,
            has_study_location BOOLEAN DEFAULT 0,
            is_parachute_research BOOLEAN DEFAULT 0,  -- Author country != Study country

            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (paper_id) REFERENCES extraction_log(paper_id)
        )
    """)

    print("✓ Created paper_geography table")

def populate_from_csvs(cursor):
    """Populate database from REFINED FIXED CSV files."""

    # Load country mapping
    print("\n=== Loading country mapping CSV ===")
    country_map = {}
    with open(COUNTRY_MAPPING_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            country_map[row['paper_id']] = row['country']

    print(f"Loaded {len(country_map):,} paper-country mappings")

    # Load affiliations
    print("\n=== Loading affiliations CSV ===")
    affiliation_map = {}  # paper_id -> first affiliation
    with open(AFFILIATIONS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row['paper_id']
            if paper_id not in affiliation_map:  # Store first affiliation only
                affiliation_map[paper_id] = row['affiliation']

    print(f"Loaded {len(affiliation_map):,} paper affiliations")

    # Insert into paper_geography
    print("\n=== Populating paper_geography table ===")
    inserted = 0
    updated = 0

    for paper_id, country in country_map.items():
        institution = affiliation_map.get(paper_id, None)
        region = "Global North" if country in GLOBAL_NORTH else "Global South"

        # Try insert, if exists update
        try:
            cursor.execute("""
                INSERT INTO paper_geography
                (paper_id, first_author_institution, first_author_country,
                 first_author_region, has_author_country, updated_date)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (paper_id, institution, country, region, datetime.now().isoformat()))
            inserted += 1
        except sqlite3.IntegrityError:
            # Already exists, update
            cursor.execute("""
                UPDATE paper_geography
                SET first_author_institution = ?,
                    first_author_country = ?,
                    first_author_region = ?,
                    has_author_country = 1,
                    updated_date = ?
                WHERE paper_id = ?
            """, (institution, country, region, datetime.now().isoformat(), paper_id))
            updated += 1

        if (inserted + updated) % 1000 == 0:
            print(f"  Progress: {inserted + updated:,} papers processed")

    print(f"✓ Inserted {inserted:,} new records")
    print(f"✓ Updated {updated:,} existing records")

    return inserted + updated

def populate_institutions_table(cursor):
    """Populate institutions table with unique institutions and countries."""

    print("\n=== Populating institutions table ===")

    # Get unique institution-country pairs from paper_geography
    cursor.execute("""
        SELECT DISTINCT first_author_institution, first_author_country
        FROM paper_geography
        WHERE first_author_institution IS NOT NULL
        AND first_author_country IS NOT NULL
    """)

    institution_data = cursor.fetchall()
    print(f"Found {len(institution_data):,} unique institution-country pairs")

    inserted = 0
    for institution, country in institution_data:
        try:
            cursor.execute("""
                INSERT INTO institutions
                (institution_name, country, created_date)
                VALUES (?, ?, ?)
            """, (institution, country, datetime.now().isoformat()))
            inserted += 1
        except sqlite3.IntegrityError:
            # Already exists, skip
            pass

    print(f"✓ Inserted {inserted:,} new institution records")
    return inserted

def update_extraction_log(cursor):
    """Add columns to extraction_log if they don't exist."""

    print("\n=== Updating extraction_log schema ===")

    # Check if columns exist
    cursor.execute("PRAGMA table_info(extraction_log)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'author_country' not in columns:
        cursor.execute("ALTER TABLE extraction_log ADD COLUMN author_country TEXT")
        print("✓ Added author_country column to extraction_log")

    if 'author_institution' not in columns:
        cursor.execute("ALTER TABLE extraction_log ADD COLUMN author_institution TEXT")
        print("✓ Added author_institution column to extraction_log")

    # Populate from paper_geography
    print("\n=== Populating extraction_log with geographic data ===")
    cursor.execute("""
        UPDATE extraction_log
        SET author_country = (
            SELECT first_author_country
            FROM paper_geography
            WHERE paper_geography.paper_id = extraction_log.paper_id
        ),
        author_institution = (
            SELECT first_author_institution
            FROM paper_geography
            WHERE paper_geography.paper_id = extraction_log.paper_id
        )
        WHERE paper_id IN (SELECT paper_id FROM paper_geography)
    """)

    updated = cursor.rowcount
    print(f"✓ Updated {updated:,} records in extraction_log")

    return updated

def generate_summary_stats(cursor):
    """Generate summary statistics."""

    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80 + "\n")

    # Total papers with country data
    cursor.execute("SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1")
    total_with_country = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM extraction_log")
    total_papers = cursor.fetchone()[0]

    coverage = (total_with_country / total_papers) * 100

    print(f"Papers in database: {total_papers:,}")
    print(f"Papers with author country: {total_with_country:,} ({coverage:.1f}%)")

    # Top countries
    cursor.execute("""
        SELECT first_author_country, COUNT(*) as count
        FROM paper_geography
        WHERE first_author_country IS NOT NULL
        GROUP BY first_author_country
        ORDER BY count DESC
        LIMIT 10
    """)

    print(f"\nTop 10 countries:")
    for country, count in cursor.fetchall():
        pct = (count / total_with_country) * 100
        print(f"  {country:20s} {count:5,} papers ({pct:5.1f}%)")

    # Global North/South
    cursor.execute("""
        SELECT first_author_region, COUNT(*) as count
        FROM paper_geography
        WHERE first_author_region IS NOT NULL
        GROUP BY first_author_region
    """)

    print(f"\nGlobal distribution:")
    for region, count in cursor.fetchall():
        pct = (count / total_with_country) * 100
        print(f"  {region:15s} {count:5,} papers ({pct:5.1f}%)")

def main():
    """Main execution function."""

    print("="*80)
    print("POPULATING GEOGRAPHIC DATA INTO DATABASE")
    print("="*80 + "\n")

    print(f"Database: {DB_PATH}")
    print(f"Input CSVs:")
    print(f"  - {COUNTRY_MAPPING_CSV}")
    print(f"  - {AFFILIATIONS_CSV}")
    print()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create paper_geography table
        create_paper_geography_table(cursor)

        # Populate from CSVs
        total_populated = populate_from_csvs(cursor)

        # Populate institutions table
        populate_institutions_table(cursor)

        # Update extraction_log
        update_extraction_log(cursor)

        # Commit changes
        conn.commit()
        print("\n✓ All changes committed to database")

        # Generate summary stats
        generate_summary_stats(cursor)

        print("\n" + "="*80)
        print("DATABASE POPULATION COMPLETE")
        print("="*80 + "\n")

        print("Tables updated:")
        print("  ✓ paper_geography (new table created)")
        print("  ✓ institutions (populated with {0:,} institutions)".format(
            cursor.execute("SELECT COUNT(*) FROM institutions").fetchone()[0]))
        print("  ✓ extraction_log (added author_country, author_institution)")
        print()
        print(f"Total papers with geographic data: {total_populated:,}")
        print(f"Coverage: {(total_populated/12240)*100:.1f}% of 12,240 papers")
        print()
        print("Next step:")
        print("  - Phase 4: Extract study location from Methods sections")
        print("  - Populate study_country, study_ocean_basin fields in paper_geography")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    main()
