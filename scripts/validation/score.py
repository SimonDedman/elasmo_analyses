"""Score rules vs human (gold) and rules vs Fable (silver); build the A/B
viability memo with a 40k-corpus token-cost extrapolation."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
# Fable pricing snapshot (USD per 1M tokens) — update from claude-api skill before quoting.
PRICE_IN, PRICE_OUT = 1.00, 5.00


def per_column_metrics(rules_df, ref_df) -> pd.DataFrame:
    """Inner-merge rules and reference labels on (literature_id, column) and
    compute confusion-matrix counts + precision/recall/f1 per column.

    NOTE: this is an inner merge — any (literature_id, column) pair present
    in only one of the two frames (e.g. a gold column with no matching rules
    column) silently contributes zero rows here. Use missing_rule_columns()
    to surface that gap before trusting these metrics as full coverage.

    Both inputs are defensively de-duplicated on (literature_id, column)
    before the merge: duplicate literature_id rows in the source parquet
    (63 in the current snapshot) would otherwise melt into duplicate long
    rows and double-weight that paper's contribution to tp/fp/fn/tn.
    """
    rules_df = rules_df.drop_duplicates(subset=["literature_id", "column"])
    ref_df = ref_df.drop_duplicates(subset=["literature_id", "column"])
    m = rules_df.merge(ref_df, on=["literature_id", "column"], suffixes=("_r", "_ref"))
    out = []
    for col, g in m.groupby("column"):
        tp = int(((g.value_r == 1) & (g.value_ref == 1)).sum())
        fp = int(((g.value_r == 1) & (g.value_ref == 0)).sum())
        fn = int(((g.value_r == 0) & (g.value_ref == 1)).sum())
        tn = int(((g.value_r == 0) & (g.value_ref == 0)).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        if pd.notna(prec) and pd.notna(rec):
            # prec/rec are both legitimately defined (there was support for
            # at least one of them). 0.0 is a real value here, not "no
            # signal" -- a fully-wrong column (prec=rec=0.0) must score
            # F1=0.0, not NaN (NaN would vanish from f1.mean() and inflate
            # macro-F1 by silently dropping the worst columns).
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        else:
            # genuinely undefined: no support at all (tp=fp=fn=0, 0/0).
            f1 = float("nan")
        out.append((col, tp, fp, fn, tn, prec, rec, f1))
    return pd.DataFrame(out, columns=["column", "tp", "fp", "fn", "tn", "precision", "recall", "f1"])


def missing_rule_columns(ref_df: pd.DataFrame, available_columns) -> dict:
    """Return {column: row_count} for every column in ref_df["column"] that
    has no counterpart in available_columns.

    `available_columns` must be the set of columns actually available in
    the merge that per_column_metrics() will perform -- i.e. the `rules`
    frame's column set (itself already restricted to Fable's label-set
    intersected with the parquet's columns), NOT the full parquet column
    universe. A gold column can exist in the parquet while never appearing
    in Fable's label set (and thus never in `rules`); checking against the
    full parquet would wrongly report "no gap" for that column.

    These are the (literature_id, column) pairs that would silently vanish
    from per_column_metrics() under its inner merge — most notably gold
    labels using an `ob_` ocean-basin prefix that the rules source does not
    have (it has `b_` basin columns instead; no ob_ -> b_ remap is
    attempted here, this only surfaces the gap).
    """
    available = set(available_columns)
    counts = ref_df["column"].value_counts()
    return {col: int(n) for col, n in counts.items() if col not in available}


def _rules_long(sample_ids, columns):
    df = pd.read_parquet(ROOT / "outputs/literature_review_enriched.parquet")
    # 63 literature_ids have duplicate rows in the parquet; drop them here,
    # before melting, so a paper doesn't get double-weighted downstream.
    df = df.drop_duplicates(subset="literature_id")
    df["literature_id"] = df["literature_id"].apply(lambda v: str(int(float(v))))
    df = df[df["literature_id"].isin(sample_ids)]
    keep = [c for c in columns if c in df.columns]
    long = df.melt(id_vars=["literature_id"], value_vars=keep, var_name="column", value_name="value")
    long["value"] = (long["value"].fillna(0).astype(float) > 0).astype(int)
    return long


def run():
    gold = pd.read_csv(OUT / "gold_labels.csv", dtype={"literature_id": str}).rename(columns={"human_value": "value"})
    fab = pd.read_parquet(OUT / "fable_labels.parquet").rename(columns={"present": "value"})
    fab["literature_id"] = fab["literature_id"].astype(str)
    cols = sorted(fab["column"].unique())
    rules = _rules_long(set(gold.literature_id) | set(fab.literature_id), cols)

    # Coverage-gap accounting: report gold (literature_id, column) pairs with
    # no matching rules column at all (e.g. ob_ prefixed basin columns), so
    # the inner merge in per_column_metrics() doesn't silently drop them.
    # IMPORTANT: check against the columns actually present in `rules`
    # (Fable's label set intersected with the parquet's columns) -- NOT the
    # full parquet column set. The merge below only ever sees `rules`'
    # columns, so checking against the whole parquet can hide a real gap
    # (a gold column absent from Fable's label set but present elsewhere in
    # the parquet).
    available_columns = set(rules["column"].unique())
    gap = missing_rule_columns(gold, available_columns)
    if gap:
        print(f"[score] {sum(gap.values())} gold rows across {len(gap)} column(s) "
              f"have NO matching rules column and are excluded from gold metrics:")
        for col, n in sorted(gap.items(), key=lambda kv: -kv[1]):
            print(f"  - {col}: {n} row(s)")
    else:
        print("[score] no coverage gap: every gold column has a matching rules column.")

    gold_ids = set(gold.literature_id)
    m_gold = per_column_metrics(rules[rules.literature_id.isin(gold_ids)][["literature_id", "column", "value"]],
                                gold[["literature_id", "column", "value"]])
    m_silver = per_column_metrics(rules[["literature_id", "column", "value"]],
                                  fab[["literature_id", "column", "value"]])
    m_gold["set"] = "gold_rules_vs_human"; m_silver["set"] = "silver_rules_vs_fable"
    metrics = pd.concat([m_gold, m_silver], ignore_index=True)
    metrics.to_parquet(OUT / "metrics.parquet")

    # bridge: fable vs human on gold
    bridge = per_column_metrics(fab[fab.literature_id.isin(gold_ids)][["literature_id", "column", "value"]],
                                gold[["literature_id", "column", "value"]])
    # cost extrapolation. Use the input_tokens>0 subset for the mean (cache
    # hits log 0 tokens and would bias the mean down), but report the
    # Fable-labelled paper count separately from the full fab frame --
    # tok.shape[0] after the >0 filter undercounts papers whose tokens were
    # logged as 0 on a cache hit.
    n_fable_papers = fab["literature_id"].nunique()
    tok = pd.read_csv(OUT / "fable_token_log.csv")
    tok = tok[tok.input_tokens > 0]
    n_pdfs_target = 40000
    mean_in, mean_out = tok.input_tokens.mean(), tok.output_tokens.mean()
    cost40k = n_pdfs_target * (mean_in / 1e6 * PRICE_IN + mean_out / 1e6 * PRICE_OUT)
    lines = [
        "# LLM extraction A/B viability", "",
        f"- Papers Fable-labelled: {n_fable_papers}",
        f"- Mean tokens/paper: {mean_in:.0f} in / {mean_out:.0f} out",
        f"- Fable-vs-human agreement (gold, macro-F1): {bridge.f1.mean():.3f}",
        f"- Rules-vs-human (gold, macro-F1): {m_gold.f1.mean():.3f}",
        f"- Rules-vs-Fable (silver, macro-F1): {m_silver.f1.mean():.3f}",
        f"- **Extrapolated Fable cost for {n_pdfs_target:,} PDFs: ${cost40k:,.0f}** "
        f"(at ${PRICE_IN}/{PRICE_OUT} per 1M in/out; excludes OCR + retries; verify pricing via claude-api skill).",
        "",
        "## Coverage gap (gold columns with no matching rules column)",
        "",
    ]
    if gap:
        lines.append(f"{sum(gap.values())} gold rows across {len(gap)} column(s) excluded from "
                      f"gold-set metrics (inner merge drops unmatched columns):")
        lines += [f"- `{col}`: {n} row(s)" for col, n in sorted(gap.items(), key=lambda kv: -kv[1])]
    else:
        lines.append("None — every gold column has a matching rules column.")
    (OUT / "ab_viability.md").write_text("\n".join(lines))


if __name__ == "__main__":
    run(); print("wrote metrics.parquet + ab_viability.md")
