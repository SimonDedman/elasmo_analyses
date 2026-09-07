r"""Coordinate-aware parser for the two-column JMIH programme books (2024, 2025).

`parse_program_book.py` reads these from `pdftotext` output, and that is where it
goes wrong. The page is two columns - time and authors on the left, "N.N | Title"
on the right - and the text layer only preserves that when every author fits the
left column. When the author list is wide, pdftotext emits one line holding the
tail of the authors AND the head of the title:

    Jake New, Jonathan Smart, Ross Dwyer, Kelli Latheam, Edwin 30.2 | Sharks and Rays of the Gulf of Carpentaria: Establishing

`_TALK` anchors the number at the start of a line, so that entry matches nothing
and is dropped outright. Seven JMIH 2025 talks went missing that way, four of
them elasmo, and JMIH 2025 has no abstract book to recover them from.

Reading word coordinates instead removes the guesswork: the columns are at fixed
x, so each entry is exactly "the left-column words beside its number" and "the
right-column words beneath it". It also picks up the poster half of the book,
which the text parser drops for an unrelated reason - poster numbers carry a "P"
prefix that `_TALK`'s `\d+\.\d+` cannot match, so JMIH 2025 held 343 talks and
none of its 190 posters.

Returns the same block dicts as `parse_program_book_blocks`, so it feeds the
existing `ingest_program_book` unchanged.
"""
import collections
import re

import pdfplumber

from conf_abstracts.config import SOCIETIES

_SOC = "|".join(sorted(SOCIETIES, key=len, reverse=True))
_SOC_PREFIX = re.compile(r"\b(" + _SOC + r")\b")
# The books kern the entry number so pdfplumber reads it as "26 .1"; despace
# before matching. A trailing letter marks a late addition ("P8.12a").
_NUM = re.compile(r"^(P?\d{1,3}\.\d{1,3}[A-Za-z]?)$")
_TIME = re.compile(r"^\d{1,2}:\d{2}$")
_MERIDIEM = re.compile(r"^(am|pm|AM|PM)$")
_SESSION = re.compile(r"^\s*Session\s+\w+\s*:\s*(.+)$", re.I)
_DAY = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b.*\d{4}$", re.I)
_BANNER = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}\s+\w+)"
    r"\s*[•·*]\s*(.+)$", re.I)
_ROOMLINE = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)?\s*[–—-]", re.I)
_MOD = re.compile(r"^Moderators?\s*:", re.I)
# Poster blocks are headed by a bold category line ("AES Posters", "ASIH Storer
# Herpetology") instead of a numbered "Session N:" line. Without it every poster
# lands with a null session and no society, which for the AES poster block is
# the difference between 60 elasmo posters attributed and none.
_BOLD = re.compile(r"Bold", re.I)
_NOTE = re.compile(r"^Note\s*:", re.I)
_LINE_TOL = 3.0          # points; two words are on one line within this
# The running page header (the day) and footer ("JMIH 2025 Conference Program 15")
# sit outside the body text block. They are not part of any entry, and appending
# them to whichever entry happened to be open is how "... Georgia Barrier Islands
# Ballroom F" and "... 15 JMIH 2025 Conference Program" got into titles.
_BODY_TOP, _BODY_BOTTOM = 45.0, 745.0
# Entry text is set light/italic at ~9pt. Anything bold or medium is furniture:
# a session line, a room-and-time banner, or a poster category heading. Such a
# line always closes the open entry.
_HEADING_FONT = re.compile(r"(Bold|Medium)", re.I)
# Consecutive lines of one entry sit ~10pt apart. A gap much larger than that
# means the entry ended and something else began, which is how a title reached
# forward into the next section's plenary listing.
_MAX_GAP = 22.0

# These books are set ragged-right and never hyphenate to justify, so a hyphen
# at a line end is always part of the word: "long-", "Hatchery-", "Herrera-".
# Join those halves and KEEP the hyphen - pdftotext drops it, which is where the
# DB's "longterm", "Floodpulse", "HighThroughput" and "landbased" came from.
# Only a break between the halves counts, so a suspended hyphen sitting inside
# one line ("Pre- and Post-Copulatory") is left exactly as printed.
_LINEBREAK = "\x00"
_WRAP = re.compile(r"-\s*" + _LINEBREAK + r"\s*")


def _despace(t):
    return t.replace(" ", "")


def _lines(words):
    """Group words into visual lines, each sorted left to right.

    Cluster on the gap between successive tops rather than bucketing
    round(top/tol): two columns of the same printed line differ by a fraction
    of a point, and a bucket edge falling between them splits the line in two.
    That is what detached the authors of JMIH 2025 P1.3 from their poster.
    """
    out = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if out and w["top"] - out[-1][0] <= _LINE_TOL:
            out[-1][1].append(w)
        else:
            out.append((w["top"], [w]))
    return [sorted(v, key=lambda w: w["x0"]) for _, v in out]


def _entry_tokens(line):
    """The 'N.N' words on this line that are actually entry numbers, i.e. the
    next word is the '|' separator. A bare 'P1.4' inside a title is not one."""
    out = []
    for i, w in enumerate(line):
        if _NUM.match(_despace(w["text"])) and i + 1 < len(line) \
                and line[i + 1]["text"].strip() == "|":
            out.append((i, w))
    return out


def _text_of(words, join_wraps=False):
    t = " ".join(w["text"] for w in words)
    if join_wraps:
        t = _WRAP.sub("-", t)
    return re.sub(r"\s+", " ", t.replace(_LINEBREAK, " ")).strip()


_BREAK = {"text": _LINEBREAK, "x0": -1.0, "top": -1.0}


def _strip_time(words):
    """Drop the leading start-time tokens ('9:00', 'am') from an author run."""
    out = list(words)
    while out and (_TIME.match(out[0]["text"]) or _MERIDIEM.match(out[0]["text"])):
        out.pop(0)
    return out


def parse_program_layout(pdf_path):
    blocks = []
    day = session = society = None
    ptype = "talk"
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["fontname", "size"])
            if not words:
                continue
            lines = _lines(words)
            # The entry numbers sit at the left edge of the title column, so
            # their own x0 defines the column boundary for this page. Pages
            # with no entries carry only headers.
            xs = [w["x0"] for ln in lines for _, w in _entry_tokens(ln)]
            if not xs:
                for ln in lines:
                    day, session, society, ptype = _headers(
                        _text_of(ln), day, session, society, ptype)
                continue
            boundary = min(xs) - 4

            # Walk the page once, opening a new entry at each number and
            # appending everything that follows to whichever entry is open.
            cur = None
            last_top = None
            for ln in lines:
                if last_top is not None and ln[0]["top"] - last_top > _MAX_GAP:
                    cur = None
                last_top = ln[0]["top"]
                if not (_BODY_TOP <= ln[0]["top"] <= _BODY_BOTTOM):
                    continue                      # running header / footer
                text = _text_of(ln)
                toks = _entry_tokens(ln)
                if not toks and _HEADING_FONT.search(ln[0]["fontname"]):
                    # furniture: a session, a room banner, or a poster heading
                    if ptype == "poster" and ln[0]["x0"] < boundary \
                            and not _ROOMLINE.match(text) and not _DAY.match(text) \
                            and not _SESSION.match(text) and not _BANNER.match(text) \
                            and 2 <= len(text) <= 70:
                        session = text
                        m = _SOC_PREFIX.search(text)
                        society = m.group(1) if m else None
                    else:
                        day, session, society, ptype = _headers(
                            text, day, session, society, ptype)
                    cur = None
                    continue
                if not toks and _NOTE.match(text):
                    cur = None
                    continue
                if not toks:
                    d2, s2, so2, pt2 = _headers(text, day, session, society, ptype)
                    if (d2, s2, pt2) != (day, session, ptype):
                        day, session, society, ptype = d2, s2, so2, pt2
                        cur = None          # a header closes the open entry
                        continue
                    day, session, society, ptype = d2, s2, so2, pt2
                    tgt = cur
                    if tgt is not None:
                        # continuation: left of the boundary is more authors,
                        # right of it is more title.
                        left = _strip_time([w for w in ln if w["x0"] < boundary])
                        right = [w for w in ln if w["x0"] >= boundary]
                        if left and not _MOD.match(text) and not _NOTE.match(text):
                            tgt["_authors"] += [_BREAK] + left
                        if right:
                            tgt["_title"] += [_BREAK] + right
                    continue
                # One or more entries start on this line.
                for k, (idx, tok) in enumerate(toks):
                    num = _despace(tok["text"])
                    end = toks[k + 1][0] if k + 1 < len(toks) else len(ln)
                    title_words = ln[idx + 2:end]
                    author_words = _strip_time(
                        [w for w in ln[:idx] if w["x0"] < boundary]) if k == 0 else []
                    cur = dict(program_number=num, _title=list(title_words),
                               _authors=list(author_words),
                               presentation_type="poster" if num.startswith("P") else ptype,
                               session_name=session,
                               societies_explicit=[society] if society else [],
                               session_datetime=day)
                    blocks.append(cur)
    for b in blocks:
        b["title"] = _text_of(b.pop("_title"), join_wraps=True)
        b["author_raw"] = _text_of(b.pop("_authors"), join_wraps=True)
    return blocks


def _headers(text, day, session, society, ptype):
    """Update the running day / session / presentation type from a header line."""
    if _DAY.match(text):
        return text, session, society, ptype
    bm = _BANNER.match(text)
    if bm:
        kind = bm.group(3).lower()
        newtype = "poster" if "poster" in kind else (
            "symposium" if "symposi" in kind else (
                "lightning" if "lightning" in kind else (
                    "plenary" if "plenary" in kind else "talk")))
        yr = re.search(r"\b(19|20)\d{2}\b", day or "")
        d = f"{bm.group(1)} {bm.group(2)}" + (f" {yr.group(0)}" if yr else "")
        return d, None, None, newtype
    sm = _SESSION.match(text)
    if sm:
        name = sm.group(1).strip()
        m = _SOC_PREFIX.search(name)
        return day, name, (m.group(1) if m else None), \
            ("poster" if re.search(r"poster", name, re.I) else ptype)
    return day, session, society, ptype
