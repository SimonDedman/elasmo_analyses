# Conference Abstracts Database — Design

**Date:** 2026-07-25
**Status:** Design (awaiting review)
**Author:** Simon Dedman + Claude

## Purpose

Build a standalone, queryable database of conference abstracts parsed from the
Carylanne conference-programme PDF collection (ASIH, JMIH, Sharks International,
EEA). It captures **every** abstract, flags the elasmobranch ones, and serves
two consumers:

1. **elasmo_analyses** — via a parquet export of the elasmo-flagged subset,
   field-aligned to `outputs/literature_review_enriched.parquet` so it can be
   joined or ingested.
2. **Carylanne** — via a shareable single-file export (SQLite + JSON + a
   formatted xlsx review sheet).

## Source data

`database/others_libraries/Carylanne/` (on the `/home` partition):

- **Digitised Programs/** — 46 native-text PDFs: ASIH 1992-2019, JMIH 2005-2026,
  Sharks International (SI2026 + one more), plus dedicated abstract books, poster
  lists, plenary-session and sessions-symposia files.
- **Undigitised Programs/** — 7 JMIH programmes 1997-2004, **OCR'd 2026-07-24**
  (image-only → full text layer). These are the noisy-OCR tail.

Total ≈ 53 PDFs. A single 738-page abstract book (e.g. 2016 JMIH) holds ~800
abstracts, so total volume plausibly runs to **several thousand** records.

### Structural realities (verified against the data)

- **One file = one meeting, many societies.** JMIH is the *joint* meeting; a
  single JMIH file contains abstracts from AES (American Elasmobranch Society,
  the elasmo one), ASIH, HL (Herpetologists' League), SSAR, NIA, etc. Standalone
  "ASIH" files are ASIH meetings. **Society is a per-abstract property, not a
  per-file one.**
- **Society tagging appears in two places on the session line — a prefix and an
  award suffix.** In JMIH abstract books each abstract begins with a line like
  `0974 AES Sawfishes Symposium, Salon E, Sunday 10 July 2016`. Two signals:
  - **Session-name prefix** (symposia): `AES Sawfishes Symposium` (23),
    `ASIH: … Symposium`, `HL: …`, or multiple `HL, ASIH, SSAR: … Symposium` (6).
  - **Award-competition suffix** (posters/talks): `… Friday 8 July 2016; SSAR
    VICTOR` or `; AES CARRIER` — i.e. `; <SOCIETY> <AWARD>`. In the 2016 book:
    40 `SSAR VICTOR` (herp), 5 `AES CARRIER` (elasmo).
  - Generic `Poster Session I/II` (274) and `Lightning Talks` (31) with **no**
    prefix and **no** award suffix are the remaining share.
  Coverage measured in the 2016 book: **~54% of entries (201/372) carry an
  explicit society signal** (prefix or award suffix); the rest are inferable.
- **Society is inferable from subject matter, not just the elasmo flag.** JMIH's
  constituent societies map to taxonomic domains — elasmobranch subject → AES,
  other fish → ASIH/NIA, amphibians/reptiles → HL/SSAR — so the LLM can assign a
  *society* (not merely is_elasmo) to every untagged record from its
  title+abstract. `is_elasmo` then derives from society = AES. So society is
  largely structural (~54%) with content inference filling the remainder.
- **Formats differ by society/era.** JMIH abstract books: `ID + session +
  location + date`, authors with superscript affiliation markers, title, body,
  underscore-rule separator. ASIH abstract books: `Surname, First; Surname,
  First` author line, title, single affiliation line, body, underscore
  separator, no ID/session line. OCR'd 1997-2004: same content but degraded
  (mid-word line breaks, garbled headers) → low-confidence tail.
- **Program books vs abstract books.** Some PDFs are schedules only (little/no
  abstract body); some are full abstract books; some are poster lists or plenary
  extracts. `doc_type` records which.

## Scope decisions (agreed)

| Decision | Choice |
|---|---|
| Coverage | **All** abstracts captured; elasmo ones flagged (not filtered out) |
| Primary store | **SQLite**, with parquet/JSON/xlsx exporters |
| Parsing | **Hybrid**: rules segment blocks, local LLM extracts fields, confidence per record |
| Location | **This Data Panel project** (`scripts/`, `database/`) |
| LLM | **Ollama local** (qwen2.5:3b) for bulk; **Fable** escalation for low-confidence / OCR-noisy tail only |
| elasmo_analyses feed | **Parquet** aligned to `literature_review_enriched.parquet` |

## Store & schema

**`database/conference_abstracts.db`** (SQLite). Three tables.

### `meetings`
The event a PDF represents (no single society).

| column | type | notes |
|---|---|---|
| meeting_id | INTEGER PK | |
| meeting | TEXT | JMIH / ASIH / SI / EEA |
| year | INTEGER | |
| name | TEXT | full event name |
| location | TEXT | |
| dates | TEXT | |
| source_pdf | TEXT | path/filename |
| doc_type | TEXT | program_book / abstract_book / poster_list / plenary / sessions_symposia |
| page_count | INTEGER | |
| is_ocr | INTEGER | 1 if from the OCR'd set |
| parse_status | TEXT | ok / partial / failed |
| n_abstracts | INTEGER | loaded count (for QA vs expected) |

### `abstracts`

| column | type | notes |
|---|---|---|
| abstract_id | INTEGER PK | |
| meeting_id | INTEGER FK | |
| program_number | TEXT | the 4-digit ID where present, else null |
| title | TEXT | |
| presentation_type | TEXT | talk / poster / lightning / symposium / plenary / keynote |
| session_name | TEXT | raw session string |
| societies_explicit | TEXT | societies from session prefix AND award suffix: "AES", "HL,ASIH,SSAR", or null |
| award | TEXT | award-competition name where present (e.g. "AES Carrier", "SSAR Victor Hutchison"), else null |
| society_inferred | TEXT | LLM-inferred society from title+abstract subject (AES/ASIH/HL/SSAR/NIA), esp. when societies_explicit is null |
| society | TEXT | resolved society: societies_explicit if present, else society_inferred |
| society_basis | TEXT | session_prefix / award / content — how `society` was set |
| session_datetime | TEXT | |
| location | TEXT | room |
| abstract_text | TEXT | full body; null for schedule-only entries |
| length_words | INTEGER | word count of abstract_text |
| **is_elasmo** | INTEGER | 1 if society = AES, OR meeting ∈ {SI, EEA} |
| **elasmo_basis** | TEXT | session_prefix / award / meeting / content — provenance of the elasmo flag |
| confidence | REAL | 0-1 extraction confidence |
| needs_review | INTEGER | 1 for low-confidence / OCR-noisy |
| source_page | INTEGER | |

### `authors`

| column | type | notes |
|---|---|---|
| author_id | INTEGER PK | |
| abstract_id | INTEGER FK | |
| full_name | TEXT | normalised "First Last" |
| position | INTEGER | author order (1 = first) |
| is_presenter | INTEGER | 1 if marked; else inferred (first author) |
| presenter_inferred | INTEGER | 1 when is_presenter is an inference, not marked |
| affiliation | TEXT | |
| affiliation_country | TEXT | best-effort |
| raw_author_string | TEXT | the pre-parse source, for audit |

Person-identity normalisation and OpenAlex linking are **out of scope for v1**
(the raw strings are retained so it can be added later).

## Pipeline

Per PDF, driven by a per-format **config block** (society/year/doc_type →
segmentation rules), mirroring Shark Network's conference-agnostic design.

1. **QA + re-OCR gate.** Run whole-doc pdftotext quality (alpha count + 3+letter
   word density, thresholds from the 2026-07-24 quality pass) over ALL PDFs
   including the 46 already-digitised ones. Any with no/low-quality text →
   re-OCR through the OCR pipeline (`carylanne_ocr.sh` approach, force-OCR since
   a bad text layer may exist), so the parser always sees the best text. Record
   which files were re-OCR'd.
2. **Classify.** meeting / year / doc_type from filename + first pages.
3. **Segment** the text into abstract blocks — reuse/extend Shark Network's
   agenda parsers (`parse_jmih2026_agenda.py`, `make_aes_only_agenda.py`,
   `build_aes2026_schedule_tab.py`) plus format-specific cues (underscore rules,
   4-digit IDs, `Surname, First;` author lines).
4. **Extract fields (hybrid).** Rules first pass for the structured fields;
   local **Ollama** LLM cleans/structures each block into the `abstracts` +
   `authors` JSON. Low-confidence or OCR-noisy blocks → `needs_review=1` and
   escalate to **Fable** (run only when Simon is away, shared Max budget).
5. **Society + elasmo tag.** Parse explicit society from BOTH the session-name
   prefix AND the `; <SOCIETY> <AWARD>` award suffix into `societies_explicit`
   (+ `award`). Where explicit is absent, the LLM infers `society_inferred` from
   the title+abstract subject (elasmobranch → AES, other fish → ASIH/NIA,
   amphibian/reptile → HL/SSAR). Resolve `society` (explicit else inferred) with
   `society_basis`. Then set `is_elasmo` = (society = AES) OR meeting ∈ {SI, EEA},
   and `elasmo_basis` in priority order session_prefix / award / meeting /
   content. Every record thus gets a society and an auditable elasmo provenance.
6. **Load** into SQLite; dedup by (meeting_id, program_number) or, where no ID,
   (meeting_id, normalised title).
7. **Export:**
   - elasmo subset → `outputs/conference_abstracts_elasmo.parquet`, fields
     aligned to `literature_review_enriched.parquet` (title, year, authors,
     abstract, …) for elasmo_analyses.
   - full set → `outputs/conference_abstracts.json` and a formatted
     `outputs/conference_abstracts.xlsx` (frozen/bold/autofiltered) for Carylanne.

## Reuse

- **Shark Network** (`/media/simon/data/Documents/Si Work/PostDoc Work/Shark
  Network`): JMIH/AES agenda parsers, conference-agnostic config
  (`gen_conference_cascade.py`), AES-only filtering, the SQLite multi-conference
  schema pattern, and its AES/conference event-prep + Google-calendar-reminder
  code as a **downstream hook** (event prep can later read this abstracts DB).
- **This project:** `scripts/flag_conference_abstracts.py`,
  `scripts/scrape_aes_abstracts.py`, and the 2026-07-24 pdftotext quality-check
  script.

## Quality & validation

- Per-record `confidence` + `needs_review`; `elasmo_basis` provenance.
- `meetings.n_abstracts` vs a rough expected count (pages × density) per file to
  catch under-segmentation.
- xlsx review sheet surfaces `needs_review` records for Carylanne/Simon to fix.
- Spot-check a sample per format family (JMIH book, ASIH book, OCR'd 1997-2004).

## Non-goals (v1)

- Person-identity resolution / OpenAlex linking (raw strings retained for later).
- Ingesting these abstracts into the main literature parquet/RAG (separate step;
  the elasmo parquet export is the interface).
- Event-prep / calendar automation (Shark Network already owns this; it becomes
  a consumer of this DB later).

## Risks

- **Volume × LLM throughput.** Thousands of abstracts on local Ollama is a
  multi-hour background job; mitigated by rules-first extraction and reserving
  Fable for the tail.
- **OCR-noisy 1997-2004** may yield many `needs_review` records; acceptable —
  they're flagged, not silently wrong.
- **~46% of entries (untagged generic posters/lightning talks) lack an explicit
  society signal**, so their elasmo status leans on content inference;
  `elasmo_basis=content` makes those auditable and separable from the ~54%
  tagged by session prefix or award suffix.
