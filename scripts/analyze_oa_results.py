#!/usr/bin/env python3
"""
Analyze Open Access results from Unpaywall lookup.
Generates summary statistics and visualizations.
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
RESULTS_FILE = OUTPUT_DIR / "unpaywall_oa_by_doi.csv"
SHARK_REF_CSV = OUTPUT_DIR / "shark_references_bulk" / "shark_references_complete_2025_to_1950_20251021.csv"


def analyze_oa_results():
    """Generate comprehensive OA analysis."""
    print("=" * 70)
    print("OPEN ACCESS ANALYSIS - SHARK RESEARCH CORPUS")
    print("=" * 70)
    print(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Load results
    if not RESULTS_FILE.exists():
        print("No results file found. Run lookup_unpaywall_oa.py first.")
        return

    df = pd.read_csv(RESULTS_FILE)
    print(f"\nTotal DOIs checked via Unpaywall: {len(df):,}")

    # Load full shark-references data
    shark_df = pd.read_csv(SHARK_REF_CSV)
    total_papers = len(shark_df)
    papers_with_doi = shark_df['doi'].notna().sum()

    print(f"Total papers in shark-references: {total_papers:,}")
    print(f"Papers with DOI: {papers_with_doi:,} ({papers_with_doi/total_papers*100:.1f}%)")
    print(f"Coverage of DOI papers: {len(df)/papers_with_doi*100:.1f}%")

    # OA Status Summary
    print("\n" + "-" * 70)
    print("OPEN ACCESS STATUS (papers with DOIs)")
    print("-" * 70)

    oa_counts = df['oa_status'].value_counts()
    for status, count in oa_counts.items():
        pct = count / len(df) * 100
        print(f"  {status:12s}: {count:6,} ({pct:5.1f}%)")

    # Summary categories
    is_oa = df['oa_is_oa'].sum()
    is_closed = len(df) - is_oa

    print(f"\n  {'TOTAL OA':12s}: {is_oa:6,} ({is_oa/len(df)*100:5.1f}%)")
    print(f"  {'TOTAL CLOSED':12s}: {is_closed:6,} ({is_closed/len(df)*100:5.1f}%)")

    # OA by year
    print("\n" + "-" * 70)
    print("OPEN ACCESS BY YEAR")
    print("-" * 70)

    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    year_stats = df.groupby('year').agg({
        'oa_is_oa': ['sum', 'count'],
        'oa_status': lambda x: (x == 'gold').sum()
    }).round(2)
    year_stats.columns = ['oa_count', 'total', 'gold_count']
    year_stats['oa_pct'] = (year_stats['oa_count'] / year_stats['total'] * 100).round(1)

    print("\nRecent years (2020-2025):")
    for year in range(2025, 2019, -1):
        if year in year_stats.index:
            row = year_stats.loc[year]
            print(f"  {year}: {int(row['oa_count']):4d}/{int(row['total']):4d} OA ({row['oa_pct']:.1f}%) "
                  f"- {int(row['gold_count'])} gold")

    # By decade
    print("\nBy decade:")
    df['decade'] = (df['year'] // 10) * 10
    decade_stats = df.groupby('decade').agg({
        'oa_is_oa': ['sum', 'count']
    })
    decade_stats.columns = ['oa_count', 'total']
    decade_stats['oa_pct'] = (decade_stats['oa_count'] / decade_stats['total'] * 100).round(1)

    for decade in sorted(decade_stats.index.dropna()):
        if decade >= 1950:
            row = decade_stats.loc[decade]
            print(f"  {int(decade)}s: {int(row['oa_count']):5d}/{int(row['total']):5d} OA ({row['oa_pct']:.1f}%)")

    # OA Types explanation
    print("\n" + "-" * 70)
    print("OA STATUS DEFINITIONS")
    print("-" * 70)
    print("""
  gold   : Published in a fully open access journal (e.g., PLOS ONE, Frontiers)
  green  : Toll-access on publisher site, but free copy in a repository
  hybrid : Free under open license in a toll-access journal (author paid APC)
  bronze : Free to read on publisher site, but no open license
  closed : No free version found
  unknown: DOI not found in Unpaywall database
""")

    # License distribution
    print("-" * 70)
    print("LICENSE DISTRIBUTION (OA papers only)")
    print("-" * 70)

    oa_papers = df[df['oa_is_oa'] == True]
    license_counts = oa_papers['oa_license'].value_counts(dropna=False)
    for license_type, count in license_counts.head(10).items():
        pct = count / len(oa_papers) * 100
        license_name = license_type if pd.notna(license_type) else "Not specified"
        print(f"  {license_name:25s}: {count:5,} ({pct:5.1f}%)")

    # Host type distribution
    print("\n" + "-" * 70)
    print("HOST TYPE (where OA version is available)")
    print("-" * 70)

    host_counts = oa_papers['oa_host_type'].value_counts(dropna=False)
    for host_type, count in host_counts.items():
        pct = count / len(oa_papers) * 100
        host_name = host_type if pd.notna(host_type) else "Unknown"
        print(f"  {host_name:15s}: {count:5,} ({pct:5.1f}%)")

    # Version distribution
    print("\n" + "-" * 70)
    print("VERSION AVAILABLE")
    print("-" * 70)

    version_counts = oa_papers['oa_version'].value_counts(dropna=False)
    for version, count in version_counts.items():
        pct = count / len(oa_papers) * 100
        version_name = version if pd.notna(version) else "Unknown"
        print(f"  {version_name:20s}: {count:5,} ({pct:5.1f}%)")

    # Journal-level OA
    print("\n" + "-" * 70)
    print("JOURNAL-LEVEL OPEN ACCESS")
    print("-" * 70)

    journal_oa = df['oa_journal_is_oa'].sum()
    journal_doaj = df['oa_journal_is_in_doaj'].sum()
    print(f"  Papers in fully OA journals: {journal_oa:,} ({journal_oa/len(df)*100:.1f}%)")
    print(f"  Papers in DOAJ-indexed journals: {journal_doaj:,} ({journal_doaj/len(df)*100:.1f}%)")

    # Extrapolate to full corpus
    print("\n" + "-" * 70)
    print("EXTRAPOLATION TO FULL CORPUS")
    print("-" * 70)

    oa_rate = is_oa / len(df)
    papers_without_doi = total_papers - papers_with_doi

    # Conservative estimate: papers without DOI are less likely to be OA
    # (older papers, grey literature, etc.)
    conservative_oa_rate_no_doi = 0.20  # Assume 20% OA for papers without DOI

    estimated_oa_with_doi = int(papers_with_doi * oa_rate)
    estimated_oa_without_doi = int(papers_without_doi * conservative_oa_rate_no_doi)
    estimated_total_oa = estimated_oa_with_doi + estimated_oa_without_doi

    print(f"\n  Papers with DOI ({papers_with_doi:,}):")
    print(f"    Estimated OA: {estimated_oa_with_doi:,} ({oa_rate*100:.1f}%)")
    print(f"\n  Papers without DOI ({papers_without_doi:,}):")
    print(f"    Estimated OA: {estimated_oa_without_doi:,} ({conservative_oa_rate_no_doi*100:.0f}% assumed)")
    print(f"\n  TOTAL CORPUS ({total_papers:,}):")
    print(f"    Estimated OA: {estimated_total_oa:,} ({estimated_total_oa/total_papers*100:.1f}%)")

    # Save summary to CSV
    summary_data = {
        'metric': [
            'total_papers_shark_references',
            'papers_with_doi',
            'dois_checked_unpaywall',
            'oa_papers_with_doi',
            'oa_rate_papers_with_doi',
            'gold_oa_count',
            'green_oa_count',
            'hybrid_oa_count',
            'bronze_oa_count',
            'closed_count',
            'papers_in_oa_journals',
            'papers_in_doaj_journals',
            'estimated_total_oa_corpus',
            'estimated_oa_rate_corpus'
        ],
        'value': [
            total_papers,
            papers_with_doi,
            len(df),
            is_oa,
            round(oa_rate * 100, 1),
            oa_counts.get('gold', 0),
            oa_counts.get('green', 0),
            oa_counts.get('hybrid', 0),
            oa_counts.get('bronze', 0),
            oa_counts.get('closed', 0),
            journal_oa,
            journal_doaj,
            estimated_total_oa,
            round(estimated_total_oa / total_papers * 100, 1)
        ]
    }

    summary_df = pd.DataFrame(summary_data)
    summary_path = OUTPUT_DIR / "analysis" / "oa_summary_statistics.csv"
    summary_path.parent.mkdir(exist_ok=True)
    summary_df.to_csv(summary_path, index=False)
    print(f"\nSummary saved to: {summary_path}")

    # Save year-by-year OA rates
    year_export = year_stats.reset_index()
    year_export.to_csv(OUTPUT_DIR / "analysis" / "oa_by_year.csv", index=False)
    print(f"Year data saved to: {OUTPUT_DIR / 'analysis' / 'oa_by_year.csv'}")


if __name__ == "__main__":
    analyze_oa_results()
