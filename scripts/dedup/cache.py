"""SQLite-backed feature cache.

Usage:
    cache = FeatureCache("outputs/pdf_features.sqlite")
    if cache.is_fresh("2019/file.pdf", size, mtime):
        feat = cache.get("2019/file.pdf")
    else:
        feat = extract_features(pdf_path)
        cache.put(feat)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .schema import EXTRACTOR_VERSION, SCHEMA_SQL, PdfFeatures


class FeatureCache:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def is_fresh(self, rel_path: str, size_bytes: int, mtime: float) -> bool:
        row = self._conn.execute(
            "SELECT size_bytes, mtime, extractor_version FROM pdf_features WHERE rel_path = ?",
            (rel_path,),
        ).fetchone()
        if row is None:
            return False
        return (
            row["size_bytes"] == size_bytes
            and abs(row["mtime"] - mtime) < 1.0
            and row["extractor_version"] == EXTRACTOR_VERSION
        )

    def get(self, rel_path: str) -> Optional[PdfFeatures]:
        row = self._conn.execute(
            "SELECT * FROM pdf_features WHERE rel_path = ?", (rel_path,)
        ).fetchone()
        if row is None:
            return None
        return PdfFeatures.from_row(dict(row))

    def bulk_get(self, rel_paths: Iterable[str]) -> dict[str, PdfFeatures]:
        rel_paths = list(rel_paths)
        if not rel_paths:
            return {}
        placeholders = ",".join("?" * len(rel_paths))
        rows = self._conn.execute(
            f"SELECT * FROM pdf_features WHERE rel_path IN ({placeholders})",
            rel_paths,
        ).fetchall()
        return {r["rel_path"]: PdfFeatures.from_row(dict(r)) for r in rows}

    def put(self, feat: PdfFeatures) -> None:
        row = feat.to_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row)
        updates = ", ".join(f"{k}=excluded.{k}" for k in row if k != "rel_path")
        self._conn.execute(
            f"INSERT INTO pdf_features ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(rel_path) DO UPDATE SET {updates}",
            row,
        )
        self._conn.commit()

    def put_many(self, feats: Iterable[PdfFeatures]) -> None:
        for f in feats:
            self.put(f)

    def find_by_sha256(self, digest: str) -> list[PdfFeatures]:
        rows = self._conn.execute(
            "SELECT * FROM pdf_features WHERE bytes_sha256 = ?", (digest,)
        ).fetchall()
        return [PdfFeatures.from_row(dict(r)) for r in rows]

    def find_by_doi(self, doi: str) -> list[PdfFeatures]:
        rows = self._conn.execute(
            "SELECT * FROM pdf_features WHERE extracted_doi = ?", (doi.lower(),)
        ).fetchall()
        return [PdfFeatures.from_row(dict(r)) for r in rows]

    def all_paths(self) -> list[str]:
        return [r[0] for r in self._conn.execute("SELECT rel_path FROM pdf_features")]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM pdf_features").fetchone()[0]
