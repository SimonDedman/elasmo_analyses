"""Coarse Species Atlas (country and ocean-basin level): docs/species_atlas/index.html.

Study country comes ONLY from papers a language model has read (Fable v1 corpus cache, Fable v2
cache, the study-site pilot). The older rule-based column geo_study_country is NOT used:
MEASURED 2026-11-11, it agreed with the model-read country in 167 of 267 papers (63%), and where the
title or abstract named only one of the two countries it named the model's 47 times and the
column's 3 times.

Ocean basin comes from the sea or ocean named in the model-read region text
(check_basin_columns.primary_basins); the keyword columns bd_* are used only as a cross-check,
reported in the coverage file. Basin polygons: docs/species_atlas/basins.json
(scripts/study_sites/export_basins_geojson.R).

Species come from the sp_* columns of the corpus parquet. Country polygons:
docs/species_atlas/countries.json (scripts/study_sites/export_countries_geojson.R).

  python3 scripts/study_sites/build_coarse_atlas.py
The page is self-contained (data inlined) so it opens from disk. Linked from the landing page and published 2026-11-12.
"""
import glob
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))
import check_basin_columns as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "outputs/literature_review_enriched.parquet"
OUT = ROOT / "docs/species_atlas"
COVER = ROOT / "outputs/study_sites/coarse_atlas_coverage.json"

ALIAS = {  # model-read name (lower case) -> Natural Earth admin name
    "usa": "United States of America", "us": "United States of America", "united states": "United States of America",
    "u.s.a.": "United States of America", "hawaii": "United States of America", "alaska": "United States of America",
    "puerto rico": "Puerto Rico", "uk": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom",
    "wales": "United Kingdom", "northern ireland": "United Kingdom", "great britain": "United Kingdom",
    "bahamas": "The Bahamas", "the bahamas": "The Bahamas", "tanzania": "United Republic of Tanzania",
    "serbia": "Republic of Serbia", "korea": "South Korea", "republic of korea": "South Korea",
    "russian federation": "Russia", "ivory coast": "Ivory Coast", "côte d'ivoire": "Ivory Coast", "cote d'ivoire": "Ivory Coast",
    "cabo verde": "Cabo Verde", "cape verde": "Cabo Verde", "timor-leste": "East Timor", "east timor": "East Timor",
    "czech republic": "Czechia", "uae": "United Arab Emirates", "burma": "Myanmar", "reunion": "France", "réunion": "France",
    "la réunion": "France", "mayotte": "France", "french guiana": "France", "guadeloupe": "France", "martinique": "France",
    "azores": "Portugal", "madeira": "Portugal", "canary islands": "Spain", "galapagos": "Ecuador", "galápagos": "Ecuador",
    "congo": "Republic of the Congo", "republic of congo": "Republic of the Congo", "dr congo": "Democratic Republic of the Congo",
    "drc": "Democratic Republic of the Congo", "guinea-bissau": "Guinea-Bissau", "sao tome and principe": "São Tomé and Principe",
    "são tomé and príncipe": "São Tomé and Principe", "micronesia": "Federated States of Micronesia", "macau": "Macao S.A.R",
    "hong kong": "Hong Kong S.A.R.", "palestine": "Palestine", "curacao": "Curaçao", "the netherlands": "Netherlands",
    "holland": "Netherlands", "the gambia": "Gambia", "viet nam": "Vietnam", "brunei darussalam": "Brunei",
    "trinidad & tobago": "Trinidad and Tobago", "st. lucia": "Saint Lucia", "new caledonia": "New Caledonia",
    "tasmania": "Australia", "sicily": "Italy", "sardinia": "Italy", "corsica": "France", "crete": "Greece",
    "svalbard": "Norway", "greenland": "Greenland", "eswatini": "eSwatini", "turkiye": "Turkey", "türkiye": "Turkey",
    "falkland islands": "Falkland Islands", "virgin islands": "United States Virgin Islands", "us virgin islands": "United States Virgin Islands",
}
NOT_A_COUNTRY = {"", "none", "n/a", "na", "global", "worldwide", "unknown", "not stated", "international", "high seas",
                 "multiple", "various", "-", "international waters"}


def model_countries():
    """lit_id -> (source, [names]). Later sources win: pilot > v2 > v1 (newest prompt last)."""
    out = {}
    for g in glob.glob(str(ROOT / "outputs/validation/.fable_corpus_cache/*.txt")):
        t = open(g, errors="replace").read()
        m, c = re.search(r"^LIT:\s*(\S+)", t, re.M), re.search(r"^COUNTRY:[ \t]*(.*)$", t, re.M)
        if m:
            out[m.group(1)] = ("fable_v1", [x.strip() for x in re.split(r"[;,/]", c.group(1))] if c else [])
    for g in glob.glob(str(ROOT / "outputs/validation/.fable_v2_cache/*.json")):
        o = json.load(open(g))
        out[str(o["lit_id"])] = ("fable_v2", o["output"].get("study_country") or [])
    for g in glob.glob(str(ROOT / "outputs/study_sites/gold_pilot/cache/*.json")):
        o = json.load(open(g))
        out[str(o["lit_id"])] = ("site_pilot", o["output"].get("country") or [])
    return out


def main():
    geo = json.loads((OUT / "countries.json").read_text())
    ne = {}
    for f in geo["features"]:
        p = f["properties"]
        for k in ("admin", "name", "name_long"):
            ne.setdefault(str(p[k]).lower(), p["adm0_a3"])
    a3name = {f["properties"]["adm0_a3"]: f["properties"]["admin"] for f in geo["features"]}

    def to_a3(name):
        k = re.sub(r"\s+", " ", name.strip().lower()).strip(" .")
        k = re.sub(r"\s*\(.*\)$", "", k)
        if k in NOT_A_COUNTRY:
            return None, "not_a_country"
        if k in ALIAS:
            k = ALIAS[k].lower()
        return (ne[k], "ok") if k in ne else (None, "unmapped")

    names = pq.ParquetFile(PARQUET).schema.names
    sp_cols = [n for n in names if n.startswith("sp_")]
    d = pd.read_parquet(PARQUET, columns=["literature_id", "title", "authors", "year", "doi"] + sp_cols)
    d["literature_id"] = d["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    d = d.drop_duplicates("literature_id").set_index("literature_id")
    sp_name = {c: c[3:].replace("_", " ").capitalize() for c in sp_cols}

    mc = model_countries()
    regions = {k: v[1] for k, v in C.model_locations().items()}
    basins_geo = json.loads((OUT / "basins.json").read_text())
    basin_name = {"north_atlantic": "North Atlantic", "south_atlantic": "South Atlantic", "north_pacific": "North Pacific",
                  "south_pacific": "South Pacific", "indian_ocean": "Indian Ocean", "southern_ocean": "Southern Ocean",
                  "arctic_ocean": "Arctic Ocean", "mediterranean": "Mediterranean and Black Sea",
                  "caribbean": "Caribbean and Gulf of Mexico"}
    if {f["properties"]["basin"] for f in basins_geo["features"]} != set(basin_name):
        sys.exit("FAIL: basins.json and the basin name table disagree")
    bd = pd.read_parquet(ROOT / "outputs/study_sites/dominant_basins.parquet").set_index("literature_id")
    n = Counter()
    unmapped = Counter()
    papers, sp_used = [], {}
    for lit, (src, cs) in sorted(mc.items()):
        n["model_read"] += 1
        if lit not in d.index:
            n["not_in_corpus_parquet"] += 1
            continue
        codes = []
        for c in cs:
            a3, st = to_a3(c)
            if a3 and a3 not in codes:
                codes.append(a3)
            elif st == "unmapped":
                unmapped[c] += 1
        basins = C.primary_basins(regions.get(lit, ""))
        if not codes:
            n["no_country_stated_or_mapped"] += 1
        if not basins:
            n["no_basin_named"] += 1
        if not codes and not basins:
            n["neither_country_nor_basin"] += 1
            continue
        if basins and lit in bd.index:  # cross-check against the dominant-basin columns (keyword channel)
            kw = {b for b in basin_name if not pd.isna(bd.at[lit, f"bd_{b}"]) and bd.at[lit, f"bd_{b}"] == 1}
            if kw:
                n["basin_crosscheck_both_channels"] += 1
                n["basin_crosscheck_agree"] += bool(kw & set(basins))
        r = d.loc[lit]
        sps = [sp_name[c] for c in sp_cols if r[c] == r[c] and r[c] and float(r[c]) > 0]
        idx = [sp_used.setdefault(s, len(sp_used)) for s in sps]
        au = str(r["authors"] or "")
        first = re.split(r"[;,&]| and ", au)[0].strip()
        au_short = (first + (" et al." if len(au) > len(first) + 3 else "")) if first else ""
        yr = int(r["year"]) if r["year"] == r["year"] else None
        doi = str(r["doi"]) if isinstance(r["doi"], str) and r["doi"].startswith("10.") else ""
        papers.append([lit, str(r["title"] or "")[:220], au_short[:60], yr, doi, codes, idx, basins])
        n["mapped"] += 1
        n["mapped_with_country"] += bool(codes)
        n["mapped_with_basin"] += bool(basins)
        n["mapped_with_species"] += bool(idx)
        n[f"source_{src}"] += 1
    if not papers:
        sys.exit("FAIL: no papers mapped")
    species = [s for s, _ in sorted(sp_used.items(), key=lambda kv: kv[1])]
    cov = {"built": time.strftime("%Y-%m-%d"), "corpus_records": len(d), **n,
           "countries_with_papers": len({c for p in papers for c in p[5]}),
           "unmapped_names": dict(unmapped.most_common()), "country_source": "model-read only; geo_study_country not used (63% agreement, MEASURED 2026-11-11)"}
    COVER.write_text(json.dumps(cov, indent=1, ensure_ascii=False))
    data = {"built": cov["built"], "n_corpus": len(d), "n_mapped": len(papers), "species": species, "a3name": a3name, "basinname": basin_name, "papers": papers,
            "n_country": n["mapped_with_country"], "n_basin": n["mapped_with_basin"]}
    html = (Path(__file__).parent / "coarse_atlas_template.html").read_text()
    html = html.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    html = html.replace("/*GEO*/null", json.dumps(geo, separators=(",", ":")))
    html = html.replace("/*BAS*/null", json.dumps(basins_geo, separators=(",", ":")))
    (OUT / "index.html").write_text(html)
    print("OK", json.dumps({k: v for k, v in cov.items() if k != "unmapped_names"}))
    print("unmapped country names (count):", dict(unmapped.most_common()))
    print(f"wrote {OUT / 'index.html'} ({(OUT / 'index.html').stat().st_size // 1024} KB), coverage {COVER}")
    print("next: commit and publish docs/species_atlas/ if the data changed")


if __name__ == "__main__":
    main()
