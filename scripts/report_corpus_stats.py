#!/usr/bin/env python3
"""Derive the project's headline figures from the artifacts themselves.

The same seven-or-so numbers (corpus size, PDFs, evidence rows, authors,
column counts, techniques, RAG index) are quoted in the README, the pipeline
overview, docs/results.html, the slide deck, viz_pipeline_diagram.R, project
memory, and every grant application. Until now each was hand-typed, so they
drifted apart: as of 2026-08-06 the author count appeared as 28,334, 28,953,
and 29,929 in three surfaces, and the technique count was quoted as 208 from a
database table that is empty.

This script is the single source of truth. It writes:

  outputs/corpus_stats.json   machine-readable, for anything that can read it
  outputs/corpus_stats.md     the markdown table to paste into the docs

Run it after any pipeline stage that changes the corpus (monthly sync,
extraction, enrichment, RAG rebuild), then re-sync the surfaces listed in
`docs/core/pipeline_overview.md` under "Where these numbers appear".

Usage:
    python3 scripts/report_corpus_stats.py [--json-only]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_LIBRARY = Path(
    "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
)

# Prefix -> human label, for the column-family breakdown.
FAMILIES = {
    "sp_": "species",
    "a_": "analytical technique",
    "sb_": "sub-basin",
    "gear_": "fishing gear",
    "pr_": "pressure / threat",
    "imp_": "impact / response",
    "eco_": "ecosystem",
    "d_": "discipline",
    "geo_": "geography",
    "b_": "ocean basin (text-mined)",
    "ob_": "ocean basin (geo pipeline)",
    "depth_": "depth",
}


def _warn(msg: str) -> None:
    print(f"  ! {msg}", file=sys.stderr)


def parquet_stats() -> dict:
    path = ROOT / "outputs" / "literature_review_enriched.parquet"
    if not path.exists():
        _warn(f"missing {path}")
        return {}
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    counts = Counter()
    for name in names:
        for prefix in FAMILIES:
            if name.startswith(prefix):
                counts[prefix] += 1
                break
    return {
        "papers": pf.metadata.num_rows,
        "columns": len(names),
        "column_families": {
            prefix: {"label": FAMILIES[prefix], "columns": counts[prefix]}
            for prefix in FAMILIES
            if counts[prefix]
        },
    }


def evidence_stats() -> dict:
    path = ROOT / "outputs" / "schema_extraction_evidence.csv"
    if not path.exists():
        _warn(f"missing {path}")
        return {}
    import pandas as pd

    # Only the id column is needed; reading it alone keeps this cheap.
    df = pd.read_csv(path, usecols=["literature_id"], low_memory=False)
    return {"rows": int(len(df)), "papers": int(df["literature_id"].nunique())}


def author_stats() -> dict:
    path = ROOT / "outputs" / "openalex_unique_authors.csv"
    if not path.exists():
        _warn(f"missing {path}")
        return {}
    import pandas as pd

    return {"unique_authors": int(len(pd.read_csv(path, low_memory=False)))}


def technique_stats() -> dict:
    # NOTE: the `techniques` table in database/technique_taxonomy.db is EMPTY.
    # The live list is the CSV. Docs quoting "208 techniques in the taxonomy
    # DB" are wrong in both the number and the location.
    path = ROOT / "data" / "master_techniques.csv"
    if not path.exists():
        _warn(f"missing {path}")
        return {}
    import pandas as pd

    return {"techniques": int(len(pd.read_csv(path)))}


def pdf_stats() -> dict:
    if not PDF_LIBRARY.exists():
        _warn(f"PDF library not mounted at {PDF_LIBRARY}")
        return {}
    # Raw file count. Over-counts supplementary files and duplicates; it is an
    # upper bound on distinct papers held, not a paper count.
    return {"pdf_files_on_disk": sum(1 for _ in PDF_LIBRARY.rglob("*.pdf"))}


def rag_stats() -> dict:
    path = ROOT / "outputs" / "rag" / "build_status.json"
    if not path.exists():
        _warn(f"missing {path}")
        return {}
    status = json.loads(path.read_text())
    return {
        "papers_indexed": status.get("papers_indexed"),
        "chunks": status.get("chunks_indexed"),
        "complete": status.get("complete"),
    }


def conference_stats() -> dict:
    path = ROOT / "database" / "conference_abstracts.db"
    if not path.exists():
        _warn(f"missing {path}")
        return {}
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        one = lambda q: con.execute(q).fetchone()[0]  # noqa: E731
        return {
            "meetings": one("SELECT COUNT(*) FROM meetings"),
            "abstracts": one("SELECT COUNT(*) FROM abstracts"),
            "elasmo_abstracts": one(
                "SELECT COUNT(*) FROM abstracts WHERE is_elasmo = 1"
            ),
            "author_rows": one("SELECT COUNT(*) FROM authors"),
        }
    finally:
        con.close()


def build() -> dict:
    print("Deriving corpus figures...", file=sys.stderr)
    return {
        "generated": date.today().isoformat(),
        "parquet": parquet_stats(),
        "evidence": evidence_stats(),
        "authors": author_stats(),
        "techniques": technique_stats(),
        "pdfs": pdf_stats(),
        "rag": rag_stats(),
        "conference_abstracts": conference_stats(),
    }


def as_markdown(s: dict) -> str:
    pq_ = s.get("parquet", {})
    fam = pq_.get("column_families", {})
    ev = s.get("evidence", {})
    rag = s.get("rag", {})
    conf = s.get("conference_abstracts", {})

    def n(v):
        return f"{v:,}" if isinstance(v, int) else "n/a"

    rows = [
        ("Papers catalogued", n(pq_.get("papers")), "rows in the enriched parquet"),
        ("Parquet columns", n(pq_.get("columns")), "all families plus metadata"),
        (
            "PDF files on disk",
            n(s.get("pdfs", {}).get("pdf_files_on_disk")),
            "raw count; over-counts supplements and duplicates",
        ),
        (
            "Evidence rows",
            n(ev.get("rows")),
            f"audit trail across {n(ev.get('papers'))} papers",
        ),
        (
            "Unique authors (OpenAlex)",
            n(s.get("authors", {}).get("unique_authors")),
            "`outputs/openalex_unique_authors.csv`",
        ),
        (
            "Techniques in taxonomy",
            n(s.get("techniques", {}).get("techniques")),
            "`data/master_techniques.csv` (NOT the taxonomy DB, whose table is empty)",
        ),
        (
            "Species columns",
            n(fam.get("sp_", {}).get("columns")),
            "`sp_` prefix",
        ),
        (
            "RAG index",
            f"{n(rag.get('papers_indexed'))} papers / {n(rag.get('chunks'))} chunks",
            "`outputs/rag/build_status.json`",
        ),
        (
            "Conference abstracts",
            n(conf.get("abstracts")),
            f"{n(conf.get('elasmo_abstracts'))} chondrichthyan, "
            f"{n(conf.get('meetings'))} meetings",
        ),
    ]

    out = [
        f"<!-- Generated by scripts/report_corpus_stats.py on {s['generated']}."
        " Do not hand-edit. -->",
        "",
        "| Metric | Value | Notes |",
        "|--------|------:|-------|",
    ]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    out += [
        "",
        "Column families:",
        "",
        "| Prefix | Meaning | Columns |",
        "|--------|---------|--------:|",
    ]
    out += [
        f"| `{p}` | {d['label']} | {d['columns']:,} |" for p, d in fam.items()
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    stats = build()
    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)

    json_path = out_dir / "corpus_stats.json"
    json_path.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"wrote {json_path}", file=sys.stderr)

    if not args.json_only:
        md = as_markdown(stats)
        md_path = out_dir / "corpus_stats.md"
        md_path.write_text(md)
        print(f"wrote {md_path}", file=sys.stderr)
        print()
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
