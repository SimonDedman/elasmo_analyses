#!/usr/bin/env python3
"""
Build/grow the RAG FAISS index from the pre-extracted Fable text cache
(outputs/validation/.fable_texts/<literature_id>.txt) instead of re-running
pdftotext + fuzzy filename matching.

Why this exists (see docs/superpowers/specs/2026-07-11-rag-schema-filters-web-
frontend-design.md): the .fable_texts cache already holds ~19,882 papers'
full text keyed EXACTLY by literature_id, so this path skips text extraction
entirely and joins metadata by exact id (no 86%-fuzzy-match loss). Embedding
on CPU is still the wall-clock floor.

CHECKPOINTING: unlike build_index.py (single write at the end), this writes the
index atomically every --checkpoint-every papers, so a server can hot-reload a
growing index while the build is still running. Resumable: on restart it reads
the existing chunks_meta/embeddings and skips literature_ids already indexed
(so it coexists with, and grows on top of, whatever build_index.py produced).

Run with the fashion-clip venv:

    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/build_from_cache.py \
        --checkpoint-every 500
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CHUNKS_JSONL, EMBED_MODEL_NAME, EMBEDDINGS_NPY, FABLE_TEXTS_DIR,
    FABLE_TEXTS_MANIFEST, FAISS_INDEX_PATH, RAG_OUT_DIR, chunk_text,
    load_metadata,
)

BUILD_STATUS_JSON = RAG_OUT_DIR / "build_status.json"
DEDUPE_SKIPPED_CSV = RAG_OUT_DIR / "dedupe_skipped.csv"
# literature_id -> PDF sha its chunks were embedded from; lets an incremental run
# notice a record whose PDF the id map reassigned and re-embed it
INDEXED_MANIFEST = RAG_OUT_DIR / "indexed_manifest.json"
EVICTED_CSV = RAG_OUT_DIR / "evicted.csv"


def load_text_shas() -> dict[str, str]:
    """literature_id -> SHA-1 of the PDF its cached text came from (prepass
    manifest). Empty when the manifest has not been written yet."""
    import csv
    out: dict[str, str] = {}
    if FABLE_TEXTS_MANIFEST.exists():
        with open(FABLE_TEXTS_MANIFEST, newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("sha"):
                    out[r["lit_id"]] = r["sha"]
    return out


def clean_id(s: str) -> str:
    """Normalise a literature_id string, stripping a trailing float '.0'."""
    s = str(s)
    return s[:-2] if s.endswith(".0") else s


def load_existing() -> tuple[list[dict], np.ndarray | None]:
    chunks: list[dict] = []
    if CHUNKS_JSONL.exists():
        with open(CHUNKS_JSONL, encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f if line.strip()]
    vecs = np.load(EMBEDDINGS_NPY) if EMBEDDINGS_NPY.exists() else None
    if vecs is not None and vecs.shape[0] != len(chunks):
        # Inconsistent prior state — safer to start the vector store fresh than
        # to misalign metadata with embeddings.
        print(f"  WARNING: {vecs.shape[0]} vecs vs {len(chunks)} chunks on disk "
              "— ignoring prior state and rebuilding from scratch.")
        return [], None
    return chunks, vecs


def atomic_write(all_chunks: list[dict], all_vecs: np.ndarray) -> None:
    import faiss

    tmp_chunks = CHUNKS_JSONL.with_name(CHUNKS_JSONL.name + ".tmp")
    with open(tmp_chunks, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    os.replace(tmp_chunks, CHUNKS_JSONL)

    tmp_npy = EMBEDDINGS_NPY.with_name(EMBEDDINGS_NPY.name + ".tmp.npy")
    np.save(tmp_npy, all_vecs)
    os.replace(tmp_npy, EMBEDDINGS_NPY)

    index = faiss.IndexFlatIP(all_vecs.shape[1])
    index.add(all_vecs)
    tmp_faiss = FAISS_INDEX_PATH.with_name(FAISS_INDEX_PATH.name + ".tmp")
    faiss.write_index(index, str(tmp_faiss))
    os.replace(tmp_faiss, FAISS_INDEX_PATH)


def write_indexed_manifest(indexed_shas: dict[str, str], lids: set[str], shas: dict[str, str]) -> None:
    for lid in lids:
        if lid in shas:
            indexed_shas[lid] = shas[lid]
    tmp = INDEXED_MANIFEST.with_name(INDEXED_MANIFEST.name + ".tmp")
    tmp.write_text(json.dumps(indexed_shas))
    os.replace(tmp, INDEXED_MANIFEST)


def write_status(papers: int, chunks: int, total_papers: int, done: bool) -> None:
    tmp = BUILD_STATUS_JSON.with_name(BUILD_STATUS_JSON.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "papers_indexed": papers,
            "chunks_indexed": chunks,
            "target_papers": total_papers,
            "complete": done,
            "updated_epoch": int(time.time()),
        }, f)
    os.replace(tmp, BUILD_STATUS_JSON)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-dir", default=str(FABLE_TEXTS_DIR))
    ap.add_argument("--checkpoint-every", type=int, default=500,
                    help="atomically rewrite the index after this many new papers")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap new papers this run (for testing)")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore any index already in RAG_OUT_DIR and build from "
                         "nothing (point RAG_OUT_DIR at a new directory so the live "
                         "index keeps serving; scripts/rag/sync_index.sh --rebuild does this)")
    args = ap.parse_args()

    t0 = time.time()
    text_dir = Path(args.text_dir)
    print(f"[1/4] Loading parquet metadata ...")
    meta = load_metadata()
    meta = meta.assign(_lid=meta["literature_id"].map(clean_id))
    meta = meta.drop_duplicates("_lid", keep="first").set_index("_lid")
    print(f"      {len(meta):,} unique literature_ids in parquet")

    print(f"[2/4] Loading existing index state ...")
    if args.fresh:
        all_chunks, existing_vecs = [], None
        print("      --fresh: starting from an empty index")
    else:
        all_chunks, existing_vecs = load_existing()
    shas = load_text_shas()
    indexed_shas: dict[str, str] = {}
    if INDEXED_MANIFEST.exists() and not args.fresh:
        try:
            indexed_shas = json.loads(INDEXED_MANIFEST.read_text())
        except (OSError, ValueError):
            indexed_shas = {}
    # Evict records whose text is gone (quarantined by the prepass) or whose PDF
    # changed since they were embedded; they re-enter below if a text exists now.
    evict: dict[str, str] = {}
    if all_chunks:
        for lid in {clean_id(c["literature_id"]) for c in all_chunks}:
            if not (text_dir / f"{lid}.txt").exists():
                evict[lid] = "text_gone"
            elif lid in indexed_shas and shas.get(lid) and shas[lid] != indexed_shas[lid]:
                evict[lid] = "pdf_changed"
        if evict:
            keep = np.array([clean_id(c["literature_id"]) not in evict for c in all_chunks])
            all_chunks = [c for c, k in zip(all_chunks, keep) if k]
            if existing_vecs is not None:
                existing_vecs = existing_vecs[keep]
            import csv
            with open(EVICTED_CSV, "a", newline="") as fh:
                w = csv.writer(fh)
                if fh.tell() == 0:
                    w.writerow(["literature_id", "reason", "evicted_at"])
                w.writerows([lid, why, time.strftime("%Y-%m-%d %H:%M")] for lid, why in sorted(evict.items()))
            for lid in evict:
                indexed_shas.pop(lid, None)
            print(f"      evicted {len(evict):,} papers ({sum(v == 'text_gone' for v in evict.values()):,} text gone, "
                  f"{sum(v == 'pdf_changed' for v in evict.values()):,} PDF changed) -> {EVICTED_CSV.name}")
    evicted_any = bool(evict)
    indexed_ids = {clean_id(c["literature_id"]) for c in all_chunks}
    vec_blocks: list[np.ndarray] = [existing_vecs] if existing_vecs is not None else []
    print(f"      {len(indexed_ids):,} papers already indexed (carried over)")

    txt_ids = sorted(
        (p.stem for p in text_dir.glob("*.txt")
         if p.stem not in indexed_ids and p.stem in meta.index),
        key=lambda x: (len(x), x),
    )
    # One PDF, one set of chunks. Byte-identical PDFs under two records (the
    # library hard-links its duplicates) would otherwise put the same passage
    # in the index twice, cited to two papers. The first record keeps it; the
    # others are listed in dedupe_skipped.csv so the omission is visible.
    sha_owner: dict[str, str] = {}
    for lid in indexed_ids:
        if lid in shas:
            sha_owner.setdefault(shas[lid], lid)
    # Two different PDF files can still yield identical text (the same paper
    # downloaded twice, or two records for one paper); hash the text as well.
    import hashlib
    text_owner: dict[str, str] = {}
    for lid in indexed_ids:
        try:
            text_owner.setdefault(hashlib.sha1((text_dir / f"{lid}.txt").read_bytes()).hexdigest(), lid)
        except OSError:
            continue
    kept, skipped = [], []
    for lid in txt_ids:
        sha = shas.get(lid)
        if sha and sha in sha_owner and sha_owner[sha] != lid:
            skipped.append((lid, sha_owner[sha], sha))
            continue
        try:
            th = hashlib.sha1((text_dir / f"{lid}.txt").read_bytes()).hexdigest()
        except OSError:
            continue
        if th in text_owner and text_owner[th] != lid:
            skipped.append((lid, text_owner[th], f"text:{th}"))
            continue
        text_owner.setdefault(th, lid)
        if sha:
            sha_owner.setdefault(sha, lid)
        kept.append(lid)
    txt_ids = kept
    if skipped:
        import csv
        new_file = not DEDUPE_SKIPPED_CSV.exists() or args.fresh
        with open(DEDUPE_SKIPPED_CSV, "w" if new_file else "a", newline="") as fh:
            w = csv.writer(fh)
            if new_file:
                w.writerow(["literature_id", "same_as", "sha_or_text_hash"])
            w.writerows(skipped)
        print(f"      {len(skipped):,} papers share a PDF with one already indexed "
              f"-> skipped (see {DEDUPE_SKIPPED_CSV.name})")
    if args.limit:
        txt_ids = txt_ids[:args.limit]
    total_target = len(indexed_ids) + len(txt_ids)
    print(f"[3/4] {len(txt_ids):,} new papers to index from {text_dir}")
    if not txt_ids:
        print("      Nothing new to index. Exiting.")
        if evicted_any:
            atomic_write(all_chunks, np.vstack(vec_blocks) if vec_blocks else np.zeros((0, 384), "float32"))
        write_indexed_manifest(indexed_shas, indexed_ids, shas)
        write_status(len(indexed_ids), len(all_chunks), total_target, True)
        return

    print(f"[4/4] Loading embedding model {EMBED_MODEL_NAME} on CPU ...")
    import torch
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")

    pending_meta: list[dict] = []
    papers_since_ckpt = 0
    n_new = 0

    def flush(final: bool = False) -> None:
        nonlocal pending_meta, papers_since_ckpt
        if not pending_meta:
            if final:
                n_papers = len({clean_id(c["literature_id"]) for c in all_chunks})
                write_status(n_papers, len(all_chunks), total_target, True)
            return
        with torch.no_grad():
            vecs = model.encode(
                [m["text"] for m in pending_meta], batch_size=args.batch_size,
                normalize_embeddings=True, convert_to_numpy=True,
                show_progress_bar=False,
            ).astype("float32")
        all_chunks.extend(pending_meta)
        vec_blocks.append(vecs)
        combined = np.vstack(vec_blocks)
        atomic_write(all_chunks, combined)
        write_indexed_manifest(indexed_shas, {clean_id(m["literature_id"]) for m in pending_meta}, shas)
        n_papers = len({clean_id(c["literature_id"]) for c in all_chunks})
        write_status(n_papers, len(all_chunks), total_target, final)
        print(f"      checkpoint: {n_papers:,} papers / {len(all_chunks):,} chunks "
              f"({time.time() - t0:.0f}s elapsed)")
        pending_meta = []
        papers_since_ckpt = 0

    for lid in txt_ids:
        try:
            text = (text_dir / f"{lid}.txt").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        pieces = chunk_text(text)
        if not pieces:
            continue
        row = meta.loc[lid]
        for i, piece in enumerate(pieces):
            pending_meta.append({
                "literature_id": lid,
                "chunk_id": f"{lid}_{i}",
                "chunk_index": i,
                "title": row["title"],
                "authors": row["authors"],
                "year": row["year"],
                "journal": row["journal"],
                "doi": row["doi"],
                "pdf_path": str(text_dir / f"{lid}.txt"),
                "text": piece,
            })
        n_new += 1
        papers_since_ckpt += 1
        if papers_since_ckpt >= args.checkpoint_every:
            flush()

    flush(final=True)
    n_papers = len({clean_id(c["literature_id"]) for c in all_chunks})
    print(f"\nDone in {time.time() - t0:.0f}s. Index now covers "
          f"{n_papers:,} papers / {len(all_chunks):,} chunks.")


if __name__ == "__main__":
    main()
