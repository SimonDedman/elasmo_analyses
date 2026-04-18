#!/usr/bin/env python3
"""Interactive duplicate PDF review tool.

Opens pairs of PDFs side-by-side and records decisions.
Usage:
    python3 scripts/review_duplicates.py [--step STEP] [--start N]

Steps (in recommended order):
    1_auto_same_size  - DOI-confirmed dupes, near-identical size (auto-delete smaller)
    1_auto_diff_size  - DOI-confirmed dupes, different sizes (review needed)
    2_very_likely     - High filename similarity, no DOI to confirm
    3_likely          - Content overlap >0.5
    4_possible        - Moderate filename similarity

Decisions:
    1 = keep file_1, delete file_2
    2 = keep file_2, delete file_1
    b = keep both (not duplicates)
    s = skip (decide later)
    q = quit and save progress
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

XLSX = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
            "/outputs/pdf_library_audit.xlsx")
PROGRESS = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
                "/outputs/.duplicate_review_progress.json")
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")


def _get_path(row, n):
    """Reconstruct file path from year_N and file_N columns."""
    return PDF_BASE / str(int(row[f"year_{n}"])) / row[f"file_{n}"]


def load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text())
    return {}


def save_progress(progress: dict) -> None:
    PROGRESS.write_text(json.dumps(progress, indent=2))


def open_pdf(path: str) -> subprocess.Popen | None:
    """Open a PDF in the default viewer."""
    p = Path(path)
    if not p.exists():
        print(f"  WARNING: file not found: {p.name}")
        return None
    try:
        return subprocess.Popen(["xdg-open", str(p)],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  Could not open: {e}")
        return None


def review_step(df: pd.DataFrame, step: str, progress: dict,
                start: int = 0) -> dict:
    """Review all pairs in a given step."""
    subset = df[df["step"] == step].reset_index(drop=True)
    print(f"\n{'='*70}")
    print(f"Step: {step} — {len(subset)} pairs")
    print(f"{'='*70}")

    reviewed = 0
    for idx, row in subset.iterrows():
        if idx < start:
            continue

        pair_key = f"{str(_get_path(row, 1))}|||{str(_get_path(row, 2))}"
        if pair_key in progress:
            continue  # already reviewed

        reviewed += 1
        print(f"\n--- Pair {idx + 1}/{len(subset)} ---")
        print(f"  File 1: {row['file_1']}  ({row['size_1_kb']:.0f} KB)")
        print(f"  File 2: {row['file_2']}  ({row['size_2_kb']:.0f} KB)")
        print(f"  Confidence: {row['confidence']}  |  "
              f"Filename J: {row['filename_jaccard']}  |  "
              f"Content J: {row.get('content_jaccard', 'N/A')}  |  "
              f"DOI match: {row.get('doi_match', 'N/A')}")
        if pd.notna(row.get("doi_1")):
            print(f"  DOI 1: {row['doi_1']}")
        if pd.notna(row.get("doi_2")):
            print(f"  DOI 2: {row['doi_2']}")
        print(f"  Size ratio: {row.get('size_ratio', 'N/A')}")
        print(f"  Recommendation: keep {row.get('keep_recommendation', 'N/A')}")

        # Open both PDFs
        print("  Opening both PDFs...")
        p1 = open_pdf(str(_get_path(row, 1)))
        p2 = open_pdf(str(_get_path(row, 2)))

        while True:
            choice = input("\n  [1]=keep file1  [2]=keep file2  "
                           "[b]=both(not dupes)  [s]=skip  [q]=quit: ").strip().lower()
            if choice in ("1", "2", "b", "s", "q"):
                break
            print("  Invalid choice.")

        # Close PDFs
        for p in (p1, p2):
            if p is not None:
                p.terminate()

        if choice == "q":
            print(f"\nSaving progress ({reviewed} reviewed this session)...")
            save_progress(progress)
            return progress

        if choice == "1":
            # Delete file 2
            f2 = _get_path(row, 2)
            if f2.exists():
                f2.unlink()
                print(f"  DELETED: {row['file_2']}")
            progress[pair_key] = "keep_1"
        elif choice == "2":
            # Delete file 1
            f1 = _get_path(row, 1)
            if f1.exists():
                f1.unlink()
                print(f"  DELETED: {row['file_1']}")
            progress[pair_key] = "keep_2"
        elif choice == "b":
            progress[pair_key] = "both_keep"
        elif choice == "s":
            progress[pair_key] = "skipped"

        save_progress(progress)

    print(f"\nStep {step} complete! Reviewed {reviewed} pairs.")
    return progress


def auto_resolve(df: pd.DataFrame, step: str, progress: dict) -> dict:
    """Auto-resolve DOI-confirmed dupes with near-identical sizes."""
    subset = df[df["step"] == step].reset_index(drop=True)
    print(f"\nAuto-resolving {len(subset)} pairs (step: {step})...")

    deleted = 0
    for _, row in subset.iterrows():
        pair_key = f"{str(_get_path(row, 1))}|||{str(_get_path(row, 2))}"
        if pair_key in progress:
            continue

        p1 = _get_path(row, 1)
        p2 = _get_path(row, 2)

        if not p1.exists() or not p2.exists():
            progress[pair_key] = "file_missing"
            continue

        s1 = p1.stat().st_size
        s2 = p2.stat().st_size

        def _filename_quality(p: Path) -> int:
            """Score filename quality: prefer proper punctuation,
            hyphens, accents, apostrophes in author names, full words
            in title."""
            import re
            stem = p.stem
            score = 0
            author = stem.split(".")[0]
            # Prefer hyphens in compound author names
            if "-" in author:
                score += 3
            # Prefer apostrophes in author names (d'Onghia > dOnghia)
            if "'" in author or "\u2019" in author:
                score += 3
            # Prefer accented characters (Páez > Paez)
            if re.search(r"[àáâãäéèêëíìîïóòôõöúùûüñçÀ-ÿ]", author):
                score += 3
            # Prefer spaces or commas in title (full words vs abbreviated)
            title_part = ".".join(stem.split(".")[3:]) if len(stem.split(".")) > 3 else ""
            score += title_part.count(" ") + title_part.count(",")
            # Penalise all-lowercase/mangled titles
            if title_part == title_part.lower() and title_part:
                score -= 2
            # Prefer filenames with more distinct words (fuller titles)
            words = set(re.findall(r"[a-zA-Z]{3,}", title_part))
            score += len(words)
            return score

        q1 = _filename_quality(p1)
        q2 = _filename_quality(p2)

        if s1 != s2:
            # Different sizes: keep the larger file
            if s1 >= s2:
                p2.unlink()
                progress[pair_key] = "auto_keep_1"
            else:
                p1.unlink()
                progress[pair_key] = "auto_keep_2"
        elif q1 >= q2:
            p2.unlink()
            progress[pair_key] = "auto_keep_1"
        else:
            p1.unlink()
            progress[pair_key] = "auto_keep_2"
        deleted += 1

    save_progress(progress)
    print(f"  Auto-deleted {deleted} files.")
    return progress


def main():
    parser = argparse.ArgumentParser(description="Review duplicate PDFs interactively")
    parser.add_argument("--step", help="Which step to review (e.g., 2_very_likely)")
    parser.add_argument("--start", type=int, default=0, help="Start from pair N")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-resolve step 1_auto_same_size (keep larger)")
    parser.add_argument("--status", action="store_true", help="Show progress summary")
    args = parser.parse_args()

    df = pd.read_excel(XLSX, sheet_name="duplicates")
    progress = load_progress()

    if args.status:
        print("Review progress:")
        for step in sorted(df["step"].unique()):
            total = len(df[df["step"] == step])
            done = sum(1 for _, r in df[df["step"] == step].iterrows()
                       if f"{_get_path(r, 1)}|||{_get_path(r, 2)}" in progress)
            print(f"  {step}: {done}/{total}")
        print(f"\nDecision counts:")
        from collections import Counter
        counts = Counter(progress.values())
        for decision, n in counts.most_common():
            print(f"  {decision}: {n}")
        return

    if args.auto:
        progress = auto_resolve(df, "1_auto_same_size", progress)
        return

    if not args.step:
        print("Available steps:")
        for step in sorted(df["step"].unique()):
            n = len(df[df["step"] == step])
            done = sum(1 for _, r in df[df["step"] == step].iterrows()
                       if f"{_get_path(r, 1)}|||{_get_path(r, 2)}" in progress)
            print(f"  {step}: {n} pairs ({done} done)")
        print("\nUsage: python3 scripts/review_duplicates.py --step 2_very_likely")
        print("       python3 scripts/review_duplicates.py --auto  (auto-resolve same-size DOI matches)")
        return

    review_step(df, args.step, progress, args.start)


if __name__ == "__main__":
    main()
