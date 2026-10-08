#!/usr/bin/env python3
"""Cross-reference the JSTOR Text Analysis Support metadata dump against the
outstanding (not yet held) papers in docs/papers_data.json.

Two matching channels, reported separately:
  1. DOI exact: our `doi` == JSTOR `ithaka_doi` (case-insensitive). Any prefix,
     not only 10.2307, because JSTOR mirrors publisher DOIs for some titles.
  2. Title + year (±1) for outstanding rows that got no DOI hit, restricted to
     JSTOR items with a parseable title. These are CANDIDATES only: an ingest
     identity check is still required before anything is filed.

Outputs (outputs/jstor_match/):
  jstor_doi_matches.csv        one row per DOI-exact hit
  jstor_title_candidates.csv   one row per title+year candidate
  jstor_item_ids_doi_oa.txt    upload list, DOI hits with review_required=false
  jstor_item_ids_doi_review.txt upload list, DOI hits with review_required=true
  coverage.json                rows in scope / matched / unmatched, by class

Usage: python3 scripts/match_jstor_metadata.py ~/Downloads/jstor_metadata_YYYY-MM-DD.jsonl.gz
"""
import csv
import gzip
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "jstor_match"
OUT.mkdir(parents=True, exist_ok=True)
OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new"}

_ws = re.compile(r"[^a-z0-9]+")


def norm_title(t):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    return _ws.sub(" ", t.lower()).strip()


def norm_doi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def year_of(s):
    m = re.match(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


def main(meta_path):
    papers = json.load(open(ROOT / "docs" / "papers_data.json"))
    out = [p for p in papers if p.get("last_status") in OUTSTANDING]
    by_doi = {}
    for p in out:
        d = norm_doi(p.get("doi"))
        if d:
            by_doi.setdefault(d, []).append(p)
    by_title = defaultdict(list)
    for p in out:
        nt = norm_title(p.get("title"))
        if len(nt) >= 25:
            by_title[nt].append(p)
    print(f"outstanding {len(out):,}  with DOI {len(by_doi):,}  with usable title {len(by_title):,}",
          flush=True)

    doi_hits = []      # (paper, item)
    title_hits = []    # (paper, item)
    n = 0
    t0 = time.time()
    with gzip.open(meta_path, "rt", encoding="utf-8") as f:
        for line in f:
            n += 1
            if n % 500_000 == 0:
                print(f"  {n:,} lines  {time.time()-t0:,.0f}s  doi_hits={len(doi_hits)} title_hits={len(title_hits)}",
                      flush=True)
            # cheap prefilter: skip lines with no title and a community/aluka DOI
            if '"title":null' in line and '"ithaka_doi":"10.2307/community' in line:
                continue
            try:
                it = json.loads(line)
            except json.JSONDecodeError:
                continue
            d = norm_doi(it.get("ithaka_doi"))
            if d and d in by_doi:
                for p in by_doi[d]:
                    doi_hits.append((p, it))
                continue
            nt = norm_title(it.get("title"))
            if nt and nt in by_title:
                jy = year_of(it.get("published_date"))
                for p in by_title[nt]:
                    try:
                        py = int(float(p.get("year")))
                    except (TypeError, ValueError):
                        py = None
                    if jy is None or py is None or abs(jy - py) <= 1:
                        title_hits.append((p, it))
    print(f"done: {n:,} lines in {time.time()-t0:,.0f}s", flush=True)

    def row(p, it):
        ids = it.get("identifiers") or {}
        return {
            "literature_id": p.get("literature_id"),
            "our_doi": p.get("doi"),
            "our_year": p.get("year"),
            "our_journal": p.get("journal_clean") or p.get("journal"),
            "our_title": p.get("title"),
            "item_id": it.get("item_id"),
            "ithaka_doi": it.get("ithaka_doi"),
            "review_required": it.get("review_required"),
            "licensing_status": it.get("licensing_status"),
            "jstor_title": (it.get("title") or "").replace("\n", " ").strip(),
            "jstor_journal": it.get("is_part_of"),
            "jstor_date": it.get("published_date"),
            "content_type": it.get("content_type"),
            "content_subtype": it.get("content_subtype"),
            "print_issn": ids.get("print_issn"),
            "url": it.get("url"),
        }

    doi_rows = [row(p, it) for p, it in doi_hits]
    matched_lids = {r["literature_id"] for r in doi_rows}
    title_rows = [row(p, it) for p, it in title_hits if p.get("literature_id") not in matched_lids]

    for name, rows in (("jstor_doi_matches.csv", doi_rows), ("jstor_title_candidates.csv", title_rows)):
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(doi_rows[0].keys()) if doi_rows else list(row(out[0], {}).keys()))
            w.writeheader()
            w.writerows(rows)

    oa_ids = sorted({r["item_id"] for r in doi_rows if r["review_required"] is False})
    rv_ids = sorted({r["item_id"] for r in doi_rows if r["review_required"] is not False})
    (OUT / "jstor_item_ids_doi_oa.txt").write_text("\n".join(oa_ids) + ("\n" if oa_ids else ""))
    (OUT / "jstor_item_ids_doi_review.txt").write_text("\n".join(rv_ids) + ("\n" if rv_ids else ""))

    jstor_prefix = [p for p in out if norm_doi(p.get("doi")).startswith("10.2307/")]
    unmatched_2307 = [p for p in jstor_prefix if p.get("literature_id") not in matched_lids]
    cov = {
        "metadata_file": str(meta_path),
        "jstor_lines_read": n,
        "outstanding_rows": len(out),
        "outstanding_with_doi": len(by_doi),
        "outstanding_10_2307": len(jstor_prefix),
        "doi_exact_matches": len(doi_rows),
        "doi_exact_distinct_papers": len(matched_lids),
        "doi_matches_by_prefix": dict(Counter(norm_doi(r["our_doi"]).split("/")[0] for r in doi_rows)),
        "doi_matches_review_required": sum(1 for r in doi_rows if r["review_required"] is not False),
        "doi_matches_open": sum(1 for r in doi_rows if r["review_required"] is False),
        "unmatched_10_2307": len(unmatched_2307),
        "unmatched_10_2307_sample": [p.get("doi") for p in unmatched_2307[:20]],
        "title_year_candidates": len(title_rows),
        "title_candidates_distinct_papers": len({r["literature_id"] for r in title_rows}),
        "title_candidates_by_jstor_journal": dict(Counter(r["jstor_journal"] for r in title_rows).most_common(30)),
        "doi_matches_by_jstor_journal": dict(Counter(r["jstor_journal"] for r in doi_rows).most_common(30)),
    }
    json.dump(cov, open(OUT / "coverage.json", "w"), indent=1)
    print(json.dumps(cov, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
