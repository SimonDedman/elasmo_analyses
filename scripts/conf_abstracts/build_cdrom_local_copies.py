"""Browsable copies of a JMIH meeting CD-ROM, sorted by session, with an index page.

Carylanne Maier asked (via Simon, 2026-10-21) for the CD abstracts sorted into
plain folders she can keep, with an index page saying what each folder holds.
The CDs never record days or times, so the folders follow the CD's own
structure:
  2003  By session/<NN Subject area>/<Fish|Herps>/  and
        By session/00 Symposia/<Society symposium>/
  2004  By author/Authors <A-B ... S-Z>/  (the CD's own author-letter pages)
Written beside the filed CD (config.CDROM_SOURCES, in SharkPapers/Conferences/<year>/).
First built in Carylanne's inbox for her to download (2026-10-21); she took them
on 2026-10-22 and the inbox copy was retired.
Each abstract is copied (never moved or linked: the folder is Synology-synced)
as '<First author> [et al] - <Title>.pdf', and an index page beside the CD's
own files ('Abstracts index.html') lists every folder and abstract, with shark/ray/chimaera talks marked.

Usage:
  build_cdrom_local_copies.py --year 2003            # dry run: counts only
  build_cdrom_local_copies.py --year 2003 --apply    # copy + write the index page
"""
import argparse
import html
import re
import shutil
import urllib.parse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import ingest_jmih_cdrom as I  # noqa: E402

AUTHOR_GROUPS = [("A-B", "AB"), ("C-F", "CDEF"), ("G-J", "GHIJ"), ("K-M", "KLM"),
                 ("N-R", "NOPQR"), ("S-Z", "STUVWXYZ")]
REL_MAX = 120     # characters below 'Undigitised Programs\\' (base 123 on the laptop)
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe(s, n=110):
    s = _BAD.sub("", I._clean(s)).strip(" .")
    return s[:n].rstrip(" .") or "untitled"


def first_surname(rec):
    if not rec["authors"]:
        return "Unknown"
    return rec["authors"][0]["full_name"].split()[-1]


def folder_for(year, rec):
    if year == 2003:
        s = rec["session_name"] or ""
        if s.startswith("Symposium: "):
            return ("00 Symposia", safe(s[len("Symposium: "):], 40))
        if s.startswith("Not listed"):
            return ("99 Not on CD index",)
        m = re.match(r"(.*?) \((Fish|Herps)\)$", s)
        return (safe(m.group(1), 60), m.group(2)) if m else (safe(s, 60),)
    letter = I._clean(first_surname(rec))[:1].upper()
    for label, letters in AUTHOR_GROUPS:
        if letter in letters:
            return (f"Authors {label}",)
    return ("Authors other",)


def plan(year, recs, root):
    top = root / ("By session" if year == 2003 else "By author")
    # number the subject areas alphabetically so the folder list reads in order
    if year == 2003:
        areas = sorted({folder_for(year, r)[0] for r in recs} - {"00 Symposia", "99 Not on CD index"})
        num = {a: f"{i:02d} {a}" for i, a in enumerate(areas, 1)}
    used, out = set(), []
    for r in sorted(recs, key=lambda r: (folder_for(year, r), first_surname(r).lower(), r["title"].lower())):
        parts = list(folder_for(year, r))
        if year == 2003 and parts[0] in num:
            parts[0] = num[parts[0]]
        lead = first_surname(r) + (" et al" if len(r["authors"]) > 2 else
                                   f" & {r['authors'][1]['full_name'].split()[-1]}" if len(r["authors"]) == 2 else "")
        # Windows (the laptop, Carylanne's machine) stops at 260 characters, and
        # the synced root is already ~120 deep: cap each path below the year
        # folder at REL_MAX, shortening the title to fit.
        # measured as if under '<year>\\' (the first build's layout) so names stay
        # stable wherever the copies live; the library path on the laptop is shorter
        rel_dir = len(str(Path(top.name).joinpath(*parts))) + len(str(year)) + 2
        room = max(30, REL_MAX - rel_dir - len(".pdf") - 5)
        name = safe(f"{safe(lead, 30)} - {safe(r['title'])}", room)
        dst = top.joinpath(*parts) / f"{name}.pdf"
        k = 2
        while str(dst).lower() in used:
            dst = top.joinpath(*parts) / f"{name} ({k}).pdf"; k += 1
        used.add(str(dst).lower())
        out.append((r, Path(r["_cd"]) / r["source_file"], dst))
    return top, out


def index_html(year, root, top, items, city):
    groups = defaultdict(list)
    for r, _src, dst in items:
        groups[dst.parent.relative_to(root)].append((r, dst))
    n_el = sum(1 for r, _, _ in items if r["is_elasmo"])
    rows = []
    for folder in sorted(groups):
        lst = groups[folder]
        e = sum(1 for r, _ in lst if r["is_elasmo"])
        rows.append(f'<details open><summary><span class="f">{html.escape(str(folder))}</span>'
                    f' <span class="n">{len(lst)} abstracts{f", {e} shark/ray" if e else ""}</span></summary><ol>')
        for r, dst in lst:
            # percent-encoded so '#', '%', '&' or accents in a name cannot break the link
            href = "/".join(urllib.parse.quote(p) for p in dst.relative_to(root).parts)
            auth = "; ".join(a["full_name"] for a in r["authors"])
            badge = '<span class="b">shark/ray</span> ' if r["is_elasmo"] else ""
            rows.append(f'<li data-s="{html.escape((r["title"] + " " + auth).lower())}">{badge}'
                        f'<a href="{html.escape(href)}">{html.escape(r["title"])}</a>'
                        f'<div class="a">{html.escape(auth)}</div></li>')
        rows.append("</ol></details>")
    how = ("subject area (then Fish or Herps) and symposium, as on the CD's own area pages"
           if year == 2003 else "first author's surname, in the CD's own A-B ... S-Z groups (the CD lists no sessions)")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JMIH {year} abstracts</title>
<style>
:root{{--bg:#fff;--fg:#1d2329;--mut:#5b6670;--acc:#1f5f8b;--line:#dde3e8;--b:#C0362C}}
@media (prefers-color-scheme:dark){{:root{{--bg:#15191d;--fg:#e6eaee;--mut:#9aa6b0;--acc:#7fb8e0;--line:#2c343b;--b:#e0675d}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:980px;padding:16px}}
h1{{font-size:1.4em;margin:.2em 0}} p{{color:var(--mut)}} a{{color:var(--acc)}}
summary{{cursor:pointer;padding:6px 0;border-top:1px solid var(--line)}} .f{{font-weight:600}} .n{{color:var(--mut);font-size:.9em}}
ol{{margin:.2em 0 .8em 1.2em;padding:0}} li{{margin:.35em 0}} .a{{color:var(--mut);font-size:.88em}}
.b{{background:var(--b);color:#fff;border-radius:3px;font-size:.75em;padding:0 5px}}
input{{width:100%;box-sizing:border-box;padding:8px;font:inherit;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px}}
button{{font:inherit;margin:8px 8px 8px 0}}
</style></head><body>
<h1>Joint Meeting of Ichthyologists and Herpetologists {year}, {html.escape(city)}</h1>
<p>{len(items)} abstracts copied from the meeting CD-ROM, {n_el} of them on sharks, rays, or chimaeras.
Folders are by {how}. Each file is the CD's own PDF for one abstract, renamed
'First author - Title'. The CD's original files are untouched beside this page.
To keep a copy, keep this page and the '{top.name}' folder side by side in the same folder
(the CD's other files are optional); the links are relative, so they work wherever the pair is saved.
Built 21 Oct 2026 for Shark Oracle.</p>
<input id="q" placeholder="Filter by title or author" oninput="f()">
<button onclick="t(true)">Expand all</button><button onclick="t(false)">Collapse all</button>
{''.join(rows)}
<script>
function t(o){{document.querySelectorAll('details').forEach(d=>d.open=o)}}
function f(){{const q=document.getElementById('q').value.toLowerCase();
document.querySelectorAll('details').forEach(d=>{{let k=0;d.querySelectorAll('li').forEach(li=>{{const s=li.dataset.s.includes(q);li.style.display=s?'':'none';k+=s}});d.style.display=k?'':'none';if(q)d.open=true}})}}
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    cd, city = C.CDROM_SOURCES[("JMIH", a.year)]
    recs, cov = I.read_cd(a.year, cd)
    for r in recs:
        I._elasmo(r, "JMIH", a.year)
        r["_cd"] = cd
    # Beside the filed CD in the conference library (moved from Carylanne's inbox
    # copy 2026-10-22, once she had downloaded hers), so the links stay relative.
    root = Path(cd)
    top, items = plan(a.year, recs, root)
    clash = [d for _, _, d in items if d.exists()]
    folders = {d.parent for _, _, d in items}
    print(f"JMIH {a.year}: {len(items)} abstracts -> {len(folders)} folders under {top}")
    print(f"  {sum(r['is_elasmo'] for r in recs)} shark/ray; {len(clash)} destination files already exist (kept)")
    if not a.apply:
        print("dry run - nothing written; pass --apply")
        return
    n = 0
    for _r, src, dst in items:
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n += 1
    # Not 'index.html': the 2004 CD's own home page already has that name.
    page = root / "Abstracts index.html"          # ours, regenerated on every run
    page.write_text(index_html(a.year, root, top, items, city), encoding="utf-8")
    on_disk = sum(1 for _ in top.rglob("*.pdf"))
    print(f"  copied {n}; {on_disk} PDFs now under {top.name}; wrote {page}")
    if on_disk != len(items):
        sys.exit(f"MISMATCH: {on_disk} PDFs on disk vs {len(items)} planned")


if __name__ == "__main__":
    main()
