#!/usr/bin/env python3
"""
Update search_query_new column in Techniques DB with corrected OR logic for synonyms.

Key principle: Since we're downloading ALL papers from Shark-References, we just need
to search for ANY mention of the technique or its synonyms. Use OR logic to combine
all relevant terms.

Example:
- Technique: "Boosted Regression Trees"
- Synonyms: "BRT, GBM, XGBoost, gradient boosting"
- Query: BRT OR GBM OR XGBoost OR "gradient boosting" OR "boosted regression"

Usage:
    python scripts/update_search_queries_with_or_logic.py
"""

import pandas as pd
import re
from pathlib import Path


def parse_synonyms(syn_text):
    """Parse synonyms field into a list of clean terms."""
    if pd.isna(syn_text) or not syn_text or syn_text == "NaN":
        return []

    # Split on commas or semicolons, strip whitespace
    terms = re.split(r'[,;]', str(syn_text))
    return [s.strip() for s in terms if s.strip()]


def should_quote(term):
    """Determine if a term needs quotes (multi-word phrases)."""
    # Skip if already quoted
    if term.startswith('"') and term.endswith('"'):
        return False

    # Quote if contains spaces (multi-word term)
    if ' ' in term:
        return True

    # Quote if contains special characters that need exact matching
    if any(c in term for c in ['/', '-', '&']):
        return True

    return False


def format_term(term):
    """Format a search term with quotes if needed."""
    if should_quote(term):
        # Remove existing quotes if any
        clean = term.strip('"')
        return f'"{clean}"'
    return term


def generate_search_query_new(row):
    """
    Generate corrected search query using OR logic.

    Strategy:
    1. Extract technique name and all synonyms
    2. Add common abbreviations/variations
    3. OR all terms together
    4. Quote multi-word phrases
    """

    technique = row['technique_name']
    synonyms_raw = row['synonyms']

    # Parse synonyms
    synonyms = parse_synonyms(synonyms_raw)

    # Start with all terms
    all_terms = [technique] + synonyms

    # Remove duplicates (case-insensitive)
    unique_terms = []
    seen_lower = set()
    for term in all_terms:
        term_lower = term.lower()
        if term_lower not in seen_lower:
            unique_terms.append(term)
            seen_lower.add(term_lower)

    # Format each term (add quotes if needed)
    formatted_terms = [format_term(term) for term in unique_terms]

    # Join with OR
    query = " OR ".join(formatted_terms)

    return query


def main():
    """Update search_query_new column in Excel file."""

    # File paths
    excel_path = Path("data/Techniques DB for Panel Review.xlsx")
    output_path = Path("data/Techniques DB for Panel Review_updated.xlsx")

    print(f"Reading: {excel_path}")

    # Read all sheets
    xl_file = pd.ExcelFile(excel_path)
    print(f"Sheets found: {xl_file.sheet_names}")

    # Read the Full_List sheet
    df = pd.read_excel(excel_path, sheet_name='Full_List')
    print(f"\nProcessing {len(df)} techniques from 'Full_List' sheet...")

    # Generate new search queries
    df['search_query_new'] = df.apply(generate_search_query_new, axis=1)

    # Create a writer object to save multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Copy all sheets, updating Full_List
        for sheet_name in xl_file.sheet_names:
            if sheet_name == 'Full_List':
                # Write updated Full_List
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Copy other sheets as-is
                sheet_df = pd.read_excel(excel_path, sheet_name=sheet_name)
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\nSaved to: {output_path}")

    # Show examples
    print("\n" + "="*80)
    print("EXAMPLE SEARCH QUERIES:")
    print("="*80)

    examples = [
        "Boosted Regression Trees",
        "Video Analysis",
        "Acoustic Telemetry",
        "Social Network Analysis",
        "Growth Curve Modeling",
        "IUCN Red List Assessment",
        "eDNA",
        "MaxEnt",
        "BORIS"
    ]

    for tech in examples:
        row = df[df['technique_name'] == tech]
        if not row.empty:
            row = row.iloc[0]
            print(f"\n{tech}")
            if pd.notna(row['synonyms']) and row['synonyms'] != 'NaN':
                print(f"  Synonyms: {row['synonyms']}")
            print(f"  Old: {row['search_query']}")
            print(f"  NEW: {row['search_query_new']}")

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total techniques processed: {len(df)}")

    # Count techniques with/without synonyms
    has_synonyms = df['synonyms'].apply(lambda x: bool(parse_synonyms(x))).sum()
    print(f"With synonyms: {has_synonyms}")
    print(f"Without synonyms: {len(df) - has_synonyms}")

    # Show distribution of OR terms
    df['or_count'] = df['search_query_new'].str.count(' OR ') + 1
    print(f"\nDistribution of OR terms:")
    print(df['or_count'].value_counts().sort_index())

    # Show techniques with most OR terms
    print("\nTechniques with most synonym variations (top 15):")
    top_or = df.nlargest(15, 'or_count')[
        ['technique_name', 'or_count', 'search_query_new']
    ]
    for _, row in top_or.iterrows():
        print(f"\n{row['technique_name']} ({int(row['or_count'])} terms)")
        print(f"  {row['search_query_new']}")

    print(f"\n{'='*80}")
    print(f"Done! Updated file saved to: {output_path}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
