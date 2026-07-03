import sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def test_sample_is_deterministic_and_covers_gold():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.select_sample import select_sample
    a = select_sample(n_silver=300)
    b = select_sample(n_silver=300)
    assert list(a["literature_id"]) == list(b["literature_id"])   # deterministic
    gold = pd.read_csv(ROOT / "outputs/validation/gold_labels.csv", dtype={"literature_id": str})
    assert set(gold["literature_id"].unique()) <= set(a["literature_id"])  # all gold included
    assert (a["tier"] == "gold").sum() == gold["literature_id"].nunique()
    assert (a["tier"] == "silver").sum() == 300
    assert a["literature_id"].is_unique


def test_sample_year_and_title_are_scalar():
    """Guards against duplicate literature_id rows in the parquet causing
    meta.loc[id, col] to return a multi-row Series, which pandas then
    stringifies (with embedded newlines like "Name: year, dtype: float64")
    into the CSV instead of a scalar value."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.select_sample import select_sample
    a = select_sample(n_silver=300)
    for val in a["year"]:
        assert not isinstance(val, pd.Series), f"year is a Series, not scalar: {val!r}"
        assert "\n" not in str(val), f"year stringifies with embedded newline: {val!r}"
    for val in a["title"]:
        assert isinstance(val, str) or pd.isna(val), f"title is not a plain string: {val!r}"
        assert "\n" not in str(val), f"title stringifies with embedded newline: {val!r}"

    # Also check the CSV that gets written to disk, since that is what
    # downstream reviewers actually read.
    csv_path = ROOT / "outputs/validation/validation_sample.csv"
    with open(csv_path) as f:
        text = f.read()
    assert "dtype: float64" not in text
    assert "dtype: object" not in text
