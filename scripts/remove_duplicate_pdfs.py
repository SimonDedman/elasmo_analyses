#!/usr/bin/env python3
"""
Remove duplicate PDFs based on recommendations from find_duplicate_pdfs.py

Safety features:
- Dry-run mode by default
- Creates backup list of removed files
- Verifies file exists before removal
- Logs all removals
"""

import pandas as pd
from pathlib import Path
import shutil
from datetime import datetime
import argparse

# Paths
project_base = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
duplicates_csv = project_base / "outputs/duplicate_pdfs_to_remove.csv"
removal_log = project_base / "logs/duplicate_pdfs_removed.log"
backup_dir = project_base / "backups/removed_duplicates"


def remove_duplicates(dry_run=True):
    """
    Remove duplicate PDFs based on CSV recommendations.

    Args:
        dry_run: If True, only show what would be removed (don't actually remove)
    """
    print("=" * 80)
    print("DUPLICATE PDF REMOVER")
    print("=" * 80)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be deleted")
    else:
        print("\n🔥 LIVE MODE - Files will be permanently deleted!")
        print("   (After confirmation)")

    # Load duplicates CSV
    print(f"\nLoading recommendations from: {duplicates_csv}")
    df = pd.read_csv(duplicates_csv)
    print(f"Found {len(df):,} duplicate pairs to process")

    # Statistics
    total_size_to_free = 0
    files_to_remove = []

    print("\nAnalyzing duplicates...")

    for idx, row in df.iterrows():
        remove_path = Path(row['remove_file'])
        keep_path = Path(row['keep_file'])

        # Verify both files exist
        if not remove_path.exists():
            print(f"⚠️  Skip (file not found): {remove_path.name}")
            continue

        if not keep_path.exists():
            print(f"⚠️  Skip (keep file not found): {keep_path.name}")
            continue

        # Add to removal list
        file_size = remove_path.stat().st_size
        total_size_to_free += file_size

        files_to_remove.append({
            'path': remove_path,
            'keep_path': keep_path,
            'size': file_size,
            'reason': row['reason'],
            'similarity': row['similarity']
        })

    print(f"\n✓ Verified {len(files_to_remove):,} files to remove")
    print(f"  Total disk space to free: {total_size_to_free / (1024**3):.2f} GB")

    # Show sample
    print("\nSample of files to remove (first 20):")
    for item in files_to_remove[:20]:
        print(f"  - {item['path'].name}")
        print(f"    Reason: {item['reason']} (similarity: {item['similarity']:.2f})")
        print(f"    Keep: {item['keep_path'].name}")
        print()

    if len(files_to_remove) > 20:
        print(f"  ... and {len(files_to_remove) - 20} more")

    # Confirmation if not dry-run
    if not dry_run:
        print("\n" + "=" * 80)
        print("⚠️  WARNING: About to delete files!")
        print("=" * 80)
        print(f"\nFiles to delete: {len(files_to_remove):,}")
        print(f"Disk space to free: {total_size_to_free / (1024**3):.2f} GB")
        print()

        response = input("Type 'DELETE' to confirm removal: ")

        if response != 'DELETE':
            print("\n❌ Cancelled - no files were deleted")
            return

        print("\n🔥 Proceeding with deletion...")

    # Remove duplicates
    removed_count = 0
    failed_count = 0

    # Prepare log
    removal_log.parent.mkdir(parents=True, exist_ok=True)
    log_entries = []

    for item in files_to_remove:
        remove_path = item['path']

        if dry_run:
            # Just log what would be removed
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'DRY_RUN',
                'removed_file': str(remove_path),
                'kept_file': str(item['keep_path']),
                'size_freed': item['size'],
                'reason': item['reason'],
                'similarity': item['similarity']
            }
            log_entries.append(log_entry)

        else:
            # Actually remove file
            try:
                remove_path.unlink()
                removed_count += 1

                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'REMOVED',
                    'removed_file': str(remove_path),
                    'kept_file': str(item['keep_path']),
                    'size_freed': item['size'],
                    'reason': item['reason'],
                    'similarity': item['similarity']
                }
                log_entries.append(log_entry)

                if removed_count % 100 == 0:
                    print(f"  Progress: {removed_count:,} / {len(files_to_remove):,} removed")

            except Exception as e:
                failed_count += 1
                print(f"❌ Failed to remove {remove_path.name}: {e}")

                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'FAILED',
                    'removed_file': str(remove_path),
                    'kept_file': str(item['keep_path']),
                    'size_freed': 0,
                    'reason': str(e),
                    'similarity': item['similarity']
                }
                log_entries.append(log_entry)

    # Save log
    log_df = pd.DataFrame(log_entries)

    if removal_log.exists():
        # Append to existing log
        log_df.to_csv(removal_log, mode='a', header=False, index=False)
    else:
        # Create new log
        log_df.to_csv(removal_log, index=False)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if dry_run:
        print(f"\n✓ DRY RUN complete")
        print(f"  Would remove: {len(files_to_remove):,} duplicate files")
        print(f"  Would free: {total_size_to_free / (1024**3):.2f} GB")
        print(f"\nLog saved to: {removal_log}")
        print("\nTo actually remove files, run with --live flag:")
        print("  ./venv/bin/python scripts/remove_duplicate_pdfs.py --live")
    else:
        print(f"\n✓ Removal complete")
        print(f"  Removed: {removed_count:,} files")
        print(f"  Failed: {failed_count:,} files")
        print(f"  Freed: {total_size_to_free / (1024**3):.2f} GB")
        print(f"\nLog saved to: {removal_log}")


def main():
    parser = argparse.ArgumentParser(
        description='Remove duplicate PDFs based on recommendations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually remove files (default is dry-run)'
    )

    args = parser.parse_args()

    # Run removal (dry-run by default)
    remove_duplicates(dry_run=not args.live)


if __name__ == "__main__":
    main()
