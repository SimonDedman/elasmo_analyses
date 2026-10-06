#!/usr/bin/env python3
"""Precompute a candidate-keyword pool for a topic so the dashboard can suggest NEW keywords and
anchors in the browser, re-ranked live as the reviewer labels papers.

    python3 scripts/build_topic_candidates.py --topic fisheries [--pool 3000] [--workers 10]

Reads the section-labelled text cache for every paper in the topic's pages (papers.js order), in
two passes over 10 workers: (1) document frequency of unigrams, (2) document frequency of bigrams
whose halves are both frequent unigrams, plus, for the chosen pool, one presence bitset per paper.
The pool is the --pool most frequent content n-grams (stopwords, numbers, citation boilerplate
removed, the tokeniser being suggest_topic_terms.py's) with document frequency >= MIN_DF, EXCLUDING
anything already in the topic's counted vocabulary (a candidate that merely extends an existing
term, e.g. "fishing gear" against "fish*", is kept and flagged).

Writes docs/topic_review/<topic>/data/cands.js:
    window.TR_CANDS = {terms:[...], df:[...], ext:[...], n_papers, built, bits:[base64 per paper, PAPERS order]}
Bit k of paper i is set when terms[k] occurs anywhere in that paper outside OTHER-labelled text.
About 9 MB for 3,000 terms x 18,700 papers; the page loads it only when suggestions are asked for.
Re-run after the vocabulary changes (a re-count) or the pages are rebuilt with different papers.
"""
import argparse
import base64
import json
import sqlite3
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from suggest_topic_terms import CACHE, ACADEMIC, tokens_of, ngram_set, term_matcher, existing_relation, load_js  # noqa: E402

MIN_DF = 20
TOP_UNIGRAMS_FOR_BIGRAMS = 6000
_CONN = None


def _init():
    global _CONN
    _CONN = sqlite3.connect(f"file:{CACHE}?mode=ro", uri=True, timeout=120)


def _clauses(lid):
    r = _CONN.execute("SELECT blob FROM sections WHERE lid=?", (lid,)).fetchone()
    if not r:
        return None
    out = []
    for label, text in json.loads(zlib.decompress(r[0])):
        if label != "OTHER" and text:
            out.extend(tokens_of(text))
    return out


def pass1(lids):
    """unigram document frequency for a chunk of papers"""
    c = Counter()
    for lid in lids:
        cl = _clauses(lid)
        if cl is None:
            continue
        c.update({t for toks in cl for t in toks if t is not None and t not in ACADEMIC})
    return c


_UNI = None
_POOL = None


def _init2(uni, pool):
    global _UNI, _POOL
    _init()
    _UNI, _POOL = uni, pool


def pass2(lids):
    """bigram document frequency (both halves frequent unigrams) + presence bitsets for the pool, if given"""
    c = Counter()
    bits = []
    nbytes = (len(_POOL) + 7) // 8 if _POOL else 0
    for lid in lids:
        cl = _clauses(lid)
        if cl is None:
            bits.append(None)
            continue
        grams = ngram_set(cl)
        if _POOL is None:
            c.update({g for g in grams if " " in g and all(h in _UNI and h not in ACADEMIC for h in g.split(" "))})
        else:
            b = bytearray(nbytes)
            for g in grams:
                k = _POOL.get(g)
                if k is not None:
                    b[k >> 3] |= 1 << (k & 7)
            bits.append(base64.b64encode(bytes(b)).decode("ascii"))
    return c, bits


def chunks(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", default="fisheries")
    ap.add_argument("--pool", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, help="first N papers only (smoke test)")
    args = ap.parse_args()
    t0 = time.time()
    ddir = ROOT / "docs" / "topic_review" / args.topic / "data"
    papers = load_js(ddir / "papers.js", "window.TR_PAPERS")
    lids = [str(p[0]) for p in papers][: args.limit or None]
    vocab = [v["term"] for v in json.loads((ROOT / "outputs" / "topic_review" / args.topic / "vocab.json").read_text())["vocab"]]
    matchers = [(t, term_matcher(t)) for t in vocab]
    ch = chunks(lids, 200)
    print(f"{len(lids):,} papers, {len(vocab)} vocabulary terms, {args.workers} workers", flush=True)

    with Pool(args.workers, initializer=_init) as pool:
        uni = Counter()
        for i, c in enumerate(pool.imap_unordered(pass1, ch)):
            uni.update(c)
            if i % 20 == 0:
                print(f"  pass 1: {min((i + 1) * 200, len(lids)):,} papers, {len(uni):,} distinct unigrams, {time.time() - t0:.0f}s", flush=True)
    uni = Counter({t: n for t, n in uni.items() if n >= MIN_DF})
    top_uni = set(t for t, _ in uni.most_common(TOP_UNIGRAMS_FOR_BIGRAMS))
    print(f"pass 1 done: {len(uni):,} unigrams with df>={MIN_DF}; {time.time() - t0:.0f}s", flush=True)

    with Pool(args.workers, initializer=_init2, initargs=(top_uni, None)) as pool:
        bi = Counter()
        for i, (c, _) in enumerate(pool.imap_unordered(pass2, ch)):
            bi.update(c)
            if i % 20 == 0:
                print(f"  pass 2: {min((i + 1) * 200, len(lids)):,} papers, {len(bi):,} distinct bigrams, {time.time() - t0:.0f}s", flush=True)
    bi = Counter({t: n for t, n in bi.items() if n >= MIN_DF})
    print(f"pass 2 done: {len(bi):,} bigrams with df>={MIN_DF}; {time.time() - t0:.0f}s", flush=True)

    # the pool: most frequent first, vocabulary excluded, extensions flagged
    terms, df, ext, dropped_same = [], [], [], 0
    for t, n in (uni + bi).most_common():
        rel = existing_relation(t, matchers)
        if rel and rel[0] == "same":
            dropped_same += 1
            continue
        terms.append(t)
        df.append(n)
        ext.append(rel[1] if rel else "")
        if len(terms) >= args.pool:
            break
    index = {t: k for k, t in enumerate(terms)}
    print(f"pool: {len(terms)} terms (df {df[-1]}..{df[0]}); {dropped_same} already in the vocabulary skipped; "
          f"{sum(1 for e in ext if e)} flagged as extending an existing term", flush=True)

    with Pool(args.workers, initializer=_init2, initargs=(top_uni, index)) as pool:
        bits = []
        for i, (_, b) in enumerate(pool.imap(pass2, ch)):
            bits.extend(b)
            if i % 20 == 0:
                print(f"  pass 3 (bitsets): {len(bits):,} papers, {time.time() - t0:.0f}s", flush=True)
    assert len(bits) == len(lids)
    out = {"terms": terms, "df": df, "ext": ext, "n_papers": len(lids), "no_text": sum(1 for b in bits if b is None),
           "min_df": MIN_DF, "built": time.strftime("%Y-%m-%d %H:%M %Z"), "bits": bits}
    path = ddir / "cands.js"
    path.write_text("window.TR_CANDS = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB); papers without text {out['no_text']}; {time.time() - t0:.0f}s total")
    print("first 40 pool terms:", ", ".join(terms[:40]))


if __name__ == "__main__":
    main()
