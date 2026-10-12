# Drop-folder ingest: standard practice

Agreed 2026-10-12 (Simon's proposal, extended with the subfolders that previous deliveries
needed). Applies to every coauthor delivery: `database/others_libraries/<Person>/` and the NAS
drop folders (`smb://nas.local/homes/MarineScience/<Person>/`).

## The two scripts

```
python3 scripts/audit_drop_folder.py --folder DIR --person NAME          # read-only
python3 scripts/apply_drop_audit.py  --audit A --folder DIR --person NAME \
        [--overrides O] --stage | --file | --verify | --credit | --sort
```

`audit_drop_folder.py` opens every PDF (OCR when there is no text layer), matches it to a
record (filename DOI, then surname + year, then filename title words), and runs the identity
test: at least 80% of the record's title words in the first pages (50% if the record's DOI is
printed there; titles of three words or fewer must appear as a phrase), and the first author's
surname as a capitalised word anywhere in the document. Each file gets one bucket. Output:
`outputs/dropaudit_<Person>_<date>/audit.csv` + `coverage.json`.

Human review then covers every non-`ingest` row and every row matched without a DOI; decisions
go in `overrides.csv` (`filename,bucket,literature_id,source_override,queue_status,note`).
`source_override` points at an OCR'd or split copy prepared during review.

## Outcome 1: ingested successfully

1. Staged as `outputs/ingest_<date>_<Person>/{papers,books}/<lid>.pdf` plus
   `<lid>.identity.json` (lid-named staging is filed by id, never re-matched).
2. Filed by `acquire_cascade.py --finalize-only` (renamed `Surname.etal.Year.Title.pdf`,
   moved into `SharkPapers/<year>/`), queue row closed in `docs/papers_data.json`,
   tracking DBs updated.
3. `scripts/refresh_pdf_map_and_extract.sh`: `pdf_id_map.csv` rebuilt, corpus row backfilled,
   evidence extracted.
4. `--verify`: the record left the queue, the library copy exists, has the source's page count,
   and passes the identity test. Zero unexpected queue removals.
5. `--credit`: scan-state entry with `literature_id` (leaderboard credit), source deleted from
   the drop folder, staging copy deleted.
6. Dashboard rebuilt (`scripts/build_remaining_papers_dashboard.py`).

## Outcome 2: a problem, sorted into a named subfolder

`--sort` moves each file into a subfolder of the drop folder with a `README.txt`, and writes a
`held` scan-state entry so the daily cron never files it.

| Subfolder | Meaning | What happens next |
|---|---|---|
| `_duplicate-already-filed` | Byte-identical, or a copy of a paper whose verified library PDF has the same pages | Delete (no credit) |
| `_already-filed-different-copy` | Record already has a PDF and this copy differs in kind (published vs manuscript, more pages) | Keep the better one in the library |
| `_review-comment` | A review, comment, reply or discussion of the target paper | Target still needed; review DOI to `sr_doi_quarantine.csv` if SR caused it |
| `_correction-erratum` | Correction, erratum or retraction notice only | Target still needed |
| `_supplement-only` | Supplementary material only | Target still needed; file beside the paper as `<stem>_SM.pdf` once the paper is in |
| `_abstract-only` | An abstract or abstracting-journal entry | Target still needed |
| `_partial-pages-missing` | Pages of the paper missing | Complete copy still needed |
| `_wrong-paper` | A different paper from the one named | Target still needed; if the PDF is itself a shark paper, add it as a new record |
| `_whole-volume-needs-split` | A whole issue, volume or book containing the record | Split with `scripts/split_volume_by_pages.py`, then file |
| `_not-in-database` | No record matches | Add as a new record if in scope, else delete |
| `_unreadable-scan` | No text even after OCR | Read by eye or re-OCR with the right language |
| `_not-elasmo` | Not about elasmobranchs | Delete |

Every target-still-needed row also gets a `prior_false_dl` flag (`scripts/flag_prior_false_downloads.py`
FLAGS), so the next downloader sees the warning on the hub.

## Rules carried over from earlier deliveries

- Open the PDF. A file that exists is not a file that is right (2026-09-17: 5% misfiled).
- OCR any scan whose only text is a download watermark (GeoScienceWorld, BioOne cover pages):
  the page-one alpha count passes, but nothing is readable.
- A BioOne or JSTOR "section" PDF may hold several notes: split to the record's page range.
- Ligatures (`ﬁ`), accents and OCR slips break surname tests; the review step catches these.
- Count queue ROWS, not unique ids (`papers_data.json` has duplicate-id rows).
