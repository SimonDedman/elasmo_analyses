#!/usr/bin/env python3
"""
oa_discovery_trawl.py

Automated open-access PDF discovery + download — NO user input required.
The legal, API-based alternative to Google-Scholar scraping: the same PDFs GS
indexes from ResearchGate/Academia/institutional repos are reachable via OA
aggregator APIs without any anti-bot wall.

Channels, tried in order per paper (stop at first PDF that downloads):
  1. OpenAlex  best_oa_location / any oa_location .pdf_url   (by DOI, else title search)
  2. Unpaywall best_oa_location.url_for_pdf                  (DOI only)
  3. Semantic Scholar  openAccessPdf.url                     (DOI, else title)
  4. CORE      download URL                                  (title/DOI)

Prioritises the CLOSED / no-access queue (what the user can't get via their
library). Polite delays, response caching, fully resumable. Downloads land in
outputs/oa_downloads/<literature_id>.pdf for a later `ingest_pdfs.py` pass
(this script does NOT touch the corpus/queue itself — download-only, safe).

Usage:
  python3 scripts/oa_discovery_trawl.py [--limit N] [--all] [--email you@x.com]
  # default: closed/unknown-OA papers first, then run ingest_pdfs.py on the output dir.
"""
import argparse, json, re, sys, time, hashlib
from pathlib import Path
import urllib.request, urllib.parse

BASE = Path(__file__).parent.parent
QUEUE = BASE / "docs/papers_data.json"
OUT = BASE / "outputs/oa_downloads"; OUT.mkdir(parents=True, exist_ok=True)
CACHE = BASE / "outputs/.oa_cache"; CACHE.mkdir(parents=True, exist_ok=True)
LOG = BASE / "outputs/oa_discovery_log.csv"
EMAIL = "simondedman@gmail.com"           # polite-pool contact for OpenAlex/Unpaywall
UA = f"EEA2025-shark-review (mailto:{EMAIL})"

def _get(url, timeout=30, is_json=True):
    """Cached GET (by URL hash). Returns parsed JSON or raw bytes, or None on error."""
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + (".json" if is_json else ".bin"))
    if key.exists():
        try: return json.loads(key.read_text()) if is_json else key.read_bytes()
        except Exception: pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=timeout).read()
    except Exception:
        return None
    if is_json:
        try: obj = json.loads(data)
        except Exception: return None
        key.write_text(json.dumps(obj)); return obj
    key.write_bytes(data); return data

def _ndoi(d):
    if not d: return None
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", str(d).strip().lower()) or None

def _norm_title(t):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(t).lower()).split())

# ---------- OA-URL discovery channels (each returns a pdf URL or None) ----------

def oa_openalex(doi, title, year):
    work = None
    if doi:
        work = _get(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?mailto={EMAIL}")
    if not work and title:
        q = urllib.parse.quote(title[:200])
        res = _get(f"https://api.openalex.org/works?filter=title.search:{q}&per-page=5&mailto={EMAIL}")
        for cand in (res or {}).get("results", []):
            if _norm_title(cand.get("title", "")) and _title_close(title, cand.get("title", "")):
                if not year or abs((cand.get("publication_year") or 0) - int(year or 0)) <= 1:
                    work = cand; break
    if not work: return None
    locs = [work.get("best_oa_location")] + (work.get("locations") or [])
    for loc in locs:
        if loc and loc.get("pdf_url"):
            return loc["pdf_url"]
    oa = work.get("open_access") or {}
    return oa.get("oa_url")

def oa_unpaywall(doi):
    if not doi: return None
    r = _get(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}")
    loc = (r or {}).get("best_oa_location") or {}
    return loc.get("url_for_pdf") or loc.get("url")

def oa_semantic_scholar(doi, title):
    r = None
    if doi:
        r = _get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=openAccessPdf,title")
    if not r and title:
        q = urllib.parse.quote(title[:200])
        s = _get(f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&fields=openAccessPdf,title,year&limit=3")
        for cand in (s or {}).get("data", []):
            if _title_close(title, cand.get("title", "")):
                r = cand; break
    pdf = (r or {}).get("openAccessPdf") or {}
    return pdf.get("url")

def _title_close(a, b, thr=0.75):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, _norm_title(a), _norm_title(b)).ratio() >= thr

CHANNELS = [("openalex", oa_openalex), ("unpaywall", oa_unpaywall), ("s2", oa_semantic_scholar)]

def _download_pdf(url, dest):
    data = _get(url, timeout=60, is_json=False)
    if not data or len(data) < 2048:
        return False
    if not (data[:5] == b"%PDF-" or b"%PDF-" in data[:1024]):   # verify it's really a PDF
        return False
    dest.write_bytes(data); return True

def find_and_download(paper):
    lid = str(paper.get("literature_id"))
    dest = OUT / f"{lid}.pdf"
    if dest.exists():
        return (lid, "already_downloaded", "")
    doi = _ndoi(paper.get("doi")); title = paper.get("title") or ""; year = paper.get("year")
    # Fast path: the queue may already carry an oa_url from a prior Unpaywall pass.
    existing = paper.get("oa_url")
    if existing and _download_pdf(existing, dest):
        return (lid, "downloaded:queue_oa_url", existing)
    for name, fn in CHANNELS:
        try:
            url = fn(doi, title, year) if fn is not oa_unpaywall else fn(doi)
        except TypeError:
            url = fn(doi, title)
        except Exception:
            url = None
        time.sleep(0.2)                     # polite between API calls
        if url and _download_pdf(url, dest):
            return (lid, f"downloaded:{name}", url)
    return (lid, "no_oa_found", "")

def main():
    global EMAIL, UA
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--all", action="store_true", help="all queue papers, not just closed/unknown-OA")
    ap.add_argument("--email", default=EMAIL)
    args = ap.parse_args()
    EMAIL = args.email; UA = f"EEA2025-shark-review (mailto:{EMAIL})"

    queue = json.load(open(QUEUE))
    # Skip 'closed' (Unpaywall already confirmed no OA copy exists). Prioritise
    # already-flagged-OA (gold/green/hybrid/bronze — near-certain hits) first, then
    # unchecked 'unknown' papers WITH a DOI (best discovery odds), then no-DOI.
    def prio(p):
        oa = str(p.get("oa_status", "")).lower()
        oa_rank = 0 if oa in ("gold", "green", "hybrid", "bronze") else (1 if oa in ("unknown", "") else 3)
        return (oa_rank, 0 if p.get("doi") else 1)
    pool = queue if args.all else [p for p in queue if str(p.get("oa_status", "")).lower() != "closed"]
    pool = sorted(pool, key=prio)[: args.limit]

    print(f"OA trawl over {len(pool)} papers (of {len(queue)} queued)...")
    results = []; hits = 0
    for i, p in enumerate(pool):
        lid, status, url = find_and_download(p)
        results.append((lid, status, url, p.get("doi", ""), (p.get("title") or "")[:80]))
        if status.startswith("downloaded"): hits += 1
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(pool)}  hits={hits}")
    import csv
    with open(LOG, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["literature_id", "status", "url", "doi", "title"]); w.writerows(results)
    print(f"\nDone: {hits}/{len(pool)} PDFs downloaded -> {OUT}")
    print(f"Log: {LOG}")
    print(f"Next: python3 scripts/ingest_pdfs.py {OUT}   # to file them into the corpus")

if __name__ == "__main__":
    main()
