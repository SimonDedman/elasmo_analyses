"""Parse the SI2022 (Valencia) detailed programme — a schedule, not an abstract
book (8pp, no bodies). Talks are 'Presenter: Title' lines under 'Session N:'
headers; keynotes are name/affiliation/title. All records are elasmo (SI).
"""
import re

_SESSION = re.compile(r"^\s*(Session\s+\d+\s*:.*|[0-9]+[a-z]?\s*:\s*[A-Z].*)$")
_SKIP = re.compile(
    r"^\s*(Chair|Chairs|Time|Location|Participants|Cost|Organiser|Sponsored|"
    r"September|October|Please|Thursday|Friday|Saturday|Sunday|Monday|Tuesday|"
    r"Wednesday|Keynote|Evening|Icebreaker|General Admission|Aquarium|Conference|"
    r"Welcome|Poster|Break|Lunch|Coffee|www|\d)", re.I)
# "Presenter Name: Title" — name before the colon is 1-4 capitalised words
_TALK = re.compile(
    r"^([A-ZÀ-Ýa-zà-ÿ][\w'’.\-]+(?:\s+[A-ZÀ-Ýa-zà-ÿ][\w'’.\-]+){0,4})\s*:\s+(\S.*)$")


def parse_si2022_blocks(text: str):
    lines = text.splitlines()
    blocks = []
    cur_session = None
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        sm = _SESSION.match(s)
        if sm and (s.lower().startswith("session") or re.match(r"^\d+[a-z]?\s*:", s)):
            cur_session = s
            i += 1
            continue
        if _SKIP.match(s):
            i += 1
            continue
        tm = _TALK.match(s)
        if tm:
            presenter = tm.group(1).strip()
            # reject if the "name" is really a session/keyword or too long
            if len(presenter) > 45 or _SKIP.match(presenter):
                i += 1
                continue
            title = tm.group(2).strip()
            # title may wrap onto following lines until next talk/session/skip
            j = i + 1
            while j < n:
                nxt = lines[j].strip()
                if not nxt or _TALK.match(nxt) or _SESSION.match(nxt) or _SKIP.match(nxt):
                    break
                title += " " + nxt
                j += 1
            blocks.append(dict(program_number=None, title=title,
                               author_raw=presenter, presentation_type="talk",
                               session_name=cur_session))
            i = j
            continue
        i += 1
    return blocks


def ingest_si2022(con, text, meeting_meta):
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "program_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_si2022_blocks(text):
        if not b["title"] or len(b["title"]) < 8:
            continue
        rec = extract.extract_fields(
            dict(program_number=None, session_line="", author_raw=b["author_raw"],
                 title=b["title"], abstract_text=None),
            "SI", fmt="jmih_book", use_llm=False)
        rec.update(session_name=b["session_name"], presentation_type="talk",
                   abstract_text=None, keywords=None, society="AES",
                   society_basis="meeting")
        rec = tag.resolve(rec, "SI")           # SI -> is_elasmo=1, basis=meeting
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
