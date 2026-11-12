"""Check the corpus basin columns (b_*, ob_*, sb_*, geo_study_ocean_basin) against study
locations a language model read from the full text.

The model caches hold study country and a free-text region, not a basin, so the reference basin
is DERIVED here, independently of the columns under test:
  strong reference: a sea or ocean named in the model's region text  (REGION_KEYS)
  weak reference  : the set of basins the model's study countries border (COUNTRY_BASINS),
                    used only for countries listed there
A reference is a SET of acceptable basins; a column is multi-label. Reported per column family:
  coverage      : reference papers where the column flags anything
  has_right     : flagged papers whose flags include an acceptable basin
  has_wrong     : flagged papers with at least one flag outside the acceptable set
  clean         : flagged papers whose flags are all acceptable
Sub-basins: for each sb_ column, recall where the model's region text names that sea, and the
share of its flagged papers whose parent basin is outside the reference.

  python3 scripts/study_sites/check_basin_columns.py [--show 12]
Writes outputs/study_sites/basin_column_check.json
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "outputs/literature_review_enriched.parquet"
OUT = ROOT / "outputs/study_sites/basin_column_check.json"

NA, SA, NP, SP, IO, SO, AR, ME, CA = ("north_atlantic", "south_atlantic", "north_pacific", "south_pacific", "indian_ocean",
                                      "southern_ocean", "arctic_ocean", "mediterranean", "caribbean")
# INFERRED: the Gulf of Mexico and the Bahamas are accepted as either North Atlantic or Caribbean, because the
# column definitions do not say which they use. Order matters: longer, more specific names first.
REGION_KEYS = [
    (r"gulf of mexico|bahamas|florida keys|bimini", {NA, CA}),
    (r"caribbean|belize|lesser antilles|greater antilles|cayman", {CA, NA}),
    (r"mediterranean|adriatic|aegean|tyrrhenian|ionian sea|ligurian|alboran|black sea|sea of marmara|levant|balearic|strait of sicily", {ME}),
    (r"\bnorth[- ]?(?:east|west)?(?:ern)? atlantic|\bn[ew]? atlantic|north sea|baltic|celtic sea|irish sea|english channel|bay of biscay|norwegian sea|"
     r"gulf of maine|sargasso|azores|canary islands|gulf of st\.? lawrence|chesapeake|georges bank|scotian shelf|macaronesia|madeira", {NA}),
    (r"\bsouth[- ]?(?:east|west)?(?:ern)? atlantic|\bs[ew] atlantic|benguela|patagoni|rio de la plata|río de la plata|gulf of guinea", {SA}),
    (r"gulf of guinea", {SA, NA}),
    (r"indian ocean|arabian sea|bay of bengal|red sea|persian gulf|arabian gulf|gulf of oman|gulf of aden|mozambique channel|andaman|"
     r"ningaloo|shark bay|chagos|mascarene|gulf of mannar|laccadive", {IO}),
    (r"\bnorth[- ]?(?:east|west)?(?:ern)? pacific|\bn[ew]? pacific|gulf of california|sea of cortez|gulf of alaska|bering sea|sea of okhotsk|sea of japan|"
     r"east china sea|south china sea|yellow sea|philippine sea|hawai|california current|southern california bight|monterey|salish sea|puget sound|"
     r"revillagigedo|gulf of thailand", {NP}),
    (r"\bsouth[- ]?(?:east|west)?(?:ern)? pacific|\bs[ew] pacific|coral sea|tasman sea|great barrier reef|french polynesia|new caledonia|fiji|"
     r"humboldt current|juan fern", {SP}),
    (r"southern ocean|antarctic|kerguelen|south georgia|ross sea|weddell", {SO}),
    (r"arctic|barents sea|svalbard|beaufort sea|chukchi|baffin|greenland sea", {AR, NA}),
]
# One display basin per REGION_KEYS entry, same order, for maps that need a single basin (Species Atlas).
# INFERRED convention, following the b_caribbean term list: Gulf of Mexico and Bahamas sit with the Caribbean.
REGION_PRIMARY = [CA, CA, ME, NA, SA, SA, IO, NP, SP, SO, AR]
assert len(REGION_PRIMARY) == len(REGION_KEYS)


def primary_basins(region):
    """Display basins named in a model-read region text (may be empty, may be several)."""
    t = region.lower()
    return sorted({REGION_PRIMARY[i] for i, (pat, _) in enumerate(REGION_KEYS) if re.search(pat, t)})


COUNTRY_BASINS = {  # countries whose coasts border a short, known set of the nine basins
    "japan": {NP}, "south korea": {NP}, "china": {NP}, "taiwan": {NP}, "philippines": {NP}, "vietnam": {NP},
    "india": {IO}, "sri lanka": {IO}, "bangladesh": {IO}, "pakistan": {IO}, "iran": {IO}, "oman": {IO}, "united arab emirates": {IO},
    "qatar": {IO}, "kuwait": {IO}, "saudi arabia": {IO}, "maldives": {IO}, "seychelles": {IO}, "mauritius": {IO}, "madagascar": {IO},
    "mozambique": {IO}, "tanzania": {IO}, "kenya": {IO}, "myanmar": {IO},
    "italy": {ME}, "greece": {ME}, "turkey": {ME}, "croatia": {ME}, "tunisia": {ME}, "malta": {ME}, "israel": {ME, IO}, "egypt": {ME, IO},
    "cyprus": {ME}, "lebanon": {ME}, "algeria": {ME}, "libya": {ME}, "montenegro": {ME}, "albania": {ME},
    "spain": {NA, ME}, "france": {NA, ME}, "morocco": {NA, ME},
    "uk": {NA}, "united kingdom": {NA}, "ireland": {NA}, "portugal": {NA}, "germany": {NA}, "netherlands": {NA}, "belgium": {NA},
    "denmark": {NA}, "sweden": {NA}, "norway": {NA, AR}, "iceland": {NA, AR}, "senegal": {NA}, "mauritania": {NA}, "cabo verde": {NA},
    "argentina": {SA}, "uruguay": {SA}, "namibia": {SA}, "angola": {SA}, "brazil": {SA, NA}, "south africa": {SA, IO, SO},
    "chile": {SP, SO}, "peru": {SP}, "new zealand": {SP, SO}, "fiji": {SP}, "french polynesia": {SP},
    "australia": {SP, IO, SO}, "indonesia": {IO, NP, SP}, "malaysia": {IO, NP},
    "bahamas": {NA, CA}, "cuba": {CA, NA}, "belize": {CA}, "jamaica": {CA}, "cayman islands": {CA}, "dominican republic": {CA, NA},
    "usa": {NA, NP, CA, AR}, "united states": {NA, NP, CA, AR}, "mexico": {NP, NA, CA}, "canada": {NA, NP, AR},
    "colombia": {CA, NP, SP}, "costa rica": {CA, NP}, "panama": {CA, NP}, "ecuador": {SP, NP},
}
OB_MAP = {"ob_arctic_ocean": AR, "ob_north_atlantic_ocean": NA, "ob_south_atlantic_ocean": SA, "ob_indian_ocean": IO,
          "ob_north_pacific_ocean": NP, "ob_south_pacific_ocean": SP, "ob_southern_ocean": SO,
          "ob_mediterranean_black_sea": ME, "ob_baltic_sea": NA}
GEO_MAP = {"North Atlantic": NA, "South Atlantic": SA, "North Pacific": NP, "South Pacific": SP, "Indian Ocean": IO, "Arctic": AR}
SB_PARENT = {  # sub-basin -> acceptable parent basins, and the words that name it in a region text
    "north_sea": ({NA}, r"north sea"), "norwegian_sea": ({NA, AR}, r"norwegian sea"), "barents_sea": ({AR, NA}, r"barents"),
    "baltic_sea": ({NA}, r"baltic"), "celtic_sea": ({NA}, r"celtic sea"), "irish_sea": ({NA}, r"irish sea"),
    "english_channel": ({NA}, r"english channel"), "bay_of_biscay": ({NA}, r"biscay"), "azores": ({NA}, r"azores"),
    "gulf_of_maine": ({NA}, r"gulf of maine"), "gulf_of_mexico": ({NA, CA}, r"gulf of mexico"), "caribbean_sea": ({CA, NA}, r"caribbean"),
    "bahamas": ({NA, CA}, r"bahamas"), "sargasso_sea": ({NA}, r"sargasso"), "gulf_of_guinea": ({SA, NA}, r"gulf of guinea"),
    "benguela": ({SA}, r"benguela"), "alboran_sea": ({ME}, r"alboran"), "ligurian_sea": ({ME}, r"ligurian"),
    "tyrrhenian_sea": ({ME}, r"tyrrhenian"), "adriatic_sea": ({ME}, r"adriatic"), "ionian_sea": ({ME}, r"ionian"),
    "aegean_sea": ({ME}, r"aegean"), "black_sea": ({ME}, r"black sea"), "sea_of_marmara": ({ME}, r"marmara"),
    "red_sea": ({IO}, r"red sea"), "arabian_sea": ({IO}, r"arabian sea"), "persian_gulf": ({IO}, r"persian gulf|arabian gulf"),
    "bay_of_bengal": ({IO}, r"bay of bengal"), "andaman_sea": ({IO}, r"andaman"), "mozambique_channel": ({IO}, r"mozambique channel"),
    "gulf_of_california": ({NP}, r"gulf of california|sea of cortez"), "gulf_of_alaska": ({NP}, r"gulf of alaska"),
    "bering_sea": ({NP, AR}, r"bering"), "sea_of_okhotsk": ({NP}, r"okhotsk"), "sea_of_japan": ({NP}, r"sea of japan|east sea"),
    "east_china_sea": ({NP}, r"east china sea"), "south_china_sea": ({NP}, r"south china sea"), "yellow_sea": ({NP}, r"yellow sea"),
    "philippine_sea": ({NP}, r"philippine sea"), "coral_sea": ({SP}, r"coral sea"), "tasman_sea": ({SP}, r"tasman"),
    "hawaii": ({NP}, r"hawai"), "california_current": ({NP}, r"california current"),
}


def wil(k, n, z=1.96):
    if not n:
        return "0/0"
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{k}/{n} = {p:.0%} (95% CI {max(0, c - h):.0%}-{min(1, c + h):.0%})"


def model_locations():
    import glob
    out = {}
    for g in glob.glob(str(ROOT / "outputs/validation/.fable_corpus_cache/*.txt")):
        t = open(g, errors="replace").read()
        m = re.search(r"^LIT:\s*(\S+)", t, re.M)
        c, r = re.search(r"^COUNTRY:[ \t]*(.*)$", t, re.M), re.search(r"^REGION:[ \t]*(.*)$", t, re.M)
        if m:
            out[m.group(1)] = ([x.strip() for x in re.split(r"[;,/]", c.group(1)) if x.strip()] if c else [], r.group(1) if r else "")
    for g in glob.glob(str(ROOT / "outputs/validation/.fable_v2_cache/*.json")):
        o = json.load(open(g))
        out[str(o["lit_id"])] = (o["output"].get("study_country") or [], o["output"].get("study_region") or "")
    for g in glob.glob(str(ROOT / "outputs/study_sites/gold_pilot/cache/*.json")):
        o = json.load(open(g))
        x = o["output"]
        out[str(o["lit_id"])] = (x["country"], " | ".join([x["finest_place"]] + [s["name"] for s in x["sites"]]))
    return out


def reference(countries, region):
    """(strength, acceptable basin set) or (None, None)."""
    t = region.lower()
    acc = set()
    for pat, bs in REGION_KEYS:
        if re.search(pat, t):
            acc |= bs
    if acc:
        return "strong", acc
    cs = [c.strip().lower() for c in countries if c.strip()]
    if cs and all(c in COUNTRY_BASINS for c in cs):
        return "weak", set().union(*(COUNTRY_BASINS[c] for c in cs))
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    names = pq.ParquetFile(PARQUET).schema.names
    bcols = [n for n in names if n.startswith("b_")]
    obcols = [n for n in names if n.startswith("ob_")]
    sbcols = [n for n in names if n.startswith("sb_")]
    d = pd.read_parquet(PARQUET, columns=["literature_id", "title", "geo_study_ocean_basin"] + bcols + obcols + sbcols)
    d["literature_id"] = d["literature_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    d = d.drop_duplicates("literature_id").set_index("literature_id")
    on = lambda v: (not pd.isna(v)) and bool(v)  # zero and missing both count as not flagged here
    ml = model_locations()
    n = Counter()
    fam = {f: {s: Counter() for s in ("strong", "weak")} for f in ("b_", "ob_", "geo_study_ocean_basin")}
    sb = {c: Counter() for c in sbcols}
    examples = []
    wrong_by, flag_by = Counter(), Counter()
    for lit, (cs, region) in ml.items():
        n["model_read"] += 1
        if lit not in d.index:
            n["not_in_parquet"] += 1
            continue
        strength, acc = reference(cs, region)
        row = d.loc[lit]
        for c in sbcols:  # sub-basin recall is judged on the region text alone, whatever the reference strength
            key = c[3:]
            if re.search(SB_PARENT[key][1], region.lower()):
                sb[c]["named_by_model"] += 1
                sb[c]["named_and_flagged"] += on(row[c])
        if not strength:
            n["no_reference"] += 1
            continue
        n[f"reference_{strength}"] += 1
        flags = {"b_": {c[2:] for c in bcols if on(row[c])}, "ob_": {OB_MAP[c] for c in obcols if on(row[c])},
                 "geo_study_ocean_basin": {GEO_MAP[row["geo_study_ocean_basin"]]} if row["geo_study_ocean_basin"] in GEO_MAP else set()}
        for f, fl in flags.items():
            k = fam[f][strength]
            k["ref"] += 1
            if not fl:
                continue
            k["flagged"] += 1
            k["has_right"] += bool(fl & acc)
            k["has_wrong"] += bool(fl - acc)
            k["clean"] += not (fl - acc)
            if f == "b_" and strength == "strong":
                wrong_by.update(fl - acc)
                flag_by.update(fl)
            if f == "b_" and strength == "strong" and (fl - acc) and len(examples) < a.show:
                examples.append((lit, sorted(fl), sorted(acc), "; ".join(cs)[:30], region[:70], str(row["title"])[:60]))
        for c in sbcols:
            if on(row[c]):
                sb[c]["flagged_with_ref"] += 1
                sb[c]["parent_outside_ref"] += not (SB_PARENT[c[3:]][0] & acc)
    print("papers:", dict(n))
    res = {"papers": dict(n), "families": {}, "sub_basins": {}}
    for f in fam:
        for s in ("strong", "weak"):
            k = fam[f][s]
            res["families"][f"{f}|{s}"] = dict(k)
            print(f"\n{f} vs {s} reference ({k['ref']} papers)")
            print(f"  coverage   {wil(k['flagged'], k['ref'])}")
            print(f"  has_right  {wil(k['has_right'], k['flagged'])}")
            print(f"  has_wrong  {wil(k['has_wrong'], k['flagged'])}")
            print(f"  clean      {wil(k['clean'], k['flagged'])}")
    print("\nSUB-BASINS  recall where the model names the sea | flagged papers whose parent basin is outside the reference")
    tot = Counter()
    for c in sbcols:
        k = sb[c]
        tot.update(k)
        res["sub_basins"][c] = dict(k)
        print(f"  {c:24s} {k['named_and_flagged']:3d}/{k['named_by_model']:3d} | {k['parent_outside_ref']:3d}/{k['flagged_with_ref']:3d}")
    print(f"  ALL  recall {wil(tot['named_and_flagged'], tot['named_by_model'])} | wrong-basin flags {wil(tot['parent_outside_ref'], tot['flagged_with_ref'])}")
    res["sub_basins_total"] = dict(tot)
    print("\nb_ flags outside the strong reference, by basin (wrong / times flagged):", {b: f"{wrong_by[b]}/{flag_by[b]}" for b in sorted(flag_by, key=lambda b: -wrong_by[b])})
    res["b_wrong_by_basin"] = {b: [wrong_by[b], flag_by[b]] for b in flag_by}
    for e in examples:
        print("  EX", e)
    OUT.write_text(json.dumps(res, indent=1))
    print(f"\nOK wrote {OUT}")


if __name__ == "__main__":
    main()
