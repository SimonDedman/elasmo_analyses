# Cascade finalize pass: ingest → verify-delete → extract

**Date:** 2026-07-07
**Status:** Approved (design), implementing
**Author:** Simon Dedman (with Claude Code)

## Problem

`acquire_cascade.py` is the unified per-paper acquisition cascade (OA discovery,
DOI recovery, BHL/archive.org, Unpaywall). It **downloads** PDFs to staging dirs
(`outputs/oa_downloads/`, `outputs/bhl_downloads/`, named `<literature_id>.pdf`)
but stops there: its own docstring says it "does NOT file them into the corpus
itself." Ingestion into SharkPapers and schema extraction are separate steps.

Consequences:
- Staged PDFs are never filed into the library automatically.
- `ingest_pdfs.py` **copies** (never moves), so staging disk is never reclaimed
  even after a manual ingest — it grew to ~9.3 GB (8.8 GB BHL + 0.47 GB OA).
- The enriched parquet isn't updated for newly-acquired papers until a separate
  extraction run.

`sync_shark_references.py` already chains all of this (Phase 5b: post-download
ingest + incremental schema extraction). The cascade is the only acquisition
path that doesn't. This spec closes that gap.

## Workflow-composition review

| Stage | Script / function | In cascade? | In sync? |
|---|---|---|---|
| Acquire (download) | `acquire_cascade.py` | ✅ is the cascade | partial |
| Ingest (file → SharkPapers, update papers_data.json + DBs) | `ingest_pdfs.ingest_source()` | ❌ **gap** | ✅ |
| Extract (schema cols → parquet) | `extract_incremental.py` | ❌ **gap** | ✅ Phase 5b |
| Orphan staging (non-SR PDFs) | `stage_orphan_pdfs.py` | n/a (SR-only) | ✅ Phase 0 |

The cascade's only missing links are **ingest** and **extract**. Orphan staging
is SR-specific and stays out.

## Design

Add one function, `finalize_acquisitions()`, to `acquire_cascade.py`, reusing the
tested `ingest_pdfs` and `extract_incremental` code rather than reimplementing.

```
finalize_acquisitions(keep_staging=False, do_extract=True, dry_run=False):
    all_rows, doi_lookup, ay_lookup = ingest_pdfs.load_database()
    staged = sorted(BHL_DOWNLOAD_DIR/*.pdf) + sorted(OA_DOWNLOAD_DIR/*.pdf)

    if dry_run:
        ingest_pdfs.check_source("cascade-finalize", staged, ...)   # report only
        return

    copied_ids, copied_dois, pdf_names, log = ingest_pdfs.ingest_source(
        "cascade-finalize", staged, doi_lookup, ay_lookup, all_rows)
    ingest_pdfs.update_papers_data_json(copied_ids, copied_dois, ts, "cascade-finalize")
    ingest_pdfs.update_tracking_dbs(copied_ids, pdf_names, ts, "cascade-finalize")

    if not keep_staging:
        delete_verified_staging(staged, copied_ids, pdf_names)   # see safety model

    if do_extract and copied_ids:
        subprocess: extract_incremental.py --ids <copied_ids>
```

### Interfaces reused (verified against source)

- `ingest_pdfs.load_database() -> (all_rows, doi_lookup, author_year_lookup)`
- `ingest_pdfs.ingest_source(label, paths, doi_lookup, ay_lookup, all_rows)
   -> (copied_ids: set, copied_dois: set, pdf_names: dict, log_lines: list)`
  - `copied_ids` = literature_ids matched **and** present in library (newly
    copied OR already-existed).
  - `pdf_names[lit_id]` = relative dest path `"{year}/{Surname.Year.Title.pdf}"`
    under `PDF_BASE` (SharkPapers).
- `ingest_pdfs.check_source(...)` — dry-run match report, copies nothing.
- `ingest_pdfs.update_papers_data_json`, `update_tracking_dbs` — same calls
  `ingest_pdfs.main()` makes after `ingest_source`.
- `extract_incremental.py --ids <csv>` — patches enriched parquet + appends
  evidence for the given ids (mirrors sync Phase 5b).

### Wiring & flags

- Full run: download loop (unchanged) → `finalize_acquisitions()` at end of `main()`.
- `--finalize-only`: skip the download loop; run only the post-pass. Used tonight
  (the currently-running PID has the old code and won't self-finalize) and as a
  permanent standalone.
- `--keep-staging`: ingest + extract but never delete.
- `--no-extract`: skip extraction (mirrors sync's flag).
- `--dry-run` + `--finalize-only`: match report only, touches nothing.

## Deletion safety model

A staged file `<lid>.pdf` is deleted **only if all gates pass**:

1. **Confirmed ingested** — `lid ∈ copied_ids` (ingest's content-based match, not
   the filename, confirmed the paper is filed).
2. **Dest exists** — `PDF_BASE / pdf_names[lid]` is present on disk.
3. **Valid file** — dest `getsize > 1024` (real PDF, not a stub).
   (NB: **not** byte-identity vs the staged file — `ingest_source` files the
   OCR'd copy for image-only scans, so byte-size legitimately differs. Size is
   recorded in the manifest as an audit signal only.)

id comparison normalises both sides (strip trailing `.0`) — the documented
literature_id float gotcha.

**Keep-categories (never deleted):** matched-but-dest-missing (WARN — real bug
signal); no-DOI/no-author-year match (orphan candidate); dedup-flagged possible
duplicate; corrupt/OCR-failed. Every failure mode resolves toward *keep*.

**Structural guards:**
1. **Containment assert** — delete refuses any path not inside the two staging
   dirs. Cannot touch SharkPapers, the queue, or anything else.
2. **Delete-after-confirm ordering** — runs only after `ingest_source` returns.
3. **Pre-delete manifest** — `outputs/cascade_finalize_manifest_<ts>.csv` lists
   every file to be deleted with dest path + both sizes, written before any
   `unlink`. Audit trail and re-download list.
4. **Two opt-outs** — `--keep-staging`, `--dry-run`.
5. **Recoverable by construction** — staged files are re-downloadable public
   PDFs; even a defeated gate isn't data loss (backstop, not primary reliance).

## Tonight's runbook (build + one-off run)

1. Let current cascade (PID 4174508) finish (~116 papers left).
2. `python3 scripts/acquire_cascade.py --finalize-only --dry-run` → match report.
3. Eyeball counts (matched vs unmatched of ~644 staged files).
4. `python3 scripts/acquire_cascade.py --finalize-only` → ingest, verify, delete
   verified, extract.
5. Confirm manifest + `du -sh outputs/{bhl,oa}_downloads` shows disk reclaimed.

## Testing

- Unit: `delete_verified_staging` gate logic (mock copied_ids / dest existence /
  containment) — asserts wrong-id, missing-dest, out-of-dir paths are all kept.
- Integration: `--finalize-only --dry-run` on real staging (no writes) before the
  live run; verify manifest matches what was deleted after.

## Out of scope

- Changing `ingest_pdfs` copy→move (shared by sync + orphan staging).
- Periodic mid-run finalize (end-of-run batch only; can add later).
- Orphan staging of unmatched files (leave in staging for manual handling).
