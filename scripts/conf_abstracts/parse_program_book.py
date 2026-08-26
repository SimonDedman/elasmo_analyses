"""Parser for modern JMIH program/schedule books (2021-2025 'Conference_Program').

These have NO abstract bodies — they are schedules. Each talk:
    Session 7: ASIH Stoye Awards: Ecology and Ethology   <- session (society prefix)
    Moderator: Scott Parker
    1:30 pm                                               <- time
    John Moore, Thomas Anderson                           <- authors
    7.1 | The Effects of Food Web Manipulations ...        <- "N.N | Title" (may wrap)

We capture title, authors, presentation_type, session, society, day/time —
abstract_text stays null. Older grid/matrix program books (2006-2019) linearise
badly and are out of scope here.
"""
import re

from conf_abstracts.config import SOCIETIES

_SOC = "|".join(sorted(SOCIETIES, key=len, reverse=True))
_TALK = re.compile(r"^\s*(?:CANCELLED\s+)?(\d+\.\d+[A-Za-z]?)\s*\|\s*(.+)$")
_TIME = re.compile(r"^\s*\d{1,2}:\d{2}\s*(am|pm|AM|PM)\s*$")
_SESSION = re.compile(r"^\s*Session\s+[\w]+\s*:\s*(.+)$", re.I)
_POSTER = re.compile(r"poster", re.I)
_DAY = re.compile(
    r"^\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b.*\d{4}", re.I)
_MOD = re.compile(r"^\s*Moderator", re.I)
_SOC_PREFIX = re.compile(r"\b(" + _SOC + r")\b")


_FUNC_WORD = re.compile(
    r"\b(of|the|and|in|on|for|with|to|from|by|at|as|between|during|using|"
    r"based|within|among|into|through|new|effects?|role)\b")


def _session_society(session_name: str):
    m = _SOC_PREFIX.search(session_name or "")
    return m.group(1) if m else None


def _is_namelist(s: str) -> bool:
    """Author line (proper names, no title function-words like 'of'/'the')."""
    return not _FUNC_WORD.search(s) and bool(s)


def _parse_time_delimited(text: str):
    """2021-2023 format: time -> authors -> title (no 'N.N |' number)."""
    lines = text.splitlines()
    blocks = []
    cur_session = cur_society = cur_day = None
    cur_type = "talk"
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if _DAY.match(s):
            cur_day = s
            i += 1
            continue
        sm = _SESSION.match(s)
        if sm:
            cur_session = sm.group(1).strip()
            cur_society = _session_society(cur_session)
            cur_type = "poster" if _POSTER.search(cur_session) else "talk"
            i += 1
            continue
        if _TIME.match(s):
            # collect content lines until the next time / session / day
            content = []
            j = i + 1
            while j < n:
                t = lines[j].strip()
                if _TIME.match(t) or _SESSION.match(t) or _DAY.match(t):
                    break
                if t and not _MOD.match(t):
                    content.append(t)
                j += 1
            # authors = leading name-list lines; title = the rest
            ai = 0
            while ai < len(content) and _is_namelist(content[ai]):
                ai += 1
            author_raw = " ".join(content[:ai]).strip()
            title = " ".join(content[ai:]).strip()
            if title and len(title) >= 6:
                blocks.append(dict(
                    program_number=None, title=title, author_raw=author_raw,
                    presentation_type=cur_type, session_name=cur_session,
                    societies_explicit=[cur_society] if cur_society else [],
                    session_datetime=cur_day))
            i = j
            continue
        i += 1
    return blocks


_TALK26 = re.compile(r"^\s*(P?\d+\.\d+[A-Za-z]?)\s*:\s*(.+)$")          # "2.1: Title"
_TIMERANGE = re.compile(r"^\s*\d{1,2}:\d{2}\s*(AM|PM)\s*-\s*\d{1,2}:\d{2}\s*(AM|PM)\s*$", re.I)
_SPEAKER = re.compile(r"^\s*Speakers?\s*:\s*(.+)$", re.I)
_LOCATION = re.compile(r"^\s*Location\s*:", re.I)


def _parse_2026_format(text: str):
    """2026 (Whova export) format: 'N.N: Title' (may wrap) -> 'h:mm AM - h:mm PM'
    -> 'Location: ...' -> 'Speaker: Name'. Sessions 'Session N: <Society> Name'."""
    lines = text.splitlines()
    blocks = []
    cur_session = cur_society = cur_day = None
    cur_type = "talk"
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if _DAY.match(s):
            cur_day = s
            i += 1
            continue
        sm = _SESSION.match(s)
        if sm:
            cur_session = sm.group(1).strip()
            cur_society = _session_society(cur_session)
            cur_type = "poster" if _POSTER.search(cur_session) else "talk"
            i += 1
            continue
        tm = _TALK26.match(s)
        if tm and not _TIMERANGE.match(s):
            num, title = tm.group(1), tm.group(2).strip()
            j = i + 1
            while j < n:
                nxt = lines[j].strip()
                if not nxt or _TIMERANGE.match(nxt) or _TALK26.match(nxt) or _SESSION.match(nxt) \
                        or _DAY.match(nxt) or _LOCATION.match(nxt) or _SPEAKER.match(nxt):
                    break
                title += " " + nxt
                j += 1
            # speaker follows within the next few lines
            speaker = ""
            k = j
            while k < n and k < j + 8:
                t = lines[k].strip()
                if _TALK26.match(t) or _SESSION.match(t):
                    break
                spm = _SPEAKER.match(t)
                if spm:
                    speaker = spm.group(1).strip()
                    break
                k += 1
            ptype = "poster" if (num.startswith("P") or cur_type == "poster") else cur_type
            blocks.append(dict(
                program_number=num, title=title.strip(), author_raw=speaker,
                presentation_type=ptype, session_name=cur_session,
                societies_explicit=[cur_society] if cur_society else [],
                session_datetime=cur_day))
            i = max(j, k if speaker else j)
            continue
        i += 1
    return blocks


def parse_program_book_blocks(text: str):
    lines = text.splitlines()
    # 2026: "N.N: Title" + "Speaker:" lines (Whova export)
    if sum(1 for l in lines if _SPEAKER.match(l)) >= 20 and sum(1 for l in lines if _TALK26.match(l)) >= 20:
        b26 = _parse_2026_format(text)
        if b26:
            return b26
    # 2024/2025 use "N.N | Title"; 2021-2023 are time-delimited with no number.
    if sum(1 for l in lines if _TALK.match(l)) < 20:
        td = _parse_time_delimited(text)
        if td:
            return td
    blocks = []
    cur_session = None
    cur_society = None
    cur_type = "talk"
    cur_day = None
    pending = []          # lines accumulated since the last time marker (authors)
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue
        if _DAY.match(s):
            cur_day = s
            pending = []
            i += 1
            continue
        sm = _SESSION.match(s)
        if sm:
            cur_session = sm.group(1).strip()
            cur_society = _session_society(cur_session)
            cur_type = "poster" if _POSTER.search(cur_session) else "talk"
            pending = []
            i += 1
            continue
        if _MOD.match(s):
            i += 1
            continue
        if _TIME.match(s):
            pending = []          # authors follow the time
            i += 1
            continue
        tm = _TALK.match(s)
        if tm:
            title = tm.group(2).strip()
            # title may wrap onto following lines until a time/talk/session/blank
            j = i + 1
            while j < n:
                nxt = lines[j].strip()
                if not nxt or _TIME.match(nxt) or _TALK.match(nxt) \
                        or _SESSION.match(nxt) or _DAY.match(nxt) or _MOD.match(nxt):
                    break
                title += " " + nxt
                j += 1
            # authors = the most recent pending non-empty line(s)
            author_raw = " ".join(pending).strip()
            blocks.append(dict(
                program_number=tm.group(1),
                title=title.strip(),
                author_raw=author_raw,
                presentation_type=cur_type,
                session_name=cur_session,
                societies_explicit=[cur_society] if cur_society else [],
                session_datetime=cur_day,
            ))
            pending = []
            i = j
            continue
        # otherwise: a candidate author line (accumulate)
        pending.append(s)
        i += 1
    return blocks


def ingest_program_book(con, text, meeting_meta):
    """Parse a modern program book and insert schedule talks (no bodies).
    Returns count."""
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "program_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    _NOISE_AUTH = re.compile(r"\b(Room|Ballroom|Hall|LOCATION|Suite|Salon|Foyer)\b", re.I)
    _NOISE_TITLE = re.compile(
        r"^(Schedule-at-a-Glance|Symposium:|LOCATION|Welcome|Break|Lunch|"
        r"Poster Session|Business Meeting|Social|Reception|Registration|Awards?)\b", re.I)
    for b in parse_program_book_blocks(text):
        if not b["title"] or len(b["title"]) < 6:
            continue
        # drop grid-schedule pollution and non-talk logistics
        if _NOISE_AUTH.search(b["author_raw"] or ""):
            continue
        if _NOISE_TITLE.match(b["title"]):
            continue
        # a real talk has a presenter (keynotes included); skip author-less items
        if not (b["author_raw"] or "").strip():
            continue
        rec = extract.extract_fields(
            dict(program_number=b["program_number"], session_line=b["session_name"] or "",
                 author_raw=b["author_raw"], title=b["title"], abstract_text=None),
            meta["meeting"], fmt="jmih_book", use_llm=False)
        # override with the schedule-derived fields
        rec["presentation_type"] = b["presentation_type"]
        rec["session_name"] = b["session_name"]
        rec["societies_explicit"] = b["societies_explicit"]
        rec["session_datetime"] = b["session_datetime"]
        rec["abstract_text"] = None
        rec["keywords"] = None
        rec = tag.resolve(rec, meta["meeting"])
        if rec.get("_llm_is_elasmo") and not rec["is_elasmo"]:
            rec["is_elasmo"] = 1
            rec["elasmo_basis"] = "content"
        rec["needs_review"] = 1 if not b["author_raw"] else 0
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
