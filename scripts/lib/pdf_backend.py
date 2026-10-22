"""One PDF backend for the pipeline: pypdf, Poppler, and pdfminer.six.

WHY THIS MODULE EXISTS
----------------------
Until 21 Oct 2026 the scripts used PyMuPDF (``fitz`` / ``pymupdf``), which is
AGPL-3.0. The repository's code is Apache-2.0, so PyMuPDF was removed and every
PDF operation now goes through this module:

* structure (page count, page extraction, blank test files) uses **pypdf** (BSD);
* text and rendering use the **Poppler** command-line tools ``pdftotext`` and
  ``pdftoppm`` (run as separate processes; ``pdfinfo`` is a page-count fallback);
* the one caller that needs per-character font, size, and colour
  (``conf_abstracts/parse_eea.py``, EEA 2026 poster booklet) uses **pdfminer.six** (MIT).

The text mode and the render settings were chosen by an equivalence test
against PyMuPDF on 60 stratified corpus PDFs, 8,482 pages (MEASURED 21 Oct 2026;
``_licence_tests/REPORT.md`` in the licence-change worktree):

* page count: pypdf, pdfinfo, and PyMuPDF agree on 60/60;
* text, ``pdftotext -raw -cropbox``: per-page similarity to PyMuPDF median 100,
  5th percentile 99.6 (rapidfuzz ratio, whitespace-normalised); DOI-on-page-1
  and study-type verdicts agree on 60/60, fetch_free_sources-style title and
  surname verdicts on 59/60 (the one disagreement is a garbage OCR layer that
  both reject). Known weakness: on 63 of 7,143 text pages (17 PDFs) -raw runs
  words together where a line has no space glyphs, so token recall falls
  below 90 %. ``mode="layout"`` separates words better (29 pages, 9 PDFs) but
  interleaves columns; it is there for callers that need only a bag of words;
* rendering, ``pdftoppm -cropbox``: identical pixel dimensions on 60/60 first
  and last pages at 150 dpi; dedup pHash distance 0-6 bits (median 0);
* per-character spans (pdfminer.six): the EEA 2026 poster parse gives 29/29
  records, 28 identical to PyMuPDF's and one differing by a stray space.

Text is close to, but NOT byte-identical with, PyMuPDF's: anything that hashes
extracted text (dedup ``full_text_hash``) must not be compared across backends.

Page numbers in this API are 0-based, like PyMuPDF's.
"""
from __future__ import annotations

import io
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Iterator

logging.getLogger("pypdf").setLevel(logging.ERROR)

# pdftotext mode chosen by measurement (see module docstring). "raw" keeps
# content-stream order, which is what PyMuPDF's get_text() returns.
# Both pdftotext and pdftoppm are run with -cropbox: PyMuPDF clips text and
# renders to the CropBox, Poppler defaults to the MediaBox (measured: 8 of 60
# sample PDFs have a CropBox smaller than the MediaBox).
TEXT_MODE = "raw"
_MODE_FLAGS = {"raw": ["-raw"], "layout": ["-layout"], "reading": []}
# mode="pypdf" (pypdf extract_text) was also measured: order like -raw, fewer
# run-together words (41 pages), but ~4x slower and not clipped to the CropBox.
_TIMEOUT = 300


class PdfBackendError(RuntimeError):
    """A PDF could not be opened or read by the backend."""


def _need(tool: str) -> str:
    exe = shutil.which(tool)
    if exe is None:
        raise PdfBackendError(f"{tool} not found on PATH (install poppler-utils)")
    return exe


def _reader(path):
    from pypdf import PdfReader
    r = PdfReader(str(path), strict=False)
    if r.is_encrypted:
        r.decrypt("")  # owner-password-only files open with an empty user password
    return r


def _pdfinfo_pages(path) -> int:
    out = subprocess.run([_need("pdfinfo"), str(path)], capture_output=True,
                         text=True, errors="replace", timeout=_TIMEOUT)
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1])
    raise PdfBackendError(f"pdfinfo could not read {path}: {out.stderr.strip()[:200]}")


def page_count(path) -> int:
    """Number of pages. pypdf first; Poppler's pdfinfo if pypdf cannot parse the file.

    Raises PdfBackendError when neither can read it (PyMuPDF raised too)."""
    try:
        return len(_reader(path).pages)
    except Exception:  # noqa: BLE001 - pypdf raises many types on damaged files
        return _pdfinfo_pages(path)


def page_texts(path, first: int = 0, last: int | None = None,
               mode: str | None = None) -> list[str]:
    """Text of pages ``first``..``last`` inclusive (0-based), one string per page.

    ``last=None`` means the final page. Uses one pdftotext call. Raises
    PdfBackendError if pdftotext fails outright."""
    mode = mode or TEXT_MODE
    if mode == "pypdf":
        r = _reader(path)
        last = len(r.pages) - 1 if last is None else min(last, len(r.pages) - 1)
        out = []
        for k in range(first, last + 1):
            try:
                out.append(r.pages[k].extract_text() or "")
            except Exception:  # noqa: BLE001
                out.append("")
        return out
    flags = _MODE_FLAGS[mode]
    cmd = [_need("pdftotext"), *flags, "-cropbox", "-enc", "UTF-8", "-f", str(first + 1)]
    if last is not None:
        if last < first:
            return []
        cmd += ["-l", str(last + 1)]
    cmd += [str(path), "-"]
    proc = subprocess.run(cmd, capture_output=True, timeout=_TIMEOUT)
    if proc.returncode != 0 and not proc.stdout:
        raise PdfBackendError(f"pdftotext failed on {path}: "
                              f"{proc.stderr.decode('utf-8', 'replace').strip()[:200]}")
    pages = proc.stdout.decode("utf-8", "replace").split("\f")
    if pages and pages[-1] == "":
        pages.pop()  # pdftotext ends every page, including the last, with \f
    return pages


def page_text(path, pno: int, mode: str | None = None) -> str:
    """Text of one page (0-based); empty string if the page has none."""
    got = page_texts(path, pno, pno, mode)
    return got[0] if got else ""


def document_text(path, max_pages: int | None = None, sep: str = "",
                  mode: str | None = None) -> tuple[str, int]:
    """(text of the first ``max_pages`` pages joined by ``sep``, total page count)."""
    n = page_count(path)
    if n == 0:
        return "", 0
    last = n - 1 if max_pages is None else min(n, max_pages) - 1
    if last < 0:
        return "", n
    return sep.join(page_texts(path, 0, last, mode)), n


def render_page(path, pno: int, dpi: int = 150, gray: bool = False):
    """Render one page (0-based) to a PIL image at ``dpi``, white background, no alpha.

    Uses pdftoppm. Dimensions agree with PyMuPDF's get_pixmap at the same zoom to
    within 1 px (measured); antialiasing differs, so pixels are not identical."""
    import tempfile
    from PIL import Image
    cmd = [_need("pdftoppm"), "-r", str(dpi), "-f", str(pno + 1), "-l", str(pno + 1),
           "-singlefile", "-png", "-cropbox"]
    if gray:
        cmd.append("-gray")
    # pdftoppm 26.01 writes nothing to stdout for "-", so render to a one-page temp file.
    with tempfile.TemporaryDirectory(prefix="pdf_backend_") as td:
        root = Path(td) / "page"
        proc = subprocess.run(cmd + [str(path), str(root)], capture_output=True, timeout=_TIMEOUT)
        png = root.with_suffix(".png")
        if proc.returncode != 0 or not png.exists():
            raise PdfBackendError(f"pdftoppm failed on {path} page {pno + 1}: "
                                  f"{proc.stderr.decode('utf-8', 'replace').strip()[:200]}")
        img = Image.open(io.BytesIO(png.read_bytes()))
        img.load()
    return img


def extract_pages(src, pages: Iterable[int], dest) -> Path:
    """Write the given 0-based pages of ``src``, in the order given, to a new PDF ``dest``."""
    from pypdf import PdfWriter
    reader = _reader(src)
    writer = PdfWriter()
    for p in pages:
        writer.add_page(reader.pages[p])
    dest = Path(dest)
    with open(dest, "wb") as fh:
        writer.write(fh)
    return dest


def write_blank_pdf(dest, n_pages: int, width: float = 595, height: float = 842) -> Path:
    """A PDF of ``n_pages`` empty pages (A4 by default), for tests."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in range(n_pages):
        writer.add_blank_page(width=width, height=height)
    dest = Path(dest)
    with open(dest, "wb") as fh:
        writer.write(fh)
    return dest


# --- per-character spans (pdfminer.six) --------------------------------------

def _colour_int(col) -> int:
    """pdfminer non-stroking colour -> 0xRRGGBB, as PyMuPDF reports span colours."""
    if col is None:
        return 0
    if isinstance(col, (int, float)):
        col = (col,)
    try:
        vals = [float(v) for v in col]
    except (TypeError, ValueError):
        return 0
    if len(vals) == 1:
        r = g = b = vals[0]
    elif len(vals) == 3:
        r, g, b = vals
    elif len(vals) == 4:
        c, m, y, k = vals
        r, g, b = (1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)
    else:
        return 0
    to8 = lambda v: max(0, min(255, round(v * 255)))  # noqa: E731
    return (to8(r) << 16) | (to8(g) << 8) | to8(b)


def _font_name(name) -> str:
    name = str(name or "")
    if len(name) > 7 and name[6] == "+" and name[:6].isupper():
        name = name[7:]  # subset prefix "ABCDEF+", which PyMuPDF also strips
    return name


def iter_page_spans(path) -> Iterator[list[dict]]:
    """Per page, the text spans in PyMuPDF ``rawdict`` span shape.

    Each span is ``{"size", "font", "color", "bbox", "chars": [{"c", "bbox"}]}``
    with top-left-origin coordinates in points. A span is a run of characters
    in one text line with the same font, size, and colour. Spaces that
    pdfminer infers between words (no glyph in the file) are kept as zero-width
    characters at the end of the previous glyph. Sizes are pdfminer's glyph
    heights, which equal the font size for unrotated, unscaled text."""
    from pdfminer.high_level import extract_pages as _pm_pages
    from pdfminer.layout import LAParams, LTAnno, LTChar, LTTextLine

    def lines_of(obj):
        if isinstance(obj, LTTextLine):
            yield obj
            return
        try:
            for child in obj:
                yield from lines_of(child)
        except TypeError:
            return

    # all_texts=True: Canva-style PDFs put text inside Form XObjects (LTFigure),
    # which pdfminer leaves ungrouped otherwise (measured: EEA 2026 poster booklet).
    for layout in _pm_pages(str(path), laparams=LAParams(all_texts=True)):
        top = layout.y1
        spans: list[dict] = []
        for line in lines_of(layout):
            cur, last_box = None, None
            for item in line:
                if isinstance(item, LTChar):
                    key = (_font_name(item.fontname), round(item.size, 2),
                           _colour_int(getattr(item.graphicstate, "ncolor", None)))
                    box = (item.x0, top - item.y1, item.x1, top - item.y0)
                    if cur is None or cur["_key"] != key:
                        cur = {"_key": key, "font": key[0], "size": item.size,
                               "color": key[2], "bbox": list(box), "chars": []}
                        spans.append(cur)
                    cur["chars"].append({"c": item.get_text(), "bbox": box})
                    b = cur["bbox"]
                    cur["bbox"] = [min(b[0], box[0]), min(b[1], box[1]),
                                   max(b[2], box[2]), max(b[3], box[3])]
                    last_box = box
                elif isinstance(item, LTAnno) and item.get_text() == " " \
                        and cur is not None and last_box is not None:
                    x = last_box[2]
                    cur["chars"].append({"c": " ", "bbox": (x, last_box[1], x, last_box[3])})
        for s in spans:
            s.pop("_key", None)
            s["bbox"] = tuple(s["bbox"])
        yield spans
