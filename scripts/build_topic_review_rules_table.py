#!/usr/bin/env python3
"""One table of every rule in every topic: docs/topic_review/rules.js, read by docs/topic_review/rules.html.

Reads   data/topic_review/<topic>.json              (champion, featured rules, proposed rules + provenance)
        docs/topic_review/<topic>/data/rules_overview.json   (keywords, anchors, threshold, counts, Fable-silver
                                                    agreement; written by build_topic_review_pages.py)
        docs/topic_review/topics.js                 (landing order and groups)
        outputs/extraction_rules.json               (the defining line of each live column in the extractor,
                                                    written by build_extraction_rules_reference.py)
Writes  docs/topic_review/rules.js

Run after every topic has been rebuilt (the last step of scripts/topic_review_build_all.sh); a column that
sits in several topics (pr_light: behaviour, physiology, sensory) appears once per topic with the same counts.

    python3 scripts/build_topic_review_rules_table.py
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "topic_review"
RULES_JSON = ROOT / "outputs" / "extraction_rules.json"
GH_DOCS = "https://github.com/SimonDedman/elasmo_analyses/blob/main/docs/"


def main():
    reg = json.loads((DOCS / "topics.js").read_text().split("=", 1)[1].strip().rstrip(";"))["topics"]
    order = {t["id"]: (t.get("order", 99), t.get("group", "")) for t in reg}
    src = {}
    if RULES_JSON.exists():
        for prefix, cols in json.loads(RULES_JSON.read_text()).items():
            if prefix.startswith("_"):
                continue
            for name, r in cols.items():
                src[name] = {"line": r.get("line"), "url": r.get("url"), "cs": r.get("case_sensitive_terms", [])}
    rows, topics_done, missing = [], [], []
    for tj in sorted((ROOT / "data" / "topic_review").glob("*.json")):
        topic = json.loads(tj.read_text())
        ov_path = DOCS / topic["id"] / "data" / "rules_overview.json"
        if not ov_path.exists():
            missing.append(topic["id"])
            continue
        featured = set(topic.get("featured", []))
        proposed = {p["id"]: p for p in topic.get("proposed_rules", [])}
        prov = topic.get("provenance", "")
        for o in json.loads(ov_path.read_text()):
            live = o["kind"] == "live"
            s = o.get("silver") or {}
            if live:
                source = src.get(o["id"], {})
                srow = {"label": f"L{source['line']}" if source.get("line") else "", "url": source.get("url")}
                cs = source.get("cs", [])
            else:
                p = proposed.get(o["id"], {})
                xlsx = "2026-09-10_FisheriesApproach_keywords_DRG.xlsx" if "FisheriesApproach_keywords_DRG" in prov else None
                srow = {"label": f"{p.get('section', '')} / {p.get('category', '')}".strip(" /"), "url": GH_DOCS + xlsx if xlsx else None}
                cs = p.get("case_sensitive", [])
            rows.append({"topic": topic["id"], "topic_title": topic["title"], "group": order.get(topic["id"], (99, ""))[1],
                         "order": order.get(topic["id"], (99, ""))[0], "champion": topic.get("champion"),
                         "discipline": o["id"] == topic.get("discipline"), "featured": o["id"] in featured,
                         "id": o["id"], "label": o["label"], "kind": o["kind"], "prefix": o.get("prefix", o["id"].split("_")[0] + "_"),
                         "terms": o["terms"], "anchors": o["anchors"], "cs": cs, "threshold": o["threshold"],
                         "proximity": o.get("proximity"), "meaning": o.get("meaning"),
                         "papers_with_hit": o["papers_with_hit"], "papers_in": o["papers_in"], "margin": o["margin"],
                         "anchor_gate_fails": o["anchor_gate_fails"], "fable_in": o["fable_in"], "gold": o["gold"],
                         "precision": s.get("precision"), "recall": s.get("recall"), "f1": s.get("f1"), "unreach": s.get("unreach"),
                         "silver_n": s.get("n"), "source": srow})
        topics_done.append(topic["id"])
    out = {"rows": rows, "generated": time.strftime("%Y-%m-%d %H:%M %Z"), "topics": topics_done, "missing": missing,
           "n_distinct_rules": len({r["id"] for r in rows}),
           "extractor_commit": (json.loads(RULES_JSON.read_text()).get("_meta", {}).get("commit") if RULES_JSON.exists() else None)}
    (DOCS / "rules.js").write_text("window.TR_RULES = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"{len(rows)} rows ({out['n_distinct_rules']} distinct rules) from {len(topics_done)} topics -> docs/topic_review/rules.js"
          + (f"; topics without an overview: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
