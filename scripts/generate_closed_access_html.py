#!/usr/bin/env python3
"""
generate_closed_access_html.py

Download-helper pages for EVERY outstanding paper (conference abstracts
excluded): one card per paper with search buttons and a "Got it" button that
writes to the shared record the downloading hub also reads.

- Papers WITH a DOI: one page per publisher (shared institutional login),
  journals grouped within it.
- Papers WITHOUT a DOI: one page per journal with >= 20 such papers, the rest
  pooled alphabetically into pages of about 300.

Also writes helper_map.json (hub journal / publisher -> helper page), which
docs/remaining_downloads.html uses to offer "Open the download helper".
The name is historical (the pages once covered closed-access DOIs only); the
output directory keeps its name so links already sent out keep working.

Usage:  python3 scripts/generate_closed_access_html.py
Output: docs/closed_access/*.html + index.html + helper_map.json
"""
import json, csv, re, urllib.parse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

BASE = Path(__file__).parent.parent
QUEUE = BASE / "docs/papers_data.json"
UW_LOG = BASE / "logs/unpaywall_download_log.csv"
# Published under docs/ so the team can actually reach these pages: anything in
# outputs/ is gitignored and therefore never reaches GitHub Pages.
import sys as _sys
_sys.path.insert(0, str((BASE / "scripts").resolve()))
from lib.crossref_prefix import publisher_for_prefix  # noqa: E402

OUT = BASE / "docs/closed_access"
MONITOR = (BASE / "scripts/monitor_firefox_pdfs.py").resolve()

# DOI prefix -> publisher (for the many queue rows with a blank publisher field)
PREFIX = {
    "10.1016": "Elsevier", "10.1002": "Wiley", "10.1111": "Wiley",
    "10.1046": "Wiley", "10.1006": "Elsevier (Academic Press)", "10.1007": "Springer", "10.1023": "Springer",
    "10.1038": "Springer", "10.1017": "Cambridge University Press",
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
    # Track E 2026-09-17: Crossref/DataCite-resolved prefixes covering the
    # bulk of rows previously shown under an unclear publisher.
    "10.5962": "Biodiversity Heritage Library",
    "10.3390": "MDPI",
    "10.1144": "Geological Society of London",
    "10.2989": "National Inquiry Services Center (NISC)",
    "10.18785": "University of Southern Mississippi",
    "10.1660": "Kansas Academy of Science",
    "10.18563": "Centre National de la Recherche Scientifique - Institut des Sciences de l'Evolution de Montpellier",
    "10.4324": "Taylor & Francis",
    "10.1638": "American Association of Zoo Veterinarians",
    "10.1371": "PLoS",
    "10.1578": "Aquatic Mammals Journal",
    "10.15517": "Universidad de Costa Rica",
    "10.1590": "SciELO",
    "10.3989": "Editorial CSIC",
    "10.2331": "Japanese Society of Fisheries Science",
    "10.5479": "Smithsonian Institution",
    "10.1163": "Brill",
    "10.1645": "American Society of Parasitologists",
    "10.4049": "The American Association of Immunologists",
    "10.3406": "PERSEE Program",
    "10.26515": "Zoological Survey of India",
    "10.1130": "Geological Society of America",
    "10.7589": "Wildlife Disease Association",
    "10.1577": "American Fisheries Society",
    "10.25268": "Marine and Coastal Research Institute INVEMAR",
    "10.4067": "SciELO (ANID)",
    "10.32360": "Arquivos de Ciências do Mar",
    "10.1671": "Society of Vertebrate Paleontology",
    "10.2960": "Northwest Atlantic Fisheries Organization (NAFO)",
    "10.1097": "Ovid Technologies (Wolters Kluwer Health)",
    "10.1042": "Portland Press Ltd.",
    "10.2475": "American Journal of Science (AJS)",
    "10.56577": "New Mexico Geological Society",
    "10.1051": "EDP Sciences",
    "10.1186": "Springer",
    "10.18475": "University of Puerto Rico at Mayaguez",
    "10.1656": "Humboldt Field Research Institute",
    "10.13140": "ResearchGate (pseudo-DOI, not a publisher)",
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

# Stored publisher values that carry no information and must not shadow the
# DOI prefix. "Unknown publisher" is the literal string written into
# papers_data.json, and treating it as authoritative kept 608 DOI-bearing rows
# filed under "Unknown publisher" when their prefix names the publisher
# outright.
_EMPTY_PUBLISHERS = {"blank", "other", "unknown", "unknown publisher",
                     "none", "n/a", "na", "-"}


# One name per publisher. Stored values and Crossref member names both pass
# through this, so "MDPI AG" and "MDPI" are one bar on the dashboard and one
# filter value on the download hub (Simon, 2026-09-18). Keys are lower-case.
PUBLISHER_ALIASES = {
    "mdpi ag": "MDPI",
    "springer nature": "Springer",
    "nature/springer": "Springer",
    "springer science and business media llc": "Springer",
    "museum national d'histoire naturelle, paris, france": "Museum Nat Hist Naturelle",
}


def canonical_publisher(name: str) -> str:
    name = (name or "").strip()
    return PUBLISHER_ALIASES.get(name.lower(), name)


def resolve_publisher(p):
    pub = (p.get("publisher") or "").strip()
    if pub and pub.lower() not in _EMPTY_PUBLISHERS:
        return canonical_publisher(pub)
    doi = str(p.get("doi", "")).strip().lower()
    if not doi:
        return "Unknown publisher"
    prefix = doi.split("/")[0]
    if prefix in PREFIX:
        return canonical_publisher(PREFIX[prefix])
    # Sub-prefixes the hand map never listed (Wiley 10.1002, Elsevier 10.1006,
    # Informa 10.1080 variants ...): ask Crossref once, cached on disk.
    name = publisher_for_prefix(prefix)
    return canonical_publisher(name) if name else f"Other ({prefix})"

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
    .controls { background: #eaf2f8; border: 1px solid #d4e6f1; padding: 12px 15px; border-radius: 8px; margin: 20px 0; }
    .controls select, .controls input, .controls button { font-size: 0.9em; padding: 3px 8px; border-radius: 4px; border: 1px solid #bdc3c7; }
    .controls button { cursor: pointer; background: #fff; }
    .controls button:hover { background: #d6eaf8; }
"""

# Kept in step with the YOU dropdown in docs/remaining_downloads.html; the
# selection is shared through the same localStorage key.
TEAM = ["Alex", "Andrew", "Brit", "Carylanne", "Cat", "Chiara", "Chris", "David Green", "David RG", "David S",
        "Deven", "Dovi", "Elena", "Emily", "Guuske", "Jürgen", "Lola", "Mike", "Nathan", "Nick",
        "Rima", "Ryan", "Simon", "Sophia", "Tobi-Dawne", "Ulrich", "Other"]
USER_OPTIONS = '<option value="">--</option>' + "".join(
    f'<option value="{n}">{n}</option>' for n in TEAM)

CSS_EXTRA = """
    .citation { color: #566573; font-size: 0.85em; margin: 3px 0; }
    .oa-badge { display: inline-block; font-size: 0.75em; border-radius: 4px; padding: 1px 6px; margin-left: 8px; background: #d5f5e3; color: #1e8449; }
    .alt-google { background: #566573; } .alt-google:hover { background: #3d4a55; }
    .alt-bhl    { background: #117864; } .alt-bhl:hover    { background: #0b5345; }
    .alt-oa     { background: #1e8449; } .alt-oa:hover     { background: #145a32; }
    .outcome { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .got, .cant, .undo { border: 1px solid #bdc3c7; background: #fff; border-radius: 4px; padding: 5px 12px; cursor: pointer; font-weight: bold; font-size: 0.85em; }
    .got { border-color: #27ae60; color: #1e8449; } .got:hover { background: #eafaf1; }
    .cant { border-color: #c0392b; color: #922b21; } .cant:hover { background: #fdedec; }
    .who { color: #7f8c8d; font-size: 0.8em; }
    .paper.done { opacity: 0.45; border-left-color: #95a5a6; }
    .paper.nope { border-left-color: #c0392b; }
    .paper.nope .title::after { content: "  (you couldn't get this)"; font-weight: normal; color: #922b21; font-size: 0.85em; }
    .toc { background: #fff; padding: 10px 15px; border-radius: 8px; margin: 12px 0; font-size: 0.9em; line-height: 1.8; }
    .toc a { color: #1f618d; margin-right: 12px; white-space: nowrap; }
    .hidebar { font-size: 0.85em; margin-left: 16px; font-weight: normal; color: #2c3e50; }
    .back { font-size: 0.9em; }
"""

# The shared record (a Google Apps Script sheet) is keyed by DOI. Rows without a
# DOI use "lid:<literature_id>", which the hub uses too, so a mark made on either
# page shows on both.
JS = """
    const SHEET = 'https://script.google.com/macros/s/AKfycbwCmkL89I8GGK3-IoCZh9x9XAVpvTshOysMlnWiRmqoXAtICFO16TkljEPlxTwXaufR/exec';
    const MINE = 'helper_outcomes';          // per-browser: {key: 'got'|'cant'}
    let mine = {};
    try { mine = JSON.parse(localStorage.getItem(MINE) || '{}'); } catch (e) {}
    let shared = {};                         // key -> {by, at}, from the shared record
    const keyOf = el => el.dataset.key;
    const me = () => localStorage.getItem('eea_username') || 'Anon';

    function paint() {
        let done = 0, cant = 0;
        document.querySelectorAll('.paper').forEach(el => {
            const k = keyOf(el), s = shared[k], m = mine[k];
            el.classList.toggle('done', !!s || m === 'got');
            el.classList.toggle('nope', m === 'cant' && !s);
            const w = el.querySelector('.who');
            w.textContent = s ? ('Marked as got by ' + (s.by || 'someone') + (s.at ? ' on ' + String(s.at).slice(0, 10) : '') + '; not filed yet. If you have it too, drop it in anyway.') : '';
            el.querySelector('.got').style.display = s ? 'none' : '';
            el.querySelector('.undo').style.display = s ? '' : 'none';
            if (s || m === 'got') done++; else if (m === 'cant') cant++;
        });
        document.getElementById('count').textContent = done;
        document.getElementById('cantcount').textContent = cant;
        applyHide();
    }
    function applyHide() {
        const hide = document.getElementById('hideDone').checked;
        document.querySelectorAll('.paper.done').forEach(el => el.style.display = hide ? 'none' : '');
        document.querySelectorAll('.paper:not(.done)').forEach(el => el.style.display = '');
    }
    function saveMine() { try { localStorage.setItem(MINE, JSON.stringify(mine)); } catch (e) {} }
    function post(body) { return fetch(SHEET, {method: 'POST', mode: 'no-cors', body: JSON.stringify(body)}).catch(() => {}); }

    // "Got it" is the only thing that tells the team a paper is done. Clicking a
    // search button records nothing: a click that hit a paywall got no PDF.
    function got(btn) {
        const el = btn.closest('.paper'), k = keyOf(el);
        mine[k] = 'got'; saveMine();
        shared[k] = {by: me(), at: new Date().toISOString()};
        post({action: 'markClicked', doi: k, title: el.dataset.title || '', by: me(), at: shared[k].at});
        paint();
    }
    function cant(btn) {
        const el = btn.closest('.paper'), k = keyOf(el);
        mine[k] = mine[k] === 'cant' ? undefined : 'cant'; saveMine(); paint();
    }
    function undo(btn) {
        const el = btn.closest('.paper'), k = keyOf(el);
        delete shared[k]; delete mine[k]; saveMine();
        post({action: 'unmark', doi: k}); paint();
    }

    fetch(SHEET + '?action=getAll').then(r => r.json()).then(res => {
        (res.data || []).forEach(x => { const k = String(x.doi || '').trim(); if (k) shared[k] = {by: x.by, at: x.at}; });
        // the sheet stores DOIs as typed; match case-insensitively
        const lower = {}; Object.keys(shared).forEach(k => lower[k.toLowerCase()] = shared[k]);
        document.querySelectorAll('.paper').forEach(el => { const k = keyOf(el); if (!shared[k] && lower[k.toLowerCase()]) shared[k] = lower[k.toLowerCase()]; });
        document.getElementById('syncStatus').textContent = 'Synced with the shared record';
        paint();
    }).catch(() => {
        document.getElementById('syncStatus').textContent = 'Offline: shared record unreachable, showing your own marks only';
        paint();
    });

    function initUser() {
        const sel = document.getElementById('userName');
        const saved = localStorage.getItem('eea_username');
        if (saved) sel.value = saved;
        sel.addEventListener('change', () => localStorage.setItem('eea_username', sel.value));
    }

    // Each person's own library search, with {TITLE} where the title goes.
    // WorldCat is the default because it works for everyone; FIU is one click away.
    const LIBKEY = 'eea_library_url';
    const LIB_FIU = 'https://fiu-flvc.primo.exlibrisgroup.com/discovery/search?query=any,contains,{TITLE}&tab=Everything&search_scope=MyInst_and_CI&vid=01FALSC_FIU%3AFIU&offset=0';
    const LIB_WORLDCAT = 'https://search.worldcat.org/search?q={TITLE}';
    function libTemplate() { return localStorage.getItem(LIBKEY) || LIB_WORLDCAT; }
    function applyLibrary() {
        const tpl = libTemplate();
        document.querySelectorAll('a.alt-fiu').forEach(a => {
            const p = a.closest('.paper');
            a.href = tpl.replace('{TITLE}', encodeURIComponent((p && p.dataset.title) || ''));
            a.textContent = tpl === LIB_FIU ? 'FIU OneSearch' : tpl === LIB_WORLDCAT ? 'WorldCat' : 'My library';
        });
        document.getElementById('libUrl').value = tpl;
    }
    function saveLibrary() {
        const v = document.getElementById('libUrl').value.trim();
        if (v) localStorage.setItem(LIBKEY, v); else localStorage.removeItem(LIBKEY);
        applyLibrary();
    }
    function presetLibrary(which) { localStorage.setItem(LIBKEY, which === 'fiu' ? LIB_FIU : LIB_WORLDCAT); applyLibrary(); }

    initUser();
    applyLibrary();
    paint();
"""

HUB = "https://simondedman.github.io/elasmo_analyses/remaining_downloads.html"
OUTSTANDING = {"needs_library", "needs_pdf", "sr_sync_new"}   # same set as the hub and the dashboard
OA_OPEN = {"gold", "green", "hybrid", "bronze"}


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def hub_journal(p):
    """The journal string the hub filters on (docs/remaining_downloads.html)."""
    return (p.get("journal_clean") or p.get("journal") or "Unknown").strip()


def paper_card(p, i):
    lid = p.get("literature_id")
    doi = str(p.get("doi") or "").strip()
    key = doi or f"lid:{lid}"
    raw_title = (p.get("title") or "").strip().rstrip(".").strip()
    enc = urllib.parse.quote(raw_title, safe="")
    first = re.split(r"[,;]", p.get("authors") or "")[0].strip()
    google = "https://www.google.com/search?q=" + urllib.parse.quote(f'"{raw_title}" filetype:pdf', safe="")
    scholar = f"https://scholar.google.com/scholar?q={enc}"
    jstor = f"https://www.jstor.org/action/doBasicSearch?Query={enc}&so=rel"
    bhl = "https://www.biodiversitylibrary.org/search?searchTerm=" + urllib.parse.quote(f"{raw_title} {first}".strip(), safe="")
    oa = (p.get("oa_status") or "").lower()
    buttons = []
    if doi:
        if oa in OA_OPEN and p.get("oa_url"):
            buttons.append(f'<a href="{esc(p["oa_url"])}" class="url-link" target="_blank">Open-access copy</a>')
            buttons.append(f'<a href="https://doi.org/{esc(doi)}" class="alt-link alt-jstor" target="_blank">Publisher page (DOI)</a>')
        else:
            buttons.append(f'<a href="https://doi.org/{esc(doi)}" class="url-link" target="_blank">Publisher page (DOI)</a>')
            buttons.append(f'<a href="{jstor}" class="alt-link alt-jstor" target="_blank">JSTOR</a>')
    else:
        buttons.append(f'<a href="{scholar}" class="url-link" target="_blank">Google Scholar</a>')
        buttons.append(f'<a href="{google}" class="alt-link alt-google" target="_blank">Google (PDF)</a>')
        buttons.append(f'<a href="{bhl}" class="alt-link alt-bhl" target="_blank">BHL</a>')
        buttons.append(f'<a href="{jstor}" class="alt-link alt-jstor" target="_blank">JSTOR</a>')
    buttons.append('<a href="#" class="alt-link alt-fiu" target="_blank">WorldCat</a>')
    if doi:
        buttons.append(f'<a href="{scholar}" class="alt-link alt-schol" target="_blank">Scholar</a>')
    badge = f'<span class="oa-badge">flagged open access</span>' if doi and oa in OA_OPEN else ""
    cite = esc(p.get("findspot_raw") or "")
    return (f'<div class="paper" id="paper-{lid}" data-key="{esc(key)}" data-title="{esc(raw_title)}">'
            f'<span class="paper-number">{i}</span><span class="paper-id">ID {lid}</span>'
            f'{f"<span class=doi>{esc(doi)}</span>" if doi else ""}{badge}'
            f'<div class="title">{esc(raw_title)}</div><div class="authors">{esc(p.get("authors"))}</div>'
            f'<div class="year">Year: {esc(p.get("year"))}</div>'
            f'{f"<div class=citation>{cite}</div>" if cite else ""}'
            f'{"".join(buttons)}'
            f'<div class="outcome"><button class="got" onclick="got(this)">Got it</button>'
            f'<button class="undo" style="display:none" onclick="undo(this)">Undo</button>'
            f'<button class="cant" onclick="cant(this)">Can\'t get it</button><span class="who"></span></div></div>')


def anchor(name):
    return "j-" + sanitize(name)[:60]


def build_page(heading, subtitle, papers, kind):
    """kind: 'doi' (grouped by journal within a publisher) or 'nodoi'."""
    byj = defaultdict(list)
    for p in papers:
        byj[clean_journal_name(p)].append(p)
    journals = sorted(byj.items(), key=lambda kv: kv[0].lower())
    n = len(papers)
    toc = ""
    if len(journals) > 1:
        toc = '<div class="toc"><strong>Journals on this page:</strong><br>' + "".join(
            f'<a href="#{anchor(j)}">{esc(j)} ({len(ps)})</a>' for j, ps in journals) + "</div>"
    routes = ("the <strong>Publisher page (DOI)</strong> first; if your login doesn't reach it, try JSTOR, "
              "then your library (WorldCat by default; set your own below), then Scholar."
              if kind == "doi" else
              "<strong>Google Scholar</strong> first (look for an [PDF] link on the right), then Google restricted "
              "to PDFs, then BHL for older and taxonomic work, then JSTOR and your library. Where there is a "
              "citation line under the title, it gives the volume and pages as Shark-References records them.")
    head = f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Download helper: {esc(heading)}</title><style>{CSS}{CSS_EXTRA}</style></head><body>
<p class="back"><a href="index.html">&larr; All download helpers</a> &nbsp;|&nbsp; <a href="{HUB}">Downloading hub</a></p>
<h1>Download helper: {esc(heading)}</h1>
<div class="stats">{subtitle}<br><strong>{n}</strong> papers across {len(journals)} journal(s). Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}; papers filed since then still appear until the next rebuild.</div>
<div class="instructions"><h3>How to use this page</h3><ol>
<li>Pick your name under <strong>You</strong> and, if you like, set your own library's search link.</li>
<li>For each paper try {routes}</li>
<li>If you get the PDF, save it and click <strong>Got it</strong>. That greys it out for everyone, here and on the downloading hub. Clicking a search button records nothing, so a dead end costs nobody anything.</li>
<li>If you can't get it, click <strong>Can't get it</strong>. That only marks it on your own browser, so you don't try it twice; someone with different access may still succeed.</li>
<li>Put the PDFs in your named folder on Simon's NAS. Any filename is fine. No NAS link yet? Email Simon and he'll send one.</li>
</ol></div>
<div class="controls"><label><strong>You:</strong> <select id="userName">{USER_OPTIONS}</select></label>
&nbsp;<span id="syncStatus" style="color:#7f8c8d;font-size:0.85em;">Connecting to the shared record…</span>
<div style="margin-top:8px;font-size:0.85em;"><strong>Library link:</strong>
<input id="libUrl" style="width:min(560px,70%);font-size:0.85em;padding:3px 6px;" title="Your library's search URL, with {{TITLE}} where the paper title goes.">
<button onclick="saveLibrary()">Save</button> <button onclick="presetLibrary('worldcat')">WorldCat</button> <button onclick="presetLibrary('fiu')">FIU</button>
<br><em>Paste your own library's search URL with <code>{{TITLE}}</code> where the title goes; this browser remembers it.</em></div></div>
<div class="progress">Got: <span id="count">0</span> / {n} &nbsp;·&nbsp; Can't get (you): <span id="cantcount">0</span>
<label class="hidebar"><input type="checkbox" id="hideDone" onchange="applyHide()"> hide papers already got</label></div>
{toc}<div id="papers">"""
    parts = [head]
    i = 0
    for jname, ps in journals:
        parts.append(f'<div class="journal-header" id="{anchor(jname)}">{esc(jname)} &nbsp;({len(ps)})</div>')
        for p in sorted(ps, key=lambda x: str(x.get("year", ""))):
            i += 1
            parts.append(paper_card(p, i))
    parts.append(f"</div><script>{JS}</script></body></html>")
    return "".join(parts)


def chunk_journals(groups, target=300):
    """Pool small journals alphabetically into pages of about `target` papers,
    never splitting a journal across two pages."""
    pages, cur = [], []
    for name, ps in sorted(groups.items(), key=lambda kv: kv[0].lower()):
        if cur and sum(len(x[1]) for x in cur) + len(ps) > target:
            pages.append(cur)
            cur = []
        cur.append((name, ps))
    if cur:
        pages.append(cur)
    return pages


def main():
    d = json.load(open(QUEUE))
    rows = [p for p in d if p.get("last_status") in OUTSTANDING and p.get("triage") != "conference_abstract"]
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):   # rebuilt from scratch: a stale page lists papers already filed
        old.unlink()
    helper_map = {"journal": {}, "publisher": {}}
    index_doi, index_nodoi = [], []

    def note(p, url):
        helper_map["journal"].setdefault(hub_journal(p), url)

    # ---- DOI rows: one page per publisher -------------------------------
    doi_rows = [p for p in rows if str(p.get("doi") or "").strip()]
    bypub = defaultdict(list)
    for p in doi_rows:
        bypub[resolve_publisher(p)].append(p)
    THRESHOLD = 15  # publishers below this share one "smaller publishers" page
    small = [p for k, v in bypub.items() if len(v) < THRESHOLD for p in v]
    for pub, papers in sorted(bypub.items(), key=lambda kv: -len(kv[1])):
        if len(papers) < THRESHOLD:
            continue
        fn = f"{sanitize(pub)}.html"
        n_oa = sum((p.get("oa_status") or "").lower() in OA_OPEN for p in papers)
        (OUT / fn).write_text(build_page(pub, f"<strong>Publisher:</strong> {esc(pub)}. Papers with a DOI; "
                                         f"{n_oa} are flagged open access but our scripts failed to fetch them.",
                                         papers, "doi"), encoding="utf-8")
        index_doi.append((pub, len(papers), fn))
        for p in papers:
            note(p, f"{fn}#{anchor(clean_journal_name(p))}")
            helper_map["publisher"].setdefault((p.get("publisher") or "").strip() or pub, fn)
    if small:
        fn = "smaller_publishers.html"
        (OUT / fn).write_text(build_page("Smaller publishers", f"Publishers with fewer than {THRESHOLD} papers each.",
                                         small, "doi"), encoding="utf-8")
        index_doi.append((f"Smaller publishers (fewer than {THRESHOLD} each)", len(small), fn))
        for p in small:
            note(p, f"{fn}#{anchor(clean_journal_name(p))}")
            helper_map["publisher"].setdefault((p.get("publisher") or "").strip() or resolve_publisher(p), fn)

    # ---- no-DOI rows: one page per big journal, the rest pooled A-Z -----
    nodoi = [p for p in rows if not str(p.get("doi") or "").strip()]
    byj = defaultdict(list)
    for p in nodoi:
        byj[clean_journal_name(p)].append(p)
    OWN = 20  # journals with at least this many papers get a page of their own
    for j, papers in sorted(byj.items(), key=lambda kv: -len(kv[1])):
        if len(papers) < OWN:
            continue
        fn = f"nodoi_{sanitize(j)[:70]}.html"
        (OUT / fn).write_text(build_page(j, "Papers with no DOI in this journal.", papers, "nodoi"), encoding="utf-8")
        index_nodoi.append((j, len(papers), fn))
        for p in papers:
            note(p, fn)
    rest = {j: ps for j, ps in byj.items() if len(ps) < OWN}
    for k, group in enumerate(chunk_journals(rest), 1):
        fn = f"nodoi_other_{k:02d}.html"
        span = f"{group[0][0][:28]} … {group[-1][0][:28]}"
        papers = [p for _, ps in group for p in ps]
        (OUT / fn).write_text(build_page(f"Other journals, {span}",
                                         f"Papers with no DOI, from journals with fewer than {OWN} such papers each.",
                                         papers, "nodoi"), encoding="utf-8")
        index_nodoi.append((f"Other journals: {span}", len(papers), fn))
        for p in papers:
            note(p, f"{fn}#{anchor(clean_journal_name(p))}")

    # The hub reads this to offer "Open the download helper" for its current filter.
    (OUT / "helper_map.json").write_text(json.dumps(helper_map, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def lis(items):
        return "\n".join(f'<li><a href="{fn}">{esc(name)}</a>: {n} papers</li>' for name, n, fn in items)
    n_doi, n_nodoi = sum(x[1] for x in index_doi), sum(x[1] for x in index_nodoi)
    (OUT / "index.html").write_text(f"""<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Download helpers</title><style>{CSS}{CSS_EXTRA}</style></head><body>
<p class="back"><a href="{HUB}">&larr; Downloading hub</a></p>
<h1>Download helpers</h1>
<div class="stats">Every paper still to get, {n_doi + n_nodoi:,} in all, laid out for working through: one card per paper with
the right search buttons, and a <strong>Got it</strong> button that tells the team it is done. The <a href="{HUB}">hub</a> tracks
progress across the whole list; these pages are for doing the downloading.<br>
Conference abstracts are left out (the abstracts project covers them).<br>
<strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<div class="instructions"><h3>Where to start</h3><ol>
<li><strong>Papers with a DOI</strong> ({n_doi:,}): pick a publisher your institution subscribes to.</li>
<li><strong>Papers without a DOI</strong> ({n_nodoi:,}): pick a journal you know, or one in your language or region.
These need searching rather than a login, and many turn up on Scholar, BHL, or a society website.</li>
<li>Save the PDFs to your named folder on Simon's NAS (any filename), and click <strong>Got it</strong> on each.</li>
</ol></div>
<h2>Papers with a DOI, by publisher</h2><ul style="font-size:1.05em;line-height:1.8">{lis(index_doi)}</ul>
<h2>Papers without a DOI, by journal</h2><ul style="font-size:1.05em;line-height:1.8">{lis(index_nodoi)}</ul>
</body></html>""", encoding="utf-8")
    print(f"DOI rows {n_doi:,} on {len(index_doi)} pages; no-DOI rows {n_nodoi:,} on {len(index_nodoi)} pages; "
          f"outstanding non-abstract rows {len(rows):,}")
    print(f"Index: {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
