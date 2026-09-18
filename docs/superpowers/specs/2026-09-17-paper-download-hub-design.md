# Paper download hub: routing the remaining papers to the people and scripts that can get them

**Date:** 2026-09-17
**Status:** design agreed in conversation on 2026-09-16/17 and largely built the same night;
this document records the design as built, the decisions taken, and what is still open.
**Branch:** `pdf-dedupe-hardlinks` (commits 4ada8385b, 1d62b6dc8, e6e2a6781).
**Supersedes in part:** sections 3 and 4 of
`2026-09-03-acquisition-backlog-retriage-design.md` (team access matrix, per-member
assignment), which are now implemented here.

## Problem

Simon wants the team to join a push to download the remaining papers, with a page that
shows what remains and why, a per-person view of what each member can realistically get,
a leaderboard, and a coauthorship threshold. Before the push could be routed, three
things were unknown: how much of the "remaining 11,665" was actually downloadable by a
person, who could reach which publisher, and how much could be fetched by scripts without
anyone lifting a finger. The design answers those in that order, because every paper a
script fetches is one nobody has to be motivated to fetch.

## Measured before designing (2026-09-16/17, do not re-derive)

- Outstanding rows were 11,665: 691 triaged conference abstracts, 557 conference-shaped
  no-DOI rows, 600 DOI rows Unpaywall calls open but the cascade failed to fetch, 1,529 DOI
  closed, 1,058 DOI with OA status never checked, 103 no-DOI stub journals, 7,127 no-DOI
  article-shaped rows.
- The no-DOI pool is genuinely DOI-less. Crossref ran over all of it (0 errors); an
  independent OpenAlex title probe on 100 post-2000 rows found 2 DOIs; a 40-row audit of
  "rejected" candidates found 38 were different works. Stop tuning matchers.
- 1,042 "unresolved publisher" DOI rows were our prefix map missing secondary prefixes
  (Wiley 10.1002, Elsevier 10.1006...), not unknown publishers; Crossref resolves all but 5.
- Hidden meeting abstracts: 372 rows under journal names (SVP supplements, SICB, SIBM
  proceedings notes) are abstracts, not papers. 23 real papers were also caught by the
  "supplement" rule and reverted; page span >= 4 is the guard.
- Team access can be inferred from deliveries: Elena has Elsevier, Inter-Research, partial
  Wiley/Springer; David RG Elsevier, Inter-Research, Company of Biologists, Informa; Ulrich
  Springer, Elsevier; Guuske Elsevier, Wiley. Everyone else is untested, never no_access.
- Institutional catalogues answer ISSN lookups keyless where they run Primo VE (FIU, OSU,
  UC Davis, Valencia, ASU). FIU holds 268 of the 311 assignable-pool journals with an ISSN
  (1,155 rows); 227 journals still lack an ISSN.
- FIU's EZproxy forbids systematic downloading; the sanctioned bulk routes are publisher
  TDM programmes (Elsevier, Springer Nature, Wiley, JSTOR DfR, T&F, CUP, OUP).

## Design

### 1. One page: `outputs/remaining_papers_dashboard.html` (published at `docs/acquisition/remaining_papers.html`)

Built by `scripts/build_remaining_papers_dashboard.py`, self-contained, inline SVG, light
and dark, a table view under every chart. Sections: constitution of the outstanding set
(seven exclusive classes), era x class, per-year, publisher x OA status for DOI rows,
2024+ rows, the no-DOI pool by era and document type, the top-45 no-DOI venues with a
route and likely member per venue (`data/venue_routing.csv`), the Simon-vs-everyone card,
the team leaderboard, and a per-card comment channel backed by the same Google Apps
Script the download helper already uses (`getComments` / `addComment`; a `comments`
sheet; deployed by Simon on 2026-09-17).

Classification rule, in `classify()`: triage flag -> abstract; else DOI with Unpaywall
colour -> doi_oa / doi_closed / doi_unknown; else conference-shaped venue string ->
conf_shaped; else blank/stub/surname journal -> nodoi_damaged; else nodoi_article.

### 2. Points, leaderboard, threshold

- A point is a PDF verified filed into the library from that person's NAS drop folder
  (`database/others_libraries/<Name>/`, scanned daily). Helper clicks are intent, not
  delivery, and are not points (53% were anonymous anyway); they stay as access evidence.
- Abstract-book credit: 25% of the elasmo abstracts in each book a person supplied, ceil
  per book. The abstracts team (Carylanne, Cat, Brit, David Green) is acknowledged on the
  same chart but is on a different incentive: only they can supply programmes.
- Attribution of books: same series + year + document type in a person's drop folder;
  phone scans and Copeia summaries to Carylanne; Oxford Abstracts exports to David Green;
  elasmo.org harvests and programme exports to Simon; weak matches flagged in the table.
- Simon's tally is the library minus everyone else's (his own collection plus every
  automated run), shown in the table and the joke card, off the team chart's axis.
- Coauthorship line: 500 points, provisional. The line must track the pool: too low and
  people stop while papers remain, too high and nobody qualifies. The page shows
  "assignable papers per person below the line" so the number can be re-set once the
  script routes have drained what they can.

### 3. Routing: scripts first, people second

Anything a script can fetch is pushed to the top of the stack. Routes proven on
2026-09-17 and being turned into `scripts/fetch_free_sources.py` channels: VLIZ/MarineInfo
(De Strandvlo and Belgian/Dutch grey literature), ICES library on Figshare, FRDC by project
number, J-STAGE, Springer Meta/OA (TDM when approved), plus the earlier Cybium, Acta
Adriatica, Annales, Afzettingen, Cossmanniana, SciELO, NOPR, NMMNHS (CONTENTdm),
archive.org by constructed identifier, NOAA/FAO/ICCAT/NAFO/CSIRO/IUCN report series.
Browser-only sources (NOAA IR, FRDC for unpatterned reports, Acta Geologica Polonica behind
Incapsula) run in a Chrome session Simon opens; a session cookie plus Chrome UA lets curl
finish the job.

Paywalled DOI rows go to people by publisher, using `outputs/team_access_matrix.xlsx`
(publishers x people; evidence from deliveries and clicks; verdict floors from the
2026-09-03 spec; untested never collapses to no_access) and, for FIU, the catalogue
pre-filter. Bulk paywalled blocks (Elsevier ~500, Wiley ~250, Springer ~170, JSTOR ~340)
go through publisher TDM programmes requested from FIU Libraries (Jamal Pathan, email sent
2026-09-17), never through a proxy script.

Meeting abstracts leave the download denominator into the abstracts project (triage flag,
coverage-matrix columns SVP, SICB, SIBM added). Book chapters route to one document each
(`outputs/book_requests_2026-09-17.xlsx`): editors (Heithaus for two volumes), colleagues,
ILL; archive.org lending is for reading, not for files.

### 4. Ingest safety (learned the hard way on 2026-09-17)

A staged file named `<literature_id>.pdf` is filed under that id after an identity check
(title tokens or first-author surname in the text); it is never rematched by title, and a
staged copy is never deleted unless the destination has the same sha256 or passes the
identity check. Existence on disk is not verification: the check must open the PDF and
confirm the queue row left. Tests in `scripts/test_acquire_cascade.py`.

### 5. Communal exploration

The page is public on GitHub Pages under `docs/acquisition/`; comments are per card and
collated at the bottom, attributed by the roster name picker; no accounts needed. Simon
prompts exploration by pointing the team at a card; answers land in the sheet.

## Decisions taken (Simon)

500-point line, provisional. Clicks dropped. 25% abstract credit. SOMEPEC is a series, not
a person. David = David RG. Fable corpus burn on hold (bad ROI on a personal subscription).
E_A acquisition batches are pre-authorised in CLAUDE.md. No automation through the FIU
proxy. Coverage-matrix additions approved ("matrix: all"). JMIH 1998/2005 Fable merged.

## Open

- Re-set the 500 line after the Springer TDM and Elsevier token blocks land.
- Per-person routed pages (spec 2026-09-03 section 4): generate from the access matrix +
  FIU pre-filter; not yet built.
- 227 assignable-pool journals without an ISSN; OpenAlex enrichment blocked by 429s (452
  DOIs correctly unbanked); 297 JMIH records without a society tag; 14590 identity hold;
  ICES 6317 was a false Figshare match.
- Reviews held for Simon: `outputs/download_push_review_2026-09-17.xlsx` (Tue 22 Sep).

## Testing

- Dashboard: `node --check` on the inline script and a headless-Chrome render before any
  hand-over (a single unescaped apostrophe blanked the page once).
- Finalize: dry-run first; independent library count before/after; a random sample of
  ingested ids opened and title-checked; queue rows confirmed gone.
- Fetch channels: positive control on a known-held item per channel; blocks recorded as
  blocked; coverage.json beside every manifest.
