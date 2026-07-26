"""Parse a JMIH/ASIH session line into structured fields.

Handles three society signals seen in the data:
  - colon-delimited prefix:  "HL, ASIH, SSAR: Eco-Evolutionary ... Symposium"
  - single-token prefix:     "AES Sawfishes Symposium"
  - award suffix:            "... Friday 8 July 2016; AES CARRIER"
"""
import re
from conf_abstracts.config import SOCIETIES

_SOC = "|".join(sorted(SOCIETIES, key=len, reverse=True))
# award suffix: "; <SOC> <AWORD...>" at end of line
_AWARD = re.compile(r";\s*(" + _SOC + r")\s+([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+)*)\s*$")
# colon prefix: "SOC[, SOC]*:"
_COLON = re.compile(r"^\s*((?:" + _SOC + r")(?:\s*,\s*(?:" + _SOC + r"))*)\s*:\s*")
# single leading society token
_LEAD = re.compile(r"^\s*(" + _SOC + r")\b")
# a date like "Sunday 10 July 2016" or "10 July 2016"
_DATE = re.compile(
    r"((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+)?\d{1,2}\s+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
    re.I,
)

_TYPE_KEYWORDS = [
    ("poster", "poster"),
    ("lightning", "lightning"),
    ("plenary", "plenary"),
    ("keynote", "keynote"),
    ("symposium", "symposium"),
]


def _presentation_type(session_name: str) -> str:
    low = session_name.lower()
    for kw, t in _TYPE_KEYWORDS:
        if kw in low:
            return t
    return "talk"


def parse_session_line(line: str) -> dict:
    """Return session_name, societies_explicit(list), award, presentation_type,
    session_datetime, location."""
    raw = line.strip()
    societies, award = [], None

    # 1. award suffix
    m = _AWARD.search(raw)
    if m:
        soc = m.group(1)
        award = f"{soc} {m.group(2)}".strip()
        societies.append(soc)
        raw = raw[: m.start()].rstrip(" ;")

    # 2. date (search anywhere; take last match)
    session_datetime = None
    dm = list(_DATE.finditer(raw))
    if dm:
        session_datetime = dm[-1].group(0).strip()

    # 3. comma split -> name / location / (date already captured)
    #    drop the trailing date part from the comma list
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if session_datetime and parts and session_datetime.lower() in parts[-1].lower():
        parts = parts[:-1]
    location = parts[-1] if len(parts) >= 2 else None
    name_part = parts[0] if parts else raw

    # 4. society prefix on the name part
    cm = _COLON.match(raw)
    if cm:
        for tok in re.split(r"\s*,\s*", cm.group(1)):
            if tok and tok not in societies:
                societies.append(tok)
        session_name = raw[cm.end():].split(",")[0].strip()
    else:
        lm = _LEAD.match(name_part)
        if lm and lm.group(1) not in societies:
            societies.append(lm.group(1))
        session_name = name_part

    return dict(
        session_name=session_name,
        societies_explicit=societies,
        award=award,
        presentation_type=_presentation_type(session_name),
        session_datetime=session_datetime,
        location=location,
    )
