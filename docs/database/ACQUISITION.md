# Acquisition: free-source channels

`scripts/fetch_free_sources.py` turns the recipes proved by hand on
2026-09-17 (see `outputs/download_push_2026-09-17/CHROME_strandvlo`,
`CHROME_ices`, `CHROME_frdc`, `A3_journals`, `SPRINGER_api`) into reusable,
resumable channels. Each channel finds a candidate PDF (or, for Springer,
JATS full text), verifies it, and stages it as
`outputs/oa_downloads/<literature_id>.pdf` (or, for Springer text,
`outputs/oa_downloads_text/<literature_id>.xml`). None of them write
`docs/papers_data.json`, ingest anything, or delete anything — they only
prepare a staging directory for a later
`scripts/acquire_cascade.py --finalize-only` run.

## Channels

| Channel  | Source | Scope (default) | Match | Verify |
|----------|--------|------------------|-------|--------|
| `vliz`   | VLIZ / MarineInfo Open Marine Archive (`api.marineinfo.org`, `marineinfo.org`) | journal/findspot contains "De Strandvlo" or "Het Zeepaard" | title token overlap >= 0.5 on the longer title, venue string in `refstrfull` | `%PDF` + >20 KB + title tokens in first 4 pages, or `scan` if no text layer |
| `ices`   | ICES library on Figshare (`api.figshare.com`, `ices-library.figshare.com`) | journal/findspot contains "ICES" | overlap >= 0.5 on longer title (title, then "surname year") | as above, over first 2 pages, **plus** first author's surname required |
| `frdc`   | FRDC (Australia) reports (`frdc.com.au`) | findspot/journal/notes contains "FRDC" and a `YYYY/NNN`-shaped project number | project-number URL pattern, project-page fallback | as VLIZ, over first 4 pages |
| `jstage` | J-STAGE, scoped to Japanese Journal of Ichthyology (`api.jstage.jst.go.jp`) | journal/journal_clean is "Japanese Journal of Ichthyology" (or alias) | overlap >= 0.75 (the proven A3 threshold) | as VLIZ, over first 4 pages |
| `springer` | Springer Nature Meta + Open Access (JATS) APIs, by DOI | outstanding rows whose `doi` starts with `10.1007` | none needed — keyed by DOI | JATS body: title overlap >= 0.5 + surname present |

Common helpers (all channels): title tokenisation on `[a-zà-ÿ]{4,}` tokens
with a small stop-word list; overlap = intersection / size of the **longer**
title's token set; a Chrome-like User-Agent with a `mailto:` contact
(**except** the `ices` channel — see the Figshare note below); a polite
delay between requests (2 s for `vliz` per the proven recipe, 1.5 s
elsewhere, overridable with `--sleep`); only 200 responses are cached,
under `outputs/free_sources/.cache/<channel>/`; a 403/429/503 is always
recorded as `blocked`, never as `not_found`.

### Figshare User-Agent gotcha (found 2026-09-18)

Figshare's `ndownloader.figshare.com` proxy returns **HTTP 202 with an
empty body, indefinitely**, to any request whose User-Agent looks like a
real browser (confirmed live: 5 retries over ~15 s, still 202) — it only
streams the file (200, real bytes) for a non-browser UA. The `ices`
channel therefore uses a distinct, honest, non-browser UA
(`API_USER_AGENT` in the script) instead of the shared Chrome-like one.
If a future channel also targets `ndownloader.figshare.com`, reuse
`API_USER_AGENT`, not `USER_AGENT`.

### FRDC is blocked, not absent

`frdc.com.au` returns a **403 to every programmatic request** (curl,
`requests`, with or without a Chrome UA) on both the direct
`.../products/<YYYY>-<NNN>-DLD.pdf` pattern and the `/project/<YYYY>-<NNN>`
fallback page — confirmed live 2026-09-18. The 2026-09-17 hand-run
successes came from a real browser (Chrome extension) rendering the page,
which this script cannot do. The channel still runs the full parse +
URL-construction + fallback logic (useful once/if the block lifts, or via
a browser-driven follow-up), and correctly reports `blocked`, never
`not_found`, so a resumed run does not mistake a block for an absence.

### Springer TDM

The Full Text (TDM) endpoint is not live yet (applied for, not approved).
`springer --tdm` checks `SPRINGER_TDM_KEY` in `.env`; if absent it prints
"no TDM key yet" and exits 0. `SPRINGER_TDM_URL` in the script is a
speculative, **untested** guess at the endpoint shape — update it from
Springer's approval email before relying on it.

## Running a channel

```bash
# report rows in scope, no network calls
python3 scripts/fetch_free_sources.py vliz --dry-run
python3 scripts/fetch_free_sources.py all --dry-run

# a real, small batch
python3 scripts/fetch_free_sources.py vliz --limit 10
python3 scripts/fetch_free_sources.py ices --limit 10
python3 scripts/fetch_free_sources.py jstage --limit 10
python3 scripts/fetch_free_sources.py frdc --limit 10
python3 scripts/fetch_free_sources.py springer --limit 10

# every channel in sequence
python3 scripts/fetch_free_sources.py all --limit 10

# generic venue override (works on any channel; matches journal/journal_clean/findspot_raw)
python3 scripts/fetch_free_sources.py vliz --venue "Some Other Belgian Journal"

# re-fetch one specific paper into a scratch dir, e.g. to spot-check a channel
python3 scripts/fetch_free_sources.py jstage --ids 1184 --staging-dir /tmp/scratch
```

`--limit` counts only rows actually attempted over the network; a row
whose `outputs/oa_downloads/<lid>.pdf` already exists is skipped for free
and does not count against the limit. `--ids` (comma-separated
`literature_id`s) overrides the outstanding-pool filter entirely and
matches on **any** `last_status`, which is what makes the scratch-dir
spot-check above possible even after a paper has already been finalized.

Each run writes/updates:
- `outputs/free_sources/<channel>_manifest.csv` — append-safe (read,
  merge by `literature_id`, rewrite), columns `literature_id, venue, url,
  path, sha256, bytes, verified, doi_seen, status, note`.
- `outputs/free_sources/<channel>_coverage.json` — `rows_in_scope,
  attempted, downloaded_verified, downloaded_scan, rejected_mismatch,
  not_found, blocked, errors_by_class, already_staged, not_attempted,
  http_counts`.

## Before a finalize

Run one or more channels, review `outputs/free_sources/*_coverage.json`
and the staged files under `outputs/oa_downloads/`, then:

```bash
python3 scripts/acquire_cascade.py --finalize-only --staging-dir outputs/oa_downloads
```

This files staged `<literature_id>.pdf` files into the corpus by trusting
the filename (subject to `acquire_cascade.py`'s own identity-check sanity
gate) — see its module docstring for the full finalize contract.

## Tests

`scripts/test_fetch_free_sources.py` — plain-assert tests for the title
matching helpers, `first_surname`, the FRDC project-number parser, scope
filtering, and the manifest schema. No network calls.

```bash
python3 -m pytest -q scripts/test_fetch_free_sources.py
```
