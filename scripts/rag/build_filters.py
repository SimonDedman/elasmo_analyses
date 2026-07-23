#!/usr/bin/env python3
"""
Materialise the RAG filter sidecar + author index from the parquet and the
OpenAlex author CSVs. Fast (seconds), independent of the embedding index, and
re-runnable whenever the registry (filter_config.py) or the parquet changes.

Outputs (git-ignored, under outputs/rag/):
  paper_filters.parquet   literature_id + every registry-named filter column
  author_index.parquet    long form: openalex_author_id -> literature_id
  author_suggest.parquet  display_name, openalex_author_id, paper_count, norm

Run with the fashion-clip venv:
    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/build_filters.py
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PARQUET_PATH, PROJECT_ROOT, RAG_OUT_DIR  # noqa: E402
from filter_config import sidecar_columns  # noqa: E402

PAPER_FILTERS = RAG_OUT_DIR / "paper_filters.parquet"
AUTHOR_INDEX = RAG_OUT_DIR / "author_index.parquet"
AUTHOR_SUGGEST = RAG_OUT_DIR / "author_suggest.parquet"

PAPER_AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_paper_authors.csv"
UNIQUE_AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"


def clean_id(s) -> str:
    s = str(s)
    return s[:-2] if s.endswith(".0") else s


def norm_name(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", str(s))
                if not unicodedata.combining(c))
    return s.lower().strip()


def build_paper_filters() -> None:
    import pyarrow.parquet as pq
    all_cols = set(pq.read_schema(PARQUET_PATH).names)
    cols = sidecar_columns(all_cols)
    print(f"[filters] reading {len(cols)} columns from parquet ...")
    df = pd.read_parquet(PARQUET_PATH, columns=cols)
    df["literature_id"] = df["literature_id"].map(clean_id)
    df = df.drop_duplicates("literature_id", keep="first")
    df.to_parquet(PAPER_FILTERS, index=False)
    print(f"[filters] wrote {PAPER_FILTERS} — {len(df):,} papers x {len(cols)} cols")


def build_author_index() -> None:
    if not PAPER_AUTHORS_CSV.exists():
        print(f"[authors] {PAPER_AUTHORS_CSV} missing — skipping author index")
        return
    pa = pd.read_csv(PAPER_AUTHORS_CSV,
                     usecols=["literature_id", "openalex_author_id"],
                     dtype=str).dropna()
    pa["literature_id"] = pa["literature_id"].map(clean_id)
    pa = pa.drop_duplicates()
    pa.to_parquet(AUTHOR_INDEX, index=False)
    print(f"[authors] wrote {AUTHOR_INDEX} — {len(pa):,} author-paper links")

    if UNIQUE_AUTHORS_CSV.exists():
        ua = pd.read_csv(UNIQUE_AUTHORS_CSV,
                         usecols=["display_name", "openalex_author_id", "paper_count"],
                         dtype={"display_name": str, "openalex_author_id": str,
                                "paper_count": "Int64"})
    else:
        ua = (pa.groupby("openalex_author_id").size()
                .reset_index(name="paper_count"))
        ua["display_name"] = ua["openalex_author_id"]
    ua = ua.dropna(subset=["openalex_author_id", "display_name"])
    ua["norm"] = ua["display_name"].map(norm_name)
    ua = ua.sort_values("paper_count", ascending=False)
    ua.to_parquet(AUTHOR_SUGGEST, index=False)
    print(f"[authors] wrote {AUTHOR_SUGGEST} — {len(ua):,} unique authors")


def main() -> None:
    build_paper_filters()
    build_author_index()
    print("Done.")


if __name__ == "__main__":
    main()
