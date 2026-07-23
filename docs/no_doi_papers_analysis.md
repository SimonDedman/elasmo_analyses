# The No-DOI Long Tail — Profile of the 10,386 Hardest-to-Acquire Papers

**Date:** 2026-07-04. Papers in the download queue with **no DOI** — 81% of the remaining 12,789. These can't be queried against Unpaywall/OpenAlex/CrossRef by identifier, so they resist all our automated channels. This profiles them to find patterns and a smarter strategy than "keep clicking."

## Headline: this is not one problem, it's four

The 10,386 no-DOI papers break down into distinct, differently-tractable classes — and **a large share aren't full papers at all.** Treating them as one undifferentiated "download backlog" overstates the real acquisition target.

## 1. Year distribution — old-skewed, but not only old

| Era | Papers | |
|---|---|---|
| pre-1950 | 1,546 (15%) | pre-digital, no DOI ever assigned |
| 1950s–1990s | 4,496 (43%) | mostly pre-digital / regional |
| 2000s | 2,374 (23%) | **recent but DOI-less → grey literature** |
| 2010s–2020s | 1,970 (19%) | recent DOI-less → abstracts, reports |

**Median year 1996; 58% pre-2000.** The pre-2000 half is genuinely pre-digital (title-search + archive work). But **42% are 2000+** — recent papers *without* DOIs, which almost always means they're **not journal articles**: conference abstracts, reports, regional-journal pieces.

## 2. Top journals — the abstract problem is enormous

| Count | Source | Type |
|---|---|---|
| 546 | American Elasmobranch Society | **conference abstracts** |
| 125 | Shark International (Abstract) | conference abstracts |
| 122 | Encuentro Colombiano Condrictios (Abstract) | conference abstracts (Spanish) |
| 106 | Cybium | journal (French) |
| 97 | World Congress of Herpetology | conference abstracts |
| 87 | "Conference Abstract" | conference abstracts |
| 75 | Copeia | journal (old) |
| 71 | Report of Japanese Society for Elasmobranch Studies | proceedings (Japanese) |
| 57 | Journal of Vertebrate Paleontology | journal (fossils) |
| 49–46 | EEA Proceedings / "Book of abstracts" / "Programme Booklet" / Shark International posters | conference abstracts |

The queue is fragmented across **3,786 distinct journals** (top 20 = only 18%) — so no single bulk source solves it. But the *pattern* is loud: **the single largest identifiable class is conference abstracts.**

## 3. Type patterns (keyword classification of title + journal)

| Class | Papers | Note |
|---|---|---|
| **Conference / proceedings / abstracts** | **1,981 (19%)** | Largest class — and mostly *abstract-only*, no full text exists |
| Non-English titles | 1,128 (11%) | Cybium (FR), Biologia Marina Mediterranea (IT), Encuentro (ES), Het Zeepaard (NL), Japanese proceedings |
| Reports / bulletins / technical | 1,008 (10%) | Grey literature — institutional repos, not publishers |
| Books / chapters | 362 (3%) | Book-chapter extraction, not article download |
| Theses / dissertations | 244 (2%) | ProQuest / institutional repositories |

(Classes overlap; keyword-based so approximate.)

## 4. Patterns we can learn — and act on

1. **A big fraction aren't acquirable *because they aren't full papers.*** ~2,000 are conference abstracts / programme booklets / poster sessions — the "full text" often never existed. **These should be triaged, not chased.** Either accept the abstract as the record, or exclude them from the "must-download" target. Doing so shrinks the real no-DOI backlog from ~10,400 toward ~8,000.
2. **The AES abstracts (546) are a known, bulk-scrapable source.** They live at `elasmo.org/meetings/abstracts/` (per the Schiffman comparison, 663 AES abstracts are already in the DB). One targeted scraper could clear this whole cluster — and doubles as the Schiffman validation-benchmark linkage.
3. **Pre-2000 taxonomy/paleontology papers** (Copeia, Cybium, J. Vert. Paleontology, J. Paleontology, Schweizerbart) are ideal for **Biodiversity Heritage Library (BHL)** and archive.org — old natural-history journals are extensively digitised there, findable by title, freely.
4. **The 11% non-English tail** clusters in a handful of regional journals — these need regional/language-specific sources (and are lower priority for an English-language synthesis unless a co-author has access).
5. **No bulk win exists for the residual.** After removing abstracts (~2k), AES-scrapable (~0.5k), and BHL-able old journals, the rest is a genuine long tail of ~5–6k obscure DOI-less papers — realistically title-by-title, low-yield, and a candidate for **explicitly declaring out-of-scope** with a documented rationale rather than indefinite effort.

## Recommended strategy (effort-ranked)

| Action | Target | Effort | Yield |
|---|---|---|---|
| **Triage/flag conference abstracts** | ~2,000 | low (one classifier pass) | removes non-papers from the backlog |
| **Scrape AES abstract archive** | ~546 | low (one scraper) | high, automated |
| **BHL/archive.org title search for pre-1960 taxonomy** | ~1,500 | medium | moderate, free |
| Regional/language sources (co-author help) | ~1,100 | high | low |
| Declare the obscure residual out-of-scope | ~5,000 | — | closes the backlog honestly |

**Bottom line:** the no-DOI 10,386 isn't a wall of downloadable papers — it's ~2k abstracts (not papers), ~0.5k bulk-scrapable, ~1.5k free-in-BHL, ~1k non-English, and a ~5k obscure residual best declared out-of-scope. The *acquirable* fraction is a few thousand via targeted automation, not manual clicking.
