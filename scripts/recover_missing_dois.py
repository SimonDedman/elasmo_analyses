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
sys.path.insert(0, str(ROOT))
from sync_shark_references import _title_similarity, _title_tokens  # noqa: E402

PAPERS = ROOT / "docs/papers_data.json"
CACHE = ROOT / "outputs/.doi_recovery_cache.json"
REVIEW = ROOT / f"outputs/doi_recovery_review_{date.today():%Y-%m-%d}.csv"
COVERAGE = ROOT / f"outputs/doi_recovery_coverage_{date.today():%Y-%m-%d}.json"
QUARANTINE = ROOT / "outputs/sr_doi_quarantine.csv"
RECHECK = ROOT / f"outputs/doi_recovery_recheck_{date.today():%Y-%m-%d}.csv"

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


# Red flags that veto a title match, found 2026-10-12 when a team member's
# downloads exposed recovered DOIs pointing at the wrong document: a Geological
# Magazine review whose title quotes the work and names "By A. Karpinsky", a
# Journal of Geology notice ending "Adolf Wurm", a "Deep Sea Research and
# Oceanographic Abstracts" entry, and one 1960 Copeia note assigned to four ORI
# reports on four different attacks (the dates in the titles disagree).
# NOT roman numerals: Ann. Mag. Nat. Hist. numbers every article "XLII.—".
REVIEW_TITLE = re.compile(r"^\s*(reviews?\b|notices?\b|correction to|erratum|corrigendum)", re.I)
REVIEW_DOI = re.compile(r"/review\d*$|/v\d+/review", re.I)
# BHL titles append a statement of responsibility ("/ by F. M. Balfour").
BY_LINE = re.compile(r"/\s*(by|von|di|par|de|door|af)\b", re.I)
MONTHS = ("january february march april may june july august september "
          "october november december").split()


def _months(title: str) -> set:
    t = (title or "").lower()
    return {m for m in MONTHS if re.search(rf"\b{m}\b", t)}


def red_flags(our_title: str, want_surname: str, cand: dict) -> list[str]:
    """Reasons a candidate is a document ABOUT the paper, not the paper."""
    flags = []
    ct = re.sub(r"<[^>]+>", " ", cand.get("title") or "")
    sn = (want_surname or "").strip().lower()
    if (len(sn) >= 3 and re.search(rf"\b{re.escape(sn)}\b", ct.lower())
            and not re.search(rf"\b{re.escape(sn)}\b", (our_title or "").lower())
            and not BY_LINE.search(ct)):
        flags.append(f"candidate title names the author ({sn}): a review or notice")
    if REVIEW_TITLE.search(ct) and not REVIEW_TITLE.search(our_title or ""):
        flags.append("candidate is a review/correction of the paper, not the paper")
    if REVIEW_DOI.search(cand.get("doi") or ""):
        flags.append("peer-review report DOI")
    if re.search(r"abstracts?\b", cand.get("journal") or "", re.I):
        flags.append(f"abstracting journal ({cand.get('journal')})")
    ma, mb = _months(our_title), _months(ct)
    if ma and mb and not (ma & mb):
        flags.append(f"dates in the titles disagree ({'/'.join(sorted(ma))} vs {'/'.join(sorted(mb))})")
    return flags


def load_quarantine() -> set[tuple[str, str]]:
    """(literature_id, doi) pairs already rejected: never re-apply them."""
    import csv
    out = set()
    if QUARANTINE.exists():
        with QUARANTINE.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out.add((str(r.get("literature_id") or ""), (r.get("rejected_doi") or "").lower()))
    return out


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
        flags = red_flags(title, want_surname, rec)
        if flags:
            rec["flags"] = flags
        if year_ok and accepted and not flags:
            return "hit", rec
        # Would have passed the probe's looser gate: hold for review.
        if year_ok and sim >= TITLE_LOOSE and best is None:
            best = rec
    return ("near", best) if best else ("rejected", None)


def recheck(apply: bool) -> None:
    """Re-judge every DOI this pipeline already put on the queue with today's gates.

    A recovered DOI that now raises a red flag, or that sits on two or more
    queue rows, is blanked (with --apply) and appended to the quarantine so no
    later pass re-applies it. DOIs from other sources that are shared between
    rows are reported only: which row owns the DOI needs a human.
    """
    import csv
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    papers = json.loads(PAPERS.read_text())
    holders = Counter((p.get("doi") or "").strip().lower() for p in papers if (p.get("doi") or "").strip())
    out = []
    for p in papers:
        doi = (p.get("doi") or "").strip().lower()
        if not doi:
            continue
        lid = str(p.get("literature_id", "")).replace(".0", "")
        m = (cache.get(lid) or {}).get("match") or {}
        recovered = (m.get("doi") or "").lower() == doi
        flags = red_flags(p.get("title", ""), surname(p.get("authors", "")), m) if recovered else []
        shared = holders[doi] > 1
        if flags and shared:
            flags.append(f"DOI on {holders[doi]} queue rows")
        elif shared:
            # One holder is usually right (a chapter and a duplicate [Abstract]
            # record): report, never blank on this alone.
            out.append({"literature_id": lid, "year": p.get("year"), "authors": (p.get("authors") or "")[:60],
                        "title": (p.get("title") or "")[:120], "doi": doi,
                        "source": "our recovery" if recovered else "other (SR or earlier work)",
                        "candidate_title": (m.get("title") or "")[:120], "candidate_journal": m.get("journal", ""),
                        "flags": f"DOI on {holders[doi]} queue rows", "action": "report only"})
            continue
        if flags:
            out.append({"literature_id": lid, "year": p.get("year"), "authors": (p.get("authors") or "")[:60],
                        "title": (p.get("title") or "")[:120], "doi": doi,
                        "source": "our recovery" if recovered else "other (SR or earlier work)",
                        "candidate_title": (m.get("title") or "")[:120], "candidate_journal": m.get("journal", ""),
                        "flags": "; ".join(flags),
                        "action": "blank + quarantine" if recovered else "report only"})
    with RECHECK.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]) if out else ["literature_id"])
        w.writeheader()
        w.writerows(out)
    blank = {r["literature_id"]: r for r in out if r["action"] == "blank + quarantine"}
    print(f"rechecked {sum(1 for v in holders.values())} queue DOIs: {len(out)} flagged, "
          f"{len(blank)} from our recovery -> {RECHECK.name}")
    if not apply or not blank:
        return
    from lib.papers_data_io import mutate
    with mutate() as rows:
        for p in rows:
            lid = str(p.get("literature_id", "")).replace(".0", "")
            if lid in blank and (p.get("doi") or "").strip().lower() == blank[lid]["doi"]:
                p["doi"] = ""
                p.pop("doi_source", None)
    known = load_quarantine()
    with QUARANTINE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for lid, r in blank.items():
            if (lid, r["doi"]) in known:
                continue
            w.writerow([date.today().isoformat(), lid, r["year"], r["authors"], r["title"], "",
                        r["doi"], r["candidate_title"], r["candidate_journal"], "",
                        f"OUR Crossref DOI recovery, not shark-references: {r['flags']}", ""])
    print(f"blanked {len(blank)} DOIs and quarantined them")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--apply", action="store_true",
                    help="write recovered DOIs into papers_data.json")
    ap.add_argument("--recheck", action="store_true",
                    help="re-judge DOIs already on the queue (with --apply: blank + quarantine bad ones)")
    args = ap.parse_args()
    if args.recheck:
        recheck(args.apply)
        return

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
                # Cached before the red-flag gate existed: re-judge it.
                flags = red_flags(p.get("title", ""), surname(p.get("authors", "")), rec["match"])
                if flags:
                    nears.append((p, {**rec["match"], "flags": flags}))
                else:
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

    # Never re-apply a DOI already rejected for this record.
    rejected = load_quarantine()
    for key in [k for k, m in hits.items() if (k, m["doi"].lower()) in rejected]:
        del hits[key]
    # One DOI won by two or more records is at most one of them (four ORI shark
    # attack reports all "recovered" the same Copeia note): hold them all.
    by_doi = Counter(m["doi"].lower() for m in hits.values())
    pool_by_key = {str(p.get("literature_id", "")).replace(".0", "") or (p.get("title") or "")[:80]: p
                   for p in pool}
    for key in [k for k, m in hits.items() if by_doi[m["doi"].lower()] > 1]:
        nears.append((pool_by_key.get(key, {"literature_id": key}),
                      {**hits.pop(key), "flags": ["DOI won by more than one record"]}))

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
                        "title_sim", "author_match", "red_flags", "decision"])
            for p, m in nears:
                w.writerow([p.get("literature_id"), p.get("year"),
                            (p.get("authors") or "")[:80],
                            (p.get("title") or "")[:140], m["doi"], m["title"],
                            m["year"], m["sim"], m["author_ok"],
                            "; ".join(m.get("flags", [])), ""])
        print(f"near-misses held for review: {len(nears):,} -> {REVIEW.name}")
        # The CSV is an intermediate. A review artefact is always a formatted
        # workbook, so build it here rather than leaving it as a manual step.
        import subprocess
        try:
            subprocess.run(["Rscript", "scripts/build_doi_review_xlsx.R",
                            str(REVIEW)], cwd=str(ROOT), check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"WARNING: could not build the xlsx ({e}); the CSV is valid")

    if not args.apply:
        print("\n(no --apply: nothing written to papers_data.json)")
        return

    # A recovered 10.5962 DOI resolves to a free Biodiversity Heritage Library
    # scan, so the paper is not a subscription problem and must not be assigned
    # to a team member. Mark the route explicitly: fetch_bhl_archive.py skips
    # every DOI-bearing row, so without this the recovered DOI would silently
    # remove these papers from the one harvester that can actually get them.
    # Track E, 2026-09-17: three DataCite prefixes whose DOIs carry a real
    # url/content field and resolve to free full text, so they belong here
    # rather than in the assignable (subscription) pool.
    FREE_FULLTEXT_PREFIXES = {
        "10.5962": "bhl",
        "10.5169": "datacite_free",   # e-periodica.ch (Birkhauser / SNSN)
        "10.21411": "datacite_free",  # Station Biologique de Roscoff (Cah. Biol. Mar.)
        "10.5281": "datacite_free",   # Zenodo
    }

    n = routed = 0
    # Everything below happens under an exclusive lock on a FRESHLY read copy,
    # not the one loaded at start-up. A separate process added 4 rows during
    # this pass on 2026-09-04; a naive read-modify-write would have erased them
    # with no error and no trace.
    from lib.papers_data_io import mutate
    with mutate() as papers:
        for p in papers:
            key = str(p.get("literature_id", "")).replace(".0", "") \
                or (p.get("title") or "")[:80]
            if key in hits and not (p.get("doi") or "").strip():
                p["doi"] = hits[key]["doi"]
                p["doi_source"] = "crossref_recovery_2026-09"
                n += 1

        # Route by DOI prefix across the WHOLE list, not only the rows this
        # pass recovered: 65 papers already carried a BHL DOI from earlier work
        # and were sitting in the assignable pool, where no subscription is
        # needed and no team member could have helped.
        for p in papers:
            doi = (p.get("doi") or "").strip().lower()
            route = FREE_FULLTEXT_PREFIXES.get(doi.split("/")[0]) if doi else None
            if route and p.get("acquisition_route") != route:
                p["acquisition_route"] = route
                routed += 1

    print(f"\napplied {n:,} recovered DOIs")
    print(f"  {routed:,} papers routed to free full text "
          f"(acquisition_route bhl / datacite_free) rather than the "
          f"assignable pool")
    print("NOTE: run the sync's Phase 3b DOI verification over these before "
          "the download helper links to any of them.")


if __name__ == "__main__":
    main()
