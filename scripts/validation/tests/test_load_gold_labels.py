# scripts/validation/tests/test_load_gold_labels.py
import subprocess, sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def test_gold_triples_shape_and_values():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.load_gold_labels import load_gold_triples
    df = load_gold_triples()
    # Three reviewers contributed on validation/A50* branches
    assert set(df["reviewer"].unique()) >= {"A5009396914", "A5027778174", "A5078322786"}
    # human_value is strictly binary; literature_id has no ".0"
    assert set(df["human_value"].unique()) <= {0, 1}
    assert not df["literature_id"].str.contains(r"\.0$").any()
    # ~190 explicit column corrections total (added+removed) — allow drift
    assert 150 <= len(df) <= 260
