#!/usr/bin/env python3
"""Fetch the chapters of a free bepress / DigitalCommons series and stage them
by literature_id.

A DigitalCommons "series" page lists every item as
<a href="https://<host>/<series>/<n>">Title</a>; the PDF of item n is
https://<host>/cgi/viewcontent.cgi?article=<1000+n-1...>&context=<series>, but the
article number is not derivable, so the item page is read for its
`citation_pdf_url` meta tag.

Stages verified PDFs as <staging-dir>/<literature_id>.pdf for a later
`acquire_cascade.py --finalize-only --staging-dir <dir>`. Writes nothing to
docs/papers_data.json. Beside the PDFs it writes manifest.csv and
coverage.json (in scope / attempted / staged / failed by class / not attempted).

Usage (Thorson 1976, Investigations of the Ichthyofauna of Nicaraguan Lakes):
  python3 scripts/fetch_digitalcommons_series.py \
      --series-url https://digitalcommons.unl.edu/ichthynicar/ \
      --venue "ichthyofauna of Nicaraguan lakes" \
      --staging-dir outputs/download_push_2026-09-18/thorson_unl
"""
import argparse
import csv
import html
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_free_sources import (  # noqa: E402
    Fetcher, compile_patterns, first_surname, load_papers, outstanding_scope,
    sha256_of, title_overlap, verify_pdf,
)

MATCH_THRESHOLD = 0.6  # INFERRED: title-token overlap; every accepted match is also verified against the PDF text


def list_series(fetcher, series_url):
    """Returns ([(item_url, title)], status). A non-200 is a block or error, never 'empty'."""
    status, body, _err, _cached = fetcher.get(series_url, use_cache=False)
    if status != 200:
        return [], status
    text = body.decode("utf-8", "replace")
    host_series = re.escape(series_url.rstrip("/"))
    items = re.findall(r'<a href="(' + host_series + r'/\d+)"[^>]*>(.*?)</a>', text, re.S)
    return [(u, html.unescape(re.sub(r"<.*?>", "", t)).strip()) for u, t in items], 200


def pdf_url_of(fetcher, item_url):
    status, body, _err, _cached = fetcher.get(item_url)
    if status != 200:
        return None, status
    text = body.decode("utf-8", "replace")
    m = re.search(r'<meta name="bepress_citation_pdf_url" content="([^"]+)"', text)
    return (html.unescape(m.group(1)) if m else None), 200


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series-url", required=True)
    ap.add_argument("--venue", required=True, help="pattern matched against journal / journal_clean / findspot_raw")
    ap.add_argument("--staging-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=8.0,
                    help="seconds between requests; bepress 403s bursts (MEASURED 2026-09-18: 9 of 15 at ~1 s)")
    args = ap.parse_args()

    staging = Path(args.staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher("digitalcommons", sleep=args.sleep)
    scope = outstanding_scope(load_papers(), compile_patterns(args.venue))
    items, status = list_series(fetcher, args.series_url)
    cov = {"series_url": args.series_url, "venue": args.venue, "rows_in_scope": len(scope),
           "series_items_listed": len(items), "series_index_status": status,
           "attempted": 0, "staged": 0, "already_staged": 0,
           "failed": {"no_title_match": 0, "no_pdf_link": 0, "blocked": 0, "http_error": 0, "verify_failed": 0},
           "not_attempted": 0, "not_attempted_why": ""}
    rows = []
    prior = {}
    if (staging / "manifest.csv").exists():  # a re-run must not erase the provenance of rows staged earlier
        prior = {r["literature_id"]: r for r in csv.DictReader(open(staging / "manifest.csv"))}
    if status != 200 or not items:
        cov["not_attempted"] = len(scope)
        cov["not_attempted_why"] = f"series index unavailable (status {status}, {len(items)} items): BLOCKED OR ERROR, not absent"
        scope = []

    host_blocked = False
    for row in scope:
        lid = str(row["literature_id"])
        if host_blocked and not (staging / f"{lid}.pdf").exists():
            # one 403/429 stops the host: the rest are NOT attempted, which is not "not found"
            cov["not_attempted"] += 1
            cov["not_attempted_why"] = "host returned a block earlier in this run; re-run later (resumable)"
            rows.append({"literature_id": lid, "title": row.get("title", ""), "status": "not_attempted_host_blocked"})
            continue
        dest = staging / f"{lid}.pdf"
        best = max(items, key=lambda it: title_overlap(row.get("title", ""), it[1]))
        score = title_overlap(row.get("title", ""), best[1])
        rec = {"literature_id": lid, "title": row.get("title", ""), "matched_title": best[1],
               "overlap": f"{score:.2f}", "item_url": best[0], "pdf_url": "", "status": "", "note": ""}
        rows.append(rec)
        if dest.exists():
            cov["already_staged"] += 1
            old = prior.get(lid, {})
            rec.update({k: old.get(k, "") for k in ("pdf_url", "note", "sha256") if old.get(k)})
            rec.setdefault("sha256", sha256_of(dest))
            rec["status"] = "staged" if old.get("status", "").startswith("staged") else "already_staged"
            continue
        if score < MATCH_THRESHOLD:
            cov["failed"]["no_title_match"] += 1
            rec["status"] = "no_title_match"
            continue
        if args.dry_run:
            rec["status"] = "dry_run_match"
            continue
        cov["attempted"] += 1
        pdf_url, st = pdf_url_of(fetcher, best[0])
        if st != 200:
            key = "blocked" if st in (403, 429, 503) else "http_error"
            cov["failed"][key] += 1
            rec["status"], rec["note"] = key, f"item page status {st}"
            host_blocked = host_blocked or key == "blocked"
            continue
        if not pdf_url:
            cov["failed"]["no_pdf_link"] += 1
            rec["status"] = "no_pdf_link"
            continue
        rec["pdf_url"] = pdf_url
        st, err = fetcher.download(pdf_url, dest)
        if st != 200:
            key = "blocked" if st in (403, 429, 503) else "http_error"
            cov["failed"][key] += 1
            rec["status"], rec["note"] = key, f"download status {st} {err or ''}"
            dest.unlink(missing_ok=True)
            host_blocked = host_blocked or key == "blocked"
            continue
        ok, note = verify_pdf(dest, title=row.get("title"), surname=first_surname(row.get("authors", "")))
        rec["note"] = note
        if ok is False:
            cov["failed"]["verify_failed"] += 1
            rec["status"] = "verify_failed"
            dest.rename(dest.with_suffix(".pdf.rejected"))
            continue
        rec["status"] = "staged" if ok is True else "staged_scan_unverified"
        rec["sha256"] = sha256_of(dest)
        cov["staged"] += 1
        time.sleep(1.0)

    fields = ["literature_id", "title", "matched_title", "overlap", "item_url", "pdf_url", "status", "note", "sha256"]
    # rows staged on an earlier run and since filed have left the queue: keep their provenance
    seen = {r["literature_id"] for r in rows}
    rows = [r for lid, r in prior.items() if lid not in seen and r.get("status", "").startswith("staged")] + rows
    with open(staging / ("manifest_dry_run.csv" if args.dry_run else "manifest.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    cov["http_counts"] = dict(fetcher.counts)
    if not args.dry_run:
        json.dump(cov, open(staging / "coverage.json", "w"), indent=2)
    print(json.dumps(cov, indent=2))
    for r in rows:
        print(f"{r['literature_id']:>7} {r['status']:26s} {r.get('overlap', '')} | {r['title'][:60]} -> {r.get('matched_title', '')[:50]} | {r.get('note', '')}")


if __name__ == "__main__":
    main()
