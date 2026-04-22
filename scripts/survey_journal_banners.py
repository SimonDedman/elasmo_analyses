#!/usr/bin/env python3
"""Survey first-page banner text across journals to inform study_type classifier.

For every journal in the corpus with >=MIN_PAPERS PDFs on disk, rank the
papers by extraction richness (sum of binary schema columns), sample the top
SAMPLE_PER_JOURNAL, extract the first page's banner zone, and print a tabular
report.

Output: outputs/journal_banner_survey.md
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
LIB = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
PARQUET = PROJECT / "outputs" / "literature_review_enriched.parquet"
OUTPUT = PROJECT / "outputs" / "journal_banner_survey.md"

MIN_PAPERS = 20           # only survey journals with >=20 papers
SAMPLE_PER_JOURNAL = 6    # banners to capture per journal
BANNER_CHARS = 600        # first N chars of page 1 to inspect


# --------------------------------------------------------------------------
# Rank papers by extraction richness
# --------------------------------------------------------------------------

_BIN_PREFIXES = ("eco_", "pr_", "gear_", "imp_", "d_", "b_", "sb_")


def richness_scores(df: pd.DataFrame) -> pd.Series:
    bin_cols = [c for c in df.columns if c.startswith(_BIN_PREFIXES)]
    # coerce non-bool columns to 0/1
    bools = df[bin_cols].apply(
        lambda s: s.fillna(0).astype(bool).astype(int) if s.dtype != bool else s.astype(int)
    )
    return bools.sum(axis=1)


# --------------------------------------------------------------------------
# PDF filename index
# --------------------------------------------------------------------------

_FNAME_RE = re.compile(
    r"^([A-Za-zÀ-ÿ'\-]+?)[.\- ](?:etal\.)?(\d{4})\.(.+)\.pdf$",
    re.IGNORECASE,
)

_STOP = {
    "the", "a", "an", "of", "and", "or", "in", "on", "to", "for", "from",
    "with", "at", "by", "using", "sharks", "shark", "rays", "ray",
}


def _toks(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", s or "") if w.lower() not in _STOP}


def build_pdf_index() -> dict[tuple[str, str], list[tuple[Path, set[str]]]]:
    idx: dict[tuple[str, str], list[tuple[Path, set[str]]]] = defaultdict(list)
    for pdf in LIB.rglob("*.pdf"):
        m = _FNAME_RE.match(pdf.name)
        if not m:
            continue
        surname = m.group(1).lower().strip("-.' ")
        year = m.group(2)
        title_toks = _toks(m.group(3))
        idx[(surname, year)].append((pdf, title_toks))
    return idx


def locate_pdf(authors: str, year, title: str, idx: dict) -> Path | None:
    first = str(authors or "").split("&")[0].strip()
    m = re.match(r"([A-Za-zÀ-ÿ'\-]+)", first)
    if not m:
        return None
    surname = m.group(1).lower()
    y = str(int(year)) if pd.notna(year) else ""
    cands = idx.get((surname, y), [])
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0][0]
    # Disambiguate by title-token overlap
    q_toks = _toks(title)
    best = max(cands, key=lambda c: len(q_toks & c[1]))
    if len(q_toks & best[1]) >= 1:
        return best[0]
    return cands[0][0]


# --------------------------------------------------------------------------
# Banner extraction
# --------------------------------------------------------------------------

def extract_banner(pdf_path: Path) -> str:
    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return ""
        text = doc[0].get_text()
        doc.close()
    except Exception as exc:
        return f"<error: {exc}>"
    # Collapse whitespace; take first BANNER_CHARS
    clean = re.sub(r"\s+", " ", text).strip()
    return clean[:BANNER_CHARS]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    print("Loading parquet…", file=sys.stderr)
    df = pd.read_parquet(PARQUET)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"].notna()]
    df["journal"] = df["journal"].fillna("(no journal)").astype(str)

    print("Scoring richness…", file=sys.stderr)
    df["_rich"] = richness_scores(df)

    print("Indexing PDFs…", file=sys.stderr)
    pdf_idx = build_pdf_index()

    # Filter to papers with a PDF match
    print("Matching parquet rows to PDFs…", file=sys.stderr)
    df["_pdf_path"] = df.apply(
        lambda r: locate_pdf(r["authors"], r["year"], r["title"], pdf_idx), axis=1
    )
    df_pdf = df[df["_pdf_path"].notna()].copy()
    print(f"  {len(df_pdf):,} parquet rows matched to a PDF", file=sys.stderr)

    # Rank journals by count
    counts = df_pdf["journal"].value_counts()
    eligible = counts[counts >= MIN_PAPERS]
    print(f"  {len(eligible):,} journals with >={MIN_PAPERS} PDF'd papers", file=sys.stderr)

    # For each journal, sample top-richness papers and extract banner
    lines: list[str] = []
    lines.append(f"# Journal banner survey ({len(eligible):,} journals, top {SAMPLE_PER_JOURNAL} richest per journal)\n")
    lines.append(f"Generated {pd.Timestamp.today():%Y-%m-%d}. Minimum {MIN_PAPERS} PDF'd papers per journal.\n")
    lines.append(f"Banner = first {BANNER_CHARS} chars of page 1 (whitespace-collapsed).\n\n")

    for journal in eligible.index:
        sub = df_pdf[df_pdf["journal"] == journal].nlargest(SAMPLE_PER_JOURNAL, "_rich")
        lines.append(f"## {journal} · {len(df_pdf[df_pdf['journal']==journal]):,} PDFs total\n\n")
        for _, r in sub.iterrows():
            lid = r["literature_id"]
            yr = int(r["year"])
            title = str(r["title"])[:90]
            richness = int(r["_rich"])
            banner = extract_banner(r["_pdf_path"])
            lines.append(f"- **{lid}** ({yr}) · richness={richness} · _{title}_\n")
            lines.append(f"    ```\n    {banner[:450]}\n    ```\n")
        lines.append("\n")

    OUTPUT.write_text("".join(lines), encoding="utf-8")
    print(f"\nWrote {OUTPUT.relative_to(PROJECT)}")
    print(f"  {len(eligible):,} journals surveyed, {sum(min(SAMPLE_PER_JOURNAL, eligible[j]) for j in eligible.index):,} banners captured")


if __name__ == "__main__":
    main()
