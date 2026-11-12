"""Build the study-site pilot summary and the regional-summaries placeholder page.

Reads the Fable gold pilot cache, weights each stratum by its corpus size, and writes
  outputs/study_sites/pilot_summary.json   (every figure the page and the spec quote)
  docs/regions/index.html                   (placeholder page; linked from the landing page and published 2026-11-12)
Rerun after any further gold papers land; the page is rebuilt from the JSON, never hand-edited.

  python3 scripts/study_sites/build_region_placeholder.py
"""
import html
import json
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "outputs/study_sites/gold_pilot"
OUT_JSON = ROOT / "outputs/study_sites/pilot_summary.json"
PAGE = ROOT / "docs/regions/index.html"

ROWS = [  # key, label shown on the page
    ("field", "Has a physical study area"),
    ("place", "Names a specific place (bay, reef, island, port)"),
    ("coords", "Prints study-site coordinates"),
    ("extent", "Prints a bounding range for the study area"),
    ("other", "Prints coordinates that are not study sites (map grid labels, museum localities, earlier records)"),
]


def wilson(p, n, z=1.96):
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def summarise():
    sample = json.loads((RUN / "sample.json").read_text())
    strata = {}
    for r in sample:
        cp = RUN / "cache" / f"{r['lit_id']}.json"
        if not cp.exists():
            continue
        g = json.loads(cp.read_text())["output"]
        t = strata.setdefault(r["stratum"], {"n": 0, "N": r["stratum_size"], **{k: 0 for k, _ in ROWS}})
        t["n"] += 1
        t["field"] += g["has_field_location"]
        t["place"] += bool(g["finest_place"])
        t["coords"] += any(s["lat_dd"] is not None and s["lon_dd"] is not None for s in g["sites"])
        t["extent"] += any(g["extent"][k] is not None for k in ("lat_min", "lat_max", "lon_min", "lon_max"))
        t["other"] += g["other_coordinates"]
    if not strata:
        raise SystemExit("FAIL: no gold cache files")
    N = sum(t["N"] for t in strata.values())
    n = sum(t["n"] for t in strata.values())
    rows = []
    for k, label in ROWS:
        share = sum(t["N"] * t[k] / t["n"] for t in strata.values()) / N
        # stratified standard error; indicative only at these stratum sizes
        var = sum((t["N"] / N) ** 2 * (t[k] / t["n"]) * (1 - t[k] / t["n"]) / t["n"] for t in strata.values())
        rows.append({"key": k, "label": label, "share": round(share, 4), "se": round(math.sqrt(var), 4),
                     "papers_est": round(share * N), "sample_yes": sum(t[k] for t in strata.values())})
    return {"built": time.strftime("%Y-%m-%d"), "papers_read": n, "papers_sampled": len(sample), "corpus_texts": N,
            "reader": "Claude Fable 5.2 (model reading, not hand-checked)", "kind": "stratum-weighted estimate, indicative",
            "strata": strata, "rows": rows}


def page(s):
    e = html.escape
    trs = "\n".join(
        f"<tr><td>{e(r['label'])}</td><td class='n'>{r['share']:.0%}</td>"
        f"<td class='n'>{max(0, r['share'] - 1.96 * r['se']):.0%} to {min(1, r['share'] + 1.96 * r['se']):.0%}</td></tr>"
        for r in s["rows"])
    by = {r["key"]: r for r in s["rows"]}
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Regional summaries and the Species Atlas</title>
<link rel="icon" href="../assets/logo/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="../assets/logo/favicon-32.png">
<style>
/* Placeholder page: what is planned, how far it has got, and the first measurement. Built by scripts/study_sites/build_region_placeholder.py */
:root{{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--border:rgba(11,11,11,.10);--seq:#2a78d6;--warn:#eda100;--good:#1baf7a}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);--seq:#3987e5}}}}
:root[data-theme="dark"]{{--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);--seq:#3987e5}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:820px;margin:0 auto;padding:24px 16px 60px}}
h1{{font-size:28px;margin:0 0 4px;text-wrap:balance}}
h2{{font-size:19px;margin:0}}
p{{margin:10px 0}}.lede{{color:var(--ink2)}}
a{{color:var(--seq)}}
.badge{{display:inline-block;font-size:12.5px;border:1px solid var(--warn);color:var(--warn);border-radius:10px;padding:1px 9px;margin-bottom:10px}}
details{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 16px;margin:14px 0}}
summary{{cursor:pointer}}summary h2{{display:inline}}
table{{border-collapse:collapse;width:100%;margin:10px 0;font-size:15px}}
th,td{{text-align:left;padding:7px 8px;border-top:1px solid var(--grid);vertical-align:top}}
th{{font-size:13px;color:var(--ink2);border-top:0}}
.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
ol.steps{{padding-left:22px}}ol.steps li{{margin:6px 0}}
.st{{font-size:12.5px;border-radius:10px;padding:0 8px;margin-left:6px;border:1px solid var(--muted);color:var(--ink2);white-space:nowrap}}
.st.done{{border-color:var(--good);color:var(--good)}}
.note{{font-size:13.5px;color:var(--ink2)}}
</style>
</head>
<body><div class="wrap">
<span class="badge">In development</span>
<h1>Regional summaries and the Species Atlas</h1>
<p class="lede">Shark Oracle is planning a map of where chondrichthyan research has been done, species by species, and a summary page for each region. This page records the plan and how far it has got.</p>

<details open><summary><h2>What we are building</h2></summary>
<p><b>Species Atlas.</b> A map with a marker on each study site, so you can zoom to a region and see which species have been studied there, by whom, and in which papers. A <a href="../species_atlas/">first version</a> maps papers by country and ocean basin.</p>
<p><b>Regional summaries.</b> One page per region that gathers the papers, species, topics, and threats studied there, kept current as new papers arrive and curated by a regional champion. They will sit beside the per-species summaries, and the map will be the way in to both.</p>
<p><b>Sensitive sites.</b> Locations of aggregation sites, pupping grounds, and similar sites of threatened species will be shown at country or ocean-basin level by default.</p>
</details>

<details open><summary><h2>Progress</h2></summary>
<ol class="steps">
<li>Study country recorded for part of the corpus; ocean basin for more. <span class="st done">in the database</span></li>
<li>First measurement of what papers print about their study sites (table below). <span class="st done">done, {e(s['built'])}</span></li>
<li>Design for extracting study sites and their extents from each paper. <span class="st">drafted, under review</span></li>
<li>Matching place names to a marine gazetteer, checked against papers that print both a name and coordinates. <span class="st">not started</span></li>
<li>Study-site extraction across the corpus. <span class="st">not started</span></li>
<li><a href="../species_atlas/">Species Atlas</a>, first version: papers by study country and ocean basin. <span class="st done">live</span></li>
<li>Species Atlas at the level of study sites, with distances to port. <span class="st">not started</span></li>
<li>Regional summary pages and regional champions. <span class="st">not started</span></li>
</ol>
</details>

<details open><summary><h2>What papers print about where they worked</h2></summary>
<p>We read a stratified sample of {s['papers_read']} papers and recorded what each one states about its study sites. Shares are weighted to the {s['corpus_texts']:,} papers with readable text.</p>
<table>
<thead><tr><th>Paper content</th><th class="n">Share of papers</th><th class="n">Rough 95% range</th></tr></thead>
<tbody>
{trs}
</tbody></table>
<p>Most papers name a place ({by['place']['share']:.0%}) and few print coordinates ({by['coords']['share']:.0%}), so the atlas will rest mainly on matching place names to a gazetteer, with printed coordinates as the precise minority.</p>
<p class="note">Indicative figures from a small sample, read by a language model ({e(s['reader'].split(' (')[0])}) and not yet checked by hand. The ranges are approximate. Built {e(s['built'])}.</p>
</details>

<p class="note"><a href="../">Back to Shark Oracle</a></p>
</div></body></html>
"""


def main():
    s = summarise()
    OUT_JSON.write_text(json.dumps(s, indent=1))
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page(s))
    print(f"OK {s['papers_read']} gold papers of {s['papers_sampled']} sampled; corpus {s['corpus_texts']:,}")
    for r in s["rows"]:
        print(f"   {r['share']:.0%} +/- {1.96 * r['se']:.0%}  {r['label']}")
    print(f"wrote {OUT_JSON}\nwrote {PAGE}\nnext: commit and publish docs/regions/ if the figures changed")


if __name__ == "__main__":
    main()
