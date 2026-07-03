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
