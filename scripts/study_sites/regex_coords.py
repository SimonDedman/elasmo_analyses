"""Strict regex extraction of study-site coordinates from paper body text.

Replaces the coordinate half of extract_study_locations_phase4.py, whose pattern
made the degree sign and the hemisphere letter optional (so it matched any two
decimals) and never captured the hemisphere (so nothing was ever negative).

Tiers, strictest first:
  A  point   : latitude token + longitude token, each with a degree sign AND a
               hemisphere letter, within PAIR_GAP characters of each other
  B  axis    : a lone token with degree sign + hemisphere (latitude bands,
               "between 30°S and 35°S"): evidence of an extent, not a point
  C  nodeg   : decimal pair with hemisphere letters but no degree sign
               ("12.345 N, 45.678 W"), or a signed decimal pair right after a
               latitude/longitude/coordinates keyword
Every hit keeps its verbatim snippet and character offset so it can be audited.

Usage:
  python3 scripts/study_sites/regex_coords.py            # whole .fable_texts cache
  python3 scripts/study_sites/regex_coords.py --ids 1,2  # named papers, prints hits
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXTS = ROOT / "outputs/validation/.fable_texts"
OUT = ROOT / "outputs/study_sites"
PAIR_GAP = 40  # INFERRED: generous enough for "12°30'S, 045°10'E" and "lat ... ; long ..."
VERSION = "v2"

NUM = r"\d{1,3}(?:[.,]\d+)?"
DEGC = "°º˚◦∘⁰"          # MEASURED on the dev half 2026-11-11: pdftotext gives ◦ for the degree sign in several journals
MINC = "′'’‘´`ʹʼ"
DEG = rf"\s?[{DEGC}]\s?"
# the minute mark is optional: text extraction drops it ("37◦ 34 N"); the hemisphere letter still gates the match
MINP = rf"(?:(?P<m>\d{{1,2}}(?:[.,]\d+)?)\s?[{MINC}]?\s?)?"
SECP = rf"(?:(?P<s>\d{{1,2}}(?:[.,]\d+)?)\s?(?:″|\"|”|“|ʺ|[{MINC}]\s?[{MINC}])\s?)?"
BODY = rf"(?P<d>{NUM}){DEG}{MINP}{SECP}"
# lookbehind also blocks a start right after a minute mark, so "14°46´24°S" cannot be read as 24°S
TOKEN = re.compile(rf"(?<![\w.,{MINC}])(?:(?P<pre>[NSEW])\s?)?{BODY}(?P<post>[NSEW])?(?![A-Za-z])")
RANGE_JOIN = re.compile(r"^\s?(?:to|and|–|—|-|y|a|e)\s?$")
NODEG = re.compile(
    r"(?<![\w.,])(?P<a>\d{1,2}[.]\d{2,})\s?(?P<ha>[NS])\s?[,;/]?\s?(?:and\s)?(?P<b>\d{1,3}[.]\d{2,})\s?(?P<hb>[EW])(?![A-Za-z])"
)
KEYED = re.compile(
    r"(?i)(?:lat(?:itude)?\.?|coordinates?|gps)\D{0,25}?(?P<a>[-−–]?\d{1,2}[.]\d{2,})\s?[,;]\s?(?:long?(?:itude)?\.?\D{0,10}?)?(?P<b>[-−–]?\d{1,3}[.]\d{2,})"
)
# OCR reads the degree sign as "8" and the minute mark as "0" or a prime ("9856′ N 76815′ E", "048070 N 968080 E",
# "9.128N 79.468E"). Accepted only as a latitude+longitude PAIR, both damaged the same way. MEASURED: 3 dev papers.
OCR_DM = re.compile(r"(?<![\w.,])(?P<a>\d{1,2})8(?P<am>[0-5]\d)[0′'’]\s?(?P<ha>[NS])\s?[,;]?\s?(?P<b>\d{1,3})8(?P<bm>[0-5]\d)[0′'’]\s?(?P<hb>[EW])(?![A-Za-z])")
OCR_DD = re.compile(r"(?<![\w.,])(?P<a>\d{1,2}\.\d+)8\s?(?P<ha>[NS])\s?[,;]?\s?(?P<b>\d{1,3}\.\d+)8\s?(?P<hb>[EW])(?![A-Za-z])")


def _f(s):
    return float(s.replace(",", ".")) if s else 0.0


def _snip(text, a, b, pad=60):
    return re.sub(r"\s+", " ", text[max(0, a - pad): b + pad]).strip()


def tokens(text):
    """Degree-sign tokens. A token with no hemisphere letter is kept only so a range
    ("34º47' to 34º55' S") can lend it the hemisphere of the token that follows."""
    out, pos = [], 0
    while True:
        m = TOKEN.search(text, pos)
        if not m:
            break
        pre, post, end = m.group("pre"), m.group("post"), m.end()
        if pre and post:
            # "S 18° 06.1′ E 11° 27.4′": the trailing letter is the NEXT token's prefix
            post, end = None, m.start("post")
        h = pre or post
        d, mi, se = _f(m.group("d")), _f(m.group("m")), _f(m.group("s"))
        pos = max(end, m.start() + 1)
        if mi >= 60 or se >= 60:
            continue
        out.append({"h": h, "abs": d + mi / 60 + se / 3600, "start": m.start(), "end": end,
                    "coarse": m.group("m") is None and "." not in m.group("d") and "," not in m.group("d")})
    for i in range(len(out) - 2, -1, -1):  # lend hemisphere backwards across a range joiner
        t, u = out[i], out[i + 1]
        if not t["h"] and u["h"] and RANGE_JOIN.match(text[t["end"]:u["start"]]):
            t["h"], t["range_start"] = u["h"], True
    res = []
    for t in out:
        if not t["h"]:
            continue
        axis = "lat" if t["h"] in "NS" else "lon"
        if t["abs"] > (90 if axis == "lat" else 180):
            continue
        res.append({"axis": axis, "value": round(-t["abs"] if t["h"] in "SW" else t["abs"], 5), "start": t["start"],
                    "end": t["end"], "coarse": t["coarse"], "range_start": t.get("range_start", False)})
    return res


def extract(text):
    """Return {'points', 'coarse', 'axes', 'nodeg'} for one paper.
    points: tier A (degree sign + hemisphere pair), R (corners of a printed range), O (OCR-damaged pair)
    coarse: whole-degree pairs with no minutes or decimals: map graticule labels and bounding ranges, not sites"""
    toks = tokens(text)
    points, coarse, used = [], [], set()
    i = 0
    while i < len(toks) - 1:
        t, u = toks[i], toks[i + 1]
        # range form: lat1 to lat2 H and lon1 to lon2 H  -> two corner points
        if (t["range_start"] and i + 3 < len(toks) and toks[i + 2]["range_start"] and t["axis"] == u["axis"]
                and toks[i + 2]["axis"] == toks[i + 3]["axis"] != t["axis"] and toks[i + 2]["start"] - u["end"] <= PAIR_GAP):
            v, w = toks[i + 2], toks[i + 3]
            for p, q in ((t, v), (u, w)):
                lat, lon = (p, q) if p["axis"] == "lat" else (q, p)
                points.append({"lat": lat["value"], "lon": lon["value"], "tier": "R", "start": t["start"],
                               "snippet": _snip(text, t["start"], w["end"])})
            used.update(range(i, i + 4))
            i += 4
            continue
        if t["axis"] != u["axis"] and u["start"] - t["end"] <= PAIR_GAP:
            lat, lon = (t, u) if t["axis"] == "lat" else (u, t)
            rec = {"lat": lat["value"], "lon": lon["value"], "tier": "A", "start": t["start"],
                   "snippet": _snip(text, t["start"], u["end"])}
            (coarse if t["coarse"] and u["coarse"] else points).append(rec)
            used.update((i, i + 1))
            i += 2
            continue
        i += 1
    axes = [{"axis": t["axis"], "value": t["value"], "tier": "B", "start": t["start"],
             "snippet": _snip(text, t["start"], t["end"])} for k, t in enumerate(toks) if k not in used]
    sgn = lambda v, h: -v if h in "SW" else v
    for m in OCR_DM.finditer(text):
        a, b = int(m.group("a")) + int(m.group("am")) / 60, int(m.group("b")) + int(m.group("bm")) / 60
        if a <= 90 and b <= 180:
            points.append({"lat": round(sgn(a, m.group("ha")), 5), "lon": round(sgn(b, m.group("hb")), 5), "tier": "O",
                           "start": m.start(), "snippet": _snip(text, m.start(), m.end())})
    for m in OCR_DD.finditer(text):
        a, b = float(m.group("a")), float(m.group("b"))
        if a <= 90 and b <= 180:
            points.append({"lat": sgn(a, m.group("ha")), "lon": sgn(b, m.group("hb")), "tier": "O",
                           "start": m.start(), "snippet": _snip(text, m.start(), m.end())})
    nodeg = []
    for m in NODEG.finditer(text):
        a, b = float(m.group("a")), float(m.group("b"))
        if a <= 90 and b <= 180:
            nodeg.append({"lat": sgn(a, m.group("ha")), "lon": sgn(b, m.group("hb")),
                          "tier": "C", "start": m.start(), "snippet": _snip(text, m.start(), m.end())})
    for m in KEYED.finditer(text):
        a = float(re.sub("[−–]", "-", m.group("a")))
        b = float(re.sub("[−–]", "-", m.group("b")))
        if abs(a) <= 90 and abs(b) <= 180:
            nodeg.append({"lat": a, "lon": b, "tier": "C", "start": m.start(),
                          "snippet": _snip(text, m.start(), m.end())})
    return {"points": points, "coarse": coarse, "axes": axes, "nodeg": nodeg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    a = ap.parse_args()
    if a.ids:
        for i in a.ids.split(","):
            r = extract((TEXTS / f"{i}.txt").read_text(errors="replace"))
            print(i, {k: len(v) for k, v in r.items()})
            for k in r:
                for h in r[k][:8]:
                    print("   ", k, h)
        return
    files = sorted(TEXTS.glob("*.txt"))
    if not files:
        sys.exit(f"FAIL: no texts in {TEXTS}")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    n = {"texts": 0, "empty": 0, "A": 0, "B_only": 0, "C_only": 0, "any": 0, "points": 0}
    tmp = OUT / f"regex_coords_{VERSION}.jsonl.tmp"
    with tmp.open("w") as fh:
        for f in files:
            text = f.read_text(errors="replace")
            n["texts"] += 1
            if len(text) < 500:
                n["empty"] += 1
            r = extract(text)
            has = {k: bool(v) for k, v in r.items()}
            if has["points"]:
                n["A"] += 1
                n["points"] += len(r["points"])
            elif has["axes"] or has.get("coarse"):
                n["B_only"] += 1
            elif has["nodeg"]:
                n["C_only"] += 1
            n["any"] += any(has.values())
            fh.write(json.dumps({"lit_id": f.stem, "chars": len(text), **r}, ensure_ascii=False) + "\n")
    tmp.replace(OUT / f"regex_coords_{VERSION}.jsonl")
    n["seconds"] = round(time.time() - t0, 1)
    (OUT / f"regex_coords_{VERSION}_coverage.json").write_text(json.dumps(n, indent=1))
    print("OK", json.dumps(n))
    print(f"next: sample + gold pilot (scripts/study_sites/); output {OUT}/regex_coords_{VERSION}.jsonl")


if __name__ == "__main__":
    main()
