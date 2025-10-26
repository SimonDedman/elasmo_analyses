#!/usr/bin/env python3
"""
Generate corrected search queries for Shark-References using OR logic for synonyms.

The original search_query and search_query_alt columns used problematic AND logic
(e.g., "+GBM +XGBoost" would exclude papers mentioning only one term).

The corrected approach: When synonyms exist, they should be ORed together since
a paper using ANY of the synonymous terms is relevant.

Example:
- Synonyms: "BRT, GBM, XGBoost, gradient boosting"
- Old (wrong): "+GBM +XGBoost"
- New (correct): "BRT OR GBM OR XGBoost OR gradient boosting"

Usage:
    python scripts/generate_corrected_search_queries.py
"""

import pandas as pd
import re
from pathlib import Path

# File paths
input_csv = Path("data/master_techniques.csv")
output_csv = Path("data/master_techniques_with_new_queries.csv")


def parse_synonyms(syn_text):
    """Parse synonyms field into a list of terms."""
    if pd.isna(syn_text) or syn_text == "NA":
        return []

    # Split on commas, strip whitespace
    return [s.strip() for s in syn_text.split(",") if s.strip()]


def generate_search_query_new(row):
    """
    Generate corrected search query using OR logic for synonyms.

    Rules:
    1. If synonyms exist, OR them together with the main technique name
    2. Keep essential modifiers as AND (+)
    3. Use exact phrases where needed
    4. Prefer OR over AND for related terms
    """
    technique = row['technique_name']
    synonyms_raw = row['synonyms']
    category = row['category_name']

    # Parse synonyms
    synonyms = parse_synonyms(synonyms_raw)

    # Special cases and manual corrections

    # Boosted Regression Trees - the example case
    if technique == "Boosted Regression Trees":
        # Synonyms: BRT, GBM, XGBoost, gradient boosting
        # Use OR for all terms
        return "BRT OR GBM OR XGBoost OR \"gradient boosting\" OR \"boosted regression\""

    # If technique has synonyms, OR them together
    if synonyms:
        # Start with main technique name
        terms = [technique]
        # Add all synonyms
        terms.extend(synonyms)

        # For multi-word terms, wrap in quotes
        quoted_terms = []
        for term in terms:
            # Check if term has spaces (multi-word)
            if ' ' in term and not term.startswith('"'):
                quoted_terms.append(f'"{term}"')
            else:
                quoted_terms.append(term)

        # Join with OR
        return " OR ".join(quoted_terms)

    # No synonyms - use the technique name
    # For multi-word techniques, use exact phrase
    if ' ' in technique:
        return f'"{technique}"'
    else:
        return technique


def main():
    """Generate corrected search queries for all techniques."""

    print(f"Reading: {input_csv}")
    df = pd.read_csv(input_csv)

    print(f"Processing {len(df)} techniques...")

    # Generate new search queries
    df['search_query_new'] = df.apply(generate_search_query_new, axis=1)

    # Save updated CSV
    df.to_csv(output_csv, index=False)
    print(f"\nSaved to: {output_csv}")

    # Show some examples
    print("\n" + "="*80)
    print("EXAMPLE CORRECTIONS:")
    print("="*80)

    examples = [
        "Boosted Regression Trees",
        "Random Forest",
        "Acoustic Telemetry",
        "DNA Metabarcoding",
        "IUCN Red List Assessment"
    ]

    for tech in examples:
        row = df[df['technique_name'] == tech]
        if not row.empty:
            row = row.iloc[0]
            print(f"\nTechnique: {tech}")
            print(f"Synonyms: {row['synonyms']}")
            print(f"Old query: {row['search_query']}")
            print(f"New query: {row['search_query_new']}")

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total techniques: {len(df)}")
    print(f"With synonyms: {df['synonyms'].notna().sum()}")
    print(f"Without synonyms: {df['synonyms'].isna().sum()}")

    # Show techniques with most synonyms
    print("\nTechniques with most synonym terms:")
    df['synonym_count'] = df['synonyms'].apply(
        lambda x: len(parse_synonyms(x)) if pd.notna(x) and x != "NA" else 0
    )
    top_synonyms = df.nlargest(10, 'synonym_count')[
        ['technique_name', 'synonym_count', 'synonyms', 'search_query_new']
    ]
    print(top_synonyms.to_string(index=False))


if __name__ == "__main__":
    main()
