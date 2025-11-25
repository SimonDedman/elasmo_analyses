#!/usr/bin/env python3
"""
Parachute Research Analysis - FIXED Data

Generate comprehensive parachute research analysis from FIXED Phase 4 data.
This script produces the same analysis as the original, but with corrected
word boundary matching and context validation.

Author: Claude Code
Date: 2025-11-24
"""

import sqlite3
import csv
from pathlib import Path
from collections import defaultdict

# Paths
DB_PATH = Path("database/technique_taxonomy.db")
OUTPUT_DIR = Path("outputs")

def main():
    """Generate parachute research analysis from FIXED data."""

    print("\n" + "="*80)
    print("PARACHUTE RESEARCH ANALYSIS - FIXED DATA")
    print("="*80 + "\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all papers with study locations
    cursor.execute("""
        SELECT paper_id, first_author_country, study_country, is_parachute_research
        FROM paper_geography
        WHERE has_study_location = 1
    """)

    papers = cursor.fetchall()

    print(f"Papers with study locations: {len(papers):,}\n")

    # Build country statistics
    country_stats = defaultdict(lambda: {
        'papers_authored': 0,
        'papers_studied': 0,
        'domestic_papers': 0,
        'source_papers_abroad': 0,
        'sink_papers_foreign': 0,
    })

    parachute_count = 0

    for paper_id, author_country, study_country, is_parachute in papers:
        if author_country:
            country_stats[author_country]['papers_authored'] += 1

        if study_country:
            country_stats[study_country]['papers_studied'] += 1

        if is_parachute == 1:
            parachute_count += 1
            if author_country:
                country_stats[author_country]['source_papers_abroad'] += 1
            if study_country:
                country_stats[study_country]['sink_papers_foreign'] += 1
        else:
            # Domestic paper
            if author_country and study_country and author_country == study_country:
                country_stats[author_country]['domestic_papers'] += 1

    print(f"Parachute research cases: {parachute_count:,} ({parachute_count/len(papers)*100:.1f}%)\n")

    # Calculate scores and classify countries
    results = []

    for country, stats in country_stats.items():
        authored = stats['papers_authored']
        studied = stats['papers_studied']
        domestic = stats['domestic_papers']
        source_abroad = stats['source_papers_abroad']
        sink_foreign = stats['sink_papers_foreign']

        # Rates
        domestic_rate = (domestic / authored * 100) if authored > 0 else 0
        source_rate = (source_abroad / authored * 100) if authored > 0 else 0
        sink_rate = (sink_foreign / studied * 100) if studied > 0 else 0

        # Scores (for classification)
        # Sink score: How much more studied than authored (if studied > authored)
        if studied > authored and authored > 0:
            sink_score = (studied - authored) / authored
        else:
            sink_score = 0.0

        # Source score: How much more authored than studied (if authored > studied)
        if authored > studied and studied > 0:
            source_score = (authored - studied) / studied
        else:
            source_score = 0.0

        # Classification
        if sink_score >= 1.0:
            classification = "MAJOR SINK"
        elif sink_score >= 0.5:
            classification = "SINK"
        elif source_score >= 1.0:
            classification = "MAJOR SOURCE"
        elif source_score >= 0.5:
            classification = "SOURCE"
        else:
            classification = "LOW ACTIVITY"

        results.append({
            'country': country,
            'papers_authored': authored,
            'papers_studied': studied,
            'domestic_papers': domestic,
            'source_papers_abroad': source_abroad,
            'sink_papers_foreign': sink_foreign,
            'domestic_rate_%': round(domestic_rate, 1),
            'source_rate_%': round(source_rate, 1),
            'sink_rate_%': round(sink_rate, 1),
            'sink_score': round(sink_score, 2),
            'source_score': round(source_score, 2),
            'classification': classification,
        })

    # Sort by total papers (authored)
    results.sort(key=lambda x: x['papers_authored'], reverse=True)

    # Save to CSV
    output_path = OUTPUT_DIR / 'parachute_research_analysis_FIXED.csv'

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'country', 'papers_authored', 'papers_studied', 'domestic_papers',
            'source_papers_abroad', 'sink_papers_foreign',
            'domestic_rate_%', 'source_rate_%', 'sink_rate_%',
            'sink_score', 'source_score', 'classification'
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"✓ Saved: {output_path}\n")

    # Report top SINKS
    print("=== TOP 5 SINK COUNTRIES ===")
    print("(Countries studied disproportionately more than they produce researchers)\n")

    sinks = [r for r in results if r['classification'] in ['MAJOR SINK', 'SINK']]
    sinks.sort(key=lambda x: x['sink_score'], reverse=True)

    for i, country in enumerate(sinks[:5], 1):
        print(f"{i}. {country['country']}")
        print(f"   Papers authored: {country['papers_authored']}")
        print(f"   Papers studied: {country['papers_studied']}")
        print(f"   Sink score: {country['sink_score']:.2f}")
        print(f"   Classification: {country['classification']}")
        print()

    # Report top SOURCES
    print("=== TOP 5 SOURCE COUNTRIES ===")
    print("(Countries producing researchers who predominantly study abroad)\n")

    sources = [r for r in results if r['classification'] in ['MAJOR SOURCE', 'SOURCE']]
    sources.sort(key=lambda x: x['source_score'], reverse=True)

    for i, country in enumerate(sources[:5], 1):
        print(f"{i}. {country['country']}")
        print(f"   Papers authored: {country['papers_authored']}")
        print(f"   Papers studied: {country['papers_studied']}")
        print(f"   Source score: {country['source_score']:.2f}")
        print(f"   Classification: {country['classification']}")
        print()

    # Compare to original run (if exists)
    original_path = OUTPUT_DIR / 'parachute_research_analysis.csv'

    if original_path.exists():
        print("=== COMPARISON TO ORIGINAL RUN ===\n")

        # Load original
        original_stats = {}
        with open(original_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                original_stats[row['Country']] = {
                    'papers_studied': int(row['Papers_Studied']),
                    'classification': row['Classification'],
                }

        # Compare specific countries that likely had false positives
        print("Countries with major changes:\n")

        for country_name in ['Cuba', 'Iran', 'India']:
            original = original_stats.get(country_name, {})
            fixed = next((r for r in results if r['country'] == country_name), None)

            if original and fixed:
                orig_studied = original['papers_studied']
                fixed_studied = fixed['papers_studied']
                change = fixed_studied - orig_studied

                print(f"{country_name}:")
                print(f"  Original: {orig_studied} papers studied")
                print(f"  FIXED: {fixed_studied} papers studied")
                print(f"  Change: {change:+d} ({change/orig_studied*100:+.1f}%)")
                print()

    conn.close()

    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80 + "\n")

    print(f"Output: {output_path}")
    print(f"Total countries analyzed: {len(results)}")
    print(f"Major SINK countries: {len([r for r in results if r['classification'] == 'MAJOR SINK'])}")
    print(f"Major SOURCE countries: {len([r for r in results if r['classification'] == 'MAJOR SOURCE'])}")

if __name__ == "__main__":
    main()
