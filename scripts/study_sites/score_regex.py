"""Score regex_coords.extract() against the Fable gold pilot.

Gold is SILVER: a model's reading, checked here only mechanically (each gold
coordinate string and quote must occur in the paper text). Report that check
beside every score.

Paper level : does the paper print study-site coordinates (gold: any site with
              lat_dd and lon_dd) vs regex (tier A point; --tiers AC adds tier C)
Point level : gold point matched when a regex point lies within TOL degrees
Corpus level: stratum-weighted estimates (strata sizes from sample.json)

  python3 scripts/study_sites/score_regex.py [--split dev|test|all] [--tiers A|AC] [--show misses|false|both]
"""
import argparse
import importlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
RUN = ROOT / "outputs/study_sites/gold_pilot"
TEXTS = ROOT / "outputs/validation/.fable_texts"
TOL = 0.02  # INFERRED: about 2 km; absorbs rounding of seconds and model arithmetic


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


def fmt(k, n):
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} = {p:.0%} (95% CI {lo:.0%}-{hi:.0%})" if n else "0/0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--tiers", default="A")
    ap.add_argument("--show", default="")
    ap.add_argument("--module", default="regex_coords")
    a = ap.parse_args()
    rx = importlib.import_module(a.module)
    sample = json.loads((RUN / "sample.json").read_text())
    rows, missing = [], 0
    gold_strings = gold_strings_found = quotes = quotes_found = 0
    for r in sample:
        if a.split != "all" and r["split"] != a.split:
            continue
        cp = RUN / "cache" / f"{r['lit_id']}.json"
        if not cp.exists():
            missing += 1
            continue
        g = json.loads(cp.read_text())["output"]
        text = (TEXTS / f"{r['lit_id']}.txt").read_text(errors="replace")
        nt = norm(text)
        gpts = [(s["lat_dd"], s["lon_dd"], s) for s in g["sites"] if s["lat_dd"] is not None and s["lon_dd"] is not None]
        for s in g["sites"]:
            for v in (s["lat_verbatim"], s["lon_verbatim"]):
                if v:
                    gold_strings += 1
                    gold_strings_found += norm(v) in nt
            if s["quote"]:
                quotes += 1
                quotes_found += norm(s["quote"]) in nt
        e = rx.extract(text)
        rpts = [(p["lat"], p["lon"], p) for p in e["points"]]
        if "C" in a.tiers:
            rpts += [(p["lat"], p["lon"], p) for p in e["nodeg"]]
        near = lambda p, q: abs(p[0] - q[0]) <= TOL and abs(p[1] - q[1]) <= TOL
        g_hit = sum(any(near(gp, rp) for rp in rpts) for gp in gpts)
        r_hit = sum(any(near(rp, gp) for gp in gpts) for rp in rpts)
        rows.append({**r, "gold_n": len(gpts), "regex_n": len(rpts), "gold_matched": g_hit, "regex_matched": r_hit,
                     "gold": g, "gpts": gpts, "rpts": rpts, "axes": len(e["axes"]),
                     "gold_extent": any(g["extent"][k] is not None for k in ("lat_min", "lat_max", "lon_min", "lon_max"))})
    print(f"split={a.split} tiers={a.tiers} regex={getattr(rx, 'VERSION', '?')}: {len(rows)} papers scored, {missing} sampled papers have NO gold yet")
    print(f"gold mechanical check: coordinate strings found verbatim in text {fmt(gold_strings_found, gold_strings)}; quotes found {fmt(quotes_found, quotes)}")
    print("\nPAPER LEVEL (prints study-site coordinates?)   by stratum: gold+ | regex+ | both | regex-only | gold-only")
    est_gold = est_both = est_regex = 0.0
    for s in ["A", "BC", "suspect", "clean"]:
        rs = [r for r in rows if r["stratum"] == s]
        if not rs:
            continue
        gp = sum(r["gold_n"] > 0 for r in rs)
        rp = sum(r["regex_n"] > 0 for r in rs)
        both = sum(r["gold_n"] > 0 and r["regex_n"] > 0 for r in rs)
        N = rs[0]["stratum_size"]
        est_gold += N * gp / len(rs)
        est_both += N * both / len(rs)
        est_regex += N * rp / len(rs)
        print(f"  {s:8s} n={len(rs):3d} of {N:6d}: {gp:3d} | {rp:3d} | {both:3d} | {rp - both:3d} | {gp - both:3d}   gold extent-only papers: {sum(r['gold_extent'] and r['gold_n'] == 0 for r in rs)}")
    tp = sum(r["gold_n"] > 0 and r["regex_n"] > 0 for r in rows)
    print(f"  sample recall    {fmt(tp, sum(r['gold_n'] > 0 for r in rows))}   (unweighted; strata are deliberately unequal)")
    print(f"  sample precision {fmt(tp, sum(r['regex_n'] > 0 for r in rows))}")
    if est_gold:
        print(f"  CORPUS ESTIMATE (stratum-weighted, indicative): papers printing study-site coordinates ~{est_gold:,.0f}; regex finds ~{est_both:,.0f} of them = recall {est_both / est_gold:.0%}; regex flags ~{est_regex:,.0f}, precision {est_both / est_regex:.0%}")
    G = sum(r["gold_n"] for r in rows)
    Rn = sum(r["regex_n"] for r in rows)
    print(f"\nPOINT LEVEL (within {TOL} deg; gold capped at 30 sites per paper, so regex extras in long station tables are not errors)")
    print(f"  gold points recovered by regex {fmt(sum(r['gold_matched'] for r in rows), G)}")
    capped = [r for r in rows if r["gold"]["n_sites_stated"] > len(r["gpts"])]
    unc = [r for r in rows if r not in capped]
    print(f"  regex points confirmed by gold {fmt(sum(r['regex_matched'] for r in unc), sum(r['regex_n'] for r in unc))} (papers where gold was not capped; {len(capped)} capped papers excluded; all papers: {sum(r['regex_matched'] for r in rows)}/{Rn})")
    if a.show:
        for r in rows:
            miss = [gp for gp in r["gpts"] if not any(abs(gp[0] - rp[0]) <= TOL and abs(gp[1] - rp[1]) <= TOL for rp in r["rpts"])]
            false = [rp for rp in r["rpts"] if not any(abs(gp[0] - rp[0]) <= TOL and abs(gp[1] - rp[1]) <= TOL for gp in r["gpts"])]
            if a.show in ("misses", "both") and miss:
                print(f"\nMISS lit {r['lit_id']} [{r['stratum']}] gold {r['gold_n']} regex {r['regex_n']} notes: {r['gold']['notes'][:150]}")
                for la, lo, s in miss[:4]:
                    print(f"   gold ({la}, {lo}) lat='{s['lat_verbatim']}' lon='{s['lon_verbatim']}' | {norm(s['quote'])[:170]}")
            if a.show in ("false", "both") and false and r not in capped:
                print(f"\nFALSE lit {r['lit_id']} [{r['stratum']}] gold {r['gold_n']} regex {r['regex_n']} other_coords={r['gold']['other_coordinates']} notes: {r['gold']['notes'][:120]}")
                for la, lo, p in false[:4]:
                    print(f"   regex ({la}, {lo}) tier {p['tier']} | {p['snippet'][:170]}")


if __name__ == "__main__":
    main()
