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


def wanted():
    """The GCFI records we lack, from papers_data.json."""
    papers = json.loads((C.REPO / "docs" / "papers_data.json").read_text())
    pat = re.compile(r"Gulf and Caribbean Fisheries Institute", re.I)
    out = []
    for p in papers:
        blob = " ".join(str(p.get(k) or "") for k in ("journal", "journal_clean", "findspot_raw"))
        if pat.search(blob):
            out.append(dict(literature_id=str(p.get("literature_id") or "").replace(".0", ""),
                            title=str(p.get("title") or ""), year=p.get("year")))
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


def _pdf_title(data, tmp):
    tmp.write_bytes(data)
    try:
        txt = subprocess.run(["pdftotext", "-f", "1", "-l", "1", str(tmp), "-"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:                                          # noqa: BLE001
        return ""
    lines = [l.strip() for l in txt.splitlines() if len(l.strip()) > 12]
    return " ".join(lines[:4])


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
    a = ap.parse_args()
    want = wanted()
    years = sorted({int(w["year"]) for w in want if w["year"]})
    vols = [(y - FIRST_YEAR, y) for y in years]
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
            head = _pdf_title(body, tmp)
            hit = _match(head, want)
            found[str(n)] = dict(bytes=len(body), head=head[:160],
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
