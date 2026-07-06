#!/usr/bin/env python3
"""
generate_closed_access_html.py

Manual-download helper HTMLs for CLOSED (not-open-access) papers still in the
queue. Grouped by PUBLISHER (one file each, for shared institutional auth),
then by JOURNAL within the file (most papers first). Links resolve via
https://doi.org/<doi> to the publisher page, where an authenticated user
downloads the PDF. Reuses the style + localStorage progress tracker from
generate_manual_download_html.py.

Usage:  python3 scripts/generate_closed_access_html.py
Output: outputs/manual_downloads/closed_access/<publisher>.html  + index.html
"""
import json, csv, re, urllib.parse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

BASE = Path(__file__).parent.parent
QUEUE = BASE / "docs/papers_data.json"
UW_LOG = BASE / "logs/unpaywall_download_log.csv"
OUT = BASE / "outputs/manual_downloads/closed_access"
MONITOR = (BASE / "scripts/monitor_firefox_pdfs.py").resolve()

# DOI prefix -> publisher (for the many queue rows with a blank publisher field)
PREFIX = {
    "10.1016": "Elsevier", "10.1002": "Wiley", "10.1111": "Wiley",
    "10.1046": "Wiley", "10.1006": "Wiley", "10.1007": "Springer", "10.1023": "Springer",
    "10.1038": "Springer Nature", "10.1017": "Cambridge University Press",
    "10.1080": "Taylor & Francis", "10.1201": "Taylor & Francis (CRC)",
    "10.1071": "CSIRO Publishing", "10.1139": "Canadian Science Publishing",
    "10.1093": "Oxford University Press", "10.1098": "Royal Society",
    "10.1126": "AAAS (Science)", "10.1152": "American Physiological Society",
    "10.1086": "University of Chicago Press", "10.1177": "SAGE",
    "10.2307": "JSTOR", "10.11646": "Magnolia Press (Zootaxa)",
    "10.1127": "Schweizerbart", "10.3354": "Inter-Research",
    "10.5343": "Bulletin of Marine Science", "10.3853": "Australian Museum",
    "10.1670": "Herpetologists' League / SSAR", "10.1242": "Company of Biologists",
    "10.1242/jeb": "Company of Biologists", "10.1554": "Wiley (Evolution)",
    "10.1643": "ASIH (Copeia)",
}

def sanitize(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

def clean_journal_name(p):
    """Journal name for grouping, stripping volume/page citation fragments that
    were baked into the journal field of some older/JSTOR entries, e.g.
    'Biological Bulletin, 61, 93-100' -> 'Biological Bulletin'."""
    j = (p.get("journal_clean") or p.get("journal") or "").strip()
    if not j:
        return "(no journal)"
    j = re.split(r",\s*\d", j)[0]           # cut at ', 61, 93-100' / ', 61'
    j = re.split(r"\s+\d{1,4}\s*[(:]", j)[0]  # cut at ' 1985(2): ...' / ' 61: 93-100'
    j = j.rstrip(" ,;:.")
    return j.strip() or "(no journal)"

def resolve_publisher(p):
    pub = (p.get("publisher") or "").strip()
    if pub and pub.lower() not in ("blank", "other", "unknown"):
        return pub
    doi = str(p.get("doi", "")).strip().lower()
    if not doi:
        return "Unknown publisher"
    prefix = doi.split("/")[0]
    return PREFIX.get(prefix, f"Other ({prefix})")

CSS = """
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
    .journal-header { background: #2c3e50; color: #fff; padding: 10px 15px; border-radius: 6px; margin: 28px 0 8px; font-size: 1.05em; }
    .stats { background: #fff; padding: 15px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .paper { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #3498db; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; }
    .paper:hover { transform: translateX(5px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
    .paper-number { display: inline-block; background: #3498db; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; margin-right: 10px; }
    .paper-id { color: #7f8c8d; font-size: 0.9em; margin-left: 10px; }
    .title { font-weight: bold; color: #2c3e50; margin: 8px 0; }
    .authors { color: #34495e; font-size: 0.95em; margin: 5px 0; }
    .year { color: #7f8c8d; font-size: 0.9em; }
    .url-link { display: inline-block; background: #27ae60; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-top: 10px; font-weight: bold; }
    .url-link:hover { background: #229954; }
    .alt-link { display: inline-block; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; margin: 10px 0 0 8px; font-size: 0.85em; font-weight: bold; }
    .alt-jstor { background: #b03a2e; } .alt-jstor:hover { background: #922b21; }
    .alt-fiu   { background: #1f618d; } .alt-fiu:hover   { background: #154360; }
    .alt-schol { background: #7d6608; } .alt-schol:hover { background: #5b4a06; }
    .export-btn { background: #8e44ad; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; font-weight: bold; cursor: pointer; margin-left: 16px; font-size: 0.85em; }
    .doi { color: #7f8c8d; font-size: 0.85em; margin-left: 12px; }
    .instructions { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0; }
    .instructions h3 { margin-top: 0; color: #856404; }
    .progress { background: #fff; padding: 15px; border-radius: 8px; margin: 20px 0; font-weight: bold; color: #27ae60; position: sticky; top: 0; z-index: 10; }
"""

JS = """
    let clicked = new Set();
    const KEY = 'clicked_' + document.title;
    if (localStorage.getItem(KEY)) {
        clicked = new Set(JSON.parse(localStorage.getItem(KEY)));
        document.getElementById('count').textContent = clicked.size;
        clicked.forEach(id => { const el = document.getElementById('paper-' + id); if (el) { el.style.opacity='0.5'; el.style.borderLeftColor='#95a5a6'; } });
    }
    function markClicked(id) {
        if (!clicked.has(id)) {
            clicked.add(id); document.getElementById('count').textContent = clicked.size;
            localStorage.setItem(KEY, JSON.stringify([...clicked]));
            const el = document.getElementById('paper-' + id); if (el) { el.style.opacity='0.5'; el.style.borderLeftColor='#95a5a6'; }
        }
    }
    // Route tracker: record which access route worked for each paper (last wins),
    // so the FIU access-map can be reconstructed from an exported routes JSON.
    let routes = {};
    const RKEY = 'routes_' + document.title;
    if (localStorage.getItem(RKEY)) { try { routes = JSON.parse(localStorage.getItem(RKEY)); } catch(e) {} }
    function useRoute(id, route) {
        routes[id] = route; localStorage.setItem(RKEY, JSON.stringify(routes)); markClicked(id);
    }
    function exportRoutes() {
        const blob = new Blob([JSON.stringify(routes, null, 2)], {type: 'application/json'});
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
        a.download = document.title.replace(/[^a-z0-9]+/gi, '_') + '_routes.json'; a.click();
    }
    document.addEventListener('keydown', e => { if (e.ctrlKey && e.key==='r') { if (confirm('Reset progress?')) { localStorage.removeItem(KEY); localStorage.removeItem(RKEY); location.reload(); } } });
"""

def build_page(publisher, papers):
    # group by journal, most papers first
    byj = defaultdict(list)
    for p in papers:
        byj[clean_journal_name(p)].append(p)
    journals = sorted(byj.items(), key=lambda kv: kv[0].lower())  # alphabetical by journal
    n = len(papers)
    parts = [f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Closed-access downloads: {publisher}</title><style>{CSS}</style></head><body>
<h1>🔒 Closed-access manual downloads: {publisher}</h1>
<div class="stats"><strong>Publisher:</strong> {publisher}<br><strong>Total papers:</strong> {n}
&nbsp;across&nbsp;{len(journals)} journal(s)<br><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<div class="instructions"><h3>📋 Instructions</h3><ol>
<li><strong>Log in once</strong> to your publisher/library access (VPN, FIU OneSearch, JSTOR) before starting.</li>
<li>Per paper, try routes in order: <strong>Download PDF (DOI)</strong> first; if no access, <strong>JSTOR</strong> → <strong>FIU OneSearch</strong> → <strong>Scholar</strong>. Save the PDF to your Downloads folder (it will be batch-ingested later).</li>
<li>Clicking any route greys the paper and records <em>which route worked</em> — this feeds the FIU access-map.</li>
<li>When you finish a page or pause, click <strong>⬇ Export routes</strong> and send the JSON: that reveals which journals/years need the library fallback vs. work direct.</li>
<li>Journals are ordered alphabetically; clear a whole journal before moving on. Pause every ~25.</li>
</ol></div>
<div class="progress">Progress: <span id="count">0</span> / {n} papers clicked
<button class="export-btn" onclick="exportRoutes()">⬇ Export routes</button></div><div id="papers">"""]
    i = 0
    for jname, ps in journals:
        parts.append(f'<div class="journal-header">📚 {jname} &nbsp;({len(ps)})</div>')
        for p in sorted(ps, key=lambda x: str(x.get("year", ""))):
            i += 1
            lid = p.get("literature_id"); doi = str(p.get("doi", "")).strip()
            url = f"https://doi.org/{doi}"
            # Strip terminal period(s)/whitespace — a trailing "." breaks JSTOR/FIU/
            # Scholar title lookups, so remove it for both display and search URLs.
            raw_title = (p.get("title") or "").strip().rstrip(".").strip()
            enc = urllib.parse.quote(raw_title, safe="")
            fiu_q = urllib.parse.quote("any,contains," + raw_title, safe="")
            jstor = f"https://www.jstor.org/action/doBasicSearch?Query={enc}&so=rel"
            fiu = (f"https://fiu-flvc.primo.exlibrisgroup.com/discovery/search?query={fiu_q}"
                   f"&tab=Everything&search_scope=MyInst_and_CI&vid=01FALSC_FIU%3AFIU&offset=0")
            scholar = f"https://scholar.google.com/scholar?q={enc}"
            title = raw_title.replace("<", "&lt;").replace(">", "&gt;")
            authors = (p.get("authors") or "").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(f"""<div class="paper" id="paper-{lid}"><span class="paper-number">{i}</span>
<span class="paper-id">ID: {lid}</span><span class="doi">{doi}</span>
<div class="title">{title}</div><div class="authors">{authors}</div><div class="year">Year: {p.get('year','')}</div>
<a href="{url}" class="url-link" target="_blank" onclick="useRoute('{lid}','doi')">📥 Download PDF (DOI)</a>
<a href="{jstor}" class="alt-link alt-jstor" target="_blank" onclick="useRoute('{lid}','jstor')">JSTOR</a>
<a href="{fiu}" class="alt-link alt-fiu" target="_blank" onclick="useRoute('{lid}','fiu')">FIU OneSearch</a>
<a href="{scholar}" class="alt-link alt-schol" target="_blank" onclick="useRoute('{lid}','scholar')">Scholar</a></div>""")
    parts.append(f"</div><script>{JS}</script></body></html>")
    return "".join(parts)

def main():
    d = json.load(open(QUEUE))
    uw = {}
    with open(UW_LOG) as f:
        r = csv.reader(f); next(r)
        for row in r:
            if len(row) >= 12:
                uw[row[0].strip().lower()] = row[10]
    closed = [p for p in d if str(p.get("doi", "")).strip()
              and uw.get(str(p.get("doi", "")).strip().lower()) == "not_open_access"]
    bypub = defaultdict(list)
    for p in closed:
        bypub[resolve_publisher(p)].append(p)
    OUT.mkdir(parents=True, exist_ok=True)
    THRESHOLD = 15  # publishers below this get folded into one "smaller_publishers" file
    big = {k: v for k, v in bypub.items() if len(v) >= THRESHOLD}
    small = [p for k, v in bypub.items() if len(v) < THRESHOLD for p in v]
    # Publishers whose HTML must NOT be overwritten (user is actively working them;
    # leaving them preserves their in-progress ordering/click state).
    SKIP_REGEN = {"Canadian Science Publishing"}
    index_rows = []
    for pub, papers in sorted(big.items(), key=lambda kv: -len(kv[1])):
        fn = f"{sanitize(pub)}.html"
        if pub in SKIP_REGEN and (OUT / fn).exists():
            print(f"  {len(papers):4d}  {pub}  -> {fn}  (SKIPPED — left as-is)")
        else:
            (OUT / fn).write_text(build_page(pub, papers), encoding="utf-8")
            print(f"  {len(papers):4d}  {pub}  -> {fn}")
        index_rows.append((pub, len(papers), fn))
    if small:
        (OUT / "smaller_publishers.html").write_text(
            build_page("Smaller publishers (mixed)", small), encoding="utf-8")
        index_rows.append((f"Smaller publishers (<{THRESHOLD} each)", len(small), "smaller_publishers.html"))
        print(f"  {len(small):4d}  smaller publishers -> smaller_publishers.html")
    # index
    links = "\n".join(f'<li><a href="{fn}">{pub}</a> — {n} papers</li>'
                      for pub, n, fn in index_rows)
    (OUT / "index.html").write_text(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Closed-access download helpers</title><style>{CSS}</style></head><body>
<h1>🔒 Closed-access download helpers (by publisher)</h1>
<div class="stats"><strong>Total closed papers:</strong> {len(closed)}<br>
<strong>Publisher files:</strong> {len(index_rows)}<br>
<strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<ul style="font-size:1.1em;line-height:1.8">{links}</ul></body></html>""", encoding="utf-8")
    print(f"\nTotal closed: {len(closed)} across {len(bypub)} publishers")
    print(f"Index: {OUT / 'index.html'}")

if __name__ == "__main__":
    main()
