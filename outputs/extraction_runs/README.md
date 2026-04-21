# Extraction-run audit trail

Each full extraction run by `scripts/extract_schema_columns.py` writes a snapshot here under a unique run-id (`<timestamp>_<git-short-sha>[-dirty]`). Three files per run:

| File | Committed? | Purpose |
|---|---|---|
| `run_summary.json` | ✓ | Per-column firing counts, per-schema summary, rule + script fingerprints, git SHA, args. Small (~50 KB). |
| `rules_snapshot.json` | ✓ | Verbatim copy of `docs/validate/assets/rules.json` at run time so the rule state can be reproduced. ~70 KB. |
| `binary_classifications.parquet` | ✗ (gitignored) | Per-paper binary classifications for every column. Needed locally for `diff_extraction_runs.py` per-paper sampling. ~1–5 MB. |

## Comparing two runs

```bash
# List available runs
python scripts/diff_extraction_runs.py --list

# Diff the two most recent runs
python scripts/diff_extraction_runs.py --latest

# Diff specific runs, show top 30 changed columns + 10 paper samples per col
python scripts/diff_extraction_runs.py 20260420T180000_86dd0e87 20260421T040000_a8dec02a --top 30 --samples 10
```

The diff prints:

1. **Per-column firing-count delta** — which rules changed behaviour the most, sorted by absolute delta.
2. **Per-paper sample for each top-changed column** — specific literature_ids that gained or lost a positive classification (for spot-checking against the source PDFs).
3. **Per-schema summary** — papers-with-any-match per schema, run A vs run B.

## Audit / validation use

- The committed `run_summary.json` files give a versioned record of how aggregate firing counts evolve as we tune rules. Useful for trend analysis without needing the underlying parquet snapshots.
- The committed `rules_snapshot.json` files capture the exact rule state for each run so you can answer "what did rules.json look like when this run was made?" without checking out the corresponding git commit.
- For per-paper "did rule X correctly fire on paper Y?" questions, validators' submissions in PRs (`validation/<openalex_id>/<timestamp>` branches → `validations/*.json`) are the ground-truth reference. A future enhancement to `diff_extraction_runs.py` could cross-reference these against the per-paper deltas: for each validator-flagged "incorrect → correct" change, did the rule update produce the expected fix?

## Pruning old snapshots

Snapshots accumulate; the parquets are large. Prune locally with:

```bash
# Keep most recent 5 runs, delete older parquet snapshots (JSON summaries kept)
ls -1d outputs/extraction_runs/*/ | head -n -5 | xargs -I{} rm -f {}/binary_classifications.parquet
```

The `run_summary.json` and `rules_snapshot.json` are tiny and worth keeping indefinitely.
