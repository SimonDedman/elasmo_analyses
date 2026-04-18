"""Shared feature schema.

Every extractor writes into one of these fields; `fusion.py` reads them.
Bump EXTRACTOR_VERSION whenever an extractor's semantics change so the
cache knows to re-run.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from typing import Optional


EXTRACTOR_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pdf_features (
    rel_path TEXT PRIMARY KEY,
    size_bytes INTEGER NOT NULL,
    mtime REAL NOT NULL,

    bytes_sha256 TEXT,
    tlsh_hash TEXT,

    page_count INTEGER DEFAULT 0,
    is_corrupted INTEGER NOT NULL DEFAULT 0,
    outline_depth INTEGER DEFAULT 0,
    outline_top_count INTEGER DEFAULT 0,
    looks_like_book INTEGER DEFAULT 0,

    xmp_title TEXT,
    xmp_subject TEXT,
    xmp_keywords TEXT,
    xmp_doi TEXT,
    xmp_type TEXT,
    info_title TEXT,
    info_subject TEXT,
    info_producer TEXT,

    extracted_doi TEXT,
    doi_source TEXT,
    crossref_type TEXT,
    crossref_title TEXT,
    crossref_container TEXT,
    crossref_year INTEGER,

    phash_p1 TEXT,
    dhash_p1 TEXT,
    phash_last TEXT,

    text_word_count INTEGER DEFAULT 0,
    text_is_extractable INTEGER DEFAULT 0,
    ocr_triggered INTEGER DEFAULT 0,
    minhash BLOB,
    detected_language TEXT,
    first_page_text_lower TEXT,
    full_text_hash TEXT,

    specter_embedding BLOB,

    extractor_errors TEXT,
    extracted_at REAL NOT NULL,
    extractor_version INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sha256 ON pdf_features(bytes_sha256);
CREATE INDEX IF NOT EXISTS idx_doi ON pdf_features(extracted_doi);
CREATE INDEX IF NOT EXISTS idx_phash ON pdf_features(phash_p1);
"""


@dataclass
class PdfFeatures:
    """One row in the feature cache. Mirrors the SQL schema 1:1."""

    rel_path: str
    size_bytes: int = 0
    mtime: float = 0.0

    bytes_sha256: Optional[str] = None
    tlsh_hash: Optional[str] = None

    page_count: int = 0
    is_corrupted: bool = False
    outline_depth: int = 0
    outline_top_count: int = 0
    looks_like_book: bool = False

    xmp_title: Optional[str] = None
    xmp_subject: Optional[str] = None
    xmp_keywords: Optional[str] = None
    xmp_doi: Optional[str] = None
    xmp_type: Optional[str] = None
    info_title: Optional[str] = None
    info_subject: Optional[str] = None
    info_producer: Optional[str] = None

    extracted_doi: Optional[str] = None
    doi_source: Optional[str] = None  # "xmp", "text_regex", "pdf2doi", "crossref_title"
    crossref_type: Optional[str] = None  # journal-article, correction, supplement, etc.
    crossref_title: Optional[str] = None
    crossref_container: Optional[str] = None
    crossref_year: Optional[int] = None

    phash_p1: Optional[str] = None  # 16-hex perceptual hash of page 1
    dhash_p1: Optional[str] = None
    phash_last: Optional[str] = None

    text_word_count: int = 0
    text_is_extractable: bool = False
    ocr_triggered: bool = False
    minhash: Optional[bytes] = None  # packed datasketch MinHash (128 uint32)
    detected_language: Optional[str] = None
    first_page_text_lower: Optional[str] = None  # truncated to 8 KB
    full_text_hash: Optional[str] = None  # SHA-256 of normalized extracted text

    specter_embedding: Optional[bytes] = None  # 768 * float32 = 3072 bytes

    extractor_errors: Optional[str] = None  # json-encoded list
    extracted_at: float = 0.0
    extractor_version: int = EXTRACTOR_VERSION

    def to_row(self) -> dict:
        d = asdict(self)
        for k in ("is_corrupted", "text_is_extractable", "ocr_triggered", "looks_like_book"):
            d[k] = int(d[k])
        return d

    @classmethod
    def from_row(cls, row: dict) -> "PdfFeatures":
        d = dict(row)
        for k in ("is_corrupted", "text_is_extractable", "ocr_triggered", "looks_like_book"):
            if k in d and d[k] is not None:
                d[k] = bool(d[k])
        return cls(**{k: d.get(k) for k in (f.name for f in fields(cls))})

    @classmethod
    def column_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]
