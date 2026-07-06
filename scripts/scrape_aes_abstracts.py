#!/usr/bin/env python3
"""
scrape_aes_abstracts.py
========================
Scrape the American Elasmobranch Society (AES) conference-abstract archive
at elasmo.org and match abstracts to the no-DOI entries in our download
queue (docs/papers_data.json) whose journal is "American Elasmobranch
Society" (conference abstracts ARE the acquirable content for these rows).

Site structure (inspected 2026-07 via curl/WebFetch, see notes below):
    Index:  https://elasmo.org/meetings/abstracts/
            lists one link per AES annual meeting, 1985-2016+.
    Old format (meeting years 1985-2005), e.g.:
            https://elasmo.org/abstracts/abst1994
            (redirects 301 -> https://elasmo.org/meetings/abstracts/abst1994/)
            Poster supplements exist for some years: abst2003p, abst2004p.
        HTML: a flat run of
            <article><address><b>SURNAME, First; ...</b><br/><i>affiliation</i></address>
            <p><cite><b>TITLE</b></cite></p>
            <blockquote><p>ABSTRACT TEXT</p></blockquote></article><hr/>
        This is the WordPress "old AES site" import and is very regular -- reliable
        to parse with BeautifulSoup by selecting <address> as the per-abstract anchor.

    New format (meeting years 2006-2015), e.g.:
            https://elasmo.org/abstracts/2006-aes-abstracts
        HTML: a flat run of plain <p> tags with NO consistent wrapper element:
            <p><strong>SURNAME, First; ...</strong></p>
            <p><em>affiliation</em></p>
            <p>Title (plain text, sentence case)</p>
            <p>Abstract text (long paragraph, can be >1 paragraph)</p>
        separated occasionally by bare section markers ("TALKS", "POSTERS").
        This is parsed with a best-effort paragraph state machine (see
        parse_new_format) -- there is no unambiguous per-abstract delimiter,
        so this path is lower-confidence than the old format and covers only
        a small fraction of our target rows (see distribution below).

    Year distribution of our 546 target rows (journal_clean == "American
    Elasmobranch Society", no DOI): 2005:124 2000:119 1996:84 2003:68
    1997:57 2004:41 1994:40 2009:4 2011:2 2010:2 2007:2 2008:1 2006:1 2001:1
    -> 532/546 (97.4%) are in OLD-format years; only 14/546 (2.6%) are in
    NEW-format years, so the old-format parser carries almost all the yield.

    BLOCKER (documented, not scraped): 171 further queue rows have
    journal_clean in {"Shark International (abstract)",
    "Programm and Poster abstracts of Shark International"}. Their source
    (sharksinternational.org.br) is DEAD (connection failure) and the
    fallback PDFs linked from elasmo.org/meetings/abstracts/ (JMIH program
    book, 2011 abstract book, "SI program.pdf") all 404. No known live
    source for these -- out of scope for this script.

Matching: normalise titles (strip accents, lowercase, alnum-only) and use
rapidfuzz.fuzz.ratio >= 72 (reproduces the difflib SequenceMatcher.ratio()>=0.72
threshold used elsewhere in this project, see audit_corpus_completeness.py),
restricted to same-year candidates, first-author surname compared as a
secondary confidence signal (logged, not required).

Usage:
    python scripts/scrape_aes_abstracts.py --limit 20      # test run
    python scripts/scrape_aes_abstracts.py                 # full run

Outputs:
    outputs/aes_abstracts/<literature_id>.txt   matched abstract text + header
    outputs/aes_abstract_matches.csv            literature_id, matched_title, year, abstract_chars
    outputs/.aes_cache/*.html                   cached fetched pages (resumable)

This script does NOT modify docs/papers_data.json.
"""

import argparse
import csv
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

FUZZ_CUTOFF = 72.0

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PILE_JSON = PROJECT_ROOT / "docs" / "papers_data.json"
CACHE_DIR = PROJECT_ROOT / "outputs" / ".aes_cache"
OUT_DIR = PROJECT_ROOT / "outputs" / "aes_abstracts"
MATCHES_CSV = PROJECT_ROOT / "outputs" / "aes_abstract_matches.csv"

USER_AGENT = (
    "EEA2025-DataPanel-AESAbstractScraper/1.0 "
    "(mailto:simondedman@gmail.com; academic literature review, polite crawl)"
)
HEADERS = {"User-Agent": USER_AGENT}
DELAY_RANGE = (3.0, 5.0)  # seconds between *uncached* requests

INDEX_URL = "https://elasmo.org/meetings/abstracts/"

# Old-format meeting years (WordPress-imported legacy AES site), talks+posters
# combined per year except where a separate poster page ("...p") exists.
OLD_FORMAT_YEARS = list(range(1985, 2006))
OLD_FORMAT_POSTER_SUFFIX_YEARS = {2003, 2004}

# New-format meeting years (native WordPress pages, paragraph-only markup).
NEW_FORMAT_YEARS = list(range(2006, 2016))


# ----------------------------------------------------------------------------- text helpers
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_norm_re = re.compile(r"[^a-z0-9]+")


def norm_title(t: str) -> str:
    if not t:
        return ""
    t = strip_accents(str(t)).lower()
    t = _norm_re.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_surname(s: str) -> str:
    if not s:
        return ""
    s = strip_accents(str(s)).lower()
    return re.sub(r"[^a-z]", "", s)


def first_author_surname_from_queue(authors_field: str) -> str:
    """Queue 'authors' format: 'Surname, F.M. & Surname2, F. (Year)' -> 'surname'."""
    if not authors_field:
        return ""
    first = authors_field.split("&")[0]
    surname = first.split(",")[0]
    return norm_surname(surname)


def first_author_surname_from_scraped(authors_raw: str) -> str:
    """Scraped address format: '*SURNAME, First; ...' / 'SURNAME, F., and OTHER' -> 'surname'."""
    if not authors_raw:
        return ""
    s = authors_raw.strip().lstrip("*").strip()
    s = re.sub(r"^\[.*?\]\s*", "", s)  # strip leading "[G]" grad-student markers etc.
    first = re.split(r"[;,]", s, maxsplit=1)[0]
    return norm_surname(first)


# ----------------------------------------------------------------------------- queue
def load_queue_targets(include_shark_international=False):
    import json

    data = json.loads(PILE_JSON.read_text())
    targets = []
    for p in data:
        doi = (p.get("doi") or "").strip()
        if doi:
            continue
        jc = (p.get("journal_clean") or p.get("journal") or "").strip().lower()
        is_aes = jc == "american elasmobranch society"
        is_si = jc in (
            "shark international (abstract)",
            "programm and poster abstracts of shark international",
        )
        if is_aes or (include_shark_international and is_si):
            targets.append(p)
    return targets


# ----------------------------------------------------------------------------- fetch (cached, polite)
def _cache_path(url: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")
    return CACHE_DIR / f"{safe}.html"


def fetch_cached(url: str, session: requests.Session):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(url)
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8", errors="replace"), True
    resp = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code == 404:
        cache_file.write_text("", encoding="utf-8")  # cache the miss too
        return "", False
    resp.raise_for_status()
    text = resp.text
    cache_file.write_text(text, encoding="utf-8")
    return text, False


# ----------------------------------------------------------------------------- parsers
def parse_old_format(html: str):
    """Yield dicts: authors_raw, title, abstract for the pre-2006 archive pages."""
    if not html:
        return
    soup = BeautifulSoup(html, "html.parser")
    for address in soup.find_all("address"):
        article = address.find_parent("article")
        container = article if article is not None else address.parent
        b_tag = address.find("b")
        authors_raw = (b_tag.get_text(" ", strip=True) if b_tag
                       else address.get_text(" ", strip=True))
        cite_tag = container.find("cite") if container else None
        title = cite_tag.get_text(" ", strip=True) if cite_tag else ""
        bq_tag = container.find("blockquote") if container else None
        abstract = bq_tag.get_text(" ", strip=True) if bq_tag else ""
        if not title or not abstract:
            continue
        yield {"authors_raw": authors_raw, "title": title, "abstract": abstract}


_SECTION_MARKERS = {"TALKS", "POSTERS", "POSTER SESSION", "TALK SESSION", "ORAL PRESENTATIONS"}


def _is_full_tag_paragraph(p, tagname):
    tag = p.find(tagname)
    if tag is None:
        return False
    tag_text = tag.get_text(" ", strip=True)
    full_text = p.get_text(" ", strip=True)
    if not tag_text or not full_text:
        return False
    return len(tag_text) >= 0.85 * len(full_text)


def parse_new_format(html: str):
    """Best-effort paragraph state machine for the 2006-2015 native WP pages.

    No unambiguous per-abstract delimiter exists in this markup (unlike the old
    format's <address>/<blockquote> structure), so this is heuristic: a
    paragraph that is *entirely* bolded (<strong>) starts a new abstract
    (author line), the next fully-italicised (<em>) paragraph is the
    affiliation, the next plain paragraph is the title, and subsequent plain
    paragraph(s) up to the next bolded line are the abstract body.
    """
    if not html:
        return
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", class_="field-item")
    if container is None:
        return
    paragraphs = container.find_all("p")

    current = None
    state = "expect_author"

    def flush(cur):
        if cur and cur.get("authors_raw") and cur.get("title") and cur.get("abstract_parts"):
            yield {
                "authors_raw": cur["authors_raw"],
                "title": cur["title"],
                "abstract": " ".join(cur["abstract_parts"]).strip(),
            }

    results = []
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if not text:
            continue
        if text.upper().strip(" .") in _SECTION_MARKERS:
            continue
        if _is_full_tag_paragraph(p, "strong"):
            if current is not None:
                results.extend(flush(current))
            current = {"authors_raw": text, "title": None, "abstract_parts": []}
            state = "expect_affil"
            continue
        if current is None:
            continue  # stray paragraph before the first author line
        if state == "expect_affil" and _is_full_tag_paragraph(p, "em"):
            state = "expect_title"
            continue
        if state in ("expect_affil", "expect_title") and current["title"] is None:
            current["title"] = text
            state = "expect_abstract"
            continue
        if state == "expect_abstract":
            current["abstract_parts"].append(text)
            continue

    if current is not None:
        results.extend(flush(current))
    yield from results


# ----------------------------------------------------------------------------- year -> URLs
def urls_for_year(year: int):
    urls = []
    if year in OLD_FORMAT_YEARS:
        urls.append((f"https://elasmo.org/abstracts/abst{year}", "old"))
        if year in OLD_FORMAT_POSTER_SUFFIX_YEARS:
            urls.append((f"https://elasmo.org/abstracts/abst{year}p", "old"))
    elif year in NEW_FORMAT_YEARS:
        urls.append((f"https://elasmo.org/abstracts/{year}-aes-abstracts", "new"))
    return urls


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=None,
                     help="Only process the first N queue target rows (for testing).")
    ap.add_argument("--include-shark-international", action="store_true",
                     help="Also attempt to match Shark International rows "
                          "(NOTE: source site is dead as of 2026-07, expect 0 matches).")
    ap.add_argument("--cutoff", type=float, default=FUZZ_CUTOFF,
                     help="rapidfuzz.fuzz.ratio threshold (0-100), default 72.")
    args = ap.parse_args()

    targets = load_queue_targets(include_shark_international=args.include_shark_international)
    print(f"[queue] {len(targets)} no-DOI AES{'+SI' if args.include_shark_international else ''} "
          f"rows loaded from {PILE_JSON.name}")

    if args.limit:
        targets = targets[: args.limit]
        print(f"[queue] --limit applied: processing first {len(targets)} rows")

    targets_by_year = {}
    for t in targets:
        try:
            y = int(t.get("year"))
        except (TypeError, ValueError):
            continue
        targets_by_year.setdefault(y, []).append(t)

    needed_years = sorted(targets_by_year)
    print(f"[queue] years needed: {needed_years}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    # ---- gather all abstracts for the needed years ----
    abstracts_by_year = {}
    fetched_live = 0
    for year in needed_years:
        year_abstracts = []
        for url, fmt in urls_for_year(year):
            html, from_cache = fetch_cached(url, session)
            if not from_cache:
                fetched_live += 1
                time.sleep(DELAY_RANGE[0] + (DELAY_RANGE[1] - DELAY_RANGE[0]) * 0.5)
            if not html:
                print(f"  [{year}] {url} -> 404 / empty, skipped")
                continue
            parser = parse_old_format if fmt == "old" else parse_new_format
            parsed = list(parser(html))
            print(f"  [{year}] {url} ({fmt}) -> {len(parsed)} abstracts parsed")
            year_abstracts.extend(parsed)
        abstracts_by_year[year] = year_abstracts

    # ---- match ----
    rows = []
    matched_ids = set()
    for year, cands in abstracts_by_year.items():
        qrows = targets_by_year.get(year, [])
        if not qrows or not cands:
            continue
        cand_norm_titles = [norm_title(c["title"]) for c in cands]
        for q in qrows:
            q_title_norm = norm_title(q.get("title"))
            if not q_title_norm:
                continue
            best_score, best_idx = 0.0, -1
            for idx, ct in enumerate(cand_norm_titles):
                if not ct:
                    continue
                score = fuzz.ratio(q_title_norm, ct)
                if score > best_score:
                    best_score, best_idx = score, idx
            if best_idx < 0 or best_score < args.cutoff:
                continue
            cand = cands[best_idx]
            q_surname = first_author_surname_from_queue(q.get("authors"))
            c_surname = first_author_surname_from_scraped(cand["authors_raw"])
            author_match = bool(q_surname) and q_surname == c_surname

            lit_id = q.get("literature_id")
            out_path = OUT_DIR / f"{lit_id}.txt"
            out_path.write_text(
                f"literature_id: {lit_id}\n"
                f"queue_title: {q.get('title')}\n"
                f"matched_title: {cand['title']}\n"
                f"year: {year}\n"
                f"authors_scraped: {cand['authors_raw']}\n"
                f"match_score: {best_score:.1f}\n"
                f"author_surname_match: {author_match}\n"
                f"\n{cand['abstract']}\n",
                encoding="utf-8",
            )
            rows.append({
                "literature_id": lit_id,
                "matched_title": cand["title"],
                "year": year,
                "abstract_chars": len(cand["abstract"]),
                "match_score": round(best_score, 1),
                "author_surname_match": author_match,
            })
            matched_ids.add(lit_id)

    MATCHES_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MATCHES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["literature_id", "matched_title", "year",
                                           "abstract_chars", "match_score",
                                           "author_surname_match"])
        w.writeheader()
        w.writerows(rows)

    print(f"\n[done] {fetched_live} pages fetched live, "
          f"{sum(len(v) for v in abstracts_by_year.values())} abstracts parsed across "
          f"{len(needed_years)} years")
    print(f"[done] {len(matched_ids)}/{len(targets)} queue rows matched "
          f"(cutoff={args.cutoff})")
    print(f"[done] abstracts written to {OUT_DIR}")
    print(f"[done] match log written to {MATCHES_CSV}")


if __name__ == "__main__":
    sys.exit(main())
