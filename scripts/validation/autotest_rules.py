"""Apply each proposed rule change to a copy of the rule set, re-extract the
sample, re-score vs Fable silver, keep only if silver-F1 improves without
regressing. Gold rules-vs-human F1 reported alongside as the overfit check.

`_extract_sample_column` is the correctness-critical wiring: it must
reproduce exactly what the real batch extractor (process_paper() in
extract_schema_columns.py) would compute for a single column, so that
accept/reject decisions made here generalise to a full re-run. See the
docstring below for the one nuance that had to be replicated by hand (the
synthetic TITLE section) to get exact (not approximate) agreement.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
IMPROVED = OUT / "improved_rules"
IMPROVED.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))


def evaluate_change(before_f1, after_f1, guard=0.0):
    return bool(after_f1 > before_f1 + guard)


def _extract_sample_column(rules_obj, column, sample_ids):
    """Run the extractor for one column over the sample with a patched rule
    set. Returns a long df (literature_id, column, value).

    Reuses the real extraction primitives directly, one compiled column
    built ONCE per call:
      - `current_rule()` (validation.propose_rules) resolves `column`'s rule
        dict out of the prefix-nested `rules_obj` structure.
      - `BinaryColumn` / `SchemaCategory` / `compile_schema()`
        (extract_schema_columns) turn that rule dict into a single
        `CompiledColumn` under a single-column `SchemaCategory` for the
        column's prefix.
      - `fable_extract._pdf_text()` resolves PDF body text per paper via the
        same (author-surname, year) + title-disambiguation path
        process_paper() uses.
      - `_match_column()` / `_label_sections()` (extract_schema_columns) do
        the actual section-weighted frequency matching; `.binary` is the
        fired flag.

    One deliberate addition beyond a literal read of those primitives:
    `fable_extract._pdf_text()` returns raw PDF body text only, but
    `process_paper()` prepends a synthetic "TITLE\\n<title>\\nOTHER\\n\\n"
    block before section-labelling so that title keywords count at the
    section weight of 2.0 (the highest weight, alongside KEYWORDS). Without
    replicating that prepend here, borderline papers whose evidence lives
    mostly in the title would score a lower weighted total_freq than the
    real pipeline and could cross the binary threshold differently.
    Replicating it gives EXACT (verified: 100/100%) agreement against the
    enriched parquet across the full 291-paper validation sample for
    eco_pelagic, d_movement, eco_coastal, d_biology (the prerequisite_terms
    path), gear_longline, and pr_bycatch -- see
    scripts/validation/tests/test_autotest_rules.py.
    """
    import extract_schema_columns as esc
    from validation.fable_extract import _get_paper_meta, _pdf_text
    from validation.propose_rules import current_rule

    prefix = column.split("_", 1)[0] + "_"
    rule = current_rule(rules_obj, column)
    bincol = esc.BinaryColumn(
        name=column,
        terms=list(rule.get("terms", [])),
        anchors=rule.get("anchors") or None,
        threshold=int(rule.get("threshold", 1)),
        case_sensitive_terms=set(rule.get("case_sensitive_terms", []) or []),
        prerequisite_terms=rule.get("prerequisite_terms", {}) or {},
    )
    compiled = esc.compile_schema(esc.SchemaCategory(prefix=prefix, columns=[bincol]))[0]

    meta = _get_paper_meta()
    rows = []
    for lit_id in sample_ids:
        text, _sha1 = _pdf_text(lit_id)
        if text is None:
            continue
        lit_norm = str(int(float(lit_id)))
        title = meta.loc[lit_norm, "title"] if lit_norm in meta.index else ""
        if title and text.strip():
            # Mirror process_paper()'s synthetic TITLE section (see docstring above).
            text = "TITLE\n" + str(title) + "\nOTHER\n\n" + text
        labelled_sections = esc._label_sections(text)
        mr = esc._match_column(text, compiled, schema_prefix=prefix, labelled_sections=labelled_sections)
        rows.append((lit_norm, column, int(mr.binary)))
    return pd.DataFrame(rows, columns=["literature_id", "column", "value"])


def _apply_proposal(rules_obj, p):
    """Mutate `rules_obj` in place per `p` (a row from rule_proposals.csv).

    `rules_obj` is prefix-nested (rules_obj[prefix][column]), matching
    docs/validate/assets/rules.json -- see current_rule() in
    validation.propose_rules for the same prefix derivation. Writing a flat
    rules_obj[column] key here would be invisible to current_rule() (and
    therefore to _extract_sample_column()), silently no-opping every
    "applied" change.
    """
    col = p["column"]
    prefix = col.split("_", 1)[0] + "_"
    r = rules_obj.setdefault(prefix, {}).setdefault(col, {})
    ct, detail = p["change_type"], str(p["detail"])
    if ct == "add_terms":
        r.setdefault("terms", []).extend(t.strip() for t in detail.split(",") if t.strip())
    elif ct == "remove_terms":
        drop = {t.strip() for t in detail.split(",")}
        r["terms"] = [t for t in r.get("terms", []) if t not in drop]
    elif ct == "threshold":
        try:
            r["threshold"] = float(detail)
        except ValueError:
            pass
    # 'anchor'/'review' left for human handling


def run():
    from validation.propose_rules import current_rule
    from validation.score import per_column_metrics

    proposals = pd.read_csv(OUT / "rule_proposals.csv")
    sample = pd.read_csv(OUT / "validation_sample.csv", dtype={"literature_id": str})
    fab = pd.read_parquet(OUT / "fable_labels.parquet").rename(columns={"present": "value"})
    fab["literature_id"] = fab["literature_id"].astype(str)
    gold = pd.read_csv(OUT / "gold_labels.csv", dtype={"literature_id": str}).rename(columns={"human_value": "value"})
    base_rules = json.loads((ROOT / "docs/validate/assets/rules.json").read_text())
    sample_ids = sample["literature_id"].tolist()
    gold_ids = set(gold.literature_id)

    log = []
    working = json.loads(json.dumps(base_rules))  # deep copy accumulator
    for _, p in proposals.iterrows():
        col = p["column"]
        if not current_rule(working, col):
            continue
        before = _extract_sample_column(working, col, sample_ids)
        f1_before = per_column_metrics(before, fab[fab.column == col][["literature_id", "column", "value"]]).f1.mean()
        trial = json.loads(json.dumps(working))
        _apply_proposal(trial, p)  # mutate trial[col] per change_type/detail
        after = _extract_sample_column(trial, col, sample_ids)
        f1_after = per_column_metrics(after, fab[fab.column == col][["literature_id", "column", "value"]]).f1.mean()
        gold_after = per_column_metrics(
            after[after.literature_id.isin(gold_ids)],
            gold[gold.column == col][["literature_id", "column", "value"]],
        ).f1.mean()
        accept = evaluate_change(f1_before, f1_after)
        if accept:
            working = trial
        log.append((col, p["change_type"], f1_before, f1_after, gold_after, accept))

    (IMPROVED / "rules.json").write_text(json.dumps(working, indent=2))
    pd.DataFrame(
        log, columns=["column", "change_type", "silver_f1_before", "silver_f1_after", "gold_f1_after", "accepted"]
    ).to_csv(OUT / "improvement_log.csv", index=False)


if __name__ == "__main__":
    run()
    print("wrote improved_rules/rules.json + improvement_log.csv")
