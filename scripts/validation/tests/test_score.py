import sys
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]


def test_per_column_metrics_math():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics
    # column c1: rules predicts [1,1,0], reference truth [1,0,0] -> tp1 fp1 fn0 tn1
    rules = pd.DataFrame({"literature_id": ["a", "b", "c"], "column": ["c1"] * 3, "value": [1, 1, 0]})
    ref = pd.DataFrame({"literature_id": ["a", "b", "c"], "column": ["c1"] * 3, "value": [1, 0, 0]})
    m = per_column_metrics(rules, ref).set_index("column").loc["c1"]
    assert (m.tp, m.fp, m.fn, m.tn) == (1, 1, 0, 1)
    assert abs(m.precision - 0.5) < 1e-9 and abs(m.recall - 1.0) < 1e-9


def test_unmatched_column_dropped_from_metrics_and_reported_by_coverage_helper():
    """A column present in ref_df ('ob_ghost') but with no matching rules
    column at all (simulating gold labels using an ob_ prefix that doesn't
    exist in the parquet, e.g. ob_south_pacific_ocean) must not silently
    contribute rows to per_column_metrics, and the coverage-gap helper must
    surface it explicitly rather than let it vanish unnoticed."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics, missing_rule_columns

    rules = pd.DataFrame({"literature_id": ["a", "b"], "column": ["c1", "c1"], "value": [1, 0]})
    ref = pd.DataFrame({
        "literature_id": ["a", "b", "a", "b", "x"],
        "column": ["c1", "c1", "ob_ghost", "ob_ghost", "ob_ghost"],
        "value": [1, 0, 1, 1, 0],
    })

    metrics = per_column_metrics(rules, ref)
    # only c1 (the matched column) should produce a metrics row
    assert set(metrics["column"]) == {"c1"}

    # coverage helper: given the set of columns actually available in the
    # rules source (here just {"c1"}), ob_ghost has 3 gold rows with no
    # matching rules column
    gap = missing_rule_columns(ref, available_columns={"c1"})
    assert gap == {"ob_ghost": 3}

    # a fully-covered ref_df should report no gap
    assert missing_rule_columns(ref[ref["column"] == "c1"], available_columns={"c1"}) == {}


def test_f1_zero_not_nan_when_fully_wrong():
    """CRITICAL: a column that's fully wrong (tp=0, fp>0, fn>0) has
    legitimately-defined precision=0.0 and recall=0.0. The old guard
    `if prec and rec and (prec+rec)` treated 0.0 as falsy and assigned NaN,
    which `f1.mean()` then silently skips -- inflating macro-F1 by dropping
    the worst columns. F1 must be 0.0 here, not NaN."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics

    rules = pd.DataFrame({"literature_id": ["a", "b", "c"], "column": ["bad"] * 3, "value": [1, 1, 0]})
    ref = pd.DataFrame({"literature_id": ["a", "b", "c"], "column": ["bad"] * 3, "value": [0, 0, 1]})
    m = per_column_metrics(rules, ref).set_index("column").loc["bad"]
    assert m.tp == 0 and m.fp == 2 and m.fn == 1
    assert m.precision == 0.0 and m.recall == 0.0
    assert m.f1 == 0.0
    assert not pd.isna(m.f1)


def test_f1_macro_mean_reflects_zero_f1_columns():
    """A 2-column frame with one perfect column (f1=1.0) and one fully-wrong
    column (f1=0.0) must macro-average to 0.5, not 1.0 (which is what
    happens if the fully-wrong column's F1 is wrongly NaN'd out and
    f1.mean() silently skips it)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics

    # "bad": paper a predicted+ but ref- (fp=1), paper c ref+ but rules- (fn=1)
    #        -> tp=0, fp=1, fn=1 -> prec=0, rec=0 -> F1=0.0 (defined, NOT NaN).
    # "good": tp=1 (a), tn=1 (b) -> F1=1.0.  macro-mean = (0.0 + 1.0) / 2 = 0.5.
    rules = pd.DataFrame({
        "literature_id": ["a", "b", "a", "c"],
        "column": ["good", "good", "bad", "bad"],
        "value": [1, 0, 1, 0],
    })
    ref = pd.DataFrame({
        "literature_id": ["a", "b", "a", "c"],
        "column": ["good", "good", "bad", "bad"],
        "value": [1, 0, 0, 1],
    })
    m = per_column_metrics(rules, ref)
    assert abs(m.set_index("column").loc["bad", "f1"] - 0.0) < 1e-9   # zero-F1 column is 0.0, not NaN
    assert abs(m.f1.mean() - 0.5) < 1e-9                              # and it drags the macro-mean down


def test_f1_stays_nan_when_no_support_at_all():
    """A column with no positive predictions and no positive reference
    labels (tp=fp=fn=0, only tn) has genuinely undefined precision/recall
    (0/0) -- F1 must stay NaN here, not become 0.0."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics

    rules = pd.DataFrame({"literature_id": ["a", "b"], "column": ["empty"] * 2, "value": [0, 0]})
    ref = pd.DataFrame({"literature_id": ["a", "b"], "column": ["empty"] * 2, "value": [0, 0]})
    m = per_column_metrics(rules, ref).set_index("column").loc["empty"]
    assert m.tp == 0 and m.fp == 0 and m.fn == 0
    assert pd.isna(m.precision) and pd.isna(m.recall)
    assert pd.isna(m.f1)


def test_duplicate_literature_id_column_pair_not_double_counted():
    """IMPORTANT: a duplicated (literature_id, column) row in either input
    (e.g. a duplicate literature_id row in the source parquet melting into
    two identical long-format rows) must not double-weight that paper's
    contribution to tp/fp/fn/tn."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics

    rules = pd.DataFrame({
        "literature_id": ["a", "a", "b"],
        "column": ["c1", "c1", "c1"],
        "value": [1, 1, 0],
    })
    ref = pd.DataFrame({
        "literature_id": ["a", "a", "b"],
        "column": ["c1", "c1", "c1"],
        "value": [1, 1, 0],
    })
    m = per_column_metrics(rules, ref).set_index("column").loc["c1"]
    assert (m.tp, m.fp, m.fn, m.tn) == (1, 0, 0, 1)


def test_rules_long_dedupes_duplicate_literature_id_rows(monkeypatch):
    """IMPORTANT: `_rules_long` must drop duplicate literature_id rows from
    the source parquet right after loading it, so a paper with duplicate
    rows (e.g. literature_id 20493, one of 63 duplicated ids in the real
    parquet) isn't melted into two identical (literature_id, column) rows
    that double-weight it downstream."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation import score

    dup_df = pd.DataFrame({
        "literature_id": [20493, 20493, 111],
        "colA": [1.0, 0.0, 0.0],
    })
    monkeypatch.setattr(score.pd, "read_parquet", lambda *a, **k: dup_df.copy())
    long = score._rules_long({"20493", "111"}, ["colA"])
    assert (long["literature_id"] == "20493").sum() == 1


def test_missing_rule_columns_uses_actual_merge_columns_not_full_parquet():
    """IMPORTANT: the coverage-gap check must compare gold columns against
    the columns actually available in the merge (the rules frame's column
    set, itself derived from Fable's label set intersected with the parquet
    columns) -- not the full parquet column universe. A gold column can be
    absent from Fable's label set (and thus from `rules`) while still being
    present in the parquet, which would wrongly report 'no gap'."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import missing_rule_columns

    gold = pd.DataFrame({
        "literature_id": ["a", "b"],
        "column": ["d_extra", "d_extra"],
        "value": [1, 0],
    })
    full_parquet_columns = {"d_extra", "d_other"}
    actual_merge_columns = {"d_other"}  # Fable never labelled d_extra

    # checking against the whole parquet hides the gap (the bug)
    assert missing_rule_columns(gold, full_parquet_columns) == {}
    # checking against the actual merge column universe surfaces it (the fix)
    assert missing_rule_columns(gold, actual_merge_columns) == {"d_extra": 2}
