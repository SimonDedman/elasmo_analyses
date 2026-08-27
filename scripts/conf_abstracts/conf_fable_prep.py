"""STAGE 1 of Fable conference-abstract extraction.

The regex parsers hit a heuristic wall on the varied EEA/JMIH/ASIH/SI title +
author + affiliation layouts (bodies extract cleanly, titles/authors do not).
The abstract-book corpus is small (~20 books, 34k-94k tokens each — every book
fits in a single Fable context), so we pass each whole book through Fable and
let it return structured abstracts as JSON.

This stage:
  - enumerates the abstract-book PDFs in scope,
  - dumps `pdftotext -layout` text to outputs/conf_abstracts/.fable_src/<key>.txt,
  - writes a worklist JSON (one entry per book) that the fetch helper and the
    merge step both read.

Run: ./venv/bin/python scripts/conf_abstracts/conf_fable_prep.py [--only SUBSTR]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from conf_abstracts import config as C

SRC_DIR = C.OUT / "conf_abstracts" / ".fable_src"
CACHE_DIR = C.OUT / "conf_abstracts" / ".fable_cache"
WORKLIST = C.OUT / "conf_abstracts" / "fable_worklist.json"

# Fable under-extracts very long books (observed: EEA2016 at 230k chars yielded
# only 20 of ~70 abstracts — it stops generating partway). Books over this size
# are split into overlapping chunks, one Fable agent each; the merge folds the
# chunks back into ONE meeting (shared source_pdf) and dedups the overlap by
# title. Books at/below ~168k chars extract fully in one pass.
CHUNK_THRESHOLD = 170_000
CHUNK_SIZE = 130_000
CHUNK_OVERLAP = 15_000


def _cache_count(cache_path) -> int:
    p = Path(cache_path)
    if not p.exists() or p.stat().st_size < 2:
        return 0
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return len(d) if isinstance(d, list) else len(d.get("abstracts", []))
    except Exception:
        return 0


def _healthy_cache(entry) -> bool:
    """A single-book cache that extracted fully: full books run ~0.40 abstracts
    per 1000 chars; truncated ones (EEA2016: 0.087) fall well below. Programmes
    with no bodies (2015/2017) are small and handled by the size threshold."""
    n = _cache_count(entry["cache_path"])
    return n > 0 and (n / max(entry["n_chars"], 1) * 1000) >= 0.25


def _chunk_text(text: str):
    """Split into overlapping char windows on paragraph/line boundaries."""
    if len(text) <= CHUNK_THRESHOLD:
        return [text]
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        if end < n:  # extend to the next line break so an abstract isn't cut mid-line
            nl = text.find("\n", end)
            if 0 < nl < end + 2000:
                end = nl
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - CHUNK_OVERLAP
    return chunks

# Books in scope. Each entry: (glob, meeting, society_hint, is_elasmo_meeting).
# EEA books are wholly elasmo (meeting=EEA -> AES society). The Cat/ folder holds
# the EEA abstract books; extend this list to sweep JMIH/ASIH/SI later.
SCOPE = [
    # abstract books only: programme-only PDFs (2015/2017/2021/2023/2025) carry no
    # bodies and would collide with the same year's abstract-book key.
    (str(C.CONFERENCES / "*" / "*_EEA_AbstractBook*.pdf"), "EEA", "AES", True),
    # JMIH abstract books (multi-society; society resolved per abstract from the
    # session heading, elasmo flag from the lexicon). Simon approved Fable for
    # 2005 and 2016 on 2026-08-25; the glob lists every book, extraction is
    # launched per index so the others stay unextracted until asked for.
    (str(C.CONFERENCES / "*" / "*_JMIH_AbstractBook.pdf"), "JMIH", "", False),
    (str(C.REPO / "database/others_libraries/Cat/EEA*.pdf"), "EEA", "AES", True),  # legacy inbox
]


def _key(pdf: Path) -> str:
    """Stable short key from the filename, e.g. EEA2004_London -> EEA2004.
    A year split across two books (oral/poster) gets an _oral/_poster suffix so
    they don't collide (e.g. EEA2023_oral, EEA2023_poster)."""
    m = re.match(r"([A-Za-z]+)_?(\d{4})", pdf.stem)          # EEA2004_London
    m2 = re.match(r"(\d{4})_([A-Za-z]+)_", pdf.stem)          # 2004_EEA_AbstractBook
    if m:
        base = f"{m.group(1)}{m.group(2)}"
    elif m2:
        base = f"{m2.group(2)}{m2.group(1)}"
    else:
        base = re.sub(r"[^A-Za-z0-9]+", "_", pdf.stem)[:32]
    low = pdf.stem.lower()
    if "oral" in low:
        base += "_oral"
    elif "poster" in low:
        base += "_poster"
    return base


def _year(pdf: Path) -> int | None:
    m = re.search(r"(19|20)\d{2}", pdf.stem)
    return int(m.group(0)) if m else None


def _city(pdf: Path) -> str | None:
    # EEA{year}_{City}_... -> City (underscores -> spaces, strip trailing descriptor)
    m = re.match(r"[A-Za-z]+\d{4}[_ ]+([A-Za-zÀ-ſ]+)", pdf.stem)
    return m.group(1) if m else None


def pdftotext_layout(pdf: Path) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True, timeout=300).stdout.decode("utf-8", "replace")


# EEA host cities by year — recovers meeting.location for a book whose source
# PDF vanished from the NAS-synced folder (so we can't parse the city from it).
_EEA_CITIES = {
    2004: "London", 2011: "Berlin", 2013: "Plymouth", 2014: "Leeuwarden",
    2015: "Peniche", 2016: "Bristol", 2017: "Amsterdam", 2018: "Peniche",
    2019: "Rende", 2023: "Brighton", 2024: "Thessaloniki", 2025: "Rotterdam",
}


def build(only=None):
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    import glob as _glob
    # keep prior entries so a book stays in the worklist even if its source PDF
    # later vanishes from the NAS-synced folder (the extracted text is the
    # durable artifact; the PDF is not).
    by_key = {}
    if WORKLIST.exists():
        for w in json.loads(WORKLIST.read_text(encoding="utf-8")):
            if "__c" in w["key"]:
                continue  # chunk entries are ephemeral — regenerated from the full book each run
            by_key[w["key"]] = w

    for pattern, meeting, soc_hint, elasmo in SCOPE:
        for path in sorted(_glob.glob(pattern)):
            pdf = Path(path)
            if only and only.lower() not in pdf.name.lower():
                continue
            key = _key(pdf)
            text = pdftotext_layout(pdf)
            if len(text) < 1000:
                # corrupt/image-only PDF (2024/2025 have broken catalogs; awaiting
                # clean copies from Cat). Skip rather than burn a Fable agent — but
                # DON'T drop a previously-extracted version of the same book.
                if key not in by_key or not Path(by_key[key]["src_txt"]).exists():
                    print(f"  SKIP {key} ({pdf.name}): only {len(text)} chars extracted")
                continue
            src = SRC_DIR / f"{key}.txt"
            src.write_text(text, encoding="utf-8")
            by_key[key] = dict(
                key=key, meeting=meeting, year=_year(pdf),
                city=_city(pdf) or _EEA_CITIES.get(_year(pdf)),
                society_hint=soc_hint, is_elasmo_meeting=elasmo,
                source_pdf=str(pdf), src_txt=str(src),
                cache_path=str(CACHE_DIR / f"{key}.json"), n_chars=len(text))

    # recover orphaned src texts on disk not represented in the worklist (e.g.
    # a book extracted on an earlier run whose worklist entry was later lost and
    # whose PDF has since vanished from the NAS folder). Reconstruct from the key.
    for txt in sorted(SRC_DIR.glob("*.txt")):
        key = txt.stem
        if key in by_key or txt.stat().st_size < 1000 or "__c" in key:
            continue  # "__c" = a chunk slice, not a standalone book
        yr = _year(txt)
        print(f"  RECOVER {key}: orphaned text, no worklist entry (rebuilt)")
        by_key[key] = dict(
            key=key, meeting="EEA", year=yr, city=_EEA_CITIES.get(yr),
            society_hint="AES", is_elasmo_meeting=True,
            source_pdf=next((str(f) for f in sorted((C.CONFERENCES / str(yr)).glob(f"{yr}_EEA_*.pdf"))
                             if "AbstractBook" in f.name), None)
            or next((str(f) for f in sorted((C.CONFERENCES / str(yr)).glob(f"{yr}_EEA_*.pdf"))),
                    str(C.CONFERENCES / str(yr) / f"{yr}_EEA_AbstractBook.pdf")),
            src_txt=str(txt), cache_path=str(CACHE_DIR / f"{key}.json"),
            n_chars=txt.stat().st_size)

    # retain orphaned entries (PDF gone) whose extracted text still survives;
    # drop those whose text is missing/empty.
    worklist = []
    for key, w in by_key.items():
        txt = Path(w["src_txt"])
        if not txt.exists() or txt.stat().st_size < 1000:
            print(f"  DROP {key}: no surviving text ({w['src_txt']})")
            continue
        w["n_chars"] = txt.stat().st_size
        # host city is per-SERIES: never let the EEA table touch a JMIH/ASIH
        # book (it silently labelled JMIH 2015 "Peniche" and 2016 "Bristol"
        # via a stale setdefault — fixed 2026-08-27). Authoritative, not
        # setdefault, so a stale value from an earlier run is corrected.
        if w.get("meeting") in ("JMIH", "ASIH"):
            try:
                from conf_abstracts.build_coverage_matrix import JMIH_LOC
                w["city"] = JMIH_LOC.get(w.get("year")) or w.get("city")
            except Exception:
                pass
        elif w.get("meeting") == "EEA":
            w["city"] = w.get("city") or _EEA_CITIES.get(w.get("year"))
        worklist.append(w)

    # split oversized books that didn't extract healthily into overlapping chunks
    # (one Fable agent each); the merge folds them back via shared source_pdf.
    expanded = []
    for w in worklist:
        text = Path(w["src_txt"]).read_text(encoding="utf-8")
        if len(text) <= CHUNK_THRESHOLD or _healthy_cache(w):
            w.setdefault("book_key", w["key"])
            w.setdefault("chunk", 0)
            expanded.append(w)
            continue
        parts = _chunk_text(text)
        print(f"  CHUNK {w['key']}: {len(text)} chars -> {len(parts)} chunks "
              f"(single-book cache had {_cache_count(w['cache_path'])} abstracts)")
        for ci, part in enumerate(parts):
            ck = f"{w['key']}__c{ci}"
            csrc = SRC_DIR / f"{ck}.txt"
            csrc.write_text(part, encoding="utf-8")
            expanded.append(dict(
                key=ck, book_key=w["key"], chunk=ci,
                meeting=w["meeting"], year=w["year"], city=w.get("city"),
                society_hint=w["society_hint"], is_elasmo_meeting=w["is_elasmo_meeting"],
                source_pdf=w["source_pdf"], src_txt=str(csrc),
                cache_path=str(CACHE_DIR / f"{ck}.json"), n_chars=len(part)))
    worklist = expanded
    worklist.sort(key=lambda w: (str(w.get("year")), w["key"]))
    for i, w in enumerate(worklist):
        w["index"] = i

    WORKLIST.parent.mkdir(parents=True, exist_ok=True)
    WORKLIST.write_text(json.dumps(worklist, indent=2), encoding="utf-8")
    print(f"worklist: {len(worklist)} books -> {WORKLIST}")
    for w in worklist:
        done = "cached" if Path(w["cache_path"]).exists() else "     "
        gone = "" if Path(w["source_pdf"]).exists() else " (PDF gone; text kept)"
        print(f"  [{w['index']:2}] {done} {w['key']:14} {w['year']} "
              f"{(w['city'] or ''):12} ~{w['n_chars']//4:>6}tok{gone}")
    return worklist


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="filename substring filter")
    a = ap.parse_args()
    build(only=a.only)
