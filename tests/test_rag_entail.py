"""Tests for scripts/rag/entailment.py (CPU NLI model; no Ollama, no live server)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "rag"))
import entailment as e  # noqa: E402


def H(i, text, ce=2.0):
    return {"literature_id": i, "text": text, "ce_score": ce}


def test_split_sentences_citations():
    a = ("Vertebral bands are used to age sharks [12]. Bands may fail in old animals [12, 15]. "
         "Sharks are fish. See Smith et al. 2010 for detail [9].\n- Bullet point claim [3]")
    s = e.split_sentences(a)
    assert [x["citations"] for x in s] == [[12], [12, 15], [], [9], [3]]
    assert s[3]["text"].startswith("See Smith et al. 2010")
    assert e.split_sentences("") == []


def test_citation_after_full_stop():
    s = e.split_sentences("Sharks are aged using vertebrae. [12] Rays differ. [7, 8]")
    assert [x["citations"] for x in s] == [[12], [7, 8]]


def test_entailed_contradicted_neutral():
    hits = [H(12, "Sharks are aged by counting growth bands in vertebrae."),
            H(9, "Vertebral bands cannot be used to age sharks.")]
    ent = e.score_sentences(e.split_sentences(
        "Vertebral bands are used to age sharks [12]."), hits[:1])[0]
    assert ent["support"] == "entailed" and ent["best_support_id"] == 12
    con = e.score_sentences(e.split_sentences(
        "Vertebral bands are used to age sharks [12]."), hits)[0]
    assert con["support"] == "contradicted" and con["contradicted_by"] == [9]
    neu = e.score_sentences(e.split_sentences(
        "Female sharks mature later than males [12]."), hits[:1])[0]
    assert neu["support"] == "neutral"


def test_irrelevant_chunk_cannot_contradict():
    hits = [H(15, "The cat sat on the mat.", ce=-3.0)]
    r = e.score_sentences(e.split_sentences("Sharks are aged using vertebrae [15]."), hits)[0]
    assert r["support"] != "contradicted"


def test_uncited_and_bounds():
    hits = [H(i, "Sharks are aged by counting growth bands in vertebrae.") for i in range(12)]
    sents = e.split_sentences(" ".join("Sharks are aged by counting growth bands in vertebrae." for i in range(12)))
    r = e.score_sentences(sents, hits)
    assert len(r) == 12 and sum(1 for x in r if x.get("not_scored")) == 4
    assert all(len(x["pairs"]) <= e.MAX_CHUNKS for x in r)
    # identical chunk text entails the uncited sentence: grounded but attributed,
    # not "uncited" (2026-10-07: small local LLMs rarely emit [id] citations)
    assert r[0]["support"] == "entailed" and r[0]["attributed"] is True
    assert r[0]["best_support_id"] is not None
    none_hits = [H(i, "Water temperature was recorded hourly at three depths.") for i in range(3)]
    r2 = e.score_sentences(e.split_sentences("Sharks are aged by counting growth bands in vertebrae."), none_hits)
    assert r2[0]["support"] in ("uncited", "neutral") and r2[0]["attributed"] is False


def test_normalise_citations_maps_author_year_to_ids():
    hits = [{"literature_id": "101", "authors": "Casey, J. G.; Pratt, H. L.", "year": 1985.0, "text": ""},
            {"literature_id": "303", "authors": "Smith, A.", "year": 2001, "text": ""},
            {"literature_id": "304", "authors": "Smith, B.", "year": 2001, "text": ""}]
    out = e.normalise_citations("Bands are counted (Casey et al., 1985). Smith et al. 2001 agree. Casey et al. 1985 [101].", hits)
    assert out.count("[101]") == 2          # appended once, existing citation left alone
    assert "[303]" not in out and "[304]" not in out   # ambiguous surname+year untouched


def _fake(support, cites, by=(), contra=()):
    return {"text": "x", "citations": cites, "support": support, "entailed_by": list(by),
            "contradicted_by": list(contra), "best_support_id": None, "pairs": []}


def test_rating_logic():
    c = e.claim_strength_entailment
    well = c([_fake("entailed", [1], [1, 2]), _fake("entailed", [3], [3])], [])
    assert well["label"] == "well-supported" and well["n_entailing_papers"] == 3
    assert well["groundedness"] == 1.0
    assert c([_fake("entailed", [1], [1])], [])["label"] == "limited"
    assert c([_fake("neutral", [1])], [])["label"] == "unresolved"
    con = c([_fake("contradicted", [1], [1, 2, 3], [9])], [])
    assert con["label"] == "contested" and "9" in con["reason"] and con["contested"][0]["contradicted_by"] == [9]
    assert c([], [])["label"] == "unresolved"


def test_contradiction_needs_shared_content_words():
    hits = [H(9, "Cats cannot swim in cold water and dislike it.")]
    r = e.score_sentences(e.split_sentences("Vertebral bands are used to age sharks [12]."), hits)[0]
    assert r["support"] != "contradicted"
