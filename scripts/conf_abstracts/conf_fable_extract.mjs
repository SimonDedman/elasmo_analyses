export const meta = {
  name: 'conf-fable-extract',
  description: 'Fable structured extraction of conference abstract books — one Fable subagent per book fetches its whole-book text, extracts every abstract as JSON, and writes a cache file',
  phases: [{ title: 'Extract', detail: 'one Fable subagent per abstract book' }],
}

// ---------------------------------------------------------------------------
// Fable conference-abstract extraction (replaces the regex parsers, which hit a
// heuristic wall on the varied title/author/affiliation layouts). Each book is
// 34k-94k tokens — fits in a single Fable context — so ONE agent per book.
//
// The JS sandbox has no filesystem access, so each agent fetches its own book
// text from disk via conf_fable_fetch.py <index> and WRITES its own JSON cache
// file; the workflow returns only counts.
//
// args = { fetchScript: "/abs/.../conf_fable_fetch.py", indices: [0,1,...] }
// ---------------------------------------------------------------------------
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const fetchScript = A.fetchScript
const indices = A.indices || []

if (!fetchScript || indices.length === 0) {
  log('conf-fable-extract: missing fetchScript or empty indices — nothing to do')
  return { ok: 0, failed: 0 }
}

log(`extracting ${indices.length} abstract books`)
phase('Extract')

function promptFor(idx) {
  return (
`You are extracting structured records from ONE marine-science conference
abstract book for a systematic review database.

STEP 1 — Run this with the Bash tool to fetch your assignment:
  python3 "${fetchScript}" ${idx}
If the output begins with "ALREADY_DONE", reply exactly "OK done" and do NOTHING
else. Otherwise the output has a CACHE_PATH line, MEETING/YEAR/CITY/SOCIETY_HINT
lines, and the full book text between the "=== BOOK TEXT ===" and
"=== END BOOK TEXT ===" markers (extracted with pdftotext -layout, so columns
and line-wraps are preserved).

STEP 2 — Read the ENTIRE book text. Extract EVERY presentation — every oral
talk, poster, keynote, plenary, and lightning talk. A typical EEA book has
40-120 presentations across an oral section and a poster section; do not stop
early. For EACH presentation, build an object with these fields:
  "title": full title, line-wraps joined into one string, no trailing period
    unless it is genuinely part of the title.
  "authors": array, in listed order, of objects
    {"full_name": "A. B. Surname", "affiliation": "institution, city, country
    or null", "is_presenter": true/false}. The presenter is usually the first
    author, or one marked with an asterisk/underline/bold; set is_presenter
    true for exactly that one if identifiable, otherwise false for all.
  "presentation_type": one of "talk","poster","keynote","plenary","lightning"
    if stated or clearly inferable from the section heading (e.g. a "Posters"
    section -> "poster"); otherwise null.
  "abstract_text": the FULL body prose, line-wraps joined, hyphenated
    word-breaks repaired; null if this entry is only a schedule/programme line
    with no body paragraph.
  "keywords": array of keyword strings if a "Keywords:" line is present, else [].
  "session_name": the session/theme heading it appears under, or null.

RULES:
- Extract each presentation exactly ONCE. If the book has both a schedule/
  programme list AND a full abstracts section, use the abstracts section (with
  the body) and ignore the duplicate schedule line.
- Never merge two abstracts into one; never split one abstract into two.
- IGNORE non-abstract material: title pages, welcome notes, committee/organiser
  lists, sponsor/advert pages, table of contents, delegate/participant lists,
  maps, floor plans, and the conference programme grid.
- Preserve accented characters and species names exactly.

STEP 3 — Use the Write tool to write ONLY a JSON array of these objects (no
markdown fences, no commentary, valid JSON) to the CACHE_PATH from step 1.

STEP 4 — Reply with only: OK <number of abstracts written>
Do NOT paste the JSON back to me — the written file is the deliverable.`
  )
}

const results = await parallel(
  indices.map((idx) => () =>
    agent(promptFor(idx), {
      label: `fable-book:${idx}`,
      phase: 'Extract',
      agentType: 'general-purpose',
      model: 'fable',
      effort: 'medium',
    }).then((r) => ({ idx, ok: true, reply: r }))
      .catch((e) => ({ idx, ok: false, err: String(e) }))
  )
)

const ok = results.filter((r) => r && r.ok).length
const failed = indices.length - ok
for (const r of results) log(`  book ${r.idx}: ${r.ok ? 'ok — ' + (r.reply || '').slice(0, 40) : 'FAILED ' + r.err}`)
log(`done: ${ok} ok, ${failed} failed`)
return { ok, failed, indices }
