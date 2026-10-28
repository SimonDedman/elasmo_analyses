"""Harvest the two online EBI proceedings (Encontro Brasileiro de Ictiologia).

Two editions of the Sociedade Brasileira de Ictiologia's meeting publish every
abstract openly on the web; no other edition does (searched 2026-10-28):

  2015  XXI EBI, Olinda   the proceedings CD, mirrored by the event company at
                          automacaodeeventos.com.br/ebi2015/cd/. listaresumos.htm
                          lists all 1,169 works (title, authors, affiliations,
                          keywords, number and type); each body is on
                          resumos/R<num>-<n>.html.
  2025  XXV EBI, Palmas   Realize Editora's "Anais do EBI" (ISBN
                          978-65-5222-033-2): 65 listing pages, then one
                          artigo/visualizar/<id> page per work, whose HTML embeds
                          the record (titulo, resumo, modalidade, area_tematica)
                          and an "Autores" block of names and institutions.

Raw pages are cached under SharkPapers/Conferences/<year>/<year>_EBI_Anais_web/
so parse_ebi.py can be re-run without touching the network. Only a 200 of
plausible size is cached; anything else is recorded as a failure in
_coverage.json, so a blocked fetch never reads as a work that does not exist.
One process per host, one request per DELAY seconds.

Usage:
  fetch_ebi.py --year 2015|2025 [--limit N]
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"
DELAY = 1.0
MIN_BYTES = 1500

BASE_2015 = "http://www.automacaodeeventos.com.br/ebi2015/cd/"
BASE_2025 = "https://editorarealize.com.br/"
LIST_2025 = BASE_2025 + "edicao/detalhes/anais-do-ebi---encontro-brasileiro-de-ictiologia"


def cache_dir(year):
    return C.CONFERENCES / str(year) / f"{year}_EBI_Anais_web"


class Fetcher:
    def __init__(self, root):
        self.root = root
        self.cov = dict(fetched=0, cached=0, failed={})

    def get(self, url, rel):
        """Return the page text from cache or network; None on failure."""
        out = self.root / rel
        if out.exists() and out.stat().st_size >= MIN_BYTES:
            self.cov["cached"] += 1
            return out.read_bytes()
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                code, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            code, body = e.code, b""
        except Exception as e:  # timeout, reset, DNS
            code, body = type(e).__name__, b""
        if code != 200 or len(body) < MIN_BYTES:
            self.cov["failed"][url] = f"{code} ({len(body)} bytes)"
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".part")
        tmp.write_bytes(body)
        tmp.replace(out)
        self.cov["fetched"] += 1
        return body


def run_2015(f, limit):
    lista = f.get(BASE_2015 + "listaresumos.htm", "listaresumos.htm")
    if lista is None:
        raise SystemExit("listaresumos.htm not fetched: " + json.dumps(f.cov["failed"]))
    links = sorted(set(re.findall(rb'href="(resumos/R[0-9]+-[0-9]+\.html)"', lista)))
    f.cov["listed"] = len(links)
    for i, l in enumerate(links[:limit] if limit else links):
        l = l.decode()
        f.get(BASE_2015 + l, l)
        if i % 100 == 0:
            print(f"  {i}/{len(links)} ({f.cov['fetched']} new, {len(f.cov['failed'])} failed)", flush=True)


def run_2025(f, limit):
    first = f.get(LIST_2025, "list/page_001.html")
    if first is None:
        raise SystemExit("listing page 1 not fetched: " + json.dumps(f.cov["failed"]))
    last = max(int(n) for n in re.findall(rb"\?page=([0-9]+)", first))
    ids = []
    for p in range(1, last + 1):
        page = first if p == 1 else f.get(f"{LIST_2025}?page={p}", f"list/page_{p:03d}.html")
        if page is None:
            continue
        for i in re.findall(rb"artigo/visualizar/([0-9]+)", page):
            if i not in ids:
                ids.append(i)
    f.cov["listing_pages"] = last
    f.cov["listed"] = len(ids)
    for n, i in enumerate(ids[:limit] if limit else ids):
        i = i.decode()
        f.get(f"{BASE_2025}artigo/visualizar/{i}", f"artigo/{i}.html")
        if n % 100 == 0:
            print(f"  {n}/{len(ids)} ({f.cov['fetched']} new, {len(f.cov['failed'])} failed)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True, choices=[2015, 2025])
    ap.add_argument("--limit", type=int, help="fetch only the first N works (a trial)")
    a = ap.parse_args()
    root = cache_dir(a.year)
    root.mkdir(parents=True, exist_ok=True)
    f = Fetcher(root)
    (run_2015 if a.year == 2015 else run_2025)(f, a.limit)
    f.cov["finished"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    f.cov["complete"] = not f.cov["failed"] and not a.limit
    (root / "_coverage.json").write_text(json.dumps(f.cov, indent=1))
    print(f"EBI {a.year}: listed {f.cov['listed']}, fetched {f.cov['fetched']}, "
          f"from cache {f.cov['cached']}, FAILED {len(f.cov['failed'])}")
    for u, why in list(f.cov["failed"].items())[:50]:
        print("  FAILED", why, u)
    print("DONE" if f.cov["complete"] else "NOT COMPLETE")


if __name__ == "__main__":
    main()
