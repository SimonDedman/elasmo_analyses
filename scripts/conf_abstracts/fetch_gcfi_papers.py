"""Fetch the GCFI papers the corpus wants, from the society's open proceedings.

Every GCFI paper since 1948 is a free PDF on proceedings.gcfi.org, so the 31
records that were sitting on the needs-library queue never needed a person. The
site's own search API is useless to us — it returns [] even for a paper we know
is there (positive control: "bonefish") — and paper pages render their download
link in JavaScript. What IS reliable is the upload path:

    /wp-content/uploads/<yyyy>/<mm>/gcfi_<volume>-<paper>.pdf

with volume N = year 1947+N (the 39th annual meeting is 1986, confirmed against
a URL found by search). The upload month differs per volume, so each volume's
path is discovered by probing, then its papers are enumerated until a run of
consecutive misses.

Titles come from the PDFs themselves and are matched against the wanted list, so
a paper is only claimed when its own first page says so.

A 404 is recorded as a miss and anything else as a FAILURE: a blocked or timed
out volume must never be mistaken for a volume with no papers in it.

Usage:
  fetch_gcfi_papers.py --probe        # discover upload paths only
  fetch_gcfi_papers.py                # full run (slow: ~2 s per request)
"""
import argparse
import json
import re
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
sys.path.insert(0, str(C.REPO / "scripts"))

BASE = "https://proceedings.gcfi.org/wp-content/uploads"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0"
DELAY = 2.0
STAGING = C.REPO / "outputs" / "gcfi_papers"
STATE = C.OUT / "gcfi_fetch_state.json"
MAX_PAPER = 120          # no GCFI volume comes close
MISS_RUN = 8             # consecutive 404s that end a volume
FIRST_YEAR = 1947        # volume N == year FIRST_YEAR + N
OCR_LANGS = "eng+spa"    # GCFI publishes in English and Spanish


# GCFI numbers its meetings, and the records SAY which one they are in
# ("Proceedings of the Fifty Nine Annual ..."). That ordinal is the volume, and
# it is the only reliable key: the `year` field is often the publication year,
# which for these proceedings runs one to eleven years after the meeting. Keying
# on year-1947 sent the first run to volumes 5, 8, 39 and 45 when the records
# name 4, 7, 37 and 41, and it matched nothing at all.
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
        "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
        "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
        "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
        "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
        "sixtieth": 60, "seventieth": 70, "eightieth": 80}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80}
# "Fifty Nine" appears in the records for the 59th; a cardinal in the units slot.
_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
          "seven": 7, "eight": 8, "nine": 9}


def volume_of(venue):
    """Volume number from a GCFI citation string, or None."""
    m = re.search(r"Proceedings,?\s+(\d{1,2})\b", venue)
    if m:
        return int(m.group(1))
    m = re.search(r"of the\s+([A-Za-z\u2013\-\s]{3,30}?)\s+Annual", venue, re.I)
    if not m:
        return None
    words = [w for w in re.split(r"[\s\u2013\-]+", m.group(1).lower()) if w]
    total = 0
    for w in words:
        if w in _TENS:
            total += _TENS[w]
        elif w in _ORD:
            total += _ORD[w]
        elif w in _UNITS:
            total += _UNITS[w]
        else:
            return None
    return total or None


def wanted():
    """The GCFI records we lack, each with the volume its own citation names."""
    papers = json.loads((C.REPO / "docs" / "papers_data.json").read_text())
    pat = re.compile(r"Gulf and Caribbean Fisheries", re.I)
    out = []
    for p in papers:
        blob = " ".join(str(p.get(k) or "") for k in ("journal", "journal_clean", "findspot_raw"))
        if not pat.search(blob):
            continue
        vol = volume_of(str(p.get("findspot_raw") or "")) or volume_of(str(p.get("journal") or ""))
        out.append(dict(literature_id=str(p.get("literature_id") or "").replace(".0", ""),
                        title=str(p.get("title") or ""), year=p.get("year"), volume=vol))
    return out


def _head(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:                                    # noqa: BLE001
        return f"{type(e).__name__}"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:                                    # noqa: BLE001
        return f"{type(e).__name__}", b""


# Upload months seen on the site, most likely first. Probing is cheap (HEAD).
_PATHS = [f"{y}/{m:02d}" for y in (2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022)
          for m in range(1, 13)]


def discover_path(vol):
    """Which /uploads/<yyyy>/<mm>/ holds this volume. Returns (path, status)."""
    for path in _PATHS:
        st = _head(f"{BASE}/{path}/gcfi_{vol}-1.pdf")
        time.sleep(0.4)
        if st == 200:
            return path, "ok"
        if st != 404:
            return None, f"probe failed: {st}"
    return None, "no path found (all 404)"


def _first_page_text(tmp):
    try:
        return subprocess.run(["pdftotext", "-f", "1", "-l", "1", str(tmp), "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:                                          # noqa: BLE001
        return ""


def _ocr_first_page(tmp):
    """OCR page 1. The pre-1990s volumes are scanned images with no text layer
    (measured: 0 alpha characters on page 1, against ~4,000 for 2006), so their
    titles can only be read this way. pdftoppm + tesseract directly, NOT
    ocrmypdf, which writes a broken vertical text layer on scans like these.
    One page is enough to identify a paper; full-document OCR is a separate job.
    """
    png = tmp.with_suffix("")
    try:
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "300", "-png",
                        str(tmp), str(png)], capture_output=True, timeout=180)
        page = next(iter(sorted(png.parent.glob(png.name + "-*.png"))), None)
        if not page:
            return ""
        out = subprocess.run(["tesseract", str(page), "stdout", "-l", OCR_LANGS],
                             capture_output=True, text=True, timeout=240,
                             env={**os.environ, "OMP_THREAD_LIMIT": "2"}).stdout
        page.unlink(missing_ok=True)
        return out
    except Exception:                                          # noqa: BLE001
        return ""


def _pdf_title(data, tmp):
    """The opening lines of page 1, from the text layer if there is one and from
    OCR if there is not. Returns (text, source) so a caller can tell a paper
    whose title was READ from one that was GUESSED at by OCR."""
    tmp.write_bytes(data)
    txt, src = _first_page_text(tmp), "text"
    if len("".join(ch for ch in txt if ch.isalpha())) < 40:
        txt, src = _ocr_first_page(tmp), "ocr"
    lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 12]
    return " ".join(lines[:4]), src


def _norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def _match(pdf_head, targets):
    """A wanted title whose normalised form appears in the PDF's opening lines."""
    h = _norm(pdf_head)
    if len(h) < 30:
        return None
    for t in targets:
        n = _norm(t["title"])
        if len(n) < 25:
            continue
        if n[:60] in h:
            return t
        if SequenceMatcher(None, n[:120], h[:400], autojunk=False) \
                .find_longest_match(0, min(120, len(n)), 0, min(400, len(h))).size >= 45:
            return t
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--volumes", help="comma-separated volume numbers to run")
    a = ap.parse_args()
    want = wanted()
    novol = [w for w in want if not w["volume"]]
    vols = sorted({(w["volume"], FIRST_YEAR + w["volume"]) for w in want if w["volume"]})
    if novol:
        print(f"  {len(novol)} record(s) name no volume — not fetchable this way: "
              + "; ".join(w["title"][:50] for w in novol), flush=True)
    if a.volumes:
        keep = {int(v) for v in a.volumes.split(",")}
        vols = [(v, y) for v, y in vols if v in keep]
    print(f"{len(want)} GCFI records wanted across {len(vols)} volumes: "
          + ", ".join(f"v{v}({y})" for v, y in vols), flush=True)

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    STAGING.mkdir(parents=True, exist_ok=True)
    tmp = STAGING / ".probe.pdf"

    for vol, year in vols:
        key = str(vol)
        rec = state.setdefault(key, {})
        if "path" not in rec:
            path, status = discover_path(vol)
            rec["path"], rec["path_status"] = path, status
            STATE.write_text(json.dumps(state, indent=1))
            print(f"  v{vol} ({year}): path={path or '-'} [{status}]", flush=True)
        if a.probe or not rec.get("path"):
            continue
        if rec.get("done"):
            continue
        found, failures, misses = rec.get("papers", {}), [], 0
        # Pre-1990s volumes are scanned images with NO text layer (measured:
        # gcfi_5-3 and gcfi_39-22 give 0 alpha characters on page 1, while
        # gcfi_59-4 and gcfi_60-10 give ~4,000). Titles cannot be read from
        # them, so matching is impossible and the run must SAY so rather than
        # grinding through the volume and reporting nothing found.
        if rec.get("no_text_layer"):
            print(f"  v{vol} ({year}): SKIPPED — scanned images, no text layer to match on",
                  flush=True)
            continue
        blank_heads = 0
        for n in range(1, MAX_PAPER + 1):
            if str(n) in found:
                continue
            url = f"{BASE}/{rec['path']}/gcfi_{vol}-{n}.pdf"
            status, body = _get(url)
            time.sleep(DELAY)
            if status == 404:
                misses += 1
                if misses >= MISS_RUN:
                    break
                continue
            if status != 200 or body[:4] != b"%PDF":
                failures.append([n, str(status), len(body)])
                misses = 0
                continue
            misses = 0
            head, head_src = _pdf_title(body, tmp)
            if not head.strip():
                blank_heads += 1
                if blank_heads >= 10 and not any(v["head"].strip() for v in found.values()):
                    rec["no_text_layer"] = True
                    rec["done"] = True
                    STATE.write_text(json.dumps(state, indent=1))
                    print(f"  v{vol} ({year}): ABANDONED — {blank_heads} PDFs yielded "
                          f"nothing from either the text layer OR OCR", flush=True)
                    break
            hit = _match(head, want)
            found[str(n)] = dict(bytes=len(body), head=head[:160], head_src=head_src,
                                 matched=hit["literature_id"] if hit else None)
            if hit:
                dest = STAGING / f"gcfi_{vol}-{n}__{hit['literature_id']}.pdf"
                dest.write_bytes(body)
                print(f"    MATCH v{vol}-{n} -> id {hit['literature_id']}  "
                      f"{hit['title'][:60]}", flush=True)
            rec["papers"], rec["failures"] = found, failures
            STATE.write_text(json.dumps(state, indent=1))
        rec["done"] = True
        STATE.write_text(json.dumps(state, indent=1))
        nmatch = sum(1 for v in found.values() if v["matched"])
        print(f"  v{vol} ({year}): {len(found)} papers seen, {nmatch} matched, "
              f"{len(failures)} FAILED", flush=True)

    tmp.unlink(missing_ok=True)
    total = sum(1 for r in state.values() for p in r.get("papers", {}).values()
                if p.get("matched"))
    fails = sum(len(r.get("failures", [])) for r in state.values())
    print(f"\nDONE: {total} of {len(want)} wanted papers downloaded, "
          f"{fails} fetch failures. Staged in {STAGING}", flush=True)


if __name__ == "__main__":
    main()
