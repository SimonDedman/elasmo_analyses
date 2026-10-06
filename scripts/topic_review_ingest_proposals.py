#!/usr/bin/env python3
"""Merge reviewer-proposed keywords from topic-review exports into the topic definition.

    python3 scripts/topic_review_ingest_proposals.py --topic data/topic_review/fisheries.json export1.json [export2.json ...]

The dashboard (docs/topic_review/review.html) lets a reviewer type a keyword the corpus has never
been counted for; it is kept on their proposed list and goes out with Export as `proposed_terms`
([{term, rule, when}]). This script adds each distinct term to the topic JSON under `reviewer_terms`
(with who proposed it, for which rule, and when), which build_topic_features.build_vocab counts
like any other term. Then re-run, in order:

    python3 scripts/build_topic_features.py --topic data/topic_review/fisheries.json      # ~10 min from the text cache
    python3 scripts/build_topic_review_pages.py --topic data/topic_review/fisheries.json  # ~2 min

after which the term appears in the Rule tab as a tickable keyword and the optimiser can test it.
Case-sensitive acronyms: pass --cs TERM for any term that must match as written (default is
case-insensitive, the same rule the extractor applies to ordinary terms).
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, type=Path)
    ap.add_argument("exports", nargs="+", type=Path, help="JSON files from the dashboard's Export button")
    ap.add_argument("--cs", action="append", default=[], help="treat this term as case-sensitive (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    topic = json.load(open(args.topic))
    have = {t["term"].lower(): t for t in topic.get("reviewer_terms", [])}
    existing_vocab = set()
    for col in topic.get("proposed_rules", []):
        existing_vocab.update(t.lower() for t in col.get("terms", []) + col.get("anchors", []))
    vocab_json = args.topic.parent.parent.parent / "outputs" / "topic_review" / topic["id"] / "vocab.json"
    if vocab_json.exists():
        existing_vocab.update(v["term"].lower() for v in json.load(open(vocab_json))["vocab"])

    added, already_counted, dupes, n_seen = [], [], 0, 0
    for f in args.exports:
        j = json.load(open(f))
        who = j.get("reviewer", f.stem)
        for p in j.get("proposed_terms", []):
            n_seen += 1
            term = p["term"].strip()
            if not term:
                continue
            if term.lower() in existing_vocab:
                already_counted.append(term)
                continue
            if term.lower() in have:
                dupes += 1
                continue
            rec = {"term": term, "cs": term in args.cs, "proposed_by": who, "for_rule": p.get("rule"), "when": p.get("when")}
            have[term.lower()] = rec
            added.append(rec)

    topic["reviewer_terms"] = sorted(have.values(), key=lambda t: t["term"].lower())
    print(f"proposals seen: {n_seen}; added: {len(added)}; already in the counted vocabulary: {len(already_counted)}; "
          f"already on the reviewer list: {dupes}; reviewer_terms now: {len(topic['reviewer_terms'])}")
    for r in added:
        print(f"  + {r['term']}  ({r['proposed_by']}, for {r['for_rule']}, {r['when']}){'  [case-sensitive]' if r['cs'] else ''}")
    for t in already_counted:
        print(f"  = {t}: already counted, add it from the Rule tab's box instead")
    if args.dry_run:
        print("dry run: topic file not written")
        return
    if added:
        json.dump(topic, open(args.topic, "w"), indent=1, ensure_ascii=False)
        print(f"wrote {args.topic}. Next: build_topic_features.py then build_topic_review_pages.py (see --help).")
    else:
        print("nothing to add; topic file untouched")


if __name__ == "__main__":
    sys.exit(main())
