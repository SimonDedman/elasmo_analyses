#!/usr/bin/env python3
"""Rule-improvement feedback loop.

Reads user notes from the duplicates tab, compares against current
auto_decision, and reports:
  - Accuracy per rule (how often 'y' / agreement vs override)
  - Pattern extraction from free-text notes (potential new rules)
  - Validation: re-run rules on notes-labelled pairs to measure change

Usage:
    python3 scripts/dupe_feedback_loop.py [--rerun]
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from dupe_rules import evaluate

PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
XLSX = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/pdf_library_audit.xlsx")


def parse_note(note: str, size_1_kb: float, size_2_kb: float) -> dict:
    """Parse free-text note into structured decision."""
    if not isinstance(note, str):
        return {"expected": None}
    nl = note.lower().strip()
    if nl == "y":
        return {"expected": "agree_with_auto"}
    if re.search(r"keep\s*#?\s*1\b|kep\s*#?\s*1|^keep1\b", nl):
        return {"expected": "keep_1"}
    if re.search(r"keep\s*#?\s*2\b|^keep2\b", nl):
        return {"expected": "keep_2"}
    m = re.match(r"(\d)\s+is\s+sm\s+of\s+(\d)", nl)
    if m:
        return {"expected": "rename_SM", "sm_side": int(m.group(1))}
    if "distinct" in nl or "different papers" in nl:
        return {"expected": "distinct"}
    if "book" in nl:
        return {"expected": "is_book"}
    if "corrupt" in nl or "doesn't open" in nl or "doesn\u2019t open" in nl or "unable to open" in nl:
        return {"expected": "keep_non_corrupt"}
    if "preprint" in nl:
        return {"expected": "preprint_detected", "keyword": "preprint"}
    if "smaller" in nl and ("identical" in nl or "both" in nl or "visually" in nl):
        return {"expected": "keep_smaller"}
    if "identical" in nl:
        return {"expected": "either"}
    return {"expected": None, "raw": note}


def validate_accuracy(df: pd.DataFrame) -> dict:
    """Compare auto_decision against user notes."""
    noted = df[df["notes"].notna()]
    stats = {"total": len(noted), "validated": 0, "correct": 0, "wrong": 0, "by_rule": defaultdict(lambda: {"correct": 0, "wrong": 0})}
    wrong_cases = []

    for _, r in noted.iterrows():
        parsed = parse_note(r["notes"], r["size_1_kb"], r["size_2_kb"])
        exp = parsed["expected"]
        if not exp:
            continue
        stats["validated"] += 1

        auto = r["auto_decision"]
        rule = ""
        if pd.notna(r["auto_reason"]):
            rule = str(r["auto_reason"]).split(":")[0]

        match = False
        if exp == "agree_with_auto":
            match = auto in ("keep_1", "keep_2")
        elif exp == "keep_1":
            match = auto == "keep_1"
        elif exp == "keep_2":
            match = auto == "keep_2"
        elif exp == "keep_smaller":
            smaller = "keep_1" if r["size_1_kb"] < r["size_2_kb"] else "keep_2"
            match = auto == smaller
        elif exp == "either":
            match = True
        elif exp == "distinct":
            match = auto == "distinct"
        elif exp == "rename_SM":
            match = auto == "rename_SM"
        elif exp == "is_book":
            match = auto == "is_book"
        elif exp == "keep_non_corrupt":
            match = auto in ("keep_1", "keep_2")  # any kept is ok
        elif exp == "preprint_detected":
            match = rule == "R3_preprint"

        if match:
            stats["correct"] += 1
            stats["by_rule"][rule]["correct"] += 1
        else:
            stats["wrong"] += 1
            stats["by_rule"][rule]["wrong"] += 1
            wrong_cases.append({
                "file_1": r["file_1"][:60],
                "file_2": r["file_2"][:60],
                "expected": exp,
                "got": auto,
                "rule": rule,
                "note": r["notes"][:100] if isinstance(r["notes"], str) else "",
            })

    stats["wrong_cases"] = wrong_cases
    return stats


def extract_patterns(df: pd.DataFrame) -> list:
    """Extract free-text patterns from notes that may suggest new rules."""
    noted = df[df["notes"].notna()]
    phrases = Counter()
    for _, r in noted.iterrows():
        note = str(r["notes"]).lower()
        # Extract notable phrases
        for phrase in re.findall(r"\b(?:"
                                  r"is preprint|is abstract|is sm|is book|is comment|"
                                  r"is corrig|is correction|is supplementary|"
                                  r"cover letter|author-produced|provisional|"
                                  r"doesn\u2019t open|unable to open|corrupted|"
                                  r"clearer text|more pages|more detail|"
                                  r"different papers|distinct|"
                                  r"in brazilian|in french|in german|in japanese|"
                                  r"no text|empty|abstract only"
                                  r")\b", note):
            phrases[phrase] += 1
    return phrases.most_common()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", action="store_true", help="Re-run rules on all manual cases")
    args = parser.parse_args()

    df = pd.read_excel(XLSX, sheet_name="duplicates")
    print(f"Total duplicate pairs: {len(df)}")
    print(f"Pairs with notes: {df['notes'].notna().sum()}")
    print()

    # Accuracy
    stats = validate_accuracy(df)
    print(f"=== Rule accuracy vs user notes ===")
    print(f"Validated: {stats['validated']}, correct: {stats['correct']}, wrong: {stats['wrong']}")
    if stats["validated"]:
        print(f"Accuracy: {stats['correct']/stats['validated']*100:.1f}%")
    print()
    print("By rule:")
    for rule, counts in sorted(stats["by_rule"].items(), key=lambda x: -x[1]["correct"] - x[1]["wrong"]):
        total = counts["correct"] + counts["wrong"]
        if total == 0:
            continue
        acc = counts["correct"] / total * 100
        print(f"  {rule or 'manual':<30} {counts['correct']:>3}/{total:<3} ({acc:.0f}%)")

    print()
    print("=== Phrase patterns in user notes ===")
    for phrase, count in extract_patterns(df):
        print(f"  {count:>3}  {phrase}")

    if stats["wrong_cases"]:
        print(f"\n=== Wrong cases ({len(stats['wrong_cases'])}) ===")
        for w in stats["wrong_cases"][:20]:
            print(f"  {w['file_1']}")
            print(f"    expected={w['expected']} got={w['got']} ({w['rule']})")
            print(f"    note: {w['note']}")

    if args.rerun:
        print("\n=== Re-running rules on all manual cases ===")
        ne_df = pd.read_excel(XLSX, sheet_name="non_english")
        lang_map = {r["filename"]: r["detected_language"] if pd.notna(r["detected_language"]) else None
                    for _, r in ne_df.iterrows()}
        manual = df[df["auto_decision"] == "manual"].reset_index(drop=True)
        print(f"Evaluating {len(manual)} manual cases...")
        # Just report potential changes (don't save by default)
        changed = 0
        for _, r in manual.iterrows():
            result = evaluate(r, PDF_BASE, lang_map)
            if result["decision"] != "manual":
                changed += 1
        print(f"Rules now resolve {changed}/{len(manual)} formerly-manual cases")


if __name__ == "__main__":
    main()
