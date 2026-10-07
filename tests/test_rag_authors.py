"""RAG author autocomplete (scripts/rag/author_match.py), ported from
tests/test_validate_author_search.py (the validation page's JS matcher)."""
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_OUT = ROOT / "outputs" / "rag_test"
os.environ.setdefault("RAG_OUT_DIR", str(TEST_OUT))
sys.path.insert(0, str(ROOT / "scripts" / "rag"))

import author_match as am  # noqa: E402

ROWS = [
    ("A5027778174", "Elena Fernández‐Corredor", 4),
    ("A5000000001", "Elena Fernández", 2),
    ("A5000000002", "María Elena Fernández Collazo", 1),
    ("A5086753224", "Nicholas K. Dulvy", 120),
    ("A5000000003", "José M. Eirín‐López", 9),
    ("A5000000004", "Nimet Selda Başçınar", 3),
    ("A5000000005", "Toshihiko Satō", 5),
]
FIXTURE = pd.DataFrame(ROWS, columns=["openalex_author_id", "display_name", "paper_count"])
ELENA = "A5027778174"


def ids(query, frame=FIXTURE, limit=10):
    return [r.openalex_author_id for r in am.match(query, frame, limit)]


def test_fold_and_tokens():
    assert am.fold("Elena Fernández‐Corredor") == "elena fernandez-corredor"
    assert am.tokens("Elena Fernández‐Corredor") == ["elena", "fernandez", "corredor"]
    assert am.fold("Başçınar") == "bascinar"
    assert am.fold("Łukasz Øster Straße") == "lukasz oster strasse"
    assert am.fold(None) == ""


def test_norm_name_delegates():
    import retrieval
    import build_filters
    assert retrieval.norm_name("Eirín‐López") == am.fold("Eirín‐López") == "eirin-lopez"
    assert build_filters.norm_name("Eirín‐López") == "eirin-lopez"


@pytest.mark.parametrize("query", [
    "Elena Fernández‐Corredor", "Elena Fernández-Corredor", "Elena Fernandez-Corredor",
    "Elena Fernandez Corredor", "Fernández-Corredor Elena", "Corredor Elena",
    "Fernandez Corredor", "Elena Fernández-Co", "corredor",
])
def test_elena_found_first(query):
    assert ids(query)[0] == ELENA, query


@pytest.mark.parametrize("query", ["elena fern", "Elena", "fernandez", "Elena Fernán"])
def test_elena_present_for_ambiguous_prefixes(query):
    assert ELENA in ids(query), query


def test_exact_name_ranks_before_longer_names():
    got = ids("Elena Fernández")
    assert got[0] == "A5000000001"
    assert set(got) == {ELENA, "A5000000001", "A5000000002"}


def test_whole_token_beats_prefix_and_ties_use_paper_count():
    df = pd.DataFrame([("a", "Ann Smithson", 50), ("b", "Ann Smith", 1),
                       ("c", "Ann Smyth", 9)],
                      columns=["openalex_author_id", "display_name", "paper_count"])
    assert ids("Ann Smith", df)[:2] == ["b", "a"]
    df2 = pd.DataFrame([("a", "Jo Lee", 1), ("b", "Jo Lea", 7)],
                       columns=["openalex_author_id", "display_name", "paper_count"])
    assert ids("Jo Le", df2) == ["b", "a"]


@pytest.mark.parametrize("query,expected", [
    ("Eirin-Lopez", "A5000000003"), ("jose eirin lopez", "A5000000003"),
    ("Bascinar", "A5000000004"), ("Basçınar Selda", "A5000000004"),
    ("Toshihiko Sato", "A5000000005"), ("Dulvy", "A5086753224"),
    ("N. K. Dulvy", "A5086753224"),
])
def test_accent_and_order_folding(query, expected):
    assert ids(query)[0] == expected, query


def test_no_match_and_short_query():
    assert ids("Zzyzx Quux") == []
    assert ids("E") == []


def test_precomputed_columns_agree_with_derived():
    pre = am.add_match_columns(FIXTURE)
    assert ids("Fernandez Corredor", pre) == ids("Fernandez Corredor")


@pytest.mark.skipif(not (TEST_OUT / "author_suggest.parquet").exists(),
                    reason="run build_filters.py with RAG_OUT_DIR=outputs/rag_test first")
def test_api_authors_prefix_query_old_matcher_missed():
    sug = pd.read_parquet(TEST_OUT / "author_suggest.parquet")
    assert {"norm", "tokens"} <= set(sug.columns), "rebuild the test sidecar"
    sug = sug[sug["tokens"].str.split().str.len() >= 3].sort_values("paper_count", ascending=False)
    target = sug.iloc[0]
    toks = target["tokens"].split()
    # Surname first, given-name prefix last: a substring match cannot find this.
    query = f"{toks[-1]} {toks[0][:3]}"
    assert not sug[sug["norm"].str.contains(am.fold(query), regex=False)].shape[0], \
        "old substring matcher would have found it; pick another example"

    from fastapi.testclient import TestClient
    import serve
    serve.S["author_suggest"] = pd.read_parquet(TEST_OUT / "author_suggest.parquet")
    client = TestClient(serve.app)  # no `with`: skips the model-loading lifespan
    r = client.get("/api/authors", params={"q": query, "limit": 50})
    assert r.status_code == 200
    got = r.json()["suggestions"]
    assert target["openalex_author_id"] in [g["id"] for g in got]
    assert set(got[0]) == {"display_name", "id", "paper_count"}
    assert client.get("/api/authors", params={"q": ""}).json() == {"suggestions": []}
