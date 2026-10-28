"""Ingest the online EBI proceedings (2015 Olinda, 2025 Palmas) into the abstracts DB.

Reads the pages fetch_ebi.py cached under
SharkPapers/Conferences/<year>/<year>_EBI_Anais_web/ and never touches the network.

  2015  resumos/R<num>-<n>.html, one per work (ISO-8859-1):
          "Área Temática: <area> (<b>Oral|Pôster</b>)"
          title in the first <b><font size=3>, authors in the next <font size=2>
          (presenter underlined, affiliation numbers in <SUP>), numbered
          affiliations in <em>, an e-mail line (NOT stored), the body, then
          "Palavras-chaves:". program_number is the file's <num>-<n>.
  2025  artigo/<id>.html, one per work: the page embeds the record as
          "key" => "value" pairs (titulo, resumo, modalidade, area_tematica,
          idioma) and lists every author with an institution in the "Autores"
          block. program_number is the Realize article id.

EBI is a general ichthyology meeting (chondrichthyans are 1.4-6.6% of a book,
Soares & Petean 2023), so is_elasmo comes from the content lexicon, per abstract;
lexicon.py carries the Portuguese names and the family stems these books use.
Text is kept verbatim in its own language; `language` records which ('pt' or
'en') and translations go in title_en / abstract_text_en (translate_abstracts.py).

Usage:
  ingest_ebi.py --year 2015|2025 [--dry-run] [--report OUT.json]
"""
import argparse
import html
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import lexicon, load, names, tag  # noqa: E402

_WS = re.compile(r"\s+")
# Only real tags: the 2015 CD leaves "<" unescaped in text ("p<0,05",
# "< 100 mm CT"), and a bare <[^>]+> ate everything up to the next ">" in 173
# of its 1,169 abstracts (MEASURED 2026-10-28).
_TAG = re.compile(r"</?[A-Za-z][^<>]*>|<!--.*?-->", re.S)
_STRAY = re.compile(r"(?<!<)/(?:i|b|u|em|sup|sub|font)>", re.I)   # "Characidium/i>"
_PHP_U = re.compile(r"\\u\{([0-9A-Fa-f]{1,6})\}")                    # PHP dump: \u{A0}
_PHP_X = re.compile(r"\\x([0-9A-Fa-f]{2})")                          # PHP dump: \x02
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


_BLOCK = re.compile(r"<(?:br|p|/p|div|/div|hr|tr|/tr|td|/td)\b[^>]*>", re.I)


def _clean(s):
    # Block tags break words, inline ones (<i>, <u>, <sup>, <font>) do not; the
    # CD puts a space inside every italic ("<i>R. micropus </i>,"), so a space
    # before closing punctuation or after an opening bracket is dropped.
    s = _STRAY.sub("", _TAG.sub("", _BLOCK.sub(" ", s or "")))
    s = html.unescape(html.unescape(s))           # 2025 titles are escaped twice (&amp;AMP;)
    s = _PHP_U.sub(lambda m: chr(int(m.group(1), 16)), s)
    # a control byte (\x02 in "ACARI\x02PÃO") stands for a lost character: a space
    s = _PHP_X.sub(lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) >= 32 else " ", s)
    s = _WS.sub(" ", s)
    s = re.sub(r"\s+([,.;:)\]])", r"\1", re.sub(r"([(\[])\s+", r"\1", s))
    return s.strip(" ,;")


def _type(raw):
    low = (raw or "").lower()
    if "oral" in low:
        return "talk"
    if "pôster" in low or "poster" in low or "banner" in low or "painel" in low:
        return "poster"
    return None


_PT_WORDS = re.compile(r"\b(?:de|da|do|das|dos|e|em|para|com|uma|um|que|na|no|foram|são|não)\b", re.I)
_EN_WORDS = re.compile(r"\b(?:the|of|and|in|to|for|with|was|were|from|this|that|are|is)\b", re.I)


def language(title, body):
    text = f"{title} {body}"
    pt, en = len(_PT_WORDS.findall(text)), len(_EN_WORDS.findall(text))
    return "en" if en > pt else "pt"


# --------------------------------------------------------------------- 2015
def parse_2015(path):
    # Windows-1252, not Latin-1: read as Latin-1, its en dashes and curly
    # quotes become C1 control characters (\x96, \x93) and drop out of titles
    raw = path.read_bytes().decode("cp1252", errors="replace")
    rec = dict(program_number=path.stem[1:].lstrip("0"), source_file=path.name)
    m = re.search(r"Área Temática:</b>(.*?)\(<b>(.*?)</b>\)", raw, re.S)
    rec["session_name"] = _clean(m.group(1)) if m else None
    rec["presentation_type"] = _type(m.group(2)) if m else None
    m = re.search(r"<b><font size=3>(.*?)</font>", raw, re.S)
    rec["title"] = _clean(m.group(1)) if m else ""
    # authors: everything from the end of the title to the first <em>
    m = re.search(r"</font><Br><font size=2></b>(.*?)</font>", raw, re.S | re.I)
    auth_html = m.group(1) if m else ""
    affs = {}
    m = re.search(r"<em>(.*?)</em>", raw, re.S)
    for line in re.split(r"<br\s*/?>", m.group(1) if m else "", flags=re.I):
        line = _clean(line)
        am = re.match(r"(\d+)\.\s*(.+)", line)
        if am:
            affs[am.group(1)] = am.group(2)
    authors, seen = [], set()
    for chunk in re.split(r"</SUP>\s*,", auth_html, flags=re.I):
        sup = re.findall(r"<SUP>([^<]*)", chunk, re.I)
        nums = re.findall(r"\d+", ",".join(sup))
        name = _clean(re.sub(r"<SUP>.*", "", chunk, flags=re.I | re.S))
        if not name or name.lower() in seen:
            continue                    # the CD lists some co-authors twice
        seen.add(name.lower())
        authors.append(dict(
            full_name=names.normalise(name), raw_author_string=name,
            is_presenter=int("<u>" in chunk.lower()),
            affiliation="; ".join(affs[n] for n in nums if n in affs) or None))
    rec["authors"] = authors
    m = re.search(r'<p align="justify">(.*?)<b>Palavras-chave', raw, re.S | re.I)
    body = m.group(1) if m else ""
    rec["abstract_text"] = _clean(_EMAIL.sub(" ", body))
    m = re.search(r"Palavras-chaves?:</b>(.*?)</font>", raw, re.S | re.I)
    rec["keywords"] = _clean(m.group(1)) if m else None
    return rec


# --------------------------------------------------------------------- 2025
def parse_2025(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    plain = _TAG.sub("", raw)
    def val(k):
        m = re.search(r'"%s"\s*=(?:>|&gt;)\s*"(.*?)"\s*\n' % k, plain, re.S)
        return _clean(m.group(1)) if m else None
    rec = dict(program_number=path.stem, source_file=path.name,
               title=val("titulo") or "",
               # authors' e-mail addresses are not republished (2 bodies carry one)
               abstract_text=_EMAIL.sub("[e-mail]", val("resumo") or "").strip(),
               session_name=val("area_tematica"), presentation_type=_type(val("modalidade")),
               _idioma=val("idioma"), _modalidade=val("modalidade"))
    kw = val("palavra_chave") or ""
    rec["keywords"] = kw if kw.strip(" ,") else None
    i = raw.find(">Autores<")
    block = raw[i:raw.find("Sugestão de citação", i)] if i >= 0 else ""
    # the submitting author is an "author-block" (<header>name</header>
    # <figure>institution</figure>), each co-author a "coauthor-block"
    # (name<br><small>institution</small>)
    pairs = re.findall(r"<header>(.*?)</header>\s*</a>\s*<figure>(.*?)</figure>", block, re.S)
    pairs += re.findall(r'class="coauthor-block[^"]*">(.*?)<br>\s*<small>(.*?)</small>', block, re.S)
    authors = []
    for n, inst in pairs:
        n, inst = _clean(n), _clean(inst)
        if inst.upper().startswith("OUTRA / MINHA INSTITUI"):
            inst = None                 # Realize's "my institution is not listed"
        authors.append(dict(full_name=names.normalise(n), raw_author_string=n, affiliation=inst))
    rec["authors"] = authors
    return rec


# --------------------------------------------------------------------- shared
def read_year(year):
    root = Path(C.EBI_SOURCES[("EBI", year)][0])
    files = sorted((root / ("resumos" if year == 2015 else "artigo")).glob("*.html"))
    cov = json.loads((root / "_coverage.json").read_text()) if (root / "_coverage.json").exists() else {}
    recs, failed = [], []
    for p in files:
        r = (parse_2015 if year == 2015 else parse_2025)(p)
        if not r["title"] or not r["abstract_text"]:
            failed.append(p.name)
            r["needs_review"] = 1
        recs.append(r)
    out = dict(listed=cov.get("listed"), fetch_complete=cov.get("complete"),
               fetch_failed=len(cov.get("failed", {})), files=len(files), parse_failed=failed,
               no_authors=sum(1 for r in recs if not r["authors"]),
               untyped=sum(1 for r in recs if not r["presentation_type"]))
    return recs, out


def finish(recs, year):
    for r in recs:
        # Titles stay as published (mostly capitals). The English casing
        # vocabulary mis-cases Portuguese ("Uma Abordagem", "são paulo" from
        # the body alone; 18 of 40 sampled titles differed and both were
        # wrong), so translate_abstracts.py re-cases them with the translation
        # and checks the result differs from the original in case only.
        # Realize's "idioma" says Português for every 2025 work, English ones
        # included, so the language is read from the text itself.
        r.pop("_idioma", None)
        r["language"] = language(r["title"], r["abstract_text"])
        r.pop("_modalidade", None)
        r = tag.resolve(r, "EBI", year)
        r["society"], r["society_basis"] = "SBI", "meeting"
        if lexicon.is_elasmo_text(r["title"], r["abstract_text"] or ""):
            r["is_elasmo"], r["elasmo_basis"] = 1, "content"
    return recs


def ensure_columns(con):
    have = {r[1] for r in con.execute("PRAGMA table_info(abstracts)")}
    for col in ("source_file", "language", "title_en", "abstract_text_en", "translation_by"):
        if col not in have:
            con.execute(f"ALTER TABLE abstracts ADD COLUMN {col} TEXT")
    con.commit()


def ingest(con, year, dry_run=False):
    folder, city = C.EBI_SOURCES[("EBI", year)]
    recs, cov = read_year(year)
    finish(recs, year)
    if dry_run:
        return None, recs, cov
    ensure_columns(con)
    ordinal = {2015: "XXI", 2025: "XXV"}[year]
    mid = load.upsert_meeting(con, dict(
        meeting="EBI", year=year, name=f"{ordinal} Encontro Brasileiro de Ictiologia (online proceedings)",
        location=city, dates=None, source_pdf=folder, doc_type="abstract_book",
        page_count=None, is_ocr=0, parse_status="ok"))
    n, dups = 0, []
    for r in recs:
        rec = {k: v for k, v in r.items() if not k.startswith("_")}
        aid = load.insert_abstract(con, mid, rec)
        if aid is None:
            dups.append(r["source_file"])
            continue
        con.execute("UPDATE abstracts SET source_file=?, language=? WHERE abstract_id=?",
                    (r["source_file"], r["language"], aid))
        n += 1
    con.execute("UPDATE meetings SET n_abstracts=(SELECT count(*) FROM abstracts WHERE meeting_id=?) "
                "WHERE meeting_id=?", (mid, mid))
    con.commit()
    cov["inserted"], cov["title_duplicates"] = n, dups
    return mid, recs, cov


def refresh(con, year):
    """Re-parse the cached pages and update this year's rows IN PLACE, keyed on
    source_file, so abstract ids (and translations keyed on them) survive a
    parser fix. Returns {source_file: changed fields}."""
    mid = con.execute("SELECT meeting_id FROM meetings WHERE meeting='EBI' AND year=?",
                      (year,)).fetchone()[0]
    recs, cov = read_year(year)
    finish(recs, year)
    rows = {f: (aid, t, b, k, el) for aid, f, t, b, k, el in con.execute(
        "SELECT abstract_id, source_file, title, abstract_text, keywords, is_elasmo "
        "FROM abstracts WHERE meeting_id=?", (mid,))}
    changed = {}
    for r in recs:
        aid, t, b, k, el = rows[r["source_file"]]
        # a stored title that differs only in case was re-cased on purpose
        # (translate_abstracts.py): keep it
        if t and re.sub(r"\s+", "", t).upper() == re.sub(r"\s+", "", r["title"]).upper():
            r["title"] = t
        diff = [n for n, old, new in (("title", t, r["title"]), ("abstract_text", b, r["abstract_text"]),
                                      ("keywords", k, r["keywords"]), ("is_elasmo", el, r["is_elasmo"]))
                if old != new]
        if not diff:
            continue
        changed[r["source_file"]] = dict(abstract_id=aid, fields=diff)
        con.execute("UPDATE abstracts SET title=?, abstract_text=?, keywords=?, length_words=?, "
                    "language=?, is_elasmo=?, elasmo_basis=? WHERE abstract_id=?",
                    (r["title"], r["abstract_text"], r["keywords"], len(r["abstract_text"].split()),
                     r["language"], r["is_elasmo"], r.get("elasmo_basis"), aid))
        con.execute("DELETE FROM authors WHERE abstract_id=?", (aid,))
        for i, a in enumerate(r["authors"], 1):
            con.execute("INSERT INTO authors (abstract_id, full_name, position, is_presenter, "
                        "presenter_inferred, affiliation, raw_author_string) VALUES (?,?,?,?,?,?,?)",
                        (aid, a["full_name"], i, int(a.get("is_presenter", 0)), 0,
                         a.get("affiliation"), a.get("raw_author_string")))
    con.commit()
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True, choices=[2015, 2025])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="write the parsed records + coverage as JSON")
    ap.add_argument("--refresh", action="store_true",
                    help="re-parse and update the already-ingested rows in place")
    a = ap.parse_args()
    con = sqlite3.connect(str(C.DB_PATH))
    if a.refresh:
        ch = refresh(con, a.year)
        from collections import Counter
        print(f"EBI {a.year} refresh: {len(ch)} rows updated; fields: "
              f"{dict(Counter(f for c in ch.values() for f in c['fields']))}")
        if a.report:
            Path(a.report).write_text(json.dumps(ch, indent=1))
        return
    mid, recs, cov = ingest(con, a.year, dry_run=a.dry_run)
    langs = {l: sum(r["language"] == l for r in recs) for l in ("pt", "en")}
    print(f"EBI {a.year}: {cov['files']} pages of {cov['listed']} listed "
          f"(fetch complete: {cov['fetch_complete']}, {cov['fetch_failed']} fetch failures), "
          f"{sum(r['is_elasmo'] for r in recs)} elasmo, languages {langs}, "
          f"{len(cov['parse_failed'])} without title or body, {cov['no_authors']} without authors, "
          f"{cov['untyped']} untyped")
    for f in cov["parse_failed"]:
        print("  PARSE FAILED", f)
    if a.report:
        Path(a.report).write_text(json.dumps(dict(coverage=cov, records=recs), indent=1,
                                             default=str, ensure_ascii=False))
    if a.dry_run:
        print("dry run - nothing written")
    else:
        print(f"  inserted {cov['inserted']} into meeting_id {mid}; "
              f"{len(cov['title_duplicates'])} skipped as same-title duplicates")
        for f in cov["title_duplicates"]:
            print("  DUPLICATE TITLE", f)


if __name__ == "__main__":
    main()
