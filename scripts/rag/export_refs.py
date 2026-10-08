#!/usr/bin/env python3
"""Reference export for the RAG page: BibTeX, RIS, CSV, JSON and five plain-text
citation styles, built from the enriched parquet. No retrieval dependencies."""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata

_YEAR_TAIL = re.compile(r"\s*\((\d{4}[a-z]?|n\.d\.)\)\s*$")
_INITIALS = re.compile(r"^(?:[A-Z]\.?-?){1,4}$")
_PARTICLES = {"de", "da", "di", "del", "della", "van", "von", "der", "den", "la", "le", "du", "dos", "das", "bin", "al", "el"}


def _clean(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "<na>") else s


def _initials(raw: str) -> str:
    """'S.' / 'SJ' / 'J.-P.' / 'John Paul' -> 'S.', 'S. J.', 'J.-P.', 'J. P.'."""
    raw = raw.strip()
    if not raw:
        return ""
    if _INITIALS.match(raw) and not raw.islower():
        letters = re.findall(r"[A-Z]", raw)
        if "-" in raw and len(letters) == 2:
            return f"{letters[0]}.-{letters[1]}."
        return " ".join(c + "." for c in letters)
    return " ".join(w[0].upper() + "." for w in re.split(r"[\s.]+", raw) if w and w[0].isalpha())


def _parse_one(a: str) -> tuple[str, str]:
    a = a.strip().strip(",;")
    if not a:
        return "", ""
    if "," in a:
        sur, _, rest = a.partition(",")
        return sur.strip(), _initials(rest)
    toks = a.split()
    if len(toks) > 1 and _INITIALS.match(toks[-1]) and toks[-1].isupper():
        return " ".join(toks[:-1]), _initials(toks[-1])      # "Smith J"
    if len(toks) > 1:                                         # "John Smith"
        k = len(toks) - 1
        while k > 1 and toks[k - 1].lower() in _PARTICLES:
            k -= 1
        return " ".join(toks[k:]), _initials(" ".join(toks[:k]))
    return a, ""


def parse_authors(s) -> list[tuple[str, str]]:
    """Parse an authors string into [(surname, initials)]. Handles
    'Surname, F. & Surname, F. (1998)', 'Surname, F.; Surname, F.' and
    'Smith J & Jones K'. A trailing '(year)' is dropped."""
    s = _clean(s)
    if not s:
        return []
    s = _YEAR_TAIL.sub("", s)
    parts = re.split(r"\s*(?:&|;|\band\b)\s*", s)
    if len(parts) == 1 and s.count(",") >= 1:
        chunks = [c.strip() for c in s.split(",") if c.strip()]
        if len(chunks) > 1 and all(re.search(r"\s[A-Z]{1,3}$", c) for c in chunks):   # "Smith J, Jones K"
            parts = chunks
    out = [_parse_one(p) for p in parts]
    return [(a, b) for a, b in out if a]


def _ascii(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_TITLE_SKIP = {"a", "an", "the", "on", "of", "in", "and", "for", "to", "at", "by"}


def bibtex_key(rec: dict, used: set[str]) -> str:
    au = rec["_authors"]
    sur = re.sub(r"[^A-Za-z0-9]", "", _ascii(au[0][0])) if au else "anon"
    words = [w for w in re.findall(r"[A-Za-z0-9]+", _ascii(rec["title"])) if w.lower() not in _TITLE_SKIP]
    key = f"{sur}{rec['year'] or 'nd'}{(words[0] if words else 'untitled').capitalize()}"
    base, n = key, 1
    while key in used:
        n += 1
        key = f"{base}{chr(96 + n) if n <= 27 else n}"
    used.add(key)
    return key


def to_records(rows: list[dict]) -> list[dict]:
    recs = []
    for r in rows:
        y = _clean(r.get("year"))
        try:
            y = str(int(float(y)))
        except ValueError:
            y = ""
        doi = _clean(r.get("doi"))
        doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
        rec = {"literature_id": _clean(r.get("literature_id")), "title": _clean(r.get("title")),
               "authors_raw": _clean(r.get("authors")), "year": y, "doi": doi,
               "journal": _clean(r.get("journal")), "volume": _clean(r.get("volume")),
               "issue": _clean(r.get("issue")), "pages": _clean(r.get("pages")),
               "abstract": _clean(r.get("abstract")), "url": _clean(r.get("pdf_url"))}
        rec["_authors"] = parse_authors(rec["authors_raw"])
        rec["link"] = f"https://doi.org/{doi}" if doi else rec["url"]
        recs.append(rec)
    return recs


def _bib_esc(s: str) -> str:
    return s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")


def to_bibtex(recs: list[dict]) -> str:
    used: set[str] = set()
    out = []
    for r in recs:
        f = []
        if r["_authors"]:
            f.append(("author", " and ".join(f"{s}, {i}" if i else s for s, i in r["_authors"])))
        f.append(("title", "{" + _bib_esc(r["title"]) + "}"))
        for k, v in (("journal", r["journal"]), ("year", r["year"]), ("volume", r["volume"]),
                     ("number", r["issue"]), ("pages", r["pages"].replace("-", "--") if "--" not in r["pages"] else r["pages"]),
                     ("doi", r["doi"]), ("url", r["link"] if not r["doi"] else ""), ("abstract", r["abstract"])):
            if v:
                f.append((k, v if k in ("doi", "url", "year") else _bib_esc(v) if k != "journal" else _bib_esc(v)))
        body = ",\n".join(f"  {k} = {{{v}}}" if not v.startswith("{") else f"  {k} = {v}" for k, v in f)
        out.append(f"@{'article' if r['journal'] else 'misc'}{{{bibtex_key(r, used)},\n{body}\n}}")
    return "\n\n".join(out) + "\n"


def _pages(p: str):
    m = re.match(r"^\s*([\w.]+)\s*[-\u2013\u2014]+\s*([\w.]+)\s*$", p)
    return (m.group(1), m.group(2)) if m else (p, "")


def to_ris(recs: list[dict]) -> str:
    out = []
    for r in recs:
        L = ["TY  - JOUR"]
        L += [f"AU  - {s}, {i}" if i else f"AU  - {s}" for s, i in r["_authors"]]
        if r["year"]:
            L.append(f"PY  - {r['year']}")
        L.append(f"TI  - {r['title']}")
        for tag, v in (("JO", r["journal"]), ("VL", r["volume"]), ("IS", r["issue"])):
            if v:
                L.append(f"{tag}  - {v}")
        if r["pages"]:
            sp, ep = _pages(r["pages"])
            L.append(f"SP  - {sp}")
            if ep:
                L.append(f"EP  - {ep}")
        if r["doi"]:
            L.append(f"DO  - {r['doi']}")
        if r["link"]:
            L.append(f"UR  - {r['link']}")
        if r["abstract"]:
            L.append("AB  - " + r["abstract"].replace("\n", " "))
        L.append("ER  - ")
        out.append("\n".join(L))
    return "\n".join(out) + "\n"


def to_csv(recs: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["literature_id", "authors", "year", "title", "journal", "volume", "issue", "pages", "doi", "url"]
    w.writerow(cols)
    for r in recs:
        w.writerow([r["literature_id"], r["authors_raw"], r["year"], r["title"], r["journal"],
                    r["volume"], r["issue"], r["pages"], r["doi"], r["link"]])
    return buf.getvalue()


def to_json(recs: list[dict]) -> str:
    return json.dumps([{k: v for k, v in r.items() if not k.startswith("_") and k != "link"}
                       | {"url": r["link"], "authors": [f"{s}, {i}".strip(", ") for s, i in r["_authors"]]}
                       for r in recs], ensure_ascii=False, indent=2)


# ---- plain-text styles -------------------------------------------------------

def _end(s: str) -> str:
    return s if s.endswith((".", "?", "!")) else s + "."


def _names(au, style: str) -> str:
    if not au:
        return "Anon."
    def fmt(a, i=None):
        s, ini = a
        if style == "vancouver":
            return f"{s} {ini.replace('.', '').replace(' ', '').replace('-', '')}".strip()
        return f"{s}, {ini}" if ini else s
    if style == "apa":
        n = [fmt(a) for a in au]
        if len(n) > 20:
            n = n[:19] + ["... " + n[-1]]
            return ", ".join(n)
        return n[0] if len(n) == 1 else ", ".join(n[:-1]) + ", & " + n[-1]
    if style == "harvard":
        n = [fmt(a) for a in au]
        return n[0] if len(n) == 1 else ", ".join(n[:-1]) + " and " + n[-1]
    if style == "vancouver":
        n = [fmt(a) for a in au]
        return ", ".join(n[:6]) + (", et al" if len(n) > 6 else "")
    if style == "chicago":
        first = fmt(au[0])
        rest = [f"{ini} {s}".strip() for s, ini in au[1:10]]
        n = [first] + rest
        if len(au) > 10:
            return ", ".join(n) + ", et al"
        return n[0] if len(n) == 1 else ", ".join(n[:-1]) + ", and " + n[-1]
    if style == "mla":
        if len(au) == 1:
            return fmt(au[0])
        if len(au) == 2:
            return f"{fmt(au[0])}, and {au[1][1]} {au[1][0]}".replace("  ", " ")
        return f"{fmt(au[0])}, et al"
    raise ValueError(style)


def format_ref(r: dict, style: str) -> str:
    au, t, j, y = r["_authors"], r["title"].rstrip("."), r["journal"], r["year"] or "n.d."
    vol, iss, pg = r["volume"], r["issue"], r["pages"].replace("--", "\u2013").replace("-", "\u2013")
    link = r["link"]
    if style == "apa":
        s = f"{_names(au, style)} ({y}). {_end(t)}"
        if j:
            s += f" {j}"
            if vol:
                s += f", {vol}" + (f"({iss})" if iss else "")
            if pg:
                s += f", {pg}"
            s += "."
        return s + (f" {link}" if link else "")
    if style == "harvard":
        s = f"{_names(au, style)} ({y}) '{t}',"
        if j:
            s += f" {j}"
            if vol:
                s += f", {vol}" + (f"({iss})" if iss else "")
            if pg:
                s += f", pp. {pg}"
        s = s.rstrip(",") + "."
        return s + (f" Available at: {link}" if link else "")
    if style == "vancouver":
        s = f"{_names(au, style)}. {_end(t)}"
        if j:
            s += f" {j}. {y}"
            if vol:
                s += f";{vol}" + (f"({iss})" if iss else "")
            if pg:
                s += f":{pg}"
            s += "."
        else:
            s += f" {y}."
        return s + (f" doi:{r['doi']}" if r["doi"] else (f" {link}" if link else ""))
    if style == "chicago":
        s = f"{_end(_names(au, style))} {y}. \u201c{t}.\u201d"
        if j:
            s += f" {j}"
            if vol:
                s += f" {vol}" + (f" ({iss})" if iss else "")
            if pg:
                s += f": {pg}"
            s += "."
        return s + (f" {link}." if link else "")
    if style == "mla":
        s = f"{_end(_names(au, style))} \u201c{t}.\u201d"
        if j:
            s += f" {j}"
            if vol:
                s += f", vol. {vol}"
            if iss:
                s += f", no. {iss}"
            s += f", {y}"
            if pg:
                s += f", pp. {pg}"
            s += "."
        else:
            s += f" {y}."
        return s + (f" {link}." if link else "")
    raise ValueError(style)


STYLES = ("apa", "harvard", "vancouver", "chicago", "mla")
FORMATS = ("bibtex", "ris", "csv", "json") + STYLES
MEDIA = {"bibtex": ("application/x-bibtex", "bib"), "ris": ("application/x-research-info-systems", "ris"),
         "csv": ("text/csv", "csv"), "json": ("application/json", "json")}


def render(rows: list[dict], fmt: str) -> str:
    recs = to_records(rows)
    if fmt == "bibtex":
        return to_bibtex(recs)
    if fmt == "ris":
        return to_ris(recs)
    if fmt == "csv":
        return to_csv(recs)
    if fmt == "json":
        return to_json(recs)
    return "\n".join(format_ref(r, fmt) for r in recs) + "\n"
