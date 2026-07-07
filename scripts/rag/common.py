#!/usr/bin/env python3
"""
Shared config, PDF<->parquet matching, text extraction and chunking helpers
for the RAG prototype (scripts/rag/build_index.py, scripts/rag/query.py).

Must be run with an interpreter that has pandas/pyarrow/sentence-transformers/
faiss installed. On this machine that is the shared "fashion-clip" venv:

    /home/simon/.venvs/fashion-clip/bin/python scripts/rag/build_index.py

Read-only with respect to papers_data.json and the enriched parquet — this
module only ever reads outputs/literature_review_enriched.parquet.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PDF_LIBRARY_DIR = Path(
    "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
)
PARQUET_PATH = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"

RAG_OUT_DIR = PROJECT_ROOT / "outputs" / "rag"
RAG_OUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNKS_JSONL = RAG_OUT_DIR / "chunks_meta.jsonl"
EMBEDDINGS_NPY = RAG_OUT_DIR / "embeddings.npy"
FAISS_INDEX_PATH = RAG_OUT_DIR / "index.faiss"
ATTEMPT_LOG_CSV = RAG_OUT_DIR / "pdf_attempt_log.csv"

# Embedding model: BGE-small is retrieval-tuned (asymmetric query/passage
# training) and small enough (33M params, 384-dim) to embed comfortably on
# CPU. Requires a query-side instruction prefix (BGE_QUERY_PREFIX) — passages
# are embedded with no prefix.
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBED_DIM = 384

# Local Ollama server (user-local install, no sudo, no systemd — see
# docs/LLM/rag_prototype_status.md for how it was started).
OLLAMA_HOST = "http://127.0.0.1:11435"
OLLAMA_MODEL = "qwen2.5:3b-instruct"

TEXT_TIMEOUT = 15  # seconds for pdftotext
MAX_TEXT_BYTES = 2_000_000  # cap very long PDFs (books etc.)

CHUNK_WORDS = 650   # ~850-900 tokens for scientific English
CHUNK_OVERLAP_WORDS = 100

_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "using",
    "were", "are", "was", "have", "has", "not", "but", "their", "its",
    "which", "these", "those", "than", "then", "also", "such", "can",
    "may", "based", "between", "among", "during", "after", "before",
    "when", "where", "while", "about", "over", "under", "more", "most",
    "some", "each", "both", "other", "different", "various", "study",
    "studies", "paper", "results", "data", "used", "use",
}


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def words_of(text: str, min_len: int = 4) -> set[str]:
    words = re.findall(r"[a-z]{%d,}" % min_len, strip_accents(text).lower())
    return {w for w in words if w not in _STOPWORDS}


# ---------------------------------------------------------------------------
# Parquet metadata
# ---------------------------------------------------------------------------

META_COLUMNS = [
    "literature_id", "title", "authors", "year", "doi", "journal",
]


def load_metadata() -> pd.DataFrame:
    """Read-only load of the enriched parquet, kept to the columns we need."""
    df = pd.read_parquet(PARQUET_PATH, columns=META_COLUMNS)
    df["literature_id"] = df["literature_id"].astype(str)

    def _year_int(y):
        try:
            return int(float(y))
        except (TypeError, ValueError):
            return None

    df["year_int"] = df["year"].map(_year_int)
    df["authors_lower"] = df["authors"].fillna("").map(
        lambda s: strip_accents(str(s)).lower()
    )
    df["title_words"] = df["title"].fillna("").map(words_of)
    return df


def build_surname_index(meta: pd.DataFrame) -> dict[str, list[int]]:
    """Map first-author surname token -> list of dataframe row positions.

    Indexes on every alphabetic token >=3 chars found before the first
    comma/semicolon/"and"/"&" of the authors string, which covers the common
    "Surname, F." and "Surname F, Other O." conventions used upstream.
    """
    index: dict[str, list[int]] = {}
    for pos, authors_lower in enumerate(meta["authors_lower"].tolist()):
        if not authors_lower:
            continue
        first_chunk = re.split(r"[;,]| and | & ", authors_lower)[0]
        for tok in re.findall(r"[a-z]{3,}", first_chunk):
            index.setdefault(tok, []).append(pos)
    return index


# ---------------------------------------------------------------------------
# Filename parsing: library convention "Surname[.etal].Year.Title frag.pdf"
# ---------------------------------------------------------------------------

_FNAME_RE = re.compile(
    r"^([A-Za-zÀ-ſ'\-]+)\.(?:etal\.)?(1[6-9]\d{2}|20\d{2})\.(.+)$"
)


def parse_library_filename(stem: str) -> dict | None:
    m = _FNAME_RE.match(stem)
    if not m:
        return None
    surname, year, title_frag = m.groups()
    surname_norm = strip_accents(surname).lower()
    # hyphenated/compound surnames (e.g. "Valderrama-Herrera") won't match
    # the surname_index verbatim since that index is built from individual
    # alpha tokens — split the same way so lookups line up.
    surname_tokens = re.findall(r"[a-z]{3,}", surname_norm) or [surname_norm]
    return {
        "surname": surname_norm,
        "surname_tokens": surname_tokens,
        "year": int(year),
        "title_words": words_of(title_frag),
    }


def match_pdf_to_paper(
    parsed: dict, meta: pd.DataFrame, surname_index: dict[str, list[int]],
    min_overlap: float = 0.25,
) -> tuple[str | None, float, str]:
    """Return (literature_id, title_overlap_score, reason)."""
    candidates: set[int] = set()
    for tok in parsed.get("surname_tokens", [parsed["surname"]]):
        candidates.update(surname_index.get(tok, []))
    if not candidates:
        return None, 0.0, "no surname match"

    year = parsed["year"]
    best_id, best_score = None, 0.0
    for pos in candidates:
        row_year = meta["year_int"].iat[pos]
        if row_year is not None and abs(row_year - year) > 1:
            continue
        row_title_words = meta["title_words"].iat[pos]
        qwords = parsed["title_words"]
        if not qwords or not row_title_words:
            continue
        overlap = len(qwords & row_title_words) / len(qwords)
        if overlap > best_score:
            best_score = overlap
            best_id = meta["literature_id"].iat[pos]

    if best_id is not None and best_score >= min_overlap:
        return best_id, best_score, "matched"
    return None, best_score, "below title-overlap threshold"


# ---------------------------------------------------------------------------
# PDF text extraction (mirrors extract_schema_columns.py's approach)
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=TEXT_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        text = result.stdout
        if not text or not text.strip():
            return None
        if len(text.encode("utf-8", errors="ignore")) > MAX_TEXT_BYTES:
            text = text[:MAX_TEXT_BYTES]
        return text
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def chunk_text(
    text: str, chunk_words: int = CHUNK_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Word-based sliding-window chunking (~850-900 tokens/chunk, overlap)."""
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(chunk_words - overlap_words, 1)
    for start in range(0, len(words), step):
        chunk = words[start:start + chunk_words]
        if len(chunk) < 40 and chunks:
            # trailing sliver too small to be useful on its own — drop
            break
        chunks.append(" ".join(chunk))
        if start + chunk_words >= len(words):
            break
    return chunks
