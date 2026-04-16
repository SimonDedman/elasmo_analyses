# Shark-References Monthly Sync — Design Spec

**Date:** 2026-04-06
**Author:** Simon Dedman
**Status:** Approved

## Purpose

Automatically detect new papers added to Shark-References since our last
sync, fetch their details, download available PDFs, and identify
download opportunities for papers we already know about but lack PDFs
for. Runs monthly via anacron, with notifications via ntfy.sh (instant
push) and Gmail (detailed summary).

## Background

The project's paper database was seeded from a full Shark-References
scrape on 20-21 October 2025 (30,523 papers). Since then, SR will have
added new papers across all years. Our enriched parquet now holds 30,558
papers; 12,905 remain without PDFs (tracked in `docs/papers_data.json`).

## Architecture

### Single script: `scripts/sync_shark_references.py`

```
Phase 1: Crawl (26 HTTP requests, ~5 min)
  GET /literature/listAll/{A..Z}
  Extract: literature_id, authors, year, title, DOI, pdf_url

Phase 2: Diff (~seconds)
  Load enriched parquet (literature_id set)
  Load papers_data.json (still-needed set)
  Categorise each SR entry:
    NEW        — not in parquet
    NEEDS_PDF  — in parquet, in papers_data.json, SR has pdf_url
    HAVE       — in parquet, not in papers_data.json (or no SR pdf_url)

Phase 3: Enrich new papers (~2s each)
  For each NEW paper:
    GET /literature/detailAjax/{id}
    Parse: abstract, keywords, taxa, download links

Phase 4: Download PDFs
  For each NEW or NEEDS_PDF paper with a pdf_url:
    Download PDF
    Validate: file size > 50KB, starts with %PDF magic bytes
    Save to SharkPapers/{FirstAuthor}/{year}/{filename}.pdf
    On validation failure: log, delete file, skip

Phase 5: Update state
  Append NEW papers to master CSV
  Remove successfully-downloaded papers from papers_data.json
  Generate SR feedback report (papers where we have PDF but SR doesn't)

Phase 6: Notify
  ntfy.sh push: one-line summary (new count, downloaded count, errors)
  Gmail SMTP: full summary with lists of new papers and any errors
  Log file: detailed run log
```

### PDF validation

Downloads are validated before keeping:

| Check | Threshold | Rationale |
|-------|-----------|-----------|
| File size | > 50 KB | Rejects placeholder pages, error pages |
| Magic bytes | Starts with `%PDF` | Rejects HTML error pages served as .pdf |
| HTTP status | 200 | Rejects redirects to login walls |

Failed downloads are logged with the reason but do not abort the run.

### Failure resistance

- **Lock file** (`/tmp/sr_sync.lock`): prevents concurrent runs; stale
  locks (>24h) are automatically cleared.
- **Per-letter resilience**: if letter M fails, the script logs the
  error and continues with N. Missed letters are retried on next
  monthly run (full re-scan each time).
- **Network retries**: 3 attempts per request with exponential backoff
  (4s, 8s, 16s).
- **Top-level exception handler**: any uncaught error still triggers
  failure notifications before exit.
- **Idempotent**: re-running the script is safe. Already-known papers
  are skipped; already-downloaded PDFs are not re-downloaded.

### Scheduling: anacron

anacron tracks "days since last run" and fires when the machine is next
available, even if it was off at the scheduled time.

```
# /etc/anacrontab entry
30  15  sr-monthly-sync  /usr/bin/python3 /media/simon/data/Documents/Si\ Work/PostDoc\ Work/EEA/2025/Data\ Panel/scripts/sync_shark_references.py
```

- **Period**: 30 days
- **Delay**: 15 minutes after boot (avoids competing with startup I/O)
- **Job ID**: `sr-monthly-sync`

### Notifications

**ntfy.sh** — instant push notification to phone/desktop:
- Channel: user-chosen private name (configured in script)
- On success: "SR sync: 12 new papers, 3 PDFs downloaded"
- On failure: "SR sync FAILED: {error}"

**Gmail SMTP** — detailed email summary:
- Requires Google App Password (one-time setup)
- Subject: "Shark-References Sync — {date} — {new_count} new"
- Body: list of new papers, downloaded PDFs, failed downloads, errors,
  feedback report summary

### SR feedback report

Each run generates/updates `outputs/sr_suggested_pdf_links.csv`:
- Papers where we have a PDF on disk but SR shows no download link
- Columns: literature_id, authors, year, title, DOI, our_pdf_path
- For manual review and periodic email to SR maintainers

## Files read

| File | Purpose |
|------|---------|
| `outputs/literature_review_enriched.parquet` | Known paper universe (literature_id, DOI) |
| `docs/papers_data.json` | Papers still needing PDFs |
| `outputs/shark_references_bulk/shark_references_complete_*.csv` | Master SR data (appended to) |

## Files written

| File | Purpose |
|------|---------|
| `outputs/shark_references_bulk/shark_references_complete_*.csv` | Appended with new papers |
| `docs/papers_data.json` | Entries removed when PDF acquired |
| `outputs/sr_suggested_pdf_links.csv` | Feedback report for SR |
| `logs/sr_sync_YYYYMMDD.log` | Detailed run log |
| PDFs in SharkPapers directory | Downloaded papers |

## CLI interface

```
python3 scripts/sync_shark_references.py [OPTIONS]

Options:
  --dry-run       Crawl and diff only; no downloads, no state changes
  --no-notify     Skip notifications (for testing)
  --ntfy-topic X  Override ntfy.sh topic name
  --verbose       Debug-level logging
```

## Configuration

Sensitive values stored in `scripts/.sr_sync_config.json` (gitignored):

```json
{
  "ntfy_topic": "your-private-topic",
  "gmail_address": "you@gmail.com",
  "gmail_app_password": "xxxx xxxx xxxx xxxx",
  "notify_to": "you@gmail.com"
}
```

## Out of scope

- Automatic email submission to SR (manual review step required)
- Modifying the enriched parquet (that's the extraction pipeline's job)
- Re-running schema extraction on new papers (separate script)
- Downloading PDFs from non-SR sources (Unpaywall, publisher sites)
