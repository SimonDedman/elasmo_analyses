#!/usr/bin/env python3
"""Count a topic's candidate vocabulary per paper, per term, per SECTION, once.

The extractor (extract_schema_columns.py) decides a column with
    round( sum over terms, sections of count[term, section] * weight[section] ) >= threshold
(after an elasmobranch-proximity filter on some columns, and an any-anchor gate).
Its evidence table keeps only the totals, so a rule change needs a corpus re-run.

This pass stores the inner counts instead. With count[term, section] (both the raw
count and the proximity-filtered one) and anchor presence per paper, ANY change to
terms kept/dropped, per-term weights, section weights, the proximity switch, the
anchor gate, or the threshold can be re-scored in the browser with no corpus run.
Only a term that was never counted needs this script again, and that re-count reads
the section-labelled text cache written here rather than re-running pdftotext.

It reuses the extractor's own functions (PDF resolution, text extraction, section
labelling, term compilation, elasmobranch pattern), so the text and the counts are
the ones the live extraction saw. `--control` proves that: it re-scores every live
column in the topic from the stored counts and compares with
outputs/schema_extraction_evidence.csv.

Usage:
  python3 scripts/build_topic_features.py --topic data/topic_review/fisheries.json
  python3 scripts/build_topic_features.py --topic data/topic_review/fisheries.json --control
"""
import argparse
import bisect
import hashlib
import json
import math
import sqlite3
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402

OUT_BASE = ROOT / "outputs" / "topic_review"
TEXT_CACHE = OUT_BASE / "text_cache.sqlite"
SECTIONS = ["TITLE", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "METHODS", "RESULTS",
            "RESULTS_AND_DISCUSSION", "DISCUSSION", "CONCLUSIONS", "OTHER"]
SEC_IDX = {s: i for i, s in enumerate(SECTIONS)}
SNIPPETS_PER_PAPER = 4
SNIPPET_WINDOW = 90


def live_columns(names):
    """{column: {prefix, terms, threshold, anchors, case_sensitive, proximity, prerequisites}} from the extractor."""
    out = {}
    for schema in X.ALL_SCHEMAS:
        for col in schema.columns:
            if col.name in names:
                out[col.name] = {
                    "prefix": schema.prefix,
                    "terms": list(col.terms),
                    "threshold": col.threshold,
                    "anchors": list(getattr(col, "anchors", None) or []),
                    "case_sensitive": sorted(getattr(col, "case_sensitive_terms", None) or []),
                    "proximity": col.name in X.PROXIMITY_CHECK_COLUMNS,
                    "prerequisites": dict(getattr(col, "prerequisite_terms", None) or {}),
                }
    missing = set(names) - set(out)
    if missing:
        sys.exit(f"topic names columns the extractor does not define: {sorted(missing)}")
    return out


def build_vocab(topic, live):
    """One entry per distinct (term, case_sensitive). Anchors are counted like terms so a
    reviewer can promote one to a keyword or demote a keyword to an anchor."""
    vocab, index = [], {}

    def add(raw, cs):
        raw = raw.strip()
        if not raw:
            return None
        key = (raw, bool(cs))
        if key not in index:
            index[key] = len(vocab)
            vocab.append({"term": raw, "cs": bool(cs)})
        return index[key]

    for name, col in live.items():
        col["term_ids"] = [add(t, t in col["case_sensitive"]) for t in col["terms"]]
        col["anchor_ids"] = [add(a, False) for a in col["anchors"]]
    for prop in topic.get("proposed_rules", []):
        cs = set(prop.get("case_sensitive", []))
        prop["term_ids"] = [add(t, t in cs) for t in prop["terms"]]
        prop["anchor_ids"] = [add(a, a in cs) for a in prop.get("anchors", [])]
    return vocab


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
_VOCAB = []
_COMPILED = []
_PDF_INDEX = {}
_PDF_BY_ID = {}
_CACHE = None


def _init(vocab, pdf_index):
    global _VOCAB, _COMPILED, _PDF_INDEX, _CACHE, _PDF_BY_ID
    _VOCAB = vocab
    _COMPILED = [X.compile_term(v["term"], case_sensitive=v["cs"]) for v in vocab]
    _PDF_INDEX = pdf_index
    _PDF_BY_ID = X.load_pdf_id_map()
    if TEXT_CACHE.exists():
        # every worker now reads the cache on every paper while the parent writes
        # new rows to it, so readers must wait rather than fail: WAL on the writer,
        # a long busy timeout here.
        _CACHE = sqlite3.connect(f"file:{TEXT_CACHE}?mode=ro", uri=True, timeout=120)
        _CACHE.execute("PRAGMA busy_timeout=120000")


def _sentence_index(chunk):
    """Sentence ends and an 'elasmobranch term within +-1 sentence' flag per sentence,
    built the way _proximity_adjusted_freq builds them (including its +1 separator
    approximation), so the filtered counts agree with the live extractor."""
    sents = X._SENTENCE_SPLIT_RE.split(chunk)
    ends, pos = [], 0
    for s in sents:
        ends.append(pos + len(s))
        pos = pos + len(s) + 1
    ok = []
    for i in range(len(sents)):
        lo, hi = max(0, i - 1), min(len(sents), i + 2)
        ok.append(bool(X._ELASMO_PATTERN.search(" ".join(sents[lo:hi]))))
    return ends, ok


def _count(regex, chunk, sent_idx):
    ends, ok = sent_idx
    raw = prox = 0
    first = None
    for m in regex.finditer(chunk):
        raw += 1
        if first is None:
            first = m.start()
        i = bisect.bisect_left(ends, m.start())
        if i >= len(ends):
            i = 0  # the extractor's linear search falls back to sentence 0
        if ok[i]:
            prox += 1
    return raw, prox, first


def resolve_text(row):
    """(labelled_sections, pdf_path) exactly as process_paper builds them, or (None, None).

    Resolution goes through the literature_id map (scripts/build_pdf_id_map.py),
    the same as production since 2026-09-23. Resolving by surname and year here
    would put another paper's text under this paper's id, which is the bug that
    map exists to kill."""
    title = row.get("title") or ""
    best = _PDF_BY_ID.get(str(row.get("literature_id")).split(".")[0])
    if best is None or not best.exists():
        return None, None
    text = X.extract_text_from_pdf(best)
    if not text:
        return None, str(best)
    if title:
        text = "TITLE\n" + title + "\nOTHER\n\n" + text
    return X._label_sections(text), str(best)


def work(row):
    lid = str(row["literature_id"]).split(".")[0]
    # The id map decides which file is this paper's. The text cache is keyed by id
    # and was first filled while the old surname+year matcher was in charge, so a
    # cached blob is only usable when it came from the file the map now names:
    # otherwise the cache quietly reinstates the borrowed-PDF bug.
    want = _PDF_BY_ID.get(lid)
    if want is None:
        return {"lid": row["literature_id"], "pdf": None, "status": "no_pdf"}
    sections, pdf, fresh = None, str(want), False
    if _CACHE is not None:
        hit = _CACHE.execute("SELECT blob, pdf FROM sections WHERE lid=?", (lid,)).fetchone()
        if hit and hit[1] == str(want):
            sections = [tuple(x) for x in json.loads(zlib.decompress(hit[0]))]
    if sections is None:
        sections, pdf = resolve_text(row)
        fresh = True
    if not sections:
        return {"lid": lid, "pdf": pdf, "status": "no_pdf" if pdf is None else "no_text"}
    indexes = [(_sentence_index(chunk), chunk.lower()) for _, chunk in sections]
    counts, snippets = [], []
    for ti, ct in enumerate(_COMPILED):
        literal = None if (ct.and_parts or "*" in ct.raw or "\\" in ct.raw) else ct.raw.lower()
        per_sec = {}
        for (label, chunk), (sidx, lower) in zip(sections, indexes):
            if literal is not None and literal not in lower:
                continue
            if ct.and_parts is not None:
                r1, p1, f1 = _count(ct.and_parts[0], chunk, sidx)
                r2 = X._count_matches(ct.and_parts[1], chunk)
                if r1 == 0 or r2 == 0:
                    continue
                raw, prox, first = min(r1, r2), min(p1, r2), f1
            else:
                raw, prox, first = _count(ct.regex, chunk, sidx)
            if raw == 0:
                continue
            s = SEC_IDX.get(label, SEC_IDX["OTHER"])
            a = per_sec.setdefault(s, [0, 0])
            a[0] += raw
            a[1] += prox
            if first is not None and len(snippets) < 40:
                lo, hi = max(0, first - SNIPPET_WINDOW), min(len(chunk), first + len(ct.raw) + SNIPPET_WINDOW)
                snippets.append((raw, ti, label, " ".join(chunk[lo:hi].split())))
        for s, (raw, prox) in per_sec.items():
            counts.append([ti, s, raw, prox])
    snippets.sort(key=lambda t: -t[0])
    keep, seen = [], set()
    for raw, ti, label, snip in snippets:
        if ti in seen:
            continue
        seen.add(ti)
        keep.append([ti, label, snip])
        if len(keep) == SNIPPETS_PER_PAPER * 3:
            break
    out = {"lid": lid, "pdf": pdf, "status": "ok", "counts": counts, "snippets": keep,
           "sections_present": sorted({SEC_IDX.get(l, 9) for l, _ in sections})}
    if fresh:
        out["_store"] = zlib.compress(json.dumps(sections).encode(), 6)
    return out


# ---------------------------------------------------------------------------
# Scoring (the reference implementation the browser mirrors)
# ---------------------------------------------------------------------------
def score(counts_by_term, col, weights):
    """sum(count*weight) and the anchor gate, as _match_column does (unrounded since 2026-09-25)."""
    total = 0.0
    fired = set()
    for tid in col["term_ids"]:
        for s, raw, prox in counts_by_term.get(tid, []):
            n = prox if col["proximity"] else raw
            if n:
                fired.add(tid)
                total += n * weights.get(SECTIONS[s], 0.25)
    anchors_ok = (not col["anchor_ids"]) or any(counts_by_term.get(a) for a in col["anchor_ids"])
    return round(total, 2), bool(fired), anchors_ok


def control(topic_dir, live):
    ev = pd.read_csv(X.EVIDENCE_CSV, low_memory=False, usecols=["literature_id", "column", "binary", "total_freq"])
    ev = ev[ev.column.isin(live)].drop_duplicates(["literature_id", "column"], keep="last")
    # total_freq is the UNROUNDED weighted total as of 2026-09-25
    truth = {(str(r.literature_id), r.column): (int(r.binary), float(r.total_freq)) for r in ev.itertuples()}
    rep = {c: {"compared": 0, "binary_agree": 0, "score_agree": 0, "only_in_evidence": 0, "only_here": 0,
               "skipped_prerequisites": bool(live[c]["prerequisites"])} for c in live}
    seen = set()
    for line in open(topic_dir / "features.jsonl"):
        p = json.loads(line)
        if p["status"] != "ok":
            continue
        by_term = {}
        for ti, s, raw, prox in p["counts"]:
            by_term.setdefault(ti, []).append((s, raw, prox))
        for c, col in live.items():
            sc, fired, anchors_ok = score(by_term, col, X._SECTION_WEIGHTS.get(col["prefix"], {}))
            sc = round(sc, 2)
            key = (str(p["lid"]), c)
            if not fired:
                continue
            seen.add(key)
            if key not in truth:
                rep[c]["only_here"] += 1
                continue
            b = int(anchors_ok and sc >= col["threshold"])
            rep[c]["compared"] += 1
            rep[c]["binary_agree"] += int(b == truth[key][0])
            rep[c]["score_agree"] += int(abs(sc - truth[key][1]) < 0.01)
    for key in truth:
        if key not in seen:
            rep[key[1]]["only_in_evidence"] += 1
    json.dump(rep, open(topic_dir / "control.json", "w"), indent=1)
    print(f"{'column':28s} {'compared':>9s} {'binary%':>8s} {'score%':>8s} {'ev-only':>8s} {'here-only':>9s}")
    for c, r in rep.items():
        n = max(r["compared"], 1)
        print(f"{c:28s} {r['compared']:9d} {100*r['binary_agree']/n:8.2f} {100*r['score_agree']/n:8.2f} "
              f"{r['only_in_evidence']:8d} {r['only_here']:9d}{'  (has prerequisites: not modelled)' if r['skipped_prerequisites'] else ''}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, help="first N corpus rows only (smoke test)")
    ap.add_argument("--control", action="store_true", help="compare re-scored live columns with the evidence table")
    args = ap.parse_args()

    topic = json.load(open(args.topic))
    live = live_columns(topic["live_columns"])
    vocab = build_vocab(topic, live)
    topic_dir = OUT_BASE / topic["id"]
    topic_dir.mkdir(parents=True, exist_ok=True)
    if args.control:
        return control(topic_dir, live)

    vocab_hash = hashlib.sha1(json.dumps(vocab, sort_keys=True).encode()).hexdigest()[:12]
    df = pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id", "title", "authors", "year", "journal", "doi"])
    df = df[df.literature_id.notna()]
    if args.limit:
        df = df.head(args.limit)
    rows = df.to_dict("records")

    db = sqlite3.connect(TEXT_CACHE, timeout=120)
    db.execute("PRAGMA journal_mode=WAL")      # readers (the workers) must not be blocked out
    db.execute("PRAGMA busy_timeout=120000")
    db.execute("CREATE TABLE IF NOT EXISTS sections (lid TEXT PRIMARY KEY, pdf TEXT, mtime REAL, blob BLOB)")
    cached = {r[0]: (r[1], r[2]) for r in db.execute("SELECT lid, pdf, mtime FROM sections")}
    n_cached = 0
    for r in rows:
        hit = cached.get(str(r["literature_id"]))
        if hit and hit[0] and Path(hit[0]).exists() and abs(Path(hit[0]).stat().st_mtime - hit[1]) < 1:
            r["_cached_pdf"] = hit[0]
            n_cached += 1
    print(f"topic {topic['id']}: {len(vocab)} vocabulary terms (hash {vocab_hash}); {len(rows):,} corpus rows; "
          f"{n_cached:,} served from the text cache", flush=True)

    pdf_index = X.build_pdf_index(X.PDF_BASE)
    cov = {"rows_in_scope": len(rows), "ok": 0, "no_pdf": 0, "no_text": 0, "vocab_hash": vocab_hash,
           "started": time.strftime("%Y-%m-%d %H:%M:%S %Z")}
    t0 = time.time()
    window = []
    tmp = topic_dir / "features.jsonl.part"
    with Pool(args.workers, initializer=_init, initargs=(vocab, pdf_index)) as pool, open(tmp, "w") as fh:
        for i, res in enumerate(pool.imap_unordered(work, rows, chunksize=20), 1):
            store = res.pop("_store", None)
            if store is not None and res.get("pdf"):
                db.execute("INSERT OR REPLACE INTO sections VALUES (?,?,?,?)",
                           (str(res["lid"]), res["pdf"], Path(res["pdf"]).stat().st_mtime, store))
            cov[res["status"]] += 1
            fh.write(json.dumps(res) + "\n")
            if i % 500 == 0:
                db.commit()
                now = time.time()
                window.append((now, i))
                window = window[-6:]
                rate = (window[-1][1] - window[0][1]) / max(now - window[0][0], 1e-9) if len(window) > 1 else i / (now - t0)
                eta = (len(rows) - i) / max(rate, 1e-9)
                print(f"{i:,}/{len(rows):,} ok={cov['ok']:,} no_pdf={cov['no_pdf']:,} no_text={cov['no_text']:,} "
                      f"rate={rate*60:,.0f}/min eta {eta/60:.0f} min "
                      f"({time.strftime('%H:%M %Z', time.localtime(now + eta))})", flush=True)
    db.commit()
    db.close()
    tmp.rename(topic_dir / "features.jsonl")
    cov["finished"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    cov["seconds"] = round(time.time() - t0)
    json.dump(cov, open(topic_dir / "coverage.json", "w"), indent=1)
    json.dump({"vocab": vocab, "sections": SECTIONS, "live": live,
               "proposed_rules": topic.get("proposed_rules", []),
               "section_weights": {k: v for k, v in X._SECTION_WEIGHTS.items()}},
              open(topic_dir / "vocab.json", "w"), indent=1)
    print("DONE", json.dumps(cov), flush=True)


if __name__ == "__main__":
    main()
