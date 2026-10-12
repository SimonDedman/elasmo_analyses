# Drop-folder ingest: standard practice

Agreed 2026-10-12 (revised the same day after Simon's review: subfolders hold only what a person
must act on, every problem file gets a traced cause, splits and language re-OCR are automatic).
Simon's proposal, extended with the subfolders that previous deliveries needed. Applies to every coauthor delivery: `database/others_libraries/<Person>/` and the NAS
drop folders (`smb://nas.local/homes/MarineScience/<Person>/`).

## The two scripts

```
python3 scripts/audit_drop_folder.py --folder DIR --person NAME          # read-only
python3 scripts/apply_drop_audit.py  --audit A --folder DIR --person NAME \
        [--overrides O] [--ledger-notes N] --stage | --file | --verify | --credit | --sort | --ledger | --tidy
```

`audit_drop_folder.py` opens every PDF (OCR when there is no text layer), matches it to a
record (filename DOI, including DOIs that shark-references stores only in `pdf_url`, then surname + year, then filename title words), and runs the identity
test (scans are OCR'd in six Latin-script languages first, then retried in Fraktur, Russian,
Japanese, Chinese, Korean and Dutch, keeping the pass with the most clean words): at least 80% of the record's title words in the first pages (50% if the record's DOI is
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

**A subfolder exists only while it holds something a person must act on.** Anything the
pipeline can finish itself (a split, a language re-OCR, a new record, a duplicate deletion) is
finished in the same run, and `--tidy` then removes every subfolder left empty. Once a delivery
is fully handled, the drop folder is empty.

| Subfolder | Meaning | Handled by | What remains for a person |
|---|---|---|---|
| `_duplicate-already-filed` | Byte-identical, or a copy of a paper whose verified library PDF has the same pages | pipeline: deleted after identity check (no credit) | nothing |
| `_already-filed-different-copy` | The record already has a PDF and this copy differs in kind (published vs manuscript, more pages) | pipeline: keep the better copy, old one to Trash | only if neither copy is clearly better |
| `_review-comment` | A review, comment, reply or discussion of the target paper | pipeline: hub flag; DOI quarantined if the list's DOI caused it | delete the file once the ledger row is written |
| `_correction-erratum` | Correction, erratum or retraction notice only | same as review-comment | same |
| `_supplement-only` | Supplementary material only | same; filed beside the paper as `<stem>_SM.pdf` once the paper is in | same |
| `_abstract-only` | An abstract or abstracting-journal entry | same | same |
| `_partial-pages-missing` | Pages of the paper missing | pipeline: hub flag | delete once a complete copy is filed |
| `_wrong-paper` | A different paper from the one named | pipeline: hub flag; DOI quarantined if the list's DOI caused it | add as a new record if it is itself an elasmobranch paper, else delete |
| `_whole-volume-needs-split` | A whole issue, volume or book containing the record | pipeline: page range found from the running page numbers, split, identity-checked, filed (or filed whole when the record IS the work) | only a volume that turns out to be the wrong one moves to `_wrong-paper` |
| `_not-in-database` | No record matches | pipeline: re-checked against every DOI source; a genuinely new paper is added (`stage_orphan_pdfs.py`, 600000+ ids) and filed | out-of-scope files: delete |
| `_unreadable-scan` | No text after OCR in EVERY installed language | none | read by eye |
| `_ambiguous-several-records` | Two or more records pass the identity test (shared DOI or same title) | none | pick the record |
| `_not-elasmo` | Not about elasmobranchs | pipeline: ledger row (why was it fetched?) | delete |

Every target-still-needed row also gets a `prior_false_dl` flag (`scripts/flag_prior_false_downloads.py`
FLAGS), so the next downloader sees the warning on the hub.

## Every problem file gets a traced cause (`--ledger`)

`data/acquisition_feedback_ledger.csv` (local and git-ignored, because it names team members and the repo is public) holds one row per problem file: `cause`,
`cause_owner`, `evidence`, `action_taken`, `report_to`, `reported_on`. `--ledger` traces the cause
automatically and `--ledger-notes` overrides it after review:

- Duplicates: re-download of the downloader's own earlier delivery (they worked from an old copy
  of the list), a parallel download by another contributor (no claim visible), or a todo row that
  stayed open although the library held the PDF (our reconciliation gap).
- Review, abstract, correction, supplement or wrong paper with the LIST's DOI in the filename:
  the DOI is wrong. `cause_owner` is "our Crossref DOI recovery" when the DOI came from
  `recover_missing_dois.py` (its cache), otherwise shark-references.
- A different DOI, or no DOI: the downloader's search or tool picked the wrong item.

Who gets what:
- **shark-references**: rows whose owner is shark-references, plus the shark-references rows of
  `outputs/sr_doi_quarantine.csv` (rows whose reason starts "OUR Crossref DOI recovery" are ours
  and are NOT sent).
- **Publishers**: rows where the publisher's DOI landing page serves the wrong PDF.
- **The downloader**: a short note listing their rows (re-fetch the list before each session; the
  wrong-part, wrong-volume and wrong-number cases).
- **Us**: DOI-recovery rows become new vetoes in `recover_missing_dois.py`; run
  `recover_missing_dois.py --recheck --apply` after any change to its gates.

## Structural checks that stop wasted downloads

- `scripts/reconcile_queue_with_library.py` (step 1b of `refresh_pdf_map_and_extract.sh`) closes
  any todo row whose mapped library PDF passes the identity test. Before 2026-10-12, three rows
  sat on the list for a year with verified PDFs in the library.
- `recover_missing_dois.py` vetoes: a candidate whose title names the record's author (a review or
  notice, "By A. Karpinsky"), "Review"/"Correction to" titles, peer-review report DOIs, abstracting
  journals, titles whose dates disagree, and any DOI won by two or more records. `--recheck`
  re-judges every DOI already on the list.
- The hub shows when the list was last published (the JSON's Last-Modified), and asks people to
  reload it before each session. A list closed locally is NOT closed for the team until
  `docs/papers_data.json` reaches GitHub Pages (main).

## Rules carried over from earlier deliveries

- Open the PDF. A file that exists is not a file that is right (2026-09-17: 5% misfiled).
- OCR any scan whose only text is a download watermark (GeoScienceWorld, BioOne cover pages):
  the page-one alpha count passes, but nothing is readable.
- A BioOne or JSTOR "section" PDF may hold several notes: split to the record's page range.
- Ligatures (`ﬁ`), accents and OCR slips break surname tests; the review step catches these.
- Count queue ROWS, not unique ids (`papers_data.json` has duplicate-id rows).
