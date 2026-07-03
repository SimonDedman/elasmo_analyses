"""For low-F1 columns, ask Fable to propose a concrete rule change from the
disagreeing papers' evidence + the current rule. Merge with David's backlog.

NOTE on rules.json shape: it is keyed by SCHEMA PREFIX (eco_, pr_, gear_,
imp_, d_, b_, sb_, sp_, a_, ob_, depth_), each mapping to a dict that nests
its own columns by full column name (e.g. rules["eco_"]["eco_pelagic"]).
It is NOT keyed by individual column name at the top level -- use
current_rule() below to resolve a column's rule, not rules.get(col, {}).
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
MODEL = "claude-fable-5"


def rank_disagreements(metrics, min_support=15, max_cols=25):
    s = metrics[metrics["set"] == "silver_rules_vs_fable"].copy()
    s["support"] = s.tp + s.fp + s.fn
    s = s[s.support >= min_support].sort_values("f1")
    return s["column"].head(max_cols).tolist()


def _rules():
    p = ROOT / "docs/validate/assets/rules.json"
    return json.loads(p.read_text()) if p.exists() else {}


def current_rule(rules, col):
    """Resolve column `col`'s rule dict from the prefix-nested rules.json
    structure. The prefix is the column's first underscore-delimited token
    plus a trailing underscore (e.g. `d_data_science` -> prefix `d_`,
    looked up as rules["d_"]["d_data_science"]). Returns {} for any
    unknown prefix or unknown column -- never raises."""
    prefix = col.split("_", 1)[0] + "_"
    return rules.get(prefix, {}).get(col, {})


def propose_for_column(col, evidence_examples, current_rule, client=None):
    if client is None:
        import anthropic; client = anthropic.Anthropic()
    prompt = (f"Column `{col}` current rule: {json.dumps(current_rule)}\n\n"
              f"Papers where the regex rule disagreed with expert judgement, with evidence:\n"
              + "\n".join(f"- {e}" for e in evidence_examples[:20]) +
              "\n\nPropose ONE concrete change: add_terms / remove_terms / threshold / anchor. "
              "Reply as JSON {change_type, detail, rationale}.")
    msg = client.messages.create(model=MODEL, max_tokens=1000,
                                 messages=[{"role": "user", "content": prompt}])
    txt = "".join(b.text for b in msg.content if b.type == "text")
    try:
        j = json.loads(txt[txt.index("{"):txt.rindex("}")+1])
    except Exception:
        j = {"change_type": "review", "detail": txt[:400], "rationale": ""}
    return j


def run():
    metrics = pd.read_parquet(OUT / "metrics.parquet")
    fab = pd.read_parquet(OUT / "fable_labels.parquet")
    rules = _rules()
    import anthropic; client = anthropic.Anthropic()
    rows = []
    for col in rank_disagreements(metrics):
        ev = fab[(fab.column == col) & (fab.present == 1)]["evidence"].dropna().tolist()
        j = propose_for_column(col, ev, current_rule(rules, col), client)
        rows.append((col, j.get("change_type", ""), j.get("detail", ""), j.get("rationale", ""), "fable", ""))
    backlog = pd.read_csv(OUT / "rule_backlog.csv")
    for _, r in backlog.iterrows():
        rows.append((r["column"], r["change_type"], r["detail"], r["rationale"], "david", ""))
    pd.DataFrame(rows, columns=["column", "change_type", "detail", "rationale", "source", "predicted_impact"]
                 ).to_csv(OUT / "rule_proposals.csv", index=False)


if __name__ == "__main__":
    run(); print("wrote rule_proposals.csv")
