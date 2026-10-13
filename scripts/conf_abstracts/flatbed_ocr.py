"""OCR for Carylanne's flatbed rescans of the old JMIH abstract books.

Two things about these scans decide how they have to be read:

1. **Two book pages per PDF page.** The 2001 book was scanned open, so each PDF
   page is a spread (left page | spiral | right page). The spread is split at
   the gutter, found per page as the widest column of the page carrying no word
   box from the scanner's own text layer (`pdftotext -bbox`). Every spread of the
   2001 book has a clean gutter 60-185 pt wide.

2. **The scanner's own OCR fails on tilted pages.** MEASURED on the 2001 book
   (2026-10-13), counting dictionary-valid words per page against the deskewed
   tesseract text below: on the 51 pages tilted < 0.5 deg the scanner layer
   recovers 99.7% as many; on the 69 pages tilted >= 0.5 deg only 67.4% (book
   p. 70, tilted 1.2 deg: 107 words against 712). So every page is rendered at
   300 dpi, deskewed with ImageMagick, and read with tesseract 5 (`--psm 4`).

The spiral binding prints as debris ("=p", "-_", "eal ge") at the inner edge of
each page. Tesseract's TSV output carries word boxes, so a word lying outside
the page's own text margins (median full-line start and end; the body is
justified), or separated from the rest of its line by a gap wider than any word
space, is
dropped.

Output is a text file with one `\\f=== PAGE <book page> ===` header per page, the
same shape `parse_jmih_caps` reads. Per-page TSVs are cached beside it, so a
rerun (or a resumed one) costs nothing for pages already read.

Run:
  PYTHONPATH=scripts ./venv/bin/python scripts/conf_abstracts/flatbed_ocr.py \\
      <pdf> --first-book-page 24 [--pages 44-137] [--workers 4]
"""
import argparse
import collections
import csv
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from conf_abstracts import config as C

DPI = 300
GAP = 100            # px at 300 dpi; MEASURED on 2001 pp. 58/87/88/98: debris gap 100-1000
OUT_DIR = C.OUT / "flatbed_text"


def gutters(pdf: Path):
    """Per PDF page: (page width pt, page height pt, gutter x in pt)."""
    html = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout
    out = []
    for p in html.split("<page ")[1:]:
        w = float(re.search(r'width="([\d.]+)"', p).group(1))
        h = float(re.search(r'height="([\d.]+)"', p).group(1))
        occ = [0] * (int(w) + 1)
        for a, b in re.findall(r'xMin="([\d.]+)" yMin="[\d.]+" xMax="([\d.]+)"', p):
            for x in range(int(float(a)), min(int(float(b)) + 1, len(occ))):
                occ[x] += 1
        lo, hi = int(0.4 * w), int(0.6 * w)
        best, start = (0, lo, lo), None
        for x in range(lo, hi + 1):
            if occ[x] == 0:
                start = x if start is None else start
            else:
                if start is not None and x - start > best[0]:
                    best = (x - start, start, x)
                start = None
        if start is not None and hi - start > best[0]:
            best = (hi - start, start, hi)
        out.append((w, h, (best[1] + best[2]) / 2))
    return out


def _ocr_half(pdf: Path, pdf_page: int, side: int, geom, tsv: Path):
    """Render one half of a spread, deskew it, and write tesseract's TSV."""
    if tsv.exists() and tsv.stat().st_size > 0:
        return
    w, h, cut = geom
    k = DPI / 72
    x0, x1 = (0, cut) if side == 0 else (cut, w)
    with tempfile.TemporaryDirectory() as td:
        img = Path(td) / "p"
        subprocess.run(["pdftoppm", "-f", str(pdf_page), "-l", str(pdf_page),
                        "-r", str(DPI), "-gray", "-singlefile",
                        "-x", str(int(x0 * k)), "-y", "0",
                        "-W", str(int((x1 - x0) * k)), "-H", str(int(h * k)),
                        str(pdf), str(img)], check=True)
        desk = Path(td) / "d.pgm"
        subprocess.run(["convert", f"{img}.pgm", "-background", "white",
                        "-deskew", "40%", "+repage", str(desk)], check=True)
        subprocess.run(["tesseract", str(desk), str(tsv.with_suffix("")),
                        "--psm", "4", "-l", "eng", "tsv"],
                       check=True, capture_output=True,
                       env={"OMP_THREAD_LIMIT": "1", "PATH": "/usr/bin:/bin"})


def tsv_lines(tsv: Path):
    """Text lines of one page, binding debris outside the text margins dropped.
    A blank line marks each tesseract paragraph break."""
    rows = [r for r in csv.DictReader(open(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
            if r["level"] == "5" and (r["text"] or "").strip()]
    lines = collections.OrderedDict()
    for r in rows:
        key = (int(r["block_num"]), int(r["par_num"]), int(r["line_num"]))
        left = int(r["left"])
        lines.setdefault(key, []).append((left, left + int(r["width"]), r["text"]))
    # Debris at the spiral edge sits ~100 px (8 mm) beyond the last real word;
    # justified word spacing never opens a gap that wide.
    for key, ws in lines.items():
        while len(ws) > 1 and ws[-1][0] - ws[-2][1] > GAP:
            ws.pop()
        while len(ws) > 1 and ws[1][0] - ws[0][1] > GAP:
            ws.pop(0)
    full = [ws for ws in lines.values() if len(ws) >= 8]
    if not full:
        return [" ".join(t for *_, t in ws) for ws in lines.values()]
    # the body is justified: the median full line marks both margins
    lm = sorted(ws[0][0] for ws in full)[len(full) // 2]
    rm = sorted(ws[-1][1] for ws in full)[len(full) // 2]
    out, prev = [], None
    for key, ws in lines.items():
        keep = [t for a, b, t in ws if b > lm - 30 and a < rm + 30]
        if prev and key[:2] != prev[:2]:
            out.append("")
        if keep:
            out.append(" ".join(keep))
        prev = key
    return out


def ocr_book(pdf: Path, first_book_page: int, pages=None, workers=4, out_dir=OUT_DIR):
    """OCR a spread-scanned book. Returns the path of the assembled text file.
    `pages` = (first, last) book pages to read; default all."""
    pdf = Path(pdf)
    cache = Path(out_dir) / pdf.stem
    cache.mkdir(parents=True, exist_ok=True)
    geoms = gutters(pdf)
    jobs = []
    for i, g in enumerate(geoms):
        for side in (0, 1):
            book = first_book_page + 2 * i + side
            if pages and not pages[0] <= book <= pages[1]:
                continue
            jobs.append((book, i + 1, side, g, cache / f"p{book:03d}.tsv"))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda j: _ocr_half(pdf, j[1], j[2], j[3], j[4]), jobs))
    parts = [f"\f=== PAGE {book} ===\n" + "\n".join(tsv_lines(tsv)) + "\n"
             for book, *_, tsv in sorted(jobs)]
    txt = Path(out_dir) / f"{pdf.stem}.txt"
    txt.write_text("".join(parts), encoding="utf-8")
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--first-book-page", type=int, required=True,
                    help="printed page number of the LEFT half of PDF page 1")
    ap.add_argument("--pages", default=None, help="book page range, e.g. 44-137")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    pages = tuple(int(x) for x in a.pages.split("-")) if a.pages else None
    print(ocr_book(Path(a.pdf), a.first_book_page, pages, a.workers))


if __name__ == "__main__":
    main()
