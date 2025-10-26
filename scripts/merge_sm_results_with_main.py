#!/usr/bin/env python3
"""
Merge supplementary material (SM) search results with main paper results.

Purpose:
- When querying PDFs for techniques, SM files are searched separately
- If a technique is found in SM but not in main paper, add it to main paper results
- This ensures complete technique coverage per publication

Usage:
    python scripts/merge_sm_results_with_main.py \
        --results results.csv \
        --sm-mapping outputs/supplementary_materials_mapping.csv \
        --output results_merged.csv
"""

import pandas as pd
from pathlib import Path
import argparse
from collections import defaultdict


def load_sm_mapping(sm_mapping_path):
    """
    Load SM-to-main mapping.

    Returns:
        dict: {sm_file: main_file}
    """
    df = pd.read_csv(sm_mapping_path)

    mapping = {}
    for _, row in df.iterrows():
        mapping[str(row['sm_file'])] = str(row['main_file'])

    return mapping


def merge_sm_results(results_df, sm_mapping):
    """
    Merge SM results with main paper results.

    Logic:
    1. Group results by technique
    2. For each technique:
       - Find papers where technique was found
       - Check if any are SM files
       - If technique found in SM but not main, add to main
       - Remove SM entry (keep only main paper)

    Args:
        results_df: DataFrame with columns [paper_path, technique, found]
        sm_mapping: dict {sm_file: main_file}

    Returns:
        DataFrame: Merged results
    """
    print("=" * 80)
    print("MERGING SM RESULTS WITH MAIN PAPERS")
    print("=" * 80)

    # Create reverse mapping for fast lookup
    sm_files = set(sm_mapping.keys())
    main_files = set(sm_mapping.values())

    print(f"\nSM files in mapping: {len(sm_files)}")
    print(f"Main files in mapping: {len(main_files)}")

    # Group by technique
    techniques = results_df['technique'].unique()
    print(f"\nTechniques found: {len(techniques)}")

    merged_results = []
    sm_merged_count = 0
    sm_only_count = 0

    for technique in techniques:
        # Get all papers where this technique was found
        technique_results = results_df[
            (results_df['technique'] == technique) &
            (results_df['found'] == True)
        ]

        papers_with_technique = set(technique_results['paper_path'].values)

        # Separate SM and main papers
        sm_papers_with_technique = papers_with_technique & sm_files
        main_papers_with_technique = papers_with_technique - sm_files

        # For each SM paper, check if main paper also has this technique
        for sm_paper in sm_papers_with_technique:
            main_paper = sm_mapping[sm_paper]

            if main_paper in main_papers_with_technique:
                # Main paper already has this technique - remove SM entry
                sm_merged_count += 1
            else:
                # Main paper doesn't have this technique - add it
                merged_results.append({
                    'paper_path': main_paper,
                    'technique': technique,
                    'found': True,
                    'source': 'SM',  # Indicate this came from SM
                    'sm_file': sm_paper
                })
                sm_only_count += 1

    # Add merged results to original
    if merged_results:
        merged_df = pd.DataFrame(merged_results)
        results_df = pd.concat([results_df, merged_df], ignore_index=True)

    # Remove SM entries (keep only main papers)
    results_df = results_df[~results_df['paper_path'].isin(sm_files)]

    print(f"\nMerge statistics:")
    print(f"  SM entries with technique also in main: {sm_merged_count} (removed)")
    print(f"  Techniques found only in SM: {sm_only_count} (added to main)")
    print(f"  Total SM entries removed: {len(sm_files)}")

    return results_df


def main():
    parser = argparse.ArgumentParser(
        description='Merge SM search results with main paper results'
    )

    parser.add_argument(
        '--results',
        required=True,
        help='Path to search results CSV'
    )

    parser.add_argument(
        '--sm-mapping',
        required=True,
        help='Path to SM mapping CSV'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Path to output merged CSV'
    )

    args = parser.parse_args()

    # Load inputs
    print(f"\nLoading results: {args.results}")
    results_df = pd.read_csv(args.results)
    print(f"  Loaded {len(results_df):,} search results")

    print(f"\nLoading SM mapping: {args.sm_mapping}")
    sm_mapping = load_sm_mapping(args.sm_mapping)
    print(f"  Loaded {len(sm_mapping)} SM-to-main mappings")

    # Merge
    merged_df = merge_sm_results(results_df, sm_mapping)

    # Save
    print(f"\nSaving merged results: {args.output}")
    merged_df.to_csv(args.output, index=False)
    print(f"  Saved {len(merged_df):,} results")

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

    # Summary
    print(f"\nBefore merge: {len(results_df):,} results")
    print(f"After merge: {len(merged_df):,} results")
    print(f"SM files removed: {len(results_df) - len(merged_df):,}")


if __name__ == "__main__":
    main()
