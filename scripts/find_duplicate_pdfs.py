#!/usr/bin/env python3
"""
Find duplicate PDFs in the SharkPapers collection.

Identifies duplicates based on:
1. Same author + year + similar title (fuzzy match)
2. Same file size and MD5 hash
3. Papers downloaded both from Dropbox and Sci-Hub

Strategy:
- Prefer Dropbox naming convention (abbreviated titles)
- Remove Sci-Hub duplicates (full title format)
"""

import hashlib
from pathlib import Path
from collections import defaultdict
import re
from difflib import SequenceMatcher

# Paths
pdf_base = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
project_base = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")


def get_file_hash(file_path, block_size=65536):
    """Calculate MD5 hash of file."""
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None


def parse_filename(filename):
    """
    Parse PDF filename into components.

    Expected formats:
    - Author.etal.YYYY.Abbreviated title.pdf (Dropbox)
    - Author.etal.YYYY.Full Long Title Words.pdf (Sci-Hub)
    - Author.YYYY.Title.pdf

    Returns:
        dict with author, year, title
    """
    # Remove .pdf extension
    name = filename.replace('.pdf', '')

    # Split by dots
    parts = name.split('.')

    if len(parts) < 3:
        return None

    # Extract author (first part)
    author = parts[0]

    # Extract year (should be YYYY format)
    year = None
    for part in parts[1:5]:  # Check first few parts
        if re.match(r'^(19|20)\d{2}$', part):
            year = part
            break

    if not year:
        return None

    # Extract title (everything after year)
    year_idx = parts.index(year)
    title_parts = parts[year_idx + 1:]
    title = ' '.join(title_parts)

    return {
        'author': author.lower(),
        'year': year,
        'title': title.lower(),
        'filename': filename
    }


def title_similarity(title1, title2):
    """Calculate similarity ratio between two titles (0-1)."""
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def is_abbreviated_title(title):
    """
    Determine if title looks abbreviated (Dropbox style).

    Abbreviated titles:
    - Shorter (< 80 chars)
    - Use abbreviations like "etal", "jName"
    - More concise wording
    """
    # Count words
    words = title.split()

    # Check for abbreviation indicators
    abbrev_indicators = ['etal', 'j ', ' j', 'spp', 'var', 'abund']

    has_abbrev = any(indicator in title.lower() for indicator in abbrev_indicators)

    # Dropbox style is typically < 80 chars
    is_short = len(title) < 80

    # Full Sci-Hub titles often have "of", "the", "and", etc.
    common_words = sum(1 for w in words if w.lower() in ['of', 'the', 'and', 'in', 'a', 'an', 'for', 'with'])
    has_many_common = common_words >= 3

    # Abbreviated if short + has abbreviations, or very short
    if is_short and has_abbrev:
        return True
    elif len(title) < 50:
        return True
    elif len(title) > 100 and has_many_common:
        return False
    else:
        return is_short


def find_duplicates_by_hash():
    """Find exact duplicates by MD5 hash."""
    print("=" * 80)
    print("FINDING EXACT DUPLICATES (by MD5 hash)")
    print("=" * 80)

    hash_map = defaultdict(list)

    # Find all PDFs
    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    print(f"\nAnalyzing {len(all_pdfs):,} PDFs...")

    # Calculate hashes
    for pdf_path in all_pdfs:
        file_hash = get_file_hash(pdf_path)
        if file_hash:
            hash_map[file_hash].append(pdf_path)

    # Find duplicates
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

    print(f"\nFound {len(duplicates)} sets of exact duplicates")

    return duplicates


def find_duplicates_by_metadata():
    """Find likely duplicates by author/year/similar title."""
    print("\n" + "=" * 80)
    print("FINDING LIKELY DUPLICATES (by author/year/title)")
    print("=" * 80)

    # Parse all filenames
    all_pdfs = list(pdf_base.glob("*/*.pdf"))
    parsed = []

    for pdf_path in all_pdfs:
        info = parse_filename(pdf_path.name)
        if info:
            info['path'] = pdf_path
            info['size'] = pdf_path.stat().st_size
            parsed.append(info)

    print(f"\nSuccessfully parsed {len(parsed):,} filenames")

    # Group by author + year
    groups = defaultdict(list)
    for item in parsed:
        key = f"{item['author']}_{item['year']}"
        groups[key].append(item)

    # Find duplicates within each group
    likely_duplicates = []

    for key, items in groups.items():
        if len(items) < 2:
            continue

        # Compare all pairs
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item1 = items[i]
                item2 = items[j]

                # Calculate title similarity
                similarity = title_similarity(item1['title'], item2['title'])

                # Consider duplicates if:
                # - High title similarity (> 0.6) OR
                # - Exact same file size
                if similarity > 0.6 or item1['size'] == item2['size']:
                    likely_duplicates.append({
                        'file1': item1,
                        'file2': item2,
                        'similarity': similarity,
                        'size_match': item1['size'] == item2['size']
                    })

    print(f"\nFound {len(likely_duplicates)} likely duplicate pairs")

    return likely_duplicates


def recommend_removal(duplicates):
    """
    Recommend which duplicates to remove.

    Strategy:
    - Keep Dropbox naming (abbreviated titles)
    - Remove Sci-Hub downloads (full titles)
    """
    print("\n" + "=" * 80)
    print("DUPLICATE REMOVAL RECOMMENDATIONS")
    print("=" * 80)

    recommendations = []

    for dup in duplicates:
        file1 = dup['file1']
        file2 = dup['file2']

        # Determine which is abbreviated (Dropbox) vs full (Sci-Hub)
        title1_abbrev = is_abbreviated_title(file1['title'])
        title2_abbrev = is_abbreviated_title(file2['title'])

        # Decide which to keep
        if title1_abbrev and not title2_abbrev:
            keep = file1
            remove = file2
            reason = "Keep Dropbox naming (abbreviated)"
        elif title2_abbrev and not title1_abbrev:
            keep = file2
            remove = file1
            reason = "Keep Dropbox naming (abbreviated)"
        elif len(file1['title']) < len(file2['title']):
            keep = file1
            remove = file2
            reason = "Keep shorter title (likely abbreviated)"
        else:
            keep = file2
            remove = file1
            reason = "Keep shorter title (likely abbreviated)"

        recommendations.append({
            'keep': keep,
            'remove': remove,
            'reason': reason,
            'similarity': dup['similarity']
        })

    return recommendations


def main():
    print("=" * 80)
    print("PDF DUPLICATE FINDER")
    print("=" * 80)

    # Find exact duplicates by hash
    hash_duplicates = find_duplicates_by_hash()

    # Show exact duplicates
    if hash_duplicates:
        print("\n" + "=" * 80)
        print("EXACT DUPLICATES (identical files)")
        print("=" * 80)

        for idx, (file_hash, files) in enumerate(hash_duplicates.items(), 1):
            print(f"\nSet {idx}: {len(files)} copies")
            for f in files:
                print(f"  - {f.relative_to(pdf_base)}")

    # Find likely duplicates by metadata
    metadata_duplicates = find_duplicates_by_metadata()

    # Generate recommendations
    if metadata_duplicates:
        recommendations = recommend_removal(metadata_duplicates)

        print(f"\nShowing top 30 duplicate pairs:")
        print()

        for idx, rec in enumerate(recommendations[:30], 1):
            keep = rec['keep']
            remove = rec['remove']

            print(f"{idx}. KEEP:   {keep['filename']}")
            print(f"   REMOVE: {remove['filename']}")
            print(f"   Reason: {rec['reason']} (similarity: {rec['similarity']:.2f})")
            print(f"   Sizes:  {keep['size']:,} vs {remove['size']:,} bytes")
            print()

        # Save recommendations to CSV
        import pandas as pd

        df_data = []
        for rec in recommendations:
            df_data.append({
                'keep_file': str(rec['keep']['path']),
                'remove_file': str(rec['remove']['path']),
                'keep_filename': rec['keep']['filename'],
                'remove_filename': rec['remove']['filename'],
                'similarity': rec['similarity'],
                'reason': rec['reason'],
                'size_match': rec['keep']['size'] == rec['remove']['size'],
                'keep_size': rec['keep']['size'],
                'remove_size': rec['remove']['size']
            })

        df = pd.DataFrame(df_data)
        output_csv = project_base / "outputs/duplicate_pdfs_to_remove.csv"
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)

        print("=" * 80)
        print(f"SUMMARY")
        print("=" * 80)
        print(f"\nTotal duplicate pairs found: {len(recommendations)}")
        print(f"Recommendations saved to: {output_csv}")
        print()
        print("Next steps:")
        print("  1. Review: cat outputs/duplicate_pdfs_to_remove.csv")
        print("  2. Remove duplicates: Use remove_duplicate_pdfs.py script")

    else:
        print("\n✓ No duplicates found!")


if __name__ == "__main__":
    main()
