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
SNIPS_PER_PAPER = 6      # Simon, 2026-10-06: six quotations per paper, one per distinct keyword
SNIP_MAX_CHARS = 600     # a "sentence" in OCR text can run for a page; cap it around the match
SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"“])|\n{2,}")
ABS_SHARDS = 64   # abstracts ship in 64 files keyed by literature_id mod 64, loaded by the page on demand
SHARED = ROOT / "docs" / "topic_review" / "shared"   # paper metadata, abstracts and the suggestion pool: one copy for every topic
TOPICS_JS = ROOT / "docs" / "topic_review" / "topics.js"


def build_shared(meta, suspects):
    """Every corpus paper that has cached text, in literature_id order: shared/papers.js and shared/abs/.
    Per-topic counts.js files index into this list, so it must only be rebuilt deliberately (--shared),
    and every topic rebuilt after it."""
    db = sqlite3.connect(f"file:{TEXT_CACHE}?mode=ro", uri=True, timeout=120)
    cached = {r[0] for r in db.execute("SELECT lid FROM sections")}
    lids = sorted((lid for lid in meta if lid in cached), key=int)
    papers, abstracts = [], {}
    for lid in lids:
        m = meta[lid]
        year = None if pd.isna(m.year) else int(m.year)
        papers.append([lid, (m.title or "")[:220], year, first_author(m.authors), (m.journal or "")[:70] if isinstance(m.journal, str) else "",
                       m.doi if isinstance(m.doi, str) else "", 1 if lid in suspects else 0])
        if isinstance(m.abstract, str) and len(m.abstract.strip()) > 40:
            abstracts.setdefault(int(lid) % ABS_SHARDS, {})[lid] = re.sub(r"\s+", " ", m.abstract.strip())
    SHARED.mkdir(parents=True, exist_ok=True)
    size = js(SHARED / "papers.js", "TR_PAPERS", papers)
    adir = SHARED / "abs"
    adir.mkdir(exist_ok=True)
    for old in adir.glob("a*.js"):
        old.unlink()
    for shard, d in abstracts.items():
        (adir / f"a{shard}.js").write_text("window.TR_ABS = Object.assign(window.TR_ABS || {}, "
                                           + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ");\n")
    print(f"shared: {len(papers):,} papers with cached text ({size/1e6:.1f} MB); abstracts for "
          f"{sum(len(d) for d in abstracts.values()):,} in {len(abstracts)} shards "
          f"({sum(f.stat().st_size for f in adir.glob('a*.js'))/1e6:.1f} MB)")
    return papers


def load_shared():
    path = SHARED / "papers.js"
    if not path.exists():
        return None
    return json.loads(path.read_text().split("=", 1)[1].strip().rstrip(";"))


def update_topics_js(summary):
    """Merge this topic's build summary into the landing page's register."""
    reg = {"topics": []}
    if TOPICS_JS.exists():
        reg = json.loads(TOPICS_JS.read_text().split("=", 1)[1].strip().rstrip(";"))
    found = False
    for t in reg["topics"]:
        if t["id"] == summary["id"]:
            t.update(summary)
            found = True
    if not found:
        reg["topics"].append(summary)
    TOPICS_JS.write_text("window.TR_TOPICS = " + json.dumps(reg, ensure_ascii=False) + ";\n")
WINDOW = 110   # no longer used for quotations (whole sentences since 2026-10-06); kept for reference


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


def sentence_around(chunk, start, end):
    """The whole sentence containing [start, end): back to the previous sentence end, forward to the
    next. Boundaries are a terminal mark followed by whitespace and a capital (so "Fig. 3" and "et al."
    mostly survive). Capped at SNIP_MAX_CHARS around the match, since OCR text has run-on 'sentences'."""
    lo_cap, hi_cap = max(0, start - SNIP_MAX_CHARS // 2), min(len(chunk), end + SNIP_MAX_CHARS // 2)
    lo = lo_cap
    # endpos must reach one past `start`, or the lookahead for the capital letter cannot see it
    for m in SENT_END.finditer(chunk, lo_cap, min(len(chunk), start + 1)):
        if m.end() <= start:
            lo = m.end()
    hi = hi_cap
    m = SENT_END.search(chunk, end, hi_cap)
    if m:
        hi = m.start()
    return lo, hi


def snippets_for(rule, vocab, lids, out_path):
    """Up to SNIPS_PER_PAPER quotations per paper for THIS rule's terms, read from the text
    cache: highest-weighted section first, one per distinct term, each the full sentence
    containing the first match (capped), with the match marked «like this»."""
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
        # one quotation per sentence: two keywords in the same sentence are both marked in one entry
        spans, seen = {}, set()   # (section i, lo, hi) -> [tid, label, [(start, end), ...]]
        for i in order:
            label, chunk = sections[i]
            for tid, ct in terms:
                if tid in seen or ct.regex is None:
                    continue
                m = ct.regex.search(chunk)
                if not m:
                    continue
                seen.add(tid)
                lo, hi = sentence_around(chunk, m.start(), m.end())
                key = next((k for k in spans if k[0] == i and k[1] < m.end() and m.start() < k[2]), None)
                if key is None:
                    if len(spans) == SNIPS_PER_PAPER:
                        continue
                    spans[(i, lo, hi)] = [tid, label, [(m.start(), m.end())]]
                else:
                    spans[key][2].append((m.start(), m.end()))
        got = []
        for (i, lo, hi), (tid, label, ranges) in spans.items():
            chunk = sections[i][1]
            text = chunk[lo:hi]
            for a, b in sorted(ranges, reverse=True):
                a, b = max(a, lo), min(b, hi)
                text = text[:a - lo] + "«" + text[a - lo:b - lo] + "»" + text[b - lo:]
            got.append([tid, SEC_IDX.get(label, 9), " ".join(text.split())])
        if got:
            out[str(lid)] = got
    return js(out_path, "TR_SNIPS", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, type=Path)
    ap.add_argument("--shared", action="store_true", help="(re)build shared/papers.js and shared/abs/ first; every other topic must then be rebuilt too")
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

    meta_df = pd.read_parquet(X.INPUT_PARQUET, columns=["literature_id", "title", "authors", "year", "journal", "doi", "abstract"])
    meta_df = meta_df[meta_df.literature_id.notna()]
    meta = {str(r.literature_id).split(".")[0]: r for r in meta_df.itertuples()}
    suspects = set()
    if SUSPECTS.exists():
        suspects = {str(r["lid"]).split(".")[0] for r in csv.DictReader(open(SUSPECTS))}

    papers = None if args.shared else load_shared()
    if papers is None:
        papers = build_shared(meta, suspects)
    lid2i = {p[0]: i for i, p in enumerate(papers)}
    counts, by_lid = [[] for _ in papers], {}
    status = {"ok": 0, "no_pdf": 0, "no_text": 0, "not_in_shared": 0}
    for line in open(tdir / "features.jsonl"):
        p = json.loads(line)
        status[p["status"]] += 1
        if p["status"] != "ok" or not p["counts"]:
            continue
        lid = str(p["lid"]).split(".")[0]
        if lid in by_lid:   # the corpus table repeats a few literature_ids: keep the first
            status["duplicate_id"] = status.get("duplicate_id", 0) + 1
            continue
        i = lid2i.get(lid)
        if i is None:       # a paper whose text was cached after shared/papers.js was built: rebuild with --shared
            status["not_in_shared"] += 1
            continue
        flat = []
        for ti, s, raw, prox in p["counts"]:
            flat += [ti * 10 + s, raw, prox]
        counts[i] = flat
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
            # the extractor stopped rounding on 2026-09-25: compare the weighted total as it stands
            is_in = gate and total >= r["threshold"]
            n_in += is_in
            n_gate_fail += (not gate)
            if gate and abs(total - r["threshold"]) <= 0.5:
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
        "topic": {k: topic.get(k) for k in ("id", "title", "champion", "discipline")}, "sections": SECTIONS,
        "vocab": [v["term"] for v in vocab], "vocab_cs": [int(v["cs"]) for v in vocab],
        "team": TEAM, "rules": rules, "section_weights": X._SECTION_WEIGHTS, "featured": topic.get("featured", []),
        "overview": overview, "coverage": {**json.load(open(tdir / "coverage.json")), **status, "papers_in_pages": len(by_lid),
                                           "shared_papers": len(papers), "suspect_text": sum(p[6] for p in papers)},
        "control": control, "built": time.strftime("%Y-%m-%d %H:%M %Z")})
    sizes["counts.js"] = js(ddir / "counts.js", "TR_COUNTS", counts)
    for stale in ("papers.js",):   # per-topic copies from before the shared layout (2026-10-06)
        if (ddir / stale).exists():
            (ddir / stale).unlink()
    if (ddir / "abs").exists():
        for f in (ddir / "abs").glob("a*.js"):
            f.unlink()
        (ddir / "abs").rmdir()
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
    disc = next((o for o in overview if o["id"] == topic.get("discipline")), overview[0])
    update_topics_js({"id": topic["id"], "title": topic["title"], "champion": topic.get("champion"), "discipline": topic.get("discipline"),
                      "n_rules": len(rules), "n_live": sum(1 for r in rules if r["kind"] == "live"),
                      "n_proposed": sum(1 for r in rules if r["kind"] != "live"),
                      "papers_with_hit": disc["papers_with_hit"], "papers_in": disc["papers_in"], "papers_any_hit": len(by_lid),
                      "fable_seen": len(fable_seen), "built": time.strftime("%Y-%m-%d %H:%M %Z")})
    for k, v in sizes.items():
        print(f"{v/1e6:8.2f} MB  {k}")
    print(f"papers with a hit in this topic: {len(by_lid):,} of {len(papers):,} shared; suspect-text flagged: {sum(p[6] for p in papers):,}; "
          f"fable-read papers: {len(fable_seen):,}; gold labels: {sum(len(v) for v in gold.values())}")


if __name__ == "__main__":
    main()
