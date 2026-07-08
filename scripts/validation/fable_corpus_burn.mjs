export const meta = {
  name: 'fable-corpus-burn',
  description: 'Fable structured extraction over one shard of the PDF corpus (166 schema cols + study geography); each subagent writes a present-only cache file',
  phases: [{ title: 'Extract', detail: 'one Fable subagent per paper' }],
}

// ---------------------------------------------------------------------------
// STAGE 2 of the corpus Fable extraction (see
// docs/superpowers/specs/2026-07-07-fable-corpus-extraction-design.md).
//
// args = {
//   shard:      [{lit_id, text_path, sha}, ...]   // <=900 papers (agent cap)
//   cacheDir:   "/abs/path/outputs/validation/.fable_corpus_cache"
//   defs:       [{name, description}, ...]         // the 166 schema columns
//   shardIndex: 0, totalShards: N                  // for logging only
// }
//
// Each subagent runs on Fable (opts.model:'fable' — burns the Fable allowance
// regardless of the orchestrator's session model), reads its paper text, and
// WRITES its own present-only cache file. The workflow returns only counts, so
// the orchestrator context never sees the label payload.
// ---------------------------------------------------------------------------

const shard = args.shard || []
const cacheDir = args.cacheDir
const defs = args.defs || []
const shardIndex = args.shardIndex ?? 0
const totalShards = args.totalShards ?? 1

if (!cacheDir || shard.length === 0) {
  log('fable-corpus-burn: empty shard or missing cacheDir — nothing to do')
  return { ok: 0, failed: 0, shardIndex }
}

// Column reference block, embedded once per agent prompt.
const defsText = defs.map(d => `- ${d.name}: ${d.description}`).join('\n')

log(`shard ${shardIndex + 1}/${totalShards}: ${shard.length} papers`)
phase('Extract')

function promptFor(item) {
  const cachePath = `${cacheDir}/${item.sha}.txt`
  return (
`You are auditing ONE shark-research paper for a systematic review. The full ` +
`paper text is in a file. Your job: decide which schema columns the paper's OWN ` +
`STUDY supports (NOT its references, background, or literature review), extract ` +
`where the study was conducted, and SAVE the result to a cache file.

STEP 1 — Read the entire paper text at:
  ${item.text_path}
(It may be long; make sure you read all of it, using offset/limit if the first ` +
`read truncates.)

STEP 2 — For EACH column in the list below, decide if the paper's own study ` +
`provides evidence for it. Include a column ONLY if present (true). A column is ` +
`present only if the study itself did/used/covered it — not merely cited it.

COLUMNS (name: what counts as evidence):
${defsText}

STEP 3 — Identify the geography of the STUDY itself:
  study_country: the country/countries where the study was conducted (data ` +
`collected / animals sampled). One or more; empty if the paper is purely ` +
`theoretical/review with no field location.
  study_region: a finer location if clearly stated (sea, gulf, reef, site, EEZ). ` +
`Leave blank if none.

STEP 4 — Use the Write tool to save EXACTLY this plain-text format to:
  ${cachePath}

Format (one header block, then one line PER PRESENT COLUMN only):
LIT: ${item.lit_id}
COUNTRY: <country1>; <country2>
REGION: <region or leave empty>
<column_name>|<confidence 0.0-1.0>|<evidence, <=80 chars, NO pipe or newline>
<column_name>|<confidence>|<evidence>
...

Rules for the file:
- List ONLY present columns (one per line). Omit absent columns entirely.
- Use exact column names from the list above.
- Evidence: a short phrase from the paper's own study; <=80 chars; never contains ` +
`'|' or a newline. If unsure of wording, give a terse paraphrase.
- If NO columns are present, still write the LIT/COUNTRY/REGION header lines ` +
`(this records that the paper was processed).

STEP 5 — After writing the file, reply with just: OK ${item.lit_id}

Do not return the column data to me — the written file is the deliverable.`
  )
}

const results = await parallel(
  shard.map((item) => () =>
    agent(promptFor(item), {
      label: `fable:${item.lit_id}`,
      phase: 'Extract',
      model: 'fable',
      effort: 'medium',
    }).then((r) => ({ lit_id: item.lit_id, ok: true }))
      .catch(() => ({ lit_id: item.lit_id, ok: false }))
  )
)

const ok = results.filter((r) => r && r.ok).length
const failed = shard.length - ok
log(`shard ${shardIndex + 1}/${totalShards} done: ${ok} ok, ${failed} failed/null`)
return { ok, failed, shardIndex, total: shard.length }
