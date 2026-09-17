#!/usr/bin/env python3
"""A rate-limited OpenAlex batch must not be recorded as processed.

On 2026-09-17 enrich_authors_openalex.py resumed with 16,631 DOIs done, hit
sustained HTTP 429, exhausted all 5 retries on both of its batches (50 + 19
DOIs), fetched nothing, and then saved "16700 DOIs processed". Every one of
those 69 DOIs was banked in outputs/.openalex_progress.json without ever
having been fetched, so every later --resume run would have skipped them
permanently. The script still exited 0.

Cause: fetch_works_by_dois() returned [] both for "OpenAlex holds nothing for
these DOIs" (a real answer) and for "all retries exhausted" (no answer at
all), and the caller banked the batch either way. This is the "a block is not
an absence" failure in our own code.

Fix under test: retry exhaustion raises BatchNotFetched; run_pipeline() leaves
those DOIs out of completed_dois and reports the count.

Run: python3 -m pytest tests/test_openalex_progress_banking.py -q
"""

import importlib.util
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "enrich_authors_openalex", PROJECT / "scripts" / "enrich_authors_openalex.py")
oa = importlib.util.module_from_spec(_spec)
sys.modules["enrich_authors_openalex"] = oa
_spec.loader.exec_module(oa)


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected raise_for_status on {self.status_code}")


class _Session:
    """Replays a fixed sequence of responses and counts the calls."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, *a, **kw):
        self.calls += 1
        return self._responses.pop(0) if self._responses else _Resp(429)


def _client(responses, monkeypatch=None):
    c = oa.OpenAlexClient.__new__(oa.OpenAlexClient)
    c.session = _Session(responses)
    c.last_request_time = 0.0
    c.min_interval = 0.0
    c.rate_limit = 10
    return c


def _no_sleep():
    oa.time.sleep = lambda *_a, **_kw: None


def test_exhausted_retries_raise_rather_than_returning_empty():
    _no_sleep()
    c = _client([_Resp(429)] * oa.MAX_RETRIES)
    try:
        c.fetch_works_by_dois(["10.1/a", "10.1/b"])
    except oa.BatchNotFetched:
        pass
    else:
        raise AssertionError(
            "a batch that exhausted its retries returned normally; it would be "
            "banked as processed")
    assert c.session.calls == oa.MAX_RETRIES


def test_a_successful_empty_result_is_still_an_answer():
    # 200 with no works means OpenAlex genuinely holds nothing: that IS a
    # result and must keep banking, or every unknown DOI is retried forever.
    _no_sleep()
    c = _client([_Resp(200, {"results": []})])
    assert c.fetch_works_by_dois(["10.1/a"]) == []


def test_run_pipeline_does_not_bank_an_unfetched_batch(tmp_path, monkeypatch):
    """The end-to-end property: 429 throughout -> progress file unchanged."""
    _no_sleep()
    progress = tmp_path / "progress.json"
    progress.write_text(json.dumps({"completed_dois": ["10.0/old"], "records": []}))
    monkeypatch.setattr(oa, "PROGRESS_FILE", progress)
    monkeypatch.setattr(oa, "OUTPUT_PAPER_AUTHORS", tmp_path / "pa.csv")
    monkeypatch.setattr(oa, "OUTPUT_UNIQUE_AUTHORS", tmp_path / "ua.csv")

    import pandas as pd
    df = pd.DataFrame({"literature_id": [1, 2], "doi": ["10.1/a", "10.1/b"]})
    df["doi_clean"] = df["doi"]
    df["doi_lower"] = df["doi"].str.lower()
    monkeypatch.setattr(oa, "load_papers", lambda: df)

    class _AlwaysRateLimited:
        def __init__(self, *a, **kw):
            pass

        def fetch_works_by_dois(self, dois):
            raise oa.BatchNotFetched("all retries exhausted")

    monkeypatch.setattr(oa, "OpenAlexClient", _AlwaysRateLimited)
    oa.run_pipeline(resume=True, batch_size=50)

    banked = set(json.loads(progress.read_text())["completed_dois"])
    assert banked == {"10.0/old"}, (
        f"rate-limited DOIs were banked as processed: {banked}")
