"""Dominant-basin columns (bd_*): a derived step AFTER the b_* basin flags, which stay untouched.

Rule: within a paper, keep a flagged basin only when its weighted score is at least DOMINANCE
times the score of the paper's top-scoring flagged basin. Scores are the production extractor's
own (total_freq in outputs/schema_extraction_evidence.csv), so nothing is re-counted.

Writes
  outputs/study_sites/dominant_basins.parquet       literature_id, bd_<basin> (1/0; missing where the
                                                    paper has no b_ extraction), bd_score_<basin>, bd_top_basin, bd_n
  outputs/study_sites/dominant_basins_coverage.json kept / lost / added against the b_ flags, by basin,
                                                    and the score against the model-read reference
  docs/schema_proposals/dominant_basins_rationale.md  the rationale, generated from the measured results
The corpus parquet is NOT modified.

  python3 scripts/study_sites/build_dominant_basins.py
Rerun check_basin_columns.py and basin_section_analysis.py first if the corpus or caches changed.
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import check_basin_columns as C  # noqa: E402

DOMINANCE = 0.33  # MEASURED 2026-11-11 (basin_section_analysis.py section 5): see the rationale document
EVID = ROOT / "outputs/schema_extraction_evidence.csv"
OUTD = ROOT / "outputs/study_sites"
DOC = ROOT / "docs/schema_proposals/dominant_basins_rationale.md"


def pct(k, n):
    return f"{k / n:.0%}" if n else "n/a"


def build():
    names = pq.ParquetFile(C.PARQUET).schema.names
    bcols = [n for n in names if n.startswith("b_")]
    d = pd.read_parquet(C.PARQUET, columns=["literature_id"] + bcols)
    d["literature_id"] = d["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    n_dup = int(d["literature_id"].duplicated().sum())
    d = d.drop_duplicates("literature_id").set_index("literature_id")
    e = pd.read_csv(EVID, usecols=["literature_id", "column", "binary", "total_freq"], dtype={"literature_id": str}, low_memory=False)
    e = e[e["column"].isin(bcols)]
    score = e.groupby(["literature_id", "column"])["total_freq"].max().unstack()  # max over the few duplicated evidence rows
    score = score.reindex(index=d.index, columns=bcols)
    flag = d[bcols].fillna(0).astype(float) > 0
    extracted = d[bcols].notna().any(axis=1)  # zero and missing kept apart: bd_ is missing where b_ was never extracted
    missing_score = int((flag & score.isna()).sum().sum())
    if missing_score:
        raise SystemExit(f"FAIL: {missing_score} b_ flags have no evidence score; rebuild the evidence file before deriving bd_")
    s = score.where(flag)
    top = s.max(axis=1)
    keep = flag & s.ge(DOMINANCE * top, axis=0)
    out = pd.DataFrame(index=d.index)
    for c in bcols:
        b = c[2:]
        out[f"bd_{b}"] = keep[c].astype("Int8").where(extracted)
        out[f"bd_score_{b}"] = s[c]
    out["bd_top_basin"] = s.idxmax(axis=1, skipna=True).where(flag.any(axis=1)).str[2:]
    out["bd_n"] = keep.sum(axis=1).astype("Int8").where(extracted)
    out = out.reset_index()
    tmp = OUTD / "dominant_basins.parquet.tmp"
    out.to_parquet(tmp, index=False)
    tmp.replace(OUTD / "dominant_basins.parquet")
    back = pd.read_parquet(OUTD / "dominant_basins.parquet")
    assert len(back) == len(d), "row count changed on write"

    by = {}
    for c in bcols:
        by[c[2:]] = {"b_flags": int(flag[c].sum()), "kept": int(keep[c].sum()), "lost": int((flag[c] & ~keep[c]).sum()),
                     "added": int((keep[c] & ~flag[c]).sum())}
    papers_flag = int(flag.any(axis=1).sum())
    cov = {"built": time.strftime("%Y-%m-%d"), "dominance": DOMINANCE, "corpus_records": len(d), "duplicate_ids_dropped": n_dup,
           "papers_with_b_extraction": int(extracted.sum()), "papers_with_any_b_flag": papers_flag,
           "papers_with_any_bd_flag": int(keep.any(axis=1).sum()),
           "papers_losing_at_least_one_basin": int(((flag & ~keep).any(axis=1)).sum()),
           "flags": {"b": int(flag.sum().sum()), "kept": int(keep.sum().sum()), "lost": int((flag & ~keep).sum().sum()),
                     "added": int((keep & ~flag).sum().sum())},
           "mean_basins_per_flagged_paper": {"b": round(float(flag.sum(axis=1)[flag.any(axis=1)].mean()), 2),
                                             "bd": round(float(keep.sum(axis=1)[keep.any(axis=1)].mean()), 2)},
           "by_basin": by}
    if cov["flags"]["added"] or cov["papers_with_any_bd_flag"] != papers_flag:
        raise SystemExit("FAIL: the dominance step added a flag or emptied a paper; it may only remove non-top basins")

    # score both column sets against the model-read reference, through the delivered file
    ml = C.model_locations()
    bd = back.set_index("literature_id")
    k = {"b": Counter(), "bd": Counter()}
    for lit, (cs, region) in ml.items():
        strength, acc = C.reference(cs, region)
        if strength != "strong" or lit not in d.index:
            continue
        sets = {"b": {c[2:] for c in bcols if flag.at[lit, c]}, "bd": {c[2:] for c in bcols if not pd.isna(bd.at[lit, f"bd_{c[2:]}"]) and bd.at[lit, f"bd_{c[2:]}"] == 1}}
        for name, fl in sets.items():
            k[name]["ref"] += 1
            if fl:
                k[name]["flagged"] += 1
                k[name]["has_right"] += bool(fl & acc)
                k[name]["has_wrong"] += bool(fl - acc)
                k[name]["clean"] += not (fl - acc)
    cov["against_model_read_reference"] = {n: dict(v) for n, v in k.items()}
    (OUTD / "dominant_basins_coverage.json").write_text(json.dumps(cov, indent=1))
    return cov


def rationale(cov):
    chk = json.loads((OUTD / "basin_column_check.json").read_text())
    ana = json.loads((OUTD / "basin_section_analysis.json").read_text())
    fam = chk["families"]

    def famrow(label, key):
        f = fam[key]
        return f"| {label} | {pct(f['flagged'], f['ref'])} | {pct(f['has_right'], f['flagged'])} | {pct(f['has_wrong'], f['flagged'])} | {f['flagged']:,} of {f['ref']:,} |"

    fo = ana["flag_origin"]
    r, w = fo["right"], fo["wrong"]

    def forow(label, key):
        return f"| {label} | {pct(r[key], r['n'])} | {pct(w[key], w['n'])} |"

    def varrow(label, key):
        v = ana["variants"][key]["test"]
        return f"| {label} | {pct(v['flagged'], v['ref'])} | {pct(v['has_right'], v['flagged'])} | {pct(v['has_wrong'], v['flagged'])} |"

    mb = ana["multi_basin"]

    def mbrow(label, key):
        v = mb["rules"][key]
        return (f"| {label} | {pct(v['groups_found'], v['groups'])} | {pct(v['all_found'], mb['n_multi'])} | "
                f"{pct(v['single_found'], mb['n_single'])} | {pct(v['wrong'], v['flagged'])} |")

    g = ana["geo_study_ocean_basin"]
    ref = cov["against_model_read_reference"]
    sbt = chk["sub_basins_total"]
    same, total = ana["control_recount_equals_stored"]
    nvt = ana["variants"]["V0 current rule"]["test"]["ref"]
    basin_rows = "\n".join(
        f"| {b.replace('_', ' ').title()} | {v['b_flags']:,} | {v['kept']:,} | {v['lost']:,} | {pct(v['lost'], v['b_flags'])} | {v['added']} |"
        for b, v in sorted(cov["by_basin"].items(), key=lambda kv: -kv[1]["lost"] / max(kv[1]["b_flags"], 1)))
    dropped = ", ".join(f'"{t}" ({b.replace("_", " ")})' for b, t in ana["dropped_terms"])
    f = cov["flags"]
    return f"""# Dominant-basin columns (`bd_*`): rationale and evidence

**Built:** {cov['built']}. This file is generated by `scripts/study_sites/build_dominant_basins.py` from the
measured results; edit the builder, not this file.
**Decision (Simon, 12 Nov 2026):** add dominant-basin columns as a derived step after the `b_*` basin
flags, with the dominance threshold at {DOMINANCE}. The `b_*` columns and the extractor are unchanged.

## What the columns are

For each paper, a flagged basin is kept only when its weighted mention score is at least
{DOMINANCE} times the score of that paper's top-scoring flagged basin. A paper that mentions the
Mediterranean twice and the North Sea thirty times keeps only the North Sea. The scores are the
extractor's own (`total_freq` in `outputs/schema_extraction_evidence.csv`), so nothing is re-counted.

- Table: `outputs/study_sites/dominant_basins.parquet`, one row per corpus record: `bd_<basin>` (1 or
  0; missing where the paper has no `b_*` extraction), `bd_score_<basin>`, `bd_top_basin`, `bd_n`.
- The corpus parquet is not modified. Join on `literature_id`.
- Read `b_*` as "the paper mentions this basin" and `bd_*` as "the paper is mainly about this basin".

## Why: how the existing basin columns perform

The reference is the sea or ocean a language model read from each paper's full text (Fable corpus
caches and the study-site pilot), mapped to the nine basins by a keyword table
(`scripts/study_sites/check_basin_columns.py`). {fam['b_|strong']['ref']:,} papers have such a reference.

| Column | Flags something | Includes a right basin | Also flags a wrong basin | Papers flagged |
|---|---|---|---|---|
{famrow('`ob_*` (title, abstract, Shark-References place keywords)', 'ob_|strong')}
{famrow('`b_*` (keyword mentions in the full text)', 'b_|strong')}
{famrow('`geo_study_ocean_basin`', 'geo_study_ocean_basin|strong')}

- `ob_*` is precise and sparse because it reads only the title, abstract, and place keywords.
- `b_*` finds the right basin and then adds others, because any mention in the paper counts.
- `geo_study_ocean_basin` returns the first basin whose keyword appears, checks North Atlantic first,
  and lists "atlantic ocean", "caribbean", and "mediterranean" under North Atlantic. Its North Atlantic
  values were {g.get('North Atlantic|right', 0)} right and {g.get('North Atlantic|wrong', 0)} wrong. No tweak rescues it; do not use it.
- Sub-basins (`sb_*`): where the model names a sea, the column flags it in {sbt['named_and_flagged']:,} of
  {sbt['named_by_model']:,} cases ({pct(sbt['named_and_flagged'], sbt['named_by_model'])}); {pct(sbt['parent_outside_ref'], sbt['flagged_with_ref'])} of its flags sit in a basin outside the reference.

## Where right and wrong `b_*` flags come from

Every basin term was re-counted per labelled section with the extractor's own patterns
(`scripts/study_sites/basin_section_analysis.py`). The re-count reproduces the stored flags in {same:,} of
{total:,} papers. {r['n']:,} flags were right and {w['n']:,} wrong.

| Where the basin is mentioned | Right flags | Wrong flags |
|---|---|---|
{forow('In the title or keywords', 'in_title_or_keywords')}
{forow('Nowhere in title, keywords, abstract, or methods', 'none_in_title_keywords_abstract_methods')}
{forow('In the introduction only', 'only_intro')}
{forow('Paper has no detected methods heading', 'no_methods_header_found')}

Wrong flags come disproportionately from passing mentions in the introduction and discussion. The
extractor weights the introduction the same as the methods (1.0 each), and Mediterranean and Southern
Ocean fire on a single mention where the other basins need two. Terms behind more wrong flags than
right ones on the tuning half: {dropped}.

## Rule changes that were simulated

Scored on a held-out half of the reference papers ({nvt:,} papers); the dropped terms were chosen on
the other half.

| Rule | Papers flagged | Includes a right basin | Also flags a wrong basin |
|---|---|---|---|
{varrow('Current', 'V0 current rule')}
{varrow('Introduction weight 1 to 0.25', 'V1 introduction weight 1 -> 0.25')}
{varrow('Introduction, discussion, and conclusions at 0.25', 'V2 intro, discussion, conclusions 0.25')}
{varrow('Threshold 2 for Mediterranean and Southern Ocean', 'V3 threshold 2 for Mediterranean and Southern Ocean')}
{varrow('Drop the terms listed above', 'V4 drop dev-chosen terms')}
{varrow('Title, keywords, abstract, and methods only', 'V6 title, keywords, abstract, methods only')}
{varrow('Dominance at 0.5', 'V5 dominance: keep basins scoring >= half the top basin')}
{varrow('Weights, thresholds, and dropped terms together', 'V8 = V2 + V3 + V4')}
{varrow('That package plus dominance at 0.5', 'V9 = V8 + dominance')}

Dominance was the largest single lever and the only one that removed wrong basins without reducing
the number of papers flagged.

## What dominance costs studies in more than one basin

{mb['n_multi']} of the reference papers name two or more different basins; {mb['n_single']:,} name one. Scored on all of them.

| Rule | Multi-basin: basins found | Multi-basin: all basins found | Single-basin: basin found | Papers with a wrong basin |
|---|---|---|---|---|
{mbrow('Current', 'current')}
{mbrow('Dominance at 0.2', 'dominance 0.2')}
{mbrow('Dominance at 0.25', 'dominance 0.25')}
{mbrow('**Dominance at 0.33 (chosen)**', 'dominance 0.33')}
{mbrow('Dominance at 0.5', 'dominance 0.5')}
{mbrow('Weights, thresholds, and dropped terms (no dominance)', 'V8 weights + thresholds + dropped terms')}
{mbrow('That package plus dominance at 0.33', 'V8 + dominance 0.33')}
{mbrow('That package plus dominance at 0.5', 'V8 + dominance 0.5')}

Reasons for the choice:

1. Dominance leaves single-basin papers almost untouched at every threshold, while the share of
   papers carrying a wrong basin falls steeply.
2. The cost falls on multi-basin papers, which are {pct(mb['n_multi'], mb['n_multi'] + mb['n_single'])} of the reference set. At 0.33 they lose
   a few points of basin recall; at 0.5 the loss roughly doubles.
3. The weight, threshold, and dropped-term package was rejected: it lowers single-basin recall, which
   dominance alone does not.
4. The rule is applied as a new derived step, so `b_*` and everything built on it are unchanged and
   the step can be dropped or re-thresholded without a re-extraction.

## What the step did to the corpus

| | Count |
|---|---|
| Corpus records | {cov['corpus_records']:,} |
| Papers with a `b_*` extraction | {cov['papers_with_b_extraction']:,} |
| Papers with at least one basin flag (same before and after) | {cov['papers_with_any_b_flag']:,} |
| Papers that lost at least one basin | {cov['papers_losing_at_least_one_basin']:,} |
| Basin flags before | {f['b']:,} |
| Kept | {f['kept']:,} |
| Lost | {f['lost']:,} |
| Added | {f['added']} |
| Mean basins per flagged paper, before and after | {cov['mean_basins_per_flagged_paper']['b']} and {cov['mean_basins_per_flagged_paper']['bd']} |

| Basin | `b_*` flags | Kept | Lost | Share lost | Added |
|---|---|---|---|---|---|
{basin_rows}

Scored through the delivered table against the same reference ({ref['b']['ref']:,} papers):

| Columns | Papers flagged | Includes a right basin | Also flags a wrong basin | All flags right |
|---|---|---|---|---|
| `b_*` | {pct(ref['b']['flagged'], ref['b']['ref'])} | {pct(ref['b']['has_right'], ref['b']['flagged'])} | {pct(ref['b']['has_wrong'], ref['b']['flagged'])} | {pct(ref['b']['clean'], ref['b']['flagged'])} |
| `bd_*` | {pct(ref['bd']['flagged'], ref['bd']['ref'])} | {pct(ref['bd']['has_right'], ref['bd']['flagged'])} | {pct(ref['bd']['has_wrong'], ref['bd']['flagged'])} | {pct(ref['bd']['clean'], ref['bd']['flagged'])} |

## Limits

- The reference is a model's reading of the study region, mapped to basins by a keyword table, and
  was not checked by hand. A hand read of 14 "wrong basin" cases found about 10 real errors, 2 gaps in
  the reference, and 2 ambiguous global studies, so the wrong-basin rates above are somewhat
  overstated for both column sets.
- The reference papers are those a model has read so far, which are mostly recent.
- Dominance does not raise recall: `b_*` finds the study basin in about two thirds of single-basin
  papers, and `bd_*` inherits that. For a basin map, the model-read region is the better source
  where it exists.
- A paper flagged for a single basin is unchanged by this step, right or wrong.

## Regenerate

```
python3 scripts/study_sites/check_basin_columns.py
python3 scripts/study_sites/basin_section_analysis.py
python3 scripts/study_sites/build_dominant_basins.py
```
"""


def main():
    cov = build()
    DOC.write_text(rationale(cov))
    f = cov["flags"]
    print(f"OK bd_* built at dominance {DOMINANCE}: flags {f['b']:,} -> kept {f['kept']:,}, lost {f['lost']:,}, added {f['added']}")
    print(f"   papers with a basin flag {cov['papers_with_any_b_flag']:,} (unchanged), papers losing a basin {cov['papers_losing_at_least_one_basin']:,}")
    for n, v in cov["against_model_read_reference"].items():
        print(f"   {n:3s} vs reference: flagged {pct(v['flagged'], v['ref'])}, has right {pct(v['has_right'], v['flagged'])}, has wrong {pct(v['has_wrong'], v['flagged'])}")
    print(f"wrote {OUTD / 'dominant_basins.parquet'}\nwrote {OUTD / 'dominant_basins_coverage.json'}\nwrote {DOC}")
    print("next: join bd_* on literature_id where a study basin is needed; the corpus parquet is unchanged")


if __name__ == "__main__":
    main()
