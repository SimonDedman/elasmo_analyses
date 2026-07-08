"""Corpus-wide Fable extraction — STAGE 3: merge/post-pass (local, no Fable).

Reads the present-only cache files written by the burn (stage 2), validates and
purges malformed ones (so they re-run next shard/night), expands them to the full
166-column binary matrix + study geography, and writes a NEW parquet
(literature_review_fable.parquet) alongside a Fable-vs-rules diff report. Never
touches literature_review_enriched.parquet or the validation-loop .fable_cache.

Cache file format (per <sha>.txt):
    LIT: 12345
    COUNTRY: Australia; New Zealand
    REGION: Great Barrier Reef
    gear_longline|0.90|caught on demersal longlines
    ...

Usage:
  python3 scripts/validation/fable_corpus_merge.py [--no-purge] [--no-diff]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
CORPUS_CACHE = OUT / ".fable_corpus_cache"
FABLE_PARQUET = ROOT / "outputs/literature_review_fable.parquet"
RULES_PARQUET = ROOT / "outputs/literature_review_enriched.parquet"
DIFF_CSV = OUT / "fable_vs_rules_diff.csv"

sys.path.insert(0, str(ROOT / "scripts"))


def schema_columns():
    """Ordered list of the 166 binary schema column names."""
    from extract_schema_columns import ALL_SCHEMAS
    return [c.name for s in ALL_SCHEMAS for c in s.columns]


def parse_cache_file(path, valid_cols):
    """Parse one <sha>.txt. Returns dict(lit_id, present:set, country, region,
    confidences:dict) or None if malformed (no LIT line)."""
    lit_id = country = region = None
    present, conf = set(), {}
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("LIT:"):
            lit_id = line.split(":", 1)[1].strip()
        elif line.startswith("COUNTRY:"):
            country = line.split(":", 1)[1].strip()
        elif line.startswith("REGION:"):
            region = line.split(":", 1)[1].strip()
        elif "|" in line:
            parts = line.split("|")
            name = parts[0].strip()
            if name in valid_cols:
                present.add(name)
                try:
                    conf[name] = float(parts[1]) if len(parts) > 1 else None
                except ValueError:
                    conf[name] = None
    if not lit_id:
        return None
    return {"lit_id": lit_id, "present": present,
            "country": country or "", "region": region or "", "conf": conf}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-purge", action="store_true",
                    help="do not delete malformed cache files")
    ap.add_argument("--no-diff", action="store_true",
                    help="skip the Fable-vs-rules diff report")
    args = ap.parse_args()

    cols = schema_columns()
    valid = set(cols)
    files = sorted(CORPUS_CACHE.glob("*.txt"))
    print(f"Cache files: {len(files)}")

    rows, purged = [], 0
    for f in files:
        rec = parse_cache_file(f, valid)
        if rec is None:
            purged += 1
            if not args.no_purge:
                f.unlink()
            print(f"  malformed (no LIT), {'purged' if not args.no_purge else 'kept'}: {f.name}",
                  file=sys.stderr)
            continue
        rows.append(rec)

    if not rows:
        print("No valid cache rows — nothing to merge.")
        return

    # De-dup: same lit_id from two SHAs (re-scan) — keep the one with more hits.
    best = {}
    for r in rows:
        prev = best.get(r["lit_id"])
        if prev is None or len(r["present"]) > len(prev["present"]):
            best[r["lit_id"]] = r
    rows = list(best.values())

    # Expand to the wide binary matrix.
    data = []
    for r in rows:
        row = {"literature_id": str(int(float(r["lit_id"]))),
               "study_country": r["country"], "study_region": r["region"],
               "fable_extracted": 1}
        for c in cols:
            row[c] = 1 if c in r["present"] else 0
        data.append(row)
    df = pd.DataFrame(data, columns=["literature_id", "study_country",
                                     "study_region", "fable_extracted"] + cols)
    df.to_parquet(FABLE_PARQUET)
    print(f"\nWrote {FABLE_PARQUET}")
    print(f"  papers        : {len(df)}")
    print(f"  malformed     : {purged} ({'purged->will re-run' if not args.no_purge else 'kept'})")
    print(f"  with country  : {(df['study_country'].str.len() > 0).sum()}")

    if args.no_diff:
        return

    # Fable-vs-rules per-column agreement.
    try:
        rules = pd.read_parquet(RULES_PARQUET, columns=["literature_id"] + cols)
    except Exception as e:
        print(f"(diff skipped: could not read rules parquet: {e})", file=sys.stderr)
        return
    rules["literature_id"] = rules["literature_id"].apply(lambda v: str(int(float(v))))
    rules = rules.drop_duplicates("literature_id", keep="first")
    m = df[["literature_id"] + cols].merge(rules, on="literature_id",
                                           suffixes=("_fable", "_rules"))
    print(f"  diff overlap  : {len(m)} papers in both")
    diff = []
    for c in cols:
        fb, rl = m[f"{c}_fable"], m[f"{c}_rules"]
        agree = int((fb == rl).sum())
        diff.append({"column": c, "n": len(m), "agree": agree,
                     "agreement_rate": round(agree / len(m), 4) if len(m) else 0.0,
                     "fable_only": int(((fb == 1) & (rl == 0)).sum()),
                     "rules_only": int(((fb == 0) & (rl == 1)).sum())})
    pd.DataFrame(diff).sort_values("agreement_rate").to_csv(DIFF_CSV, index=False)
    print(f"  wrote diff    : {DIFF_CSV}")


if __name__ == "__main__":
    main()
