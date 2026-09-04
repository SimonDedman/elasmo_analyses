"""Harvest the SOMEPEC abstract books (Simposium Nacional de Tiburones y Rayas).

The Sociedad Mexicana de Peces Cartilaginosos publishes its memorias openly on
somepec.org, so this series needs no email to anyone: crawl the site, take every
PDF, and report what came back. The corpus already cites 44 abstracts from the
VI (2014 Mazatlan) alone, and the series has run since 2004.

Follows the network rules that matter here: a 403/404/timeout is recorded as a
FAILURE, never as "no such file", and only 200s of a plausible size are kept, so
a blocked fetch can never be mistaken for a meeting that published nothing.

Usage:
  scrape_somepec.py                 # crawl + download into the staging dir
  scrape_somepec.py --list          # show what would be fetched, download nothing
"""
import argparse
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402

BASE = "https://somepec.org"
STAGING = C.REPO / "database" / "others_libraries" / "SOMEPEC"
UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0")
DELAY = 2.0          # one process, polite; the site is a small society's WordPress
MIN_PDF_BYTES = 20_000

# Pages worth crawling for links. The site is small; this is cheaper and kinder
# than a blind spider, and it keeps the crawl inside somepec.org.
SEED_PATHS = ["/", "/memorias/", "/programa/", "/directorio/", "/simposium/",
              "/ix-simposium-ii-congreso-latinoamericano/", "/publicaciones/",
              "/eventos/", "/nosotros/"]

# PDFs found by site-restricted search that are not linked from the seed pages.
KNOWN = [
    "/wp-content/uploads/2018/10/3er-Semana-del-Tiburon-y-la-UNAM-y-1er-Simposium-"
    "Nacional-de-Tiburones-y-Rayas.pdf",
    "/wp-content/uploads/2018/10/III-Simposium-Nacional-de-Tiburones-y-Rayas.pdf",
    "/wp-content/uploads/2018/10/Memorias-IV-Simposium-Nacional-de-Tiburones-y-Rayas.pdf",
    "/wp-content/uploads/2018/10/Libro_Resumenes.pdf",
    "/wp-content/uploads/2021/08/Programa_IXSNTyR.pdf",
    "/wp-content/uploads/2025/10/Khondros_2025_new-version-8.pdf",
]

_PDF = re.compile(r'href=["\']([^"\']+\.pdf)["\']', re.I)
_HREF = re.compile(r'href=["\'](/[^"\']*)["\']', re.I)


def _get(url, timeout=60):
    """Return (status, bytes). Status is an int for HTTP, or the error string —
    a block and a miss must never look the same to the caller."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:                                    # noqa: BLE001
        return f"{type(e).__name__}: {e}", b""


def crawl():
    """Collect PDF URLs from the seed pages plus the known ones."""
    found, visited, failures = set(), set(), []
    queue = [urllib.parse.urljoin(BASE, p) for p in SEED_PATHS]
    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        status, body = _get(url)
        if status != 200:
            failures.append((url, status))
            continue
        html = body.decode("utf-8", "replace")
        for m in _PDF.finditer(html):
            found.add(urllib.parse.urljoin(url, m.group(1)))
        # one hop deeper, same host only
        for m in _HREF.finditer(html):
            nxt = urllib.parse.urljoin(BASE, m.group(1))
            if (nxt.startswith(BASE) and nxt not in visited and len(visited) < 40
                    and not nxt.endswith((".jpg", ".png", ".pdf"))):
                queue.append(nxt)
        time.sleep(DELAY)
    for k in KNOWN:
        found.add(urllib.parse.urljoin(BASE, k))
    return sorted(found), failures


def download(urls):
    STAGING.mkdir(parents=True, exist_ok=True)
    got, failed, skipped = [], [], []
    for url in urls:
        name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        dest = STAGING / name
        if dest.exists() and dest.stat().st_size > MIN_PDF_BYTES:
            skipped.append(name)
            continue
        status, body = _get(url, timeout=180)
        if status == 200 and len(body) >= MIN_PDF_BYTES and body[:4] == b"%PDF":
            dest.write_bytes(body)
            got.append((name, len(body)))
        else:
            # explicit failure, never silence: an empty result here means the
            # fetch failed, not that the society published nothing that year
            failed.append((name, status, len(body)))
        time.sleep(DELAY)
    return got, failed, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    urls, page_failures = crawl()
    print(f"{len(urls)} PDF URLs found; {len(page_failures)} seed pages failed")
    for url, status in page_failures:
        print(f"  PAGE FAILED [{status}] {url}")
    for u in urls:
        print("  " + u)
    if a.list:
        return
    got, failed, skipped = download(urls)
    print(f"\ndownloaded {len(got)}, already held {len(skipped)}, FAILED {len(failed)}")
    for n, sz in got:
        print(f"  OK   {sz/1e6:7.2f} MB  {n}")
    for n, status, sz in failed:
        print(f"  FAIL [{status}] {sz}B  {n}")
    print(f"\nstaged in {STAGING}")


if __name__ == "__main__":
    main()
