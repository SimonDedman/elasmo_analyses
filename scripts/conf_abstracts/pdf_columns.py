"""Column-aware text extraction for multi-column scanned abstract books.

`pdftotext -layout` on a two-column page emits BOTH columns on the same line
("<col1 sentence>    <col2 sentence>"), interleaving two unrelated abstracts.
Fable copes, but it wastes tokens on padding and blurs the title/author/body
boundaries the extraction depends on.

This module finds each page's column gutters geometrically (the x positions
that almost no word bounding box crosses), then runs `pdftotext -layout` once
per column strip, so the text comes out in true reading order: column 1 top to
bottom, then column 2.

Measured on 1998_JMIH_AbstractBook (Carylanne's flatbed scan, 2026-08-28):
the abstract pages 20-129 are uniformly 2-column with a gutter at x=384 that
only 31 of 178,318 words cross (0.017%).

Deliberately opt-in per book (config.COLUMN_BOOKS) — re-extracting an already
Fable-cached book would change its text, invalidate the cache, and re-chunk it.
"""
import re
import subprocess
from pathlib import Path

_PAGE_RE = re.compile(r'<page width="([0-9.]+)" height="([0-9.]+)"')
_WORD_RE = re.compile(r'xMin="([0-9.]+)" yMin="[0-9.]+" xMax="([0-9.]+)"')


def page_geometry(pdf: Path, page: int):
    """(page_width, page_height, [(xMin, xMax), ...]) for one page."""
    out = subprocess.run(
        ["pdftotext", "-bbox", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
    m = _PAGE_RE.search(out)
    if not m:
        return None, None, []
    words = [(float(a), float(b)) for a, b in _WORD_RE.findall(out)]
    return float(m.group(1)), float(m.group(2)), words


def detect_gutters(width, words, max_cross_frac=0.005, min_words=30):
    """x positions splitting the page into columns: valleys in the count of
    words whose bounding box straddles x. Returns [] if the page is single
    column or too sparse to judge."""
    if len(words) < min_words or not width:
        return []
    lo, hi = int(width * 0.10), int(width * 0.90)
    thr = max(2, int(max_cross_frac * len(words)))
    prof = {c: sum(1 for x0, x1 in words if x0 < c < x1) for c in range(lo, hi, 2)}
    cuts, c = [], lo
    while c < hi:
        if prof.get(c, 10 ** 9) <= thr:
            start = c
            while c < hi and prof.get(c, 10 ** 9) <= thr:
                c += 2
            cuts.append((start + c - 2) // 2)
        else:
            c += 2
    return cuts


def extract_page_columns(pdf: Path, page: int, gutters):
    """`pdftotext -layout` once per column strip, concatenated in reading order."""
    width, height, _ = page_geometry(pdf, page)
    if not width:
        return ""
    bounds = [0] + list(gutters) + [int(width) + 2]
    parts = []
    for i in range(len(bounds) - 1):
        x0, x1 = bounds[i], bounds[i + 1]
        txt = subprocess.run(
            ["pdftotext", "-layout", "-f", str(page), "-l", str(page),
             "-x", str(int(x0)), "-y", "0", "-W", str(int(x1 - x0)),
             "-H", str(int(height) + 2), str(pdf), "-"],
            capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
        # strip the per-strip trailing form feed and the leading gutter padding
        txt = txt.replace("\f", "")
        txt = "\n".join(line.rstrip() for line in txt.splitlines())
        if txt.strip():
            parts.append(txt.strip("\n"))
    return "\n\n".join(parts)


def extract(pdf: Path, first=1, last=None, fixed_gutters=None, verbose=False):
    """Whole-document column-aware text. `fixed_gutters` pins the split (use it
    when the pages are known-uniform); otherwise gutters are detected per page."""
    if last is None:
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True).stdout.decode()
        last = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    pages = []
    for p in range(first, last + 1):
        if fixed_gutters is not None:
            gut = list(fixed_gutters)
        else:
            w, _h, words = page_geometry(pdf, p)
            gut = detect_gutters(w, words)
        txt = extract_page_columns(pdf, p, gut)
        if verbose:
            print(f"  p{p}: {len(gut) + 1} col(s) gutters={gut} -> {len(txt)} chars")
        pages.append(txt)
    return "\f".join(pages)
