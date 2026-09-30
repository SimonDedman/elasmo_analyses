"""The validation landing page's local author matcher (docs/validate/assets/author_search.js).

Runs the matcher under node against fixture rows and, when the generated
assets/authors_index.json exists, against the real index. Written after Elena
Fernández‐Corredor could not find her own page (2026-09-30): the page called
OpenAlex's `?search=` list endpoint, which does whole-word matching only and
costs 10 credits of a 1,000-credit daily budget shared by every machine behind
one IP address.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "docs" / "validate" / "assets" / "author_search.js"
INDEX = ROOT / "docs" / "validate" / "assets" / "authors_index.json"

FIXTURE = [
    ["A5027778174", "Elena Fernández‐Corredor", "Institut Català de Ciències del Clima", 4],
    ["A5000000001", "Elena Fernández", "Somewhere", 2],
    ["A5000000002", "María Elena Fernández Collazo", "Elsewhere", 1],
    ["A5086753224", "Nicholas K. Dulvy", "Simon Fraser University", 120],
    ["A5000000003", "José M. Eirín‐López", "FIU", 9],
    ["A5000000004", "Nimet Selda Başçınar", "Trabzon", 3],
    ["A5000000005", "Toshihiko Satō", "Tokyo", 5],
]

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def run_search(rows, query, limit=10, tmp_path=None):
    """Rows go through a file: the real index is 1.8 MB, too big for an argv."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)
        rows_path = fh.name
    script = f"""
const m = require({json.dumps(str(MODULE))});
const rows = JSON.parse(require('fs').readFileSync({json.dumps(rows_path)}, 'utf8'));
const idx = m.buildIndex(rows);
process.stdout.write(JSON.stringify(m.searchLocal(idx, {json.dumps(query)}, {limit}).map(r => r.id)));
"""
    try:
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    finally:
        Path(rows_path).unlink(missing_ok=True)
    return json.loads(out.stdout)


def test_module_exists():
    assert MODULE.exists(), f"{MODULE} missing"


@pytest.mark.parametrize(
    "query",
    [
        "Elena Fernández‐Corredor",   # exact, with OpenAlex's U+2010 hyphen
        "Elena Fernández-Corredor",         # ASCII hyphen
        "Elena Fernandez-Corredor",              # no accent
        "Elena Fernandez Corredor",              # no hyphen
        "Fernández-Corredor Elena",         # surname first
        "Corredor Elena",                        # second surname first
        "Fernandez Corredor",                    # surnames only
        "Elena Fernández-Co",                    # typing prefix past the hyphen
        "corredor",                              # single token
    ],
)
def test_elena_found_first(query):
    assert run_search(FIXTURE, query)[0] == "A5027778174", query


@pytest.mark.parametrize("query", ["elena fern", "Elena", "fernandez"])
def test_elena_present_for_ambiguous_prefixes(query):
    """A prefix shared by several people lists all of them; her rank among them is not asserted."""
    assert "A5027778174" in run_search(FIXTURE, query), query


def test_prefix_ranks_shorter_exact_name_first():
    # "Elena Fernández" matches three people; the exact full-name match ranks first.
    ids = run_search(FIXTURE, "Elena Fernández")
    assert ids[0] == "A5000000001"
    assert set(ids) == {"A5027778174", "A5000000001", "A5000000002"}


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Eirin-Lopez", "A5000000003"),
        ("jose eirin lopez", "A5000000003"),
        ("Bascinar", "A5000000004"),
        ("Basçınar Selda", "A5000000004"),
        ("Toshihiko Sato", "A5000000005"),
        ("Dulvy", "A5086753224"),
        ("N. K. Dulvy", "A5086753224"),
    ],
)
def test_accent_and_order_folding(query, expected):
    assert run_search(FIXTURE, query)[0] == expected, query


def test_no_match_returns_empty():
    assert run_search(FIXTURE, "Zzyzx Quux") == []


def test_short_query_returns_empty():
    assert run_search(FIXTURE, "E") == []


@pytest.mark.skipif(not INDEX.exists(), reason="generated index not present")
def test_real_index_finds_elena():
    rows = json.loads(INDEX.read_text(encoding="utf-8"))["authors"]
    assert run_search(rows, "Elena Fernandez-Corredor")[0] == "A5027778174"
    assert run_search(rows, "Fernandez Corredor")[0] == "A5027778174"
