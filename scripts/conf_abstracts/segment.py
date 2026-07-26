"""Split programme text into raw abstract blocks (before field extraction).

JMIH abstract book: blocks are separated by underscore rules; each block =
  <ID> <session line>
  <author line>
  <affiliation lines...>
  <Title-Case title, 1-3 lines>
  <abstract body...>
ASIH abstract book: underscore-separated; author line is "Surname, First; ...",
then title, then a single affiliation line, then body.
"""
import re

_SEP = re.compile(r"^_{15,}\s*$", re.M)
_HEADER = re.compile(r"^\s*(\d{3,4})\s+(.+)$")
_AFFIL_KW = re.compile(
    r"\b(univ|institut|department|dept\.?|museum|laborator|college|academy|"
    r"commission|survey|foundation|cent(er|re)|fisheries|noaa|ministry|school|"
    r"station|society|USA|UK|Canada|Australia|China|Brazil|Mexico|Germany|Japan)\b",
    re.I)


def _leading_digit(s: str) -> bool:
    return bool(s) and s[0].isdigit()


# a "First [M.] Last" name token, optionally with trailing superscript digits
_NAME_TOK = re.compile(r"^[A-Z][A-Za-z'\-]+(?:\s+[A-Z]\.?)*\s+[A-Z][A-Za-z'\-]+\d*$")


def _author_like(s: str) -> bool:
    """True if the line looks like an author list (skip when hunting the title)."""
    s = s.strip()
    if not s:
        return False
    if ";" in s and "," in s:          # "Surname, First; Surname, First"
        return True
    toks = [t.strip() for t in s.split(",") if t.strip()]
    if not toks:
        return False
    namey = sum(1 for t in toks if _NAME_TOK.match(t))
    # single "First Last<digit>" or a comma list that's mostly names
    return namey == len(toks) and namey >= 1


def _title_like(s: str) -> bool:
    words = [w for w in s.split() if len(w) >= 4 and w[0].isalpha()]
    if not words or len(s) < 12:
        return False
    cap = sum(1 for w in words if w[0].isupper())
    return cap / len(words) >= 0.6


def _split_body(rest):
    """Given the lines after the header, split into (author_raw, title, body)."""
    lines = [l.rstrip() for l in rest]
    while lines and not lines[0].strip():
        lines.pop(0)
    author_raw = lines.pop(0).strip() if lines else ""
    # author list may wrap onto following lines
    while lines and _author_like(lines[0].strip()):
        author_raw += " " + lines.pop(0).strip()
    # find title: first title-like line that is not an affiliation, a bare
    # leading-digit line, or another author line
    ti = None
    for i, l in enumerate(lines):
        s = l.strip()
        if not s:
            continue
        if _title_like(s) and not _AFFIL_KW.search(s) and not _leading_digit(s) \
                and not _author_like(s):
            ti = i
            break
    if ti is None:
        return author_raw, "", " ".join(x.strip() for x in lines if x.strip())
    # title may span up to 3 consecutive title-like lines
    title_lines = []
    j = ti
    while j < len(lines) and lines[j].strip() and _title_like(lines[j].strip()) \
            and not _AFFIL_KW.search(lines[j].strip()) and len(title_lines) < 3:
        title_lines.append(lines[j].strip())
        j += 1
    title = " ".join(title_lines).strip()
    body = " ".join(x.strip() for x in lines[j:] if x.strip())
    return author_raw, title, body


def _segment_jmih(text: str):
    blocks = []
    for chunk in _SEP.split(text):
        lines = chunk.splitlines()
        hi = None
        header = None
        for i, l in enumerate(lines):
            m = _HEADER.match(l)
            if m and (re.search(r"\d{4}", l) or
                      re.search(r"Session|Symposium|Talks|Award|Plenary", l, re.I)):
                hi, header = i, m
                break
        if hi is None:
            continue
        author_raw, title, body = _split_body(lines[hi + 1:])
        blocks.append(dict(
            program_number=header.group(1),
            session_line=header.group(2).strip(),
            author_raw=author_raw,
            title=title,
            abstract_text=body,
        ))
    return blocks


def _segment_asih(text: str):
    blocks = []
    for chunk in _SEP.split(text):
        lines = [l.rstrip() for l in chunk.splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        author_raw = lines[0].strip()
        # title = first title-like line after author
        ti = next((i for i, l in enumerate(lines[1:], 1)
                   if _title_like(l) and not _AFFIL_KW.search(l)), None)
        if ti is None:
            continue
        title_lines = []
        j = ti
        while j < len(lines) and _title_like(lines[j]) and not _AFFIL_KW.search(lines[j]) \
                and len(title_lines) < 3:
            title_lines.append(lines[j].strip())
            j += 1
        # skip an affiliation line if present, then body
        body_lines = lines[j:]
        if body_lines and _AFFIL_KW.search(body_lines[0]):
            body_lines = body_lines[1:]
        blocks.append(dict(
            program_number=None,
            session_line="",
            author_raw=author_raw,
            title=" ".join(title_lines).strip(),
            abstract_text=" ".join(body_lines).strip(),
        ))
    return blocks


def segment_blocks(text: str, fmt: str = "jmih_book"):
    if fmt == "asih_book":
        return _segment_asih(text)
    return _segment_jmih(text)
