#!/usr/bin/env python3
"""Progress display for scripts/topic_review_build_all.sh (for `watch`). State, not just counts:
QUEUED / RUNNING / DONE / FAILED / SKIPPED per topic and stage, rate from completed feature passes,
ETA as an absolute clock time, and the log's last lines including any error."""
import json, os, re, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "topic_review"
ST, LOG = OUT / "build_all_status.json", OUT / "build_all.log"
topics = sorted(p.stem for p in (ROOT / "data" / "topic_review").glob("*.json"))
d = json.load(open(ST)) if ST.exists() else {}
now = time.time()
def st(t, stage):
    e = d.get(t, {}).get(stage); return (e or {}).get("state", "QUEUED").upper(), (e or {}).get("seconds"), (e or {}).get("at")
feat_done = [st(t, "features")[1] for t in topics if st(t, "features")[0] == "DONE" and st(t, "features")[1]]
page_done = [st(t, "pages")[1] for t in topics if st(t, "pages")[0] == "DONE" and st(t, "pages")[1]]
mf = sum(feat_done) / len(feat_done) if feat_done else 480.0
mp = sum(page_done) / len(page_done) if page_done else 130.0
remaining = 0.0
rows = []
for t in topics:
    fs, fsec, fat = st(t, "features"); ps, psec, pat = st(t, "pages")
    if fs == "RUNNING":
        el = now - time.mktime(time.strptime(fat, "%Y-%m-%d %H:%M:%S")); remaining += max(0, mf - el) + mp
        fs = f"RUNNING {el/60:.0f}m"
    elif fs == "QUEUED": remaining += mf + mp
    elif ps == "RUNNING":
        el = now - time.mktime(time.strptime(pat, "%Y-%m-%d %H:%M:%S")); remaining += max(0, mp - el); ps = f"RUNNING {el/60:.0f}m"
    elif ps == "QUEUED": remaining += mp
    rows.append((t, fs, f"{fsec/60:.1f}m" if fsec else "", ps, f"{psec/60:.1f}m" if psec else ""))
pool = st("_shared", "pool")[0]; chain = st("_all", "chain")[0]
if pool == "QUEUED": remaining += 70
failed = any("FAILED" in r[1] or "FAILED" in r[3] for r in rows) or pool == "FAILED"
state = "DONE" if chain == "DONE" else ("FAILED (chain continues)" if failed else "RUNNING")
if ST.exists() and now - ST.stat().st_mtime > 1800 and chain != "DONE": state = "STALLED? (no status change for %d min)" % ((now - ST.stat().st_mtime) / 60)
print(f"topic review build-all   {state}   updated {d.get('_updated', '-')}")
print(f"{'topic':18s} {'features':14s} {'took':7s} {'pages':14s} {'took':7s}")
for r in rows: print(f"{r[0]:18s} {r[1]:14s} {r[2]:7s} {r[3]:14s} {r[4]:7s}")
print(f"{'shared pool':18s} {pool}")
print(f"\nfeatures done {len(feat_done)}/{len(topics)} (mean {mf/60:.1f} min)   pages done {len(page_done)}/{len(topics)} (mean {mp/60:.1f} min)")
if chain != "DONE" and not failed:
    eta = now + remaining; print(f"eta ~{remaining/60:.0f} min ({time.strftime('%H:%M %Z', time.localtime(eta))})")
if LOG.exists():
    tail = LOG.read_text(errors="ignore").splitlines()[-6:]
    print("\nlog tail:"); [print("  " + l[:150]) for l in tail]
    errs = [l for l in LOG.read_text(errors="ignore").splitlines() if re.search(r"Traceback|Error|FAILED|!!!", l)]
    if errs: print(f"\nERRORS in log: {len(errs)}"); [print("  " + l[:150]) for l in errs[-5:]]
