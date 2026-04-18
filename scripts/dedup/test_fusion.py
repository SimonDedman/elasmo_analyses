"""Synthetic unit tests for fusion.evaluate_pair.

Run directly: python3 scripts/dedup/test_fusion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from datasketch import MinHash

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.dedup.fusion import evaluate_pair  # noqa: E402
from scripts.dedup.schema import PdfFeatures  # noqa: E402


def make_minhash(words: list[str], num_perm: int = 128) -> bytes:
    mh = MinHash(num_perm=num_perm)
    for w in words:
        mh.update(w.encode("utf-8"))
    return np.asarray(mh.hashvalues, dtype="<u4").tobytes()


BASE_WORDS_A = [f"term{i} word{i+1} token{i+2} lexeme{i+3}" for i in range(500)]
BASE_WORDS_B = [f"alpha{i} beta{i+1} gamma{i+2} delta{i+3}" for i in range(500)]


def f(**kw) -> PdfFeatures:
    defaults = dict(rel_path="x.pdf", size_bytes=1_000_000, mtime=1.0,
                    bytes_sha256="a" * 64, page_count=10,
                    text_word_count=2000, text_is_extractable=True,
                    detected_language="en")
    defaults.update(kw)
    return PdfFeatures(**defaults)


def main() -> int:
    results = []

    # 1. byte-identical
    r = evaluate_pair(f(rel_path="1", bytes_sha256="abc"),
                      f(rel_path="2", bytes_sha256="abc"))
    results.append(("byte-identical", r.decision == "same_content" and r.confidence >= 0.99, r))

    # 2. both corrupted
    r = evaluate_pair(f(rel_path="1", is_corrupted=True, bytes_sha256=None),
                      f(rel_path="2", is_corrupted=True, bytes_sha256=None))
    results.append(("both-corrupt", r.decision == "manual", r))

    # 3. one corrupted
    r = evaluate_pair(f(rel_path="1", is_corrupted=True, bytes_sha256=None),
                      f(rel_path="2", bytes_sha256="b" * 64))
    results.append(("one-corrupt", r.decision == "keep_2" and r.keep == 2, r))

    # 4. different languages
    r = evaluate_pair(f(rel_path="1", detected_language="en", bytes_sha256="b"),
                      f(rel_path="2", detected_language="fr", bytes_sha256="c"))
    results.append(("lang-differ", r.decision == "distinct", r))

    # 5. same DOI (+ supporting) → high confidence
    mh_same = make_minhash(BASE_WORDS_A)
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", extracted_doi="10.1/foo",
          phash_p1="abcdef0123456789", minhash=mh_same,
          crossref_title="A Shark Paper", xmp_title="A Shark Paper"),
        f(rel_path="2", bytes_sha256="y", extracted_doi="10.1/foo",
          phash_p1="abcdef0123456789", minhash=mh_same,
          crossref_title="A Shark Paper", xmp_title="A Shark Paper"),
    )
    results.append(("same-doi+phash+text", r.decision.startswith("keep_") and r.confidence >= 0.85, r))

    # 6. different DOIs → distinct
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", extracted_doi="10.1/foo"),
        f(rel_path="2", bytes_sha256="y", extracted_doi="10.1/bar"),
    )
    results.append(("different-doi", r.decision == "distinct", r))

    # 7. SM markers + same paper → rename_sm
    mh_a = make_minhash(BASE_WORDS_A)
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", extracted_doi="10.1/foo",
          minhash=mh_a, text_word_count=8000, size_bytes=2_000_000),
        f(rel_path="2", bytes_sha256="y", extracted_doi="10.1/foo",
          minhash=mh_a, text_word_count=1000, size_bytes=500_000,
          first_page_text_lower="supplementary information for sharks"),
    )
    results.append(("sm-marker", r.decision == "rename_sm" and r.keep == 1, r))

    # 8. corrigendum → is_corrigendum
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", extracted_doi="10.1/foo",
          minhash=mh_a, size_bytes=2_000_000),
        f(rel_path="2", bytes_sha256="y", extracted_doi="10.1/foo",
          minhash=mh_a, size_bytes=300_000,
          info_title="Corrigendum to Sharks in the Sea", page_count=2,
          crossref_type="correction"),
    )
    results.append(("corrigendum", r.decision == "is_corrigendum" and r.keep == 1, r))

    # 9. both books
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", looks_like_book=True, page_count=400),
        f(rel_path="2", bytes_sha256="y", looks_like_book=True, page_count=500),
    )
    results.append(("both-book", r.decision == "is_book", r))

    # 10. chapter of book
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", looks_like_book=False, page_count=12),
        f(rel_path="2", bytes_sha256="y", looks_like_book=True, page_count=400),
    )
    results.append(("chapter-of-book", r.decision == "is_chapter", r))

    # 11. unrelated papers (different minhash, different text) → distinct
    mh_b = make_minhash(BASE_WORDS_B)
    r = evaluate_pair(
        f(rel_path="1", bytes_sha256="x", minhash=mh_a, phash_p1="0000000000000000",
          xmp_title="Shark movements"),
        f(rel_path="2", bytes_sha256="y", minhash=mh_b, phash_p1="ffffffffffffffff",
          xmp_title="Whale songs"),
    )
    results.append(("unrelated", r.decision == "distinct" and r.confidence < 0.2, r))

    # Report
    ok = sum(1 for _, p, _ in results if p)
    print(f"Passed: {ok}/{len(results)}")
    for name, passed, dec in results:
        mark = "OK " if passed else "FAIL"
        print(f"  {mark}  {name:<24} -> {dec.decision} conf={dec.confidence:.2f} rule={dec.rule}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
