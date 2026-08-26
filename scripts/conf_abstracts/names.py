"""Author-name normalisation for the conference-abstracts DB.

Target convention (Simon, 2026-08-26): "First I. Last" — the form used by the
Fable extractions and most JMIH/SI records (~32k of ~38k author rows). Sources
that print "LAST, FIRST I." (elasmo.org 2000-2005, some JMIH books) or
ALL CAPS are converted; anything that doesn't look like a clean personal name
(digits, more than five tokens, several commas — the regex parsers' author-block
fragments) is left untouched so garbage isn't made worse.
"""
import re

_PARTICLES = {"de", "da", "del", "della", "der", "den", "di", "do", "dos", "du",
              "la", "le", "van", "von", "y", "e", "af", "av", "ten", "ter"}
_SUFFIX = re.compile(r"^(jr|sr|ii|iii|iv)\.?$", re.I)


def _cap_word(w: str) -> str:
    if not w:
        return w
    low = w.lower()
    if low in _PARTICLES:
        return low
    if _SUFFIX.match(w):
        return w.capitalize().rstrip(".") + ("." if low.startswith(("jr", "sr")) else "")
    # initials like "J.A." stay upper
    if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]?\.?", w):
        return w.upper()
    if len(w) <= 2 and w.isalpha() and w.isupper():
        return w  # bare initials without dots
    out = "-".join(p[:1].upper() + p[1:].lower() for p in w.split("-"))
    out = "'".join(p[:1].upper() + p[1:] for p in out.split("'"))
    if out.lower().startswith("mc") and len(out) > 2:
        out = "Mc" + out[2:3].upper() + out[3:]
    return out


def _capital_case(s: str) -> str:
    return " ".join(_cap_word(w) for w in s.split())


def _clean_personal(s: str) -> bool:
    return bool(s) and not re.search(r"\d", s) and len(s.split()) <= 6 and s.count(",") <= 2


def normalise(full_name: str) -> str:
    """'LAST, FIRST I.' / 'Last, First I., Jr.' / 'LAST FIRST' -> 'First I. Last'."""
    s = (full_name or "").strip().strip(",")
    if not _clean_personal(s):
        return full_name
    suffix = ""
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) >= 2 and _SUFFIX.match(parts[-1]):
        suffix = parts.pop()
    if len(parts) == 2:
        last, first = parts
        s = f"{first} {last}"
    elif len(parts) > 2:
        return full_name
    if s.isupper() or (last_upper := any(w.isupper() and len(w) > 3 for w in s.split())):
        s = _capital_case(s)
    if suffix:
        s = f"{s} {_cap_word(suffix)}"
    # O'Gorman / D'Angelo with straight or curly apostrophes
    s = re.sub(r"\b([OD])(['\u2019])([a-z])", lambda m: m.group(1) + m.group(2) + m.group(3).upper(), s)
    return s


def normalise_db(con) -> int:
    """Apply normalise() to every authors.full_name; returns rows changed."""
    n = 0
    for aid, name in con.execute("SELECT author_id, full_name FROM authors").fetchall():
        new = normalise(name)
        if new != name:
            con.execute("UPDATE authors SET full_name=? WHERE author_id=?", (new, aid))
            n += 1
    con.commit()
    return n


if __name__ == "__main__":
    import sqlite3, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from conf_abstracts import config as C
    con = sqlite3.connect(str(C.DB_PATH))
    print("normalised", normalise_db(con), "author names")
