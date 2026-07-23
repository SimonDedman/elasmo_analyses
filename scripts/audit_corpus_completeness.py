#!/usr/bin/env python3
"""
audit_corpus_completeness.py
============================
Generic, reusable corpus-completeness audit for the EEA 2025 Data Panel.

Quantifies, across MANY authors, how many of their (OpenAlex-attributed) works are
missing from (a) OUR corpus, (b) OUR download pile, and (c) Shark-References (SR).
This proves/quantifies that SR is NOT a complete source of truth for shark papers,
and produces actionable acquire / contribute-back lists.

Buckets per author-work:
    IN_CORPUS      title/DOI matches a parquet row (int-normalised ids)
    IN_PILE        matches docs/papers_data.json download pile
    C  (SR_MISSED) not in our system, but PRESENT in SR listByAuthor -> we should acquire
    D  (NOT_IN_SR) not in our system AND absent from SR -> SR itself is incomplete
                     D1 = likely-shark (SR would want it)
                     D2 = prey / out-of-scope (dolphin/dugong/turtle/marine-mammal...)

Method notes (learned the hard way, obeyed here):
  * literature_id is FLOAT in openalex CSVs but STRING in parquet -> int-normalise before join.
  * SR endpoint = https://shark-references.com/literature/listByAuthor/<Surname>-<Initials>./
    (trailing slash, follow redirects). Multiple initials forms are unioned for recall.
  * Match by TITLE (normalised fuzzy, difflib ratio>=0.72, year +/-2), NOT DOI: SR often
    lists a different DOI than the author's CV/OpenAlex.
  * gsearch endpoint is JS-only -> never used.
  * OpenAlex works API is free/no-key; author full works via cursor pagination.
  * Polite: 3-10 s jitter between SR requests, descriptive User-Agent, responses cached.

Usage:
    python scripts/audit_corpus_completeness.py --top-n 30
    python scripts/audit_corpus_completeness.py --author-id A5056604056
    python scripts/audit_corpus_completeness.py --top-n 50 --min-papers 20

Outputs:
    outputs/corpus_completeness_audit.csv     one row per author-work with bucket
    outputs/corpus_completeness_summary.csv   per-author bucket counts + gap rates
    Cache: outputs/.audit_cache/openalex/*.json , outputs/.audit_cache/sr/*.html
"""

import argparse
import json
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

# rapidfuzz.fuzz.ratio (0-100) is the normalised Indel similarity: it closely tracks
# difflib SequenceMatcher.ratio()*100 but runs ~100x faster (C-level, batched process.*).
# score_cutoff=72 reproduces the validated ratio>=0.72 threshold (heuristic anyway).
FUZZ_CUTOFF = 72.0

# ----------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNIQUE_AUTHORS = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"
PARQUET = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
PILE_JSON = PROJECT_ROOT / "docs" / "papers_data.json"

CACHE_DIR = PROJECT_ROOT / "outputs" / ".audit_cache"
OA_CACHE = CACHE_DIR / "openalex"
SR_CACHE = CACHE_DIR / "sr"
AUDIT_CSV = PROJECT_ROOT / "outputs" / "corpus_completeness_audit.csv"
SUMMARY_CSV = PROJECT_ROOT / "outputs" / "corpus_completeness_summary.csv"

USER_AGENT = "EEA2025-CorpusCompletenessAudit/1.0 (mailto:simondedman@gmail.com; shark literature review)"
HEADERS = {"User-Agent": USER_AGENT}

# ----------------------------------------------------------------------------- relevance keywords
# Chondrichthyan / elasmobranch relevance (title-level). OpenAlex topic used as backup.
SHARK_KEYWORDS = [
    "shark", "elasmobranch", "chondrichthy", "batoid", "ray ", " ray", "rays", "skate",
    "sawfish", "guitarfish", "stingray", "stingrays", "dogfish", "chimaera", "chimaeras",
    "holocephal", "selachi", "carcharhin", "sphyrna", "hammerhead", "requiem shark",
    "wobbegong", "catshark", "houndshark", "angelshark", "numbfish", "electric ray",
    "eagle ray", "manta", "mobula", "devil ray", "torpedo ray",
]
# Prey / non-chondrichthyan predator-ecology subjects -> plausibly outside SR scope (D2)
PREY_KEYWORDS = [
    "dolphin", "dugong", "turtle", "marine mammal", "cetacean", "manatee", "sea snake",
    "seabird", "sea bird", "seagrass", "sea grass", "porpoise", "whale", "pinniped",
    "seal ", "sea lion", "crocodile", "fish community", "teleost",
]
SHARK_TOPIC_HINTS = ["shark", "elasmobranch", "chondrichthy", "fisheries research", "ray"]


# ----------------------------------------------------------------------------- helpers
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_norm_re = re.compile(r"[^a-z0-9]+")


def norm_title(t: str) -> str:
    if not t:
        return ""
    t = strip_accents(str(t)).lower()
    t = _norm_re.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_doi(d):
    if not d or (isinstance(d, float) and pd.isna(d)):
        return ""
    d = str(d).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d.strip()


def int_norm_id(x):
    """Normalise a literature_id (float/str) to a bare-int string. '' if not parseable."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return ""
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


def fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return fuzz.ratio(a, b) / 100.0


def classify_relevance(title: str, topic_field: str, topic_name: str):
    """Return (is_shark, is_prey). Title keywords first, OpenAlex topic as backup."""
    tl = " " + norm_title(title) + " "
    topic_blob = f"{topic_field} {topic_name}".lower()
    is_shark = any(k.strip() in tl for k in SHARK_KEYWORDS) or any(
        h in topic_blob for h in ("shark", "elasmobranch", "chondrichthy")
    )
    is_prey = (not is_shark) and any(k in tl for k in PREY_KEYWORDS)
    return is_shark, is_prey


# ----------------------------------------------------------------------------- corpus / pile indices
class TitleIndex:
    """Year-bucketed normalised-title + DOI index for fast fuzzy lookup."""

    def __init__(self):
        self.by_doi = {}          # norm_doi -> id
        # int year -> (list[norm_title], list[id]) parallel arrays for rapidfuzz.process
        self.by_year = {}
        self.exact_title = {}     # norm_title -> id

    def add(self, ident, title, doi, year):
        nt = norm_title(title)
        nd = norm_doi(doi)
        if nd:
            self.by_doi.setdefault(nd, ident)
        if nt:
            self.exact_title.setdefault(nt, ident)
            try:
                yr = int(float(year))
            except (ValueError, TypeError):
                yr = None
            titles, ids = self.by_year.setdefault(yr, ([], []))
            titles.append(nt)
            ids.append(ident)

    def _candidates(self, yr, year_window):
        """Return (titles, ids) across the year window (plus the None-year bucket)."""
        if yr is None:
            titles, ids = [], []
            for t, i in self.by_year.values():
                titles.extend(t)
                ids.extend(i)
            return titles, ids
        titles, ids = [], []
        for cy in range(yr - year_window, yr + year_window + 1):
            b = self.by_year.get(cy)
            if b:
                titles.extend(b[0])
                ids.extend(b[1])
        # also allow undated corpus rows to match
        nb = self.by_year.get(None)
        if nb:
            titles.extend(nb[0])
            ids.extend(nb[1])
        return titles, ids

    def match(self, title, doi, year, cutoff=FUZZ_CUTOFF, year_window=2):
        nd = norm_doi(doi)
        if nd and nd in self.by_doi:
            return self.by_doi[nd], 1.0, "doi"
        nt = norm_title(title)
        if not nt:
            return None, 0.0, ""
        if nt in self.exact_title:
            return self.exact_title[nt], 1.0, "title_exact"
        try:
            yr = int(float(year))
        except (ValueError, TypeError):
            yr = None
        titles, ids = self._candidates(yr, year_window)
        if not titles:
            return None, 0.0, ""
        hit = process.extractOne(nt, titles, scorer=fuzz.ratio, score_cutoff=cutoff)
        if hit is None:
            return None, 0.0, ""
        _, score, pos = hit
        return ids[pos], score / 100.0, "title_fuzzy"


def build_corpus_index():
    df = pd.read_parquet(PARQUET, columns=["literature_id", "title", "doi", "year"])
    idx = TitleIndex()
    for row in df.itertuples(index=False):
        idx.add(int_norm_id(row.literature_id), row.title, row.doi, row.year)
    return idx, len(df)


def build_pile_index():
    data = json.loads(PILE_JSON.read_text())
    idx = TitleIndex()
    for rec in data:
        idx.add(int_norm_id(rec.get("literature_id")), rec.get("title"),
                rec.get("doi"), rec.get("year"))
    return idx, len(data)


# ----------------------------------------------------------------------------- OpenAlex
def fetch_openalex_works(author_id: str, delay=1.0):
    """Full works for an OpenAlex author id (bare 'A...'), cached to disk."""
    author_id = author_id.replace("https://openalex.org/", "").strip()
    cache_file = OA_CACHE / f"{author_id}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    OA_CACHE.mkdir(parents=True, exist_ok=True)
    works, cursor = [], "*"
    select = "id,doi,title,display_name,publication_year,primary_topic"
    while cursor:
        params = {
            "filter": f"author.id:{author_id}",
            "per-page": 200,
            "cursor": cursor,
            "select": select,
        }
        r = requests.get("https://api.openalex.org/works", params=params,
                         headers=HEADERS, timeout=60)
        r.raise_for_status()
        j = r.json()
        for w in j["results"]:
            pt = w.get("primary_topic") or {}
            works.append({
                "openalex_work_id": (w.get("id") or "").replace("https://openalex.org/", ""),
                "title": w.get("title") or w.get("display_name") or "",
                "year": w.get("publication_year"),
                "doi": norm_doi(w.get("doi")),
                "topic_name": pt.get("display_name") or "",
                "topic_field": (pt.get("field") or {}).get("display_name") or "",
            })
        cursor = j["meta"].get("next_cursor")
        if not j["results"]:
            break
        time.sleep(delay)
    cache_file.write_text(json.dumps(works))
    return works


# ----------------------------------------------------------------------------- Shark-References
def build_sr_name_variants(display_name: str, last_name: str):
    """Build Surname-Initials. URL slugs. Union of initial forms + accent-stripped."""
    last_name = (last_name or "").strip()
    display_name = (display_name or "").strip()
    if not last_name:
        return []
    # given-name portion = display_name with the last_name removed from its end
    given = display_name
    if display_name.lower().endswith(last_name.lower()):
        given = display_name[: len(display_name) - len(last_name)].strip()
    tokens = [t for t in re.split(r"[\s]+", given) if t]
    initials = []
    for tok in tokens:
        m = re.search(r"[A-Za-zÀ-ÿ]", tok)
        if m:
            initials.append(m.group(0).upper())
    variants = set()
    surnames = {last_name, strip_accents(last_name)}
    for sn in surnames:
        sn_slug = sn.strip()
        if initials:
            all_init = ".".join(initials) + "."
            first_init = initials[0] + "."
            variants.add(f"{sn_slug}-{all_init}")
            variants.add(f"{sn_slug}-{first_init}")
        else:
            variants.add(f"{sn_slug}-")
    return sorted(variants)


def fetch_sr_author(name_variant: str, delay_range=(3, 8)):
    """Fetch one SR listByAuthor page (cached). Returns list of (norm_title, year_or_None)."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name_variant)
    cache_file = SR_CACHE / f"{safe}.html"
    if cache_file.exists():
        html = cache_file.read_text()
    else:
        SR_CACHE.mkdir(parents=True, exist_ok=True)
        url = f"https://shark-references.com/literature/listByAuthor/{name_variant}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
            html = r.text if r.status_code == 200 else ""
        except requests.RequestException:
            html = ""
        cache_file.write_text(html)
        time.sleep(random.uniform(*delay_range))
    return parse_sr_html(html)


def parse_sr_html(html: str):
    entries = []
    if not html:
        return entries
    soup = BeautifulSoup(html, "html.parser")
    for div in soup.select("div.list-text"):
        auth_span = div.find("span", class_="lit-authors")
        if not auth_span:
            continue
        # year from the authors span, e.g. "... (2026)"
        ym = re.search(r"\((\d{4})\)", auth_span.get_text())
        year = int(ym.group(1)) if ym else None
        # TITLE = text between lit-authors span and lit-findspot span
        title_parts = []
        node = auth_span.next_sibling
        while node is not None:
            name = getattr(node, "name", None)
            if name == "span" and "lit-findspot" in (node.get("class") or []):
                break
            if name == "span" and "lit-authors" in (node.get("class") or []):
                break
            if isinstance(node, str):
                title_parts.append(node)
            elif name not in ("br",):
                title_parts.append(node.get_text(" "))
            node = node.next_sibling
        title = " ".join(title_parts)
        title = re.sub(r"DOI:.*$", "", title, flags=re.IGNORECASE).strip()
        nt = norm_title(title)
        if nt:
            entries.append((nt, year))
    return entries


def get_sr_titles(display_name, last_name):
    """Union SR titles across all name variants. Returns (list_of_(nt,year), n_variants_hit)."""
    variants = build_sr_name_variants(display_name, last_name)
    all_entries, hits = [], 0
    for v in variants:
        ent = fetch_sr_author(v)
        if ent:
            hits += 1
        all_entries.extend(ent)
    # de-dup by normalised title
    seen, deduped = set(), []
    for nt, yr in all_entries:
        if nt not in seen:
            seen.add(nt)
            deduped.append((nt, yr))
    return deduped, hits, variants


def match_in_sr(title, year, sr_entries, cutoff=FUZZ_CUTOFF, year_window=2):
    nt = norm_title(title)
    if not nt or not sr_entries:
        return False, 0.0
    try:
        yr = int(float(year))
    except (ValueError, TypeError):
        yr = None
    if yr is None:
        cands = [e[0] for e in sr_entries]
    else:
        cands = [e[0] for e in sr_entries
                 if e[1] is None or abs(e[1] - yr) <= year_window]
    if not cands:
        return False, 0.0
    hit = process.extractOne(nt, cands, scorer=fuzz.ratio)
    best = (hit[1] / 100.0) if hit else 0.0
    return best >= cutoff / 100.0, best


# ----------------------------------------------------------------------------- main audit
def select_authors(args, authors_df):
    if args.author_id:
        aid = args.author_id.replace("https://openalex.org/", "").strip()
        sub = authors_df[authors_df["openalex_author_id"].str.contains(aid, na=False)]
        if sub.empty:
            # allow auditing an id not in our unique-authors table
            return [{"openalex_author_id": f"https://openalex.org/{aid}",
                     "display_name": args.author_id, "last_name": "",
                     "paper_count": None}]
        return sub.to_dict("records")
    df = authors_df[authors_df["paper_count"] >= args.min_papers]
    df = df.sort_values("paper_count", ascending=False).head(args.top_n)
    return df.to_dict("records")


def run(args):
    print(f"[setup] Building corpus index from {PARQUET.name} ...", flush=True)
    corpus_idx, n_corpus = build_corpus_index()
    print(f"[setup] corpus rows indexed: {n_corpus}", flush=True)
    pile_idx, n_pile = build_pile_index()
    print(f"[setup] download-pile rows indexed: {n_pile}", flush=True)

    authors_df = pd.read_csv(UNIQUE_AUTHORS)
    authors = select_authors(args, authors_df)
    print(f"[setup] auditing {len(authors)} author(s)\n", flush=True)

    audit_rows = []
    summary_rows = []

    for i, a in enumerate(authors, 1):
        aid = str(a["openalex_author_id"]).replace("https://openalex.org/", "").strip()
        dname = a.get("display_name") or ""
        lname = a.get("last_name") or ""
        pcount = a.get("paper_count")
        print(f"[{i}/{len(authors)}] {dname} ({aid}) paper_count={pcount}", flush=True)

        try:
            works = fetch_openalex_works(aid)
        except Exception as e:  # noqa: BLE001
            print(f"    ! OpenAlex fetch failed: {e}", flush=True)
            continue
        print(f"    OpenAlex works: {len(works)}", flush=True)

        sr_entries, sr_hits, sr_variants = get_sr_titles(dname, lname)
        print(f"    SR titles: {len(sr_entries)} (variants hit {sr_hits}/{len(sr_variants)})",
              flush=True)

        counts = {k: 0 for k in
                  ["IN_CORPUS", "IN_PILE", "C_SR_MISSED", "D_NOT_IN_SR"]}
        shark_counts = dict(counts)
        d1 = d2 = 0  # D split among shark-relevant / prey
        n_shark = 0

        for w in works:
            is_shark, is_prey = classify_relevance(
                w["title"], w["topic_field"], w["topic_name"])
            if is_shark:
                n_shark += 1

            cid, cr, cmethod = corpus_idx.match(w["title"], w["doi"], w["year"])
            if cid is not None:
                bucket = "IN_CORPUS"
                sr_present, sr_r = None, None
                matched_id = cid
            else:
                pid, pr, pmethod = pile_idx.match(w["title"], w["doi"], w["year"])
                if pid is not None:
                    bucket = "IN_PILE"
                    sr_present, sr_r = None, None
                    matched_id = pid
                else:
                    sr_present, sr_r = match_in_sr(w["title"], w["year"], sr_entries)
                    bucket = "C_SR_MISSED" if sr_present else "D_NOT_IN_SR"
                    matched_id = ""

            counts[bucket] += 1
            if is_shark:
                shark_counts[bucket] += 1
            if bucket == "D_NOT_IN_SR":
                if is_shark:
                    d1 += 1
                elif is_prey:
                    d2 += 1

            d_class = ""
            if bucket == "D_NOT_IN_SR":
                d_class = "D1_likely_shark" if is_shark else ("D2_prey_out_of_scope"
                                                              if is_prey else "D3_ambiguous")

            audit_rows.append({
                "author_openalex_id": aid,
                "author_display_name": dname,
                "author_paper_count": pcount,
                "openalex_work_id": w["openalex_work_id"],
                "title": w["title"],
                "year": w["year"],
                "doi": w["doi"],
                "topic_field": w["topic_field"],
                "topic_name": w["topic_name"],
                "is_shark_relevant": is_shark,
                "is_prey_flagged": is_prey,
                "bucket": bucket,
                "d_class": d_class,
                "matched_literature_id": matched_id,
                "sr_variants_hit": sr_hits,
                "sr_best_ratio": round(sr_r, 3) if sr_r is not None else "",
            })

        total = len(works)
        summary_rows.append({
            "author_openalex_id": aid,
            "author_display_name": dname,
            "author_paper_count": pcount,
            "openalex_works": total,
            "shark_relevant_works": n_shark,
            "in_corpus": counts["IN_CORPUS"],
            "in_pile": counts["IN_PILE"],
            "C_sr_missed": counts["C_SR_MISSED"],
            "D_not_in_sr": counts["D_NOT_IN_SR"],
            "D1_likely_shark": d1,
            "D2_prey_out_of_scope": d2,
            "shark_in_corpus": shark_counts["IN_CORPUS"],
            "shark_C_sr_missed": shark_counts["C_SR_MISSED"],
            "shark_D_not_in_sr": shark_counts["D_NOT_IN_SR"],
            "corpus_gap_pct": round(100 * (total - counts["IN_CORPUS"]) / total, 1) if total else 0,
            "sr_gap_pct": round(100 * counts["D_NOT_IN_SR"] / total, 1) if total else 0,
            "sr_variants_hit": sr_hits,
            "sr_lookup_ok": sr_hits > 0,
        })
        s = summary_rows[-1]
        print(f"    -> corpus {s['in_corpus']} | pile {s['in_pile']} | "
              f"C(SR missed) {s['C_sr_missed']} | D(not in SR) {s['D_not_in_sr']} "
              f"(D1 {d1}/D2 {d2})\n", flush=True)

    # ------------------------------------------------------------------- write outputs
    audit_df = pd.DataFrame(audit_rows)
    summary_df = pd.DataFrame(summary_rows)
    audit_df.to_csv(AUDIT_CSV, index=False)
    summary_df.to_csv(SUMMARY_CSV, index=False)

    print_headline(audit_df, summary_df)
    print(f"\n[done] wrote {AUDIT_CSV.relative_to(PROJECT_ROOT)} ({len(audit_df)} rows)")
    print(f"[done] wrote {SUMMARY_CSV.relative_to(PROJECT_ROOT)} ({len(summary_df)} rows)")


def print_headline(audit_df, summary_df):
    if audit_df.empty:
        print("\n[headline] no works audited.")
        return
    total = len(audit_df)
    shark = audit_df[audit_df["is_shark_relevant"]]
    n_shark = len(shark)

    def pct(n, d):
        return f"{100 * n / d:.1f}%" if d else "n/a"

    d_all = (audit_df["bucket"] == "D_NOT_IN_SR").sum()
    not_corpus_all = (audit_df["bucket"] != "IN_CORPUS").sum()
    d1 = ((audit_df["bucket"] == "D_NOT_IN_SR") & audit_df["is_shark_relevant"]).sum()
    d2 = ((audit_df["bucket"] == "D_NOT_IN_SR") & audit_df["is_prey_flagged"]).sum()
    d3 = d_all - d1 - d2

    ds_corpus = (shark["bucket"] != "IN_CORPUS").sum()
    ds_D = (shark["bucket"] == "D_NOT_IN_SR").sum()
    ds_C = (shark["bucket"] == "C_SR_MISSED").sum()

    print("\n" + "=" * 72)
    print("HEADLINE  -  corpus completeness audit")
    print("=" * 72)
    print(f"Authors audited              : {len(summary_df)}")
    print(f"OpenAlex works checked (all) : {total}")
    print(f"  of which shark-relevant    : {n_shark} ({pct(n_shark, total)})")
    print("-" * 72)
    print("ALL works:")
    print(f"  not in OUR corpus          : {not_corpus_all} ({pct(not_corpus_all, total)})")
    print(f"  in SR but we missed (C)    : {(audit_df['bucket']=='C_SR_MISSED').sum()} "
          f"({pct((audit_df['bucket']=='C_SR_MISSED').sum(), total)})")
    print(f"  NOT in SR at all (D)       : {d_all} ({pct(d_all, total)})")
    print(f"      D1 likely-shark        : {d1}")
    print(f"      D2 prey/out-of-scope   : {d2}")
    print(f"      D3 ambiguous           : {d3}")
    print("-" * 72)
    print("SHARK-RELEVANT works only:")
    print(f"  not in OUR corpus          : {ds_corpus} ({pct(ds_corpus, n_shark)})")
    print(f"  in SR but we missed (C)    : {ds_C} ({pct(ds_C, n_shark)})")
    print(f"  NOT in SR at all (D=D1)    : {ds_D} ({pct(ds_D, n_shark)})")
    print("=" * 72)

    # top authors by SR-gap (D count), SR lookup must have worked
    ok = summary_df[summary_df["sr_lookup_ok"]].copy()
    top = ok.sort_values("D_not_in_sr", ascending=False).head(15)
    print("\nTop authors by SR-gap (D = works absent from Shark-References):")
    print(f"  {'author':30s} {'works':>5s} {'corpus':>6s} {'C':>3s} {'D':>3s} {'D1':>3s} {'D2':>3s}")
    for _, r in top.iterrows():
        print(f"  {str(r['author_display_name'])[:30]:30s} {r['openalex_works']:5d} "
              f"{r['in_corpus']:6d} {r['C_sr_missed']:3d} {r['D_not_in_sr']:3d} "
              f"{r['D1_likely_shark']:3d} {r['D2_prey_out_of_scope']:3d}")


def main():
    ap = argparse.ArgumentParser(description="Generic corpus-completeness audit (OpenAlex vs corpus vs SR).")
    ap.add_argument("--top-n", type=int, default=30,
                    help="Audit the N most-prolific authors (default 30).")
    ap.add_argument("--min-papers", type=int, default=10,
                    help="Only consider authors with >= this OpenAlex paper_count (default 10).")
    ap.add_argument("--author-id", type=str, default=None,
                    help="Audit a single OpenAlex author id (e.g. A5056604056).")
    args = ap.parse_args()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    run(args)


if __name__ == "__main__":
    main()
