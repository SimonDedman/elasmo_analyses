"""Parse the SI2026 PDF abstract book into per-ID blocks and merge bodies into
the abstracts DB (the xlsx has no body text; the 641pp PDF does).

Learned PDF structure (each abstract, delimited by a form-feed + `A-####` line):
    A-####                                   <- id (block delimiter + join key)
    <title, 1-3 lines>
    <authors: Name<superscripts>[*], ...>    <- superscript affiliation nums, * = corresponding
    1 <affiliation>                          <- numbered affiliations
    2 <affiliation>
    *Corresponding author email: <email>
    <abstract body, one or more paragraphs>
    Keywords: <comma-separated>              <- reliable block terminator
"""
import re

# id alone on a line (form-feed / whitespace tolerated around it)
_ID = re.compile(r"(?:^|\n|\f)\s*(A-\d{4})\s*(?=\n)")
_AUTHOR_LINE = re.compile(r"[A-Za-zÀ-ÿ]\d|\*")          # letter+digit superscript or *
_AFFIL_LINE = re.compile(r"^\s*\d+\s+\S")               # "1 Associació..."
_EMAIL_LINE = re.compile(r"corresponding author email", re.I)
_KW_LINE = re.compile(r"^\s*keywords:", re.I)


def _parse_block(chunk: str) -> dict:
    lines = chunk.splitlines()
    kw_i = next((i for i, l in enumerate(lines) if _KW_LINE.match(l)), None)
    em_i = next((i for i, l in enumerate(lines) if _EMAIL_LINE.search(l)), None)
    # title = leading non-empty lines up to the first author-ish line
    title_lines = []
    ai = None
    for i, l in enumerate(lines):
        s = l.strip()
        if not s:
            if title_lines:
                continue
            else:
                continue
        # stop at the author line only (superscript nums / *) — affiliations
        # come after, and titles may legitimately start with a number
        if _AUTHOR_LINE.search(s):
            ai = i
            break
        title_lines.append(s)
    title = " ".join(title_lines).strip()
    # body start: after corresponding-email line, else after last affiliation line
    if em_i is not None:
        body_start = em_i + 1
    else:
        aff_idx = [i for i, l in enumerate(lines) if _AFFIL_LINE.match(l)]
        body_start = (aff_idx[-1] + 1) if aff_idx else (ai + 1 if ai else 0)
    body_end = kw_i if kw_i is not None else len(lines)
    body = " ".join(l.strip() for l in lines[body_start:body_end] if l.strip())
    # strip stray page numbers (bare integers) that pdftotext leaves inline
    body = re.sub(r"\s+\d{1,3}\s+", " ", body).strip()
    keywords = None
    if kw_i is not None:
        kw = " ".join(lines[kw_i:]).split(":", 1)
        keywords = kw[1].strip() if len(kw) > 1 else None
        if keywords:  # strip a trailing bare page number
            keywords = re.sub(r"\s+\d{1,3}\s*$", "", keywords).strip()
    return dict(title=title, abstract_text=body or None, keywords=keywords)


def parse_si_pdf_blocks(text: str) -> dict:
    """Return {abstract_id: {title, abstract_text, keywords}}."""
    matches = list(_ID.finditer(text))
    blocks = {}
    for i, m in enumerate(matches):
        aid = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks[aid] = _parse_block(text[start:end])
    return blocks


def merge_pdf_bodies(con, pdf_text: str, meeting="SI", year=2026) -> dict:
    """Fill abstract_text/keywords for SI abstracts from parsed PDF blocks,
    matched by program_number == abstract id. Returns match stats."""
    blocks = parse_si_pdf_blocks(pdf_text)
    rows = con.execute(
        """SELECT a.abstract_id, a.program_number, a.title
           FROM abstracts a JOIN meetings m ON a.meeting_id=m.meeting_id
           WHERE m.meeting=? AND m.year=?""", (meeting, year)).fetchall()
    matched = filled = title_ok = 0
    for aid, pn, dbtitle in rows:
        blk = blocks.get(pn)
        if not blk:
            continue
        matched += 1
        if blk["abstract_text"]:
            wc = len(blk["abstract_text"].split())
            con.execute(
                "UPDATE abstracts SET abstract_text=?, length_words=?, "
                "keywords=COALESCE(keywords, ?) WHERE abstract_id=?",
                (blk["abstract_text"], wc, blk["keywords"], aid))
            filled += 1
        # sanity: does the PDF title agree with the xlsx title?
        if dbtitle and blk["title"]:
            a = re.sub(r"\W+", " ", dbtitle.lower()).strip()
            b = re.sub(r"\W+", " ", blk["title"].lower()).strip()
            if a[:40] and a[:40] in b or b[:40] in a:
                title_ok += 1
    con.commit()
    return dict(pdf_blocks=len(blocks), db_rows=len(rows), matched=matched,
                bodies_filled=filled, title_agree=title_ok)
