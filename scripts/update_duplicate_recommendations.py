#!/usr/bin/env python3
"""
Update duplicate recommendations to prefer abbreviated Dropbox titles.

When there are 3+ versions of a file, ensure the most abbreviated
(Dropbox style) version is kept.

Example:
  Heithaus.etal.2012.The ecological importance of intact top-predator.pdf
  Heithaus.etal.2012.The ecological importance of intact top-predator_v1.pdf
  Heithaus.etal.2012.Ecol import intact top pred popns synth 15 yr res seagrass ecosys.pdf

  Should keep: The abbreviated third one (Dropbox style)
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

project_base = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
duplicates_csv = project_base / "outputs/duplicate_pdfs_to_remove.csv"


def is_abbreviated_title(filename):
    """
    Determine if filename is abbreviated Dropbox style.

    Indicators:
    - Short (< 80 chars in title part)
    - Uses abbreviations like 'etal', 'jName', 'spp', 'var', 'abund'
    - Fewer common words ('of', 'the', 'and')
    """
    # Extract title part (after year)
    parts = filename.replace('.pdf', '').split('.')

    if len(parts) < 3:
        return False

    # Find year
    year_idx = None
    for i, part in enumerate(parts[:5]):
        if part.isdigit() and len(part) == 4:
            year_idx = i
            break

    if year_idx is None:
        return False

    # Get title
    title = '.'.join(parts[year_idx + 1:])

    # Check length
    if len(title) < 50:
        return True

    # Check for abbreviation indicators
    abbrev_indicators = ['etal', 'j', 'spp', 'var', 'abund', 'consrv', 'ecol', 'pred', 'popns']
    has_abbrev = any(ind in title.lower() for ind in abbrev_indicators)

    # Check for common words
    common_words = ['of', 'the', 'and', 'in', 'a', 'for', 'with', 'from', 'to']
    title_words = title.lower().split()
    common_count = sum(1 for w in title_words if w in common_words)

    # Abbreviated if:
    # - Has abbreviations and < 80 chars
    # - Has few common words (< 3) and < 100 chars
    if has_abbrev and len(title) < 80:
        return True
    elif common_count < 3 and len(title) < 100:
        return True

    return False


def count_abbreviations(title):
    """Count number of abbreviated words (Dropbox style indicators)."""
    abbrev_indicators = [
        'ecol', 'pred', 'popns', 'synth', 'consrv', 'hab', 'abund', 'var',
        'spp', 'behav', 'strat', 'energetic', 'endoth', 'forag', 'spat',
        'seg', 'jj', 'mar', 'resp', 'freerang', 'elasmos', 'dep', 'bod',
        'siz', 'whiteshak', 'gws', 'preds', 'prey', 'subtrop', 'ecosys'
    ]
    title_lower = title.lower()
    return sum(1 for ind in abbrev_indicators if ind in title_lower)


def count_common_words(title):
    """Count common words that indicate full (non-abbreviated) title."""
    common = ['the', 'of', 'and', 'in', 'a', 'for', 'with', 'from', 'to', 'on', 'an']
    words = title.lower().split()
    return sum(1 for w in words if w in common)


def find_best_version_to_keep(files):
    """
    Among multiple versions, find the best one to keep.

    Preference order:
    1. Most abbreviated (Dropbox style with many abbreviations)
    2. Non-versioned (_v1, _v2)
    3. Shorter (but not too short)
    """
    # Score each file
    scores = []

    for file_path in files:
        filename = Path(file_path).name

        # Extract title part (after year)
        parts = filename.replace('.pdf', '').split('.')

        # Find year
        year_idx = None
        for i, part in enumerate(parts[:5]):
            if part.isdigit() and len(part) == 4:
                year_idx = i
                break

        if year_idx is None or year_idx + 1 >= len(parts):
            # Can't parse, give low score
            scores.append((file_path, filename, 0))
            continue

        title = '.'.join(parts[year_idx + 1:])

        score = 0

        # High weight for abbreviations (Dropbox style)
        abbrev_count = count_abbreviations(title)
        score += abbrev_count * 20

        # Penalty for common words (full titles)
        common_count = count_common_words(title)
        score -= common_count * 10

        # Prefer shorter titles (but not too short)
        title_len = len(title)
        if 40 <= title_len <= 80:
            # Sweet spot for abbreviated titles
            score += 30
        score += (100 - min(title_len, 100))

        # Prefer non-versioned
        if '_v' not in filename.lower():
            score += 50

        scores.append((file_path, filename, score))

    # Sort by score (highest first)
    scores.sort(key=lambda x: x[2], reverse=True)

    return scores[0][0]  # Return best file path


def update_recommendations():
    """
    Update duplicate recommendations to prefer abbreviated titles.
    """
    print("=" * 80)
    print("UPDATING DUPLICATE RECOMMENDATIONS")
    print("=" * 80)

    # Load existing recommendations
    print(f"\nLoading: {duplicates_csv}")
    df = pd.read_csv(duplicates_csv)
    print(f"Loaded {len(df):,} duplicate pairs")

    # Group by author+year+base_title to find sets of 3+
    print("\nFinding duplicate sets (3+ files)...")

    # Extract author and year from keep_filename
    def extract_key(filename):
        parts = filename.replace('.pdf', '').split('.')
        if len(parts) < 2:
            return None

        author = parts[0]

        # Find year
        year = None
        for part in parts[1:5]:
            if part.isdigit() and len(part) == 4:
                year = part
                break

        if not year:
            return None

        return f"{author}_{year}"

    # Build file groups
    file_groups = defaultdict(set)

    for _, row in df.iterrows():
        keep_file = row['keep_file']
        remove_file = row['remove_file']

        key = extract_key(Path(keep_file).name)
        if key:
            file_groups[key].add(keep_file)
            file_groups[key].add(remove_file)

    # Find groups with 3+ files
    large_groups = {k: v for k, v in file_groups.items() if len(v) >= 3}

    print(f"Found {len(large_groups)} groups with 3+ duplicate files")

    if len(large_groups) == 0:
        print("\n✓ No multi-file groups need updating")
        return

    # Show examples
    print("\nExamples of multi-file groups:")
    for idx, (key, files) in enumerate(list(large_groups.items())[:5], 1):
        print(f"\n{idx}. {key} ({len(files)} files):")
        for f in sorted(files):
            abbrev = "✓ ABBREV" if is_abbreviated_title(Path(f).name) else ""
            print(f"   - {Path(f).name} {abbrev}")

    # For each large group, find best version to keep
    print("\n" + "=" * 80)
    print("DETERMINING BEST VERSION TO KEEP")
    print("=" * 80)

    best_versions = {}

    for key, files in large_groups.items():
        best = find_best_version_to_keep(list(files))
        best_versions[key] = best

        print(f"\n{key}:")
        print(f"  KEEP: {Path(best).name}")
        print(f"  REMOVE: {len(files) - 1} others")

    # Rebuild recommendations with updated keep files
    print("\n" + "=" * 80)
    print("REBUILDING RECOMMENDATIONS")
    print("=" * 80)

    updated_rows = []

    for key, files in file_groups.items():
        if len(files) < 2:
            continue

        # Determine which to keep
        if key in best_versions:
            keep_file = best_versions[key]
        else:
            # For pairs, use existing logic
            files_list = list(files)
            best = find_best_version_to_keep(files_list)
            keep_file = best

        # All others should be removed
        for file in files:
            if file != keep_file:
                updated_rows.append({
                    'keep_file': keep_file,
                    'remove_file': file,
                    'keep_filename': Path(keep_file).name,
                    'remove_filename': Path(file).name,
                    'reason': 'Prefer abbreviated Dropbox title',
                })

    # Create new DataFrame
    df_updated = pd.DataFrame(updated_rows)

    # Add missing columns from original
    if 'similarity' not in df_updated.columns:
        df_updated['similarity'] = 0.9  # Default
    if 'size_match' not in df_updated.columns:
        df_updated['size_match'] = False
    if 'keep_size' not in df_updated.columns:
        df_updated['keep_size'] = 0
    if 'remove_size' not in df_updated.columns:
        df_updated['remove_size'] = 0

    # Save
    output_csv = project_base / "outputs/duplicate_pdfs_to_remove_updated.csv"
    df_updated.to_csv(output_csv, index=False)

    print(f"\n✓ Updated recommendations saved to: {output_csv}")
    print(f"\nBefore: {len(df):,} duplicate pairs")
    print(f"After: {len(df_updated):,} duplicate pairs")

    # Show changes
    groups_updated = len([k for k in file_groups.keys() if k in best_versions])
    print(f"\nUpdated {groups_updated} multi-file groups to prefer abbreviated titles")

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    update_recommendations()
