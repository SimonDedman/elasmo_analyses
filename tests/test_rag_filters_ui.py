"""Shark Oracle filter panel: labels, removed/blank options, /api/papers browse mode.
Runs without loading models: serve.S is filled by hand and the app is used
WITHOUT the lifespan context, against the sidecar in outputs/rag_test."""
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("RAG_OUT_DIR", str(ROOT / "outputs" / "rag_test"))
sys.path.insert(0, str(ROOT / "scripts" / "rag"))

import labels  # noqa: E402

SIDECAR = Path(os.environ["RAG_OUT_DIR"]) / "paper_filters.parquet"


def test_label_for_acronyms_and_names():
    assert labels.label_for("a_akde") == "AKDE (autocorrelated kernel density estimation)"
    assert labels.label_for("a_cpue") == "CPUE (catch per unit effort)"
    assert labels.label_for("imp_cpue") == "CPUE (catch per unit effort)"
    assert labels.label_for("a_edna") == "eDNA (environmental DNA)"
    assert labels.label_for("a_age_&_growth") == "Age & Growth"
    assert labels.label_for("b_north_atlantic") == "North Atlantic"
    assert labels.label_for("sb_gulf_of_mexico") == "Gulf of Mexico"
    assert labels.label_for("sb_sea_of_japan") == "Sea of Japan"


def test_epoch_and_oa_order():
    assert labels.epoch_label("rezent") == "Recent"
    vals = ["Cambrian", "Miocene", "rezent", "Maastrichtian", "Late Jurassic", "Holocene"]
    assert sorted(vals, key=labels.epoch_rank)[:5] == [
        "rezent", "Holocene", "Miocene", "Late Jurassic", "Cambrian"]
    assert sorted(["closed", "gold", "green", "diamond", "bronze", "hybrid"],
                  key=labels.oa_rank) == ["diamond", "gold", "hybrid", "green", "bronze", "closed"]


@pytest.fixture(scope="module")
def client():
    if not SIDECAR.exists():
        pytest.skip("run scripts/rag/build_filters.py with RAG_OUT_DIR=outputs/rag_test first")
    import serve
    from fastapi.testclient import TestClient
    from retrieval import build_author_map
    pf = pd.read_parquet(SIDECAR)
    pf["literature_id"] = pf["literature_id"].astype(str)
    serve.S["paper_filters"] = pf.set_index("literature_id")
    serve.S["author_map"] = build_author_map(pd.read_parquet(serve.AUTHOR_INDEX))
    serve.S["author_suggest"] = pd.read_parquet(serve.AUTHOR_SUGGEST)
    serve.S["filters_payload"] = serve._build_filters_payload()
    return TestClient(serve.app)


def test_removed_families_and_options(client):
    fams = {f["key"]: f for f in client.get("/api/filters").json()["families"]}
    for gone in ("superregion", "study_lat", "study_lon"):
        assert gone not in fams
    eco = [o["value"] for o in fams["ecosystem"]["options"]]
    assert not any(v.startswith("eco_") and v.endswith("_guess") for v in eco)
    flags = [o["value"] for o in fams["geo_oa_flags"]["options"]]
    assert "geo_has_study_location" not in flags and "geo_has_author_country" not in flags
    labs = [o["label"] for o in fams["geo_oa_flags"]["options"]]
    assert "Paper is open access" in labs
    assert "Journal listed in DOAJ (Directory of Open Access Journals)" in labs


def test_no_blank_options_and_labels(client):
    fams = client.get("/api/filters").json()["families"]
    for f in fams:
        if f["kind"] == "categorical":
            for o in f["options"]:
                assert not labels.is_blank(o["value"]), (f["key"], o)
    by = {f["key"]: f for f in fams}
    assert "Recent" in [o["label"] for o in by["epoch"]["options"]]
    assert "AKDE (autocorrelated kernel density estimation)" in [
        o["label"] for o in by["technique"]["options"]]
    assert "Coauthor-contributed library" in [o["label"] for o in by["data_source"]["options"]]
    assert by["oa_status"]["sorts"][1]["id"] == "best"


def test_papers_author_filter_sorted(client):
    import serve
    sug = serve.S["author_suggest"].iloc[0]
    r = client.post("/api/papers", json={"filters": {"author": [sug.openalex_author_id]}})
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 0 and d["papers"]
    years = [p["year"] for p in d["papers"] if p["year"] is not None]
    assert years == sorted(years, reverse=True)
    assert set(d["papers"][0]) >= {"literature_id", "title", "authors", "year", "journal", "doi"}


def test_papers_no_filters_400(client):
    assert client.post("/api/papers", json={"filters": {}}).status_code == 400


def test_country_record_only_real_countries(client):
    fams = {f["key"]: f for f in client.get("/api/filters").json()["families"]}
    fam = fams["country_record"]
    vals = {o["value"] for o in fam["options"]}
    for bad in ("Mediterranean", "North America", "Kansas", "Europe", "Antarctica", "Georgia", "Alberta"):
        assert bad not in vals
    for good in ("Germany", "United Kingdom", "Japan"):
        assert good in vals
    from filter_config import is_country
    assert all(is_country(v) for v in vals)
    assert "Countries only" in fam["note"] and "Sub-basin" in fam["note"]
    assert {o["label"] for o in fam["options"]} >= {"Tunisia"}
