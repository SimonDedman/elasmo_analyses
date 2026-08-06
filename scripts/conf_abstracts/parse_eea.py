"""General parser for EEA (European Elasmobranch Association) abstract books.

EEA books share a TITLE-FIRST layout (unlike the JMIH/ASIH author-first or
ID-first formats):
    [session / time / 'ORAL CONTRIBUTION' / page-number header]   (optional)
    TITLE            (1-3 lines, first)
    AUTHORS          (A. Surname & B. Surname | Name 1,2 | SURNAME, Init.)
    AFFILIATION(S)   (institution lines, sometimes numbered/superscript)
    [Email: ...]
    BODY             (prose)
    [Keywords: ...]

Segmentation is prose-gap based: each abstract = a short header block followed
by a prose body. All EEA records are elasmo (meeting=EEA).
"""
import re

from conf_abstracts.segment import _title_like, _AFFIL_KW
from conf_abstracts.parse_si2018_pdf import _is_prose

_NOISE = re.compile(
    r"^\s*(Session\b|ORAL\b|POSTER\b|Oral Contribution|Poster Contribution|"
    r"Keywords?\b|Organisation\b|Address\b|Email\b|\d{1,3}\s*$|"
    r"\d{1,2}[:.]\d{2}\b|Page\b|Contents?\b|Programme\b|Index\b)", re.I)
_EMAIL = re.compile(r"[\w.\-]+@[\w.\-]+")
# title function-words (NOT 'and'/'&', which are author connectors)
_TITLEWORD = re.compile(
    r"\b(of|the|in|on|for|with|to|from|by|between|during|using|through|within|"
    r"among|into|study|effects?|role|status|case|analysis|assessment|new|"
    r"population|distribution|reproductive|management|conservation)\b", re.I)
# a name token: initial "J." / "J.F." or a Capitalised word (opt superscript/accent)
_NAMETOK = re.compile(r"^(?:[A-ZÀ-Ý]\.?){1,3}$|^[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]+\d*[,;]?$")


_POSTAL = re.compile(r"\b[A-Z]{1,2}\s?\d{3,5}\b|\b\d{4,5}\b")
_COUNTRY = re.compile(
    r"\b(UK|USA|Spain|Portugal|Italy|France|Germany|Netherlands|Greece|Norway|"
    r"Ireland|Belgium|Sweden|Denmark|Turkey|Brazil|Mexico|Canada|Australia|"
    r"South Africa|Scotland|England|Wales)\.?\s*$", re.I)
_INSTITUTE = re.compile(
    r"\b(Universit|Institut|Department|Departamento|Dept|Laborator|Laboratoire|"
    r"Museum|Museo|Facult|Centre|Center|Centro|Station|Society|Associació|"
    r"Foundation|Fundaci|Branch|Ministry|Marine|Ocean|Fisheries|Research|"
    r"College|Box|Street|Avenue|Via|Rua|Calle)\b", re.I)


def _looks_affil(s):
    """Affiliation/address/email line — must NOT be treated as abstract body."""
    return bool(_EMAIL.search(s) or _AFFIL_KW.search(s) or _INSTITUTE.search(s)
                or _COUNTRY.search(s) or _POSTAL.search(s))


def _is_body(s):
    """A genuine abstract-body prose line (not an affiliation/address)."""
    return _is_prose(s) and not _looks_affil(s)


def _is_namelist(s):
    """Author line: mostly name tokens (initials/surnames + and/&/commas),
    no title function-words, not an affiliation/email."""
    s = s.strip()
    if not s or _EMAIL.search(s) or _AFFIL_KW.search(s) or _TITLEWORD.search(s):
        return False
    core = re.sub(r"\b(and)\b|&|,|;", " ", s)          # drop author connectors
    words = [w for w in core.split() if w]
    if len(words) < 2:
        return False
    nameish = sum(1 for w in words if _NAMETOK.match(w))
    return nameish >= 2 and nameish / len(words) >= 0.7


def _parse_header(header_lines):
    """Return (title, author_raw, affiliation) from the header block."""
    lines = [l.strip() for l in header_lines if l.strip() and not _NOISE.match(l)]
    if not lines:
        return None, None, None
    # TITLE = leading title-like lines until the first author/affiliation line
    ti = 0
    title_parts = []
    while ti < len(lines):
        s = lines[ti]
        if _is_namelist(s) or _AFFIL_KW.search(s) or _EMAIL.search(s):
            break
        if _title_like(s) or len(s) > 25:
            title_parts.append(s)
            ti += 1
        else:
            break
    title = " ".join(title_parts).strip()
    rest = lines[ti:]
    # authors = leading name-list lines of the remainder
    auth = []
    ai = 0
    while ai < len(rest) and _is_namelist(rest[ai]):
        auth.append(rest[ai])
        ai += 1
    author_raw = " ".join(auth).strip()
    # affiliation = first institution / email-bearing line after authors
    affil = next((l for l in rest[ai:] if _AFFIL_KW.search(l) or _EMAIL.search(l)), None)
    return (title or None), (author_raw or None), affil


# per-abstract delimiters seen across EEA books
_TIMESLOT = re.compile(r"^\s*\d{1,2}[.:]\d{2}\s*[–—-]\s*\d{1,2}[.:]\d{2}\s*$")
_SESSION_DELIM = re.compile(r"^\s*Session\s+\w+\s*[:.]", re.I)


def _parse_one_abstract(block_lines):
    """Parse a single-abstract block: [delimiter?] title, authors, affils, body."""
    lines = [l.strip() for l in block_lines
             if l.strip() and not _NOISE.match(l)]
    if not lines:
        return None
    # title = leading title-like lines until an author / affiliation line
    tp, ti = [], 0
    while ti < len(lines):
        s = lines[ti]
        if _is_namelist(s) or _looks_affil(s):
            break
        if _title_like(s) or len(s) > 25:
            tp.append(s)
            ti += 1
        else:
            break
    title = " ".join(tp).strip()
    rest = lines[ti:]
    author_raw = " ".join(l for l in rest if _is_namelist(l)).strip()
    affil = next((l for l in rest if _looks_affil(l)), None)
    # body = from the first genuine (non-affil) sentence to the block end —
    # the header (authors/affils/emails) sits above it; once prose starts it
    # runs to the end, so mid-body institution mentions are kept.
    bstart = next((k for k, l in enumerate(rest) if _is_body(l)), None)
    if bstart is None:
        return None
    body = re.sub(r"\s{2,}", " ", " ".join(rest[bstart:])).strip()
    if not title or len(body.split()) < 40:
        return None
    return dict(title=title, author_raw=author_raw or None,
                affiliation=affil, abstract_text=body)


def _split_at(lines, idxs):
    blocks = []
    for k, start in enumerate(idxs):
        end = idxs[k + 1] if k + 1 < len(idxs) else len(lines)
        parsed = _parse_one_abstract(lines[start:end])
        if parsed:
            blocks.append(parsed)
    return blocks


def _prose_gap(lines):
    blocks, header, i, n = [], [], 0, len(lines)
    while i < n:
        s = lines[i].strip()
        # TRIGGER a body only on a genuine (non-affiliation) prose sentence, so
        # header affiliation lines don't start/bridge a body. Once started,
        # CONTINUE on any prose (mid-body institution mentions kept); the next
        # abstract's short title line (not prose) ends the body.
        if _is_body(s):
            body = [s]
            i += 1
            while i < n and (_is_prose(lines[i].strip()) or not lines[i].strip()):
                t = lines[i].strip()
                if t and not re.match(r"(?i)^keywords", t):
                    body.append(t)
                i += 1
            title, author_raw, affil = _parse_header(header)
            body_txt = re.sub(r"\s{2,}", " ", " ".join(body)).strip()
            if title and body_txt and len(body_txt.split()) >= 40:
                blocks.append(dict(title=title, author_raw=author_raw,
                                   affiliation=affil, abstract_text=body_txt))
            header = []
        else:
            if s:
                header.append(s)
            if len(header) > 12:
                header = header[-6:]
            i += 1
    return blocks


def _author_anchored(lines):
    """Segment on the reliable EEA signature: an AUTHOR line (name list)
    immediately followed by an AFFILIATION/email. title = lines directly above
    the author; body = prose after the affiliation, to before the next author."""
    strip = [l.strip() for l in lines]
    n = len(strip)
    anchors = []
    for i in range(n):
        if not _is_namelist(strip[i]):
            continue
        if any(strip[j] and _looks_affil(strip[j]) for j in range(i + 1, min(i + 4, n))):
            anchors.append(i)
    blocks = []
    for k, ai in enumerate(anchors):
        # title = contiguous title-like lines directly above the author
        tl, j = [], ai - 1
        while j >= 0:
            s = strip[j]
            if not s:
                j -= 1
                continue
            if _is_body(s) or _is_namelist(s) or _looks_affil(s):
                break
            if _title_like(s) or len(s) > 18:
                tl.insert(0, s)
                j -= 1
            else:
                break
        title = " ".join(tl).strip()
        # authors = the anchor line + following name-list lines
        auth, j = [strip[ai]], ai + 1
        while j < n and _is_namelist(strip[j]):
            auth.append(strip[j])
            j += 1
        author_raw = " ".join(auth).strip()
        affil = next((strip[x] for x in range(j, min(j + 5, n))
                      if _looks_affil(strip[x])), None)
        # body = prose from after the affil/email block to before the next anchor
        end = anchors[k + 1] if k + 1 < len(anchors) else n
        # skip the affiliation/email header run
        while j < end and (not strip[j] or _looks_affil(strip[j]) or _is_namelist(strip[j])):
            j += 1
        seg = [strip[x] for x in range(j, end) if strip[x]]
        bs = next((x for x, l in enumerate(seg) if _is_body(l)), None)
        if bs is None:
            continue
        # trim trailing lines that belong to the next abstract's title
        be = len(seg)
        while be > bs and not _is_prose(seg[be - 1]):
            be -= 1
        body = re.sub(r"\s{2,}", " ", " ".join(seg[bs:be])).strip()
        if not title or len(body.split()) < 40:
            continue
        blocks.append(dict(title=title, author_raw=author_raw or None,
                           affiliation=affil, abstract_text=body))
    return blocks


def _good(blocks):
    """Score a segmentation: abstracts with a plausible (non-fragment) title."""
    return sum(1 for x in blocks if x["title"] and 12 < len(x["title"]) < 200
               and x["title"][0].isupper() and x["author_raw"])


def parse_eea_blocks(text):
    """Prose-gap segmentation — the most reliable across EEA layouts. Bodies
    extract cleanly; titles/authors are rough (heuristic wall — a long title
    line vs a body sentence is regex-ambiguous) and are refined by an optional
    LLM header pass at ingest (see ingest_eea use_llm)."""
    return _prose_gap(text.splitlines())


def ingest_eea(con, text, meeting_meta):
    from conf_abstracts import load, extract, tag
    meta = dict(meeting_meta)
    meta.setdefault("meeting", "EEA")
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    n = 0
    for b in parse_eea_blocks(text):
        rec = extract.extract_fields(
            dict(program_number=None, session_line="", author_raw=b["author_raw"] or "",
                 title=b["title"], abstract_text=b["abstract_text"]),
            "EEA", fmt="asih_book", use_llm=False)
        rec.update(abstract_text=b["abstract_text"], keywords=None,
                   society="AES", society_basis="meeting")
        if b.get("affiliation") and rec["authors"]:
            rec["authors"][0]["affiliation"] = b["affiliation"]
        rec = tag.resolve(rec, "EEA")     # EEA -> is_elasmo=1, basis=meeting
        if not rec.get("title") or len(rec["title"]) > 240:
            rec["needs_review"] = 1
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    con.commit()
    return n
