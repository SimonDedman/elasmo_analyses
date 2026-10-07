"""Corpus-wide text cache + Fable worklist — STAGE 1: pre-pass (local, no Fable).

Materialises one body-text file per literature_id from the PDF the id map
assigns to it, and builds the worklist the Fable burn (stage 2,
fable_corpus_burn.mjs) consumes. The same text cache is what the RAG index
(scripts/rag/build_from_cache.py) is built from.

PDF resolution (changed 2026-10-07): a record's PDF is whatever
outputs/pdf_id_map.csv says, and nothing else. The July 2026 version resolved
PDFs with the surname+year matcher, which gave one PDF to two records 2,670
times and left 2,948 mapped records with no text. A record absent from the map
has no text here, by design: "no entry" means nothing ties a file to it.

Outputs (all under outputs/validation/, git-ignored):
  .fable_texts/<lit_id>.txt        body text (<=120k chars), one per mapped record
  fable_texts_manifest.csv         lit_id, sha, pdf, size, mtime, extracted_at
                                   (which PDF each text came from; reused to skip
                                   re-hashing unchanged files on the next run)
  .fable_texts_unbacked/           texts whose record the map no longer backs,
                                   moved here by --purge-unbacked, never deleted
  fable_texts_unbacked.csv         why each quarantined text was moved
  fable_corpus_worklist.json       [{lit_id, text_path, sha}, ...] still to burn
  fable_corpus_columns.json        [{name, description}, ...] for the 166 cols
  fable_prepass_coverage.json      in scope / attempted / succeeded / failed / skipped

Usage:
  python3 scripts/validation/fable_corpus_prepass.py [--purge-unbacked] [--workers 8]
                                                     [--limit N] [--quiet]
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
TEXTS = OUT / ".fable_texts"
UNBACKED_DIR = OUT / ".fable_texts_unbacked"
UNBACKED_CSV = OUT / "fable_texts_unbacked.csv"
MANIFEST = OUT / "fable_texts_manifest.csv"
CORPUS_CACHE = OUT / ".fable_corpus_cache"
WORKLIST = OUT / "fable_corpus_worklist.json"
COLUMNS_JSON = OUT / "fable_corpus_columns.json"
COVERAGE = OUT / "fable_prepass_coverage.json"
MAX_CHARS = 120_000  # matches the validated fable_extract prompt window
MANIFEST_COLS = ["lit_id", "sha", "pdf", "size", "mtime", "extracted_at"]

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "validation"))


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest() -> dict[str, dict]:
    """lit_id -> manifest row. Seeded from the July worklists (which recorded
    the sha each text was extracted from) when no manifest exists yet."""
    rows: dict[str, dict] = {}
    if MANIFEST.exists():
        with open(MANIFEST, newline="") as fh:
            for r in csv.DictReader(fh):
                rows[r["lit_id"]] = r
        return rows
    for wl in (OUT / "fable_corpus_worklist_prev.json", WORKLIST):
        if wl.exists():
            try:
                for e in json.loads(wl.read_text()):
                    rows.setdefault(str(e["lit_id"]), {
                        "lit_id": str(e["lit_id"]), "sha": e.get("sha", ""),
                        "pdf": "", "size": "", "mtime": "", "extracted_at": "2026-07-07"})
            except (ValueError, KeyError):
                continue
    return rows


def write_manifest(rows: dict[str, dict]) -> None:
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_COLS, extrasaction="ignore")
        w.writeheader()
        for lid in sorted(rows, key=lambda x: (len(x), x)):
            w.writerow({c: rows[lid].get(c, "") for c in MANIFEST_COLS})
    os.replace(tmp, MANIFEST)


def _years_by_lid() -> dict[str, int]:
    """literature_id -> publication year from the enriched parquet (worklist order)."""
    try:
        import pandas as pd
        df = pd.read_parquet(ROOT / "outputs/literature_review_enriched.parquet",
                             columns=["literature_id", "year"])
    except Exception:  # noqa: BLE001 (no parquet: fall back to id order)
        return {}
    out: dict[str, int] = {}
    for lid, yr in zip(df["literature_id"], df["year"]):
        try:
            out.setdefault(str(lid).split(".")[0], int(float(yr)))
        except (TypeError, ValueError):
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="cap records processed (smoke test)")
    ap.add_argument("--workers", type=int, default=8, help="parallel pdftotext workers")
    ap.add_argument("--purge-unbacked", action="store_true",
                    help="move texts whose record the id map does not back into "
                         ".fable_texts_unbacked/ (reversible; nothing is deleted)")
    ap.add_argument("--worklist-to-next", action="store_true",
                    help="write the Fable worklist to fable_corpus_worklist.next.json instead of "
                         "replacing fable_corpus_worklist.json (used by scripts/rag/sync_index.sh, so "
                         "an index sync never shifts the indices a running burn reads by position)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.limit and args.purge_unbacked:
        sys.exit("--purge-unbacked needs a full run: with --limit every unvisited text looks unbacked")

    from extract_schema_columns import extract_text_from_pdf, load_pdf_id_map
    import fable_extract

    TEXTS.mkdir(parents=True, exist_ok=True)
    CORPUS_CACHE.mkdir(parents=True, exist_ok=True)
    COLUMNS_JSON.write_text(json.dumps(fable_extract._schema_column_defs()))

    pdf_by_id = load_pdf_id_map()
    if not pdf_by_id:
        sys.exit("outputs/pdf_id_map.csv is missing or empty: run scripts/build_pdf_id_map.py first")
    lids = sorted(pdf_by_id, key=lambda x: (len(x), x))
    if args.limit:
        lids = lids[: args.limit]
    manifest = load_manifest()
    today = time.strftime("%Y-%m-%d")

    # --- 1. which PDF backs each record now, by content hash --------------------
    t0 = time.time()
    current: dict[str, dict] = {}
    n_missing_pdf = 0
    for i, lid in enumerate(lids):
        pdf = pdf_by_id[lid]
        try:
            st = pdf.stat()
        except OSError:
            n_missing_pdf += 1
            continue
        prev = manifest.get(lid, {})
        if (prev.get("pdf") == str(pdf) and prev.get("size") == str(st.st_size)
                and prev.get("mtime") == str(int(st.st_mtime)) and prev.get("sha")):
            sha = prev["sha"]
        else:
            sha = sha1_of(pdf)
        current[lid] = {"lit_id": lid, "sha": sha, "pdf": str(pdf),
                        "size": str(st.st_size), "mtime": str(int(st.st_mtime))}
        if not args.quiet and (i + 1) % 2000 == 0:
            print(f"  ...hashed {i+1}/{len(lids)} ({time.time()-t0:.0f}s)", file=sys.stderr)

    # --- 2. extract text where missing or where the record's PDF changed -------
    todo = []
    for lid, row in current.items():
        text_path = TEXTS / f"{lid}.txt"
        prev_sha = manifest.get(lid, {}).get("sha")
        if text_path.exists() and prev_sha == row["sha"]:
            row["extracted_at"] = manifest[lid].get("extracted_at") or today
            continue
        todo.append(lid)

    def _extract(lid: str):
        text = extract_text_from_pdf(Path(current[lid]["pdf"]))
        if not text:
            return lid, False
        tmp = TEXTS / f"{lid}.txt.tmp"
        tmp.write_text(text[:MAX_CHARS])
        os.replace(tmp, TEXTS / f"{lid}.txt")
        return lid, True

    n_ok = n_fail = 0
    failed: list[str] = []
    if todo:
        print(f"extracting text for {len(todo):,} records with {args.workers} workers ...",
              file=sys.stderr)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for k, (lid, ok) in enumerate(ex.map(_extract, todo), 1):
                if ok:
                    n_ok += 1
                    current[lid]["extracted_at"] = today
                else:
                    n_fail += 1
                    failed.append(lid)
                    (TEXTS / f"{lid}.txt").unlink(missing_ok=True)  # stale text from a previous PDF
                if not args.quiet and k % 500 == 0:
                    print(f"  ...{k}/{len(todo)} extracted ok={n_ok} failed={n_fail} "
                          f"({time.time()-t0:.0f}s)", file=sys.stderr)
    for lid in failed:
        current.pop(lid, None)

    # --- 3. quarantine texts the map does not back ------------------------------
    on_disk = {p.stem for p in TEXTS.glob("*.txt")}
    unbacked = sorted(on_disk - set(current), key=lambda x: (len(x), x))
    if args.purge_unbacked and unbacked:
        UNBACKED_DIR.mkdir(exist_ok=True)
        sha_owner: dict[str, list[str]] = {}
        for lid, row in current.items():
            sha_owner.setdefault(row["sha"], []).append(lid)
        mapped_all = set(pdf_by_id)
        new_rows = []
        for lid in unbacked:
            sha = manifest.get(lid, {}).get("sha", "")
            owners = sha_owner.get(sha, [])
            if lid in mapped_all and lid not in current:
                reason = "pdf_missing_or_unreadable"
            elif lid not in mapped_all and owners:
                reason = "same_pdf_now_mapped_to:" + ";".join(owners)
            elif lid not in mapped_all:
                reason = "record_not_in_pdf_id_map"
            else:
                reason = "unknown"
            shutil.move(str(TEXTS / f"{lid}.txt"), str(UNBACKED_DIR / f"{lid}.txt"))
            new_rows.append({"lit_id": lid, "sha": sha, "reason": reason, "moved_on": today})
            manifest.pop(lid, None)
        write_header = not UNBACKED_CSV.exists()
        with open(UNBACKED_CSV, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["lit_id", "sha", "reason", "moved_on"])
            if write_header:
                w.writeheader()
            w.writerows(new_rows)
        print(f"moved {len(unbacked):,} unbacked texts to {UNBACKED_DIR}", file=sys.stderr)

    # --- 4. manifest + Fable worklist ------------------------------------------
    for lid, row in current.items():
        manifest[lid] = {**manifest.get(lid, {}), **row}
    if not args.limit:
        # a partial run must not drop manifest rows for records it did not visit
        manifest = {lid: r for lid, r in manifest.items()
                    if lid in current or (TEXTS / f"{lid}.txt").exists()}
    write_manifest(manifest)

    worklist = [{"lit_id": lid, "text_path": str(TEXTS / f"{lid}.txt"), "sha": row["sha"]}
                for lid, row in current.items()
                if not (CORPUS_CACHE / f"{row['sha']}.txt").exists()]
    # Newest papers first, as the July burn ran (index 0 = most recent year); the
    # burn consumes the list by position, so this order IS the priority order.
    years = _years_by_lid()
    worklist.sort(key=lambda e: (-(years.get(e["lit_id"]) or 0), len(e["lit_id"]), e["lit_id"]))
    worklist_path, coverage_path = WORKLIST, COVERAGE
    if args.limit:
        # a smoke run must never replace the burn's worklist with a truncated one
        worklist_path = OUT / "fable_corpus_worklist.smoke.json"
        coverage_path = OUT / "fable_prepass_coverage.smoke.json"
    elif args.worklist_to_next:
        worklist_path = OUT / "fable_corpus_worklist.next.json"
    elif WORKLIST.exists():
        shutil.copy(WORKLIST, OUT / "fable_corpus_worklist_prev.json")
    worklist_path.write_text(json.dumps(worklist))

    n_done = len(current) - len(worklist)
    cov = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "records_in_pdf_id_map": len(pdf_by_id),
        "records_in_scope": len(lids),
        "pdf_missing_on_disk": n_missing_pdf,
        "texts_already_current": len(current) - n_ok,
        "extraction_attempted": len(todo),
        "extraction_succeeded": n_ok,
        "extraction_failed_no_text": n_fail,
        "extraction_failed_ids": failed,
        "texts_backed_by_map": len(current),
        "texts_unbacked_found": len(unbacked),
        "texts_unbacked_quarantined": len(unbacked) if args.purge_unbacked else 0,
        "fable_done_by_sha": n_done,
        "fable_worklist": len(worklist),
    }
    coverage_path.write_text(json.dumps(cov, indent=1))

    print("\nPre-pass complete:")
    for k, v in cov.items():
        if k != "extraction_failed_ids":
            print(f"  {k:28s}: {v}")
    print(f"  worklist  : {worklist_path}")
    print(f"  manifest  : {MANIFEST}")
    if unbacked and not args.purge_unbacked:
        print(f"  NOTE: {len(unbacked):,} texts are not backed by the id map; "
              f"re-run with --purge-unbacked to quarantine them")
    if worklist:
        print(f"  suggested burn shards (<=300/shard): {-(-len(worklist) // 300)}")


if __name__ == "__main__":
    main()
