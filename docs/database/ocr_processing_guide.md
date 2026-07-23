# PDF Text Extraction & OCR Pipeline

**Last updated:** 2026-07-21

This guide covers how PDFs in the SharkPapers library are made
text-searchable so the schema-extraction pipeline can read them. Every
downstream step (the 123-column extraction in
`scripts/extract_schema_columns.py`) reads text via `pdftotext` only —
there's no title/abstract fallback — so a scan with no text layer is
invisible to the analysis. OCR is what brings image-only and historical
scans into the analysable corpus.

> The legacy `ocr_missing_pdfs.py` workflow (backup-and-replace, single
> English model) is superseded and archived at
> `docs/archive/ocr_processing_guide_LEGACY_ocr_missing_pdfs_2025-10-24.md`.
> Use the pipeline below.

---

## Tools

| Tool | Role |
|------|------|
| `pdftotext` (Poppler) | Extract text; also the *test* for whether a PDF is already searchable. |
| `ocrmypdf` | Add a searchable text layer to image-only PDFs. Only *adds* a layer — page images are preserved. |
| Tesseract | The OCR engine `ocrmypdf` drives, with per-language models. |
| Ghostscript | PDF rasterising/repair (used by `ocrmypdf` and by `ocr_gs_repair.py`). |

**Installed Tesseract language packs** (as of 2026-07-21):
`eng deu fra spa por ita nld rus jpn chi_sim chi_tra kor Fraktur`
(+ `osd` orientation/script detection). `Fraktur` is the blackletter
model (`tesseract-ocr-script-frak`) for old German type. To add more:
`sudo apt install tesseract-ocr-<code>` then confirm with
`tesseract --list-langs`.

---

## The pipeline: screen → OCR → verify

### 1. Screen — `scripts/find_non_extractable_pdfs.py`

Scans every PDF in the library, runs `pdftotext -l 1` on page 1, and
flags any with fewer than **50 alphabetic characters** (`MIN_ALPHA`) as
non-extractable. It also runs lightweight language detection (stopword +
accent/script matching) so OCR can pick the right model.

- **Output:** `outputs/non_extractable_pdfs.xlsx` — columns
  `year, filename, title_language, open_file`.
- Page-1 test is a fast *screen* for candidates, not a verdict — see
  Verify below.

```bash
./venv/bin/python scripts/find_non_extractable_pdfs.py
```

### 2. OCR — `scripts/ocr_library.py`

Reads the report and runs `ocrmypdf` on each flagged file. Language is
chosen per file from the `title_language` column via `LANG_MAP`,
falling back to `eng` when the required pack isn't installed. Output
goes to a tempfile and is **atomically renamed** over the original, so a
crash never leaves a half-written PDF.

- Default mode: `--skip-text` (OCR only image-only pages), falling back
  to `--force-ocr` if that bails on mixed content.
- The page-1 re-check skips any file that already gained text from a
  partial previous run.
- **Logging is incremental** (per file, flushed), so a kill mid-run
  leaves an accurate record of what completed — essential for long runs.

Options:

| Flag | Effect |
|------|--------|
| `--dry-run` | List targets, OCR nothing. |
| `--limit N` | Process only the first N (testing). |
| `--languages A,B` | Only files whose `title_language` is in the list. |
| `--redo` | Re-OCR pages that already have text (`--redo-ocr`), to correct wrong-language OCR. Bypasses the has-text skip. |
| `--report PATH` | Use a different report XLSX — for resuming a partial run from a filtered list. |
| `--timeout N` | Per-file `ocrmypdf` timeout in seconds (default 600). Raise for multi-hundred-page volumes. |
| `--tmpdir PATH` | Where ocrmypdf renders pages. See the disk-space and AppArmor notes below — the path is constrained. |

### Temp space and the AppArmor constraint (read before setting `--tmpdir`)

`ocrmypdf` rasterises **every page to PNG at 400 DPI** before OCR, so one
400–1000 page volume can need several GB of scratch at once. Two traps:

1. **A full temp dir fails everything, silently.** If the temp filesystem
   fills, Ghostscript fails at *startup* and every subsequent file fails
   fast with an empty/garbled error and idle CPU. The usual cause is
   orphaned `ocrmypdf.io.*` dirs left by `kill -9`'d runs — ocrmypdf
   cleans up on normal completion but not when killed. `ocr_library.py`
   now clears these at startup when `--tmpdir` is set; otherwise clean
   manually: `rm -rf /tmp/ocrmypdf.io.*`.

2. **Ghostscript is AppArmor-confined.** `/etc/apparmor.d/gs` restricts
   `gs` to `/tmp`, `/var/tmp`, and `$HOME` (via `abstractions/user-tmp`).
   Pointing `--tmpdir` at anything else — notably `/media/**` — makes
   *every* file fail with:

   ```
   Last OS error: Permission denied
   Could not open the scratch file /media/.../gs_XXXXXX
   SubprocessOutputError: Ghostscript rasterizing failed
   ```

   Note this is invisible in the log, because `ocr_one` truncates stderr
   to 200 chars and the Ghostscript banner fills it. To diagnose, run
   `ocrmypdf` directly on one file and read the full stderr.

**Use `/var/tmp/ocr_scratch`** (permitted, disk-backed rather than the
RAM-backed `/tmp`). To use a larger disk, add an AppArmor exception
first:

```bash
sudo tee /etc/apparmor.d/local/gs >/dev/null <<'EOF'
owner /media/simon/data/ocr_scratch/** rwk,
/media/simon/data/ocr_scratch/ r,
EOF
sudo apparmor_parser -r /etc/apparmor.d/gs
```

**Per-report logs:** with `--report`, the log is named
`logs/ocr_library_log_<report_stem>.txt`, so concurrent or sequential
runs on different reports don't clobber each other. The default run uses
`logs/ocr_library_log.txt`.

```bash
./venv/bin/python scripts/ocr_library.py --dry-run          # list targets
./venv/bin/python scripts/ocr_library.py --limit 10         # test on 10
./venv/bin/python scripts/ocr_library.py                    # full run
```

**Fraktur routing (old German).** Many pre-~1940 German scientific texts
are set in Fraktur (blackletter), which the roman-type `deu` model reads
poorly. When a file is German and its year (from the path's year folder)
predates 1940, `ocr_one` OCRs it with combined **`deu+Fraktur`** (`deu`
kept first). It's combined rather than Fraktur-only because the era is
mixed — by ~1900 many journals had switched to roman (Antiqua) type — and
A/B tests showed `deu+Fraktur` never does worse than `deu` on roman
pages while adding the blackletter option. Note Fraktur can't rescue
degraded/low-quality scans; it only helps genuine blackletter.

### 3. Verify — whole-document `pdftotext`

Judge OCR success with a **whole-document** `pdftotext` call, *not* the
page-1 screen. Historical taxonomy scans (Linné 1758, Gmelin 1789, etc.)
routinely have an image-only title page followed by hundreds of good
OCR'd pages: a page-1 test returns ~0 chars and falsely reads as
failure. Threshold whole-doc alpha at **≥200** for a real verdict.

```bash
# whole-doc, not -l 1
pdftotext "path/to/file.pdf" - | tr -cd '[:alpha:]' | wc -c
```

---

## Language handling

Two independent knobs, because the batch and inline paths differ:

- **Batch (`ocr_library.py`)** does per-file language selection from the
  detector's `title_language`, mapped through `LANG_MAP`. Multi-model
  codes are supported (e.g. CJK maps to `jpn+chi_sim+chi_tra` because
  the detector can't disambiguate Japanese from Chinese); `ocr_one`
  filters each `+`-joined code against installed packs.
- **Inline ingest (`ingest_pdfs.py`)** has *no* per-file detection — it
  applies one fixed string, `OCR_LANGS = "eng+fra+deu+spa+por+ita"`, to
  every OCR call. CJK/Cyrillic are deliberately left out here to avoid
  slowing every ingest and risking misreads on English scans; those are
  handled by the batch path.

### Resolving language from the filename — `resolve_pdf_language.py`

The screen's `title_language` is detected from page-1 OCR text, which for
scanned/historical volumes is blank or garbage — so languages are
frequently wrong (a German volume mislabelled French will then be OCR'd
with the wrong model). `scripts/resolve_pdf_language.py` re-derives a
better `title_language` from cleaner signals, in priority order:

1. the **filename title fragment** (always present, human-typed —
   `"…Systematischen Verzeichniss der Versteinerungen…"` reads as German),
2. the **corpus title + journal name**, when the file matches a
   `viz_data.csv` entry by first-author surname + year ±1 + title-word
   overlap.

Both beat page-1 OCR text. It also records the filename year (used for
Fraktur routing). Note the corpus has **no** language field and most old
no-DOI volumes aren't in it (~14% match), so the filename fragment is the
primary signal. In practice it corrects ~5–25% of labels (all observed
errors were German wrongly tagged French).

```bash
# produce a language-corrected report, then OCR from it
./venv/bin/python scripts/resolve_pdf_language.py \
    --report outputs/non_extractable_pdfs.xlsx \
    --out    outputs/non_extractable_resolved.xlsx
./venv/bin/python scripts/ocr_library.py --report outputs/non_extractable_resolved.xlsx
```

The resolved report carries extra columns (`resolved_year`,
`lang_source`); `ocr_library.py` reads only the first three, so it
consumes either the standard or the resolved report.

### Correcting wrong-language OCR (`--redo`)

Files OCR'd before the correct pack was installed (or under a wrong
language label) carry a bad text layer. `--skip-text` won't overwrite
it, so re-run with `--redo` (uses `ocrmypdf --redo-ocr`, replacing the
existing OCR layer, with a `--force-ocr` fallback). Combine with a
resolved report so the corrected languages are used:

```bash
./venv/bin/python scripts/ocr_library.py \
    --report outputs/non_extractable_resolved.xlsx --redo --timeout 3600
```

`--redo` bypasses the "already has text" skip check, since the whole
point is to reprocess files that already have (wrong) text.

---

## Inline OCR during ingestion — `scripts/ingest_pdfs.py`

New PDFs entering the corpus are OCR'd on the fly rather than waiting for
a batch pass. During ingest, `ensure_text_extractable()`:

1. Checks page-1 alpha against `OCR_MIN_ALPHA` (50); returns the
   original path if it already has text.
2. Otherwise runs `ocrmypdf` (`--skip-text`, then `--force-ocr`) into a
   cache at `outputs/.ocr_cache/`, keyed by the source **SHA1** so
   re-runs reuse prior work.
3. The OCR'd copy is preferred for the library so downstream extraction
   has text. OCR failure is **non-fatal** (the original is kept).

Disable with `--no-ocr`. Language is `OCR_LANGS` (see above).

---

## Retry / repair scripts

For residuals the main pass can't handle:

| Script | Purpose |
|--------|---------|
| `ocr_gs_repair.py` | Ghostscript pre-repair of malformed PDFs before OCR. |
| `ocr_footer_retry.py` | Retry with footer/margin handling. |
| `ocr_retry_residuals.py` | Re-attempt files that failed the main pass. |
| `ocr_missing_pdfs.py` | Legacy standalone OCR (superseded; kept for reference). |
| `analyze_pdf_ocr_status.py` | Report OCR status across the library. |
| `apply_ocr_residual_decisions.py` | Apply manual triage decisions to residuals. |

---

## Quick reference

```bash
# 1. Find non-extractable PDFs
./venv/bin/python scripts/find_non_extractable_pdfs.py

# 2. (optional) correct languages from filename + corpus before OCR
./venv/bin/python scripts/resolve_pdf_language.py \
    --report outputs/non_extractable_pdfs.xlsx \
    --out    outputs/non_extractable_resolved.xlsx

# 3. OCR them (per-file language incl. deu+Fraktur for old German, in place)
./venv/bin/python scripts/ocr_library.py --report outputs/non_extractable_resolved.xlsx

# 4. Re-OCR files done under the wrong language/model
./venv/bin/python scripts/ocr_library.py --report outputs/non_extractable_resolved.xlsx --redo --timeout 3600

# 5. Verify a file (whole-doc, not page 1)
pdftotext "file.pdf" - | tr -cd '[:alpha:]' | wc -c   # want >= 200
```

**Key thresholds:** page-1 screen `< 50` alpha → OCR candidate;
whole-doc `>= 200` alpha → OCR verified.
**Related:** `docs/database/ocr_resource_requirements.md` (CPU/time
estimates), `docs/archive/pdf_ocr_status_report.md` (historical status).
