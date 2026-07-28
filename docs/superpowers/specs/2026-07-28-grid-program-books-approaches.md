# Grid/matrix program books (2006-2019) — approaches & assessment

**Date:** 2026-07-28
**Problem:** the 2006-2019 JMIH "Program-Book" PDFs are at-a-glance schedule
**grids** (rooms × time), not the clean `Session N: … / N.N | Title` linear
format of 2021-2025. pdftotext linearises the grid columns badly, interleaving
cells. The B (`parse_program_book.py`) parser gets ~0 usable talks from them.

## What testing showed
- No `N.N | Title` lines, no/one `Session N:` header in 2010/2013/2019.
- ~1,000-1,650 "long title-ish" lines per book, but most are committee rosters,
  affiliations, and logistics — NOT talk titles. (2010 had ~43 genuine
  taxonomic/talk phrases, so *some* title content exists, thinly.)
- `pdfplumber` 0.11.7 IS installed → word-level (x,y) coordinates work.
- `pdftotext -layout` preserves horizontal spacing but is slow and still
  interleaves complex grids.

## Approaches considered

**A. `pdftotext -layout` + column heuristics.** Parse the space-aligned layout,
detect column boundaries by whitespace. Cheap, no deps. *Con:* fragile on
wrapped cells and multi-block grids; breaks across page splits.

**B. pdfplumber coordinate clustering (most robust for true grids).** Extract
words with (x0, top); cluster x → room columns, y → time rows; reconstruct each
cell as a talk. Handles the real grid geometry. *Con:* per-book tuning; a "cell"
often holds only a session name + moderator, not a per-talk title.

**C. pdfplumber `extract_tables()`.** Uses ruling lines to get cells directly.
Cleanest *if* the grids are drawn with borders. *Con:* many at-a-glance grids
are whitespace-only (no rulings) → returns nothing. Quick to test per file.

**D. LLM extraction (Ollama).** Feed each page's `-layout` text to qwen2.5:3b,
ask for `{title, authors, session, time}` JSON. Robust to any layout. *Con:*
slow (60-76 pages × books), can hallucinate, needs validation; and it cannot
invent titles that aren't printed.

**E. Accept the limitation / change source (RECOMMENDED).** These are *program*
books whose grids largely list **session names + moderators, not per-talk
titles/authors/abstracts**. Where titles do appear they are sparse and hard to
associate with authors. The real detail for these years lives in the **abstract
books**, which we DON'T have for 2006/2010/2011/2013/2014/2017/2018/2019 — but
**Carylanne has ALL societies' abstracts 1992-2024 and is digitising the gaps.**
Parsing her abstract books (A1/A2/A3 parsers already work) yields far more, far
cleaner data than any grid-scraping method.

## Recommendation
1. **Primary:** get the 2006-2019 **abstract books** from Carylanne and run the
   existing A1/A2/A3 parsers — high yield, clean, includes bodies.
2. **If only the grid program books are ever available:** try C (extract_tables)
   first per file (cheap); fall back to B (coordinate clustering) for the grids
   that have no rulings; use B's output only for schedule metadata
   (session/room/time/moderator), accepting that per-talk titles will be partial.
3. **Do NOT** invest heavily in D (LLM) here — it can't recover titles that
   aren't printed, and the yield ceiling is set by the source, not the method.

Net: the bottleneck is the *source document type* (program vs abstract book),
not the parser. Route effort to acquiring abstract books, not grid-scraping.
