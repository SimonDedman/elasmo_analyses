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

# Books in scope. Each entry: (glob, meeting, society_hint, is_elasmo_meeting).
# EEA books are wholly elasmo (meeting=EEA -> AES society). The Cat/ folder holds
# the EEA abstract books; extend this list to sweep JMIH/ASIH/SI later.
SCOPE = [
    (str(C.REPO / "database/others_libraries/Cat/EEA*.pdf"), "EEA", "AES", True),
]


def _key(pdf: Path) -> str:
    """Stable short key from the filename, e.g. EEA2004_London -> EEA2004."""
    m = re.match(r"([A-Za-z]+)_?(\d{4})", pdf.stem)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return re.sub(r"[^A-Za-z0-9]+", "_", pdf.stem)[:32]


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


def build(only=None):
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    import glob as _glob
    worklist = []
    idx = 0
    for pattern, meeting, soc_hint, elasmo in SCOPE:
        for path in sorted(_glob.glob(pattern)):
            pdf = Path(path)
            if only and only.lower() not in pdf.name.lower():
                continue
            key = _key(pdf)
            text = pdftotext_layout(pdf)
            if len(text) < 1000:
                # corrupt/image-only PDF (2024/2025 have broken catalogs; awaiting
                # clean copies from Cat). Skip rather than burn a Fable agent.
                print(f"  SKIP {key} ({pdf.name}): only {len(text)} chars extracted")
                continue
            src = SRC_DIR / f"{key}.txt"
            src.write_text(text, encoding="utf-8")
            worklist.append(dict(
                index=idx,
                key=key,
                meeting=meeting,
                year=_year(pdf),
                city=_city(pdf),
                society_hint=soc_hint,
                is_elasmo_meeting=elasmo,
                source_pdf=str(pdf),
                src_txt=str(src),
                cache_path=str(CACHE_DIR / f"{key}.json"),
                n_chars=len(text),
            ))
            idx += 1
    WORKLIST.parent.mkdir(parents=True, exist_ok=True)
    WORKLIST.write_text(json.dumps(worklist, indent=2), encoding="utf-8")
    print(f"worklist: {len(worklist)} books -> {WORKLIST}")
    for w in worklist:
        done = "cached" if Path(w["cache_path"]).exists() else "     "
        print(f"  [{w['index']:2}] {done} {w['key']:10} {w['year']} "
              f"{(w['city'] or ''):14} ~{w['n_chars']//4:>6}tok")
    return worklist


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="filename substring filter")
    a = ap.parse_args()
    build(only=a.only)
