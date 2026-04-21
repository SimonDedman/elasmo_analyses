#!/usr/bin/env python3
"""Compare extraction runs by run-id.

Each extraction run writes a snapshot to `outputs/extraction_runs/<run_id>/`:
  - run_summary.json            (committed)
  - rules_snapshot.json         (committed)
  - binary_classifications.parquet  (gitignored)

This script diffs two snapshots and reports:
  1. Per-column firing-count delta (which rules changed behaviour most)
  2. Per-paper sample for the top-changed columns (which specific papers
     gained or lost a positive classification — for spot-checking)
  3. Per-schema summary of papers-with-any-match

Usage:
    python scripts/diff_extraction_runs.py --list
    python scripts/diff_extraction_runs.py --latest             # diff last 2
    python scripts/diff_extraction_runs.py <run_a> <run_b>
    python scripts/diff_extraction_runs.py <run_a> <run_b> --top 30 --samples 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_BASE = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_BASE / "outputs" / "extraction_runs"


def list_runs() -> list[str]:
    if not RUNS_DIR.exists():
        return []
    return sorted(p.name for p in RUNS_DIR.iterdir() if p.is_dir())


def load_run(run_id: str) -> tuple[dict, pd.DataFrame | None]:
    rd = RUNS_DIR / run_id
    summary = json.loads((rd / "run_summary.json").read_text())
    bcl_path = rd / "binary_classifications.parquet"
    bcl = pd.read_parquet(bcl_path) if bcl_path.exists() else None
    return summary, bcl


def cmd_list() -> None:
    runs = list_runs()
    if not runs:
        print(f"No runs found in {RUNS_DIR}")
        return
    print(f"{'run_id':70s}  {'papers':>8s}  rules_fp")
    for r in runs:
        try:
            s = json.loads((RUNS_DIR / r / "run_summary.json").read_text())
            n = s.get("n_papers_in_parquet", "?")
            fp = s.get("rules_fingerprint", "?")
            print(f"{r:70s}  {n:>8}  {fp}")
        except Exception as exc:
            print(f"{r:70s}  (load error: {exc})")


def diff(run_a: str, run_b: str, top: int, samples: int) -> None:
    print(f"\nComparing {run_a} → {run_b}\n")

    summary_a, bcl_a = load_run(run_a)
    summary_b, bcl_b = load_run(run_b)

    print(f"  A: {summary_a['timestamp_utc']}  rules={summary_a['rules_fingerprint']}  papers={summary_a['n_papers_in_parquet']}")
    print(f"  B: {summary_b['timestamp_utc']}  rules={summary_b['rules_fingerprint']}  papers={summary_b['n_papers_in_parquet']}")

    a_counts = summary_a.get("per_column_firing_counts", {})
    b_counts = summary_b.get("per_column_firing_counts", {})

    deltas = []
    for col in sorted(set(a_counts) | set(b_counts)):
        ac, bc = a_counts.get(col, 0), b_counts.get(col, 0)
        if ac == bc:
            continue
        delta = bc - ac
        pct = (delta / ac * 100) if ac else float("inf")
        deltas.append((col, ac, bc, delta, pct))

    deltas.sort(key=lambda r: abs(r[3]), reverse=True)

    print(f"\n=== Per-column firing-count delta (top {top}) ===")
    print(f"{'column':40s}  {'A':>7s} → {'B':>7s}  {'Δ':>7s}  Δ%")
    for col, ac, bc, d, pct in deltas[:top]:
        pct_str = f"{pct:+6.1f}%" if pct != float("inf") else "  new"
        print(f"{col:40s}  {ac:>7d} → {bc:>7d}  {d:+7d}  {pct_str}")

    if bcl_a is None or bcl_b is None:
        print("\n(Per-paper snapshots not available — skipping per-paper sampling.)")
    else:
        print(f"\n=== Sample papers per top change column ({samples} each) ===")
        bcl_a = bcl_a.set_index("literature_id")
        bcl_b = bcl_b.set_index("literature_id")
        common = bcl_a.index.intersection(bcl_b.index)
        for col, ac, bc, d, pct in deltas[:top]:
            if col not in bcl_a.columns or col not in bcl_b.columns:
                continue
            mask_gained = (bcl_a.loc[common, col] == 0) & (bcl_b.loc[common, col] == 1)
            mask_lost   = (bcl_a.loc[common, col] == 1) & (bcl_b.loc[common, col] == 0)
            n_gain = int(mask_gained.sum())
            n_lost = int(mask_lost.sum())
            if n_gain == 0 and n_lost == 0:
                continue
            print(f"\n  {col}: +{n_gain} gained, -{n_lost} lost")
            if n_gain > 0:
                print(f"    gained sample: {list(common[mask_gained][:samples])}")
            if n_lost > 0:
                print(f"    lost sample:   {list(common[mask_lost][:samples])}")

    print("\n=== Per-schema summary (papers-with-any-match) ===")
    sa = summary_a.get("per_schema_summary", {})
    sb = summary_b.get("per_schema_summary", {})
    print(f"{'prefix':10s}  {'A':>8s}  {'B':>8s}  {'Δ':>7s}")
    for prefix in sorted(set(sa) | set(sb)):
        am = sa.get(prefix, {}).get("papers_with_any_match", 0)
        bm = sb.get(prefix, {}).get("papers_with_any_match", 0)
        print(f"{prefix:10s}  {am:>8d}  {bm:>8d}  {bm-am:+7d}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_a", nargs="?")
    ap.add_argument("run_b", nargs="?")
    ap.add_argument("--list", action="store_true", help="list available run IDs")
    ap.add_argument("--latest", action="store_true", help="diff the two most recent runs")
    ap.add_argument("--top", type=int, default=20, help="show top N changed columns (default 20)")
    ap.add_argument("--samples", type=int, default=5, help="paper samples per change column (default 5)")
    args = ap.parse_args()

    if args.list:
        cmd_list()
        return

    runs = list_runs()
    if args.latest:
        if len(runs) < 2:
            print(f"Need ≥2 runs to diff (found {len(runs)}).", file=sys.stderr)
            sys.exit(1)
        run_a, run_b = runs[-2], runs[-1]
    elif args.run_a and args.run_b:
        run_a, run_b = args.run_a, args.run_b
        if run_a not in runs or run_b not in runs:
            print(f"Unknown run id(s). Available:", file=sys.stderr)
            for r in runs: print(f"  {r}", file=sys.stderr)
            sys.exit(1)
    else:
        ap.print_help()
        return

    diff(run_a, run_b, args.top, args.samples)


if __name__ == "__main__":
    main()
