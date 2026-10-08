"""Build the static public abstracts browser: docs/abstracts/index.html + data/*.json.

Reads database/conference_abstracts.db (read-only), outputs/conference_coverage_matrix.xlsx
(Coverage sheet) and data/matrix_legend.json. Run: python3 scripts/conf_abstracts/build_abstracts_site.py
Data layout (all under docs/abstracts/data/):
  meta.json        counts, meetings, series, presentation types, index file list, search manifest
  index_N.json     compact rows: [idx, abstract_id, meeting_idx, year, title, first_author, presenter, n_authors, is_elasmo, ptype_idx]
  abs_N.json       full text + authors for rows idx//SHARD == N
  s_<f><N>.json    inverted index shards per field f in t(itle)/a(uthors)/b(abstract): {word: "delta,coded,idx"}
  coverage.json    society x year grid
"""
import json, re, sqlite3, unicodedata, shutil
from collections import defaultdict, Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database" / "conference_abstracts.db"
XLSX = REPO / "outputs" / "conference_coverage_matrix.xlsx"
LEGEND = REPO / "data" / "matrix_legend.json"
OUT = REPO / "docs" / "abstracts"
DATA = OUT / "data"
SHARD = 500          # abstracts per full-text shard
INDEX_CHUNK = 8000   # rows per compact index file
SEARCH_MAX = 2_400_000  # bytes per inverted-index file (target)
STATUSES = ["Missing", "Schedule", "Hardcopy", "OCR", "Programme", "Pending", "Digital", "Extracted", "Partial", "Ingested", "NA"]
FILL = {"Missing": "E06666", "Schedule": "ED9C6B", "Hardcopy": "F6B26B", "OCR": "F9CB9C", "Programme": "FFD966",
        "Pending": "FFE599", "Digital": "B6D7A8", "Extracted": "93C47D", "Partial": "A2C4C9", "Ingested": "6AA84F"}
GAP = {"Missing", "Schedule", "Hardcopy", "Programme", "Pending"}
MAIN = ["ASIH/JMIH", "AES", "EEA", "OCS", "SI"]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def words(s):
    return re.findall(r"[a-z0-9]+", norm(s))


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path.stat().st_size


def main():
    if DATA.exists():
        shutil.rmtree(DATA)
    DATA.mkdir(parents=True)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    meetings = [dict(r) for r in con.execute("select * from meetings order by meeting, year, meeting_id")]
    mid_to_i = {m["meeting_id"]: i for i, m in enumerate(meetings)}
    authors = defaultdict(list)
    for r in con.execute("select * from authors order by abstract_id, position"):
        authors[r["abstract_id"]].append(r)
    rows = [dict(r) for r in con.execute("select * from abstracts")]
    # newest first, then meeting, then programme number
    def pn(r):
        m = re.search(r"\d+", str(r["program_number"] or ""))
        return int(m.group()) if m else 10**9
    rows.sort(key=lambda r: (-(meetings[mid_to_i[r["meeting_id"]]]["year"] or 0), mid_to_i[r["meeting_id"]], pn(r), r["abstract_id"]))
    ptypes = sorted({(r["presentation_type"] or "").strip() or "unspecified" for r in rows})
    pt_i = {p: i for i, p in enumerate(ptypes)}

    index = []
    postings = {f: defaultdict(list) for f in 'tab'}  # t=title, a=authors, b=abstract text
    n_auth_total = 0
    for idx, r in enumerate(rows):
        au = authors.get(r["abstract_id"], [])
        n_auth_total += len(au)
        first = au[0]["full_name"] if au else ""
        pres = next((a["full_name"] for a in au if a["is_presenter"]), "")
        mi = mid_to_i[r["meeting_id"]]
        index.append([idx, r["abstract_id"], mi, meetings[mi]["year"], r["title"] or "", first, pres, len(au),
                      1 if r["is_elasmo"] else 0, pt_i[(r["presentation_type"] or "").strip() or "unspecified"]])
        for t in set(words(r["title"])):
            postings["t"][t].append(idx)
        for t in set(words(r["abstract_text"])):
            postings["b"][t].append(idx)
        for t in {w for a in au for w in words(a["full_name"])}:
            postings["a"][t].append(idx)

    # full-text shards
    n_shards = (len(rows) + SHARD - 1) // SHARD
    sizes = {}
    for s in range(n_shards):
        d = {}
        for idx in range(s * SHARD, min(len(rows), (s + 1) * SHARD)):
            r = rows[idx]
            d[idx] = [r["abstract_text"] or "", r["session_name"] or "", str(r["program_number"] or ""),
                      r["session_datetime"] or "", r["elasmo_basis"] or "",
                      [[a["full_name"], a["affiliation"] or "", a["affiliation_country"] or "", 1 if a["is_presenter"] else 0]
                       for a in authors.get(r["abstract_id"], [])]]
        sizes[f"abs_{s}.json"] = dump(DATA / f"abs_{s}.json", d)

    index_files = []
    for c in range(0, len(index), INDEX_CHUNK):
        name = f"index_{c // INDEX_CHUNK}.json"
        sizes[name] = dump(DATA / name, index[c:c + INDEX_CHUNK])
        index_files.append(name)

    # inverted index per field (t/a/b): drop 1-char words and (abstract only) words in >30% of docs;
    # shard by 2-char key, packed to size. The page ORs the fields for the mixed box and uses one for each field box.
    n = len(rows)
    manifest = {}
    for fld in "tab":
        by_key = defaultdict(dict)
        for w, ids in postings[fld].items():
            if len(w) < 2 or (fld == "b" and len(ids) > 0.3 * n):
                continue
            prev, out = 0, []
            for i in sorted(ids):
                out.append(i - prev); prev = i
            by_key[w[:2]][w] = ",".join(map(str, out))
        manifest[fld] = {}
        cur, cur_size, fi = [], 0, 0
        def flush():
            nonlocal cur, cur_size, fi
            if not cur:
                return
            name = f"s_{fld}{fi}.json"
            merged = {}
            for k in cur:
                merged.update(by_key[k])
                manifest[fld][k] = name
            sizes[name] = dump(DATA / name, merged)
            cur, cur_size, fi = [], 0, fi + 1
        for k in sorted(by_key):
            sz = sum(len(w) + len(v) + 6 for w, v in by_key[k].items())
            if cur and cur_size + sz > SEARCH_MAX:
                flush()
            cur.append(k); cur_size += sz
        flush()

    # coverage grid from the matrix workbook
    cov = {"series": [], "years": [], "cells": {}, "gaps": {}}
    try:
        import openpyxl
        ws = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)["Coverage"]
        data = list(ws.iter_rows(values_only=True))
        head = list(data[0])
        pat = re.compile(r"(?:^|; )(" + "|".join(STATUSES) + r")\b")
        grid = {}
        for row in data[1:]:
            y = row[0]
            if not isinstance(y, (int, float)):
                continue
            for j, cell in enumerate(row[1:], 1):
                if not cell:
                    continue
                txt = str(cell)
                m = pat.search(txt.split(" — ")[0])
                if not m or m.group(1) == "NA":
                    continue
                loc = txt.split(" — ")[0][:m.start()].strip().rstrip(";").strip()
                loc = re.sub(r"\s*\(\d+\)$", "", loc)
                if head[j] == "EEA" and int(y) == 2020:
                    continue  # no meeting (covid); the workbook on disk predates that correction
                grid[(head[j], int(y))] = [m.group(1), "" if loc in ("?", "none") else loc]
        START = 1983  # the matrix figure's first year (AES); the workbook runs to 1916 but only ASIH/JMIH is populated before 1973
        used = sorted({s for (s, y) in grid if y >= START} | set(MAIN),
                      key=lambda s: (MAIN.index(s) if s in MAIN else 99, head.index(s) if s in head else 999))
        cov["series"] = used
        cov["start"] = START
        cov["years"] = sorted({y for (s, y) in grid if y >= START and s in used})
        for (s, y), v in grid.items():
            if s in used and y >= START:
                cov["cells"].setdefault(s, {})[y] = v
        for s in MAIN:
            cov["gaps"][s] = sorted(y for (ss, y), v in grid.items() if ss == s and y >= START and v[0] in GAP)
    except Exception as e:  # coverage is optional
        print("coverage skipped:", e)
    leg = json.loads(LEGEND.read_text())
    meanings = leg["meanings"]
    # public page: strip private names from the legend
    scrub = {"(Carylanne, Cat, Ali)": "(a member holds a paper copy)", "A named contact has it or is looking for it": "Someone is looking for it or has promised it"}
    for k, v in meanings.items():
        for a, b in scrub.items():
            v = v.replace(a, b)
        meanings[k] = v
    cov["legend"] = {k: {"text": v, "colour": "#" + FILL.get(k, "FFFFFF")} for k, v in meanings.items() if k in FILL}
    sizes["coverage.json"] = dump(DATA / "coverage.json", cov)

    series = Counter(m["meeting"] for m in meetings)
    meta = {
        "counts": {"meetings": len(meetings), "abstracts": n, "elasmo": sum(1 for r in rows if r["is_elasmo"]),
                   "authors": len({norm(a["full_name"]) for v in authors.values() for a in v}), "author_rows": n_auth_total},
        "meetings": [[m["meeting"], m["year"], m["name"] or "", m["location"] or "", m["n_abstracts"] or 0, m["meeting_id"]] for m in meetings],
        "series": sorted(series), "ptypes": ptypes, "years": [min(m["year"] for m in meetings), max(m["year"] for m in meetings)],
        "index_files": index_files, "shard": SHARD, "search": manifest,
    }
    sizes["meta.json"] = dump(DATA / "meta.json", meta)
    (OUT / "index.html").write_text(HTML, encoding="utf-8")
    for k, v in sorted(sizes.items(), key=lambda kv: -kv[1])[:5]:
        print(k, round(v / 1e6, 2), "MB")
    print("files", len(sizes), "total MB", round(sum(sizes.values()) / 1e6, 1), meta["counts"])


HTML = (Path(__file__).with_name('abstracts_site_template.html')).read_text(encoding='utf-8')
if __name__ == "__main__":
    main()
