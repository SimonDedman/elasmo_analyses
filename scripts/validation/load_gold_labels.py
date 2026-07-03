"""Load human validation ground truth from the validation/A50* git branches
and David Ruiz-Garcia's rule-proposal xlsx into flat tables."""
import json, subprocess
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"; OUT.mkdir(parents=True, exist_ok=True)

def _branches():
    txt = subprocess.run(["git", "branch", "-r"], cwd=ROOT, capture_output=True, text=True).stdout
    return [b.strip() for b in txt.splitlines() if "origin/validation/A" in b]

def _json_on_branch(branch):
    # each branch holds validations/<openalexid>_<ts>.json
    files = subprocess.run(["git", "ls-tree", "-r", "--name-only", branch.strip()],
                           cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    for f in files:
        if f.startswith("validations/") and f.endswith(".json"):
            blob = subprocess.run(["git", "show", f"{branch.strip()}:{f}"],
                                  cwd=ROOT, capture_output=True, text=True).stdout
            return json.loads(blob)
    return None

def load_gold_triples() -> pd.DataFrame:
    rows = []
    for br in _branches():
        payload = _json_on_branch(br)
        if not payload:
            continue
        reviewer = payload.get("openalex_id", "").rsplit("/", 1)[-1]
        for lit, sections in (payload.get("papers") or {}).items():
            lit = str(int(float(lit)))
            for prefix, data in sections.items():
                if not isinstance(data, dict):
                    continue
                rating = data.get("rating") or ""
                for col in (data.get("added") or []):
                    rows.append((lit, col, 1, reviewer, rating))
                for col in (data.get("removed") or []):
                    rows.append((lit, col, 0, reviewer, rating))
    df = pd.DataFrame(rows, columns=["literature_id", "column", "human_value", "reviewer", "group_rating"])
    df = df.drop_duplicates(subset=["literature_id", "column", "reviewer"], keep="last")
    df.to_csv(OUT / "gold_labels.csv", index=False)
    return df

def load_rule_backlog() -> pd.DataFrame:
    xlsx = ROOT / "docs/schema_proposals/ruiz_garcia_validation_master.xlsx"
    rows = []
    if xlsx.exists():
        x = pd.read_excel(xlsx, sheet_name="Validation_Rules")
        for _, r in x.iterrows():
            rows.append((str(r.get("extraction_target", "")), str(r.get("assessment", "")),
                         str(r.get("rule_proposed", "")),
                         str(r.get("issues", "")), "david",
                         str(r.get("paper_id based on which proposal is done", ""))))
    df = pd.DataFrame(rows, columns=["column", "change_type", "detail", "rationale", "source", "paper_ref"])
    df.to_csv(OUT / "rule_backlog.csv", index=False)
    return df

if __name__ == "__main__":
    g = load_gold_triples(); b = load_rule_backlog()
    print(f"gold triples: {len(g)} across {g['reviewer'].nunique()} reviewers")
    print(f"rule backlog: {len(b)} proposals")
