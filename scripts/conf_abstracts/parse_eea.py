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


# ---------------------------------------------------------------------------
# EEA 2026 (online, Shark Trust; Canva-built, born-digital booklet).
# The generic prose-gap parser above plateaus on titles, and this book's
# author lines vary too much (superscripts, none, two-column affiliations) for
# a purely structural split. But the booklet opens with its own 7-page agenda,
# which names every talk, so each abstract is ANCHORED on its agenda title.
# Earlier years are untouched: nothing above calls this.
# Per-abstract layout (pdftotext -layout):
#   [DAY n — SESSION n (Name)]   session header, sometimes after a photo page
#   TITLE      1-3 lines              AUTHORS   names, superscript affil numbers
#   AFFILS     "1" line + text, "¹Text", or two columns   BODY   prose
#   KEYWORDS   one unlabelled comma/semicolon line
# ---------------------------------------------------------------------------
_SUP = "¹²³⁴⁵⁶⁷⁸⁹⁰"
_SUP_MAP = str.maketrans(_SUP + "˒", "1234567890,")
_E26_SESSION = re.compile(r"^DAY\s+(\d)\s*[—–-]\s*SESSION\s+(\d)\s*\((.+)\)\s*$")
_E26_TIME = re.compile(r"^\d{2}:\d{2}$")
_E26_NOTTALK = re.compile(r"(?i)session introduction|q&a|^break|welcome|close of day|"
                          r"closing remarks|panel discussion")
# an author name carrying an affiliation superscript: letter, then digits
_E26_AUTHSUP = re.compile(r"[A-Za-zÀ-ÿ.)*]\s?(?:\d{1,2}|[" + _SUP + r"]+)(?:,\s?\d{1,2})*\s*(?:[;,&]|$)")
# an affiliation marker line: a bare number (or two, for two-column layouts),
# a number glued to the text ("1Institute"), or a unicode superscript. A body
# line opening "24, 36, 48 hours" must NOT match.
_E26_MARK = re.compile(r"^(?:\d{1,2}(?:\s{2,}\d{1,2})?\s*$|\d{1,2}(?=[A-Za-zÀ-ÿ])|[" + _SUP + r"]+)")


def _e26_norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def parse_eea2026_agenda(raw_text):
    """Talks from the agenda pages of the RAW (non-layout) pdftotext output:
    [dict(day, time_uk, minutes, speaker, title)], in programme order.
    Time is the agenda's 'UTC +1' column (UK, BST); minutes = slot length,
    5 = speed talk, 10 = regular talk."""
    pages = raw_text.split("\f")
    rows, day = [], 0
    for pg in pages[1:8]:
        if "EEA Agenda" in pg:
            day += 1
        if not day:
            continue
        paras = [re.sub(r"\n\d{1,2}\n", "\n", p.strip()) for p in re.split(r"\n\s*\n", pg) if p.strip()]
        i = 0
        while i < len(paras):
            if _E26_TIME.match(paras[i]):
                times = [paras[i]]
                while i + 1 < len(paras) and _E26_TIME.match(paras[i + 1]) and len(times) < 3:
                    i += 1
                    times.append(paras[i])
                rest = paras[i + 1:i + 3] + ["", ""]
                rows.append(dict(day=day, time_uk=times[-1],
                                 speaker=re.sub(r"\s+", " ", rest[0]).strip(),
                                 title=re.sub(r"\s+", " ", re.sub(r"\s\d{1,2}(?=\s)", " ", rest[1])).strip()))
            i += 1
    for k, r in enumerate(rows):          # slot length = gap to the next row
        if k + 1 < len(rows) and rows[k + 1]["day"] == r["day"]:
            h1, m1 = map(int, r["time_uk"].split(":"))
            h2, m2 = map(int, rows[k + 1]["time_uk"].split(":"))
            r["minutes"] = (h2 * 60 + m2) - (h1 * 60 + m1)
        else:
            r["minutes"] = None
    return [r for r in rows if r["title"] and not _E26_NOTTALK.search(r["title"])
            and not _E26_NOTTALK.search(r["speaker"]) and not r["speaker"].startswith("Chair")]


def _e26_split_authors(raw):
    """'A B1; C D2,3, E F1' -> [[name, ['1'], followed_by_semicolon], ...]."""
    raw = raw.translate(_SUP_MAP)
    raw = re.sub(r"\s+(?:and|&)\s+", ", ", raw)
    raw = re.sub(r"\((?:Ph\.?D\.?|PhD)\)", "", raw)
    out = []
    for m in re.finditer(r"([^,;\d]+?)\s*\*?\s*((?:\d{1,2})(?:\s?,\s?\d{1,2}(?=\s*(?:,|;|$)|\s?,\s?\d))*)?\s*\*?\s*([;,]|$)", raw):
        name = re.sub(r"^(?:Dr\.?|Prof\.?)\s+", "", m.group(1).strip(" *"))
        if not name:
            continue
        nums = [n.strip() for n in (m.group(2) or "").split(",") if n.strip()]
        if re.fullmatch(r"(?:[A-Z]\.?){1,3}", name) and out:
            out[-1][0] = f"{name.rstrip('.')}. {out[-1][0]}"     # "Meyers, E.K.M."
            out[-1][1] += nums
            continue
        sm = re.fullmatch(r"([A-ZÀ-Ý][\w'À-ÿ-]+(?:\s[A-ZÀ-Ý][\w'À-ÿ-]+)?)\s((?:[A-Z]\.?){1,4})", name)
        if sm and sm.group(2).replace(".", "").isupper() and len(sm.group(2).replace(".", "")) <= 4 \
                and not re.search(r"[a-z]", sm.group(2)):
            ini = sm.group(2) if sm.group(2).endswith(".") else sm.group(2) + "."
            name = f"{ini} {sm.group(1)}"                       # "Toledo-Padilla H" -> "H. Toledo-Padilla"
        out.append([name, nums, m.group(3) == ";"])
    return out


def _e26_layout_lines(layout_text):
    """[(page, line)] with trailing page numbers and photo credits removed."""
    out = []
    for p, page in enumerate(layout_text.split("\f"), start=1):
        lines = page.splitlines()
        # the page number sits among the last non-blank lines (a photo credit
        # can follow it), alone or after a wide gap
        tail = [k for k, l in enumerate(lines) if l.strip()][-3:]
        for k, ln in enumerate(lines):
            if k in tail:
                ln = re.sub(r"\s{3,}\d{1,3}\s*$", "", ln)
                if re.fullmatch(r"\s*\d{1,3}\s*", ln):
                    ln = ""
            ln = ln.replace("\u00ad", "").strip()
            if ln.startswith("©"):
                ln = ""
            out.append((p, ln))
    return out


def _e26_find_title(lines, title, start):
    """Index of the line where `title` starts (first 30 normalised chars
    matched across up to 3 joined lines), searching from `start`."""
    want = _e26_norm(title)[:30]
    for i in range(start, len(lines)):
        if not lines[i][1] or _E26_SESSION.match(lines[i][1]):
            continue
        joined = "".join(_e26_norm(lines[j][1]) for j in range(i, min(i + 3, len(lines))))
        if joined.startswith(want) and _e26_norm(lines[i][1])[:12] == want[:12]:
            return i
    return None


def parse_eea2026_blocks(layout_text, raw_text):
    """One dict per agenda talk (abstract found or not): agenda fields plus
    title (booklet spelling), authors, affiliations, abstract_text, keywords,
    session, page, found."""
    agenda = parse_eea2026_agenda(raw_text)
    lines = _e26_layout_lines(layout_text)
    first = next(i for i, (_, l) in enumerate(lines) if _E26_SESSION.match(l))
    sessions = [(i, f"Day {m.group(1)} Session {m.group(2)}: {m.group(3).strip()}")
                for i, (_, l) in enumerate(lines) if (m := _E26_SESSION.match(l))]
    for a in agenda:
        a["_at"] = _e26_find_title(lines, a["title"], first)
    starts = sorted(a["_at"] for a in agenda if a["_at"] is not None)
    out = []
    for a in agenda:
        ti = a.pop("_at")
        rec = dict(a, found=ti is not None)
        if ti is None:
            out.append(rec)
            continue
        end = next((s for s in starts if s > ti), len(lines))
        # title: lines until the normalised agenda title is covered
        want, got, x = _e26_norm(a["title"]), "", ti
        while x < end and lines[x][1] and len(got) < len(want) - 1:
            if len(got) >= 0.8 * len(want) and _E26_AUTHSUP.search(lines[x][1]):
                break           # booklet title shorter than the agenda's
            got += _e26_norm(lines[x][1])
            x += 1
        title = re.sub(r"\s+", " ", " ".join(lines[y][1] for y in range(ti, x))).strip()
        # authors: first line after the title, plus continuation lines
        while x < end and not lines[x][1]:
            x += 1
        auth = [lines[x][1]] if x < end else []
        x += 1
        def namelist(l):        # unnumbered continuation: "Booth, Demian Chapman, Luke"
            chunks = [c.strip() for c in re.split(r"[,;]", l) if c.strip()]
            return (l.count(",") + l.count(";") >= 2 and not _looks_affil(l)
                    and all(len(c.split()) <= 4 for c in chunks))
        while x < end and lines[x][1] and not _E26_MARK.match(lines[x][1]) and (
                auth[-1].rstrip().endswith((",", ";", "-")) or namelist(lines[x][1]) or
                (_E26_AUTHSUP.search(lines[x][1]) and ("," in lines[x][1] or re.search(r"\d$", lines[x][1])))):
            auth.append(lines[x][1])
            x += 1
        author_raw = re.sub(r"(\w)-\s+(?=[A-ZÀ-Ý])", r"\1-", " ".join(auth))
        # paragraphs after the authors; the body starts at the first prose
        # paragraph that holds no affiliation marker
        paras, cur = [], []
        for y in range(x, end):
            s = lines[y][1]
            if _E26_SESSION.match(s):
                continue
            if s:
                cur.append(s)
            elif cur:
                paras.append(cur)
                cur = []
        if cur:
            paras.append(cur)

        def is_body(p):
            txt = " ".join(p)
            if any(_E26_MARK.match(l) for l in p):
                return False
            return (len(p) >= 2 and sum(map(len, p)) / len(p) >= 60) or (len(txt) >= 200 and txt.endswith("."))
        b0 = next((k for k, p in enumerate(paras) if is_body(p)), len(paras))
        aff_lines = [l for p in paras[:b0] for l in p]
        body_paras = paras[b0:]
        keywords = None
        if len(body_paras) >= 2:
            kw = re.sub(r"\s+", " ", " ".join(body_paras[-1])).strip()
            if len(kw) < 250 and len(body_paras[-1]) <= 2 and not re.search(r"\.\s+[A-Z]", kw) and (
                    not kw.endswith(".") or (len(kw.split()) <= 15 and re.search(r"[,;]", kw))):
                keywords = kw
                body_paras.pop()
        body = "\n\n".join(re.sub(r"\s+", " ", " ".join(p)) for p in body_paras)
        body = re.sub(r"(\w)- (\w)", r"\1-\2", body).strip()
        # affiliations: numbered when every marker line carries ONE number;
        # two-column layouts (two numbers on a line) cannot be paired reliably
        affs, two_col, num = {}, False, None
        for l in aff_lines:
            m = _E26_MARK.match(l)
            if m:
                nums = re.findall(r"\d{1,2}", m.group(0).translate(_SUP_MAP))
                if len(nums) > 1:
                    two_col = True
                num = nums[0] if nums else None
                rest = l[m.end():].strip()
                affs[num] = rest
            elif num is not None:
                affs[num] = (affs[num] + " " + l).strip()
            else:
                affs["0"] = (affs.get("0", "") + " " + l).strip()
        if two_col:
            affs = {"raw": re.sub(r"\s{2,}", " | ", " ".join(aff_lines))}
        sess = None
        for si, name in sessions:
            if si <= ti:
                sess = name
        authors, seen = [], set()
        for au in _e26_split_authors(author_raw):     # a name printed twice
            if au[0] not in seen:                      # (Klangnurak) is one author
                seen.add(au[0])
                authors.append(au)
        rec.update(title=title or a["title"], author_raw=author_raw,
                   authors=authors,
                   affiliations={k: v.strip(" ;,") for k, v in affs.items()},
                   two_column_affils=two_col, abstract_text=body,
                   keywords=keywords, session=sess, page=lines[ti][0])
        out.append(rec)
    return out


def _e26_tokens(name):
    import unicodedata
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return {t for t in re.split(r"[\s.\-]+", n) if len(t) >= 3}


def ingest_eea2026(con, layout_text, raw_text, meeting_meta):
    """Load the EEA 2026 booklet. Presenters come from the agenda's speaker
    column (a talk with two named speakers, e.g. Dedman & Tiktak, flags both);
    slot length gives presentation_type (5 min = 'lightning', else 'talk').
    Returns (n_inserted, blocks)."""
    from conf_abstracts import load, tag, names
    meta = dict(meeting_meta)
    meta.setdefault("meeting", "EEA")
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    mid = load.upsert_meeting(con, meta)
    blocks = parse_eea2026_blocks(layout_text, raw_text)
    days = {1: "Tuesday 6 October 2026", 2: "Wednesday 7 October 2026",
            3: "Thursday 8 October 2026"}
    bodies = {}
    n = 0
    for b in blocks:
        if not b["found"] or not b.get("abstract_text"):
            continue
        speakers = [s.strip() for s in re.split(r"\s*(?:&|,| and )\s*", b["speaker"]) if s.strip()]
        pres = set()
        for sp in speakers:
            st = _e26_tokens(sp)
            best = max(range(len(b["authors"])), key=lambda k: len(st & _e26_tokens(b["authors"][k][0])),
                       default=None)
            if best is not None and len(st & _e26_tokens(b["authors"][best][0])) >= min(2, len(st)):
                pres.add(best)
        inferred = not pres
        if inferred and b["authors"]:
            pres = {0}
        affs = b["affiliations"]
        authors = []
        for k, (name, nums, _semi) in enumerate(b["authors"], start=1):
            if "raw" in affs:
                aff = None                       # two-column block: pairing unreliable
            elif nums:
                aff = "; ".join(affs[x] for x in nums if affs.get(x)) or None
            else:
                aff = affs.get("0") if len(affs) == 1 else None
            authors.append(dict(full_name=names.normalise(name), position=k,
                                is_presenter=int(k - 1 in pres),
                                presenter_inferred=int(inferred and k - 1 in pres),
                                affiliation=aff, raw_author_string=b["author_raw"]))
        key = re.sub(r"\W+", "", b["abstract_text"].lower())[:400]
        dup_body = key in bodies
        bodies.setdefault(key, b["title"])
        rec = dict(title=b["title"],
                   presentation_type="lightning" if b.get("minutes") == 5 else "talk",
                   session_name=b["session"],
                   session_datetime=f"{days.get(b['day'], '')} {b['time_uk']} (UK, UTC+1)".strip(),
                   abstract_text=b["abstract_text"], keywords=b["keywords"],
                   authors=authors, society="AES", society_basis="meeting",
                   societies_explicit=None, source_page=b["page"],
                   needs_review=int(dup_body or "raw" in affs))
        rec = tag.resolve(rec, "EEA", 2026)   # EEA -> is_elasmo=1, basis=meeting
        rec.update(society="AES", society_basis="meeting")   # house convention for EEA rows
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=(SELECT COUNT(*) FROM abstracts "
                "WHERE meeting_id=?) WHERE meeting_id=?", (mid, mid))
    con.commit()
    return n, blocks


def eea2026_texts(pdf):
    import subprocess
    lay = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True,
                         text=True, check=True).stdout
    raw = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True,
                         text=True, check=True).stdout
    return lay, raw


if __name__ == "__main__":
    # cd scripts && ../venv/bin/python -m conf_abstracts.parse_eea --eea2026 [--dry-run]
    # (idempotent: insert_abstract skips titles already in the meeting)
    import argparse
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from conf_abstracts import config as C, schema
    ap = argparse.ArgumentParser()
    ap.add_argument("--eea2026", action="store_true", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db", default=str(C.DB_PATH))
    a = ap.parse_args()
    pdf = C.CONFERENCES / "2026" / "2026_EEA_AbstractBook.pdf"
    lay, raw = eea2026_texts(pdf)
    if a.dry_run:
        bl = parse_eea2026_blocks(lay, raw)
        print(f"{len(bl)} agenda talks, {sum(x['found'] for x in bl)} abstracts found")
        raise SystemExit(0)
    con = schema.create_db(a.db)
    n, bl = ingest_eea2026(con, lay, raw, C.EEA_STRUCTURED_FILES["2026_EEA_AbstractBook"] | dict(source_pdf=str(pdf)))
    print(f"inserted {n} abstracts; {len(bl)} agenda talks, "
          f"{sum(x['found'] for x in bl)} with an abstract in the booklet")
