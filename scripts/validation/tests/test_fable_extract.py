import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class _FakeUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeToolUseBlock:
    """Fake tool_use content block: .type == 'tool_use', .input is the dict."""

    def __init__(self, tool_input):
        self.type = "tool_use"
        self.input = tool_input


class _FakeMessage:
    def __init__(self, columns, input_tokens=111, output_tokens=22):
        self.content = [_FakeToolUseBlock({"columns": columns})]
        self.usage = _FakeUsage(input_tokens, output_tokens)


class _StubMessages:
    """Fake .messages namespace: records calls, always returns the same message."""

    def __init__(self, response):
        self._response = response
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return self._response


class _StubClient:
    def __init__(self, response):
        self.messages = _StubMessages(response)


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


def test_schema_column_defs_nonempty():
    """Schema column defs are built from ALL_SCHEMAS (7 SchemaCategory
    objects) with name+description, no network/API needed."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.fable_extract import _schema_column_defs
    cols = _schema_column_defs()
    assert len(cols) > 100
    names = {c["name"] for c in cols}
    assert "eco_pelagic" in names
    sample = next(c for c in cols if c["name"] == "eco_pelagic")
    assert "description" in sample and sample["description"]


def test_pdf_text_resolves_sample_paper():
    """_pdf_text() resolves real PDF text + sha1 for a paper on the
    validation sample list, using only local files (no network)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    from validation.fable_extract import _pdf_text

    sample_csv = ROOT / "outputs/validation/validation_sample.csv"
    if not sample_csv.exists():
        import pytest
        pytest.skip("validation_sample.csv not present")

    sample = pd.read_csv(sample_csv, dtype={"literature_id": str})
    resolved = False
    for lit_id in sample["literature_id"].head(20):
        text, sha1 = _pdf_text(lit_id)
        if text:
            resolved = True
            assert isinstance(sha1, str) and len(sha1) == 40
            assert len(text) > 0
            break
    assert resolved, "expected at least one of the first 20 sample papers to resolve a PDF"


def test_extract_paper_parses_forced_tool_use_and_returns_usage():
    """extract_paper() with a stub client parses the forced tool_use block
    into the expected {name: {present, evidence, confidence}} dict and
    returns the (input_tokens, output_tokens) usage tuple. No network."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.fable_extract import extract_paper

    columns = [{"name": "d_movement", "description": "movement ecology"}]
    fake_message = _FakeMessage(
        [{"name": "d_movement", "present": True, "evidence": "acoustic telemetry",
          "confidence": 0.85}],
        input_tokens=123, output_tokens=45)
    client = _StubClient(fake_message)

    result, usage = extract_paper("paper text goes here", columns, client)

    assert result == {"d_movement": {"present": True, "evidence": "acoustic telemetry",
                                      "confidence": 0.85}}
    assert usage == (123, 45)
    assert client.messages.calls == 1


def test_run_cache_hit_skips_client_and_returns_stored_usage(tmp_path, monkeypatch):
    """A second run() over the same PDF sha must hit the on-disk cache: no
    second call to the stub client, and the token log reports the usage
    stored in the cache (not (0, 0)) on both rows."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    import validation.fable_extract as fe

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(fe, "CACHE", cache_dir)
    monkeypatch.setattr(fe, "OUT", tmp_path)
    monkeypatch.setattr(fe, "_schema_column_defs", lambda: [{"name": "d_movement", "description": "x"}])

    def fake_pdf_text(lit_id):
        if lit_id == "1":
            return ("paper one text", "sha_paper_one")
        return (None, None)

    monkeypatch.setattr(fe, "_pdf_text", fake_pdf_text)

    fake_message = _FakeMessage(
        [{"name": "d_movement", "present": True, "evidence": "e", "confidence": 0.5}],
        input_tokens=100, output_tokens=50)
    client = _StubClient(fake_message)

    # Same literature_id (same PDF -> same sha) appears twice.
    sample = pd.DataFrame({"literature_id": ["1", "1"]})
    fe.run(sample, client=client)

    assert client.messages.calls == 1, "second occurrence should hit the cache, not call the client again"

    toks = pd.read_csv(tmp_path / "fable_token_log.csv", dtype={"literature_id": str})
    assert len(toks) == 2
    assert (toks["input_tokens"] == 100).all()
    assert (toks["output_tokens"] == 50).all(), "cache hit must not undercount tokens as (0, 0)"

    cache_file = cache_dir / "sha_paper_one.json"
    cached = json.loads(cache_file.read_text())
    assert cached["usage"] == [100, 50]
    assert cached["labels"]["d_movement"]["present"] is True


def test_run_cache_hit_backward_compat_old_format_returns_zero_usage(tmp_path, monkeypatch):
    """An old-format cache file (bare labels dict, no 'usage' key) must
    still be read correctly, reporting (0, 0) usage for that cache hit."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    import validation.fable_extract as fe

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(fe, "CACHE", cache_dir)
    monkeypatch.setattr(fe, "OUT", tmp_path)
    monkeypatch.setattr(fe, "_schema_column_defs", lambda: [{"name": "d_movement", "description": "x"}])

    def fake_pdf_text(lit_id):
        return ("paper two text", "sha_paper_two")

    monkeypatch.setattr(fe, "_pdf_text", fake_pdf_text)

    # Pre-seed an old-format cache entry (bare labels dict).
    old_cache = cache_dir / "sha_paper_two.json"
    old_cache.write_text(json.dumps(
        {"d_movement": {"present": False, "evidence": "", "confidence": 0.1}}))

    client = _StubClient(_FakeMessage([]))  # must not be called
    sample = pd.DataFrame({"literature_id": ["2"]})
    fe.run(sample, client=client)

    assert client.messages.calls == 0
    toks = pd.read_csv(tmp_path / "fable_token_log.csv", dtype={"literature_id": str})
    assert toks.iloc[0]["input_tokens"] == 0
    assert toks.iloc[0]["output_tokens"] == 0


def test_run_builds_rows_skips_unresolved_and_normalises_id(tmp_path, monkeypatch):
    """run() on a tiny sample builds correct long-format rows (literature_id,
    column, present, evidence, confidence), skips papers whose _pdf_text
    returns (None, None) without crashing, and normalises a float64
    literature_id via str(int(float(x)))."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    import validation.fable_extract as fe

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(fe, "CACHE", cache_dir)
    monkeypatch.setattr(fe, "OUT", tmp_path)
    monkeypatch.setattr(fe, "_schema_column_defs", lambda: [{"name": "d_movement", "description": "x"}])

    def fake_pdf_text(lit_id):
        if lit_id == "10":
            return ("text for paper 10", "sha_ten")
        return (None, None)  # unresolved paper — must be skipped, not crash

    monkeypatch.setattr(fe, "_pdf_text", fake_pdf_text)

    fake_message = _FakeMessage(
        [{"name": "d_movement", "present": True, "evidence": "ev", "confidence": 0.9}])
    client = _StubClient(fake_message)

    # 10.0 (float64-like) must normalise to "10"; 99 has no resolvable PDF.
    sample = pd.DataFrame({"literature_id": [10.0, 99]})
    fe.run(sample, client=client)

    labels = pd.read_parquet(tmp_path / "fable_labels.parquet")
    assert len(labels) == 1
    row = labels.iloc[0]
    assert row["literature_id"] == "10"
    assert row["column"] == "d_movement"
    assert row["present"] == 1
    assert row["evidence"] == "ev"
    assert row["confidence"] == 0.9

    toks = pd.read_csv(tmp_path / "fable_token_log.csv", dtype={"literature_id": str})
    assert list(toks["literature_id"]) == ["10"]


def test_run_raises_when_zero_papers_succeed(tmp_path, monkeypatch):
    """If every paper in the sample is unresolvable (no PDF), run() must
    still write whatever partial output exists (none, here) but raise a
    RuntimeError rather than silently leaving no/empty fable_labels.parquet
    for score.run to trip over later."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    import pytest
    import validation.fable_extract as fe

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(fe, "CACHE", cache_dir)
    monkeypatch.setattr(fe, "OUT", tmp_path)
    monkeypatch.setattr(fe, "_schema_column_defs", lambda: [{"name": "d_movement", "description": "x"}])

    def fake_pdf_text(lit_id):
        return (None, None)  # every paper unresolvable

    monkeypatch.setattr(fe, "_pdf_text", fake_pdf_text)

    client = _StubClient(_FakeMessage([]))  # must not be called
    sample = pd.DataFrame({"literature_id": ["1", "2", "3"]})

    with pytest.raises(RuntimeError, match="0/3 papers succeeded"):
        fe.run(sample, client=client)

    assert client.messages.calls == 0
    assert not (tmp_path / "fable_labels.parquet").exists()


def test_run_continues_after_one_paper_raises(tmp_path, monkeypatch):
    """A per-paper exception (e.g. a broken PDF resolution) must not abort
    the whole run — the remaining papers should still be processed and
    written to the output files."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pandas as pd
    import validation.fable_extract as fe

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(fe, "CACHE", cache_dir)
    monkeypatch.setattr(fe, "OUT", tmp_path)
    monkeypatch.setattr(fe, "_schema_column_defs", lambda: [{"name": "d_movement", "description": "x"}])

    def fake_pdf_text(lit_id):
        if lit_id == "5":
            raise RuntimeError("simulated resolution failure")
        return ("text for paper 20", "sha_twenty")

    monkeypatch.setattr(fe, "_pdf_text", fake_pdf_text)

    fake_message = _FakeMessage(
        [{"name": "d_movement", "present": False, "evidence": "", "confidence": 0.2}])
    client = _StubClient(fake_message)

    sample = pd.DataFrame({"literature_id": ["5", "20"]})
    fe.run(sample, client=client)  # must not raise

    labels = pd.read_parquet(tmp_path / "fable_labels.parquet")
    assert list(labels["literature_id"]) == ["20"]
