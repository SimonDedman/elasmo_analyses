#!/usr/bin/env python3
"""
Build the relevance-adjudication workbook from one run_eval.py run.

    python3 scripts/rag/eval/build_adjudication.py --date 2026-10-07 --index-name rag

Pools, for every question, the top-10 papers of every config run that day
(outputs/rag_eval/<date>_<index-name>_<config>.json), adds any silver
relevant_ids that no config retrieved, and writes ONE data tab with one row
per (question, candidate paper) that has not been judged yet. Pairs already
judged in questions.jsonl (`judgements`) are never served again.

Output: outputs/rag_eval/<date>_question_adjudication.xlsx
Decisions go back in with apply_adjudication.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
EVAL_DIR = PROJECT_ROOT / "outputs" / "rag_eval"
QUESTIONS = HERE / "questions.jsonl"
PARQUET = PROJECT_ROOT / "outputs" / "literature_review_enriched.parquet"
POOL_DEPTH = 10
CAT_ORDER = {"known_answer": 0, "exact_term": 1, "unanswerable": 2, "assessor": 3}


def clean_id(s) -> str:
    s = str(s)
    return s[:-2] if s.endswith(".0") else s


def load_questions(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def text_dup_groups(index_dir: Path) -> dict[str, str]:
    """literature_id -> canonical id (lowest) of its byte-identical-text group,
    measured by hashing the index's chunks_meta.jsonl (same instrument as run_eval)."""
    import hashlib
    hashers: dict[str, "hashlib._Hash"] = {}
    with open(index_dir / "chunks_meta.jsonl", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            hashers.setdefault(clean_id(c["literature_id"]), hashlib.sha1()).update(
                (c.get("text") or "").encode("utf-8", "ignore"))
    by_sha: dict[str, list[str]] = {}
    for lid, h in hashers.items():
        by_sha.setdefault(h.hexdigest(), []).append(lid)
    out = {}
    for ids in by_sha.values():
        if len(ids) > 1:
            canon = min(ids, key=lambda s: (len(s), s))
            for i in ids:
                out[i] = canon
    return out


def pool_rows(questions: list[dict], runs: dict[str, dict], depth: int = POOL_DEPTH,
              canon: dict[str, str] | None = None) -> list[dict]:
    """One row per unjudged (question, candidate). Candidates whose indexed
    text is identical (`canon` maps id -> group canonical id) share ONE row;
    the other ids go in `also_ids` and receive the same decision. Pure."""
    canon = canon or {}
    by_q = {name: {r["id"]: r for r in res["questions"]} for name, res in runs.items()}
    rows = []
    for q in questions:
        if q.get("status") == "dropped":
            continue
        judged = {clean_id(k) for k in (q.get("judgements") or {})}
        silver = {clean_id(x) for x in q.get("relevant_ids") or []}
        cands: dict[str, dict] = {}
        for name, qmap in by_q.items():
            r = qmap.get(q["id"])
            if not r:
                continue
            for rank, p in enumerate(r["ranked_papers"][:depth], start=1):
                key = canon.get(p["literature_id"], p["literature_id"])
                c = cands.setdefault(key, {"ranks": {}, "ce": None, "cos": None,
                                           "title": p.get("title"), "ids": set()})
                c["ids"].add(p["literature_id"])
                c["ranks"][name] = min(rank, c["ranks"].get(name, rank))
                if p.get("ce") is not None:
                    c["ce"] = p["ce"] if c["ce"] is None else max(c["ce"], p["ce"])
                if p.get("cosine") is not None:
                    c["cos"] = p["cosine"] if c["cos"] is None else max(c["cos"], p["cosine"])
        for lid in silver:
            key = canon.get(lid, lid)
            cands.setdefault(key, {"ranks": {}, "ce": None, "cos": None, "title": None,
                                   "ids": set()})["ids"].add(lid)
        for key, c in cands.items():
            ids = c["ids"] or {key}
            if ids <= judged:
                continue
            silver_hit = sorted(ids & silver)
            lid = silver_hit[0] if silver_hit else min(ids, key=lambda s: (len(s), s))
            also = sorted(ids - {lid}, key=lambda s: (len(s), s))
            if silver_hit:
                why = ("target paper of a known-answer question" if q["category"] == "known_answer"
                       else "body text contains the term verbatim")
                proposal = f"Y (silver: {why})"
            elif q["category"] == "unanswerable":
                proposal = "N unless it really answers the question (question believed unanswerable)"
            else:
                proposal = "judge"
            rows.append({
                "question_id": q["id"], "category": q["category"], "question": q["question"],
                "literature_id": lid, "also_ids": also, "title": c["title"],
                "ranks": c["ranks"], "best_ce": c["ce"], "best_cosine": c["cos"],
                "retrieved": bool(c["ranks"]), "proposal": proposal,
            })
    rows.sort(key=lambda r: (CAT_ORDER.get(r["category"], 9), r["question_id"],
                             min(r["ranks"].values()) if r["ranks"] else 99))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--index-name", default="rag")
    ap.add_argument("--eval-dir", default=str(EVAL_DIR))
    ap.add_argument("--questions", default=str(QUESTIONS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--index-dir", default=None,
                    help="index the run used (default outputs/<index-name>); its chunk texts "
                         "are hashed so duplicate papers share one row")
    args = ap.parse_args()

    eval_dir = Path(args.eval_dir)
    runs = {}
    for cfg in ("vector", "vector_ce", "hybrid_ce"):
        p = eval_dir / f"{args.date}_{args.index_name}_{cfg}.json"
        if p.exists():
            runs[cfg] = json.loads(p.read_text(encoding="utf-8"))
    if not runs:
        raise SystemExit(f"no run files for {args.date}_{args.index_name}_*.json in {eval_dir}")
    questions = load_questions(Path(args.questions))
    index_dir = Path(args.index_dir) if args.index_dir else PROJECT_ROOT / "outputs" / args.index_name
    canon = text_dup_groups(index_dir) if (index_dir / "chunks_meta.jsonl").exists() else {}
    rows = pool_rows(questions, runs, canon=canon)

    meta = pd.read_parquet(PARQUET, columns=["literature_id", "title", "year", "journal", "doi", "abstract"])
    meta["literature_id"] = meta["literature_id"].map(clean_id)
    meta = meta.drop_duplicates("literature_id").set_index("literature_id")

    out = Path(args.out) if args.out else eval_dir / f"{args.date}_question_adjudication.xlsx"
    wb = Workbook()
    info = wb.active
    info.title = "Info"
    n_q = len({r["question_id"] for r in rows})
    info_lines = [
        ("SharkOracle retrieval evaluation: relevance adjudication (SILVER labels to confirm)", True),
        ("", False),
        ("Why this workbook exists", True),
        ("The query interface's retrieval has never been measured. A baseline needs a question set with "
         "known relevant papers. The questions and their current relevance labels were written by Claude "
         "(silver); this workbook turns them into adjudicated labels.", False),
        ("", False),
        ("What was done automatically", True),
        (f"85 questions written (scripts/rag/eval/questions.jsonl): 30 known-answer (from the human-gold and "
         f"silver validation-sample papers), 20 exact-term (species, places, methods found verbatim in the "
         f"text cache), 20 assessor-style, 15 believed unanswerable.", False),
        (f"Every question was run through {', '.join(runs)} on index '{args.index_name}' "
         f"({args.date}); each config's top {POOL_DEPTH} papers were pooled, and any silver-relevant paper "
         f"no config found was added. {len(rows)} (question, paper) pairs from {n_q} questions need a "
         f"decision; pairs already decided in questions.jsonl are not shown.", False),
        ("Rows are ordered easy to hard: known-answer confirmations first, then exact-term, then "
         "unanswerable (mostly N), then assessor questions (real judgement).", False),
        ("", False),
        ("Tabs", True),
        ("judgements: one row per (question, candidate paper). 'also_ids' lists other literature_ids whose indexed "
         "text is identical (duplicate records); your decision applies to all of them. Columns: question, paper metadata, a DOI link, "
         "the abstract (truncated), the rank each config gave the paper (blank = not in that config's top 10), "
         "the best cross-encoder score (above 0 = the reranker thought it relevant), the proposal, then your decision.", False),
        ("questions: every question with its status, provenance and silver relevant_ids, with two editable columns.", False),
        ("", False),
        ("What to do", True),
        ("1. judgements tab: for each row, read the question and the abstract, and put Y, N, or partial in "
         "'relevant'. Y = this paper answers (or directly bears on) the question; partial = related evidence "
         "that would help but does not answer it; N = not relevant. Use 'notes' for anything worth keeping.", False),
        ("2. Rows whose proposal starts 'Y (silver' are labels Claude already assumed; confirm or overrule them.", False),
        ("3. Unanswerable questions: if ANY paper is Y, the question is answerable after all; say so in notes.", False),
        ("4. Leave a row blank if you cannot judge it; it will be served again next round, nothing else changes.", False),
        ("5. questions tab (optional): type replacement wording in 'new_wording', or Y in 'drop' to retire a question.", False),
        ("6. Save the file and tell Claude, or run: python3 scripts/rag/eval/apply_adjudication.py <this file> --judge <your initials>. "
         "That writes the decisions into questions.jsonl; re-run run_eval.py for adjudicated numbers.", False),
        ("", False),
        ("Provenance", True),
        (f"Generated {dt.datetime.now():%Y-%m-%d %H:%M} by scripts/rag/eval/build_adjudication.py from "
         f"{', '.join(str(eval_dir / f'{args.date}_{args.index_name}_{c}.json') for c in runs)}. "
         "Metadata and abstracts from outputs/literature_review_enriched.parquet. Known gaps: the live index "
         "holds about 3,000 duplicate texts, so a paper and its duplicate can both appear for one question; "
         "the questions were written by the builder's assistant, not independent assessors.", False),
    ]
    for i, (text, bold) in enumerate(info_lines, start=1):
        c = info.cell(row=i, column=1, value=text)
        c.font = Font(bold=bold, size=12 if i == 1 else 11)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    info.column_dimensions["A"].width = 120

    ws = wb.create_sheet("judgements")
    cfgs = list(runs)
    header = (["question_id", "category", "question", "literature_id", "also_ids", "title", "year", "journal", "doi",
               "abstract"] + [f"rank_{c}" for c in cfgs] +
              ["best_ce", "notes", "proposal", "relevant"])
    ws.append(header)
    for r in rows:
        m = meta.loc[r["literature_id"]] if r["literature_id"] in meta.index else None
        doi = (m["doi"] if m is not None else None) or None
        abstract = (m["abstract"] if m is not None else None) or ""
        year = m["year"] if m is not None else None
        try:
            year = int(float(year))
        except (TypeError, ValueError):
            year = None
        ws.append([
            r["question_id"], r["category"], r["question"], r["literature_id"],
            ", ".join(r["also_ids"]) or None,
            (m["title"] if m is not None else None) or r["title"], year,
            m["journal"] if m is not None else None,
            None, str(abstract)[:600],
            *[r["ranks"].get(c) for c in cfgs],
            round(r["best_ce"], 2) if r["best_ce"] is not None else None,
            None, r["proposal"], None,
        ])
        if doi:
            cell = ws.cell(row=ws.max_row, column=header.index("doi") + 1)
            cell.value = f'=HYPERLINK("https://doi.org/{doi}","doi")'
            cell.font = Font(color="0563C1", underline="single")
    widths = {"question_id": 8, "category": 11, "question": 45, "literature_id": 9, "also_ids": 9, "title": 45,
              "year": 6, "journal": 18, "doi": 5, "abstract": 60, "best_ce": 7, "notes": 20,
              "proposal": 22, "relevant": 9}
    for i, h in enumerate(header, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = widths.get(h, 8)
        ws.cell(row=1, column=i).font = Font(bold=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=header[c.column - 1] in ("question", "title", "proposal"))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    dec_col = ws.cell(row=1, column=len(header)).column_letter
    dv = DataValidation(type="list", formula1='"Y,N,partial"', allow_blank=True)
    ws.add_data_validation(dv)
    if rows:
        dv.add(f"{dec_col}2:{dec_col}{len(rows) + 1}")
    fill = PatternFill("solid", fgColor="FFF2CC")
    for r in range(2, len(rows) + 2):
        ws[f"{dec_col}{r}"].fill = fill

    qs = wb.create_sheet("questions")
    qh = ["id", "category", "status", "question", "relevant_ids", "provenance", "new_wording", "drop"]
    qs.append(qh)
    for q in questions:
        qs.append([q["id"], q["category"], q.get("status"), q["question"],
                   ", ".join(q.get("relevant_ids") or []), q.get("provenance"), None, None])
    for i, (h, w) in enumerate(zip(qh, (7, 12, 14, 60, 22, 60, 40, 6)), start=1):
        qs.column_dimensions[qs.cell(row=1, column=i).column_letter].width = w
        qs.cell(row=1, column=i).font = Font(bold=True)
    qs.freeze_panes = "A2"
    qs.auto_filter.ref = qs.dimensions

    wb.save(out)
    print(f"{len(rows)} rows from {n_q} questions -> {out}")


if __name__ == "__main__":
    main()
