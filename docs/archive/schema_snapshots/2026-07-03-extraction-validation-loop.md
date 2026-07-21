# Extraction Validation Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the 123-column rule extractor's accuracy against human + LLM labels, run a loop that auto-tests rule improvements, and produce a conference dashboard plus an LLM-extraction viability verdict.

**Architecture:** Seven focused Python/R modules under `scripts/validation/` writing to `outputs/validation/`. A gold set (15 human-labelled papers) licenses Fable as an oracle over a 300-paper stratified silver set; the scorer compares rules vs Fable vs human; a diagnosis+auto-test loop proposes and validates regex/threshold changes; an R dashboard renders the figures.

**Tech Stack:** Python 3 (pandas, pyarrow, anthropic SDK), Fable (`claude-fable-5`) via structured tool-use output, R (ggplot2, openxlsx) for figures, existing `scripts/extract_schema_columns.py` for re-extraction.

## Global Constraints

- **literature_id join gotcha:** `outputs/openalex_paper_authors.csv` stores `literature_id` as float (`6920.0`); `outputs/literature_review_enriched.parquet` and `outputs/schema_extraction_evidence.csv` use string (`'6920'`). Always normalise with `str(int(float(x)))` before any join.
- **PDF text source:** reuse the text + section pipeline from `scripts/extract_schema_columns.py` (do NOT re-implement PDF parsing). PDF library root: `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/`.
- **Determinism:** every sampling/seed uses `random.Random(20260707)`. Fable calls cached by PDF SHA-1 under `outputs/validation/.fable_cache/` so reruns are free and stable.
- **Gold is never LLM-derived.** Gold labels come only from human JSONs. Silver is Fable-labelled and always reported as such.
- **Model id:** Fable = `claude-fable-5`. Use the Anthropic SDK with a forced tool call (structured output); never parse free text.
- **Language:** Python for pipeline/automation; R (ggplot2) for figures/dashboard, per project convention.
- **Outputs dir:** all artefacts under `outputs/validation/`. All review sheets `.xlsx` with frozen+bold+autofiltered header.

---

### Task 1: Ground-truth loader

**Files:**
- Create: `scripts/validation/load_gold_labels.py`
- Create: `scripts/validation/__init__.py` (empty)
- Test: `scripts/validation/tests/test_load_gold_labels.py`

**Interfaces:**
- Produces: `load_gold_triples() -> pandas.DataFrame` with columns `literature_id:str, column:str, human_value:int(0|1), reviewer:str, group_rating:str`. Writes `outputs/validation/gold_labels.csv`.
- Produces: `load_rule_backlog() -> pandas.DataFrame` with columns `column, change_type, detail, rationale, source, paper_ref`. Writes `outputs/validation/rule_backlog.csv`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_load_gold_labels.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validation.load_gold_labels'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/validation/load_gold_labels.py
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
            rows.append((str(r.get("Category", "")), "proposal",
                         str(r.get("Proposed Rule", r.get("Proposed_Rule", ""))),
                         str(r.get("Assessment", "")), "david", str(r.get("Paper", ""))))
    df = pd.DataFrame(rows, columns=["column", "change_type", "detail", "rationale", "source", "paper_ref"])
    df.to_csv(OUT / "rule_backlog.csv", index=False)
    return df

if __name__ == "__main__":
    g = load_gold_triples(); b = load_rule_backlog()
    print(f"gold triples: {len(g)} across {g['reviewer'].nunique()} reviewers")
    print(f"rule backlog: {len(b)} proposals")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && git fetch origin && python -m pytest scripts/validation/tests/test_load_gold_labels.py -v`
Expected: PASS. (If the `Validation_Rules` column names differ, adjust the `.get()` keys — inspect with `python -c "import pandas as pd; print(pd.read_excel('docs/schema_proposals/ruiz_garcia_validation_master.xlsx', sheet_name='Validation_Rules').columns.tolist())"`.)

- [ ] **Step 5: Commit**

```bash
git add scripts/validation/__init__.py scripts/validation/load_gold_labels.py scripts/validation/tests/test_load_gold_labels.py outputs/validation/gold_labels.csv outputs/validation/rule_backlog.csv
git commit -m "feat(validation): load human gold labels + rule backlog"
```

---

### Task 2: Stratified sample selector

**Files:**
- Create: `scripts/validation/select_sample.py`
- Test: `scripts/validation/tests/test_select_sample.py`

**Interfaces:**
- Consumes: `outputs/literature_review_enriched.parquet`, `outputs/validation/gold_labels.csv`, schema column list from `scripts/extract_schema_columns.py` (`ALL_SCHEMAS`).
- Produces: `select_sample(n_silver=300) -> pandas.DataFrame` with `literature_id:str, year, title, tier:'gold'|'silver'`. Writes `outputs/validation/validation_sample.csv`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/validation/tests/test_select_sample.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_select_sample.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/validation/select_sample.py
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
    from extract_schema_columns import ALL_SCHEMAS
    cols = []
    for schema in ALL_SCHEMAS:
        cols += list(schema["columns"].keys()) if isinstance(schema, dict) else []
    return cols

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
        ids = grp["literature_id"].tolist(); rng.shuffle(ids)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_select_sample.py -v`
Expected: PASS. (If `ALL_SCHEMAS` structure differs, adapt `_schema_columns()` — it is only used for optional coverage checks here; the discipline strata come from `d_` parquet columns.)

- [ ] **Step 5: Commit**

```bash
git add scripts/validation/select_sample.py scripts/validation/tests/test_select_sample.py outputs/validation/validation_sample.csv
git commit -m "feat(validation): deterministic stratified sample selector"
```

---

### Task 3: Fable oracle extractor

**Files:**
- Create: `scripts/validation/fable_extract.py`
- Test: `scripts/validation/tests/test_fable_extract.py`

**Interfaces:**
- Consumes: `outputs/validation/validation_sample.csv`; PDF text via `extract_schema_columns` helpers; schema column definitions (name+description).
- Produces: `extract_paper(text:str, columns:list[dict]) -> dict` returning `{col: {"present": bool, "evidence": str, "confidence": float}}`; `run(sample_df) -> None` writing `outputs/validation/fable_labels.parquet` (long: `literature_id, column, present, evidence, confidence`) and `outputs/validation/fable_token_log.csv` (`literature_id, input_tokens, output_tokens`).
- Caching: `outputs/validation/.fable_cache/<pdf_sha1>.json`.

- [ ] **Step 1: Write the failing test** (deterministic parse + cache; no network)

```python
# scripts/validation/tests/test_fable_extract.py
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def test_parse_tool_response_to_dict():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.fable_extract import parse_tool_response
    fake = {"columns": [
        {"name": "d_movement", "present": True, "evidence": "acoustic telemetry", "confidence": 0.9},
        {"name": "pr_fishing", "present": False, "evidence": "", "confidence": 0.8}]}
    out = parse_tool_response(fake)
    assert out["d_movement"]["present"] is True
    assert out["d_movement"]["evidence"] == "acoustic telemetry"
    assert out["pr_fishing"]["present"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_fable_extract.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/validation/fable_extract.py
"""Fable (claude-fable-5) oracle extraction of the 123 schema columns per paper,
via a forced structured tool call. Cached by PDF SHA-1; token usage logged."""
import hashlib, json, os, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"; CACHE = OUT / ".fable_cache"; CACHE.mkdir(parents=True, exist_ok=True)
MODEL = "claude-fable-5"
sys.path.insert(0, str(ROOT / "scripts"))

TOOL = {
    "name": "record_columns",
    "description": "Record presence of each schema column in the paper.",
    "input_schema": {
        "type": "object",
        "properties": {"columns": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "present": {"type": "boolean"},
                "evidence": {"type": "string"},
                "confidence": {"type": "number"}},
            "required": ["name", "present", "confidence"]}}},
        "required": ["columns"]},
}

def parse_tool_response(tool_input: dict) -> dict:
    out = {}
    for c in tool_input.get("columns", []):
        out[c["name"]] = {"present": bool(c.get("present")),
                          "evidence": c.get("evidence", ""),
                          "confidence": float(c.get("confidence", 0.0))}
    return out

def _prompt(text, columns):
    defs = "\n".join(f"- {c['name']}: {c['description']}" for c in columns)
    return (f"You are auditing a shark-research paper. For EACH column below, decide if the "
            f"paper's own study (not its references/background) provides evidence for it. "
            f"Return every column.\n\nCOLUMNS:\n{defs}\n\nPAPER TEXT:\n{text[:120000]}")

def extract_paper(text, columns, client=None):
    if client is None:
        import anthropic; client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=8000, tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_columns"},
        messages=[{"role": "user", "content": _prompt(text, columns)}])
    usage = (msg.usage.input_tokens, msg.usage.output_tokens)
    block = next(b for b in msg.content if b.type == "tool_use")
    return parse_tool_response(block.input), usage

def _schema_column_defs():
    from extract_schema_columns import ALL_SCHEMAS
    cols = []
    for s in ALL_SCHEMAS:
        for name, spec in (s.get("columns") or {}).items():
            cols.append({"name": name, "description": (spec.get("description") if isinstance(spec, dict) else str(spec)) or name})
    return cols

def _pdf_text(lit_id):
    from extract_schema_columns import get_pdf_text_for_paper  # reuse existing resolver
    return get_pdf_text_for_paper(lit_id)  # returns (text, sha1) or (None, None)

def run(sample_df):
    import anthropic; client = anthropic.Anthropic()
    columns = _schema_column_defs()
    rows, toks = [], []
    for lit in sample_df["literature_id"]:
        text, sha = _pdf_text(lit)
        if not text:
            continue
        cache = CACHE / f"{sha}.json"
        if cache.exists():
            res = json.loads(cache.read_text()); usage = (0, 0)
        else:
            res, usage = extract_paper(text, columns, client)
            cache.write_text(json.dumps(res))
        for col, v in res.items():
            rows.append((lit, col, int(v["present"]), v["evidence"], v["confidence"]))
        toks.append((lit, usage[0], usage[1]))
    pd.DataFrame(rows, columns=["literature_id", "column", "present", "evidence", "confidence"]
                 ).to_parquet(OUT / "fable_labels.parquet")
    pd.DataFrame(toks, columns=["literature_id", "input_tokens", "output_tokens"]
                 ).to_csv(OUT / "fable_token_log.csv", index=False)

if __name__ == "__main__":
    run(pd.read_csv(OUT / "validation_sample.csv", dtype={"literature_id": str}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_fable_extract.py -v`
Expected: PASS (parse test is offline).

- [ ] **Step 5: Live smoke test (1 paper) then commit**

Run: `cd "$(git rev-parse --show-toplevel)" && ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY python -c "import pandas as pd, sys; sys.path.insert(0,'scripts'); from validation.fable_extract import run; run(pd.read_csv('outputs/validation/validation_sample.csv', dtype={'literature_id':str}).head(1))"`
Expected: creates `outputs/validation/fable_labels.parquet` with rows for 1 paper; `fable_token_log.csv` shows non-zero tokens.
Note: verify `get_pdf_text_for_paper` / `get_pdf_text_for_paper`-equivalent name in `extract_schema_columns.py` first (`grep -n "def .*pdf.*text\|def .*text.*paper" scripts/extract_schema_columns.py`) and wire `_pdf_text` to the real resolver.

```bash
git add scripts/validation/fable_extract.py scripts/validation/tests/test_fable_extract.py
git commit -m "feat(validation): Fable oracle extractor with SHA-1 cache + token log"
```

---

### Task 4: Scorer (accuracy + A/B + cost)

**Files:**
- Create: `scripts/validation/score.py`
- Test: `scripts/validation/tests/test_score.py`

**Interfaces:**
- Consumes: `gold_labels.csv`, `fable_labels.parquet`, rule labels from `literature_review_enriched.parquet` (binary columns), `fable_token_log.csv`.
- Produces: `per_column_metrics(rules_df, ref_df) -> pandas.DataFrame` (`column, tp, fp, fn, tn, precision, recall, f1`); `run() -> None` writing `outputs/validation/metrics.parquet` and `outputs/validation/ab_viability.md`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/validation/tests/test_score.py
import sys
import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def test_per_column_metrics_math():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.score import per_column_metrics
    # column c1: rules predicts [1,1,0], reference truth [1,0,0] -> tp1 fp1 fn0 tn1
    rules = pd.DataFrame({"literature_id": ["a","b","c"], "column": ["c1"]*3, "value": [1,1,0]})
    ref   = pd.DataFrame({"literature_id": ["a","b","c"], "column": ["c1"]*3, "value": [1,0,0]})
    m = per_column_metrics(rules, ref).set_index("column").loc["c1"]
    assert (m.tp, m.fp, m.fn, m.tn) == (1, 1, 0, 1)
    assert abs(m.precision - 0.5) < 1e-9 and abs(m.recall - 1.0) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_score.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/validation/score.py
"""Score rules vs human (gold) and rules vs Fable (silver); build the A/B
viability memo with a 40k-corpus token-cost extrapolation."""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
# Fable pricing snapshot (USD per 1M tokens) — update from claude-api skill before quoting.
PRICE_IN, PRICE_OUT = 1.00, 5.00

def per_column_metrics(rules_df, ref_df) -> pd.DataFrame:
    m = rules_df.merge(ref_df, on=["literature_id", "column"], suffixes=("_r", "_ref"))
    out = []
    for col, g in m.groupby("column"):
        tp = int(((g.value_r == 1) & (g.value_ref == 1)).sum())
        fp = int(((g.value_r == 1) & (g.value_ref == 0)).sum())
        fn = int(((g.value_r == 0) & (g.value_ref == 1)).sum())
        tn = int(((g.value_r == 0) & (g.value_ref == 0)).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if prec and rec and (prec + rec) else float("nan")
        out.append((col, tp, fp, fn, tn, prec, rec, f1))
    return pd.DataFrame(out, columns=["column", "tp", "fp", "fn", "tn", "precision", "recall", "f1"])

def _rules_long(sample_ids, columns):
    df = pd.read_parquet(ROOT / "outputs/literature_review_enriched.parquet")
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

    gold_ids = set(gold.literature_id)
    m_gold = per_column_metrics(rules[rules.literature_id.isin(gold_ids)][["literature_id","column","value"]],
                                gold[["literature_id","column","value"]])
    m_silver = per_column_metrics(rules[["literature_id","column","value"]],
                                  fab[["literature_id","column","value"]])
    m_gold["set"] = "gold_rules_vs_human"; m_silver["set"] = "silver_rules_vs_fable"
    metrics = pd.concat([m_gold, m_silver], ignore_index=True)
    metrics.to_parquet(OUT / "metrics.parquet")

    # bridge: fable vs human on gold
    bridge = per_column_metrics(fab[fab.literature_id.isin(gold_ids)][["literature_id","column","value"]],
                                gold[["literature_id","column","value"]])
    # cost extrapolation
    tok = pd.read_csv(OUT / "fable_token_log.csv")
    tok = tok[tok.input_tokens > 0]
    n_pdfs_target = 40000
    mean_in, mean_out = tok.input_tokens.mean(), tok.output_tokens.mean()
    cost40k = n_pdfs_target * (mean_in/1e6*PRICE_IN + mean_out/1e6*PRICE_OUT)
    lines = [
        "# LLM extraction A/B viability", "",
        f"- Papers Fable-labelled: {tok.shape[0]}",
        f"- Mean tokens/paper: {mean_in:.0f} in / {mean_out:.0f} out",
        f"- Fable-vs-human agreement (gold, macro-F1): {bridge.f1.mean():.3f}",
        f"- Rules-vs-human (gold, macro-F1): {m_gold.f1.mean():.3f}",
        f"- Rules-vs-Fable (silver, macro-F1): {m_silver.f1.mean():.3f}",
        f"- **Extrapolated Fable cost for {n_pdfs_target:,} PDFs: ${cost40k:,.0f}** "
        f"(at ${PRICE_IN}/{PRICE_OUT} per 1M in/out; excludes OCR + retries; verify pricing via claude-api skill).",
    ]
    (OUT / "ab_viability.md").write_text("\n".join(lines))

if __name__ == "__main__":
    run(); print("wrote metrics.parquet + ab_viability.md")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_score.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/validation/score.py scripts/validation/tests/test_score.py
git commit -m "feat(validation): scorer with gold/silver metrics + A/B cost memo"
```

---

### Task 5: Diagnosis + rule-proposal engine

**Files:**
- Create: `scripts/validation/propose_rules.py`
- Test: `scripts/validation/tests/test_propose_rules.py`

**Interfaces:**
- Consumes: `metrics.parquet`, `fable_labels.parquet` (evidence quotes), `docs/validate/assets/rules.json`, `rule_backlog.csv`.
- Produces: `rank_disagreements(metrics) -> list[str]` (columns worst-first by silver F1 with enough support); `run() -> None` writing `outputs/validation/rule_proposals.csv` (`column, change_type, detail, rationale, source, predicted_impact`).

- [ ] **Step 1: Write the failing test**

```python
# scripts/validation/tests/test_propose_rules.py
import sys, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def test_rank_disagreements_orders_worst_first():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.propose_rules import rank_disagreements
    m = pd.DataFrame({"set":["silver_rules_vs_fable"]*3, "column":["a","b","c"],
                      "f1":[0.2,0.9,0.5], "tp":[10,10,10], "fp":[9,1,4], "fn":[8,1,3]})
    assert rank_disagreements(m)[0] == "a"  # lowest f1, adequate support
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_propose_rules.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/validation/propose_rules.py
"""For low-F1 columns, ask Fable to propose a concrete rule change from the
disagreeing papers' evidence + the current rule. Merge with David's backlog."""
import json, sys
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
        j = propose_for_column(col, ev, rules.get(col, {}), client)
        rows.append((col, j.get("change_type", ""), j.get("detail", ""), j.get("rationale", ""), "fable", ""))
    backlog = pd.read_csv(OUT / "rule_backlog.csv")
    for _, r in backlog.iterrows():
        rows.append((r["column"], r["change_type"], r["detail"], r["rationale"], "david", ""))
    pd.DataFrame(rows, columns=["column","change_type","detail","rationale","source","predicted_impact"]
                 ).to_csv(OUT / "rule_proposals.csv", index=False)

if __name__ == "__main__":
    run(); print("wrote rule_proposals.csv")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_propose_rules.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/validation/propose_rules.py scripts/validation/tests/test_propose_rules.py
git commit -m "feat(validation): Fable rule-diagnosis + proposal engine"
```

---

### Task 6: Auto-test loop

**Files:**
- Create: `scripts/validation/autotest_rules.py`
- Test: `scripts/validation/tests/test_autotest_rules.py`

**Interfaces:**
- Consumes: `rule_proposals.csv`, `validation_sample.csv`, `fable_labels.parquet` (silver reference), `gold_labels.csv` (overfit check), the extractor's sample-mode re-run.
- Produces: `evaluate_change(before_f1, after_f1, guard=0.0) -> bool`; `run() -> None` writing `outputs/validation/improved_rules/` and `outputs/validation/improvement_log.csv` (`column, change_type, silver_f1_before, silver_f1_after, gold_f1_after, accepted`).

- [ ] **Step 1: Write the failing test**

```python
# scripts/validation/tests/test_autotest_rules.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def test_evaluate_change_accepts_only_improvements():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.autotest_rules import evaluate_change
    assert evaluate_change(before_f1=0.50, after_f1=0.62) is True
    assert evaluate_change(before_f1=0.50, after_f1=0.50) is False
    assert evaluate_change(before_f1=0.50, after_f1=0.40) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_autotest_rules.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/validation/autotest_rules.py
"""Apply each proposed rule change to a copy of the rule set, re-extract the
sample, re-score vs Fable silver, keep only if silver-F1 improves without
regressing. Gold rules-vs-human F1 reported alongside as the overfit check."""
import json, shutil, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
IMPROVED = OUT / "improved_rules"; IMPROVED.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))

def evaluate_change(before_f1, after_f1, guard=0.0):
    return bool(after_f1 > before_f1 + guard)

def _extract_sample_column(rules_obj, column, sample_ids):
    """Run the extractor for one column over the sample with a patched rule set.
    Returns a long df literature_id,column,value. Reuses extract_schema_columns
    in single-column mode (see its `extract_columns(text, only=[column])`)."""
    from extract_schema_columns import extract_for_ids_with_rules  # sample-mode entrypoint
    return extract_for_ids_with_rules(sample_ids, rules_obj, only=[column])

def run():
    from validation.score import per_column_metrics
    proposals = pd.read_csv(OUT / "rule_proposals.csv")
    sample = pd.read_csv(OUT / "validation_sample.csv", dtype={"literature_id": str})
    fab = pd.read_parquet(OUT / "fable_labels.parquet").rename(columns={"present": "value"})
    fab["literature_id"] = fab["literature_id"].astype(str)
    gold = pd.read_csv(OUT / "gold_labels.csv", dtype={"literature_id": str}).rename(columns={"human_value": "value"})
    base_rules = json.loads((ROOT / "docs/validate/assets/rules.json").read_text())
    sample_ids = sample["literature_id"].tolist()
    gold_ids = set(gold.literature_id)

    log = []
    working = json.loads(json.dumps(base_rules))  # deep copy accumulator
    for _, p in proposals.iterrows():
        col = p["column"]
        if col not in working:
            continue
        before = _extract_sample_column(working, col, sample_ids)
        f1_before = per_column_metrics(before, fab[fab.column == col][["literature_id","column","value"]]).f1.mean()
        trial = json.loads(json.dumps(working))
        _apply_proposal(trial, p)  # mutate trial[col] per change_type/detail
        after = _extract_sample_column(trial, col, sample_ids)
        f1_after = per_column_metrics(after, fab[fab.column == col][["literature_id","column","value"]]).f1.mean()
        gold_after = per_column_metrics(after[after.literature_id.isin(gold_ids)],
                                        gold[gold.column == col][["literature_id","column","value"]]).f1.mean()
        accept = evaluate_change(f1_before, f1_after)
        if accept:
            working = trial
        log.append((col, p["change_type"], f1_before, f1_after, gold_after, accept))

    (IMPROVED / "rules.json").write_text(json.dumps(working, indent=2))
    pd.DataFrame(log, columns=["column","change_type","silver_f1_before","silver_f1_after","gold_f1_after","accepted"]
                 ).to_csv(OUT / "improvement_log.csv", index=False)

def _apply_proposal(rules_obj, p):
    r = rules_obj.setdefault(p["column"], {})
    ct, detail = p["change_type"], str(p["detail"])
    if ct == "add_terms":
        r.setdefault("terms", []).extend(t.strip() for t in detail.split(",") if t.strip())
    elif ct == "remove_terms":
        drop = {t.strip() for t in detail.split(",")}
        r["terms"] = [t for t in r.get("terms", []) if t not in drop]
    elif ct == "threshold":
        try: r["threshold"] = float(detail)
        except ValueError: pass
    # 'anchor'/'review' left for human handling

if __name__ == "__main__":
    run(); print("wrote improved_rules/rules.json + improvement_log.csv")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_autotest_rules.py -v`
Expected: PASS.

- [ ] **Step 5: Wire the sample-mode extractor, then commit**

Before running `run()`, confirm/implement the two reuse hooks in `scripts/extract_schema_columns.py`:
`grep -n "def extract_for_ids_with_rules\|def extract_columns\|only=" scripts/extract_schema_columns.py`. If absent, add a thin `extract_for_ids_with_rules(ids, rules_obj, only)` wrapper that runs the existing per-paper extraction against `rules_obj` for the listed ids/columns and returns a long df. Keep that wrapper change in this commit.

```bash
git add scripts/validation/autotest_rules.py scripts/validation/tests/test_autotest_rules.py scripts/extract_schema_columns.py
git commit -m "feat(validation): auto-test rule-improvement loop with overfit guard"
```

---

### Task 7: Dashboard + figures

**Files:**
- Create: `scripts/validation/make_dashboard.R`
- Create: `scripts/validation/build_dashboard.py` (assembles a self-contained HTML from the metrics + figures)
- Test: `scripts/validation/tests/test_dashboard_outputs.py`

**Interfaces:**
- Consumes: `metrics.parquet`, `ab_viability.md`, `improvement_log.csv`.
- Produces: `outputs/validation/figures/*.png` and `outputs/validation/dashboard.html`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/validation/tests/test_dashboard_outputs.py
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/validation"

def test_dashboard_artifacts_exist_and_nonempty():
    for f in ["figures/per_column_pr.png", "figures/improvement.png", "dashboard.html"]:
        p = OUT / f
        assert p.exists() and p.stat().st_size > 1000, f"missing/empty: {f}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "$(git rev-parse --show-toplevel)" && python -m pytest scripts/validation/tests/test_dashboard_outputs.py -v`
Expected: FAIL (files absent).

- [ ] **Step 3: Write the figure + dashboard builders**

```r
# scripts/validation/make_dashboard.R
# Per-column precision/recall bars (worst-first) + before/after improvement.
suppressMessages({library(arrow); library(ggplot2); library(dplyr); library(tidyr)})
out <- "outputs/validation"; dir.create(file.path(out, "figures"), showWarnings = FALSE, recursive = TRUE)
m <- read_parquet(file.path(out, "metrics.parquet")) |> filter(set == "silver_rules_vs_fable")
pr <- m |> select(column, precision, recall) |> pivot_longer(-column) |>
  filter(!is.na(value)) |> group_by(column) |> mutate(ord = mean(value)) |> ungroup()
ggplot(pr, aes(reorder(column, ord), value, fill = name)) +
  geom_col(position = "dodge") + coord_flip() +
  scale_fill_manual(values = c(precision = "#2166AC", recall = "#B2182B")) +
  labs(x = NULL, y = NULL, fill = NULL, title = "Rule extractor: precision & recall per column (vs Fable silver)") +
  theme_minimal(base_size = 9)
ggsave(file.path(out, "figures/per_column_pr.png"), width = 8, height = 11, dpi = 150)

imp <- read.csv(file.path(out, "improvement_log.csv"))
if (nrow(imp) > 0) {
  impl <- imp |> select(column, silver_f1_before, silver_f1_after) |>
    pivot_longer(-column, names_to = "stage", values_to = "f1")
  ggplot(impl, aes(reorder(column, f1), f1, colour = stage, group = column)) +
    geom_line(colour = "grey70") + geom_point(size = 2) + coord_flip() +
    scale_colour_manual(values = c(silver_f1_before = "grey50", silver_f1_after = "#1B7837")) +
    labs(x = NULL, y = "macro F1", colour = NULL, title = "Rule improvement: before -> after") +
    theme_minimal(base_size = 9)
  ggsave(file.path(out, "figures/improvement.png"), width = 8, height = 6, dpi = 150)
} else {
  file.copy(file.path(out, "figures/per_column_pr.png"), file.path(out, "figures/improvement.png"))
}
cat("figures written\n")
```

```python
# scripts/validation/build_dashboard.py
"""Assemble a self-contained HTML dashboard (inline base64 PNGs + the A/B memo)."""
import base64
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "outputs/validation"

def _img(name):
    p = OUT / "figures" / name
    b = base64.b64encode(p.read_bytes()).decode()
    return f'<img style="max-width:100%" src="data:image/png;base64,{b}">'

def main():
    memo = (OUT / "ab_viability.md").read_text() if (OUT / "ab_viability.md").exists() else ""
    html = f"""<!doctype html><meta charset=utf-8><title>Extraction validation</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:1000px}}pre{{background:#f4f4f4;padding:1rem}}</style>
<h1>Extraction validation dashboard</h1>
<h2>Per-column precision &amp; recall</h2>{_img('per_column_pr.png')}
<h2>Rule improvement (before &rarr; after)</h2>{_img('improvement.png')}
<h2>LLM extraction A/B viability</h2><pre>{memo}</pre>"""
    (OUT / "dashboard.html").write_text(html)
    print("wrote dashboard.html")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run builders, then the test to verify it passes**

Run: `cd "$(git rev-parse --show-toplevel)" && Rscript scripts/validation/make_dashboard.R && python scripts/validation/build_dashboard.py && python -m pytest scripts/validation/tests/test_dashboard_outputs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/validation/make_dashboard.R scripts/validation/build_dashboard.py scripts/validation/tests/test_dashboard_outputs.py
git commit -m "feat(validation): dashboard figures + self-contained HTML"
```

---

## End-to-end run order

```bash
cd "$(git rev-parse --show-toplevel)"
git fetch origin                                            # gold branches
python scripts/validation/load_gold_labels.py
python scripts/validation/select_sample.py
python scripts/validation/fable_extract.py                 # ~315 Fable calls (cached)
python scripts/validation/score.py                         # metrics + A/B memo
python scripts/validation/propose_rules.py                 # rule proposals
python scripts/validation/autotest_rules.py                # improvement loop
Rscript scripts/validation/make_dashboard.R && python scripts/validation/build_dashboard.py
```

## Notes for the implementer

- **Reuse, don't rebuild:** `fable_extract._pdf_text` and `autotest_rules._extract_sample_column` MUST call into `scripts/extract_schema_columns.py`. Grep for the real function names first; the plan's names are placeholders for those hooks and Step 5 of Tasks 3 & 6 covers wiring them.
- **rules.json shape:** confirm `docs/validate/assets/rules.json` structure (`grep -o '"[a-z]*_[a-z_]*"' docs/validate/assets/rules.json | head`) and adapt `_apply_proposal` to it before running Task 6.
- **Pricing:** the `ab_viability.md` cost line hard-codes a pricing snapshot — read the `claude-api` skill and update `PRICE_IN/PRICE_OUT` before quoting the number on a slide.
- **Cost control:** Task 3 caps 315 papers; if tokens/paper run high, cut silver to 150 (still passes all tests). The cache makes reruns free.
