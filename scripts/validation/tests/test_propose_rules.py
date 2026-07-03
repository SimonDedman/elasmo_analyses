import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]


class _FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


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


def test_rank_disagreements_orders_worst_first():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.propose_rules import rank_disagreements
    m = pd.DataFrame({"set": ["silver_rules_vs_fable"] * 3, "column": ["a", "b", "c"],
                      "f1": [0.2, 0.9, 0.5], "tp": [10, 10, 10], "fp": [9, 1, 4], "fn": [8, 1, 3]})
    assert rank_disagreements(m)[0] == "a"  # lowest f1, adequate support


def test_current_rule_resolves_real_column():
    """current_rule() must derive the schema PREFIX (first token + '_') from
    a full column name and look the column up inside that prefix's nested
    dict in rules.json -- rules.json is keyed by prefix (eco_, pr_, gear_,
    imp_, d_, ...), not by individual column name."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.propose_rules import _rules, current_rule

    rules = _rules()
    rule = current_rule(rules, "eco_pelagic")
    assert rule.get("threshold") == 2
    assert "pelagic" in rule.get("terms", [])


def test_current_rule_returns_empty_dict_for_unknown_column():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.propose_rules import current_rule

    assert current_rule({}, "nonexistent_column_xyz") == {}
    assert current_rule({"eco_": {"eco_pelagic": {"threshold": 2}}}, "eco_nope") == {}
    assert current_rule({"eco_": {"eco_pelagic": {"threshold": 2}}}, "totally_unknown_prefix_col") == {}


def test_propose_for_column_parses_json_reply():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.propose_rules import propose_for_column

    reply = json.dumps({"change_type": "add_terms", "detail": "x,y", "rationale": "z"})
    client = _StubClient(_FakeMessage(reply))

    result = propose_for_column("d_movement", ["evidence one", "evidence two"], {"terms": ["move"]}, client)

    assert result == {"change_type": "add_terms", "detail": "x,y", "rationale": "z"}
    assert client.messages.calls == 1


def test_propose_for_column_falls_back_on_non_json_reply():
    sys.path.insert(0, str(ROOT / "scripts"))
    from validation.propose_rules import propose_for_column

    client = _StubClient(_FakeMessage("Sorry, I cannot comply with that request."))

    result = propose_for_column("d_movement", [], {}, client)

    assert result["change_type"] == "review"
    assert "Sorry" in result["detail"]
