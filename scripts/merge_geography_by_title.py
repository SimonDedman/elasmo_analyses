#!/usr/bin/env python3
"""
Companion to merge_geography.py.

merge_geography.py resolves paper_geography.paper_id (a SharkPapers
library FILENAME) to a parquet literature_id by parsing the filename
into (author, year, truncated-title-words) and fuzzy-matching against
the parquet's author/year/title columns. That leaves ~300/6,183 rows
unmatched -- usually because the filename's title fragment is a heavily
abbreviated/word-clipped truncation (e.g. "Eval artisan fish glob
threat elasmo Bay Bengal") that doesn't subsequence-match the real
title closely enough, or the (author, year) bucket has several papers
and the filename fragment is ambiguous between them.

This script recovers those rows by going straight to the source: it
locates the actual PDF on disk (by filename, allowing for minor
naming drift such as O'Connell/OConnell or trailing punctuation), runs
`pdftotext` on pages 1-2, extracts a title guess, and matches that
title (via difflib ratio + significant-word overlap, within year +/-2)
against the parquet's `title` column. This is strictly a supplement to
merge_geography.py: it only considers rows that script left unmatched,
and applies the same "reject on ambiguity" discipline.

Usage:
    python scripts/merge_geography_by_title.py             # merge, write parquet
    python scripts/merge_geography_by_title.py --dry-run    # report only, no writes
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_geography as mg  # reuse FILENAME_RE, word_list, subseq_match_score, GEO_COLUMNS, strip_accents

PROJECT = mg.PROJECT
DB_PATH = mg.DB_PATH
PARQUET_PATH = mg.PARQUET_PATH
BACKUP_DIR = mg.BACKUP_DIR
LIBRARY_ROOT = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")

GEO_COLUMNS = mg.GEO_COLUMNS
FILENAME_RE = mg.FILENAME_RE

TITLE_RATIO_THRESHOLD = 0.85
MIN_SHARED_WORDS = 6
YEAR_TOLERANCE = 2
PDF_TEXT_TIMEOUT = 15
AMBIGUITY_MARGIN = 0.95  # 2nd-best score within this fraction of best -> reject


# ---------------------------------------------------------------------------
# Locate the physical PDF for a paper_geography.paper_id filename
# ---------------------------------------------------------------------------

def norm_author(a: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", mg.strip_accents(a).lower())


def build_library_index() -> tuple[dict, dict]:
    """basename -> [paths]; (norm_author, year) -> [paths]."""
    basename_map: dict[str, list[str]] = defaultdict(list)
    ay_index: dict[tuple[str, str], list[str]] = defaultdict(list)
    for root, _, files in os.walk(LIBRARY_ROOT):
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            p = os.path.join(root, fn)
            basename_map[fn].append(p)
            m = FILENAME_RE.match(fn)
            if m:
                ay_index[(norm_author(m.group("author")), m.group("year"))].append(p)
    return basename_map, ay_index


def locate_candidates(pid: str, basename_map: dict, ay_index: dict) -> list[str]:
    """Return plausible on-disk PDF path(s) for a geography paper_id.

    Exact basename match wins outright. Otherwise falls back to the
    (normalised author, year) bucket -- this may return >1 path when
    several papers by the same first author appeared the same year;
    those are disambiguated later by actually reading each PDF's title.
    """
    if pid in basename_map:
        return basename_map[pid]
    m = FILENAME_RE.match(pid)
    if not m:
        return []
    return ay_index.get((norm_author(m.group("author")), m.group("year")), [])


# ---------------------------------------------------------------------------
# PDF text / title extraction
# ---------------------------------------------------------------------------

def extract_first_pages_text(pdf_path: str) -> str:
    parts = []
    for pg in ("1", "2"):
        try:
            r = subprocess.run(
                ["pdftotext", "-f", pg, "-l", pg, pdf_path, "-"],
                capture_output=True, text=True, timeout=PDF_TEXT_TIMEOUT,
            )
            if r.returncode == 0 and r.stdout:
                parts.append(r.stdout)
        except (subprocess.TimeoutExpired, OSError):
            continue
    return "\n".join(parts)


def guess_title_line(text: str) -> str:
    """First plausible title block on page 1 (adapted from
    scripts/stage_orphan_pdfs.py:guess_title_and_author)."""
    if not text or len(text) < 50:
        return ""
    head = text[:1500]
    cut = re.search(r"\b(Abstract|Introduction|Summary|Keywords|ABSTRACT)\b", head)
    head_for_title = head[: cut.start()] if cut else head
    lines = [ln.strip() for ln in head_for_title.splitlines() if ln.strip()]
    title_lines: list[str] = []
    for ln in lines:
        if len(ln) < 20:
            if title_lines:
                break
            continue
        if re.search(r"\d{4}.*\d{4}", ln):
            continue
        if re.match(
            r"^(Vol|VOL|Volume|VOLUME|Issue|ISSUE|No\.|No |DOI|Received|Accepted|"
            r"Published|Copyright|©)", ln,
        ):
            continue
        title_lines.append(ln)
        if sum(len(t) for t in title_lines) > 200:
            break
    title = " ".join(title_lines).strip()
    return re.sub(r"\s+", " ", title)[:300]


def sig_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower())) - mg.STOPWORDS


# ---------------------------------------------------------------------------
# Match extracted PDF text/title against the parquet
# ---------------------------------------------------------------------------

def build_year_index(df: pd.DataFrame) -> dict[int, list[tuple[str, str, set[str]]]]:
    """year -> [(literature_id, title, sig_words(title))]."""
    idx: dict[int, list[tuple[str, str, set[str]]]] = defaultdict(list)
    for _, row in df.iterrows():
        try:
            year = int(float(row.get("year")))
        except (ValueError, TypeError):
            continue
        title = str(row.get("title", ""))
        idx[year].append((str(row["literature_id"]), title, sig_words(title)))
    return idx


def best_match_for_pdf(pdf_text: str, title_guess: str, year_hint: int | None,
                        year_index: dict) -> tuple[str | None, str]:
    guess_words = sig_words(title_guess) if title_guess else set()
    body_words = sig_words(pdf_text[:2500])

    years = (
        range(year_hint - YEAR_TOLERANCE, year_hint + YEAR_TOLERANCE + 1)
        if year_hint is not None else year_index.keys()
    )
    scored = []
    for y in years:
        for lit_id, rtitle, rwords in year_index.get(y, []):
            if len(rwords) < 3:
                continue
            ratio = SequenceMatcher(None, title_guess.lower(), rtitle.lower()).ratio() if title_guess else 0.0
            shared_guess = len(guess_words & rwords)
            shared_body = len(body_words & rwords)
            best_shared = max(shared_guess, shared_body)
            coverage = best_shared / len(rwords)
            if ratio >= TITLE_RATIO_THRESHOLD or best_shared >= MIN_SHARED_WORDS:
                # combined = shared_count * coverage. Neither raw count nor
                # coverage alone is safe to rank on: a long title sharing
                # many generic words (elasmobranch, shark, species...) with
                # the PDF body racks up a high raw count at low coverage; a
                # short title (e.g. a companion conference abstract) can
                # trivially hit 100% coverage on 3-4 generic words. The
                # product penalises both -- it only scores high when a
                # candidate shares MANY of the words AND those words are
                # MOST of that title.
                combined = best_shared * coverage
                scored.append((combined, best_shared, ratio, coverage, lit_id, rtitle))

    if not scored:
        return None, "no candidate title cleared threshold (ratio>=0.85 or shared_words>=6)"

    scored.sort(key=lambda t: t[0], reverse=True)
    best = scored[0]
    # de-dup same literature_id before checking ambiguity
    others = [s for s in scored[1:] if s[4] != best[4]]
    if others and others[0][0] >= best[0] * AMBIGUITY_MARGIN:
        return None, f"ambiguous: {best[5]!r} (score {best[0]:.2f}) vs {others[0][5]!r} (score {others[0][0]:.2f})"
    return best[4], f"shared_words={best[1]}, ratio={best[2]:.2f}, coverage={best[3]:.2f}, combined={best[0]:.2f}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def normalise_id(x) -> str:
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Report only, do not write parquet")
    args = ap.parse_args()

    if not PARQUET_PATH.exists():
        print(f"ERROR: {PARQUET_PATH} not found", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found", file=sys.stderr)
        return 1
    if not LIBRARY_ROOT.exists():
        print(f"ERROR: {LIBRARY_ROOT} not found", file=sys.stderr)
        return 1

    print(f"Loading {PARQUET_PATH} ...")
    df = pd.read_parquet(PARQUET_PATH)
    print(f"  {len(df)} rows, {len(df.columns)} columns")

    print(f"Loading paper_geography from {DB_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    try:
        geo = pd.read_sql("SELECT * FROM paper_geography", conn)
    finally:
        conn.close()
    print(f"  {len(geo)} geography rows")

    print("Reconstructing merge_geography.py's filename-based mapping "
          "(to find the rows it left unmatched) ...")
    pid_to_litid_filename = mg.build_paper_id_to_literature_id(geo, df)
    all_pids = set(geo["paper_id"])
    unmatched_pids = sorted(all_pids - set(pid_to_litid_filename.keys()))
    print(f"  {len(pid_to_litid_filename)}/{len(geo)} matched by filename; "
          f"{len(unmatched_pids)} left for title-text matching")

    already_used_litids = set(pid_to_litid_filename.values())

    print("Indexing SharkPapers library on disk ...")
    basename_map, ay_index = build_library_index()
    print(f"  {sum(len(v) for v in basename_map.values())} PDFs indexed")

    print("Building parquet year -> title index ...")
    year_index = build_year_index(df)

    print(f"Processing {len(unmatched_pids)} unmatched geography rows ...")
    new_mapping: dict[str, str] = {}
    reasons = defaultdict(int)
    detail_rows = []

    for i, pid in enumerate(unmatched_pids, 1):
        if i % 50 == 0:
            print(f"  ... {i}/{len(unmatched_pids)}")
        m = FILENAME_RE.match(pid)
        year_hint = int(m.group("year")) if m else None

        candidates = locate_candidates(pid, basename_map, ay_index)
        if not candidates:
            reasons["pdf_not_found_on_disk"] += 1
            detail_rows.append((pid, None, "not_found", None))
            continue

        # When several papers share the same first author + year, the
        # filename's own (truncated) title fragment is usually still
        # enough to identify which physical file paper_id refers to --
        # e.g. "Baremore...Seasonal size-rel differen diet Atlantic angel
        # shark.pdf" clearly means the "Seasonal and sizerelated
        # differences..." file, not the "Reproductive aspects..." one by
        # the same author+year. Narrow to that single best-filename match
        # before falling back to comparing extracted-title results, so
        # two candidates don't get flagged ambiguous just because both
        # happen to independently clear the title-match threshold.
        if len(candidates) > 1 and m:
            fn_words = mg.word_list(m.group("title"))
            scored_fn = []
            for c in candidates:
                m2 = FILENAME_RE.match(os.path.basename(c))
                tw = mg.word_list(m2.group("title")) if m2 else []
                matched, tot = mg.subseq_match_score(fn_words, tw)
                frac = matched / tot if tot else 0.0
                scored_fn.append((frac, c))
            scored_fn.sort(key=lambda t: t[0], reverse=True)
            if scored_fn[0][0] > 0 and (len(scored_fn) < 2 or scored_fn[0][0] > scored_fn[1][0]):
                candidates = [scored_fn[0][1]]

        # Try every (remaining) candidate PDF; keep the single best match
        # across all of them, and require it to beat the others clearly.
        best_overall = None  # (score, lit_id, reason, path)
        per_candidate_ambiguous = False
        for path in candidates:
            text = extract_first_pages_text(path)
            if len(text.strip()) < 30:
                continue
            title_guess = guess_title_line(text)
            lit_id, reason = best_match_for_pdf(text, title_guess, year_hint, year_index)
            if lit_id is None:
                continue
            # score for cross-candidate comparison: parse back out of reason string is fragile;
            # recompute directly instead.
            if best_overall is None or lit_id != best_overall[1]:
                if best_overall is not None:
                    per_candidate_ambiguous = True
                best_overall = (reason, lit_id, reason, path)

        if best_overall is None:
            reasons["title_no_match"] += 1
            detail_rows.append((pid, candidates[0] if len(candidates) == 1 else str(candidates), "no_title_match", None))
            continue
        if per_candidate_ambiguous:
            reasons["ambiguous_across_candidate_files"] += 1
            detail_rows.append((pid, str(candidates), "ambiguous_candidates", None))
            continue

        _, lit_id, reason, path = best_overall
        if lit_id in already_used_litids or lit_id in new_mapping.values():
            reasons["literature_id_already_claimed"] += 1
            detail_rows.append((pid, path, f"already_claimed:{reason}", lit_id))
            continue

        new_mapping[pid] = lit_id
        reasons["matched"] += 1
        detail_rows.append((pid, path, reason, lit_id))

    print()
    print("=== Title-text matching report ===")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print(f"  Newly recovered: {len(new_mapping)} / {len(unmatched_pids)} previously-unmatched rows")

    log_path = PROJECT / "outputs" / "geography_title_match_log.csv"
    pd.DataFrame(detail_rows, columns=["paper_id", "pdf_path", "reason", "literature_id"]).to_csv(log_path, index=False)
    print(f"  Detail log: {log_path}")

    if not new_mapping:
        print("\nNo new matches recovered -- nothing to merge.")
        return 0

    # Build the geo_ subset for the newly matched rows only
    geo_new = geo[geo["paper_id"].isin(new_mapping.keys())].copy()
    geo_new["literature_id"] = geo_new["paper_id"].map(new_mapping).map(normalise_id)
    geo_new = geo_new.drop_duplicates(subset=["literature_id"], keep="first")
    geo_subset = geo_new[["literature_id"] + GEO_COLUMNS].copy()
    geo_subset = geo_subset.rename(columns={c: f"geo_{c}" for c in GEO_COLUMNS})

    df["_lit_id_norm"] = df["literature_id"].map(normalise_id)
    geo_cols_present = [f"geo_{c}" for c in GEO_COLUMNS if f"geo_{c}" in df.columns]
    if not geo_cols_present:
        print("ERROR: expected geo_ columns from merge_geography.py not found in parquet "
              "-- run merge_geography.py first.", file=sys.stderr)
        return 1

    # Fill only rows where geo_ columns are currently all-NA, using combine_first
    # per matched literature_id (never overwrite an existing filename-based match).
    lookup = geo_subset.set_index("_lit_id_norm" if "_lit_id_norm" in geo_subset.columns else "literature_id")

    n_filled = 0
    for lit_id_norm, gz_row in geo_subset.set_index("literature_id").iterrows():
        mask = (df["_lit_id_norm"] == lit_id_norm) & df["geo_first_author_country"].isna()
        if not mask.any():
            continue
        for c in geo_cols_present:
            df.loc[mask, c] = gz_row[c]
        n_filled += mask.sum()

    df = df.drop(columns=["_lit_id_norm"])

    coverage_any = df[geo_cols_present].notna().any(axis=1).sum()
    print()
    print("=== Merge report ===")
    print(f"Rows filled this run:        {n_filled}")
    print(f"Rows total:                  {len(df)}")
    print(f"Rows with any geo_ data now: {coverage_any} ({coverage_any / len(df) * 100:.2f}%)")

    if args.dry_run:
        print("\n--dry-run: not writing parquet.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"literature_review_enriched.backup_{timestamp}.parquet"
    print(f"\nBacking up original parquet to {backup_path}")
    shutil.copy2(PARQUET_PATH, backup_path)

    tmp_path = PARQUET_PATH.with_suffix(".parquet.tmp")
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, PARQUET_PATH)
    print(f"Wrote merged parquet to {PARQUET_PATH} ({len(df)} rows, {len(df.columns)} columns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
