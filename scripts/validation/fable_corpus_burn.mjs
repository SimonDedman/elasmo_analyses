export const meta = {
  name: 'fable-corpus-burn',
  description: 'Fable structured extraction over one shard of the PDF corpus (166 schema cols + study geography); each Fable subagent fetches its paper, classifies, and writes a present-only cache file',
  phases: [{ title: 'Extract', detail: 'one Fable subagent per paper' }],
}

// ---------------------------------------------------------------------------
// STAGE 2 of the corpus Fable extraction (see
// docs/superpowers/specs/2026-07-07-fable-corpus-extraction-design.md).
//
// The JS sandbox has NO filesystem access and args must be a literal value in
// the launch call, so per-paper data is NOT passed in args. Instead each agent
// fetches its own assignment from disk via a tested Python helper
// (fable_agent_fetch.py <index>), which prints the cache path + 166 column defs
// + full paper text in one blob. The agent then classifies and WRITES its own
// present-only cache file; the workflow returns only counts.
//
// args = {
//   fetchScript: "/abs/.../scripts/validation/fable_agent_fetch.py",
//   startIndex:  0,          // first worklist index in this shard
//   count:       900,        // papers in this shard (<=900; agent cap is 1000)
//   shardIndex:  0, totalShards: 23   // logging only
// }
// ---------------------------------------------------------------------------

// args may arrive as a JS object OR as a JSON-encoded string depending on how
// the launch call was serialised — handle both.
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const fetchScript = A.fetchScript
const startIndex = A.startIndex ?? 0
const count = A.count ?? 0
const shardIndex = A.shardIndex ?? 0
const totalShards = A.totalShards ?? 1

if (!fetchScript || count <= 0) {
  log('fable-corpus-burn: missing fetchScript or count<=0 — nothing to do')
  return { ok: 0, failed: 0, shardIndex }
}

log(`shard ${shardIndex + 1}/${totalShards}: papers ${startIndex}..${startIndex + count - 1}`)
phase('Extract')

function promptFor(idx) {
  return (
`You are auditing ONE shark-research paper for a systematic review.

STEP 1 — Run this command with the Bash tool to fetch your assignment:
  python3 "${fetchScript}" ${idx}
If the output begins with "ALREADY_DONE", this paper is already processed —
reply exactly "OK done" and do NOTHING else (no reading, no writing).
Otherwise the output contains: a CACHE_PATH line, a LIT line (the paper's id), a
list of COLUMNS (name: what counts as evidence), and the full PAPER TEXT between
the "=== PAPER TEXT ===" and "=== END PAPER TEXT ===" markers.

STEP 2 — Read the whole paper text. For EACH column, decide whether the paper's
OWN STUDY provides evidence for it — NOT its references, background, or
literature review. A column is present ONLY if the study itself did/used/covered
it. Most columns will be absent for any given paper.

STEP 3 — Identify the geography of the STUDY itself:
  study_country: the country/countries where the study was conducted (data
    collected / animals sampled). One or more; empty if purely theoretical/review.
  study_region: a finer location if clearly stated (sea, gulf, reef, site, EEZ);
    empty if none.

STEP 4 — Use the Write tool to save EXACTLY this plain-text format to the
CACHE_PATH from step 1 (one header block, then ONE line per PRESENT column only):

LIT: <the LIT value>
COUNTRY: <country1>; <country2>
REGION: <region or leave empty after the colon>
<column_name>|<confidence 0.0-1.0>|<evidence, <=80 chars, NO '|' and NO newline>
<column_name>|<confidence>|<evidence>
...

Rules:
- List ONLY present columns, one per line; omit every absent column.
- Use exact column names from the COLUMNS list.
- Evidence: short phrase from the paper's own study; <=80 chars; never contains
  '|' or a newline. Terse paraphrase is fine.
- If NO columns are present, still write the LIT/COUNTRY/REGION header lines so
  the paper is recorded as processed.

STEP 5 — Reply with only: OK <the LIT value>
Do NOT return the column data to me — the written file is the deliverable.`
  )
}

const idxs = Array.from({ length: count }, (_, k) => startIndex + k)

const results = await parallel(
  idxs.map((idx) => () =>
    agent(promptFor(idx), {
      label: `fable:${idx}`,
      phase: 'Extract',
      agentType: 'general-purpose',
      model: 'fable',
      effort: 'medium',
    }).then(() => ({ idx, ok: true }))
      .catch(() => ({ idx, ok: false }))
  )
)

const ok = results.filter((r) => r && r.ok).length
const failed = count - ok
log(`shard ${shardIndex + 1}/${totalShards} done: ${ok} ok, ${failed} failed/null`)
return { ok, failed, shardIndex, count, startIndex }
