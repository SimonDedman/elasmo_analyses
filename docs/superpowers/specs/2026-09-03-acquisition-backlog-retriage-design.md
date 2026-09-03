# Acquisition backlog retriage, DOI recovery, and per-member assignment

**Date:** 2026-09-03
**Status:** design agreed for sections 1-2; sections 3-4 written but to be
revisited once the retriage and DOI-recovery numbers land.
**Branch:** `conference-abstracts-db` (current) or a new
`acquisition-retriage` branch.

## Problem

The acquisition todo list holds 11,877 outstanding papers and a single flat
percentage is used to describe progress against it. That number is not
actionable, for three separate reasons:

1. Roughly 1,200 rows are conference abstracts, which the conference-abstracts
   project is acquiring by a completely different route. They will never be
   "downloaded" and they permanently depress the figure.
2. 9,472 rows (79.7%) have no DOI, so they have no resolvable publisher, no OA
   status, and no route to anybody's institutional access. They cannot be
   assigned to a person because we cannot say where they live.
3. Team members' journal access has never been mapped, so the manual-download
   effort is unrouted: everybody works the same undifferentiated list, and
   nobody knows which publishers are dead ends for whom.

The goal is to raise the acquisition rate by routing work to the people who can
actually complete it, which requires first knowing what is routable.

## Measurements taken before designing

Every number below was measured on 2026-09-03, not assumed. Two premises were
tested and both failed, which is why they are recorded here.

### Publisher resolution is not an age problem

Initially assumed pre-1980 papers were unreachable via institutional
subscriptions. Measured: publisher resolves for 15.1% of pre-1980 outstanding
rows against 22.4% of 1980+. That is a gradient, not a wall, and the pre-1980
resolvable set is led by JSTOR (152 rows), precisely the deep digitised backfile
a university library holds. **Year is the wrong axis; resolved identity is the
right one.**

### DOI recovery has no age gradient either

Sampled 100 no-DOI outstanding rows per era and ran a Crossref bibliographic
lookup with a title-and-year gate.

| Stratum | Recoverable | Ceiling on known DOIs |
|---|---|---|
| pre-1950 | 24.0% | n/a |
| 1950-1979 | 9.0% | 95.0% |
| 1980-1999 | 12.0% | 94.9% |
| 2000-2009 | 13.0% | 91.7% |
| 2010+ | 19.4% | 93.3% |

The ceiling column is a positive control: corpus papers whose DOI we already
hold, with the DOI hidden, fed through the identical pipeline. Recovery is
92-95% in every era, so the pipeline is sound and the low recovery rates are a
property of the data.

**Consequence:** the residual no-DOI pool is grey literature, regional
non-English serials, museum bulletins, and book chapters at every date. There
is no case for restricting DOI recovery to post-2000. Run the whole pool.
Expect roughly 900-1,200 promotions from ~6,970 article-shaped no-DOI rows.

### The click log is a usable access instrument

The download helper's click log holds 1,038 attributed DOIs. Joining it against
what is still outstanding separates "attempted and failed" from "never
attempted". Elena's profile (444 attempts) reads as real holdings: Wiley
223/334, Springer 25/25, Royal Society 11/23, Elsevier 0/33, Inter-Research
0/28.

Validated by control:

| Check | Result |
|---|---|
| Elena / Wiley "landed" | 12 of 12 sampled verified on disk |
| Elena / Springer "landed" | 9 of 12 on disk |
| Anon / Springer "landed" | 11 of 12 on disk |
| Elena / Elsevier "no access" | 29 clicked, 0 in corpus, 0 on disk |

Two biases recorded rather than hidden. The outstanding-list proxy for "landed"
runs about 25% optimistic because of filename variance, so the production
matrix counts PDFs verified on disk instead. And a click is not an acquisition
attempt: Chiara's 15 and Carylanne's 12 clicks with no deliveries mean they have
not tried, not that they lack access.

## Section 1: track model

Every row in `docs/papers_data.json` carries exactly one `track`, assigned by
`scripts/assign_acquisition_tracks.py`, and each track reports its own
percentage. Tracks are keyed on resolved identity, never on year.

| Track | Definition | Size (2026-09-03) | Owner |
|---|---|---|---|
| **A** assignable | has a DOI, so publisher resolves | 2,405 | team members, by access |
| **B** abstract-covered | no DOI, conference-shaped journal string | 1,126 | conference-abstracts project |
| **C1** DOI-recoverable | no DOI, article-shaped journal name | 6,965 | automated recovery pass |
| **C2** archival | no DOI, grey literature or damaged metadata | 1,381 | BHL, archive.org, ILL |
| | | **11,877** | |

The four tracks partition the outstanding set exactly, with no row in two
tracks and none unassigned. A further **75 conference-shaped rows do carry a
DOI** and so sit in A; they are included in the Track B review sheet because a
DOI does not stop something being an abstract, but they are not moved out of A
until the review says so. Total conference-shaped rows under review: 1,201.

Tracks are not static. A C1 row whose DOI is recovered becomes A. A C2 row whose
journal field is repaired becomes C1. The assignment script is idempotent and
re-runs after every sync.

Reporting: one acquisition percentage per track plus an overall, so the archival
tail stops masking movement on the part the team can affect. Track B leaves the
acquisition denominator entirely once a matching abstract record is confirmed,
recorded as satisfied-by-abstract rather than acquired.

### Track B migration is human-gated

`outputs/acquisition_triage_<date>.xlsx`, tab `Conference_series`, lists all 369
conference-shaped journal strings covering 1,201 rows, pre-classified
CONFERENCE_SERIES / PEER_REVIEWED_JOURNAL / UNCLEAR and cross-checked against
the five series already in `outputs/conference_coverage_matrix.xlsx`.

The pre-classification is wrong in both directions by design, being recall-
biased: "Proceedings of the Biological Society of Washington" is a real journal,
"Programme Booklet of The" is a truncated abstract book. Simon and Carylanne fill
`decision` (MIGRATE / KEEP_AS_PAPER / SPLIT / UNSURE) and `series_name`.

Already identified as new series to add to the coverage matrix, which currently
tracks only ASIH/JMIH, AES, EEA, OCS, and SI:

- **Encuentro Colombiano sobre Condrictios**, 123 rows, 2014. Confirmed by Simon
  as missing from the abstracts job list.
- **World Congress of Herpetology**, 98 rows, 2012.
- **"Conference Abstract"**, 87 rows, 1980-2022, an unlabelled catch-all that
  needs breaking apart by year before it can be assigned to series.
- Others surfaced by the review: Colloque international (48), Programme Booklet
  of The (47), Book of Abstracts (23), First Pacific Shark Workshop (12).

Sharks International is already tracked. "Proceedings of the European
Elasmobranch Association" classifies as UNCLEAR on wording but is flagged as an
already-tracked series so that no duplicate is created for it.

### Damaged metadata is human-gated too

Same workbook, tab `Damaged_journals`: 202 rows across 88 distinct strings where
the journal field is blank, truncated ("The", "pp.", "of the"), a bare author
surname ("Martin"), or an editor credit. These defeat title-based lookup, so
they block C1 until repaired.

Detection deliberately avoids a length rule. `Ambio` and `Copeia` are five- and
six-character real journals; a length test condemns them beside `SMITH`. Instead
a journal string is flagged as a surname only when it matches that row's own
first-author surname, and as a title only when it duplicates the row's own
title.

## Section 1b: findspot backfill (do this FIRST)

Investigating the stub journal strings ("Conference Abstract", "In Programme
Booklet of The", "Proceedings of the", "Book of Abstracts") found that they are
**our own damage, not Shark-References'**, and that the lost text is still
live and re-fetchable.

For literature_id 14171:

```
stored by us : "In Programme Booklet of The"
live on SR   : "In Programme Booklet of The 15th Annual Scientific Conference
                of the European Elasmobranch Association, Berlin,
                29.10.-30.10.2011"
```

The current parser is correct: `sync_shark_references.py` line ~302 takes
`<span class="lit-findspot">` verbatim and returns the whole string. The
truncation was baked in by an earlier scrape or cleaning step and has never been
back-filled, because Phase 2 diffs and only enriches genuinely NEW papers.
Existing rows keep whatever they were first stored with.

### Measured on the live letter B and C pages

| Measure | Result |
|---|---|
| Our rows matched to live entries | 918 (B), plus C |
| Ours is a truncated prefix of live | 75.2% |
| Non-conference rows where the discarded tail is only volume/pages | 835 (benign, correct behaviour) |
| **Conference-shaped rows that gain a real conference name** | **161 of 186, 87%** |

The 75% headline is misleading and must not be quoted on its own: stripping
`"Zootaxa, 5357(3), 301-341"` to `"Zootaxa"` is exactly what
`clean_journal_name()` should do. The damage is confined to the case where the
discarded remainder carried the venue's identity rather than its volume and
pages, which is precisely the conference rows.

Recovered strings also carry the page number within the abstract book
(`"...23rd annual conference, 16-18 October 2019, Rende, Italy: 53"`), which the
conference-abstracts project needs to link an abstract to its book and page.

### Design

Add a **`findspot_raw`** field, populated verbatim from the list pages, and
never cleaned. `journal` and `journal_clean` keep their current meanings and
current values, so nothing downstream breaks.

`findspot_raw` then serves three consumers:

1. **Track B series identification.** The conference name, year, city, and page
   come free, which is most of what the coverage matrix needs.
2. **C1 DOI lookup.** A Crossref bibliographic query with a real venue string
   beats one with "Proceedings of the".
3. **Damaged-field repair.** Some of the 202 `Damaged_journals` rows are simply
   truncations that the raw findspot resolves outright.

Implement as a new phase in `sync_shark_references.py` that writes
`findspot_raw` for every row seen on the list pages, not only new ones, so the
backfill runs once and then self-maintains on every monthly sync. The crawl is
already happening; only the write is new.

**Sequencing:** this runs BEFORE the Track B review sheet is finalised and
before the C1 DOI pass, since both get materially better inputs from it. The
current `acquisition_triage_2026-09-03.xlsx` should be regenerated afterwards.

### Why not an LLM, and specifically not Fable 5.1

Fable is the strongest model available here and it would still be the wrong
instrument for this job. The conference names are not missing, ambiguous, or in
need of inference: they are sitting on a public web page we already crawl every
month. Asking a model to reconstruct "In Programme Booklet of The" into a
conference identity is asking it to guess at a fact we can simply fetch, and a
plausible wrong guess is indistinguishable from a right one at review time.

Re-scrape first. Fable earns its place only on the genuine residue, where SR's
own findspot is uninformative and the answer has to come from the PDF or from
judgement. Measure that residue after the backfill rather than assuming its
size.

## Section 2: DOI recovery pass

`scripts/recover_missing_dois.py`, run over all no-DOI rows regardless of year.

**Lookup.** Crossref `query.bibliographic` with title plus journal, five rows,
keyless, `mailto` set. Reuses `_title_similarity` from
`sync_shark_references.py` so there is one definition of title matching in the
project, not two.

**Acceptance, tighter than the probe used.** The probe's title-plus-year gate
produced a wrong DOI in about 5% of control cases. Given that the 2026-04
off-by-one corruption put 45 wrong DOIs into the download helper for three
months without anyone noticing, a confidently wrong DOI is worse than a blank
one. Production therefore requires **both**:

- title similarity >= 0.90, **or** title similarity >= 0.75 with a first-author
  surname match against the Crossref record; **and**
- year within +/-1.

Anything that passes the probe gate but fails this one is written to a review
file rather than applied, so the tightening loses no candidates, it only
withholds them from automatic application.

**Three outcomes, never two.** `hit`, `rejected` (candidates returned, none good
enough), `absent` (no candidates), and `error` kept separate. Errors are
excluded from every rate denominator and shown as a count, because a 429 that is
silently counted as "no DOI exists" turns a rate limit into a finding. Only 200
responses are cached; a cached failure would make a transient block permanent.

**Coverage recorded beside results.** Rows queried, rows erroring, and last
index reached are written per run, so a truncated pass is visibly truncated
rather than looking complete.

**Output.** Recovered DOIs are applied to `docs/papers_data.json` and propagated
to the parquet by the existing Phase 5b path. Every applied DOI passes through
the existing Phase 3b Crossref verification as a second, independent check
before it reaches the download helper. Near-misses go to
`outputs/doi_recovery_review_<date>.xlsx` for manual adjudication.

## Section 3: team access matrix

*To be revisited once sections 1-2 land and the real Track A size is known.*

`outputs/team_access_matrix.xlsx`, one row per person and publisher, seeded from
evidence and corrected by the people themselves.

| Verdict | Rule |
|---|---|
| `has_access` | >= 5 attempts, >= 60% landed |
| `no_access` | >= 10 attempts, 0 landed |
| `partial` | >= 5 attempts, in between |
| `untested` | everything below those floors |

`untested` is the default and is never collapsed into `no_access`. The floors
exist because Chiara's 15 and Carylanne's 12 exploratory clicks would otherwise
be read as evidence of no access when they are evidence of nothing.

"Landed" is counted from PDFs verified on disk, not inferred from the
outstanding list, because the Springer control showed that proxy runs about 25%
optimistic.

Each person gets a sheet pre-filled with their inferred rows plus every
publisher we need that they have no history with, so they correct a draft rather
than face a blank form.

**Open dependency:** 546 of 1,038 clicks are anonymous. The helper needs a name
attached before per-person tracking is meaningful going forward.

## Section 4: per-member assignment

*To be revisited alongside section 3.*

Assignment goes through the existing download-helper HTML rather than a new
channel, because that helper writes the click log, and the click log is the
instrument the access matrix depends on. A parallel xlsx-only channel would
produce deliveries that cannot be attributed and would blind the matrix over
time.

`scripts/generate_closed_access_html.py` gains a per-person mode. Each person
receives pages for publishers where they are `has_access` or `partial`, plus a
small stratified calibration batch drawn from their `untested` publishers so the
matrix keeps learning. Papers no member can reach fall into an unassigned pool,
which is the evidence base for an interlibrary-loan request or a direct author
request.

## Operational notes

- **Disk headroom.** `/media/simon/data` is at 98%, 44G free. A large
  acquisition round wants headroom before it starts.
- **Sync cadence.** The August sync never fired; last successful run before
  today was 2026-07-24, and today's found 2,760 new papers. Worth checking why
  the anacron 30-day trigger missed a cycle.
- **Unblocked by today's sync.** Issue #17, the Shark-References feedback
  package of DOI corrections and papers they lack, was waiting on the August
  sync and can now proceed.

## Testing

- `scripts/lib/repair_xlsx.R` is verified by the review workbook now loading in
  openpyxl, which it did not before: openxlsx writes a relationship to
  `xl/drawings/drawing1.xml` that it never emits, making every review sheet this
  project produces structurally invalid.
- Track assignment: the four tracks must partition the outstanding set exactly,
  asserted as a count check after every run.
- DOI recovery: the positive control (known DOIs, hidden, re-recovered) is kept
  as a regression test, and must stay above 90% or the lookup has regressed.
- Access matrix: a cell may never report `no_access` below the attempt floor,
  asserted directly.

## Related

- `memory/project_manual_download_fiu_access.md` — supersedes its claim that no
  attempt log exists; the click log is one.
- `memory/project_doi_offbyone_corruption.md` — why the recovery gate is
  deliberately stricter than the probe's.
- `memory/project_conference_abstracts_db.md` — Track B's destination.
- `docs/superpowers/specs/2026-07-25-conference-abstracts-db-design.md`
