#!/usr/bin/env python3
"""
Build Analysis Tables from Technique Extraction

Creates CSV exports for downstream analysis:
- Discipline trends by year
- Technique trends by year
- Data science segmentation (DATA-only vs cross-cutting)
- Top techniques overall
- Discipline co-occurrence matrix

Output: outputs/analysis/*.csv
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_BASE = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
DATABASE = PROJECT_BASE / "database/technique_taxonomy.db"
OUTPUT_DIR = PROJECT_BASE / "outputs/analysis"

def create_discipline_trends():
    """Create discipline trends by year."""
    print("📊 Building discipline trends by year...")

    conn = sqlite3.connect(DATABASE)

    query = """
    SELECT
        year,
        discipline_code,
        COUNT(DISTINCT paper_id) as paper_count,
        SUM(technique_count) as total_techniques,
        assignment_type
    FROM paper_disciplines
    WHERE year IS NOT NULL
        AND year >= 1950
        AND year <= 2025
    GROUP BY year, discipline_code, assignment_type
    ORDER BY year, discipline_code
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    output_file = OUTPUT_DIR / "discipline_trends_by_year.csv"
    df.to_csv(output_file, index=False)
    print(f"   ✓ Saved: {output_file}")
    print(f"   {len(df):,} rows, {df['year'].min()}-{df['year'].max()}")

    return df

def create_technique_trends():
    """Create technique trends by year."""
    print("\n🔬 Building technique trends by year...")

    conn = sqlite3.connect(DATABASE)

    # Get year from paper_disciplines
    query = """
    SELECT
        pd.year,
        pt.technique_name,
        pt.primary_discipline,
        COUNT(DISTINCT pt.paper_id) as paper_count,
        SUM(pt.mention_count) as total_mentions,
        AVG(pt.mention_count) as avg_mentions_per_paper
    FROM paper_techniques pt
    JOIN paper_disciplines pd ON pt.paper_id = pd.paper_id
    WHERE pd.year IS NOT NULL
        AND pd.year >= 1950
        AND pd.year <= 2025
    GROUP BY pd.year, pt.technique_name, pt.primary_discipline
    ORDER BY pd.year, paper_count DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    output_file = OUTPUT_DIR / "technique_trends_by_year.csv"
    df.to_csv(output_file, index=False)
    print(f"   ✓ Saved: {output_file}")
    print(f"   {len(df):,} rows")
    print(f"   {df['technique_name'].nunique()} unique techniques")
    print(f"   Years: {df['year'].min()}-{df['year'].max()}")

    return df

def create_data_science_segmentation():
    """Create DATA-only vs cross-cutting breakdown."""
    print("\n📈 Building Data Science segmentation...")

    conn = sqlite3.connect(DATABASE)

    # Papers with DATA discipline
    query_data = """
    SELECT DISTINCT paper_id, year
    FROM paper_disciplines
    WHERE discipline_code = 'DATA'
    """

    data_papers = pd.read_sql_query(query_data, conn)

    # For each DATA paper, check if it has other disciplines
    results = []

    for _, row in data_papers.iterrows():
        paper_id = row['paper_id']
        year = row['year']

        # Get all disciplines for this paper
        cursor = conn.cursor()
        cursor.execute(
            "SELECT discipline_code, assignment_type FROM paper_disciplines WHERE paper_id = ?",
            (paper_id,)
        )
        disciplines = cursor.fetchall()

        disc_codes = [d[0] for d in disciplines]
        data_type = next((d[1] for d in disciplines if d[0] == 'DATA'), None)

        # Classify
        has_data = 'DATA' in disc_codes
        has_other = any(d != 'DATA' for d in disc_codes)

        category = None
        if has_data and not has_other:
            category = 'DATA_only'
        elif has_data and has_other:
            if data_type == 'primary':
                category = 'DATA_primary_with_others'
            else:
                category = 'DATA_cross_cutting'

        results.append({
            'paper_id': paper_id,
            'year': year,
            'category': category,
            'num_disciplines': len(disc_codes),
            'disciplines': ','.join(disc_codes),
            'data_assignment_type': data_type
        })

    conn.close()

    df = pd.DataFrame(results)

    output_file = OUTPUT_DIR / "data_science_segmentation.csv"
    df.to_csv(output_file, index=False)
    print(f"   ✓ Saved: {output_file}")
    print(f"   {len(df):,} DATA papers total")
    print(f"\n   Breakdown:")
    for cat, count in df['category'].value_counts().items():
        print(f"      {cat}: {count:,} papers ({count/len(df)*100:.1f}%)")

    return df

def create_top_techniques():
    """Create top techniques overall."""
    print("\n🏆 Building top techniques summary...")

    conn = sqlite3.connect(DATABASE)

    query = """
    SELECT
        technique_name,
        primary_discipline,
        COUNT(DISTINCT paper_id) as paper_count,
        SUM(mention_count) as total_mentions,
        AVG(mention_count) as avg_mentions_per_paper,
        MAX(mention_count) as max_mentions
    FROM paper_techniques
    GROUP BY technique_name, primary_discipline
    ORDER BY paper_count DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    output_file = OUTPUT_DIR / "top_techniques.csv"
    df.to_csv(output_file, index=False)
    print(f"   ✓ Saved: {output_file}")
    print(f"   {len(df)} techniques total")
    print(f"\n   Top 10 techniques by paper count:")
    for idx, row in df.head(10).iterrows():
        print(f"      {row['technique_name']}: {row['paper_count']:,} papers")

    return df

def create_discipline_cooccurrence():
    """Create discipline co-occurrence matrix."""
    print("\n🔗 Building discipline co-occurrence matrix...")

    conn = sqlite3.connect(DATABASE)

    # Get all unique discipline pairs per paper
    query = """
    SELECT DISTINCT p1.paper_id, p1.discipline_code as disc1, p2.discipline_code as disc2
    FROM paper_disciplines p1
    JOIN paper_disciplines p2 ON p1.paper_id = p2.paper_id
    WHERE p1.discipline_code < p2.discipline_code
    """

    df = pd.read_sql_query(query, conn)

    # Count co-occurrences
    cooccur = df.groupby(['disc1', 'disc2']).size().reset_index(name='count')

    # Create full matrix
    disciplines = ['BEH', 'BIO', 'CON', 'DATA', 'FISH', 'GEN', 'MOV', 'TRO']
    matrix = pd.DataFrame(0, index=disciplines, columns=disciplines)

    for _, row in cooccur.iterrows():
        matrix.loc[row['disc1'], row['disc2']] = row['count']
        matrix.loc[row['disc2'], row['disc1']] = row['count']

    # Get single discipline counts
    cursor = conn.cursor()
    for disc in disciplines:
        cursor.execute(
            "SELECT COUNT(DISTINCT paper_id) FROM paper_disciplines WHERE discipline_code = ?",
            (disc,)
        )
        matrix.loc[disc, disc] = cursor.fetchone()[0]

    conn.close()

    output_file = OUTPUT_DIR / "discipline_cooccurrence_matrix.csv"
    matrix.to_csv(output_file)
    print(f"   ✓ Saved: {output_file}")
    print(f"   {len(disciplines)} x {len(disciplines)} matrix")

    return matrix

def create_summary_stats():
    """Create overall summary statistics."""
    print("\n📋 Building summary statistics...")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    stats = {}

    # Papers
    cursor.execute("SELECT COUNT(*) FROM extraction_log WHERE status = 'success'")
    stats['total_papers_extracted'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT paper_id) FROM paper_techniques")
    stats['papers_with_techniques'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT paper_id) FROM paper_disciplines")
    stats['papers_with_disciplines'] = cursor.fetchone()[0]

    # Techniques
    cursor.execute("SELECT COUNT(DISTINCT technique_name) FROM paper_techniques")
    stats['unique_techniques'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM paper_techniques")
    stats['total_technique_mentions'] = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(cnt) FROM (SELECT COUNT(*) as cnt FROM paper_techniques GROUP BY paper_id)")
    stats['avg_techniques_per_paper'] = cursor.fetchone()[0]

    # Disciplines
    cursor.execute("SELECT discipline_code, COUNT(DISTINCT paper_id) as cnt FROM paper_disciplines GROUP BY discipline_code ORDER BY cnt DESC")
    discipline_counts = cursor.fetchall()

    # Year range
    cursor.execute("SELECT MIN(year), MAX(year) FROM paper_disciplines WHERE year IS NOT NULL")
    min_year, max_year = cursor.fetchone()
    stats['year_range_start'] = min_year
    stats['year_range_end'] = max_year

    conn.close()

    # Convert to DataFrame
    df_stats = pd.DataFrame([stats])
    df_disciplines = pd.DataFrame(discipline_counts, columns=['discipline_code', 'paper_count'])

    output_file_stats = OUTPUT_DIR / "summary_statistics.csv"
    df_stats.to_csv(output_file_stats, index=False)
    print(f"   ✓ Saved: {output_file_stats}")

    output_file_disc = OUTPUT_DIR / "discipline_summary.csv"
    df_disciplines.to_csv(output_file_disc, index=False)
    print(f"   ✓ Saved: {output_file_disc}")

    print(f"\n   Key Stats:")
    print(f"      Papers extracted: {stats['total_papers_extracted']:,}")
    print(f"      Unique techniques: {stats['unique_techniques']}")
    print(f"      Year range: {stats['year_range_start']}-{stats['year_range_end']}")
    print(f"      Avg techniques/paper: {stats['avg_techniques_per_paper']:.2f}")

    return df_stats, df_disciplines

def main():
    """Build all analysis tables."""
    print("=" * 80)
    print("BUILDING ANALYSIS TABLES")
    print("=" * 80)
    print(f"\nDatabase: {DATABASE}")
    print(f"Output: {OUTPUT_DIR}\n")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build tables
    discipline_trends = create_discipline_trends()
    technique_trends = create_technique_trends()
    data_segmentation = create_data_science_segmentation()
    top_techniques = create_top_techniques()
    cooccurrence = create_discipline_cooccurrence()
    summary_stats, discipline_summary = create_summary_stats()

    print("\n" + "=" * 80)
    print("✅ ALL ANALYSIS TABLES COMPLETE")
    print("=" * 80)
    print(f"\nFiles created in: {OUTPUT_DIR}/")
    print("""
    - discipline_trends_by_year.csv
    - technique_trends_by_year.csv
    - data_science_segmentation.csv
    - top_techniques.csv
    - discipline_cooccurrence_matrix.csv
    - summary_statistics.csv
    - discipline_summary.csv
    """)

    print(f"\nTimestamp: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
