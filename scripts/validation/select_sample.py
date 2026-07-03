"""Deterministic stratified sample: all gold papers + n_silver papers chosen to
spread across disciplines and to include both fired and non-fired papers per
column (exposing false negatives)."""
import random, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
sys.path.insert(0, str(ROOT / "scripts"))


def _schema_columns():
    """Optional coverage-check helper. Non-critical: the discipline strata
    used by select_sample() come from the d_* columns already present in the
    parquet, not from this list. Must never raise — return [] on any
    import/shape mismatch instead of crashing select_sample()."""
    try:
        from extract_schema_columns import ALL_SCHEMAS
        cols = []
        for schema in ALL_SCHEMAS:
            if isinstance(schema, dict):
                cols += list(schema["columns"].keys())
            elif hasattr(schema, "columns"):
                cols += [c.name if hasattr(c, "name") else str(c) for c in schema.columns]
        return cols
    except Exception:
        return []


def select_sample(n_silver: int = 300) -> pd.DataFrame:
    rng = random.Random(20260707)
    df = pd.read_parquet(ROOT / "outputs/literature_review_enriched.parquet")
    df["literature_id"] = df["literature_id"].apply(lambda v: str(int(float(v))))
    gold_ids = pd.read_csv(OUT / "gold_labels.csv", dtype={"literature_id": str})["literature_id"].unique().tolist()

    # discipline strata: d_* columns present in the parquet
    dcols = [c for c in df.columns if c.startswith("d_")]
    pool = df[~df["literature_id"].isin(gold_ids)].copy()

    # bucket each paper by its first-firing discipline (or 'none')
    def disc(row):
        for c in dcols:
            if row.get(c):
                return c
        return "none"

    pool["stratum"] = pool.apply(disc, axis=1)
    strata = pool.groupby("stratum")
    per = max(1, n_silver // max(1, pool["stratum"].nunique()))
    picked = []
    for _, grp in strata:
        ids = grp["literature_id"].tolist()
        rng.shuffle(ids)
        picked += ids[:per]
    # top up / trim to exactly n_silver
    remaining = [i for i in pool["literature_id"] if i not in set(picked)]
    rng.shuffle(remaining)
    while len(picked) < n_silver and remaining:
        picked.append(remaining.pop())
    picked = picked[:n_silver]

    meta = df.set_index("literature_id")
    rows = [(g, meta.loc[g, "year"] if g in meta.index else None,
             meta.loc[g, "title"] if g in meta.index else "", "gold") for g in gold_ids]
    rows += [(p, meta.loc[p, "year"], meta.loc[p, "title"], "silver") for p in picked]
    out = pd.DataFrame(rows, columns=["literature_id", "year", "title", "tier"]).drop_duplicates("literature_id")
    out.to_csv(OUT / "validation_sample.csv", index=False)
    return out


if __name__ == "__main__":
    s = select_sample()
    print(s["tier"].value_counts().to_dict())
