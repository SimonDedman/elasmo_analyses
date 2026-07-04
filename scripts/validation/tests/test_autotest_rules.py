import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_evaluate_change_accepts_only_improvements():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import evaluate_change
    assert evaluate_change(before_f1=0.50, after_f1=0.62) is True
    assert evaluate_change(before_f1=0.50, after_f1=0.50) is False
    assert evaluate_change(before_f1=0.50, after_f1=0.40) is False


def test_apply_proposal_add_terms_extends_and_preserves_other_keys():
    """add_terms must append the comma-split, stripped detail terms onto the
    existing terms list, and must not touch threshold/anchors/other keys."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import _apply_proposal

    rules = {"eco_pelagic": {"terms": ["pelagic", "oceanic"], "threshold": 2, "anchors": []}}
    proposal = pd.Series({"column": "eco_pelagic", "change_type": "add_terms", "detail": "open sea, blue water "})

    _apply_proposal(rules, proposal)

    assert rules["eco_pelagic"]["terms"] == ["pelagic", "oceanic", "open sea", "blue water"]
    assert rules["eco_pelagic"]["threshold"] == 2
    assert rules["eco_pelagic"]["anchors"] == []


def test_apply_proposal_remove_terms_filters_and_preserves_other_keys():
    """remove_terms must drop only the named terms and leave everything else
    (including term order for survivors) untouched."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import _apply_proposal

    rules = {"eco_pelagic": {"terms": ["pelagic", "oceanic", "epipelagic"], "threshold": 2}}
    proposal = pd.Series({"column": "eco_pelagic", "change_type": "remove_terms", "detail": "oceanic"})

    _apply_proposal(rules, proposal)

    assert rules["eco_pelagic"]["terms"] == ["pelagic", "epipelagic"]
    assert rules["eco_pelagic"]["threshold"] == 2


def test_apply_proposal_threshold_sets_float_and_preserves_other_keys():
    """threshold change must overwrite only the threshold key, leaving terms
    untouched, and must not raise/mutate on a non-numeric detail."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import _apply_proposal

    rules = {"eco_pelagic": {"terms": ["pelagic"], "threshold": 2}}
    proposal = pd.Series({"column": "eco_pelagic", "change_type": "threshold", "detail": "3"})

    _apply_proposal(rules, proposal)

    assert rules["eco_pelagic"]["threshold"] == 3.0
    assert rules["eco_pelagic"]["terms"] == ["pelagic"]

    # non-numeric detail must be silently ignored, not raise
    rules2 = {"eco_pelagic": {"terms": ["pelagic"], "threshold": 2}}
    proposal2 = pd.Series({"column": "eco_pelagic", "change_type": "threshold", "detail": "not-a-number"})
    _apply_proposal(rules2, proposal2)
    assert rules2["eco_pelagic"]["threshold"] == 2


def test_apply_proposal_unknown_column_creates_empty_dict_without_raising():
    """A proposal for a column not yet present in the working rules copy
    (e.g. a brand-new column suggested by Fable) must not raise -- it should
    seed an empty dict for that column and apply the change onto it."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import _apply_proposal

    rules = {}
    proposal = pd.Series({"column": "d_new_column", "change_type": "add_terms", "detail": "foo, bar"})
    _apply_proposal(rules, proposal)
    assert rules["d_new_column"]["terms"] == ["foo", "bar"]


# ---------------------------------------------------------------------------
# Local verification: _extract_sample_column must reproduce the real
# extractor's binary decisions for real papers under the UNMODIFIED current
# rule set. This is the correctness-critical wiring check -- if this drifts
# from the real pipeline, every accept/reject decision downstream is unsound.
# ---------------------------------------------------------------------------

_SAMPLE_CSV = ROOT / "outputs/validation/validation_sample.csv"
_PARQUET = ROOT / "outputs/literature_review_enriched.parquet"
_RULES_JSON = ROOT / "docs/validate/assets/rules.json"

_MISSING_LOCAL_DATA = not (_SAMPLE_CSV.exists() and _PARQUET.exists() and _RULES_JSON.exists())


@pytest.mark.skipif(_MISSING_LOCAL_DATA, reason="requires local validation sample + enriched parquet + rules.json")
@pytest.mark.parametrize("column", ["eco_pelagic", "d_movement", "eco_coastal"])
def test_extract_sample_column_reproduces_parquet_values(column):
    """For the UNMODIFIED current rule, _extract_sample_column's binary
    decision for each (paper, column) must equal the binarised value already
    stored in the enriched parquet (which was produced by the real
    extractor's process_paper()). Uses the first 5 sample papers that have a
    resolvable PDF.

    Investigated: fable_extract._pdf_text() returns PDF body text only (no
    synthetic TITLE section), while process_paper() prepends
    "TITLE\\n<title>\\nOTHER\\n\\n" before section-labelling so title
    keywords count at the eco_/d_/... section weight of 2.0. Replicating
    that prepend in _extract_sample_column gives EXACT (100%) agreement
    across the full 291-paper validation sample for eco_pelagic, d_movement,
    eco_coastal, d_biology (prerequisite_terms path), gear_longline, and
    pr_bycatch -- so this test asserts exact equality, not a tolerance band.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import _extract_sample_column
    from validation.fable_extract import _pdf_text

    rules_obj = json.loads(_RULES_JSON.read_text())
    sample = pd.read_csv(_SAMPLE_CSV, dtype={"literature_id": str})

    sample_ids = []
    for lit in sample["literature_id"]:
        text, _sha = _pdf_text(lit)
        if text is not None:
            sample_ids.append(lit)
        if len(sample_ids) >= 5:
            break
    assert len(sample_ids) == 5, "expected at least 5 sample papers with a resolvable PDF"

    result = _extract_sample_column(rules_obj, column, sample_ids)
    assert list(result.columns) == ["literature_id", "column", "value"]
    assert len(result) == len(sample_ids)
    assert set(result["column"]) == {column}

    df = pd.read_parquet(_PARQUET, columns=["literature_id", column])
    df["literature_id"] = df["literature_id"].apply(lambda v: str(int(float(v))))
    df = df.drop_duplicates(subset="literature_id", keep="first").set_index("literature_id")

    for _, row in result.iterrows():
        expected = int(df.loc[row["literature_id"], column])
        assert int(row["value"]) == expected, (
            f"{column} mismatch for paper {row['literature_id']}: "
            f"_extract_sample_column={row['value']} parquet={expected}"
        )
