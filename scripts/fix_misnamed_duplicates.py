#!/usr/bin/env python3
"""
Fix filenames for papers that were kept with wrong names during duplicate removal.

The duplicate removal used the old CSV which had reversed recommendations,
resulting in some papers keeping verbose names instead of abbreviated ones.

This script renames them to the correct abbreviated Dropbox-style names.
"""

import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime

project_base = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
old_csv = project_base / "outputs/duplicate_pdfs_to_remove.csv"
updated_csv = project_base / "outputs/duplicate_pdfs_to_remove_updated.csv"
rename_log = project_base / "logs/duplicate_renames.log"


def find_files_to_rename():
    """
    Compare old and updated CSVs to find files that need renaming.

    Returns:
        list: Dictionaries with current_path and target_path
    """
    print("=" * 80)
    print("FINDING MISNAMED FILES")
    print("=" * 80)

    # Load both CSVs
    print(f"\nLoading old CSV: {old_csv}")
    df_old = pd.read_csv(old_csv)
    print(f"  Loaded {len(df_old):,} entries")

    print(f"\nLoading updated CSV: {updated_csv}")
    df_updated = pd.read_csv(updated_csv)
    print(f"  Loaded {len(df_updated):,} entries")

    # Build lookup of what should be kept (from updated CSV)
    # Key: (year_folder, any_filename) -> correct_keep_file
    should_keep = {}

    for _, row in df_updated.iterrows():
        keep_path = Path(row['keep_file'])
        remove_path = Path(row['remove_file'])

        year_folder = keep_path.parent

        # Map both filenames to the correct keep file
        should_keep[(str(year_folder), keep_path.name)] = keep_path
        should_keep[(str(year_folder), remove_path.name)] = keep_path

    print(f"\nBuilt lookup table with {len(should_keep):,} entries")

    # Find files that exist but have wrong names
    renames = []

    for _, row in df_old.iterrows():
        old_keep = Path(row['keep_file'])
        old_remove = Path(row['remove_file'])

        year_folder = str(old_keep.parent)

        # Check what the updated CSV says should be kept
        lookup_key = (year_folder, old_keep.name)

        if lookup_key in should_keep:
            correct_file = should_keep[lookup_key]

            # If current file exists but is not the correct name
            if old_keep.exists() and old_keep.name != correct_file.name:
                # Verify the correct file doesn't already exist
                if not correct_file.exists():
                    renames.append({
                        'current_path': old_keep,
                        'target_path': correct_file,
                        'current_name': old_keep.name,
                        'target_name': correct_file.name,
                        'year': old_keep.parent.name
                    })

    # Remove duplicates (same rename might appear multiple times)
    unique_renames = []
    seen = set()

    for r in renames:
        key = (str(r['current_path']), str(r['target_path']))
        if key not in seen:
            seen.add(key)
            unique_renames.append(r)

    print(f"\nFound {len(unique_renames)} files to rename")

    return unique_renames


def show_samples(renames, count=20):
    """Show sample of renames."""
    print("\n" + "=" * 80)
    print(f"SAMPLE RENAMES (showing {min(count, len(renames))} of {len(renames)})")
    print("=" * 80)

    for idx, r in enumerate(renames[:count], 1):
        print(f"\n{idx}. Year: {r['year']}")
        print(f"   Current:  {r['current_name']}")
        print(f"   Rename to: {r['target_name']}")

    if len(renames) > count:
        print(f"\n   ... and {len(renames) - count} more")


def rename_files(renames, dry_run=True):
    """
    Rename files.

    Args:
        renames: List of rename dictionaries
        dry_run: If True, don't actually rename (just log)
    """
    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN - NO FILES WILL BE RENAMED")
    else:
        print("RENAMING FILES")
    print("=" * 80)

    renamed_count = 0
    failed_count = 0
    skipped_count = 0

    log_entries = []

    for r in renames:
        current_path = r['current_path']
        target_path = r['target_path']

        # Safety checks
        if not current_path.exists():
            print(f"⚠️  Skip (source missing): {current_path.name}")
            skipped_count += 1

            log_entries.append({
                'timestamp': datetime.now().isoformat(),
                'status': 'SKIPPED_MISSING',
                'current_path': str(current_path),
                'target_path': str(target_path),
                'reason': 'Source file does not exist'
            })
            continue

        if target_path.exists():
            print(f"⚠️  Skip (target exists): {target_path.name}")
            skipped_count += 1

            log_entries.append({
                'timestamp': datetime.now().isoformat(),
                'status': 'SKIPPED_EXISTS',
                'current_path': str(current_path),
                'target_path': str(target_path),
                'reason': 'Target file already exists'
            })
            continue

        # Rename
        if dry_run:
            log_entries.append({
                'timestamp': datetime.now().isoformat(),
                'status': 'DRY_RUN',
                'current_path': str(current_path),
                'target_path': str(target_path),
                'reason': 'Would rename'
            })
            renamed_count += 1
        else:
            try:
                current_path.rename(target_path)
                renamed_count += 1

                log_entries.append({
                    'timestamp': datetime.now().isoformat(),
                    'status': 'RENAMED',
                    'current_path': str(current_path),
                    'target_path': str(target_path),
                    'reason': 'Successfully renamed'
                })

                if renamed_count % 20 == 0:
                    print(f"  Progress: {renamed_count} / {len(renames)} renamed")

            except Exception as e:
                failed_count += 1
                print(f"❌ Failed: {current_path.name}")
                print(f"   Error: {e}")

                log_entries.append({
                    'timestamp': datetime.now().isoformat(),
                    'status': 'FAILED',
                    'current_path': str(current_path),
                    'target_path': str(target_path),
                    'reason': str(e)
                })

    # Save log
    if log_entries:
        rename_log.parent.mkdir(parents=True, exist_ok=True)
        log_df = pd.DataFrame(log_entries)

        if rename_log.exists():
            log_df.to_csv(rename_log, mode='a', header=False, index=False)
        else:
            log_df.to_csv(rename_log, index=False)

        print(f"\n✓ Log saved to: {rename_log}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if dry_run:
        print(f"\n✓ DRY RUN complete")
        print(f"  Would rename: {renamed_count} files")
        print(f"  Would skip: {skipped_count} files")
    else:
        print(f"\n✓ Rename complete")
        print(f"  Renamed: {renamed_count} files")
        print(f"  Failed: {failed_count} files")
        print(f"  Skipped: {skipped_count} files")


def main():
    parser = argparse.ArgumentParser(
        description='Fix filenames for papers kept with wrong names',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually rename files (default is dry-run)'
    )

    args = parser.parse_args()

    # Find files to rename
    renames = find_files_to_rename()

    if len(renames) == 0:
        print("\n✓ No files need renaming!")
        return

    # Show samples
    show_samples(renames, count=20)

    # Confirmation if live mode
    if not args.live:
        print("\n" + "=" * 80)
        print("DRY RUN MODE")
        print("=" * 80)
        print("\nTo actually rename files, run with --live flag:")
        print("  ./venv/bin/python scripts/fix_misnamed_duplicates.py --live")
    else:
        print("\n" + "=" * 80)
        print("⚠️  WARNING: About to rename files!")
        print("=" * 80)
        print(f"\nFiles to rename: {len(renames)}")
        print("\nThis will change filenames to abbreviated Dropbox-style names.")
        print()

        response = input("Type 'RENAME' to confirm: ")

        if response != 'RENAME':
            print("\n❌ Cancelled - no files renamed")
            return

        print("\n🔄 Proceeding with renames...")

    # Rename files
    rename_files(renames, dry_run=not args.live)

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
