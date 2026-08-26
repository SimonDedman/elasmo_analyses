"""Harvest the AES abstracts hosted on elasmo.org (1985-2005) into the DB.

https://elasmo.org/meetings/abstracts/abst<YYYY>/ serves one HTML page per AES
annual meeting with FULL abstract bodies (probed 2026-08-25: 200 for
1985-2005, 404 for 1983-84 and 2006+). Each abstract is an <article> holding
<address><b>authors</b><br/><i>affiliation</i></address>,
<p><cite><b>title</b></cite></p>, <blockquote><p>body</p></blockquote>; an
<h3> before a run of articles names the section (oral / poster).

Author-string formats vary by year; every record keeps raw_author_string so
a later pass can re-split. Records whose split looks doubtful get needs_review.

Usage:
  scrape_elasmo_org.py --dry-run        # fetch (cached) + parse stats, no DB
  scrape_elasmo_org.py                  # load into config.DB_PATH
  scrape_elasmo_org.py --dedup          # after loading: drop JMIH-book copies of
                                        # the same AES abstracts (title match)
  scrape_elasmo_org.py --supersede      # then: in years elasmo.org covers, drop the
                                        # JMIH-book elasmo records that are AES-session
                                        # or needs_review (OCR-mangled titles defeat
                                        # the title match; elasmo.org is authoritative)

Only HTTP-200 pages containing <article> are cached (WEB-LOOKUPS rule: never
cache a failure).
"""
import argparse
import html as htmllib
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C, schema, load  # noqa: E402

YEARS = range(1985, 2006)
URL = "https://elasmo.org/meetings/abstracts/abst{y}/"
CACHE = C.OUT / "conf_abstracts" / "elasmo_org_html"
UA = {"User-Agent": "Mozilla/5.0 (elasmo_analyses conference-abstracts harvester; simondedman@gmail.com)"}

_TAG = re.compile(r"<[^>]+>")
_SUP = re.compile(r"<sup>.*?</sup>", re.S)
_WS = re.compile(r"\s+")


def clean(s: str, drop_sup=True) -> str:
    if drop_sup:
        s = _SUP.sub("", s)
    s = _TAG.sub(" ", s)
    s = htmllib.unescape(s)
    return _WS.sub(" ", s).strip()


def fetch(year: int) -> str | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"abst{year}.html"
    if p.exists() and p.stat().st_size > 1000:
        return p.read_text(encoding="utf-8")
    r = requests.get(URL.format(y=year), headers=UA, timeout=60)
    if r.status_code != 200 or "<article>" not in r.text:
        print(f"  {year}: HTTP {r.status_code}, {'no <article>' if r.status_code == 200 else ''} — NOT cached")
        return None
    p.write_text(r.text, encoding="utf-8")
    time.sleep(1.0)
    return r.text


# ---- author splitting -----------------------------------------------------
_INITIALS_LEAD = re.compile(r"^(?:[A-Z]\.\s*)+")          # "R.A. Roundtree"
_AND = re.compile(r"\s*,?\s+\b(?:and|AND|&)\b\s+")


def split_authors(raw: str):
    """Return (authors:list[dict], award:str|None, doubtful:bool)."""
    s = raw.strip()
    award = None
    m = re.match(r"^\[([A-Z])\]\s*", s)
    if m:
        award = {"G": "student (Gruber)"}.get(m.group(1), m.group(1))
        s = s[m.end():]
    s = s.rstrip(" .")
    # generational suffixes are not authors: glue ", Jr." / ", III" to the
    # preceding token so the Surname, Given pairing keeps its parity
    s = re.sub(r",\s*(Jr|Sr|II|III|IV)\.?(?=\s*(,|;|$|\s+and\b))", r" \1.", s)
    doubtful = False
    if ";" in s:
        parts = [p for p in re.split(r"\s*;\s*", _AND.sub("; ", s)) if p.strip(" ,")]
        names = [p.strip(" ,") for p in parts]
    else:
        s2 = _AND.sub(", ", s)
        toks = [t.strip() for t in s2.split(",") if t.strip()]
        if len(toks) <= 2:
            names = [", ".join(toks)] if toks else []
        elif _INITIALS_LEAD.match(toks[2].replace("*", "")) or toks[2].replace("*", "").isupper():
            # "Surname, I.I., I.I. Surname, I.I. Surname"
            names = [f"{toks[0]}, {toks[1]}"] + toks[2:]
        else:
            # "Surname, Given, Surname, Given, ..."
            names = [f"{toks[i]}, {toks[i + 1]}" for i in range(0, len(toks) - 1, 2)]
            if len(toks) % 2:
                names.append(toks[-1])
                doubtful = True
    authors = []
    for i, n in enumerate(names, start=1):
        pres = "*" in n
        n = n.replace("*", "").strip(" ,")
        if not n:
            continue
        authors.append(dict(full_name=n, position=i, is_presenter=int(pres),
                            raw_author_string=raw))
    if not authors:
        doubtful = True
    return authors, award, doubtful


# ---- page parsing ---------------------------------------------------------
_ITEM = re.compile(r"<h3>(?P<h3>.*?)</h3>|<article>(?P<art>.*?)</article>", re.S)
_ADDR = re.compile(r"<address>(.*?)</address>", re.S)
_ITAL = re.compile(r"<i>(.*?)</i>", re.S)
_CITE = re.compile(r"<cite>(.*?)</cite>", re.S)
_BQ = re.compile(r"<blockquote>(.*?)</blockquote>", re.S)


def parse(page: str, year: int):
    m = re.search(r'<div class="field-item even">(.*)', page, re.S)
    body = m.group(1) if m else page
    section = None
    out = []
    for it in _ITEM.finditer(body):
        if it.group("h3") is not None:
            section = clean(it.group("h3"))
            continue
        art = it.group("art")
        addr = _ADDR.search(art)
        raw_auth = raw_aff = ""
        if addr:
            a = addr.group(1)
            ital = _ITAL.findall(a)
            raw_aff = clean(" ".join(ital), drop_sup=False) if ital else ""
            a_no_aff = _ITAL.sub(" ", a)
            raw_auth = clean(a_no_aff)
        cite = _CITE.search(art)
        title = clean(cite.group(1)) if cite else ""
        paras = [clean(p) for p in _BQ.findall(art)]
        text = "\n\n".join(p for p in paras if p) or None
        authors, award, doubtful = split_authors(raw_auth)
        for au in authors:
            au["affiliation"] = raw_aff or None
        sec = (section or "").lower()
        ptype = "poster" if "poster" in sec else ("talk" if "oral" in sec else None)
        out.append(dict(
            title=title or None, abstract_text=text, authors=authors, award=award,
            presentation_type=ptype, session_name=section,
            society="AES", society_basis="meeting", societies_explicit="AES",
            is_elasmo=1, elasmo_basis="meeting", confidence=1.0,
            needs_review=int(doubtful or not title or not text),
        ))
    return out


def meeting_location(year: int):
    try:
        from conf_abstracts.build_coverage_matrix import JMIH_LOC
        return JMIH_LOC.get(year)
    except Exception:
        return None


def run(dry_run: bool):
    con = None if dry_run else schema.create_db(C.DB_PATH)
    grand = 0
    for y in YEARS:
        page = fetch(y)
        if page is None:
            continue
        recs = parse(page, y)
        n_body = sum(1 for r in recs if r["abstract_text"])
        n_rev = sum(r["needs_review"] for r in recs)
        n_au = sum(len(r["authors"]) for r in recs)
        print(f"  {y}: {len(recs):4} abstracts, {n_body:4} with body, {n_au:4} authors, "
              f"{n_rev:3} needs_review, sections={sorted({r['session_name'] for r in recs if r['session_name']})}")
        grand += len(recs)
        if con is None:
            continue
        meta = dict(meeting="AES", year=y, name=f"AES {y} Annual Meeting (elasmo.org)",
                    location=meeting_location(y), dates=None, source_pdf=URL.format(y=y),
                    doc_type="abstract_book", page_count=None, is_ocr=0, parse_status="ok")
        mid = load.upsert_meeting(con, meta)
        ins = sum(1 for r in recs if r["title"] and load.insert_abstract(con, mid, r))
        con.execute("UPDATE meetings SET n_abstracts=(SELECT COUNT(*) FROM abstracts "
                    "WHERE meeting_id=?) WHERE meeting_id=?", (mid, mid))
        con.commit()
        print(f"        -> inserted {ins} into meeting_id {mid}")
    print(f"TOTAL parsed: {grand}")
    if con:
        con.close()


# ---- dedup against JMIH-book copies of the same AES abstracts -------------
_STOP = {"the", "of", "a", "an", "in", "on", "and", "for", "from", "to", "with", "by", "at"}


def _toks(t: str):
    return {w for w in re.findall(r"[a-z]{3,}", (t or "").lower()) if w not in _STOP}


def dedup(threshold: float):
    con = sqlite3.connect(str(C.DB_PATH))
    years = [r[0] for r in con.execute("SELECT DISTINCT year FROM meetings WHERE meeting='AES'")]
    total_del = 0
    for y in years:
        aes = con.execute("""SELECT a.title FROM abstracts a JOIN meetings m USING(meeting_id)
                             WHERE m.meeting='AES' AND m.year=?""", (y,)).fetchall()
        aes_toks = [_toks(t) for (t,) in aes if t]
        jm = con.execute("""SELECT a.abstract_id, a.title FROM abstracts a JOIN meetings m USING(meeting_id)
                            WHERE m.meeting IN ('JMIH','ASIH') AND m.year=? AND a.is_elasmo=1""", (y,)).fetchall()
        if not jm:
            continue
        victims = []
        for aid, title in jm:
            tt = _toks(title)
            if len(tt) < 3:
                continue
            best = max((len(tt & at) / len(tt | at) for at in aes_toks if at), default=0)
            if best >= threshold:
                victims.append(aid)
        print(f"  {y}: {len(jm)} elasmo records in JMIH/ASIH books, {len(victims)} match an elasmo.org title (>= {threshold}) -> removed")
        for aid in victims:
            con.execute("DELETE FROM authors WHERE abstract_id=?", (aid,))
            con.execute("DELETE FROM abstracts WHERE abstract_id=?", (aid,))
        total_del += len(victims)
    con.execute("UPDATE meetings SET n_abstracts=(SELECT COUNT(*) FROM abstracts WHERE abstracts.meeting_id=meetings.meeting_id)")
    con.commit()
    con.close()
    print(f"removed {total_del} JMIH/ASIH duplicates of elasmo.org AES abstracts")


def supersede():
    """elasmo.org is the authoritative AES source for its years: remove JMIH/ASIH-book
    elasmo records that are AES-session talks (duplicates by construction) or
    needs_review (degraded OCR; title match can't see them). Non-AES elasmo
    talks with clean titles are kept."""
    con = sqlite3.connect(str(C.DB_PATH))
    years = [r[0] for r in con.execute("SELECT DISTINCT year FROM meetings WHERE meeting='AES'")]
    tot = 0
    for y in years:
        rows = con.execute("""SELECT a.abstract_id FROM abstracts a JOIN meetings m USING(meeting_id)
                              WHERE m.meeting IN ('JMIH','ASIH') AND m.year=? AND a.is_elasmo=1
                                AND (a.society='AES' OR a.needs_review=1)""", (y,)).fetchall()
        if not rows:
            continue
        for (aid,) in rows:
            con.execute("DELETE FROM authors WHERE abstract_id=?", (aid,))
            con.execute("DELETE FROM abstracts WHERE abstract_id=?", (aid,))
        left = con.execute("""SELECT COUNT(*) FROM abstracts a JOIN meetings m USING(meeting_id)
                              WHERE m.meeting IN ('JMIH','ASIH') AND m.year=? AND a.is_elasmo=1""", (y,)).fetchone()[0]
        print(f"  {y}: removed {len(rows)} superseded JMIH/ASIH elasmo records; {left} non-AES elasmo kept")
        tot += len(rows)
    con.execute("UPDATE meetings SET n_abstracts=(SELECT COUNT(*) FROM abstracts WHERE abstracts.meeting_id=meetings.meeting_id)")
    con.commit(); con.close()
    print(f"superseded {tot} records")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dedup", action="store_true")
    ap.add_argument("--supersede", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.6)
    a = ap.parse_args()
    if a.supersede:
        supersede()
    elif a.dedup:
        dedup(a.threshold)
    else:
        run(a.dry_run)
