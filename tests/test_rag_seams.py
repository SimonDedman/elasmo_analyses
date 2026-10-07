"""Multi-user seams: LLM backend factory, token auth, query history."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_OUT = ROOT / "outputs" / "rag_test"
os.environ["RAG_OUT_DIR"] = str(TEST_OUT)
sys.path.insert(0, str(ROOT / "scripts" / "rag"))

from fastapi.testclient import TestClient  # noqa: E402

import llm_backend  # noqa: E402
import history  # noqa: E402
import serve  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(serve.app) as c:   # runs lifespan (loads models, ~seconds)
        yield c


@pytest.fixture(autouse=True)
def clean(monkeypatch, tmp_path):
    for k in ("RAG_AUTH_MODE", "RAG_AUTH_TOKENS", "RAG_LLM_BACKEND", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(history.common, "RAG_STATE_DIR", tmp_path)   # isolated history db
    monkeypatch.setattr("auth.common.RAG_STATE_DIR", tmp_path)       # no stray token file
    monkeypatch.setenv("RAG_LLM_BACKEND", "none")                  # never call an LLM


Q = {"question": "age and growth in sharks", "generate": False, "top_k": 3, "retrieve_n": 10}


def test_open_mode_passes_and_records_anonymous(client):
    r = client.post("/api/query", json=Q)
    assert r.status_code == 200
    h = client.get("/api/history").json()
    assert h["client"] == "anonymous"
    assert h["queries"][0]["question"] == Q["question"]
    assert h["queries"][0]["mode"] == "retrieval-only"


def test_token_mode_rejects_missing_and_wrong(client, monkeypatch):
    monkeypatch.setenv("RAG_AUTH_MODE", "token")
    monkeypatch.setenv("RAG_AUTH_TOKENS", "alice:s3cret,bob:other")
    assert client.post("/api/query", json=Q).status_code == 401
    r = client.post("/api/query", json=Q, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and "detail" in r.json()
    assert client.get("/api/history").status_code == 401


def test_token_mode_accepts_both_headers_and_scopes_history(client, monkeypatch):
    monkeypatch.setenv("RAG_AUTH_MODE", "token")
    monkeypatch.setenv("RAG_AUTH_TOKENS", "alice:s3cret,bob:other")
    a = {"Authorization": "Bearer s3cret"}
    b = {"X-SharkOracle-Token": "other"}
    assert client.post("/api/query", json=Q, headers=a).status_code == 200
    q2 = dict(Q, question="eDNA detection of rays")
    assert client.post("/api/query", json=q2, headers=b).status_code == 200
    ha = client.get("/api/history", headers=a).json()
    hb = client.get("/api/history", headers=b).json()
    assert ha["client"] == "alice" and [x["question"] for x in ha["queries"]] == [Q["question"]]
    assert hb["client"] == "bob" and [x["question"] for x in hb["queries"]] == ["eDNA detection of rays"]


def test_token_file(client, monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_AUTH_MODE", "token")
    (tmp_path / "auth_tokens.json").write_text('{"carol": "filetok"}')
    r = client.get("/api/history", headers={"Authorization": "Bearer filetok"})
    assert r.status_code == 200 and r.json()["client"] == "carol"


def test_history_failure_never_breaks_query(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("disk full")
    monkeypatch.setattr(history, "_connect", boom)
    assert client.post("/api/query", json=Q).status_code == 200


def test_backend_factory_default_is_ollama(monkeypatch):
    monkeypatch.delenv("RAG_LLM_BACKEND", raising=False)
    b = llm_backend.get_backend()
    assert isinstance(b, llm_backend.OllamaBackend) and b.name.startswith("ollama:")


def test_anthropic_backend_needs_key(monkeypatch):
    monkeypatch.setenv("RAG_LLM_BACKEND", "anthropic")
    with pytest.raises(llm_backend.BackendError, match="ANTHROPIC_API_KEY"):
        llm_backend.get_backend()
    import query
    assert query.llm_backend_status()[0] is False
    assert query.generate_answer("q", []).startswith("[generation error")


def test_anthropic_backend_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-not-used")
    b = llm_backend.AnthropicBackend()
    assert b.model == "claude-haiku-4-5" and b.name == "anthropic:claude-haiku-4-5"
    monkeypatch.setenv("RAG_LLM_MODEL", "claude-sonnet-5-5")
    assert llm_backend.AnthropicBackend().model == "claude-sonnet-5-5"


def test_unknown_backend_errors(monkeypatch):
    monkeypatch.setenv("RAG_LLM_BACKEND", "bogus")
    with pytest.raises(llm_backend.BackendError):
        llm_backend.get_backend()
