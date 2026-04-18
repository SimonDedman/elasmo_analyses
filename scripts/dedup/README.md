# Dedup v8 — confidence-scored PDF deduplication

Rule-based + visual + semantic pipeline for deciding whether two PDFs
are the same paper, a supplementary-material pair, a corrigendum, a
book/chapter pair, or genuinely distinct. Every decision comes with a
confidence in `[0, 1]` and the list of signals that produced it.

## Architecture

```
scripts/
├── dedup/
│   ├── schema.py          PdfFeatures dataclass + SQLite DDL
│   ├── cache.py           FeatureCache (SQLite, incremental)
│   ├── fusion.py          evaluate_pair(f1, f2) -> PairDecision
│   ├── ingest_hook.py     check_new_pdf() for ingestion pipeline
│   └── extractors/
│       ├── __init__.py    orchestrator: extract_features(pdf_path)
│       ├── hashes.py      SHA-256 + TLSH
│       ├── structure.py   pikepdf page count + outline + XMP/Info
│       ├── visual.py      pymupdf render + imagehash pHash/dHash
│       ├── text.py        pymupdf text + datasketch MinHash + langdetect
│       ├── ocr.py         ocrmypdf fallback for scanned PDFs
│       └── doi.py         DOI regex + pdf2doi + CrossRef enrichment
├── build_features.py      corpus indexer (multi-process, incremental)
├── evaluate_duplicates_v8.py  workbook scorer (writes v8_* cols)
└── check_new_pdf.py       CLI for ingest integration
```

## Setup

Dependencies (already installed via `pip --user --break-system-packages`):

```
pikepdf pymupdf imagehash datasketch pdf2doi langdetect python-tlsh
ocrmypdf tesseract-ocr rapidfuzz pandas openpyxl
```

Optional: `sentence-transformers + allenai/specter2` for semantic
embedding scoring (not wired yet — the feature column exists but the
extractor is a stub).

## Typical workflow

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# 1. Build the feature cache (incremental; first run ~30 min for 2.5k PDFs
#    with 6 workers; subsequent runs skip unchanged files)
python3 scripts/build_features.py --workers 6

# 2. Score the duplicates tab (adds v8_decision / v8_confidence / v8_signals)
python3 scripts/evaluate_duplicates_v8.py

# 3. Open outputs/pdf_library_audit.xlsx and review rows sorted by
#    v8_confidence DESC. Trust rows at confidence >= 0.85, spot-check
#    the 0.55 - 0.85 band, ignore the rest.
```

Speed-for-accuracy tradeoffs:

```bash
python3 scripts/build_features.py --no-doi      # skip CrossRef network calls
python3 scripts/build_features.py --no-ocr      # skip OCR on scanned PDFs
python3 scripts/build_features.py --year 2020   # just one year
python3 scripts/build_features.py --force       # re-extract everything
```

## Confidence interpretation

| Band | Meaning | Action |
|---|---|---|
| `>= 0.85` | high-confidence duplicate / SM / corrigendum | trust auto-delete or auto-rename |
| `0.55 - 0.85` | likely duplicate but worth a glance | review queue |
| `< 0.55` | insufficient signal | treat as distinct, or manual |

Decision vocabulary (stable; downstream code pins these strings):

| Decision | Meaning |
|---|---|
| `same_content` | byte-identical — delete either |
| `keep_1` / `keep_2` | duplicate; keep the named side |
| `rename_sm` | smaller side is supplementary material |
| `is_corrigendum` | smaller side is a corrigendum/erratum/reply |
| `is_book` | both sides are books — not a duplicate pair |
| `is_chapter` | one side is a chapter of the other |
| `distinct` | confirmed not a duplicate |
| `manual` | insufficient signal → human decides |
| `needs_index` | feature cache missing for one side — re-run builder |
| `file_missing` | at least one PDF no longer on disk |

## Signals that drive fusion

Positive (add to confidence):
- `doi_match` (+0.50)  DOIs extracted from XMP or first page identical
- `phash_p1_d=<n>` (+0.25 if ≤5, +0.10 if ≤10)  first-page visual match
- `phash_last_d=<n>` (+0.10 if ≤5)
- `minhash_j=<j>` (+0.25 if ≥0.85, +0.10 if ≥0.60)  text overlap
- `tlsh_d=<n>` (+0.10 if <30)
- `title_fuzz=<r>` (+0.15 if ≥95, +0.05 if ≥80)
- `full_text_hash_equal` (+0.30)
- `sha256_equal` (→ 1.0, short-circuit)

Negative (subtract, or force `distinct`):
- `doi_differ(...)` → force `distinct` @ 0.90
- `lang_differ` → force `distinct` @ 0.90
- `title_fuzz` < 40 (-0.30)
- `minhash_j` < 0.20 (-0.20)
- `phash_p1_d` ≥ 30 (-0.10)
- `pc_ratio` ≥ 2 without SM marker (-0.10)

Special cases that override fusion:
- SM markers (XMP Subject / CrossRef type / first-page regex) on one
  side + same-paper evidence → `rename_sm` @ 0.88
- Corrigendum markers + same-paper evidence → `is_corrigendum` @ 0.88
- Both `looks_like_book` → `is_book`
- One book, one ≥3× smaller → `is_chapter`
- Corrupted side → keep the other @ 0.95

## Integration with the ingestion pipeline

From Python:
```python
from scripts.dedup.ingest_hook import check_new_pdf
flags = check_new_pdf(Path("/corpus/2020/new.pdf"))
# each `flag` is a dict with decision, confidence, signals, new_file, candidate
```

From shell (after a PDF lands in the corpus):
```bash
python3 scripts/check_new_pdf.py /path/to/new.pdf
# writes JSONL flags to outputs/on_ingest_flags.jsonl
# exit 0 even if flags found; inspect the log or stdout
```

The hook:
1. Extracts features for the new file (caches them).
2. Finds candidates via SHA-256 equality, DOI equality, pHash Hamming ≤ 10.
3. Runs fusion against each candidate.
4. Appends high-confidence flags (≥0.55) to `outputs/on_ingest_flags.jsonl`.

## Cache

`outputs/pdf_features.sqlite` stores one row per relative path:

- Features reused across runs (incremental by size+mtime).
- Schema versioned via `EXTRACTOR_VERSION` in `schema.py` — bump it
  when an extractor's semantics change and the next run will re-extract.
- Indexed on `bytes_sha256`, `extracted_doi`, `phash_p1`.

Inspect:
```bash
sqlite3 outputs/pdf_features.sqlite 'select rel_path, page_count, extracted_doi, detected_language from pdf_features limit 10'
```

## Tuning

Weights in `fusion.py` are heuristic defaults. To recalibrate on user
notes from `pdf_library_audit.xlsx`:

```bash
python3 scripts/evaluate_duplicates_v8.py --compare
```

prints a v7-vs-v8 accuracy summary against the `notes` column and lists
disagreements. Adjust weights in `fusion.py` accordingly and re-run.
