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
