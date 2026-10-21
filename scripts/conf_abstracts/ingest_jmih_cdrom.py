"""Ingest a JMIH meeting CD-ROM (2003 Manaus, 2004 Norman) into the abstracts DB.

Carylanne Maier (AES) copied both CDs whole and delivered them on 2026-10-21.
Until then JMIH 2003 and 2004 were held only as phone-scanned books too
degraded to parse (0 and 1 records). Each CD carries one born-digital PDF per
abstract, so this is the cleanest source we have for either year:

  [*] SURNAME, GIVEN; SURNAME, GIVEN ...      authors, capitals, ';'-separated
  (ABC, DE) Affiliation; (FG) Affiliation     coded by the authors' initials
                                              (one uncoded affiliation = all)
  Title

  Body ...

The CDs differ only in their index pages, which supply what the PDFs lack:
  2003: area/*.htm lists every abstract under a subject area ("Behavior",
        split into Fish and Herps) or a society symposium ("AES Sawfish").
        pdf/ and search/Pdf/ hold the same files under different names, so
        abstracts are taken once each by content hash.
  2004: abstract/jointMeeting.js holds the CD search's title, author, and
        keyword arrays; the index pages group abstracts only by author letter.
Neither CD records the day, time, or presentation type.

The leading '*' is kept in raw_author_string only: the CDs never say what it
marks (in later JMIH books it flags a student presenter).

Usage:
  ingest_jmih_cdrom.py --year 2003 [--dry-run] [--report OUT.json]
"""
import argparse
import hashlib
import html
import json
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import lexicon, load, names, tag  # noqa: E402

_WS = re.compile(r"\s+")
# Affiliation code: "(CRA, JAG)" at the start of an affiliation.
_CODE = re.compile(r"\(([A-Z]{1,5}(?:\s*,\s*[A-Z]{1,5})*)\)\s*")


def _clean(s):
    return _WS.sub(" ", (s or "").replace("\xa0", " ")).strip()


def pdf_text(path):
    # -layout keeps the blank line between title and body; plain mode runs them together.
    return subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
                          capture_output=True, text=True, check=True).stdout


def _upperish(line):
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) > 0.85


_AFFIL_WORD = re.compile(
    r"\b(Univ|Dep(t|artment)|Inst|Museum|Laborat|Lab\b|Cent(er|re)|College|School|Division|"
    r"Station|Survey|Program|Service|Fisheries|Society|Aquarium|Zoo|Foundation|Inc\b|Ltd|"
    r"Facult|Escola|Universidad|Universidade|Universit|Instituto|Museo|Museu|Departamento|"
    r"Centro|Unidad|Research)", re.I)


def _author_line(line):
    """Capitals in most of the CD; a few 2004 entries are typed in mixed case
    ('Dean, Mason N.; *Schaefer, Justin T.'), so fall back to 'no affiliation
    signs': no code bracket, no digit, no institution word."""
    if _upperish(line):
        return True
    if re.fullmatch(r"(?:[A-Z]\.?\s*){1,4}[,;.]?", line.strip()):
        return True       # a wrapped list's last initials ('VERDI,' / 'A.')
    l = line.strip()
    return bool(l) and not l.startswith("(") and not re.search(r"\d", l) \
        and not _AFFIL_WORD.search(l) and ("," in l or ";" in l)


def parse_abstract(text):
    """One abstract PDF's text -> raw parts. Raises ValueError when the layout
    is not the CD's (no capitalised author block, no title)."""
    lines = [_clean(l) for l in text.replace("\f", "\n").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    auth = []
    while lines and lines[0].strip() and _author_line(lines[0]):
        auth.append(lines.pop(0).strip())
    if not auth:
        raise ValueError("no capitalised author block")
    affil = []
    while lines and lines[0].strip():
        affil.append(lines.pop(0).strip())
    paras, cur = [], []
    for l in lines:
        if l.strip():
            cur.append(l.strip())
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    if not paras:
        raise ValueError("no title")
    authors_raw, affil_raw = " ".join(auth), _clean(" ".join(affil))
    # A capitalised author line can run straight on into the affiliation
    # ("DEYNAT, PASCAL P. Muséum national d'Histoire Naturelle, ..."): cut at
    # the first mixed-case word that follows a full stop.
    m = re.search(r"(?<=\.)\s+(?=[A-Z][a-zà-ÿ])", authors_raw)
    if m and _upperish(authors_raw[:m.start()]):
        authors_raw, affil_raw = authors_raw[:m.start()], _clean(authors_raw[m.end():] + " " + affil_raw)
    # ... or with no full stop ("FERNANDES, RONALDO Departamento de Vertebrados",
    # "HERNANDEZ DE S. M. CENTRO DE INVESTIGACIÓN"): cut at the institution word.
    m = _AFFIL_WORD.search(authors_raw)
    if m and "," in authors_raw[:m.start()]:
        authors_raw, affil_raw = authors_raw[:m.start()].strip(" ,;"), _clean(authors_raw[m.start():] + " " + affil_raw)
    # Hyphenated line breaks inside words ("anti-\npredator") are kept as typed.
    return dict(authors_raw=authors_raw, affil_raw=affil_raw, layout="standard",
                title=_clean(paras[0]), body=_clean("\n\n".join(paras[1:])) or None)


def _paras(text):
    paras, cur = [], []
    for l in text.replace("\f", "\n").splitlines():
        l = _clean(l)
        if l:
            cur.append(l)
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras


def parse_title_first(text):
    """The other 2003 layout (38 PDFs, mostly from Brazilian authors): title,
    then 'First Last and First Last' in mixed case with superscript affiliation
    numbers, then the affiliation, then the body. The author split here is a
    heuristic, so these records are marked needs_review."""
    paras = _paras(text)
    if len(paras) < 3:
        raise ValueError("title-first layout with fewer than 3 paragraphs")
    title, rest = paras[0], paras[1:]
    segs = [x.strip() for x in rest[0].split(",")]
    names_, affil = [], []
    for k, seg in enumerate(segs):
        if _AFFIL_WORD.search(seg) or re.search(r"\d{2,}|@", seg):
            affil = segs[k:]
            break
        names_.append(seg)
    authors_raw = ", ".join(names_)
    affil_parts = [", ".join(affil)] if affil else []
    body = []
    for p in rest[1:]:
        if not body and len(p.split()) < 40:
            affil_parts.append(p)
        else:
            body.append(p)
    return dict(authors_raw=authors_raw, affil_raw=_clean(" ".join(affil_parts)),
                layout="title_first", title=_clean(title), body=_clean("\n\n".join(body)) or None)


def _toks(s):
    return set(re.findall(r"[a-zà-ÿ]{3,}", (s or "").lower()))


def _split_mixed(raw):
    """'Luciana Lugli¹ and Flora Acuña Juncá²' -> ['Luciana Lugli', 'Flora Acuña Juncá']."""
    raw = re.sub(r"[\d¹²³⁴⁵⁶⁷⁸⁹⁰*]+", "", raw)
    return [p.strip(" .") for p in re.split(r",|\band\b|&", raw, flags=re.I) if p.strip(" .")]


def _initials(given, surname):
    g = [w[0] for w in re.split(r"[\s.\-]+", given) if w and w[0].isalpha()]
    s = [w[0] for w in re.split(r"[\s\-]+", surname) if w and w[0].isalpha()]
    return g, s


_SUFFIX_TOK = re.compile(r"^(Jr|Sr|II|III|IV)\.?$", re.I)


def _surname_first_parts(body):
    """'SURNAME, GIVEN; SURNAME, GIVEN' as typed, including the CD's variants:
    ' & ' or ' AND ' before the last name, comma-only lists
    ('DILLMAN, CASEY B., WOOD, ROBERT M.'), and no separator at all
    ('SMITH, CHAD C. SARGENT, R. CRAIG')."""
    body = re.sub(r"\s*\*\s*", " ", body.replace(":", ";")).strip()
    if ";" in body:
        # Semicolons separate people, so each chunk is one name even when it
        # carries a stray comma before the initials ('CRAMPTON, WILLIAM, G. R.').
        body = re.sub(r"\s+(?:AND|and|&)\s+", "; ", body)
        out = []
        for chunk in [c.strip() for c in body.split(";") if c.strip()]:
            toks = [t.strip() for t in chunk.split(",") if t.strip()]
            sfx = [t for t in toks if _SUFFIX_TOK.match(t)]
            rest = [t for t in toks if not _SUFFIX_TOK.match(t)]
            if len(rest) >= 4 and len(rest) % 2 == 0:
                # two people in one chunk ('EDWARDS, THEA M., GUILLETTE, LOUIS J.')
                out += [f"{rest[k]}, {rest[k + 1]}" for k in range(0, len(rest), 2)]
            elif len(rest) >= 2:
                out.append(", ".join([rest[0], " ".join(rest[1:])] + sfx[:1]))
            else:
                out.append(" ".join(rest + sfx[:1]))
        return out
    body = re.sub(r"\s+(?:AND|and|&)\s+", "; ", body)
    body = re.sub(r"(?<=[A-Z]\.)\s+(?=[A-Z][A-Z'\-]{2,},)", "; ", body)
    parts = []
    for chunk in [c.strip() for c in body.split(";") if c.strip()]:
        toks = [t.strip() for t in chunk.split(",") if t.strip()]
        sfx = [t for t in toks if _SUFFIX_TOK.match(t)]
        if sfx and len(toks) <= 3:
            # One name with a suffix in any position: 'DODD, C. KENNETH, JR.',
            # 'POMBAL, Jr., J.P.', 'BARTON C. MARCY, JR.' (given-name first).
            rest = [t for t in toks if not _SUFFIX_TOK.match(t)]
            parts.append(", ".join(rest + sfx[:1]) if len(rest) == 2 else
                         (rest[0] + " " + sfx[0] if rest else chunk))
            continue
        if len(toks) <= 2:
            parts.append(chunk)
            continue
        i = 0
        while i < len(toks):
            name = toks[i] + (", " + toks[i + 1] if i + 1 < len(toks) else "")
            i += 2
            if i < len(toks) and _SUFFIX_TOK.match(toks[i]):
                name += ", " + toks[i]; i += 1
            parts.append(name)
    return parts


def split_authors(raw, layout="standard"):
    """'* AADLAND, CHRISTOPHER R.; BRAUN, CHRISTOPHER B.' -> author dicts."""
    body = raw.lstrip("* ").strip()
    out = []
    if layout == "title_first":
        for i, name in enumerate(_split_mixed(body), 1):
            bits = name.split()
            out.append(dict(full_name=names._capital_case(name) if name.isupper() else name,
                            position=i, is_presenter=0, presenter_inferred=0,
                            affiliation=None, affiliation_country=None, raw_author_string=raw,
                            _given=" ".join(bits[:-1]), _surname=bits[-1] if bits else ""))
        return out
    for i, part in enumerate(_surname_first_parts(body), 1):
        part = part.lstrip("* ")
        surname, _, given = part.partition(",")
        out.append(dict(full_name=names.normalise(part), position=i, is_presenter=0,
                        presenter_inferred=0, affiliation=None, affiliation_country=None,
                        raw_author_string=raw, _given=given.strip(), _surname=surname.strip()))
    return out


def assign_affiliations(authors, affil_raw):
    """Fill author['affiliation'] from the coded affiliation block. Returns the
    number of authors left without one."""
    if not affil_raw:
        return len(authors)
    pieces = list(_CODE.finditer(affil_raw))
    if not pieces:
        for a in authors:
            a["affiliation"] = affil_raw
        return 0
    for k, m in enumerate(pieces):
        end = pieces[k + 1].start() if k + 1 < len(pieces) else len(affil_raw)
        text = affil_raw[m.end():end].strip().rstrip(";").strip()
        for code in [c.strip() for c in m.group(1).split(",")]:
            hits = []
            for a in authors:
                g, s = _initials(a["_given"], a["_surname"])
                forms = {"".join(g + s), "".join(g[:1] + s), "".join(g + s[-1:]),
                         "".join(g[:1] + s[-1:]), "".join(g + s[:1])}
                if code in forms:
                    hits.append(a)
            if len(hits) == 1:
                a = hits[0]
                a["affiliation"] = f"{a['affiliation']}; {text}" if a["affiliation"] else text
    return sum(1 for a in authors if not a["affiliation"])


# ---- 2003: subject areas and symposia from the CD's area pages -------------

class _Stream(HTMLParser):
    """Ordered stream of ('text', s) and ('pdf', href) from an area page."""
    def __init__(self):
        super().__init__(); self.items = []; self.href = None; self.buf = []

    def handle_starttag(self, t, a):
        if t == "a":
            self.href = dict(a).get("href"); self.buf = []

    def handle_endtag(self, t):
        if t == "a":
            if self.href and self.href.lower().endswith(".pdf"):
                self.items.append(("pdf", self.href, _clean(" ".join(self.buf))))
            self.href = None

    def handle_data(self, d):
        d = _clean(d)
        if not d:
            return
        if self.href:
            self.buf.append(d)
        elif not d.startswith("<!--"):
            self.items.append(("text", d, None))


_NAV = {"2003 JOINT MEETING of ICHTHYOLOGISTS and HERPETOLOGISTS", "Index of Area",
        "back", "home", "instal Adobe Acrobat", "."}


def sessions_2003(cd):
    """{pdf filename (lower): (area, sub, symposium_society, link title)} in CD order."""
    # Sub-headings are Fish/Herps on subject pages and the symposium names
    # listed on simp2a.htm; anything else is a stray text node (a link label
    # split across tags, "l", "Diet of Mugil curema") and must not relabel the
    # abstracts after it.
    simp = (cd / "area" / "simp2a.htm").read_text(encoding="latin-1")
    symposia = {_clean(html.unescape(re.sub(r"<[^>]+>", " ", lab)))
                for lab in re.findall(r'<a[^>]*href="2a[a-z]\.htm"[^>]*>(.*?)</a>', simp, re.S | re.I)}
    out = {}
    for page in sorted((cd / "area").glob("2*.htm")):
        s = _Stream(); s.feed(page.read_text(encoding="latin-1"))
        texts = [x for x in s.items if x[0] == "text" and x[1] not in _NAV]
        if not texts:
            continue
        area, sub, soc = texts[0][1], None, None
        for kind, val, title in s.items:
            if kind == "text":
                if val in _NAV or val == area:
                    continue
                if val not in ({"Fish", "Herps"} | (symposia if area == "Simposia" else set())):
                    continue
                sub = val
                if area == "Simposia":
                    head = val.split()[0]
                    soc = head if head in C.SOCIETIES else None
            elif kind == "pdf":
                key = Path(urllib.parse.unquote(val)).name.lower()
                out.setdefault(key, (area, sub, soc, title, page.name))
    return out


def _session_name(area, sub):
    if area == "Simposia":
        return f"Symposium: {sub}"
    return f"{area} ({sub})" if sub else area


# ---- 2004: titles, authors, keywords from the CD search's JS arrays --------

def js_2004(cd):
    t = (cd / "abstract" / "jointMeeting.js").read_text(encoding="latin-1")
    arr = lambda name: {int(i): v for i, v in re.findall(rf'^{name}\[(\d+)\]="(.*)";', t, re.M)}
    files, titles, authors = arr("files"), arr("titles"), arr("authors")
    kws = {}
    for i, _j, v in re.findall(r'^keywordArray\[(\d+)\]\[(\d+)\]="(.*)";', t, re.M):
        v = v.strip().rstrip(",").strip()
        if v and v.lower() != "z":
            kws.setdefault(int(i), []).append(re.sub(r"<[^>]+>", "", v).lower())
    out = {}
    for i, f in files.items():
        out[f.lower()] = dict(title=_clean(titles.get(i)), authors=_clean(authors.get(i)),
                              keywords="; ".join(kws.get(i, [])) or None, index=i)
    return out


def read_cd(year, cd):
    """All abstracts on the CD -> (records, coverage)."""
    cd = Path(cd)
    if year == 2003:
        files = sorted(list((cd / "pdf").glob("*.pdf")) + list((cd / "search" / "Pdf").glob("*.pdf")))
        files = [f for f in files if f.name.lower() != "abstracts2003.pdf"]   # the whole book
        meta = sessions_2003(cd)
    else:
        files = sorted((cd / "abstract").glob("*.pdf"))
        meta = js_2004(cd)
    seen, recs, cov = {}, [], dict(pdf_files=len(files), duplicate_content=0,
                                   parse_failed=[], no_body=0, affil_unassigned=0,
                                   not_on_index=0)
    for f in files:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        rel = str(f.relative_to(cd))
        if h in seen:
            cov["duplicate_content"] += 1
            # a copy listed on the index beats an unlisted one
            r = seen[h]
            if r["_session_key"] is None and f.name.lower() in meta:
                _apply_meta(r, year, meta[f.name.lower()], rel)
            continue
        m = meta.get(f.name.lower())
        index_title = (m[3] if year == 2003 else m["title"]) if m else None
        try:
            text = pdf_text(f)
        except subprocess.CalledProcessError as e:
            cov["parse_failed"].append(f"{rel}: {e}")
            continue
        try:
            p = parse_abstract(text)
        except ValueError:
            p = None
        # Title-first layout: what was read as the author block is the title.
        ta = _toks(p["authors_raw"]) if p else set()
        if p is None or (index_title and ta and len(ta & _toks(index_title)) / len(ta) >= 0.6):
            try:
                p = parse_title_first(text)
            except ValueError as e:
                cov["parse_failed"].append(f"{rel}: {e}")
                continue
            cov.setdefault("title_first_layout", []).append(rel)
        authors = split_authors(p["authors_raw"], p["layout"])
        cov["affil_unassigned"] += assign_affiliations(authors, p["affil_raw"])
        for a in authors:
            a.pop("_given"); a.pop("_surname")
        r = dict(title=p["title"], abstract_text=p["body"], keywords=None,
                 presentation_type=None, award=None, session_name=None,
                 session_datetime=None, program_number=None, location=None,
                 societies_explicit=[], authors=authors, confidence=1.0,
                 needs_review=0 if p["body"] and p["layout"] == "standard" else 1,
                 source_page=None, source_file=rel, _session_key=None,
                 _pdf_title=p["title"], _layout=p["layout"])
        if not p["body"]:
            cov["no_body"] += 1
        if m:
            _apply_meta(r, year, m, rel)
        seen[h] = r
        recs.append(r)
    for r in recs:
        if r["_session_key"] is None:
            cov["not_on_index"] += 1
            if year == 2003:
                r["session_name"] = "Not listed on the CD's area pages"
    return recs, cov


def _apply_meta(r, year, m, rel):
    r["source_file"] = rel
    if year == 2003:
        area, sub, soc, link_title, page = m
        r["session_name"] = _session_name(area, sub)
        r["societies_explicit"] = [soc] if soc else []
        r["_session_key"] = (area, sub)
        if link_title and len(link_title) > 10:
            r["title"] = link_title           # the CD's own index title
    else:
        # The CD search's titles are URL-encoded capitals with HTML tags
        # ('BULL+SHARKS+(<I>CARCHARHINUS...'); the PDF's own title is clean, so
        # the index title is used only when the PDF gave none.
        r["keywords"] = m["keywords"]
        r["_session_key"] = m["index"]
        if not r["title"] and m["title"]:
            r["title"] = _clean(re.sub(r"<[^>]+>", "", urllib.parse.unquote_plus(m["title"])))


def _elasmo(rec, meeting, year):
    rec = tag.resolve(rec, meeting, year)
    if not rec["is_elasmo"] and lexicon.is_elasmo_text(rec["title"], rec["abstract_text"] or ""):
        rec["is_elasmo"], rec["elasmo_basis"] = 1, "content"
    return rec


def ensure_columns(con):
    have = {r[1] for r in con.execute("PRAGMA table_info(abstracts)")}
    if "source_file" not in have:
        con.execute("ALTER TABLE abstracts ADD COLUMN source_file TEXT")
    con.commit()


def ingest(con, year, meeting="JMIH", dry_run=False):
    cd, city = C.CDROM_SOURCES[(meeting, year)]
    recs, cov = read_cd(year, cd)
    for r in recs:
        _elasmo(r, meeting, year)
    if dry_run:
        return None, recs, cov
    ensure_columns(con)
    mid = load.upsert_meeting(con, dict(
        meeting=meeting, year=year, name=f"Joint Meeting of Ichthyologists and Herpetologists {year} (CD-ROM)",
        location=city, dates=None, source_pdf=str(cd), doc_type="abstract_book",
        page_count=None, is_ocr=0, parse_status="ok"))
    n = 0
    for r in recs:
        rec = {k: v for k, v in r.items() if not k.startswith("_") and k != "source_file"}
        aid = load.insert_abstract(con, mid, rec)
        if aid is None:
            cov.setdefault("title_duplicates", []).append(r["source_file"])
            continue
        con.execute("UPDATE abstracts SET source_file=? WHERE abstract_id=?", (r["source_file"], aid))
        r["_abstract_id"] = aid
        n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    cov["inserted"] = n
    return mid, recs, cov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="write the parsed records + coverage as JSON")
    a = ap.parse_args()
    con = sqlite3.connect(str(C.DB_PATH))
    mid, recs, cov = ingest(con, a.year, dry_run=a.dry_run)
    n_el = sum(r["is_elasmo"] for r in recs)
    print(f"JMIH {a.year} CD: {len(recs)} distinct abstracts from {cov['pdf_files']} PDFs "
          f"({cov['duplicate_content']} duplicate copies), {n_el} elasmo, "
          f"{cov['no_body']} without a body, {len(cov['parse_failed'])} unparsable, "
          f"{cov['not_on_index']} not on the CD index, {cov['affil_unassigned']} authors "
          f"without an affiliation")
    for f in cov["parse_failed"]:
        print("  PARSE FAILED", f)
    if a.report:
        Path(a.report).write_text(json.dumps(dict(coverage=cov, records=recs), indent=1,
                                             default=str, ensure_ascii=False))
    if a.dry_run:
        print("dry run - nothing written")
    else:
        print(f"  inserted {cov['inserted']} into meeting_id {mid}; "
              f"{len(cov.get('title_duplicates', []))} skipped as same-title duplicates")


if __name__ == "__main__":
    main()
