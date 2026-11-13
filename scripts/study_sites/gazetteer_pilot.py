#!/usr/bin/env python3
"""Gazetteer pilot (spec phase 2): geocode the place names the model read from the 120 pilot papers
and measure the result against the coordinates the same papers print. No model spend.

    python3 scripts/study_sites/gazetteer_pilot.py scan    # GeoNames dump -> candidates (local, ~3 min)
    python3 scripts/study_sites/gazetteer_pilot.py mr      # Marine Regions API -> candidates (network, resumable)
    python3 scripts/study_sites/gazetteer_pilot.py score   # acceptance rule, known answers, negative control

Inputs: outputs/study_sites/gold_pilot/cache/*.json (sites with name, optional lat_dd/lon_dd, country).
Gazetteers: GeoNames allCountries dump (CC BY 4.0; outputs/study_sites/gazetteers/, downloaded
2026-11-12) and the Marine Regions REST gazetteer (one process, 1 request a second).
Outputs: outputs/study_sites/gazetteer_pilot/ (candidates, per-site results.csv, summary.json).

Acceptance rule (spec section 3): a candidate counts only if it lies in a country the paper states.
- GeoNames: its country code is a stated country, or the point is inside a stated country's polygon
  (overseas departments), or it has no country code and lies within EEZ_KM of a stated country.
- Marine Regions (no country code): inside, or within EEZ_KM of, a stated country's polygon.
EEZ_KM is a stand-in for the EEZ polygons, which are not on disk.  # INFERRED: 200 nm = 370 km
Accepted candidates that all sit within SAME_PLACE_KM of each other are one place (resolved);
otherwise the site is ambiguous and gets no position.

Statuses are kept apart: resolved, ambiguous, rejected (candidates exist, none in a stated country),
unresolved (no candidate under any name variant), no_context (paper states no mappable country),
blocked (a Marine Regions request failed; never counted as a miss).
"""
import csv
import glob
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import build_coarse_atlas as B  # noqa: E402  (country_lookup: the one place a country name becomes a code)

PILOT = ROOT / "outputs/study_sites/gold_pilot/cache"
GAZ = ROOT / "outputs/study_sites/gazetteers"
OUT = ROOT / "outputs/study_sites/gazetteer_pilot"
GN_CAND = OUT / "geonames_candidates.json"
MR_CACHE = OUT / "mr_cache.json"
MR_LOG = OUT / "mr_progress.json"
EEZ_KM = 370          # INFERRED: 200 nautical miles, a proxy for EEZ polygons
SAME_PLACE_KM = 25    # INFERRED: untested choice; the summary reports sensitivity at 10 and 100 km
UA = "gazetteer-pilot/0.1"
MR_URL = "https://www.marineregions.org/rest/getGazetteerRecordsByName.json/{}/?like=false&fuzzy=false&offset=0&count=100"
CONTROL_HIT, CONTROL_MISS = "North Sea", "Zzqxv Nonplace"

LEAD = re.compile(r"^(?:(?:just\s+)?(?:off|near|around|outside|within|along|from|at|in)\s+(?:the\s+)?|the\s+|"
                  r"(?:coast|coastline|shelf|slope|waters|coastal waters|mouth|estuary)\s+(?:off|of)\s+(?:the\s+)?|"
                  r"(?:north|south|east|west|northern|southern|eastern|western|central|north-?east|north-?west|south-?east|south-?west)"
                  r"(?:ern)?\s+(?:of|coast of|part of)\s+(?:the\s+)?)", re.I)
TRAIL = re.compile(r"\s+(?:waters|coast|coastline|area|region|offshore|shelf|slope|harbou?r|port|fishing port|landing site)$", re.I)


def norm(s):
    """Match key: accents stripped by Unicode class, case folded, punctuation to spaces."""
    if not s.isascii():
        s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.casefold().replace("’", "'").replace("`", "'")
    return " ".join(re.sub(r"[^\w']+", " ", s).split())


def variants(name):
    """Ordered (text, how) variants of a site name, most specific first."""
    out, seen = [], set()

    def add(t, how):
        t = " ".join(t.split()).strip(" ,;:.-")
        k = norm(t)
        if len(k) >= 3 and not k.replace(" ", "").isdigit() and k not in seen:
            seen.add(k)
            out.append((t, how))
    full = name.strip()
    add(full, "full")
    nop = re.sub(r"\s*\([^)]*\)", "", full)
    add(nop, "no_parenthesis")
    head = nop.split(",")[0]
    add(head, "before_comma")
    for base in (nop, head):
        t = base
        for _ in range(3):
            t2 = TRAIL.sub("", LEAD.sub("", t))
            if t2 == t:
                break
            t = t2
        add(t, "stripped")
    return out


def pilot_units():
    """One unit per named site, plus the paper's finest_place when it is not already a site name."""
    geo = json.loads((ROOT / "docs/species_atlas/countries.json").read_text())
    to_a3, _ = B.country_lookup(geo)
    units, papers = [], {}
    for f in sorted(glob.glob(str(PILOT / "*.json"))):
        o = json.load(open(f))
        lit, out = str(o["lit_id"]), o["output"]
        a3 = []
        for c in out.get("country") or []:
            code, _st = to_a3(c)
            if code and code not in a3:
                a3.append(code)
        papers[lit] = a3
        names = set()
        for i, s in enumerate(out.get("sites") or []):
            nm = (s.get("name") or "").strip()
            if not nm:
                continue
            names.add(norm(nm))
            has = s.get("lat_dd") is not None and s.get("lon_dd") is not None
            units.append({"lit": lit, "unit": f"site{i}", "name": nm, "kind": s.get("kind"),
                          "lat": s["lat_dd"] if has else None, "lon": s["lon_dd"] if has else None})
        fp = (out.get("finest_place") or "").strip()
        if fp and norm(fp) not in names:
            units.append({"lit": lit, "unit": "finest", "name": fp, "kind": "finest_place", "lat": None, "lon": None})
    if len(papers) != 120:
        sys.exit(f"FAIL: expected 120 pilot papers, found {len(papers)}")
    return units, papers, geo


def all_variants(units):
    v = {}
    for u in units:
        for t, _how in variants(u["name"]):
            v.setdefault(norm(t), t)
    return v


def cmd_scan():
    units, _, _ = pilot_units()
    want = set(all_variants(units)) | {norm("London"), norm(CONTROL_MISS)}
    found = defaultdict(list)
    n = 0
    z = zipfile.ZipFile(GAZ / "allCountries.zip")
    with z.open("allCountries.txt") as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8"):
            n += 1
            c = line.rstrip("\n").split("\t")
            if len(c) != 19:
                sys.exit(f"FAIL: GeoNames row {n} has {len(c)} fields, expected 19")
            hit = {}
            for field, x in (("name", c[1]), ("asciiname", c[2])):
                k = norm(x)
                if k in want:
                    hit.setdefault(k, field)
            if c[3]:
                for x in c[3].split(","):
                    k = norm(x)
                    if k in want:
                        hit.setdefault(k, "alternate")
            for k, field in hit.items():
                found[k].append({"src": "geonames", "id": c[0], "name": c[1], "lat": float(c[4]), "lon": float(c[5]),
                                 "fclass": c[6], "fcode": c[7], "cc": c[8], "pop": int(c[14] or 0), "field": field})
    if n < 10_000_000:
        sys.exit(f"FAIL: GeoNames dump has only {n:,} rows; truncated download?")
    london = [r for r in found.get("london", []) if r["cc"] == "GB" and r["fcode"] == "PPLC"]
    if not london:
        sys.exit("FAIL positive control: London (GB, capital) not found in the GeoNames scan")
    if found.get(norm(CONTROL_MISS)):
        sys.exit("FAIL negative control: the nonsense name matched a GeoNames row")
    OUT.mkdir(parents=True, exist_ok=True)
    GN_CAND.write_text(json.dumps({"rows_scanned": n, "keys_wanted": len(want) - 2, "found": found}, ensure_ascii=False))
    print(f"OK scan: {n:,} GeoNames rows; {sum(1 for k in want if found.get(k)) - 1} of {len(want) - 2} name variants have a candidate; "
          f"controls passed (London found, nonsense name absent)")
    print("next: python3 scripts/study_sites/gazetteer_pilot.py mr")


def mr_fetch(text):
    """-> (status, records). status: ok | miss | blocked:<why>. A miss is HTTP 404 with body [] only."""
    url = MR_URL.format(urllib.parse.quote(text, safe=""))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
            body = r.read().decode("utf-8", "replace")
            if r.status == 200:
                recs = json.loads(body)
                return ("ok", recs) if isinstance(recs, list) and recs else (f"blocked:200 with unexpected body {body[:60]!r}", [])
            return f"blocked:http {r.status}", []
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace").strip()
        if e.code == 404 and body == "[]":
            return "miss", []
        return f"blocked:http {e.code}", []
    except Exception as e:  # timeout, DNS, reset, bad JSON
        return f"blocked:{type(e).__name__}", []


def mr_controls():
    a, _ = mr_fetch(CONTROL_HIT)
    time.sleep(1)
    b, _ = mr_fetch(CONTROL_MISS)
    time.sleep(1)
    return a == "ok" and b == "miss", f"{CONTROL_HIT}: {a}; {CONTROL_MISS}: {b}"


def cmd_mr():
    units, _, _ = pilot_units()
    v = all_variants(units)
    OUT.mkdir(parents=True, exist_ok=True)
    cache = json.loads(MR_CACHE.read_text()) if MR_CACHE.exists() else {}
    ok, msg = mr_controls()
    if not ok:
        sys.exit(f"FAIL Marine Regions controls before the run ({msg}); nothing fetched")
    todo = [k for k in sorted(v) if k not in cache]
    n = Counter(cached=len(v) - len(todo))
    streak, t0 = 0, time.time()
    for i, k in enumerate(todo):
        st, recs = mr_fetch(v[k])
        if st == "ok":
            cache[k] = {"status": "ok", "q": v[k], "recs": [
                {"src": "marineregions", "id": r.get("MRGID"), "name": r.get("preferredGazetteerName"), "lat": r.get("latitude"),
                 "lon": r.get("longitude"), "type": r.get("placeType"), "status": r.get("status"),
                 "bbox": [r.get("minLatitude"), r.get("minLongitude"), r.get("maxLatitude"), r.get("maxLongitude")]} for r in recs]}
            n["ok"] += 1
            streak = 0
        elif st == "miss":
            cache[k] = {"status": "miss", "q": v[k], "recs": []}   # the API's own "no record" answer; controls passed this run
            n["miss"] += 1
            streak = 0
        else:
            n[st] += 1
            n["blocked"] += 1
            streak += 1
        if i % 20 == 0 or streak:
            tmp = MR_CACHE.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache, ensure_ascii=False))
            tmp.replace(MR_CACHE)
            MR_LOG.write_text(json.dumps({"at": time.strftime("%H:%M:%S"), "done": i + 1, "of": len(todo), **n, "running": True}))
        if streak >= 5:
            print(f"STOP: 5 failed requests in a row ({st}); the service is blocking or down. Cached so far kept; rerun to resume.")
            break
        time.sleep(1.0)
    tmp = MR_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False))
    tmp.replace(MR_CACHE)
    ok2, msg2 = mr_controls()
    left = [k for k in v if k not in cache]
    MR_LOG.write_text(json.dumps({"at": time.strftime("%H:%M:%S"), "of": len(todo), **n, "running": False,
                                  "not_fetched": len(left), "controls_after": msg2}))
    print(f"{'OK' if not left and ok2 else 'INCOMPLETE'} mr: variants {len(v)}, {dict(n)}, not fetched {len(left)}, "
          f"{time.time() - t0:.0f}s; controls after: {msg2}")
    if not ok2:
        print("WARNING: controls failed after the run; misses recorded late in this run may be blocks. Delete them and rerun.")
    print("next: python3 scripts/study_sites/gazetteer_pilot.py score")


# ---------------------------------------------------------------- scoring
def cmd_score():
    from pyproj import Geod
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points
    geod = Geod(ellps="WGS84")
    units, papers, geo = pilot_units()
    gn = json.loads(GN_CAND.read_text())["found"]
    mr = json.loads(MR_CACHE.read_text()) if MR_CACHE.exists() else {}
    poly = {f["properties"]["adm0_a3"]: shape(f["geometry"]) for f in geo["features"] if f["geometry"]}
    iso3 = {f["properties"]["adm0_a3"]: (f["properties"]["iso_a3"] if f["properties"]["iso_a3"] not in ("-99", None) else f["properties"]["adm0_a3"])
            for f in geo["features"]}
    iso2 = {}
    for line in open(GAZ / "countryInfo.txt", encoding="utf-8"):
        if not line.startswith("#"):
            c = line.split("\t")
            iso2[c[1]] = c[0]

    def km(lat1, lon1, lat2, lon2):
        return geod.inv(lon1, lat1, lon2, lat2)[2] / 1000

    dcache = {}

    def km_to_country(lat, lon, a3):
        key = (round(lat, 4), round(lon, 4), a3)
        if key not in dcache:
            pt = Point(lon, lat)
            if poly[a3].contains(pt):
                dcache[key] = 0.0
            else:
                q = nearest_points(poly[a3], pt)[0]   # nearest in degree space, then a geodesic length
                dcache[key] = km(lat, lon, q.y, q.x)
        return dcache[key]

    def accepted(c, a3s):
        if c["lat"] is None or c["lon"] is None:
            return False
        if c["src"] == "geonames" and c["cc"] and c["cc"] in {iso2.get(iso3[a]) for a in a3s}:
            return True
        d = min(km_to_country(c["lat"], c["lon"], a) for a in a3s)
        if c["src"] == "geonames" and c["cc"]:
            return d == 0.0
        return d <= EEZ_KM

    PRI = {"H": 0, "T": 1, "L": 2, "U": 3, "P": 4, "A": 5, "V": 6, "S": 7, "R": 8}

    def rank(c):
        return (0, 0, 0) if c["src"] == "marineregions" else (1, PRI.get(c["fclass"], 9), -c["pop"])

    def resolve(u, a3s, sources, same_km=SAME_PLACE_KM):
        """-> (status, position candidate or None, variant how, n candidates, n accepted, blocked?)"""
        any_cand, blocked = 0, False
        for t, how in variants(u["name"]):
            k = norm(t)
            cands = []
            if "geonames" in sources:
                cands += gn.get(k, [])
            if "marineregions" in sources:
                if k in mr:
                    cands += mr[k]["recs"]
                else:
                    blocked = True
            if not cands:
                continue
            any_cand += len(cands)
            if not a3s:
                return "no_context", None, how, any_cand, 0, blocked
            acc = [c for c in cands if accepted(c, a3s)]
            if not acc:
                continue
            spread = max((km(a["lat"], a["lon"], b["lat"], b["lon"]) for a in acc for b in acc), default=0)
            best = sorted(acc, key=rank)[0]
            return ("resolved" if spread <= same_km else "ambiguous"), best, how, any_cand, len(acc), blocked
        if any_cand:
            return "rejected", None, "", any_cand, 0, blocked
        if blocked:
            return "blocked", None, "", 0, 0, True
        return ("no_context" if not a3s else "unresolved"), None, "", 0, 0, False

    def run(sources, ctx, same_km=SAME_PLACE_KM):
        rows = []
        for u in units:
            st, best, how, nc, na, bl = resolve(u, ctx[u["lit"]], sources, same_km)
            err = km(u["lat"], u["lon"], best["lat"], best["lon"]) if best and u["lat"] is not None else None
            rows.append({**u, "status": st, "variant": how, "n_candidates": nc, "n_accepted": na, "err_km": err,
                         "gaz": best["src"] if best else "", "gaz_id": best["id"] if best else "", "gaz_name": best["name"] if best else "",
                         "gaz_type": (best.get("type") or f'{best.get("fclass")}.{best.get("fcode")}') if best else "",
                         "gaz_lat": best["lat"] if best else None, "gaz_lon": best["lon"] if best else None})
        return rows

    def summarise(rows):
        s = Counter(r["status"] for r in rows)
        known = [r for r in rows if r["lat"] is not None]
        res = sorted(r["err_km"] for r in known if r["status"] == "resolved")
        amb = sorted(r["err_km"] for r in known if r["status"] == "ambiguous")

        def dist(v):
            if not v:
                return {"n": 0}
            return {"n": len(v), "median_km": round(v[len(v) // 2], 1), "within_10km": sum(x <= 10 for x in v),
                    "within_50km": sum(x <= 50 for x in v), "within_200km": sum(x <= 200 for x in v), "max_km": round(v[-1])}
        return {"units": len(rows), "status": dict(s), "papers_with_a_resolved_site": len({r["lit"] for r in rows if r["status"] == "resolved"}),
                "known_answer_units": len(known), "known_answer_status": dict(Counter(r["status"] for r in known)),
                "known_resolved_error": dist(res), "known_ambiguous_top_pick_error_indicative": dist(amb)}

    # negative control: every paper gets another paper's countries (next paper, in id order, sharing none of its own)
    lits = sorted(p for p in papers if papers[p])
    shuffled = dict(papers)
    for i, p in enumerate(lits):
        for j in range(1, len(lits)):
            q = lits[(i + j) % len(lits)]
            if not set(papers[q]) & set(papers[p]):
                shuffled[p] = papers[q]
                break
        else:
            sys.exit("FAIL: negative control could not find a disjoint country set")

    have_mr = bool(mr)
    configs = {"geonames": ["geonames"]}
    if have_mr:
        configs.update({"marineregions": ["marineregions"], "both": ["geonames", "marineregions"]})
    summary = {"built": time.strftime("%Y-%m-%d %H:%M"), "papers": len(papers), "papers_with_mappable_country": len(lits),
               "eez_km": EEZ_KM, "same_place_km": SAME_PLACE_KM, "marine_regions_cache": len(mr), "kind": "pilot, 120 papers, model-read names, not hand-checked"}
    per = {}
    for name, src in configs.items():
        rows = run(src, papers)
        per[name] = rows
        summary[name] = summarise(rows)
        ctl = Counter(r["status"] for r in run(src, shuffled))
        summary[name]["negative_control_shuffled_country"] = dict(ctl)
        summary[name]["same_place_sensitivity"] = {f"{k}km": dict(Counter(r["status"] for r in run(src, papers, k))) for k in (10, 100)}
        by_type = defaultdict(list)
        for r in rows:
            if r["status"] == "resolved" and r["err_km"] is not None:
                by_type[r["gaz_type"].split(".")[0] if r["gaz"] == "geonames" else "MR:" + r["gaz_type"]].append(round(r["err_km"], 1))
        summary[name]["known_resolved_error_by_type_km"] = {k: sorted(v) for k, v in sorted(by_type.items())}
        if name == ("both" if have_mr else "geonames"):
            final = rows
    if have_mr:
        # "either": a site counts as resolved when one gazetteer alone resolves it (Marine Regions first), since pooling
        # the two lists turns one place with two centroids into an ambiguity
        ei = [m if m["status"] == "resolved" else g if g["status"] == "resolved" else b
              for g, m, b in zip(per["geonames"], per["marineregions"], per["both"])]
        summary["either"] = summarise(ei)
        agree = [(km(g["gaz_lat"], g["gaz_lon"], m["gaz_lat"], m["gaz_lon"])) for g, m in zip(per["geonames"], per["marineregions"])
                 if g["status"] == "resolved" and m["status"] == "resolved"]
        summary["either"]["both_gazetteers_resolved"] = len(agree)
        summary["either"]["of_which_within_25km_of_each_other"] = sum(x <= 25 for x in agree)
        summary["either"]["of_which_within_100km_of_each_other"] = sum(x <= 100 for x in agree)
        for r, g, m in zip(ei, per["geonames"], per["marineregions"]):
            r["status_geonames"], r["status_marineregions"] = g["status"], m["status"]
        final, name = ei, "either"
    total = len(units)
    if sum(summary[name]["status"].values()) != total:
        sys.exit("FAIL completeness: statuses do not sum to the units in scope")
    with open(OUT / "results.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(final[0].keys()))
        w.writeheader()
        w.writerows(final)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"wrote {OUT / 'results.csv'} ({len(final)} rows) and {OUT / 'summary.json'}")
    if not have_mr:
        print("NOTE: Marine Regions not fetched yet; GeoNames only. next: gazetteer_pilot.py mr, then score again")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"scan": cmd_scan, "mr": cmd_mr, "score": cmd_score}.get(cmd, lambda: sys.exit(__doc__))()
