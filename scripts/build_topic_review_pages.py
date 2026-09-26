#!/usr/bin/env python3
"""Turn a topic's feature table into the static data files behind docs/topic_review/<topic>/.

Reads   outputs/topic_review/<topic>/features.jsonl, vocab.json, coverage.json, control.json
        (written by build_topic_features.py), the corpus parquet for paper metadata,
        the Fable corpus cache as SILVER labels, outputs/validation/gold_labels.csv as the
        few existing expert labels, and the borrowed-PDF suspects list.
Writes  docs/topic_review/<topic>/data/meta.js, papers.js, counts.js, seed_labels.js,
        snips_<rule>.js for each featured rule, and rules_overview.json.

Plain <script src> files, not fetch(): the pages must open from file:// as well as
from GitHub Pages.

  python3 scripts/build_topic_review_pages.py --topic data/topic_review/fisheries.json
"""
import argparse
import csv
import glob
import json
import re
import sqlite3
import sys
import time
import zlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402
from generate_closed_access_html import TEAM  # noqa: E402
from build_topic_features import OUT_BASE, SECTIONS, SEC_IDX, TEXT_CACHE, build_vocab, live_columns  # noqa: E402

SUSPECTS = ROOT / "outputs" / "extraction_borrowed_pdf_suspects_2026-09-18.csv"
FABLE_CACHE = ROOT / "outputs" / "validation" / ".fable_corpus_cache"
GOLD = ROOT / "outputs" / "validation" / "gold_labels.csv"
SNIPS_PER_PAPER = 3
WINDOW = 110


def js(path, name, obj):
    path.write_text(f"window.{name} = " + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + ";\n")
    return path.stat().st_size


def first_author(authors):
    a = [x.strip() for x in re.split(r";|&| and ", str(authors or "")) if x.strip()]
    if not a:
        return ""
    sur = a[0].split(",")[0].strip()
    return sur + (" et al." if len(a) > 1 else "")


def py_round(x):
    return round(x)


def score(by_term, rule, weights):
    total, fired = 0.0, False
    for tid in rule["term_ids"]:
        for s, raw, prox in by_term.get(tid, ()):
            n = prox if rule["proximity"] else raw
            if n:
                fired = True
                total += n * weights.get(SECTIONS[s], 0.25)
    gate = (not rule["anchor_ids"]) or any(by_term.get(a) for a in rule["anchor_ids"])
    return total, fired, gate


def snippets_for(rule, vocab, lids, out_path):
    """Up to SNIPS_PER_PAPER snippets per paper for THIS rule's terms, read from the text
    cache: highest-weighted section first, one snippet per distinct term."""
    terms = [(tid, X.compile_term(vocab[tid]["term"], case_sensitive=vocab[tid]["cs"])) for tid in rule["term_ids"]]
    weights = X._SECTION_WEIGHTS.get(rule["prefix"], {})
    db = sqlite3.connect(f"file:{TEXT_CACHE}?mode=ro", uri=True, timeout=120)
    out = {}
    for lid in lids:
        row = db.execute("SELECT blob FROM sections WHERE lid=?", (str(lid),)).fetchone()
        if not row:
            continue
        sections = json.loads(zlib.decompress(row[0]))
        order = sorted(range(len(sections)), key=lambda i: -weights.get(sections[i][0], 0.25))
        got, seen = [], set()
        for i in order:
            label, chunk = sections[i]
            for tid, ct in terms:
                if tid in seen or ct.regex is None:
                    continue
                m = ct.regex.search(chunk)
                if not m:
                    continue
                seen.add(tid)
                lo, hi = max(0, m.start() - WINDOW), min(len(chunk), m.end() + WINDOW)
                text = " ".join((chunk[lo:m.start()] + "«" + m.group(0) + "»" + chunk[m.end():hi]).split())
                got.append([tid, SEC_IDX.get(label, 9), text])
                if len(got) == SNIPS_PER_PAPER:
                    break
            if len(got) == SNIPS_PER_PAPER:
                break
        if got:
            out[str(lid)] = got
    return js(out_path, "TR_SNIPS", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, type=Path)
    args = ap.parse_args()
    topic = json.load(open(args.topic))
    tdir = OUT_BASE / topic["id"]
    live = live_columns(topic["live_columns"])
    vocab = build_vocab(topic, live)
    stored = json.load(open(tdir / "vocab.json"))
    if [v["term"] for v in stored["vocab"]] != [v["term"] for v in vocab]:
        sys.exit("topic vocabulary changed since the feature pass: re-run build_topic_features.py first")

    rules = []
    for name, col in live.items():
        rules.append({"id": name, "label": name, "kind": "live", "group": "Live extraction columns",
                      "term_ids": col["term_ids"], "anchor_ids": col["anchor_ids"], "threshold": col["threshold"],
                      "proximity": col["proximity"], "prefix": col["prefix"], "meaning": None, "ref": None,
                      "prerequisites": bool(col["prerequisites"])})
    for p in topic.get("proposed_rules", []):
        rules.append({"id": p["id"], "label": f"{p['category']} › {p['subcategory']}", "kind": "proposed",
                      "group": f"Proposed by David: {p['section']}", "term_ids": p["term_ids"],
                      "anchor_ids": p["anchor_ids"], "threshold": p["threshold"], "proximity": p.get("proximity", True),
                      "prefix": p.get("prefix", "d_"), "meaning": p.get("meaning"), "ref": p.get("reference_paper"),
                      "prerequisites": False})

    meta_df = pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id", "title", "authors", "year", "journal", "doi"])
    meta_df = meta_df[meta_df.literature_id.notna()]
    meta = {str(r.literature_id).split(".")[0]: r for r in meta_df.itertuples()}
    suspects = set()
    if SUSPECTS.exists():
        suspects = {str(r["lid"]).split(".")[0] for r in csv.DictReader(open(SUSPECTS))}

    papers, counts, by_lid = [], [], {}
    status = {"ok": 0, "no_pdf": 0, "no_text": 0}
    for line in open(tdir / "features.jsonl"):
        p = json.loads(line)
        status[p["status"]] += 1
        if p["status"] != "ok" or not p["counts"]:
            continue
        lid = str(p["lid"]).split(".")[0]
        m = meta.get(lid)
        if m is None or lid in by_lid:   # the corpus table repeats a few literature_ids: keep the first
            status["duplicate_id"] = status.get("duplicate_id", 0) + (lid in by_lid)
            continue
        flat = []
        for ti, s, raw, prox in p["counts"]:
            flat += [ti * 10 + s, raw, prox]
        year = None if pd.isna(m.year) else int(m.year)
        papers.append([lid, (m.title or "")[:220], year, first_author(m.authors), (m.journal or "")[:70] if isinstance(m.journal, str) else "",
                       m.doi if isinstance(m.doi, str) else "", 1 if lid in suspects else 0])
        counts.append(flat)
        by_lid[lid] = p["counts"]

    # --- seed labels -------------------------------------------------------
    rule_ids = {r["id"] for r in rules}
    fable, fable_seen = {}, []
    for f in glob.glob(str(FABLE_CACHE / "*.txt")):
        t = open(f).read()
        m = re.search(r"^LIT:\s*(\d+)", t, re.M)
        if not m:
            continue
        fable_seen.append(m.group(1))
        for ln in t.splitlines():
            part = ln.split("|")
            if len(part) >= 2 and part[0] in rule_ids:
                try:
                    fable.setdefault(part[0], {})[m.group(1)] = [float(part[1]), "|".join(part[2:])[:180]]
                except ValueError:
                    pass
    gold = {}
    if GOLD.exists():
        for r in csv.DictReader(open(GOLD)):
            if r["column"] in rule_ids:
                gold.setdefault(r["column"], {})[str(r["literature_id"]).split(".")[0]] = [int(float(r["human_value"])), r["reviewer"]]

    # --- per-rule overview (the workload table on the topic landing page) ---
    overview = []
    for r in rules:
        w = X._SECTION_WEIGHTS.get(r["prefix"], {})
        n_hit = n_in = n_margin = n_gate_fail = 0
        hist = {}
        for lid, cts in by_lid.items():
            bt = {}
            for ti, s, raw, prox in cts:
                bt.setdefault(ti, []).append((s, raw, prox))
            total, fired, gate = score(bt, r, w)
            if not fired:
                continue
            n_hit += 1
            sc = py_round(total)
            is_in = gate and sc >= r["threshold"]
            n_in += is_in
            n_gate_fail += (not gate)
            if gate and abs(total - (r["threshold"] - 0.5)) <= 0.5:
                n_margin += 1
            b = min(int(total), 15)
            hist[b] = hist.get(b, 0) + 1
        overview.append({"id": r["id"], "label": r["label"], "kind": r["kind"], "group": r["group"],
                         "terms": [vocab[t]["term"] for t in r["term_ids"]],
                         "anchors": [vocab[a]["term"] for a in r["anchor_ids"]],
                         "threshold": r["threshold"], "n_terms": len(r["term_ids"]), "n_anchors": len(r["anchor_ids"]),
                         "papers_with_hit": n_hit, "papers_in": int(n_in), "margin": n_margin,
                         "anchor_gate_fails": n_gate_fail, "hist": hist,
                         "fable_in": len(fable.get(r["id"], {})), "gold": len(gold.get(r["id"], {}))})

    ddir = ROOT / "docs" / "topic_review" / topic["id"] / "data"
    ddir.mkdir(parents=True, exist_ok=True)
    sizes = {}
    control = json.load(open(tdir / "control.json")) if (tdir / "control.json").exists() else {}
    sizes["meta.js"] = js(ddir / "meta.js", "TR_META", {
        "topic": {k: topic[k] for k in ("id", "title", "champion")}, "sections": SECTIONS,
        "vocab": [v["term"] for v in vocab], "vocab_cs": [int(v["cs"]) for v in vocab],
        "team": TEAM, "rules": rules, "section_weights": X._SECTION_WEIGHTS, "featured": topic.get("featured", []),
        "overview": overview, "coverage": {**json.load(open(tdir / "coverage.json")), **status, "papers_in_pages": len(papers),
                                           "suspect_text": sum(p[6] for p in papers)},
        "control": control, "built": time.strftime("%Y-%m-%d %H:%M %Z")})
    sizes["papers.js"] = js(ddir / "papers.js", "TR_PAPERS", papers)
    sizes["counts.js"] = js(ddir / "counts.js", "TR_COUNTS", counts)
    sizes["seed_labels.js"] = js(ddir / "seed_labels.js", "TR_SEED", {"fable": fable, "fable_seen": fable_seen, "gold": gold})
    for rid in topic.get("featured", []):
        r = next(x for x in rules if x["id"] == rid)
        lids = []
        for lid, cts in by_lid.items():
            tids = set(r["term_ids"])
            if any(ti in tids for ti, *_ in cts):
                lids.append(lid)
        sizes[f"snips_{rid}.js"] = snippets_for(r, vocab, lids, ddir / f"snips_{rid}.js")
    json.dump(overview, open(ddir / "rules_overview.json", "w"), indent=1)
    for k, v in sizes.items():
        print(f"{v/1e6:8.2f} MB  {k}")
    print(f"papers in pages: {len(papers):,}; suspect-text flagged: {sum(p[6] for p in papers):,}; "
          f"fable-read papers: {len(fable_seen):,}; gold labels: {sum(len(v) for v in gold.values())}")


if __name__ == "__main__":
    main()
