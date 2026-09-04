#!/usr/bin/env python3
"""Recover missing DOIs for outstanding papers via Crossref (Track C1).

Run over the WHOLE no-DOI pool regardless of year. Measured 2026-09-03,
recoverability has no age gradient: 24.0% pre-1950, 9.0% 1950-79, 12.0%
1980-99, 13.0% 2000-09, 19.4% 2010+. A positive control (papers whose DOI we
already hold, hidden then re-recovered through this same pipeline) returns
92-95% in every era, so the pipeline is sound and the low rates are a property
of the data: the residue is grey literature, regional non-English serials,
museum bulletins, and book chapters at every date. Expect ~900-1,200
promotions from ~6,970 article-shaped rows, not thousands.

ACCEPTANCE IS DELIBERATELY STRICTER THAN THE PROBE'S
The probe used title>=0.75 plus year+/-1 and still produced a wrong DOI in ~5%
of controls. After the 2026-04 off-by-one corruption put 45 wrong DOIs into the
download helper for three months, a confidently wrong DOI is worse than a blank
one. Production requires year+/-1 AND (title>=0.90 OR title>=0.75 with a
first-author surname match). Anything that would have passed the looser gate but
fails this one is written to a review file rather than applied, so the
tightening withholds candidates instead of losing them.

THREE OUTCOMES, NEVER TWO
hit / rejected (candidates returned, none good enough) / absent (no candidates)
are kept apart, and `error` is excluded from every rate denominator. A 429 that
silently counted as "no DOI exists" would turn a rate limit into a finding.
Only 200s are cached: a cached failure makes a transient block permanent.

Usage:
    python3 scripts/recover_missing_dois.py [--limit N] [--dry-run] [--apply]

Default is a full pass that WRITES nothing until --apply is given.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from sync_shark_references import _title_similarity, _title_tokens  # noqa: E402

PAPERS = ROOT / "docs/papers_data.json"
CACHE = ROOT / "outputs/.doi_recovery_cache.json"
REVIEW = ROOT / f"outputs/doi_recovery_review_{date.today():%Y-%m-%d}.csv"
COVERAGE = ROOT / f"outputs/doi_recovery_coverage_{date.today():%Y-%m-%d}.json"

API = "https://api.crossref.org/works"
MAILTO = "simondedman@gmail.com"
DELAY = 0.6
TITLE_STRICT = 0.90
TITLE_LOOSE = 0.75
YEAR_TOL = 1

MIN_TOKENS = 4          # a title with fewer content words cannot be judged
TWO_SIDED_MIN = 0.60    # overlap over the LONGER title


def title_ok(ours: str, cand: str, sim: float, author_ok: bool) -> tuple[bool, str]:
    """Two-sided title test.

    `_title_similarity` divides the token overlap by the SHORTER title, so a
    two-token Crossref record scores a perfect 1.00 against any longer title
    containing those words. On the first full pass that produced 170 confident
    but wrong matches: "CHIMAERAS" for a European field guide, "OSPREY" for a
    paper on osprey predation, "São Tomé and Príncipe" for a coastal fish
    checklist. All index or encyclopaedia entries, none the actual paper.

    So require BOTH titles to carry enough content words, and require the
    overlap to hold up over the LONGER title too, not just the shorter one.
    """
    ta, tb = _title_tokens(ours), _title_tokens(cand)
    if not ta or not tb:
        return False, "unusable title"
    if min(len(ta), len(tb)) < MIN_TOKENS:
        return False, f"title too short to judge ({min(len(ta), len(tb))} tokens)"
    two_sided = len(ta & tb) / max(len(ta), len(tb))
    if two_sided < TWO_SIDED_MIN:
        return False, f"two-sided overlap {two_sided:.2f} < {TWO_SIDED_MIN}"
    if sim >= TITLE_STRICT or (sim >= TITLE_LOOSE and author_ok):
        return True, f"sim={sim:.2f} two_sided={two_sided:.2f}"
    return False, f"sim {sim:.2f} below gate"


NON_ARTICLE = re.compile(
    r"abstract|programm|program\b|proceedings|resúmenes|resumenes|congress|"
    r"symposium|conference|meeting|libro de|book of|thesis|dissertation|"
    r"workshop|booklet|unknown|^\s*$", re.I)


def is_article(journal: str) -> bool:
    j = (journal or "").strip()
    if len(j) < 6 or NON_ARTICLE.search(j):
        return False
    if len(j.split()) == 1 and j.istitle():
        return False
    return True


def year_of(v):
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def surname(authors: str) -> str:
    return re.split(r"[,&(]", (authors or "").strip())[0].strip().lower()


def query_string(p: dict) -> str:
    """Prefer findspot_raw: a real venue string beats 'Proceedings of the'."""
    venue = (p.get("findspot_raw") or p.get("journal_clean")
             or p.get("journal") or "")
    return f"{(p.get('title') or '').strip()} {venue}".strip()


def lookup(session, p: dict):
    """-> (outcome, payload). outcome in {hit, near, rejected, absent, error}"""
    title = (p.get("title") or "").strip()
    if len(title) < 15:
        return "absent", None
    params = {"query.bibliographic": query_string(p), "rows": 5,
              "select": "DOI,title,container-title,issued,author",
              "mailto": MAILTO}
    try:
        r = session.get(API, params=params, timeout=45)
        if r.status_code in (429, 403, 503) or not r.ok:
            return "error", {"http": r.status_code}
        items = r.json()["message"]["items"]
    except Exception as e:  # noqa: BLE001
        return "error", {"exc": type(e).__name__}
    if not items:
        return "absent", None

    want_year = year_of(p.get("year"))
    want_surname = surname(p.get("authors", ""))
    best = None
    for it in items:
        cand_title = (it.get("title") or [""])[0]
        sim = _title_similarity(title, cand_title)
        if sim is None:
            continue
        issued = (it.get("issued", {}).get("date-parts") or [[None]])[0]
        cand_year = issued[0] if issued else None
        year_ok = (not want_year or not cand_year
                   or abs(cand_year - want_year) <= YEAR_TOL)
        cand_surnames = {(a.get("family") or "").lower()
                         for a in (it.get("author") or [])}
        author_ok = bool(want_surname) and want_surname in cand_surnames

        rec = {"doi": it["DOI"], "sim": round(sim, 3), "year": cand_year,
               "author_ok": author_ok,
               "title": cand_title[:140],
               "journal": (it.get("container-title") or [""])[0][:80]}
        accepted, why = title_ok(title, cand_title, sim, author_ok)
        rec["why"] = why
        if year_ok and accepted:
            return "hit", rec
        # Would have passed the probe's looser gate: hold for review.
        if year_ok and sim >= TITLE_LOOSE and best is None:
            best = rec
    return ("near", best) if best else ("rejected", None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--apply", action="store_true",
                    help="write recovered DOIs into papers_data.json")
    args = ap.parse_args()

    papers = json.loads(PAPERS.read_text())
    pool = [p for p in papers
            if not (p.get("doi") or "").strip()
            and is_article(p.get("findspot_raw") or p.get("journal_clean")
                           or p.get("journal") or "")]
    if args.limit:
        pool = pool[:args.limit]

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    print(f"no-DOI article-shaped rows: {len(pool):,}   cached: {len(cache):,}")

    session = requests.Session()
    session.headers["User-Agent"] = f"elasmo-analyses/1.0 (mailto:{MAILTO})"

    outcomes = Counter()
    hits, nears = {}, []
    started = time.time()

    for i, p in enumerate(pool, 1):
        lid = str(p.get("literature_id", "")).replace(".0", "")
        key = lid or (p.get("title") or "")[:80]
        if key in cache:
            rec = cache[key]
            outcomes[rec["outcome"]] += 1
            if rec["outcome"] == "hit":
                hits[key] = rec["match"]
            elif rec["outcome"] == "near":
                nears.append((p, rec["match"]))
            continue

        outcome, payload = lookup(session, p)
        outcomes[outcome] += 1
        # Cache 200s only. A cached failure would make a transient block
        # permanent, and this pass is meant to be re-runnable.
        if outcome in ("hit", "near", "rejected", "absent"):
            cache[key] = {"outcome": outcome, "match": payload}
        if outcome == "hit":
            hits[key] = payload
        elif outcome == "near":
            nears.append((p, payload))

        if i % 100 == 0:
            rate = i / max(time.time() - started, 1)
            eta = (len(pool) - i) / rate if rate else 0
            fin = time.localtime(time.time() + eta)
            print(f"  {i:,}/{len(pool):,}  {dict(outcomes)}  "
                  f"eta {eta/60:.0f}m ({time.strftime('%H:%M %Z', fin)})",
                  flush=True)
            CACHE.write_text(json.dumps(cache))
        time.sleep(DELAY)

    CACHE.write_text(json.dumps(cache))

    ok = sum(v for k, v in outcomes.items() if k != "error")
    print("\n" + "=" * 62)
    for k, v in outcomes.most_common():
        print(f"  {k:10} {v:6,}")
    print(f"\nrecovery rate: {100*outcomes['hit']/ok:.1f}% of {ok:,} successful "
          f"queries ({outcomes['error']:,} errors excluded from the denominator)")

    # Coverage beside results: a truncated pass must look truncated.
    COVERAGE.write_text(json.dumps({
        "run_finished": datetime.now().isoformat(timespec="seconds"),
        "pool_size": len(pool), "queried": len(pool),
        "outcomes": dict(outcomes), "applied": bool(args.apply),
    }, indent=1))

    if nears:
        import csv
        with REVIEW.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["literature_id", "year", "authors", "title",
                        "candidate_doi", "candidate_title", "candidate_year",
                        "title_sim", "author_match", "decision"])
            for p, m in nears:
                w.writerow([p.get("literature_id"), p.get("year"),
                            (p.get("authors") or "")[:80],
                            (p.get("title") or "")[:140], m["doi"], m["title"],
                            m["year"], m["sim"], m["author_ok"], ""])
        print(f"near-misses held for review: {len(nears):,} -> {REVIEW.name}")

    if not args.apply:
        print("\n(no --apply: nothing written to papers_data.json)")
        return

    backup = PAPERS.with_suffix(f".backup-{datetime.now():%Y%m%d-%H%M%S}.json")
    shutil.copy2(PAPERS, backup)
    n = 0
    for p in papers:
        key = str(p.get("literature_id", "")).replace(".0", "") \
            or (p.get("title") or "")[:80]
        if key in hits and not (p.get("doi") or "").strip():
            p["doi"] = hits[key]["doi"]
            p["doi_source"] = "crossref_recovery_2026-09"
            n += 1
    tmp = PAPERS.with_suffix(".tmp")
    tmp.write_text(json.dumps(papers, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    tmp.replace(PAPERS)
    print(f"\napplied {n:,} recovered DOIs (backup: {backup.name})")
    print("NOTE: run the sync's Phase 3b DOI verification over these before "
          "the download helper links to any of them.")


if __name__ == "__main__":
    main()
