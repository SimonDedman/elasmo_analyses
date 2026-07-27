"""Orchestrate the conference-abstracts pipeline over the Carylanne PDFs.

Per PDF: classify -> (optional) ensure_ocr -> segment -> extract -> tag -> load.
Then export parquet/JSON/xlsx. Writes progress to logs/conf_abstracts.log and a
machine-readable summary to outputs/conf_abstracts_run_summary.json (which the
agent reads to post Marine-calendar milestone/failure events).

Usage:
  python -m conf_abstracts.run_pipeline [--only GLOB] [--no-llm] [--reocr]
Run from the repo's scripts/ dir on sys.path, e.g.:
  ./venv/bin/python scripts/conf_abstracts/run_pipeline.py --no-llm
"""
import argparse
import fnmatch
import json
import sys
import time
import traceback
from pathlib import Path

# make the package importable when run as a plain script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conf_abstracts import (config, schema, classify, qa_ocr, segment,
                            extract, tag, load, export, ingest_si_xlsx)


def log(msg):
    config.LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with open(config.LOG, "a") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def list_pdfs(only=None):
    pdfs = []
    for d, is_ocr in ((config.DIGITISED, False), (config.UNDIGITISED, True)):
        if d.exists():
            # case-insensitive: catch both .pdf and .PDF
            seen = set()
            for p in sorted(d.iterdir()):
                if p.suffix.lower() != ".pdf" or p.name in seen:
                    continue
                seen.add(p.name)
                if only and not fnmatch.fnmatch(p.name, only):
                    continue
                pdfs.append((p, is_ocr))
    return pdfs


def fmt_for(meta):
    return "asih_book" if meta["meeting"] == "ASIH" else "jmih_book"


def process_pdf(con, path, is_ocr, use_llm, do_reocr):
    meta = classify.classify_pdf(path, is_ocr=is_ocr)
    # Route conferences with a structured xlsx source to the xlsx ingester
    # instead of parsing the PDF (SI programmes ship as spreadsheets).
    key = (meta["meeting"], meta["year"])
    if key in config.SI_SOURCES:
        xlsx = config.SI_SOURCES[key]
        smeta = dict(meta)
        smeta["source_pdf"] = xlsx
        smeta["doc_type"] = "abstract_book"
        smeta["parse_status"] = "ok"
        n = ingest_si_xlsx.ingest_si_xlsx(con, xlsx, smeta)
        # SI2026: merge abstract bodies from the companion PDF (matched by id)
        try:
            from conf_abstracts import parse_si_pdf
            body_pdf = qa_ocr.extract_text(config.SI2026_BODY_PDF)
            parse_si_pdf.merge_pdf_bodies(con, body_pdf, meta["meeting"], meta["year"])
        except Exception as e:
            log(f"  SI2026 body merge skipped: {e}")
        return dict(pdf=path.name, meeting=meta["meeting"], year=meta["year"],
                    doc_type="xlsx", blocks=n, inserted=n, status="ok")

    # SI abstract-book PDFs with a dedicated parser (matched by filename).
    for frag, (mtg, yr, mod) in config.SI_PDF_PARSERS.items():
        if frag in path.name:
            import importlib
            parser = importlib.import_module(f"conf_abstracts.{mod}")
            smeta = dict(meta)
            smeta["meeting"], smeta["year"] = mtg, yr
            smeta["source_pdf"] = str(path)
            text = qa_ocr.extract_text(path)
            n = parser.ingest_si2018(con, text, smeta)
            return dict(pdf=path.name, meeting=mtg, year=yr, doc_type="pdf_parser",
                        blocks=n, inserted=n, status="ok")
    if do_reocr:
        q = qa_ocr.ensure_ocr(path)
        if q.get("reocr"):
            log(f"  re-OCR {path.name}: {q['before']['status']} -> "
                f"{q.get('after',{}).get('status')}")
    text = qa_ocr.extract_text(path)
    fmt = fmt_for(meta)
    blocks = segment.segment_blocks(text, fmt)
    meta["parse_status"] = "ok" if blocks else "partial"
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in blocks:
        try:
            rec = extract.extract_fields(b, meta["meeting"], fmt, use_llm=use_llm)
            rec = tag.resolve(rec, meta["meeting"])
            # if LLM said elasmo but society resolution didn't catch it
            if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
                rec["is_elasmo"] = 1
                rec["elasmo_basis"] = "content"
            if load.insert_abstract(con, mid, rec):
                n += 1
        except Exception as e:
            log(f"    block error in {path.name}: {e}")
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return dict(pdf=path.name, meeting=meta["meeting"], year=meta["year"],
                doc_type=meta["doc_type"], blocks=len(blocks), inserted=n,
                status=meta["parse_status"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="filename glob")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--reocr", action="store_true", help="re-OCR poor PDFs first")
    ap.add_argument("--db", default=str(config.DB_PATH))
    args = ap.parse_args()

    con = schema.create_db(args.db)
    pdfs = list_pdfs(args.only)
    log(f"=== run start: {len(pdfs)} PDFs, llm={not args.no_llm}, reocr={args.reocr} ===")
    results, failures = [], []
    for path, is_ocr in pdfs:
        try:
            r = process_pdf(con, path, is_ocr, not args.no_llm, args.reocr)
            results.append(r)
            log(f"OK {r['pdf']}: {r['inserted']} abstracts ({r['status']})")
        except Exception as e:
            failures.append(dict(pdf=path.name, error=str(e)))
            log(f"FAIL {path.name}: {e}")
            traceback.print_exc()

    total = sum(r["inserted"] for r in results)
    n_elasmo = con.execute("SELECT count(*) FROM abstracts WHERE is_elasmo=1").fetchone()[0]

    config.OUT.mkdir(parents=True, exist_ok=True)
    pq = config.OUT / "conference_abstracts_elasmo.parquet"
    js = config.OUT / "conference_abstracts.json"
    xl = config.OUT / "conference_abstracts.xlsx"
    export.to_parquet_elasmo(con, pq)
    export.to_json(con, js)
    export.to_xlsx(con, xl)

    summary = dict(
        pdfs=len(pdfs), processed=len(results), failed=len(failures),
        total_abstracts=total, elasmo_abstracts=n_elasmo,
        results=results, failures=failures,
        exports=dict(parquet=str(pq), json=str(js), xlsx=str(xl)),
        db=args.db, llm=not args.no_llm,
    )
    (config.OUT / "conf_abstracts_run_summary.json").write_text(
        json.dumps(summary, indent=2))
    log(f"=== DONE: {total} abstracts ({n_elasmo} elasmo) from "
        f"{len(results)}/{len(pdfs)} PDFs, {len(failures)} failed ===")
    log("RUN COMPLETE")


if __name__ == "__main__":
    main()
