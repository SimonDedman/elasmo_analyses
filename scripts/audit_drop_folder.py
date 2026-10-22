#!/usr/bin/env python3
"""Audit a coauthor drop folder BEFORE anything is filed.

Every PDF is matched to a record (filename DOI first, then surname+year+title),
opened (OCR when there is no text layer), and identity-tested against that record:
title words found in the first pages AND the first author's surname present. Each
file gets exactly one bucket; the buckets double as the drop folder's problem
subfolders (see SUBFOLDERS), so the audit, the review page and the folder layout
use one vocabulary.

  python3 scripts/audit_drop_folder.py --folder DIR --person Andrew [--workers 6]

Writes outputs/dropaudit_<person>_<date>/audit.csv and coverage.json. Read-only:
it never files, moves or deletes anything. Resumable: rows already in audit.csv
(keyed by filename + size) are reused.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import pdf_backend  # noqa: E402  PDF access via scripts/lib/pdf_backend.py (pypdf + Poppler); PyMuPDF removed 21 Oct 2026 (AGPL).
import ingest_pdfs as ing  # noqa: E402

PROJECT = ing.PROJECT
QUEUE_JSON = PROJECT / "docs/papers_data.json"
PDF_MAP = PROJECT / "outputs/pdf_id_map.csv"
MERGED = PROJECT / "outputs/merged_records.csv"

# bucket -> drop-folder subfolder the file is moved into after the audit.
# "ingest" files are filed into the library and leave the drop folder entirely.
SUBFOLDERS = {
    "ingest": None,
    "duplicate_identical": "_duplicate-already-filed",   # byte-identical to the library copy
    "already_filed": "_already-filed-different-copy",    # record already has a PDF, bytes differ
    "review_comment": "_review-comment",                 # book review, comment, reply, discussion
    "correction": "_correction-erratum",                 # erratum / corrigendum / retraction notice
    "supplement": "_supplement-only",                    # supplementary material, not the paper
    "wrong_paper": "_wrong-paper",                       # PDF is another paper than the record
    "whole_volume": "_whole-volume-needs-split",          # issue/volume/book holding the record
    "no_record": "_not-in-database",                     # no record matches: new paper or off-list
    "unreadable": "_unreadable-scan",                    # no text even after OCR; cannot verify
    "abstract_only": "_abstract-only",                   # abstracting-journal entry / abstract, no full text
    "partial": "_partial-pages-missing",                 # pages of the paper missing (start, end or middle)
    "ambiguous": "_ambiguous-several-records",           # 2+ records pass identity (shared DOI, same title)
    "not_elasmo": "_not-elasmo",                         # reserved: set by hand at review
}

REVIEW_RX = re.compile(
    r"^\W*(book\s+reviews?|reviews?\s*[—–:-]|review of\b|reviewed by\b|comment on\b|"
    r"reply to\b|response to\b|discussion of\b|a reply\b|rejoinder\b)", re.I)
CORRECTION_RX = re.compile(r"\b(erratum|corrigendum|corrigenda|correction to|retraction)\b", re.I)
SUPPLEMENT_RX = re.compile(r"^\W*(supplementary|supporting information|electronic supplementary|"
                           r"appendix s\d|fig(ure)?\.?\s*s\d|table s\d)", re.I)


def squash(doi: str) -> str:
    """DOI reduced to lowercase alphanumerics, so 10.2307/1446270 == 10.2307-1446270."""
    return re.sub(r"[^a-z0-9]", "", (doi or "").lower())


def parse_name(fn: str) -> dict:
    stem = Path(fn).stem
    parts = stem.split("_", 2)
    out = {"surname": parts[0].replace("-", " ").strip(), "year": "", "doi_sq": "", "title_hint": ""}
    if len(parts) >= 2 and re.fullmatch(r"\d{4}", parts[1]):
        out["year"] = parts[1]
    rest = parts[2] if len(parts) == 3 else ""
    if rest.startswith("10."):
        out["doi_sq"] = squash(rest)
    else:
        out["title_hint"] = rest.replace("-", " ")
    return out


def sr_url_dois() -> dict[str, str]:
    """literature_id -> DOI taken from the master CSV's doi OR pdf_url (doi.org link)."""
    import glob
    csv.field_size_limit(10**9)
    files = sorted(glob.glob(str(PROJECT / "outputs/shark_references_bulk/shark_references_complete_*.csv")))
    out = {}
    if not files:
        return out
    with open(files[-1], newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = (r.get("doi") or "").strip()
            if not d:
                m = re.search(r"doi\.org/(10\.\d{4,9}/\S+)", r.get("pdf_url") or "", re.I)
                d = m.group(1) if m else ""
            if d:
                out[str(r.get("literature_id") or "").split(".")[0]] = d
    return out


def load_indexes() -> dict:
    rows, _doi_lookup, ay_lookup = ing.load_database()
    queue = json.loads(QUEUE_JSON.read_text())
    qrows = {str(r["literature_id"]): r for r in queue}
    by_id = {str(r["literature_id"]): r for r in rows}
    for lid, q in qrows.items():          # queue-only rows (recent SR adds) are records too
        by_id.setdefault(lid, {"literature_id": lid, "year": q.get("year"),
                               "authors": q.get("authors", ""), "title": q.get("title", ""),
                               "doi": q.get("doi", "")})
    by_doi: dict[str, list[str]] = {}
    for lid, r in by_id.items():
        if not r.get("doi") and lid in qrows:   # viz_data row blank, queue row carries the DOI
            r["doi"] = qrows[lid].get("doi", "")
        sq = squash(ing.normalise_doi(r.get("doi") or ""))
        if sq:
            by_doi.setdefault(sq, []).append(lid)
    # shark-references sometimes leaves `doi` blank and puts the DOI in `pdf_url`
    # (https://doi.org/...). Missed on 2026-10-12: record 35862 looked absent, and a
    # duplicate record was nearly created for a paper filed five days earlier.
    for lid, d in sr_url_dois().items():
        if lid in by_id and lid not in by_doi.get(squash(d), []):
            by_doi.setdefault(squash(d), []).append(lid)
    pdfmap: dict[str, str] = {}
    with open(PDF_MAP, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pdfmap.setdefault(str(r["literature_id"]), r["pdf"])
    merged = {}
    if MERGED.exists():
        with open(MERGED, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                a, b = r.get("literature_id") or r.get("merged_id"), r.get("merged_into")
                if a and b:
                    merged[str(a)] = str(b)
    return {"by_id": by_id, "by_doi": by_doi, "ay": ay_lookup, "queue": qrows,
            "pdfmap": pdfmap, "merged": merged}


IDX: dict = {}


def _init():
    global IDX
    IDX = load_indexes()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def page_text(p: Path, n: int = 3) -> tuple[str, int]:
    count = pdf_backend.page_count(p)
    txt = "\n".join(pdf_backend.page_texts(p, 0, min(n, count) - 1)) if count else ""
    return ing._strip_zero_width(txt), count


def surname_present(text: str, authors: str, fuzzy: bool = False) -> bool:
    """First author's surname as a capitalised word (Title or UPPER case), so the
    surname "Bone" is not found in the word "bone". fuzzy allows one OCR slip."""
    sn = ing.strip_accents(ing.extract_first_author(authors or ""))
    toks = [t for t in re.split(r"[\s-]+", sn) if len(t) >= 3]
    if not toks:
        return True
    t = ing.strip_accents(text)
    # no trailing \b: "Corradi1" (superscript affiliation digit) must still yield "Corradi"
    words = set(re.findall(r"(?<![A-Za-z])[A-Z][A-Za-z']+", t))
    for tok in toks:
        if tok in words or tok.upper() in words or tok.capitalize() in words:
            return True
        if fuzzy:
            import difflib
            cands = [w for w in words if abs(len(w) - len(tok)) <= 1]
            if difflib.get_close_matches(tok.lower(), [w.lower() for w in cands], n=1, cutoff=0.8):
                return True
    return False


def identity(text: str, rec: dict, fuzzy: bool) -> tuple[bool, bool, int, float, bool]:
    """(title_ok, surname_ok, overlap, ratio, doi_in_text).

    Title words: >= 80% of the record's title words in the first pages; >= 50% suffices
    when the record's DOI is printed in the text. Titles of 3 words or fewer must
    appear as a phrase, because "Biology of Fishes" matches almost any fish paper.
    """
    rtw = ing._title_words(rec.get("title") or "")
    ov = len(ing._title_words(text) & rtw) if rtw else 0
    ratio = ov / len(rtw) if rtw else 1.0
    dsq = squash(ing.normalise_doi(rec.get("doi") or ""))
    doi_in = bool(dsq) and len(dsq) > 8 and dsq in squash(text)
    if rtw and len(rtw) <= 3:
        norm = lambda x: " ".join(re.findall(r"[a-z0-9]+", ing.strip_accents(x).lower()))  # noqa: E731
        title_ok = norm(rec.get("title") or "") in norm(text) or doi_in
    else:
        title_ok = ratio >= 0.8 or (doi_in and ratio >= 0.5)
    return title_ok, surname_present(text, rec.get("authors"), fuzzy), ov, round(ratio, 2), doi_in


def candidates(info: dict) -> list[tuple[str, str]]:
    out = []
    if info["doi_sq"]:
        out += [(lid, "doi") for lid in IDX["by_doi"].get(info["doi_sq"], [])]
    if not out and info["year"]:
        key = f"{ing.strip_accents(info['surname'].split()[0]).lower()}_{info['year']}"
        out += [(str(r["literature_id"]), "author_year") for r in IDX["ay"].get(key, [])]
    return out


# Tried in turn when the standard OCR (ingest_pdfs.OCR_LANGS, six Latin-script
# languages) leaves a scan with no usable text. The best-scoring pass wins, so a
# Fraktur, Cyrillic or CJK scan is read and audited like any other file, and
# `_unreadable-scan` only ever holds files no installed language can read.
RELANG_SETS = ["Fraktur+deu", "rus+eng", "jpn+eng", "chi_sim+chi_tra+eng", "kor+eng", "nld+eng"]


def relang_ocr(p: Path) -> tuple[Path | None, str]:
    import subprocess
    best, best_alpha, best_lang = None, 0, ""
    for langs in RELANG_SETS:
        out = ing.OCR_CACHE / f"{sha256(p)[:16]}.{langs.replace('+', '_')}.pdf"
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(["ocrmypdf", "--force-ocr", "--output-type", "pdf", "--language", langs,
                                "--quiet", "--pages", "1-5", str(p), str(out)], capture_output=True)
            if r.returncode != 0 or not out.exists():
                continue
        text, _ = page_text(out, 5)
        # Score clean words, not letters: a wrong language pack emits plenty of
        # letters as noise (a CJK pack read a German page with more letters than
        # the Fraktur pack did). CJK text has no spaces, so count its characters.
        toks = text.split()
        clean = sum(1 for t in toks if re.fullmatch(r"[^\W\d_]{3,}[.,;:]?", t))
        cjk = sum(1 for c in text if "\u3040" <= c <= "\u9fff" or "\uac00" <= c <= "\ud7af")
        score = clean * (clean / max(len(toks), 1)) + cjk / 2
        if score > best_alpha:
            best, best_alpha, best_lang = out, score, langs
    return (best, best_lang) if best_alpha >= 40 else (None, "")


def audit_one(path_str: str) -> dict:
    p = Path(path_str)
    info = parse_name(p.name)
    row = {"filename": p.name, "size": p.stat().st_size, "surname": info["surname"],
           "year": info["year"], "doi_in_name": bool(info["doi_sq"]), "literature_id": "",
           "match": "", "queue_status": "", "pages": "", "ocr": False, "title_overlap": "",
           "surname_ok": "", "doi_in_text": "", "first_line": "", "lib_pdf": "", "sha256": "", "bucket": "",
           "reason": "", "candidates": ""}
    try:
        row["sha256"] = sha256(p)
        tp = ing.ensure_text_extractable(p)
        row["ocr"] = tp != p
        text, row["pages"] = page_text(tp)
        if row["pages"] > 30:   # scanned books: covers and library stamps before the title page
            text, _ = page_text(tp, 10)
    except Exception as e:  # noqa: BLE001
        row.update(bucket="unreadable", reason=f"open failed: {e}")
        return row
    if sum(c.isalpha() for c in text) < 200:
        tp2, langs = relang_ocr(p)
        if tp2:
            text, _ = page_text(tp2, 5)
            row["ocr"] = f"relang {langs}"
    first = " ".join(text.split())[:160]
    row["first_line"] = first
    alpha = sum(c.isalpha() for c in text)

    cands = candidates(info)
    # choose the candidate whose title the text agrees with best
    scored = []
    for lid, how in cands:
        lid = IDX["merged"].get(lid, lid)
        rec = IDX["by_id"].get(lid)
        if not rec:
            continue
        agrees, sn_ok, ov, ratio, doi_in = identity(text, rec, fuzzy=True)
        scored.append((agrees, sn_ok, ratio, lid, how, ov, doi_in))
    scored.sort(reverse=True)
    row["candidates"] = ";".join(s[3] for s in scored[:6])
    if not scored and info["title_hint"]:
        # no DOI and no author-year hit: title words from the filename against all rows
        hint = {"title": info["title_hint"]}
        for lid, rec in IDX["by_id"].items():
            if info["year"] and str(rec.get("year", "")).split(".")[0] != info["year"]:
                continue
            ok, _sn, ov, ratio, _d = identity(text, rec, fuzzy=True)
            if ok and ratio >= 0.8:
                scored.append((True, _sn, ratio, lid, "title_hint", ov, _d))
        scored.sort(reverse=True)

    if alpha < 200:
        row.update(bucket="unreadable", reason="no text after OCR in every installed language")
        if scored:
            row["literature_id"] = scored[0][3]
        return row
    if REVIEW_RX.search(first) or p.name.lower().startswith("book-review"):
        row["bucket"], row["reason"] = "review_comment", "page one opens as a review/comment/reply"
    elif SUPPLEMENT_RX.search(first):
        row["bucket"], row["reason"] = "supplement", "page one opens as supplementary material"
    elif CORRECTION_RX.search(first[:120]):
        row["bucket"], row["reason"] = "correction", "page one opens as a correction notice"
    if not scored:
        if not row["bucket"]:
            row.update(bucket="no_record", reason="no record matches the filename DOI or surname+year")
        return row

    agrees, sn_ok, ratio, lid, how, ov, doi_in = scored[0]
    rec = IDX["by_id"][lid]
    if agrees and not sn_ok:
        # notes and old papers print the byline at the END; chapters a page or two in
        full, _ = page_text(tp, 60)
        sn_ok = surname_present(full, rec.get("authors"), fuzzy=True)
    row.update(literature_id=lid, match=how, title_overlap=f"{ov} ({ratio:.0%})",
               surname_ok=sn_ok, doi_in_text=doi_in)
    q = IDX["queue"].get(lid)
    row["queue_status"] = q["last_status"] if q else ""
    lib = IDX["pdfmap"].get(lid, "")
    row["lib_pdf"] = lib
    if row["bucket"]:
        return row
    # Several records sharing one DOI (a queue DOI copied onto an abstract, a report
    # series, a duplicate record) all pass on title words. 2026-10-12: Davies 1960,
    # Stevenson 2004 and Mollen 2024 were filed under the wrong one of a tie.
    rivals = [s_ for s_ in scored[1:] if s_[0] and s_[1] and s_[2] >= ratio - 0.15]
    if agrees and sn_ok and rivals:
        row.update(bucket="ambiguous", reason="also passes: " + ", ".join(
            f"{s_[3]} ({s_[2]:.0%})" for s_ in rivals) + f"; chosen {lid} ({ratio:.0%})")
        return row
    if not (agrees and sn_ok):
        row.update(bucket="wrong_paper",
                   reason=f"record {lid}: title words {ov} ({ratio:.0%}), "
                          f"surname {'found' if sn_ok else 'absent'}, DOI {'in' if doi_in else 'not in'} text")
        return row
    vol = ing.whole_volume_reason(tp, {**rec, **(q or {})})
    if vol:
        row.update(bucket="whole_volume", reason=vol)
        return row
    if lib and Path(lib).exists():
        if sha256(Path(lib)) == row["sha256"]:
            row.update(bucket="duplicate_identical", reason="byte-identical to library copy")
        else:
            row.update(bucket="already_filed", reason="record already holds a different PDF")
        return row
    row.update(bucket="ingest", reason="on queue" if q else "record has no PDF (not on queue)")
    return row


FIELDS = ["filename", "size", "surname", "year", "doi_in_name", "literature_id", "match",
          "queue_status", "pages", "ocr", "title_overlap", "surname_ok", "doi_in_text", "first_line", "lib_pdf",
          "sha256", "bucket", "reason", "candidates"]


def list_pdfs(folder: Path, recursive: bool) -> list[Path]:
    """The delivery's PDFs. `_*` subfolders hold already-sorted problems and are never
    re-read; conference abstract books belong to the conference-abstracts pipeline."""
    import scan_coauthor_libraries as scan
    it = folder.rglob("*") if recursive else folder.iterdir()
    out = []
    for p in it:
        if not (p.is_file() and p.suffix.lower() == ".pdf"):
            continue
        parts = p.relative_to(folder).parts[:-1]
        if any(x.startswith("_") or x.lower() in scan.SKIP_SUBDIRS for x in parts):
            continue
        if scan.is_conference_book(p):
            continue
        out.append(p)
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", required=True, type=Path)
    ap.add_argument("--person", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--recursive", action="store_true",
                    help="include subfolders (never `_*` problem subfolders, programme folders or conference books)")
    a = ap.parse_args()
    out = a.out or PROJECT / f"outputs/dropaudit_{a.person}_{date.today():%Y-%m-%d}"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "audit.csv"
    done = {}
    if csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            done = {(r["filename"], r["size"]): r for r in csv.DictReader(f)}
    pdfs = list_pdfs(a.folder, a.recursive)
    rel = {p: str(p.relative_to(a.folder)) for p in pdfs}
    todo = [p for p in pdfs if (rel[p], str(p.stat().st_size)) not in done]
    print(f"{len(pdfs)} PDFs, {len(done)} already audited, {len(todo)} to do", flush=True)
    new_file = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        with ProcessPoolExecutor(a.workers, initializer=_init) as ex:
            futs = {ex.submit(audit_one, str(p)): p for p in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                try:
                    r = fu.result()
                except Exception as e:  # noqa: BLE001
                    r = {"filename": futs[fu].name, "size": futs[fu].stat().st_size,
                         "bucket": "unreadable", "reason": f"worker error: {e}"}
                r["filename"] = rel[futs[fu]]   # relative path: a delivery may use subfolders
                w.writerow(r)
                f.flush()
                print(f"[{i}/{len(todo)}] {r.get('bucket')}: {r['filename']}", flush=True)
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    from collections import Counter
    cov = {"folder": str(a.folder), "person": a.person, "generated": datetime.now().isoformat(timespec="seconds"),
           "in_scope": len(pdfs), "audited": len(rows), "not_attempted": len(pdfs) - len(rows),
           "by_bucket": dict(Counter(r["bucket"] for r in rows)),
           "subfolders": SUBFOLDERS}
    (out / "coverage.json").write_text(json.dumps(cov, indent=1))
    (out / "DONE").write_text(cov["generated"])
    print(json.dumps(cov["by_bucket"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
