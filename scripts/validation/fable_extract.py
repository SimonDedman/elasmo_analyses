"""Fable (claude-fable-5) oracle extraction of the schema columns per paper,
via a forced structured tool call. Cached by PDF SHA-1; token usage logged."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"
CACHE = OUT / ".fable_cache"
CACHE.mkdir(parents=True, exist_ok=True)
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
        import anthropic
        client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=8000, tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_columns"},
        messages=[{"role": "user", "content": _prompt(text, columns)}])
    usage = (msg.usage.input_tokens, msg.usage.output_tokens)
    block = next(b for b in msg.content if b.type == "tool_use")
    return parse_tool_response(block.input), usage


def _schema_column_defs():
    """Build {name, description} dicts from the 7 SchemaCategory objects
    (ECO, PR, GEAR, IMP, DISC, BASIN, SUB_BASIN) in ALL_SCHEMAS. Each
    BinaryColumn has .name/.terms/.threshold (no .description field), so
    the description is synthesised from the column name + its first few
    search terms.

    Note: this covers only the 123 schema binary columns. The pipeline's
    other extracted fields (eco_*_guess, depth_range, gear_target_species,
    imp_is_bycatch/direction/quantified, study_type, etc. — see
    process_paper() in extract_schema_columns.py) are free-text/derived
    columns, not binary presence flags, and are intentionally excluded
    here per the task brief.
    """
    from extract_schema_columns import ALL_SCHEMAS
    cols = []
    for s in ALL_SCHEMAS:
        for c in s.columns:
            desc = c.name.replace("_", " ") + " — evidence such as: " + ", ".join(c.terms[:8])
            cols.append({"name": c.name, "description": desc})
    return cols


_PDF_INDEX = None


def _get_pdf_index():
    global _PDF_INDEX
    if _PDF_INDEX is None:
        from extract_schema_columns import PDF_BASE, build_pdf_index
        _PDF_INDEX = build_pdf_index(PDF_BASE)
    return _PDF_INDEX


def _pdf_text(lit_id):
    """Resolve PDF text + SHA-1 for a paper, given its literature_id.

    Mirrors the resolution path used by process_paper() in
    extract_schema_columns.py: look up authors/year/title from the main
    parquet, derive the first-author surname via _first_surname(), find
    candidate PDFs in the (surname, year) index, disambiguate with
    _pick_best_pdf() using the title, then extract text with
    extract_text_from_pdf(). Returns (None, None) if no PDF resolves.
    """
    from extract_schema_columns import _first_surname, _pick_best_pdf, extract_text_from_pdf

    lit_id = str(int(float(lit_id)))
    df = _get_paper_meta()
    if lit_id not in df.index:
        return None, None
    row = df.loc[lit_id]
    authors = row.get("authors")
    year_raw = row.get("year")
    title = row.get("title") or ""

    if not authors or year_raw is None or (isinstance(year_raw, float) and pd.isna(year_raw)):
        return None, None
    year = int(year_raw)

    surname = _first_surname(authors)
    if not surname:
        return None, None

    candidates = _get_pdf_index().get((surname, year), [])
    best_pdf = _pick_best_pdf(candidates, title)
    if best_pdf is None:
        return None, None

    text = extract_text_from_pdf(best_pdf)
    if not text:
        return None, None

    sha1 = hashlib.sha1(best_pdf.read_bytes()).hexdigest()
    return text, sha1


_PAPER_META = None


def _get_paper_meta():
    global _PAPER_META
    if _PAPER_META is None:
        df = pd.read_parquet(
            ROOT / "outputs/literature_review_enriched.parquet",
            columns=["literature_id", "authors", "year", "title"],
        )
        df["literature_id"] = df["literature_id"].apply(lambda v: str(int(float(v))))
        df = df.drop_duplicates(subset="literature_id", keep="first")
        _PAPER_META = df.set_index("literature_id")
    return _PAPER_META


def _read_cache(cache_path):
    """Read a paper's cache file. Returns (labels_dict, (in_tok, out_tok)).

    Backward-compatible with the old cache format, which was just the bare
    labels dict with no usage recorded (treated as (0, 0) usage)."""
    cached = json.loads(cache_path.read_text())
    if isinstance(cached, dict) and "labels" in cached:
        return cached["labels"], tuple(cached.get("usage", (0, 0)))
    return cached, (0, 0)


def _write_cache(cache_path, labels, usage):
    cache_path.write_text(json.dumps({"labels": labels, "usage": list(usage)}))


def run(sample_df, client=None):
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    columns = _schema_column_defs()
    rows, toks = [], []

    def _flush():
        # Write whatever has been accumulated so far, so an interruption
        # (or one paper's failure) doesn't lose already-completed work.
        if rows:
            pd.DataFrame(rows, columns=["literature_id", "column", "present", "evidence", "confidence"]
                         ).to_parquet(OUT / "fable_labels.parquet")
        if toks:
            pd.DataFrame(toks, columns=["literature_id", "input_tokens", "output_tokens"]
                         ).to_csv(OUT / "fable_token_log.csv", index=False)

    try:
        for i, lit in enumerate(sample_df["literature_id"]):
            lit_norm = str(int(float(lit)))
            try:
                text, sha = _pdf_text(lit_norm)
                if not text:
                    continue
                cache = CACHE / f"{sha}.json"
                if cache.exists():
                    res, usage = _read_cache(cache)
                else:
                    res, usage = extract_paper(text, columns, client)
                    _write_cache(cache, res, usage)
                for col, v in res.items():
                    rows.append((lit_norm, col, int(v["present"]), v["evidence"], v["confidence"]))
                toks.append((lit_norm, usage[0], usage[1]))
            except Exception as e:
                print(f"[fable_extract] paper {lit_norm} failed, skipping: {e}", file=sys.stderr)
                continue
            if (i + 1) % 25 == 0:
                _flush()
    finally:
        _flush()


if __name__ == "__main__":
    run(pd.read_csv(OUT / "validation_sample.csv", dtype={"literature_id": str}))
