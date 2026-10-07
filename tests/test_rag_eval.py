"""Tests for the retrieval evaluation harness (scripts/rag/eval/).

    /home/simon/.venvs/fashion-clip/bin/python -m pytest tests/test_rag_eval.py -q

Pure-function tests need nothing; the integration test loads outputs/rag_test
(never the live index) and the two small CPU models.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts" / "rag" / "eval"
sys.path.insert(0, str(EVAL))

import run_eval as rv  # noqa: E402
import apply_adjudication as aa  # noqa: E402
import build_adjudication as ba  # noqa: E402

RAG_TEST = ROOT / "outputs" / "rag_test"


# --- metrics ---------------------------------------------------------------

def test_metrics_single_relevant_at_rank_3():
    m = rv.question_metrics(["a", "b", "c", "d"], {"c"})
    assert m["hit@1"] == 0 and m["hit@5"] == 1 and m["hit@10"] == 1
    assert m["MRR"] == pytest.approx(1 / 3)
    assert m["P@10"] == pytest.approx(0.1)
    assert m["R@10"] == 1.0
    assert m["nDCG@10"] == pytest.approx(1 / math.log2(4))


def test_metrics_miss_and_partial_gain():
    m = rv.question_metrics(["x", "p"], {"r"}, partial={"p"})
    assert m["hit@20"] == 0 and m["MRR"] == 0 and m["R@10"] == 0
    # partial earns nDCG credit only: gain 0.5 at rank 2; ideal = 1 at rank 1 + 0.5 at rank 2
    ideal = 1 + 0.5 / math.log2(3)
    assert m["nDCG@10"] == pytest.approx((0.5 / math.log2(3)) / ideal)


def test_metrics_shown_flag():
    m = rv.question_metrics(["a", "b"], {"b"}, shown={"a"})
    assert m["hit@shown"] == 0.0
    m = rv.question_metrics(["a", "b"], {"b"}, shown={"a", "b"})
    assert m["hit@shown"] == 1.0


def test_dedupe_to_papers_first_occurrence_and_best_scores():
    hits = [{"literature_id": "1", "score": 0.5, "ce_score": 2.0},
            {"literature_id": "2.0", "score": 0.9, "ce_score": 1.0},
            {"literature_id": "1", "score": 0.7, "ce_score": -1.0}]
    p = rv.dedupe_to_papers(hits)
    assert [x["literature_id"] for x in p] == ["1", "2"]
    assert p[0]["cosine"] == 0.7 and p[0]["ce"] == 2.0 and p[0]["n_chunks"] == 2
    assert p[1]["first_chunk_rank"] == 2


def test_expand_dups_credits_shared_pdf():
    groups = {"10": {"11"}, "11": {"10"}}
    assert rv.expand_dups({"10"}, groups) == {"10", "11"}
    m = rv.question_metrics(["11"], rv.expand_dups({"10"}, groups))
    assert m["hit@1"] == 1


def test_dup_groups_from_text():
    g = rv.dup_groups_from_text({"1": "h", "2": "h", "3": "k"})
    assert g == {"1": {"2"}, "2": {"1"}}


def test_aggregate_means():
    rows = [{"metrics": {"hit@1": 1.0}}, {"metrics": {"hit@1": 0.0}}]
    assert rv.aggregate(rows)["hit@1"] == 0.5


def test_questions_file_targets_and_schema():
    qs = rv.load_questions(EVAL / "questions.jsonl")
    from collections import Counter
    c = Counter(q["category"] for q in qs)
    assert c["known_answer"] >= 30 and c["exact_term"] >= 20
    assert c["assessor"] >= 20 and c["unanswerable"] >= 15
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids))
    for q in qs:
        assert {"id", "category", "question", "relevant_ids", "provenance", "status"} <= set(q)
        assert q["status"] in {"silver", "needs_judgement", "adjudicated", "dropped"}
        if q["category"] in ("known_answer", "exact_term"):
            assert q["relevant_ids"], q["id"]
            assert len(q["relevant_ids"]) <= 10


# --- adjudication round trip -------------------------------------------------

def _qs():
    return [{"id": "KA01", "category": "known_answer", "question": "q1",
             "relevant_ids": ["5"], "status": "silver", "provenance": "x"},
            {"id": "UN01", "category": "unanswerable", "question": "q2",
             "relevant_ids": [], "status": "needs_judgement", "provenance": "x"}]


def test_pool_rows_skips_judged_and_adds_unretrieved_silver():
    qs = _qs()
    runs = {"vector": {"questions": [
        {"id": "KA01", "ranked_papers": [{"literature_id": "7", "ce": None, "cosine": 0.8}]},
        {"id": "UN01", "ranked_papers": [{"literature_id": "8", "ce": -3.0, "cosine": 0.7}]}]}}
    rows = ba.pool_rows(qs, runs)
    pairs = {(r["question_id"], r["literature_id"]) for r in rows}
    assert pairs == {("KA01", "7"), ("KA01", "5"), ("UN01", "8")}
    silver = [r for r in rows if r["literature_id"] == "5"][0]
    assert not silver["retrieved"] and silver["proposal"].startswith("Y (silver")
    qs[0]["judgements"] = {"7": {"label": "N"}}
    pairs = {(r["question_id"], r["literature_id"]) for r in ba.pool_rows(qs, runs)}
    assert ("KA01", "7") not in pairs


def test_pool_rows_collapses_text_duplicates_and_apply_spreads():
    qs = _qs()
    runs = {"vector": {"questions": [
        {"id": "KA01", "ranked_papers": [{"literature_id": "50", "ce": 1.0, "cosine": 0.8},
                                         {"literature_id": "5", "ce": 0.5, "cosine": 0.7}]}]}}
    rows = [r for r in ba.pool_rows(qs, runs, canon={"5": "5", "50": "5"}) if r["question_id"] == "KA01"]
    assert len(rows) == 1 and rows[0]["literature_id"] == "5" and rows[0]["also_ids"] == ["50"]
    aa.apply(qs, [{"question_id": "KA01", "literature_id": "5", "also_ids": "50", "relevant": "Y"}],
             [], "SD", "d")
    assert set(qs[0]["relevant_ids"]) == {"5", "50"} and set(qs[0]["judgements"]) == {"5", "50"}


def test_apply_decisions_and_edits():
    qs = _qs()
    judg = [{"question_id": "KA01", "literature_id": 5, "relevant": "y", "notes": None},
            {"question_id": "KA01", "literature_id": "7", "relevant": "partial", "notes": "close"},
            {"question_id": "UN01", "literature_id": "8", "relevant": None},
            {"question_id": "UN01", "literature_id": "9", "relevant": "maybe"}]
    edits = [{"id": "UN01", "new_wording": "q2 better", "drop": None}]
    c = aa.apply(qs, judg, edits, "SD", "2026-10-07")
    assert c["Y"] == 1 and c["partial"] == 1 and c["blank"] == 1 and c["invalid"] == 1
    assert qs[0]["relevant_ids"] == ["5"] and qs[0]["partial_ids"] == ["7"]
    assert qs[0]["status"] == "adjudicated"
    assert qs[0]["judgements"]["7"]["notes"] == "close"
    assert qs[1]["question"] == "q2 better" and qs[1]["previous_wording"] == "q2"
    # N removes a previously relevant id
    aa.apply(qs, [{"question_id": "KA01", "literature_id": "5", "relevant": "N"}], [], "SD", "d")
    assert qs[0]["relevant_ids"] == []
    aa.apply(qs, [], [{"id": "KA01", "drop": "Y"}], "SD", "d")
    assert qs[0]["status"] == "dropped"


# --- integration against the 200-paper test index ---------------------------

@pytest.mark.skipif(not (RAG_TEST / "index.faiss").exists(), reason="rag_test not built")
def test_run_config_on_rag_test():
    first = json.loads((RAG_TEST / "chunks_meta.jsonl").open().readline())
    lid = rv.clean_id(first["literature_id"])
    # a passage from the paper's own first chunk (titles are not in the body-only text)
    passage = " ".join(first["text"].split()[40:80])
    qs = [{"id": "T1", "category": "known_answer", "question": passage,
           "relevant_ids": [lid], "status": "silver"},
          {"id": "T2", "category": "unanswerable",
           "question": "CRISPR gene editing protocols for shark embryos",
           "relevant_ids": [], "status": "needs_judgement"}]
    eng = rv.Engine(RAG_TEST, RAG_TEST / "fts.sqlite")
    indexed = set(eng.meta)
    res = rv.run_config(eng, "vector", qs, {}, indexed)
    t1 = res["questions"][0]
    assert t1["n_relevant_indexed"] == 1
    assert t1["metrics"]["hit@5"] == 1.0          # its own passage finds it
    assert res["by_category"]["unanswerable"]["n_judged"] == 0
    res_ce = rv.run_config(eng, "vector_ce", qs[1:], {}, indexed)
    assert res_ce["questions"][0]["badge_top8"] in {"unresolved", "limited", "well-supported"}
    assert res_ce["by_category"]["unanswerable"]["frac_unresolved_top8"] is not None
