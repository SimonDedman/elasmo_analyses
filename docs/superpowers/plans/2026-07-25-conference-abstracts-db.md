# Conference Abstracts Database — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> or superpowers:subagent-driven-development to implement task-by-task. Steps
> use checkbox (`- [ ]`) syntax.

**Goal:** Parse the 53 Carylanne conference-programme PDFs into a queryable
SQLite database of abstracts (all captured, elasmo flagged), with parquet/JSON/
xlsx exports.

**Architecture:** A small Python package `scripts/conf_abstracts/` with one
module per pipeline stage (classify → qa/re-OCR → segment → extract → tag →
load → export), driven by a per-format config block. Rules do structural
segmentation; local Ollama does field extraction/society inference; Fable
escalates the noisy tail. Output in `database/conference_abstracts.db`.

**Tech Stack:** Python 3 (project `venv`), `pdftotext`/`pdfinfo` (poppler),
`ocrmypdf`+`gs` (re-OCR, as in carylanne_ocr.sh), SQLite (`sqlite3` stdlib),
`pandas`+`pyarrow` (parquet), `openpyxl` (xlsx), Ollama HTTP API (qwen2.5:3b),
Fable via the existing corpus-burn harness.

## Global Constraints

- Primary store: SQLite at `database/conference_abstracts.db`; schema =
  `meetings` / `abstracts` / `authors` (see spec).
- Capture ALL abstracts; `is_elasmo` is a flag, never a filter.
- `society` resolved from `societies_explicit` (session prefix + `; SOCIETY
  AWARD` suffix) else `society_inferred` (LLM from subject); `society_basis` ∈
  {session_prefix, award, content}. `is_elasmo` = society==AES OR meeting∈{SI,EEA};
  `elasmo_basis` ∈ {session_prefix, award, meeting, content}.
- Temp for any OCR/gs → `--tmpdir /media/simon/data/ocr_scratch` (AppArmor-
  permitted; NEVER /var/tmp — same partition as /home). See
  [[project_ocr_relang_pipeline]].
- xlsx outputs: frozen top row, bold header, autofilter (openpyxl).
- elasmo parquet export field-aligned to `outputs/literature_review_enriched.parquet`.
- Source PDFs live under `database/others_libraries/Carylanne/{Digitised,Undigitised} Programs/`.
- Reuse Shark Network parsers at `/media/simon/data/.../Shark Network/py/`
  (`parse_jmih2026_agenda.py` society/type logic) — do not import cross-project;
  copy/adapt the patterns.

---

### Task 1: Package scaffold, config, and SQLite schema

**Files:**
- Create: `scripts/conf_abstracts/__init__.py`, `scripts/conf_abstracts/config.py`,
  `scripts/conf_abstracts/schema.py`
- Test: `tests/conf_abstracts/test_schema.py`

**Interfaces:**
- Produces: `config.SOCIETIES` (set), `config.SOCIETY_ALIASES` (dict),
  `config.PRESENTATION_TYPES` (set), `config.DB_PATH` (Path);
  `schema.create_db(path) -> sqlite3.Connection` creating tables `meetings`,
  `abstracts`, `authors` per spec columns.

- [ ] **Step 1:** Write `tests/conf_abstracts/test_schema.py`:
```python
from scripts.conf_abstracts import schema
def test_create_db_has_tables(tmp_path):
    db = tmp_path/"t.db"; con = schema.create_db(db)
    got = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"meetings","abstracts","authors"} <= got
    cols = {r[1] for r in con.execute("pragma table_info(abstracts)")}
    assert {"society","societies_explicit","society_inferred","society_basis",
            "is_elasmo","elasmo_basis","award","presentation_type","abstract_text"} <= cols
```
- [ ] **Step 2:** Run `./venv/bin/python -m pytest tests/conf_abstracts/test_schema.py -q` → FAIL (no module).
- [ ] **Step 3:** Write `config.py` (SOCIETIES={AES,ASIH,HL,SSAR,NIA,SI,EEA,…},
  aliases, PRESENTATION_TYPES={talk,poster,lightning,symposium,plenary,keynote},
  DB_PATH) and `schema.py` with `create_db()` issuing the three `CREATE TABLE`
  statements from the spec (all columns), plus indexes on
  `abstracts(meeting_id)`, `authors(abstract_id)`.
- [ ] **Step 4:** Run pytest → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): package scaffold, config, sqlite schema`.

---

### Task 2: PDF classifier (meeting / year / doc_type)

**Files:**
- Create: `scripts/conf_abstracts/classify.py`
- Test: `tests/conf_abstracts/test_classify.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `classify.classify_pdf(path) -> dict(meeting, year, doc_type, is_ocr)`.
  `meeting` ∈ {JMIH,ASIH,SI,EEA}; `doc_type` ∈ {program_book, abstract_book,
  poster_list, plenary, sessions_symposia}; `is_ocr` bool (True if path under
  "Undigitised Programs" originally, tracked via a set).

- [ ] **Step 1:** Test with representative filenames:
```python
from scripts.conf_abstracts import classify
def test_classify_filenames(tmp_path):
    c = classify.classify_from_name  # pure-name helper, no PDF read
    assert c("2016-JMIH-Abstract-Book-180n2l2.pdf") == ("JMIH",2016,"abstract_book")
    assert c("2007 ASIH.pdf")[:2] == ("ASIH",2007)
    assert c("SI2026 - Abstract Book (29th April 2026).pdf")[:2] == ("SI",2026)
    assert c("2009-JMIH-Poster-Presentations-13bd3x5.pdf")[2] == "poster_list"
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `classify_from_name` (regex on year, meeting token,
  doc_type keywords: "abstract"→abstract_book, "poster"→poster_list,
  "plenary"→plenary, "sessions"/"symposia"→sessions_symposia, else
  program_book) and `classify_pdf` wrapping it + `pdfinfo` for page_count.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): pdf classifier`.

---

### Task 3: QA quality gate + re-OCR of poor digitised PDFs

**Files:**
- Create: `scripts/conf_abstracts/qa_ocr.py`
- Test: `tests/conf_abstracts/test_qa.py`

**Interfaces:**
- Produces: `qa_ocr.text_quality(pdf) -> dict(alpha, words, density, status)`
  with status ∈ {ok, low_quality, no_text} (thresholds: alpha<200→no_text,
  density<0.45→low_quality); `qa_ocr.ensure_ocr(pdf, scratch) -> path` that
  re-OCRs in place (force-ocr, eng, --max-image-mpixels 0 --optimize 0, tmpdir
  scratch, backup first) when status != ok, returns the (possibly rewritten) path.

- [ ] **Step 1:** Test `text_quality` classification on synthetic strings:
```python
from scripts.conf_abstracts import qa_ocr
def test_density_thresholds():
    assert qa_ocr._classify(alpha=0, density=0.0) == "no_text"
    assert qa_ocr._classify(alpha=5000, density=0.30) == "low_quality"
    assert qa_ocr._classify(alpha=5000, density=0.60) == "ok"
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `_classify`, `text_quality` (whole-doc pdftotext +
  counts, reuse qual_check.py logic), and `ensure_ocr` (shell out to ocrmypdf
  mirroring `.claude/jobs/*/tmp/carylanne_ocr.sh`: backup → force-ocr → atomic
  replace; skip if already ok).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): text-quality gate + re-OCR`.

---

### Task 4: Session-line parser (society prefix, award suffix, type)

**Files:**
- Create: `scripts/conf_abstracts/sessions.py`
- Test: `tests/conf_abstracts/test_sessions.py`

**Interfaces:**
- Produces: `sessions.parse_session_line(line) -> dict(session_name,
  societies_explicit, award, presentation_type, session_datetime, location)`.

- [ ] **Step 1:** Test on real lines from the 2016 book:
```python
from scripts.conf_abstracts.sessions import parse_session_line as p
def test_prefix_society():
    r = p("AES Sawfishes Symposium, Salon E, Sunday 10 July 2016")
    assert r["societies_explicit"] == ["AES"] and r["presentation_type"]=="symposium"
def test_award_suffix():
    r = p("Poster Session I, Acadia/Bissonet, Friday 8 July 2016; AES CARRIER")
    assert r["societies_explicit"] == ["AES"] and r["award"].startswith("AES")
    assert r["presentation_type"] == "poster"
def test_multi_society():
    r = p("HL, ASIH, SSAR: Eco-Evolutionary Dynamics Symposium, ...")
    assert set(r["societies_explicit"]) == {"HL","ASIH","SSAR"}
def test_no_society():
    r = p("Poster Session II, Acadia/Bissonet, Saturday 9 July 2016")
    assert r["societies_explicit"] == [] and r["presentation_type"]=="poster"
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: split leading `SOC[, SOC…]:` prefix; trailing
  `; <SOC> <AWARD>` suffix; type keywords (Poster→poster, Lightning→lightning,
  Symposium→symposium, Plenary→plenary, else talk); date/location by regex.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): session-line parser`.

---

### Task 5: Abstract-book segmenter (JMIH + ASIH formats)

**Files:**
- Create: `scripts/conf_abstracts/segment.py`
- Test: `tests/conf_abstracts/test_segment.py` + fixture `tests/conf_abstracts/fixtures/jmih2016_p50.txt`

**Interfaces:**
- Consumes: `sessions.parse_session_line`.
- Produces: `segment.segment_blocks(full_text, fmt) -> list[dict]` each with
  `program_number, session_line, author_block, title, abstract_text,
  source_page` (raw fields; extraction refines). `fmt` ∈ {jmih_book, asih_book,
  agenda}.

- [ ] **Step 1:** Save a real 2-3 page slice of JMIH 2016 as fixture; test that
  segmenting yields ≥2 blocks with a numeric `program_number`, a `title`, and
  non-empty `abstract_text`:
```python
from scripts.conf_abstracts import segment
def test_jmih_book_blocks():
    txt = open("tests/conf_abstracts/fixtures/jmih2016_p50.txt").read()
    blocks = segment.segment_blocks(txt, "jmih_book")
    assert len(blocks) >= 2
    b = blocks[0]
    assert b["program_number"].isdigit() and b["title"] and b["abstract_text"]
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement jmih_book (split on `^\d{3,4} .*(Session|Symposium|
  Talks)` headers + underscore-rule separators; author block = lines between
  header and title; title = first non-affiliation cap line; body = rest) and
  asih_book (underscore separator; `Surname, First;` author line; title; affil;
  body). Keep `agenda` as a thin wrapper over adapted Shark Network logic.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): abstract-book segmenter`.

---

### Task 6: Field extractor (rules + Ollama) and author parsing

**Files:**
- Create: `scripts/conf_abstracts/extract.py`, `scripts/conf_abstracts/llm.py`
- Test: `tests/conf_abstracts/test_extract.py`

**Interfaces:**
- Consumes: block dicts from `segment`.
- Produces: `extract.extract_fields(block, meeting, fmt) -> dict` populating
  abstracts columns + `authors` list [dict(full_name, position, is_presenter,
  presenter_inferred, affiliation, affiliation_country, raw_author_string)];
  `llm.ollama_json(prompt, schema) -> dict` (HTTP to localhost:11434, model
  qwen2.5:3b, format=json) and `llm.available() -> bool`.

- [ ] **Step 1:** Test rules author parsing (no LLM needed):
```python
from scripts.conf_abstracts import extract
def test_parse_authors_asih():
    a = extract.parse_authors("Armbruster, Jonathan; de Souza, Lesley; Lujan, Nathan")
    assert a[0]["full_name"] == "Jonathan Armbruster" and a[0]["position"]==1
    assert a[0]["is_presenter"] and a[0]["presenter_inferred"]
    assert len(a) == 3
def test_parse_authors_superscript():
    a = extract.parse_authors("Dana Bethea1, John Carlson1, Gregg Poulakis3")
    assert [x["full_name"] for x in a] == ["Dana Bethea","John Carlson","Gregg Poulakis"]
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `parse_authors` (handle both "Surname, First;" and
  "First Last<superscript>," forms; strip affiliation digits; first author =
  presenter with presenter_inferred=True), `llm.py` (Ollama HTTP wrapper,
  graceful `available()`), and `extract_fields` (rules for title/authors/
  abstract; call Ollama only to clean ambiguous blocks + infer society when
  `societies_explicit` empty; set confidence + needs_review).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): field + author extraction, ollama wrapper`.

---

### Task 7: Society resolution + elasmo tagging

**Files:**
- Create: `scripts/conf_abstracts/tag.py`
- Test: `tests/conf_abstracts/test_tag.py`

**Interfaces:**
- Produces: `tag.resolve(record, meeting) -> record` setting `society`,
  `society_basis`, `is_elasmo`, `elasmo_basis`.

- [ ] **Step 1:** Test resolution priority:
```python
from scripts.conf_abstracts.tag import resolve
def test_explicit_aes():
    r = resolve({"societies_explicit":["AES"],"society_inferred":None}, "JMIH")
    assert r["society"]=="AES" and r["society_basis"]=="session_prefix"
    assert r["is_elasmo"]==1 and r["elasmo_basis"]=="session_prefix"
def test_meeting_si():
    r = resolve({"societies_explicit":[],"society_inferred":None}, "SI")
    assert r["is_elasmo"]==1 and r["elasmo_basis"]=="meeting"
def test_content_inferred():
    r = resolve({"societies_explicit":[],"society_inferred":"AES","award":None}, "JMIH")
    assert r["society"]=="AES" and r["society_basis"]=="content" and r["is_elasmo"]==1
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement priority: explicit(prefix>award) → inferred; is_elasmo
  from society==AES or meeting∈{SI,EEA}; set both basis fields.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): society + elasmo tagging`.

---

### Task 8: Loader (insert + dedup)

**Files:**
- Create: `scripts/conf_abstracts/load.py`
- Test: `tests/conf_abstracts/test_load.py`

**Interfaces:**
- Produces: `load.upsert_meeting(con, meta) -> meeting_id`;
  `load.insert_abstract(con, meeting_id, record) -> abstract_id | None`
  (None if duplicate by (meeting_id, program_number) or (meeting_id, norm_title));
  inserts authors.

- [ ] **Step 1:** Test insert + dedup on an in-memory DB (uses schema.create_db).
```python
def test_insert_and_dedup(tmp_path):
    from scripts.conf_abstracts import schema, load
    con = schema.create_db(tmp_path/"t.db")
    mid = load.upsert_meeting(con, {"meeting":"JMIH","year":2016,"source_pdf":"x"})
    rec = {"program_number":"0974","title":"T","abstract_text":"body",
           "society":"AES","is_elasmo":1,"authors":[{"full_name":"A B","position":1}]}
    a1 = load.insert_abstract(con, mid, rec); a2 = load.insert_abstract(con, mid, rec)
    assert a1 and a2 is None
    assert con.execute("select count(*) from authors").fetchone()[0]==1
```
- [ ] **Step 2:** Run → FAIL.  **Step 3:** Implement.  **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): sqlite loader with dedup`.

---

### Task 9: Exporters (parquet / JSON / xlsx)

**Files:**
- Create: `scripts/conf_abstracts/export.py`
- Test: `tests/conf_abstracts/test_export.py`

**Interfaces:**
- Produces: `export.to_parquet_elasmo(con, path)` (elasmo subset, corpus-aligned
  columns), `export.to_json(con, path)` (nested authors), `export.to_xlsx(con,
  path)` (formatted, flags needs_review).

- [ ] **Step 1:** Test each exporter writes a non-empty file with expected
  columns/keys from a seeded DB (2 abstracts, 1 elasmo).
- [ ] **Step 2:** Run → FAIL.  **Step 3:** Implement (pandas read_sql → parquet;
  json.dump nested; openpyxl with freeze/bold/autofilter).  **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(conf-abstracts): parquet/json/xlsx exporters`.

---

### Task 10: Orchestrator + first real run

**Files:**
- Create: `scripts/conf_abstracts/run_pipeline.py`
- Test: manual/integration (run over 1 file, assert DB rows).

**Interfaces:**
- Produces: CLI `run_pipeline.py [--only GLOB] [--no-llm] [--reocr]` iterating
  PDFs: classify → ensure_ocr → segment → extract → tag → load; then export.

- [ ] **Step 1:** Implement orchestrator wiring the modules; per-file try/except
  logging parse_status; progress to `logs/conf_abstracts.log`.
- [ ] **Step 2:** Dry integration on ONE clean file (2016 JMIH abstract book,
  `--no-llm`): `./venv/bin/python -m scripts.conf_abstracts.run_pipeline --only "2016-JMIH-Abstract-Book*" --no-llm`
  → assert `abstracts` rows > 100, spot-check 3 records.
- [ ] **Step 3:** Start Ollama (`ollama serve` bg; `ollama pull qwen2.5:3b` if
  needed); re-run WITH llm on the same file; verify society_inferred populated
  for untagged posters.
- [ ] **Step 4:** Commit `feat(conf-abstracts): pipeline orchestrator + first run`.
- [ ] **Step 5:** Full run over all 53 PDFs as a background job + monitor; then
  export; QA counts per meeting.

---

## Self-Review

- **Spec coverage:** schema (T1), classify/doc_type (T2), QA+re-OCR gate incl.
  digitised PDFs (T3), society prefix+award+type (T4), segmentation of JMIH/ASIH/
  agenda (T5), rules+Ollama extraction + authors/presenter (T6), society
  inference + elasmo basis (T7), dedup load (T8), parquet(corpus-aligned)/JSON/
  xlsx (T9), orchestration + Fable-tail escalation + full run (T10). Fable
  escalation is invoked within T6/T10 for needs_review records (run when away).
- **Placeholders:** none — each task has real test + implementation direction.
- **Type consistency:** `society`/`societies_explicit`/`society_inferred`/
  `society_basis`/`is_elasmo`/`elasmo_basis` consistent across T4/T6/T7/T8/T9.

## Overnight execution note

Executor: run Tasks 1-9 inline (fast, TDD). Task 10 step 5 (full 53-PDF run +
LLM extraction of thousands of abstracts) is the long job — launch as a
background job with a Monitor, escalate needs_review to Fable while Simon is
away (resource window to ~2026-08-07, [[project_resource_window_aug2026]]).
