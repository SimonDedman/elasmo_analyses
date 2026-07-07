#!/usr/bin/env python3
"""
Build a FAISS vector index over a sample of the SharkPapers PDF corpus, for
the RAG prototype.

Run with the fashion-clip venv (has pandas/pyarrow/sentence-transformers/faiss):

    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/build_index.py \
        --sample 300

Resumable: PDFs already recorded in outputs/rag/pdf_attempt_log.csv are
skipped on rerun (whether they matched, failed extraction, or were below the
title-overlap threshold), and chunks/embeddings already in
outputs/rag/chunks_meta.jsonl + embeddings.npy are kept and simply
re-combined with any newly processed papers. Re-run with a bigger --sample
to grow the index; use --force to ignore the attempt log and retry
everything.

Read-only w.r.t. papers_data.json and the parquet.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ATTEMPT_LOG_CSV, CHUNKS_JSONL, EMBED_MODEL_NAME, EMBEDDINGS_NPY,
    FAISS_INDEX_PATH, PDF_LIBRARY_DIR, build_surname_index, chunk_text,
    extract_text_from_pdf, load_metadata, match_pdf_to_paper,
    parse_library_filename,
)

ATTEMPT_FIELDS = [
    "pdf_path", "status", "literature_id", "title_overlap", "n_chunks",
]


def list_library_pdfs() -> list[Path]:
    pdfs = []
    for p in PDF_LIBRARY_DIR.rglob("*.pdf"):
        if any(part.startswith(".") for part in p.relative_to(PDF_LIBRARY_DIR).parts):
            continue
        pdfs.append(p)
    return pdfs


def load_attempt_log() -> dict[str, dict]:
    if not ATTEMPT_LOG_CSV.exists():
        return {}
    with open(ATTEMPT_LOG_CSV, newline="", encoding="utf-8") as f:
        return {row["pdf_path"]: row for row in csv.DictReader(f)}


def append_attempt_log(rows: list[dict]) -> None:
    exists = ATTEMPT_LOG_CSV.exists()
    with open(ATTEMPT_LOG_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ATTEMPT_FIELDS)
        if not exists:
            w.writeheader()
        w.writerows(rows)


def load_existing_chunks() -> list[dict]:
    if not CHUNKS_JSONL.exists():
        return []
    with open(CHUNKS_JSONL, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=300,
                    help="target number of NEWLY indexed papers this run")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-overlap", type=float, default=0.25)
    ap.add_argument("--force", action="store_true",
                     help="ignore attempt log, retry previously-seen PDFs")
    args = ap.parse_args()

    t0 = time.time()
    print(f"[1/6] Loading parquet metadata from outputs/literature_review_enriched.parquet ...")
    meta = load_metadata()
    surname_index = build_surname_index(meta)
    print(f"      {len(meta):,} papers loaded, {len(surname_index):,} surname tokens indexed")

    print(f"[2/6] Listing PDFs under {PDF_LIBRARY_DIR} ...")
    all_pdfs = list_library_pdfs()
    print(f"      {len(all_pdfs):,} PDFs found in library")

    attempted = {} if args.force else load_attempt_log()
    already_indexed_ids = {
        row["literature_id"] for row in attempted.values()
        if row["status"] == "indexed"
    }
    print(f"      {len(attempted):,} PDFs already attempted "
          f"({len(already_indexed_ids):,} already indexed) — will be skipped")

    candidates = [p for p in all_pdfs if str(p) not in attempted]
    rng = random.Random(args.seed)
    rng.shuffle(candidates)

    print(f"[3/6] Matching + extracting up to {args.sample} new papers "
          f"(oversampling from {len(candidates):,} unattempted candidates) ...")

    new_chunks: list[dict] = []
    new_attempt_rows: list[dict] = []
    n_indexed = 0
    n_unmatched = 0
    n_extract_fail = 0
    n_dup_literature_id = 0

    for pdf_path in candidates:
        if n_indexed >= args.sample:
            break

        parsed = parse_library_filename(pdf_path.stem)
        if parsed is None:
            new_attempt_rows.append({
                "pdf_path": str(pdf_path), "status": "unparseable_filename",
                "literature_id": "", "title_overlap": "", "n_chunks": 0,
            })
            n_unmatched += 1
            continue

        lit_id, score, reason = match_pdf_to_paper(
            parsed, meta, surname_index, min_overlap=args.min_overlap
        )
        if lit_id is None:
            new_attempt_rows.append({
                "pdf_path": str(pdf_path), "status": f"unmatched ({reason})",
                "literature_id": "", "title_overlap": f"{score:.2f}", "n_chunks": 0,
            })
            n_unmatched += 1
            continue

        if lit_id in already_indexed_ids:
            new_attempt_rows.append({
                "pdf_path": str(pdf_path), "status": "duplicate_of_indexed",
                "literature_id": lit_id, "title_overlap": f"{score:.2f}", "n_chunks": 0,
            })
            n_dup_literature_id += 1
            continue

        text = extract_text_from_pdf(pdf_path)
        if not text:
            new_attempt_rows.append({
                "pdf_path": str(pdf_path), "status": "extract_failed",
                "literature_id": lit_id, "title_overlap": f"{score:.2f}", "n_chunks": 0,
            })
            n_extract_fail += 1
            continue

        pieces = chunk_text(text)
        if not pieces:
            new_attempt_rows.append({
                "pdf_path": str(pdf_path), "status": "empty_after_chunking",
                "literature_id": lit_id, "title_overlap": f"{score:.2f}", "n_chunks": 0,
            })
            n_extract_fail += 1
            continue

        row = meta.loc[meta["literature_id"] == lit_id].iloc[0]
        for i, piece in enumerate(pieces):
            new_chunks.append({
                "literature_id": lit_id,
                "chunk_id": f"{lit_id}_{i}",
                "chunk_index": i,
                "title": row["title"],
                "authors": row["authors"],
                "year": row["year"],
                "journal": row["journal"],
                "doi": row["doi"],
                "pdf_path": str(pdf_path),
                "text": piece,
            })

        already_indexed_ids.add(lit_id)
        n_indexed += 1
        new_attempt_rows.append({
            "pdf_path": str(pdf_path), "status": "indexed",
            "literature_id": lit_id, "title_overlap": f"{score:.2f}",
            "n_chunks": len(pieces),
        })

    append_attempt_log(new_attempt_rows)
    print(f"      newly indexed: {n_indexed} | unmatched: {n_unmatched} | "
          f"extract failed: {n_extract_fail} | dup literature_id skipped: {n_dup_literature_id}")
    print(f"      new chunks produced: {len(new_chunks):,}")

    if not new_chunks:
        print("No new chunks to embed this run. Exiting (index unchanged).")
        return

    print(f"[4/6] Loading embedding model {EMBED_MODEL_NAME} on CPU ...")
    import torch
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")
    texts = [c["text"] for c in new_chunks]
    print(f"[5/6] Embedding {len(texts):,} new chunks on CPU (batch_size=32) ...")
    with torch.no_grad():
        new_vecs = model.encode(
            texts, batch_size=32, show_progress_bar=True,
            normalize_embeddings=True, convert_to_numpy=True,
        ).astype("float32")

    existing_chunks = load_existing_chunks()
    all_chunk_meta = existing_chunks + new_chunks

    if EMBEDDINGS_NPY.exists():
        old_vecs = np.load(EMBEDDINGS_NPY)
        all_vecs = np.vstack([old_vecs, new_vecs])
    else:
        all_vecs = new_vecs

    assert all_vecs.shape[0] == len(all_chunk_meta), (
        f"embedding/metadata count mismatch: {all_vecs.shape[0]} vs {len(all_chunk_meta)}"
    )

    print(f"[6/6] Writing {len(all_chunk_meta):,} total chunks "
          f"({len(existing_chunks):,} carried over + {len(new_chunks):,} new) "
          "and rebuilding FAISS index ...")

    with open(CHUNKS_JSONL, "w", encoding="utf-8") as f:
        for c in all_chunk_meta:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    np.save(EMBEDDINGS_NPY, all_vecs)

    import faiss
    index = faiss.IndexFlatIP(all_vecs.shape[1])
    index.add(all_vecs)
    faiss.write_index(index, str(FAISS_INDEX_PATH))

    n_papers = len({c["literature_id"] for c in all_chunk_meta})
    print(f"\nDone in {time.time() - t0:.1f}s.")
    print(f"Index now covers {n_papers:,} papers / {len(all_chunk_meta):,} chunks.")
    print(f"  FAISS index : {FAISS_INDEX_PATH}")
    print(f"  Chunk meta  : {CHUNKS_JSONL}")
    print(f"  Embeddings  : {EMBEDDINGS_NPY}")
    print(f"  Attempt log : {ATTEMPT_LOG_CSV}")


if __name__ == "__main__":
    main()
