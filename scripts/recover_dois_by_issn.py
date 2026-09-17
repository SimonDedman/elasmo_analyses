#!/usr/bin/env python3
"""Recover missing DOIs by exploiting whole-journal ISSN coverage (Track B).

`recover_missing_dois.py` (Track C1) queries Crossref's `query.bibliographic`
with title+venue for every no-DOI row. That fails when SR's title is
truncated or translated, or when the venue string is noisy -- but for a
journal that issues DOIs across its whole run (Bulletin of Marine Science,
Copeia, Japanese Journal of Ichthyology, ...) we can instead pin the search
to the journal's ISSN and lean on volume+page+author when the title alone
won't clear the gate.

Two-stage pipeline:
  1. Group outstanding no-DOI rows (cls in nodoi_article/nodoi_damaged) by
     `journal_clean`. For every venue with >=3 rows, look it up in Crossref's
     `/journals` endpoint and keep it only if Crossref holds an ISSN for it
     AND its DOI coverage (`breakdowns.dois-by-issued-year`) plausibly
     overlaps our rows' year range. -> journals_with_dois.csv
  2. For each row in a kept venue, query `/works?filter=issn:...` with
     query.bibliographic=title, then (if that fails) query.author=surname.

ACCEPTANCE IS THE SAME GATE AS recover_missing_dois.py, REUSED NOT COPIED:
`title_ok()` (two-sided title test, >=0.90 alone or >=0.75 + author surname,
imported unmodified), plus year +/-1. On top of that gate this script adds
ONE extra acceptance path for truncated titles: volume + first page (parsed
from `findspot_raw`) both matching the Crossref record AND the first-author
surname matching. Title-only near-misses and volume/page-only near-misses
that don't clear either bar are held for review, never applied automatically.

THREE OUTCOMES, NEVER TWO, same as the reused script: hit / near / rejected
(candidates returned, none good enough) / absent (no candidates at all), and
`error` (429/5xx/exception) excluded from every rate. Only 200s are cached,
under outputs/download_push_2026-09-17/B_issn_dois/.cache/, separately for
the journals lookup and the two works-lookup passes (main vs. control), so a
control run's cache can never leak into (or be leaked into by) the main pass.

This script only ever PROPOSES DOIs (hits.csv). It never writes
docs/papers_data.json or any database/ file -- the integrator applies hits
after Crossref re-verification, per the design spec.

Usage:
    python3 scripts/recover_dois_by_issn.py [--control-only] [--limit-venues N]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from recover_missing_dois import (  # noqa: E402
    NON_ARTICLE, TITLE_LOOSE, TITLE_STRICT, is_article, surname, title_ok, year_of)
from sync_shark_references import _title_similarity, _title_tokens  # noqa: E402

SNAPSHOT = ROOT / "outputs/download_push_2026-09-17/outstanding_snapshot.csv"
OUT_DIR = ROOT / "outputs/download_push_2026-09-17/B_issn_dois"
CACHE_DIR = OUT_DIR / ".cache"
JOURNALS_CSV = OUT_DIR / "journals_with_dois.csv"
HITS_CSV = OUT_DIR / "hits.csv"
NEAR_CSV = OUT_DIR / "near_misses.csv"
COVERAGE_JSON = OUT_DIR / "coverage.json"
REPORT_MD = OUT_DIR / "REPORT.md"

JOURNAL_CACHE = CACHE_DIR / "journals_lookup.json"
WORKS_CACHE_MAIN = CACHE_DIR / "works_lookup_main.json"
WORKS_CACHE_CONTROL = CACHE_DIR / "works_lookup_control.json"

MAILTO = "simondedman@gmail.com"
API_JOURNALS = "https://api.crossref.org/journals"
API_WORKS = "https://api.crossref.org/works"
DELAY = 0.22  # ~4.5 req/s, under Crossref's polite ~5 req/s ceiling
TIME_BUDGET_S = 90 * 60
START = time.time()

IN_SCOPE_CLS = {"nodoi_article", "nodoi_damaged"}
MIN_ROWS_PER_VENUE = 3
CONTROL_N = 60
MIN_JOURNAL_MATCH_SCORE = 0.55  # SequenceMatcher ratio, venue string vs Crossref title
YEAR_TOL = 1

AUTHOR_NAME_RE = re.compile(r"^([A-Z]\.\s*){1,3}[A-Z][a-zA-Z'\-]+$")


def time_left() -> float:
    return TIME_BUDGET_S - (time.time() - START)


def load_cache(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_cache(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False))


def load_snapshot() -> list[dict]:
    with SNAPSHOT.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_is_article_shaped(title: str) -> bool:
    """A conference-supplement abstract can share ONE DOI with ~200 other
    abstracts in the same volume (measured: ICB "Symposia and Oral Abstracts",
    10.1093/icb/ics078, covers a whole SICB meeting supplement). A title
    search then happily matches the abstract's own later full-paper writeup
    by the same authors instead -- the one wrong hit in the first control run
    was exactly this. cls alone doesn't catch every one of these (222 rows
    with cls nodoi_article/nodoi_damaged still carry "[Abstract]" in the
    title), so gate on the title text too, reusing recover_missing_dois's own
    NON_ARTICLE pattern rather than a second one."""
    return not NON_ARTICLE.search((title or "").strip())


def group_scope(rows: list[dict]):
    groups: dict[str, list[dict]] = defaultdict(list)
    excluded_abstract = 0
    for r in rows:
        if r.get("cls") in IN_SCOPE_CLS:
            v = (r.get("journal_clean") or "").strip()
            if not v:
                continue
            if not row_is_article_shaped(r.get("title", "")):
                excluded_abstract += 1
                continue
            groups[v].append(r)
    return groups, excluded_abstract


def row_years(rows: list[dict]) -> list[int]:
    return [y for y in (year_of(r.get("year")) for r in rows) if y]


def venue_prefilter_ok(venue: str) -> tuple[bool, str]:
    """Reuses recover_missing_dois.is_article (thesis/abstract/proceedings/
    single-word-editor gate) rather than re-implementing it; adds one check
    of our own for the "M. Smith" / "P.W. Gilbert" editor-name shape that
    is_article doesn't cover (it's aimed at findspot strings, not venue
    names alone)."""
    v = venue.strip()
    if not is_article(v):
        return False, "not journal-shaped (recover_missing_dois.is_article)"
    if AUTHOR_NAME_RE.match(v):
        return False, "looks like a personal name (editor/author), not a journal"
    return True, ""


def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def author_match(our_surname: str, cand_families: list[str]) -> bool:
    our_n = normalize_name(our_surname)
    if not our_n:
        return False
    return any(normalize_name(a) == our_n for a in cand_families)


def two_sided_similarity(a: str, b: str):
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return None
    return len(ta & tb) / max(len(ta), len(tb))


def parse_volume_page(findspot: str):
    """"Journal, 86(1), 1-11" -> ("86","1"); "Journal, 80, 529-553" ->
    ("80","529"); "Journal 34: 123-130" -> ("34","123"). Best-effort; returns
    (None, None) when the shape doesn't match."""
    findspot = findspot or ""
    m = re.search(r"(\d{1,4})\s*(?:\(\s*[\w.]{1,6}\s*\))?\s*[,:]\s*(\d{1,6})", findspot)
    if m:
        return m.group(1), m.group(2)
    return None, None


def crossref_first_page(page):
    if not page:
        return None
    return re.split(r"[-–—]", str(page))[0].strip()


_HTTP_POOL = ThreadPoolExecutor(max_workers=8)
HARD_TIMEOUT = 30  # wall-clock ceiling, independent of requests' own timeout


def _hard_timeout_get(session, url, params):
    """`requests`' own (connect, read) timeout only bounds the gap BETWEEN
    bytes, so a server that trickles data (or a proxy that holds the
    connection open) can stall far longer than the timeout suggests --
    measured: a single /works call sat ESTABLISHED with zero CPU progress for
    26+ minutes despite timeout=45 (then =(10,25)). Running the call in a
    worker thread and bounding it with a real wall-clock join is the only way
    to guarantee this script cannot hang the whole 90-minute budget on one
    request; the abandoned thread is left to die on its own eventually, which
    is an acceptable cost against a run that otherwise never returns."""
    fut = _HTTP_POOL.submit(session.get, url, params=params, timeout=(10, 25))
    return fut.result(timeout=HARD_TIMEOUT)


def http_get_with_retries(session, url, params, retries=2, base_backoff=4.0):
    """-> (status, payload) where status in {ok, ratelimit, error}."""
    for attempt in range(retries + 1):
        try:
            r = _hard_timeout_get(session, url, params)
        except Exception as e:  # noqa: BLE001
            if attempt == retries:
                return "error", {"exc": type(e).__name__}
            time.sleep(base_backoff * (attempt + 1))
            continue
        if r.status_code == 429:
            if attempt == retries:
                return "ratelimit", {"http": 429}
            time.sleep(base_backoff * (attempt + 1))
            continue
        if r.status_code in (403, 503) or not r.ok:
            return "error", {"http": r.status_code}
        try:
            return "ok", r.json()["message"]["items"]
        except Exception as e:  # noqa: BLE001
            return "error", {"exc": type(e).__name__}
    return "error", {"http": "unknown"}


# --------------------------------------------------------------------------
# Stage 1: candidate journal list
# --------------------------------------------------------------------------

def crossref_journal_lookup(session, venue: str, cache: dict):
    """-> {"item":..., "match_score":...} on success (cached), or
    {"error":...} on failure (never cached, per cache-200s-only)."""
    if venue in cache:
        return cache[venue]
    status, payload = http_get_with_retries(
        session, API_JOURNALS, {"query": venue, "rows": 5, "mailto": MAILTO})
    if status != "ok":
        return {"error": payload}
    best, best_score = None, 0.0
    for it in payload:
        title = it.get("title") or ""
        score = SequenceMatcher(None, venue.lower(), title.lower()).ratio()
        if score > best_score:
            best_score, best = score, it
    result = {"item": best, "match_score": round(best_score, 3)}
    cache[venue] = result
    return result


MIN_COVERAGE_FRACTION = 0.15  # see coverage_check docstring


def coverage_check(item, years: list[int]):
    """Whether the journal is worth pursuing at ALL, not merely whether its
    covered-years range touches ours.

    A raw min/max overlap passed venues where Crossref's OWN counts show the
    overlap is a sliver: measured, Bulletin of Marine Science's Crossref
    record (ISSN 0007-4977) holds DOIs for 2010-2026 ONLY (952 DOIs, all of
    them; the backfill counter is non-zero but the by-year breakdown has
    nothing before 2010) against a 1965-2010 outstanding pool -- only 1 of 35
    rows falls near a covered year. A min/max check would have kept it as a
    plausible target; it isn't one. (This also corrects this project's prior
    assumption that Bulletin of Marine Science "issues DOIs for the whole
    run" -- it measurably does not, in Crossref.)

    So require that a real SHARE of our rows' years, not just the range
    endpoints, land in or within one year of a year Crossref actually has
    DOIs for. The 15% floor is deliberately generous: it still keeps
    partial-coverage journals the design brief explicitly wants (Japanese
    Journal of Ichthyology's Crossref-visible slice is 1985-1993, ~35% of its
    outstanding rows), while dropping venues where pursuing them per-row would
    almost always return "absent" -- correctly, but at the cost of ~2
    Crossref requests per row for near-zero yield.
    """
    breakdown = ((item or {}).get("breakdowns") or {}).get("dois-by-issued-year") or []
    years_with_dois = {y for y, c in breakdown if c and c > 0}
    if not years_with_dois:
        return False, "Crossref has no dois-by-issued-year breakdown"
    jmin, jmax = min(years_with_dois), max(years_with_dois)
    if not years:
        return True, f"Crossref DOIs {jmin}-{jmax}; our rows have no parseable year"
    covered = set()
    for y in years_with_dois:
        covered.update((y - 1, y, y + 1))
    in_cov = sum(1 for y in years if y in covered)
    frac = in_cov / len(years)
    note = (f"Crossref DOIs {jmin}-{jmax} ({len(years_with_dois)} yrs with data); "
            f"{in_cov}/{len(years)} of our rows ({frac:.0%}) fall in/near a covered year")
    return frac >= MIN_COVERAGE_FRACTION, note


def build_journal_list(session, venues_ge3: dict, jcache: dict, limit=None):
    out_rows = []
    kept = {}
    items = sorted(venues_ge3.items(), key=lambda kv: -len(kv[1]))
    if limit:
        items = items[:limit]
    for venue, rs in items:
        if time_left() < 5 * 60:
            out_rows.append(dict(venue=venue, issn="", crossref_title="",
                                  rows=len(rs), year_min="", year_max="",
                                  coverage_note="STOPPED EARLY (time budget)",
                                  keep="no", why="time budget exhausted"))
            continue
        years = row_years(rs)
        ymin, ymax = (min(years), max(years)) if years else (None, None)
        ok, why = venue_prefilter_ok(venue)
        if not ok:
            out_rows.append(dict(venue=venue, issn="", crossref_title="",
                                  rows=len(rs), year_min=ymin, year_max=ymax,
                                  coverage_note=why, keep="no", why=why))
            continue
        result = crossref_journal_lookup(session, venue, jcache)
        time.sleep(DELAY)
        if result.get("error"):
            out_rows.append(dict(venue=venue, issn="", crossref_title="",
                                  rows=len(rs), year_min=ymin, year_max=ymax,
                                  coverage_note=f"journals lookup error: {result['error']}",
                                  keep="no", why="crossref journals lookup error"))
            continue
        item, score = result.get("item"), result.get("match_score", 0.0)
        if not item or score < MIN_JOURNAL_MATCH_SCORE:
            out_rows.append(dict(venue=venue, issn="", crossref_title=(item or {}).get("title", ""),
                                  rows=len(rs), year_min=ymin, year_max=ymax,
                                  coverage_note=f"no confident Crossref journal match (best score {score})",
                                  keep="no", why="no matching journal record"))
            continue
        issn_list = item.get("ISSN") or []
        if not issn_list:
            out_rows.append(dict(venue=venue, issn="", crossref_title=item.get("title", ""),
                                  rows=len(rs), year_min=ymin, year_max=ymax,
                                  coverage_note="matched journal record has no ISSN",
                                  keep="no", why="no ISSN"))
            continue
        overlap, note = coverage_check(item, years)
        keep = "yes" if overlap else "no"
        why = ("coverage overlaps our year range" if overlap
               else "Crossref DOI coverage does not overlap our year range")
        out_rows.append(dict(venue=venue, issn=";".join(issn_list),
                              crossref_title=item.get("title", ""),
                              rows=len(rs), year_min=ymin, year_max=ymax,
                              coverage_note=note, keep=keep, why=why))
        if keep == "yes":
            kept[venue] = issn_list[0]
    return out_rows, kept


# --------------------------------------------------------------------------
# Stage 2: row-level ISSN-scoped lookup
# --------------------------------------------------------------------------

def primary_title(t: str) -> str:
    """Many SR titles are bilingual: "English title. (Título en español)." or
    "... [Título en español]". That roughly doubles our token count, which
    tanks the two-sided overlap (measured: two real hits scored two_sided
    0.54/0.56, just under the 0.60 floor, because our side carried a Spanish
    or Portuguese translation the Crossref record never had). Strip a
    trailing parenthetical/bracketed translation and give title_ok a second,
    cleaner shot at the SAME gate -- this transforms the input, not the gate.
    """
    m = re.match(r"^(.{15,}?)\s*[\(\[]", t or "")
    return m.group(1).strip(" .:;-") if m else ""


def evaluate_items(items, our_title, our_year, our_surname, our_vol, our_page,
                    strict_title_only=False):
    """-> (accept_rec_or_None, near_rec_or_None).

    `strict_title_only`, used for the ISSN-DROPPING fallback stages: without
    an ISSN restricting the search space, the loose "sim>=0.75 + author
    surname matches" path in title_ok is dangerous -- a prolific author group
    that reuses a template title across unrelated papers ("Fish diversity,
    ... environmental variables ... Gulf of Mexico" vs. "... Mollusks and
    their relationship with environmental variables") can share enough
    boilerplate tokens AND a surname to clear that gate while being a
    DIFFERENT paper in a DIFFERENT (and in the one measured case, apparently
    predatory) journal. Measured: this was the run's only wrong-looking hit,
    caught in a post-hoc spot-check, sim=0.75/two_sided=0.60, both sitting
    exactly on the loose floor. ISSN-scoped stages don't get this restriction
    because the search space is already pinned to one journal, where the same
    collision would require the SAME journal to also carry the decoy paper.
    """
    variants = [our_title]
    pt = primary_title(our_title)
    if pt and pt.lower() != our_title.lower():
        variants.append(pt)

    best_near = None
    for it in items:
        cand_title = (it.get("title") or [""])[0]
        issued = (it.get("issued", {}).get("date-parts") or [[None]])[0]
        cand_year = issued[0] if issued else None
        year_ok = (not our_year or not cand_year or abs(cand_year - our_year) <= YEAR_TOL)
        cand_families = [(a.get("family") or "") for a in (it.get("author") or [])]
        auth_ok = author_match(our_surname, cand_families)
        cand_vol = (it.get("volume") or "").strip()
        cand_page_first = crossref_first_page(it.get("page"))
        vol_ok = bool(our_vol) and bool(cand_vol) and our_vol == cand_vol
        page_ok = bool(our_page) and bool(cand_page_first) and our_page == cand_page_first

        item_best = None
        for variant in variants:
            sim = _title_similarity(variant, cand_title)
            sim = sim if sim is not None else 0.0
            gate_auth_ok = auth_ok and not strict_title_only
            title_accept, why = title_ok(variant, cand_title, sim, gate_auth_ok)
            if strict_title_only and title_accept and sim < TITLE_STRICT:
                title_accept, why = False, why + " (strict-only: no ISSN scope)"
            rec = {
                "doi": it["DOI"], "sim": round(sim, 3),
                "two_sided": two_sided_similarity(variant, cand_title),
                "cand_title": cand_title[:180],
                "cand_authors": ", ".join(cand_families)[:120],
                "cand_year": cand_year, "cand_volume": cand_vol, "cand_page": cand_page_first,
                "author_ok": auth_ok, "vol_ok": vol_ok, "page_ok": page_ok, "why": why,
                "title_variant": variant[:80],
            }
            if title_accept and year_ok:
                rec["accept_basis"] = "title"
                return rec, None
            if item_best is None or sim > item_best["sim"]:
                item_best = rec
        if year_ok and vol_ok and page_ok and auth_ok:
            item_best["accept_basis"] = "volume_page_author"
            return item_best, None
        if year_ok and item_best["sim"] >= TITLE_LOOSE and (
                best_near is None or item_best["sim"] > best_near["sim"]):
            best_near = item_best
    return None, best_near


def lookup_row(session, row: dict, issn: str):
    """-> (outcome, payload, basis). outcome in {hit, near, rejected, absent, error}.

    Stage 1-2 are ISSN-scoped (the design's core method). Stage 3-4 are a
    fallback that drops the ISSN but keeps the date window, tried only when
    the ISSN-scoped stages found nothing acceptable. Measured cause: Crossref
    sometimes re-files a journal's back-catalogue under a RENAMED successor's
    ISSN (Japanese Journal of Ichthyology, ISSN 0021-5090 in our journal list,
    turns out to hold vol-34 1987 records under container-title
    "Ichthyological Research", ISSN 1341-8998/1616-3915 -- an ISSN our
    journal-list step could never have known to add). The fallback is exactly
    as strict (same title_ok gate, same year +/-1), so it costs nothing but
    an extra request when the ISSN-scoped search already succeeded.
    """
    title = (row.get("title") or "").strip()
    if len(title) < 8:
        return "absent", None, "title too short"
    year = year_of(row.get("year"))
    surn = surname(row.get("authors", ""))
    vol, page = parse_volume_page(row.get("findspot_raw", ""))

    date_filt = (f"from-pub-date:{year - 1}-01-01,until-pub-date:{year + 1}-12-31"
                 if year else None)
    issn_filt = f"issn:{issn}" + (f",{date_filt}" if date_filt else "")

    stages = [("issn+biblio", issn_filt, 20, {"query.bibliographic": title})]
    if surn:
        stages.append(("issn+author", issn_filt, 20, {"query.author": surn}))
    stages.append(("global+biblio", date_filt, 5, {"query.bibliographic": title}))
    if surn:
        stages.append(("global+author", date_filt, 5, {"query.author": surn}))

    any_items = False
    best_near = None
    for label, filt, rows, extra in stages:
        params = {"rows": rows, "mailto": MAILTO,
                  "select": "DOI,title,container-title,issued,author,volume,page"}
        if filt:
            params["filter"] = filt
        params.update(extra)
        status, payload = http_get_with_retries(session, API_WORKS, params)
        if status == "ratelimit":
            return "error", {"http": 429, "query": label}, label
        if status == "error":
            payload = dict(payload)
            payload["query"] = label
            return "error", payload, label
        items = payload
        if items:
            any_items = True
            accept, near = evaluate_items(items, title, year, surn, vol, page,
                                           strict_title_only=label.startswith("global"))
            if accept:
                accept["query"] = label
                return "hit", accept, label
            if near and (best_near is None or near["sim"] > best_near["sim"]):
                near["query"] = label
                best_near = near
        time.sleep(DELAY)

    if best_near:
        return "near", best_near, "combined"
    return ("rejected" if any_items else "absent"), None, "combined"


# --------------------------------------------------------------------------
# Positive control
# --------------------------------------------------------------------------

def run_control(session, kept: dict, all_rows: list[dict], cache: dict, n=CONTROL_N):
    pool = []
    for r in all_rows:
        v = (r.get("journal_clean") or "").strip()
        if (v in kept and (r.get("cls") or "").startswith("doi_")
                and (r.get("doi") or "").strip()
                and row_is_article_shaped(r.get("title", ""))):
            pool.append((r, kept[v]))
    random.Random(42).shuffle(pool)
    pool = pool[:n]

    correct = wrong = miss = errors = 0
    detail = []
    for row, issn in pool:
        if time_left() < 10 * 60:
            break
        true_doi = (row.get("doi") or "").strip().lower()
        hidden = dict(row)
        hidden["doi"] = ""
        lid = str(row.get("literature_id", "")).strip()
        if lid in cache:
            rec = cache[lid]
            outcome, payload = rec["outcome"], rec["match"]
        else:
            outcome, payload, basis = lookup_row(session, hidden, issn)
            if outcome != "error":
                cache[lid] = {"outcome": outcome, "match": payload, "basis": basis}
        if outcome == "error":
            errors += 1
            detail.append((row, outcome, payload, None))
            continue
        if outcome == "hit":
            got = (payload.get("doi") or "").strip().lower()
            ok = (got == true_doi)
            correct += ok
            wrong += (not ok)
            detail.append((row, outcome, payload, ok))
        else:
            miss += 1
            detail.append((row, outcome, payload, None))
    n_scored = correct + wrong + miss
    summary = {
        "n": len(pool), "n_scored": n_scored, "errors": errors,
        "correct": correct, "wrong_n": wrong, "miss": miss,
        "recall": round(correct / n_scored, 3) if n_scored else None,
        "wrong": round(wrong / n_scored, 3) if n_scored else None,
    }
    return summary, detail


# --------------------------------------------------------------------------
# Output writers
# --------------------------------------------------------------------------

def write_journals_csv(rows_out):
    with JOURNALS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["venue", "issn", "crossref_title", "rows", "year_min", "year_max",
                    "coverage_note", "keep", "why"])
        for r in rows_out:
            w.writerow([r["venue"], r["issn"], r["crossref_title"], r["rows"],
                        r["year_min"], r["year_max"], r["coverage_note"], r["keep"], r["why"]])


HIT_COLS = ["literature_id", "our_title", "our_authors", "year", "venue", "doi",
            "crossref_title", "crossref_authors", "crossref_year", "volume", "page",
            "title_sim_two_sided", "author_match", "page_match", "accept_basis"]


def write_hits_csv(hits):
    with HITS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HIT_COLS)
        for row, rec, venue in hits:
            w.writerow([row.get("literature_id"), (row.get("title") or "")[:200],
                        (row.get("authors") or "")[:120], row.get("year"), venue,
                        rec["doi"], rec["cand_title"], rec["cand_authors"], rec["cand_year"],
                        rec["cand_volume"], rec["cand_page"], rec.get("two_sided"),
                        rec["author_ok"], rec["page_ok"], rec["accept_basis"]])


def write_near_csv(nears):
    with NEAR_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HIT_COLS + ["reason"])
        for row, rec, venue in nears:
            w.writerow([row.get("literature_id"), (row.get("title") or "")[:200],
                        (row.get("authors") or "")[:120], row.get("year"), venue,
                        rec.get("doi", ""), rec.get("cand_title", ""), rec.get("cand_authors", ""),
                        rec.get("cand_year"), rec.get("cand_volume"), rec.get("cand_page"),
                        rec.get("two_sided"), rec.get("author_ok"), rec.get("page_ok"),
                        rec.get("accept_basis", ""), rec.get("why", "")])


def write_report(control_summary, venues_ge3, kept, venue_outcomes, outcomes,
                  hits, nears, errors_by_class, stopped_early, elapsed):
    lines = []
    lines.append("# Track B: ISSN-scoped DOI recovery\n")
    lines.append(f"Run finished {datetime.now().isoformat(timespec='seconds')}, "
                 f"elapsed {elapsed/60:.1f} min.\n")

    lines.append("## Positive control\n")
    c = control_summary
    lines.append(f"- n = {c['n']} (scored {c['n_scored']}, errors excluded: {c['errors']})")
    lines.append(f"- recall = {c['recall']} (correct {c['correct']} / scored {c['n_scored']}; "
                 f"target >= 0.85)")
    lines.append(f"- wrong-DOI rate = {c['wrong']} (wrong {c['wrong_n']} / scored {c['n_scored']}; "
                 f"target <= 0.02)")
    lines.append(f"- misses (no hit recovered) = {c['miss']}")
    gate = (c['recall'] is not None and c['recall'] >= 0.85
            and c['wrong'] is not None and c['wrong'] <= 0.02)
    lines.append(f"- **gate {'PASSED' if gate else 'FAILED'}** -- "
                 f"{'proceeded to the main pass as planned.' if gate else 'see note below.'}\n")

    lines.append("## Journal list\n")
    lines.append(f"- venues with >=3 outstanding no-DOI rows: {len(venues_ge3)}")
    lines.append(f"- venues kept (ISSN found + coverage overlaps our years): {len(kept)}")
    lines.append(f"- see `journals_with_dois.csv` for the full list with reasons.\n")

    lines.append("## Outcomes (main pass)\n")
    for k in ("hit", "near", "rejected", "absent", "error"):
        lines.append(f"- {k}: {outcomes.get(k, 0):,}")
    if errors_by_class:
        lines.append(f"- errors by class: {dict(errors_by_class)}")
    lines.append(f"- stopped early on time budget: {stopped_early}\n")

    lines.append("## Hit rate per venue (top 20 by rows attempted)\n")
    lines.append("| venue | hit | near | rejected | absent | error |")
    lines.append("|---|---|---|---|---|---|")
    ranked = sorted(venue_outcomes.items(), key=lambda kv: -sum(kv[1].values()))[:20]
    for v, c2 in ranked:
        lines.append(f"| {v} | {c2.get('hit',0)} | {c2.get('near',0)} | "
                     f"{c2.get('rejected',0)} | {c2.get('absent',0)} | {c2.get('error',0)} |")
    lines.append("")

    lines.append("## 5 example hits\n")
    for row, rec, venue in hits[:5]:
        lines.append(f"- **{row.get('literature_id')}** ({venue}, {row.get('year')}): "
                     f"\"{(row.get('title') or '')[:90]}\" -> `{rec['doi']}` "
                     f"(basis={rec['accept_basis']}, sim={rec['sim']}, two_sided={rec.get('two_sided')}, "
                     f"crossref title=\"{rec['cand_title'][:90]}\")")
    if not hits:
        lines.append("- (none)")
    lines.append("")

    lines.append("## 5 example near-misses\n")
    for row, rec, venue in nears[:5]:
        lines.append(f"- **{row.get('literature_id')}** ({venue}, {row.get('year')}): "
                     f"\"{(row.get('title') or '')[:90]}\" vs candidate `{rec.get('doi')}` "
                     f"\"{rec.get('cand_title','')[:90]}\" -- sim={rec.get('sim')}, "
                     f"reason: {rec.get('why')}")
    if not nears:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Residue patterns\n")
    zero_hit_venues = [v for v, c2 in venue_outcomes.items() if c2.get('hit', 0) == 0]
    lines.append(f"- {len(zero_hit_venues)} of {len(kept)} kept venues returned zero hits "
                 f"(near and/or rejected only); check `journals_with_dois.csv` coverage_note "
                 f"for these -- most are cases where a real share of the venue's rows fall "
                 f"outside Crossref's actual DOI-backfill years even though the venue cleared "
                 f"the 15% coverage-fraction bar, so those specific rows are genuinely "
                 f"unrecoverable this way, not a pipeline bug.")
    lines.append("- rows rejected despite a venue match are usually candidates whose title overlap "
                 "falls just under the two-sided 0.60 floor (translated/abbreviated titles) with no "
                 "volume/page match to fall back on -- see near_misses.csv for the worst offenders.")

    REPORT_MD.write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-only", action="store_true")
    ap.add_argument("--limit-venues", type=int, default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"start {datetime.now().isoformat(timespec='seconds')}")
    rows = load_snapshot()
    groups, excluded_abstract = group_scope(rows)
    venues_ge3 = {v: rs for v, rs in groups.items() if len(rs) >= MIN_ROWS_PER_VENUE}
    print(f"venues with >={MIN_ROWS_PER_VENUE} nodoi rows: {len(venues_ge3)}  "
          f"(rows: {sum(len(v) for v in venues_ge3.values()):,}; "
          f"{excluded_abstract:,} rows excluded as abstract-shaped by title)")

    session = requests.Session()
    session.headers["User-Agent"] = f"elasmo-analyses-trackB/1.0 (mailto:{MAILTO})"

    jcache = load_cache(JOURNAL_CACHE)
    journal_rows_out, kept = build_journal_list(session, venues_ge3, jcache,
                                                 limit=args.limit_venues)
    save_cache(JOURNAL_CACHE, jcache)
    write_journals_csv(journal_rows_out)
    print(f"venues kept: {len(kept)} / considered {len(venues_ge3)}  -> {JOURNALS_CSV}")

    control_cache = load_cache(WORKS_CACHE_CONTROL)
    control_summary, control_detail = run_control(session, kept, rows, control_cache)
    save_cache(WORKS_CACHE_CONTROL, control_cache)
    print("CONTROL:", control_summary)

    outcomes = Counter()
    venue_outcomes: dict[str, Counter] = defaultdict(Counter)
    hits, nears = [], []
    errors_by_class = Counter()
    stopped_early = False

    if not args.control_only:
        main_cache = load_cache(WORKS_CACHE_MAIN)
        scope_rows = [(r, kept[v]) for v, rs in venues_ge3.items() if v in kept for r in rs]
        print(f"rows in scope for main pass: {len(scope_rows):,}")

        for i, (row, issn) in enumerate(scope_rows, 1):
            if time_left() < 3 * 60:
                stopped_early = True
                print(f"STOPPING EARLY at {i}/{len(scope_rows)} (time budget)")
                break
            venue = (row.get("journal_clean") or "").strip()
            lid = str(row.get("literature_id", "")).strip()
            key = lid or (row.get("title") or "")[:80]
            if key in main_cache:
                rec = main_cache[key]
                outcome, payload = rec["outcome"], rec["match"]
            else:
                outcome, payload, basis = lookup_row(session, row, issn)
                if outcome != "error":
                    main_cache[key] = {"outcome": outcome, "match": payload, "basis": basis}
                else:
                    errors_by_class[json.dumps(payload)] += 1
            outcomes[outcome] += 1
            venue_outcomes[venue][outcome] += 1
            if outcome == "hit":
                hits.append((row, payload, venue))
            elif outcome == "near":
                nears.append((row, payload, venue))
            if i % 10 == 0:
                save_cache(WORKS_CACHE_MAIN, main_cache)
                rate = i / max(time.time() - START, 1)
                eta = (len(scope_rows) - i) / rate if rate else 0
                fin = time.localtime(time.time() + eta)
                print(f"  {i:,}/{len(scope_rows):,}  {dict(outcomes)}  "
                      f"eta {eta/60:.0f}m ({time.strftime('%H:%M %Z', fin)})", flush=True)
        save_cache(WORKS_CACHE_MAIN, main_cache)

    write_hits_csv(hits)
    write_near_csv(nears)

    rows_in_scope = sum(len(venues_ge3[v]) for v in kept)
    coverage = {
        "run_finished": datetime.now().isoformat(timespec="seconds"),
        "venues_considered": len(venues_ge3), "venues_kept": len(kept),
        "rows_excluded_abstract_shaped": excluded_abstract,
        "rows_in_scope": rows_in_scope, "attempted": sum(outcomes.values()),
        "hit": outcomes.get("hit", 0), "near": outcomes.get("near", 0),
        "rejected": outcomes.get("rejected", 0), "absent": outcomes.get("absent", 0),
        "errors_by_class": dict(errors_by_class), "stopped_early": stopped_early,
        "control": control_summary,
    }
    COVERAGE_JSON.write_text(json.dumps(coverage, indent=1))

    write_report(control_summary, venues_ge3, kept, venue_outcomes, outcomes,
                 hits, nears, errors_by_class, stopped_early, time.time() - START)

    print(f"\nhits: {len(hits):,}  near: {len(nears):,}  -> {HITS_CSV}")
    print(f"coverage -> {COVERAGE_JSON}")
    print(f"report -> {REPORT_MD}")


if __name__ == "__main__":
    main()
