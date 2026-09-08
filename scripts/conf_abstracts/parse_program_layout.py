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
# The 2021-2023 books are the same two columns as 2024/2025 but print no entry
# number, so the start time in the left column is what opens an entry.
_TIMED_ENTRY = re.compile(r"^\d{1,2}:\d{2}$")
# The 2023 poster half opens each entry with a "P<session>-<n>" id where an oral
# entry carries a start time.
_POSTER_ID = re.compile(r"^P\d+-\d+[A-Za-z]?$")
_MERIDIEM = re.compile(r"^(am|pm|AM|PM)$")
_SESSION = re.compile(r"^\s*Session\s+\w+\s*:\s*(.+)$", re.I)
_DAY = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b.*\d{4}$", re.I)
_BANNER = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\d{1,2}\s+\w+)"
    r"\s*[•·*]\s*(.+)$", re.I)
_ROOMLINE = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)?\s*[–—-]", re.I)
_MOD = re.compile(r"^Moderators?\s*:", re.I)
_GLANCE = re.compile(r"^Schedule[- ]at[- ]a[- ]Glance", re.I)
# The 2022 poster listing prints no marker at all - no time, no poster id, just
# the author list beside the title - so the only thing separating one poster
# from the next is the leading it gets: ~15pt between entries against ~10.5pt
# inside one. That is a weak signal, so it is used ONLY inside a poster section
# (a "<day> - Poster Presentations" banner is in force). Applied to any
# two-column page it over-generates badly: JMIH 2025 went 544 blocks to 668.
_ENTRY_LEAD = 1.25
_MIN_LEAD_GAPS = 6
# A leading-opened entry has no marker vouching for it, so it has to look like a
# talk before it is kept. The 2021 poster section has a floor-plan page inside
# it whose scattered room labels ("105 A T E E T", "O E S T R E ET") otherwise
# come through as abstracts.
_WORDY = re.compile(r"[a-z]{4}")
_WORD = re.compile(r"[A-Za-z]{2,}")
# The author index sets its page numbers with dot leaders, and inside the poster
# section those lines straddle both columns exactly like a poster does. Counting
# the dots as words let "Baldwin, Carole . . . . . ." through as a title.
_LEADERS = re.compile(r"\.\s*\.\s*\.\s*\.")
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


def _has_entries(lines, boundary, marker_less=False):
    """Does this page hold entries at all, numbered or timed?

    `marker_less` is set only inside a poster section, where an entry can open
    with nothing but a line that straddles the two columns.
    """
    if any(_entry_tokens(ln) or (ln[0]["x0"] < boundary and _opens_entry(ln[0]))
           for ln in lines):
        return True
    return marker_less and _straddles(lines, boundary) >= 4


def _straddles(lines, boundary):
    return sum(1 for ln in lines if ln[0]["x0"] < boundary
               and any(w["x0"] >= boundary for w in ln))


def _lead_threshold(lines):
    """The leading that separates two entries on a marker-less poster page, or
    None when the page's lines are too uniform to tell entries apart."""
    gaps = sorted(round(b[0]["top"] - a[0]["top"], 1)
                  for a, b in zip(lines, lines[1:])
                  if 4 < b[0]["top"] - a[0]["top"] < 40)
    if len(gaps) < _MIN_LEAD_GAPS:
        return None
    inner = gaps[len(gaps) // 4]          # the common within-entry step
    return inner * _ENTRY_LEAD if gaps[-1] > inner * _ENTRY_LEAD else None


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
    """Drop the leading entry marker - a start time ('9:00', 'am') or a poster
    id - from an author run."""
    out = list(words)
    while out and (_TIME.match(out[0]["text"]) or _MERIDIEM.match(out[0]["text"])
                   or _POSTER_ID.match(out[0]["text"])):
        out.pop(0)
    return out


def _opens_entry(word):
    return bool(_TIMED_ENTRY.match(word["text"]) or _POSTER_ID.match(word["text"]))


def parse_program_layout(pdf_path):
    blocks = []
    day = session = society = None
    ptype = "talk"
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [(pg, _lines(pg.extract_words(extra_attrs=["fontname", "size"])))
                 for pg in pdf.pages]
        # A page whose entries all run both columns onto one line shows the
        # title column's edge only once or twice, so fall back to the edge the
        # document as a whole uses.
        doc_starts = collections.Counter(
            round(ln[0]["x0"]) for _, lns in pages for ln in lns if ln[0]["x0"] >= 200)
        doc_edge = doc_starts.most_common(1)[0][0] if doc_starts else None
        seen_listing = False
        for page, lines in pages:
            if not lines:
                continue
            # The entry numbers sit at the left edge of the title column, so
            # their own x0 defines the column boundary for this page. Pages
            # with no entries carry only headers.
            # The Schedule-at-a-Glance pages are a different table entirely -
            # event name, time, room - and their times would open bogus entries.
            if any(_GLANCE.match(_text_of(ln)) for ln in lines[:6]):
                continue
            # Social events and meetings are listed with times in the same left
            # column as talks, so a time alone does not mean an entry. Every
            # talk-listing page carries a moderator or a presentations banner;
            # the events pages carry neither.
            # A moderator, a "<day> - Poster Presentations" banner or a poster
            # id marks a listing page. Continuation pages carry none of those,
            # so once the daily listings have begun the rest of the book is
            # listings: the special-events and at-a-glance tables, which also
            # put times in the left column, are all front matter.
            has_banner = any(_BANNER.match(_text_of(ln)) for ln in lines[:6])
            listing = has_banner or seen_listing \
                or any(_MOD.match(_text_of(ln)) for ln in lines) \
                or any(_POSTER_ID.match(ln[0]["text"]) for ln in lines)
            seen_listing = seen_listing or has_banner
            # Only a poster section may open entries on leading alone.
            in_posters = ptype == "poster" or any(
                _BANNER.match(_text_of(ln)) and "poster" in _text_of(ln).lower()
                for ln in lines[:6])
            xs = [w["x0"] for ln in lines for _, w in _entry_tokens(ln)]
            numbered = bool(xs)
            if xs:
                boundary = min(xs) - 4
            else:
                # No entry numbers (2021-2023): the title column is the left
                # edge that continuation lines start at, well right of the time
                # (x~49) and author (x~94) columns.
                starts = collections.Counter(
                    round(ln[0]["x0"]) for ln in lines if ln[0]["x0"] >= 200)
                edge = starts.most_common(1)[0] if starts else None
                boundary = ((edge[0] if edge[1] >= 3 else (doc_edge or edge[0])) - 4
                            if edge else (doc_edge - 4 if doc_edge else None))
            if boundary is None or not _has_entries(lines, boundary, in_posters):
                for ln in lines:
                    day, session, society, ptype = _headers(
                        _text_of(ln), day, session, society, ptype)
                continue

            # Walk the page once, opening a new entry at each number and
            # appending everything that follows to whichever entry is open.
            # A marker-less poster page: entries are separated by extra leading.
            gap_open = None
            if in_posters and not numbered and listing and not any(
                    ln[0]["x0"] < boundary and _opens_entry(ln[0])
                    and not _ROOMLINE.match(_text_of(ln)) for ln in lines):
                gap_open = _lead_threshold(lines)
            cur = None
            last_top = None
            for ln in lines:
                last_gap = None if last_top is None else ln[0]["top"] - last_top
                if last_gap is not None and last_gap > _MAX_GAP:
                    cur = None
                last_top = ln[0]["top"]
                if not (_BODY_TOP <= ln[0]["top"] <= _BODY_BOTTOM):
                    continue                      # running header / footer
                text = _text_of(ln)
                toks = _entry_tokens(ln)
                if not toks and _HEADING_FONT.search(ln[0]["fontname"]):
                    # Furniture: a room-and-time banner, a day, or a heading. Any
                    # other bold line in the left column names the block that
                    # follows - "Session 1: SSAR Seibert Ecology" in 2022/2023,
                    # a bare "Reptile Conservation and Management I" in 2021
                    # (which is why the text parser's heading detection found
                    # nothing there), and "AES Posters" on a poster page.
                    if ln[0]["x0"] < boundary and not _ROOMLINE.match(text) \
                            and not _DAY.match(text) and not _BANNER.match(text) \
                            and 2 <= len(text) <= 90:
                        sm = _SESSION.match(text)
                        session = sm.group(1).strip() if sm else text
                        m = _SOC_PREFIX.search(session)
                        society = m.group(1) if m else None
                    else:
                        day, session, society, ptype = _headers(
                            text, day, session, society, ptype)
                    cur = None
                    continue
                # A room-and-time banner opens with a time, so it would look
                # like an entry; the day banner must still reach _headers, which
                # is what sets the section's presentation type.
                if not toks and (_NOTE.match(text) or _ROOMLINE.match(text)):
                    cur = None
                    continue
                if not toks:
                    # A timed entry: the start time opens it, the authors follow
                    # in the same column and the title sits in the other.
                    opens = (not numbered and listing
                             and ln[0]["x0"] < boundary and _opens_entry(ln[0]))
                    # Leading alone opens an entry, so every line that is not
                    # one has to be excluded by name: the section banner spans
                    # both columns and follows a big gap, and would otherwise be
                    # read as the section's first poster.
                    if not opens and gap_open is not None and last_gap is not None \
                            and last_gap > gap_open and ln[0]["x0"] < boundary \
                            and any(w["x0"] >= boundary for w in ln) \
                            and not _BANNER.match(text) and not _DAY.match(text) \
                            and not _MOD.match(text) and not _GLANCE.match(text):
                        opens = True
                    if not opens:
                        pass
                    else:
                        left = _strip_time([w for w in ln if w["x0"] < boundary])
                        right = [w for w in ln if w["x0"] >= boundary]
                        pid = ln[0]["text"] if _POSTER_ID.match(ln[0]["text"]) else None
                        cur = dict(program_number=pid, _title=list(right),
                                   _authors=list(left),
                                   _by_lead=not _opens_entry(ln[0]),
                                   presentation_type="poster" if pid else ptype,
                                   session_name=session,
                                   societies_explicit=[society] if society else [],
                                   session_datetime=day)
                        blocks.append(cur)
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
    out = []
    for b in blocks:
        b["title"] = _text_of(b.pop("_title"), join_wraps=True)
        b["author_raw"] = _text_of(b.pop("_authors"), join_wraps=True)
        if b.pop("_by_lead", False) and not _plausible(b):
            continue
        out.append(b)
    return out


def _plausible(block):
    """Does a leading-opened entry read like a talk rather than page furniture?"""
    title, authors = block["title"], block["author_raw"]
    if _LEADERS.search(title) or _LEADERS.search(authors):
        return False
    return (len(_WORD.findall(title)) >= 4 and len(_WORDY.findall(title)) >= 2
            and bool(_WORDY.search(authors)) and not _ROOMLINE.match(title))


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
