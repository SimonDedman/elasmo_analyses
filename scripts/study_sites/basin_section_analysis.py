"""Where do right and wrong b_* basin flags come from, and would section or threshold changes help?

Uses the same reference as check_basin_columns.py (basins derived from model-read region text;
strong reference only). For every reference paper it re-counts each b_ term per labelled section
with the production matcher's own compiled patterns and section labeller, then:
  1. compares the section mix of mentions behind right flags and wrong flags (stored flags)
  2. tallies which terms drive wrong flags
  3. simulates alternative rules and scores them; papers are split in half by id hash, any
     data-derived choice (term exclusions) is made on the dev half and scored on the test half
  4. explains geo_study_ocean_basin's errors by its value distribution

  python3 scripts/study_sites/basin_section_analysis.py
Writes outputs/study_sites/basin_section_analysis.json. Changes nothing in the extractor.
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))
import extract_schema_columns as X  # noqa: E402
import check_basin_columns as C  # noqa: E402

TEXTS = ROOT / "outputs/validation/.fable_texts"
OUT = ROOT / "outputs/study_sites/basin_section_analysis.json"
CUR_W = dict(X._SECTION_WEIGHTS["b_"])
UNKNOWN_W = 0.25  # the matcher's default for a section label missing from the table
SECS = ["TITLE", "KEYWORDS", "ABSTRACT", "INTRODUCTION", "METHODS", "RESULTS", "RESULTS_AND_DISCUSSION", "DISCUSSION", "CONCLUSIONS", "OTHER"]


def half(lit):
    return "dev" if int(hashlib.sha1(lit.encode()).hexdigest(), 16) % 2 == 0 else "test"


def main():
    cols = X.compile_schema(X.BASIN)
    thr = {c.name[2:]: c.threshold for c in cols}
    names = pq.ParquetFile(C.PARQUET).schema.names
    bcols = [n for n in names if n.startswith("b_")]
    d = pd.read_parquet(C.PARQUET, columns=["literature_id", "title", "geo_study_ocean_basin"] + bcols)
    d["literature_id"] = d["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    d = d.drop_duplicates("literature_id").set_index("literature_id")
    ml = C.model_locations()
    papers = {}
    n = Counter()
    for lit, (cs, region) in ml.items():
        strength, acc = C.reference(cs, region)
        if strength != "strong" or lit not in d.index:
            continue
        tp = TEXTS / f"{lit}.txt"
        if not tp.exists():
            n["no_text"] += 1
            continue
        text = tp.read_text(errors="replace")
        secs = [("TITLE", str(d.at[lit, "title"] or ""))] + X._label_sections(text)
        counts = defaultdict(Counter)  # basin -> (term, section) -> raw count
        for c in cols:
            for ct in c.terms:
                if ct.regex is None:
                    continue
                for lab, chunk in secs:
                    k = X._count_matches(ct.regex, chunk)
                    if k:
                        counts[c.name[2:]][(ct.raw, lab)] += k
        stored = {b[2:] for b in bcols if not pd.isna(d.at[lit, b]) and d.at[lit, b]}
        # distinct basin groups named in the region text: each matching pattern is one group of
        # interchangeable basins; overlapping groups are merged, so two groups means two different basins
        groups = []
        for pat, bs in C.REGION_KEYS:
            if C.re.search(pat, region.lower()):
                bs = set(bs)
                for g in [g for g in groups if g & bs]:
                    bs |= g
                    groups.remove(g)
                groups.append(bs)
        papers[lit] = {"acc": acc, "counts": counts, "stored": stored, "half": half(lit), "groups": groups,
                       "labels": {lab for lab, _ in secs}, "geo": d.at[lit, "geo_study_ocean_basin"]}
        n["papers"] += 1
    print("papers with strong reference and text:", dict(n))

    def flags(p, w=CUR_W, th=thr, drop=frozenset(), dominance=None):
        score = {}
        for b, ct in p["counts"].items():
            s = sum(k * w.get(lab, UNKNOWN_W) for (term, lab), k in ct.items() if (b, term) not in drop)
            if s >= th[b]:
                score[b] = s
        if dominance and score:
            top = max(score.values())
            score = {b: s for b, s in score.items() if s >= dominance * top}
        return set(score)

    def evaluate(fn, which):
        k = Counter()
        for p in papers.values():
            if which != "all" and p["half"] != which:
                continue
            fl = fn(p)
            k["ref"] += 1
            if fl:
                k["flagged"] += 1
                k["has_right"] += bool(fl & p["acc"])
                k["has_wrong"] += bool(fl - p["acc"])
                k["clean"] += not (fl - p["acc"])
                k["nflags"] += len(fl)
        return k

    # control: does the re-count reproduce the stored flags?
    same = sum(flags(p) == p["stored"] for p in papers.values())
    print(f"control: re-counted current rule equals the stored b_ flags in {C.wil(same, len(papers))}")

    # 1. section mix behind right and wrong stored flags
    mix = {"right": Counter(), "wrong": Counter()}
    only = {"right": Counter(), "wrong": Counter()}
    nfl = Counter()
    term_tally = {"dev": defaultdict(Counter), "test": defaultdict(Counter)}
    for p in papers.values():
        for b in p["stored"]:
            cls = "right" if b in p["acc"] else "wrong"
            nfl[cls] += 1
            by_sec = Counter()
            for (term, lab), k in p["counts"].get(b, {}).items():
                by_sec[lab] += k
                term_tally[p["half"]][(b, term)][cls] += 1 if True else 0
            tot = sum(by_sec.values()) or 1
            for lab, k in by_sec.items():
                mix[cls][lab] += k / tot
            core = sum(by_sec[s] for s in ("TITLE", "KEYWORDS", "ABSTRACT", "METHODS"))
            only[cls]["none_in_title_keywords_abstract_methods"] += core == 0
            only[cls]["only_intro"] += bool(by_sec) and set(by_sec) <= {"INTRODUCTION"}
            only[cls]["in_title_or_keywords"] += (by_sec["TITLE"] + by_sec["KEYWORDS"]) > 0
            only[cls]["no_methods_header_found"] += "METHODS" not in p["labels"]
    print(f"\n1. SECTION MIX of mentions behind stored flags (mean share per flag): right n={nfl['right']}, wrong n={nfl['wrong']}")
    print(f"   {'section':24s} right   wrong")
    for s in SECS:
        print(f"   {s:24s} {mix['right'][s] / max(nfl['right'], 1):5.0%}   {mix['wrong'][s] / max(nfl['wrong'], 1):5.0%}")
    for k in ("in_title_or_keywords", "none_in_title_keywords_abstract_methods", "only_intro", "no_methods_header_found"):
        print(f"   {k:42s} right {C.wil(only['right'][k], nfl['right'])} | wrong {C.wil(only['wrong'][k], nfl['wrong'])}")

    # 2. terms behind wrong flags (all papers, for reading; exclusions below use the dev half only)
    allt = defaultdict(Counter)
    for h in term_tally.values():
        for k, v in h.items():
            allt[k].update(v)
    print("\n2. TERMS present behind flags: wrong / right (terms with at least 8 wrong)")
    for (b, term), v in sorted(allt.items(), key=lambda kv: -kv[1]["wrong"]):
        if v["wrong"] >= 8:
            print(f"   {b:16s} {term:22s} wrong {v['wrong']:4d}  right {v['right']:4d}  wrong share {v['wrong'] / (v['wrong'] + v['right']):.0%}")
    drop = frozenset(k for k, v in term_tally["dev"].items() if v["wrong"] >= 4 and v["wrong"] > v["right"])
    print("   terms excluded by the dev-half rule (wrong > right, at least 4 wrong):", sorted(drop))

    # 3. simulated rules
    w_intro = {**CUR_W, "INTRODUCTION": 0.25}
    w_intro_disc = {**CUR_W, "INTRODUCTION": 0.25, "DISCUSSION": 0.25, "RESULTS_AND_DISCUSSION": 0.25, "CONCLUSIONS": 0.25}
    w_core = {s: (CUR_W[s] if s in ("TITLE", "KEYWORDS", "ABSTRACT", "METHODS") else 0.0) for s in SECS}
    w_core2 = {**w_core, "ABSTRACT": 1.0}
    th2 = {**thr, "mediterranean": 2, "southern_ocean": 2}
    variants = {
        "V0 current rule": lambda p: flags(p),
        "V1 introduction weight 1 -> 0.25": lambda p: flags(p, w=w_intro),
        "V2 intro, discussion, conclusions 0.25": lambda p: flags(p, w=w_intro_disc),
        "V3 threshold 2 for Mediterranean and Southern Ocean": lambda p: flags(p, th=th2),
        "V4 drop dev-chosen terms": lambda p: flags(p, drop=drop),
        "V5 dominance: keep basins scoring >= half the top basin": lambda p: flags(p, dominance=0.5),
        "V6 title, keywords, abstract, methods only": lambda p: flags(p, w=w_core),
        "V7 as V6 with abstract weight 1": lambda p: flags(p, w=w_core2),
        "V8 = V2 + V3 + V4": lambda p: flags(p, w=w_intro_disc, th=th2, drop=drop),
        "V9 = V8 + dominance": lambda p: flags(p, w=w_intro_disc, th=th2, drop=drop, dominance=0.5),
        "V10 = V7 + V3 + V4 + dominance": lambda p: flags(p, w=w_core2, th=th2, drop=drop, dominance=0.5),
    }
    res = {"papers": len(papers), "variants": {}}
    print("\n3. SIMULATED RULES on the held-out half (coverage | has a right basin | also a wrong basin | all flags right | flags per flagged paper)")
    for name, fn in variants.items():
        k = evaluate(fn, "test")
        ka = evaluate(fn, "all")
        res["variants"][name] = {"test": dict(k), "all": dict(ka)}
        f = k["flagged"] or 1
        print(f"   {name:58s} {k['flagged'] / k['ref']:4.0%} | {k['has_right'] / f:4.0%} | {k['has_wrong'] / f:4.0%} | {k['clean'] / f:4.0%} | {k['nflags'] / f:.2f}   (n={k['ref']}, flagged {k['flagged']})")

    # 5. what the dominance rule costs studies that worked in more than one basin
    multi = [p for p in papers.values() if len(p["groups"]) >= 2]
    single = [p for p in papers.values() if len(p["groups"]) == 1]
    print(f"\n5. MULTI-BASIN STUDIES: {len(multi)} papers name two or more different basins, {len(single)} name one")
    print("   rule                                             | multi: basins found | multi: ALL basins found | single: basin found | all papers: also a wrong basin")
    res["multi_basin"] = {"n_multi": len(multi), "n_single": len(single), "rules": {}}
    rules = {"current": lambda p: flags(p)}
    for dth in (0.1, 0.2, 0.25, 0.33, 0.5):
        rules[f"dominance {dth}"] = (lambda p, dth=dth: flags(p, dominance=dth))
    rules["V8 weights + thresholds + dropped terms"] = lambda p: flags(p, w=w_intro_disc, th=th2, drop=drop)
    for dth in (0.2, 0.33, 0.5):
        rules[f"V8 + dominance {dth}"] = (lambda p, dth=dth: flags(p, w=w_intro_disc, th=th2, drop=drop, dominance=dth))
    for name, fn in rules.items():
        gf = gt = allf = 0
        for p in multi:
            fl = fn(p)
            hit = [bool(fl & g) for g in p["groups"]]
            gf += sum(hit)
            gt += len(hit)
            allf += all(hit)
        sf = sum(bool(fn(p) & p["groups"][0]) for p in single)
        fl_all = [fn(p) for p in papers.values()]
        flagged = sum(bool(f) for f in fl_all)
        wrong = sum(bool(f - p["acc"]) for f, p in zip(fl_all, papers.values()))
        res["multi_basin"]["rules"][name] = {"groups_found": gf, "groups": gt, "all_found": allf, "single_found": sf, "wrong": wrong, "flagged": flagged}
        print(f"   {name:48s} | {gf}/{gt} = {gf / gt:4.0%} | {allf}/{len(multi)} = {allf / len(multi):4.0%} | {sf}/{len(single)} = {sf / len(single):4.0%} | {wrong}/{flagged} = {wrong / flagged:4.0%}")

    # 4. geo_study_ocean_basin
    g = Counter()
    for p in papers.values():
        v = p["geo"]
        if isinstance(v, str) and v in C.GEO_MAP:
            g[(v, "right" if C.GEO_MAP[v] in p["acc"] else "wrong")] += 1
    print("\n4. geo_study_ocean_basin values against the reference:", {f"{a} {b}": c for (a, b), c in sorted(g.items())})
    res["geo_study_ocean_basin"] = {f"{a}|{b}": c for (a, b), c in g.items()}
    res["flag_origin"] = {c: {**dict(only[c]), "n": nfl[c]} for c in only}
    res["control_recount_equals_stored"] = [same, len(papers)]
    res["section_mix"] = {c: {s: mix[c][s] / max(nfl[c], 1) for s in SECS} for c in mix}
    res["dropped_terms"] = sorted(map(list, drop))
    OUT.write_text(json.dumps(res, indent=1))
    print(f"\nOK wrote {OUT}")


if __name__ == "__main__":
    main()
