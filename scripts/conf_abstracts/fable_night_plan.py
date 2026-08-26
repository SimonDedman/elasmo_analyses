"""Print the uncached Fable worklist indices for the given book keys, sized for
an overnight run (Simon, 2026-08-26: queue ~2 Max windows' worth, ~15-20 chunks
per window, launch at bedtime, relaunch the remainder after the reset).

Usage: fable_night_plan.py JMIH2015 JMIH2008 JMIH2007
Prints one JSON line: {"indices":[...], "per_book":{...}, "n":N}
"""
import json, os, sys
from pathlib import Path
WL = Path(__file__).resolve().parents[2] / "outputs" / "conf_abstracts" / "fable_worklist.json"
w = json.loads(WL.read_text())
books = sys.argv[1:]
idx, per = [], {}
for x in w:
    if x.get("book_key") in books and not (os.path.exists(x["cache_path"]) and os.path.getsize(x["cache_path"]) >= 2):
        idx.append(x["index"]); per[x["book_key"]] = per.get(x["book_key"], 0) + 1
print(json.dumps({"indices": idx, "per_book": per, "n": len(idx)}))
