"""Reference export (BibTeX / RIS / styles) and the matched-terms helper."""
import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "outputs" / "rag_test"
os.environ["RAG_OUT_DIR"] = str(TEST_DIR)
sys.path.insert(0, str(ROOT / "scripts" / "rag"))

import export_refs as ex  # noqa: E402
import hybrid  # noqa: E402


@pytest.mark.parametrize("raw,want", [
    ("Dedman, S.; Tiktak, G.", [("Dedman", "S."), ("Tiktak", "G.")]),
    ("Smith J & Jones K", [("Smith", "J."), ("Jones", "K.")]),
    ("Fernández-Corredor, E.", [("Fernández-Corredor", "E.")]),
    ("Rodriguez-Cabello, C. & de La Gandara, F. (1998)",
     [("Rodriguez-Cabello", "C."), ("de La Gandara", "F.")]),
    ("Smith J, Jones KL", [("Smith", "J."), ("Jones", "K. L.")]),
    ("", []), (None, []),
])
def test_parse_authors(raw, want):
    assert ex.parse_authors(raw) == want


@pytest.fixture(scope="module")
def client():
    if not (TEST_DIR / "chunks_meta.jsonl").exists():
        pytest.skip("outputs/rag_test not built")
    from fastapi.testclient import TestClient
    import serve
    return TestClient(serve.app)  # no `with`: skips model loading


@pytest.fixture(scope="module")
def ids():
    out = []
    for line in open(TEST_DIR / "chunks_meta.jsonl", encoding="utf-8"):
        lid = str(json.loads(line)["literature_id"])
        if lid not in out:
            out.append(lid)
        if len(out) == 3:
            break
    return out


def test_bibtex_well_formed(client, ids):
    r = client.get("/api/export", params={"ids": ",".join(ids), "fmt": "bibtex"})
    assert r.status_code == 200 and "bibtex" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    entries = re.findall(r"@(?:article|misc)\{([A-Za-z0-9]+),\n((?:  \w+ = \{.*\},?\n)+)\}", r.text)
    assert len(entries) == 3
    keys = [k for k, _ in entries]
    assert len(set(keys)) == 3
    for _, body in entries:
        assert re.search(r"^  title = \{", body, re.M) and re.search(r"^  year = \{\d{4}\}", body, re.M)


def test_ris_well_formed(client, ids):
    r = client.get("/api/export", params={"ids": ",".join(ids), "fmt": "ris"})
    assert r.status_code == 200 and "research-info" in r.headers["content-type"]
    lines = r.text.splitlines()
    assert sum(l.startswith("ER  -") for l in lines) == 3
    assert sum(l.startswith("TY  - JOUR") for l in lines) == 3
    assert sum(l.startswith("TI  - ") for l in lines) == 3


def test_styles_and_other_formats(client, ids):
    for fmt in ("csv", "json", "apa", "harvard", "vancouver", "chicago", "mla"):
        r = client.get("/api/export", params={"ids": ids[0], "fmt": fmt})
        assert r.status_code == 200 and r.text.strip(), fmt
    apa = client.get("/api/export", params={"ids": ids[0], "fmt": "apa"}).text
    assert re.search(r"\(\d{4}\)\.", apa)
    assert len(client.get("/api/export", params={"ids": ",".join(ids), "fmt": "mla"}).text.strip().splitlines()) == 3


def test_unknown_id_ignored_and_errors(client, ids):
    r = client.get("/api/export", params={"ids": f"{ids[0]},999999999", "fmt": "ris"})
    assert r.status_code == 200 and r.text.count("ER  -") == 1
    assert client.get("/api/export", params={"ids": "", "fmt": "ris"}).status_code == 400
    assert client.get("/api/export", params={"fmt": "ris"}).status_code == 400
    assert client.get("/api/export", params={"ids": ids[0], "fmt": "nope"}).status_code == 400
    assert client.get("/api/export", params={"ids": "999999999", "fmt": "ris"}).status_code == 404


def test_bibtex_key_dedup():
    rows = [{"literature_id": "1", "title": "The Shark", "authors": "Smith, J. (2001)", "year": 2001},
            {"literature_id": "2", "title": "A shark again", "authors": "Smith, J. (2001)", "year": 2001}]
    keys = re.findall(r"@(?:article|misc)\{(\w+),", ex.render(rows, "bibtex"))
    assert keys[0] == "Smith2001Shark" and len(set(keys)) == 2


def test_matched_terms():
    assert hybrid.matched_terms("clownfish", "A giant bull shark was caught") == []
    got = hybrid.matched_terms("bull sharks in Chennai", "The Bull shark at Chennai coast")
    assert "Chennai" in got and "sharks" in got
