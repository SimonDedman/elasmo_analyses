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
VERSION = "v1"

NUM = r"\d{1,3}(?:[.,]\d+)?"
DEG = r"\s?[°º˚]\s?"
MINP = r"(?:(?P<m>\d{1,2}(?:[.,]\d+)?)\s?[′'’´`]\s?)?"
SECP = r"(?:(?P<s>\d{1,2}(?:[.,]\d+)?)\s?(?:″|\"|”|''|’’)\s?)?"
TOKEN = re.compile(
    rf"(?<![\w.,])(?:(?P<pre>[NSEW])\s?)?(?P<d>{NUM}){DEG}{MINP}{SECP}(?P<post>[NSEW])?(?![A-Za-z])"
)
NODEG = re.compile(
    r"(?<![\w.,])(?P<a>\d{1,2}[.]\d{2,})\s?(?P<ha>[NS])\s?[,;/]?\s?(?:and\s)?(?P<b>\d{1,3}[.]\d{2,})\s?(?P<hb>[EW])(?![A-Za-z])"
)
KEYED = re.compile(
    r"(?i)(?:lat(?:itude)?\.?|coordinates?|gps)\D{0,25}?(?P<a>[-−–]?\d{1,2}[.]\d{2,})\s?[,;]\s?(?:long?(?:itude)?\.?\D{0,10}?)?(?P<b>[-−–]?\d{1,3}[.]\d{2,})"
)


def _f(s):
    return float(s.replace(",", ".")) if s else 0.0


def _snip(text, a, b, pad=60):
    return re.sub(r"\s+", " ", text[max(0, a - pad): b + pad]).strip()


def tokens(text):
    """Degree-sign tokens that carry a hemisphere letter."""
    out = []
    for m in TOKEN.finditer(text):
        h = m.group("post") or m.group("pre")
        if not h:
            continue
        d, mi, se = _f(m.group("d")), _f(m.group("m")), _f(m.group("s"))
        if mi >= 60 or se >= 60:
            continue
        val = d + mi / 60 + se / 3600
        axis = "lat" if h in "NS" else "lon"
        if (axis == "lat" and val > 90) or (axis == "lon" and val > 180):
            continue
        out.append({"axis": axis, "value": round(-val if h in "SW" else val, 5),
                    "start": m.start(), "end": m.end(), "raw": m.group(0).strip()})
    return out


def extract(text):
    """Return {'points': [...], 'axes': [...], 'nodeg': [...]} for one paper."""
    toks = tokens(text)
    points, used = [], set()
    for i, t in enumerate(toks[:-1]):
        u = toks[i + 1]
        if i in used or t["axis"] == u["axis"] or u["start"] - t["end"] > PAIR_GAP:
            continue
        lat, lon = (t, u) if t["axis"] == "lat" else (u, t)
        points.append({"lat": lat["value"], "lon": lon["value"], "tier": "A", "start": t["start"],
                       "snippet": _snip(text, t["start"], u["end"])})
        used.update((i, i + 1))
    axes = [{"axis": t["axis"], "value": t["value"], "tier": "B", "start": t["start"],
             "snippet": _snip(text, t["start"], t["end"])} for i, t in enumerate(toks) if i not in used]
    nodeg = []
    for m in NODEG.finditer(text):
        a, b = float(m.group("a")), float(m.group("b"))
        if a <= 90 and b <= 180:
            nodeg.append({"lat": -a if m.group("ha") == "S" else a, "lon": -b if m.group("hb") == "W" else b,
                          "tier": "C", "start": m.start(), "snippet": _snip(text, m.start(), m.end())})
    for m in KEYED.finditer(text):
        a = float(re.sub("[−–]", "-", m.group("a")))
        b = float(re.sub("[−–]", "-", m.group("b")))
        if abs(a) <= 90 and abs(b) <= 180:
            nodeg.append({"lat": a, "lon": b, "tier": "C", "start": m.start(),
                          "snippet": _snip(text, m.start(), m.end())})
    return {"points": points, "axes": axes, "nodeg": nodeg}


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
            elif has["axes"]:
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
