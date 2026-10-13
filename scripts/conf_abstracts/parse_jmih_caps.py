"""Parser for the flatbed rescans of the 1997-2004 JMIH abstract books, read by
`flatbed_ocr` (deskewed tesseract). First book: JMIH 2001, Penn State.

Each abstract, single column, no number:

    *COX FERNANDES, CRISTINA, LUNDBERG, JOHN G.          <- authors, small caps; * = presenter
    (CC) Morrill Science Center, ... MA 01002; (JGL) ...  <- affiliation, keyed by initials
    Tributary Effects on Electric Fish Diversity ...      <- title (bold)
    Many processes at different spatial ...               <- body
    ... confluences. (Session P-32, Monday, July 9, Penn Stater, Deans Hall)

Tesseract renders the small caps as CAPITALS, which makes the author line a
reliable anchor; the closing "(Session ...)" note is the second one. A record
starts at an author line, or at the first line after a closed note when the
author line is too mangled to recognise (flagged, then repaired by hand below).

Instruments that check a parse (see `qa`): the book's own author index (every
surname with its page, printed separately from the abstracts) and the session
notes (one per abstract). Titles were also checked against the scanner's bold
title text, a different OCR engine plus a font cue.
"""
import re

HDR = re.compile(r"(Meetings|ASI[HT]|AS1H|ASH/|/AES)", re.I)
PNUM = re.compile(r"^[\W_]*\d{1,3}[\W_]*$")
NOTE = re.compile(r"\(\s*(?:Poster\s+)?Session\b", re.I)
DAYS = re.compile(r"(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,|Penn Stater|July \d")
ADDR = re.compile(r"\b\d{4,6}\b|\b[A-Z]{2}\s*\d{4,5}|^\(|;|\b(Univ|Dept|Department|Institut|"
                  r"Museum|Laborator|College|Box|Street|St\.|Ave|Road|Drive|Hall|Center|Centre|"
                  r"Building|USA|Canada|Mexico|Brazil|Japan|Australia|Germany|Chile)\b")
_PLACES = ("USA|U\\.S\\.A\\.|Canada|M[eé]xico|Brazil|Japan|Australia|Germany|Chile|Switzerland|"
           "U\\.K\\.|England|Scotland|France|Spain|Italy|Venezuela|Colombia|Argentina|Peru|Africa|"
           "Zealand|China|Taiwan|Korea|India|Israel|Norway|Sweden|Denmark|Netherlands|Belgium|"
           "Portugal|Panama|Rico|Cuba|Philippines|Indonesia|Malaysia|Thailand|Kenya|Tanzania|"
           "Malawi|Uganda|Austria|Finland|Ecuador|Bolivia|Uruguay|Paraguay|Belize|Guatemala|"
           "Honduras|Nicaragua|Bahamas|Ethiopia|Russia|Antilles|UK")
# a line that closes an address: postcode or country at its end
ADDR_END = re.compile(r"(\d{4,6}|[A-Z]{2}\s*\d{4,5}|[A-Z]\d[A-Z]\s*\d[A-Z]\d|" + _PLACES + r")\W*$")
AUTH = re.compile(r"\*?\s?([A-Z][A-Za-z'’\-]+(?:[ -][A-Z][A-Za-z'’\-]+)*),\s+[A-Z]")
NOTE_TAIL = re.compile(r"[\s(=®\W]*\(?\s*((?:Poster\s+)?Session\s+[\dP][^()]*)\)?\W*$", re.I)
SUFFIX = re.compile(r"^(JR|SR|II|III|IV)\.?$", re.I)


def _letters(s):
    return [c for c in s if c.isalpha()]


def author_pos(s, anywhere=False):
    """Index where an author list starts in s, or None. Small caps OCR as
    capitals, but not always ("HuBBS", "DaviD", "Cole, KATHLEEN S."), so the
    test is on the next 80 characters (>= 60% capitals), not the surname."""
    for m in AUTH.finditer(s):
        if not anywhere and m.start() > 25:
            break
        sur = _letters(m.group(1))
        tail = s[m.start():]
        lt = _letters(tail[:80])
        if (len(sur) >= 2 and sur[0].isupper()
                and lt and sum(c.isupper() for c in lt) / len(lt) >= 0.6
                and not NOTE.search(tail)):
            st = m.start()
            if s.lstrip().startswith("(") or s[:st].rstrip().endswith("("):
                return None       # "(CFJ, LUN, HLP) ..." is an affiliation key
            if re.search(r"\d", s[:st + 30]):
                return None       # "A316 EMS, UCSC, ...": names carry no digits
            return st - 1 if st and s[st - 1] == "*" else st
    return None


def _clean_author(s, pos=0):
    toks = s[pos:].strip().split()
    while toks and any(c.islower() for c in toks[-1]) and not toks[-1].startswith(("Jr", "Sr")):
        toks.pop()            # trailing binding debris: "eal ge 4"
    while toks and not re.search(r"[A-Za-z]", toks[-1]):
        toks.pop()
    return " ".join(toks)


def load_lines(text):
    """(book page, line) pairs, running heads, page numbers and debris removed."""
    parts = re.split(r"\f=== PAGE (\d+) ===\n", text)[1:]
    out = []
    # short lines worth keeping: a note's tail "208, 9:15)", a postcode line "MI 48109"
    keep_short = lambda s: (NOTE.search(s) or re.search(r"\d\)\W*$", s)
                            or re.search(r"\d{4,}|^[A-Z]{2}$", s))
    for num, body in zip(parts[0::2], parts[1::2]):
        for ln in body.splitlines():
            s = ln.strip()
            if len(s) < 40 and (HDR.search(s) or PNUM.match(s)):
                continue
            s = re.sub(r"\S*([a-z])\1{3,}\S*|\S*[acemns]{18,}\S*", "", s).strip()  # rules read as 'aaaa'
            if s and len(_letters(s)) < 3 and not keep_short(s):
                continue
            s = re.sub(r"^(?:[^\w(*\s]+\)?\s+|\|\s*)+", "", s)     # debris at line start: "=) ", "| "
            s = re.sub(r"(?:\s+[^\w\s)]+)+$", "", s)                # ... and at line end
            out.append((int(num), s))
    return out


def parse_blocks(text, first_page, last_page):
    lines = [(p, s) for p, s in load_lines(text) if first_page <= p <= last_page]
    starts, cut, forced, cont = [], {}, set(), {}
    last_nb = -1
    after_note, in_note, note_at = True, False, -1
    for i, (_, s) in enumerate(lines):
        if not s:
            continue
        pos = author_pos(s, anywhere=after_note)
        if (pos is not None and starts and last_nb == starts[-1] + cont[starts[-1]]
                and not re.search(r"\d", s) and not ADDR.search(s)):
            cont[starts[-1]] += i - last_nb          # author list wrapped onto a 2nd line
        elif pos is not None:
            starts.append(i); cut[i] = pos; cont[i] = 0
            after_note = in_note = False
        elif (after_note and starts and i > starts[-1] + 3 and len(_letters(s)) >= 6
              and "," in s[:40] and not NOTE.search(s) and not DAYS.search(s)):
            # a note closed the last abstract but this author line is too mangled
            # to recognise ("smits, w.L."): start a record anyway, flagged
            starts.append(i); cut[i] = 0; cont[i] = 0; forced.add(i)
            after_note = in_note = False
        elif NOTE.search(s) or in_note:
            if NOTE.search(s):
                note_at = i
            tail = s[NOTE.search(s).start():] if NOTE.search(s) else s
            if ")" in tail:
                after_note, in_note = True, False
            elif i - note_at > 3:          # never closed: a ")" further on is not its end
                after_note, in_note = False, False
            else:
                after_note, in_note = False, True
        last_nb = i

    recs = []
    for k, i in enumerate(starts):
        block = lines[i:starts[k + 1] if k + 1 < len(starts) else len(lines)]
        authors = [_clean_author(block[0][1], cut[i])]
        authors += [_clean_author(s) for _, s in block[1:cont[i] + 1] if s]
        nb = [s for _, s in block[cont[i] + 1:] if s]
        if not nb:
            continue
        width = max(len(s) for s in nb)
        long_ = lambda s: len(s) >= 0.8 * width

        def affil_cont(prev, nxt):
            if NOTE.search(nxt):
                return False
            if nxt[:1] == "(":
                return True                                   # next affiliation key
            if re.search(r",\s*$|\)\s*\d{1,5}\s*$", prev):
                return True                                   # address runs on
            if ADDR_END.search(prev):
                return False                                  # previous line closed an address
            if nxt[:1].islower():
                return True                                   # word wrapped mid-line
            return ((long_(prev) and bool(ADDR.search(nxt) or ADDR_END.search(nxt)))
                    or bool(ADDR_END.search(nxt) and ADDR.search(nxt)))

        idx, affil = 1, [nb[0]]
        while idx < len(nb) - 1 and affil_cont(nb[idx - 1], nb[idx]):
            affil.append(nb[idx]); idx += 1
        title = []
        if idx < len(nb):
            title.append(nb[idx]); idx += 1
            # a full-width title wraps once; its remainder is a short line
            if idx < len(nb) - 1 and long_(nb[idx - 1]) and not long_(nb[idx]):
                title.append(nb[idx]); idx += 1
        body = re.sub(r"(\w)- (\w)", r"\1\2", " ".join(nb[idx:]))
        body = re.sub(r"\s+", " ", body).strip()
        note, m = None, None
        for m in re.finditer(r"\(\s*(?:Poster\s+)?Session\b", body, re.I):
            pass
        if m and len(body) - m.start() < 140:
            note, body = body[m.start():].strip(), body[:m.start()].strip()
        recs.append(dict(page=block[0][0], author_raw=" ".join(authors),
                         affiliation=" ".join(affil), title=" ".join(title).strip(),
                         abstract_text=body, session_note=note, forced_start=i in forced))
    return recs


def _clean_title(t):
    t = re.sub(r"^(?:[^\w\s]+\s+|\w{1,2}\)\s+|[=>»®]+\s*)+", "", t).strip()
    t = re.sub(r"\s+[-_—=~|«]+$", "", t).strip()
    return re.sub(r"(\s+[^\sAa])+$", "", t).strip()          # single-character binding debris


# ---------------------------------------------------------------------------
# Per-book knowledge. Everything below is specific to one printed book.
BOOKS = {
    ("JMIH", 2001): dict(
        first_book_page=24,            # PDF page 1 = book pp. 24-25 (front matter not scanned)
        abstract_pages=(44, 137),      # pp. 24-43 schedule, 138-142 author index, 143 floor plan
        index_pages=(138, 142),
        location_city="University Park, PA",     # as the phone-scan meeting row had it
        # Session headers from the schedule, pp. 24-43, read 2026-10-13. 'society'
        # is what the header prints; symposia print none, except where the
        # subject is elasmobranchs (16, 26: AES-sponsored).
        sessions={
            "1": ("Plenary: Introduction and Distinguished Lectures", None),
            "2": ("ASIH symposium: Speciation in Fishes, Reptiles, and Amphibians", "ASIH"),
            "3": ("AES: Fisheries and Populations", "AES"),
            "4": ("ASIH: Ecology I", "ASIH"),
            "5": ("ASIH: Reproduction and Parasitology", "ASIH"),
            "6": ("Symposium: Ecology and Behavior of Cichlid Fishes of Great Lakes of Africa, Part One", None),
            "7": ("AES: Behavior and Ecology", "AES"),
            "8": ("ASIH: Ecology II", "ASIH"),
            "9": ("ASIH: Systematics-Morphology I", "ASIH"),
            "10": ("AES: Movements, Systematics and Biology", "AES"),
            "11": ("ASIH: Behavior I", "ASIH"),
            "12": ("ASIH: Systematics-Genetics I", "ASIH"),
            "13": ("ASIH: Behavior II", "ASIH"),
            "15": ("Symposium: Ecology and Behavior of Cichlid Fishes of Great Lakes of Africa, Part Two", None),
            "16": ("Symposium: Nonfisheries-Related Human Impact on Elasmobranchs", "AES"),
            "17": ("ASIH: Feeding Ecology", "ASIH"),
            "18": ("ASIH: Systematics-Morphology II", "ASIH"),
            "19": ("ASIH: Physiology I", "ASIH"),
            "20": ("AES: Immunology, Biochemistry, and Physiology", "AES"),
            "21": ("ASIH: Conservation I", "ASIH"),
            "22": ("ASIH: Ecology III", "ASIH"),
            "23": ("ASIH: Molecular Systematics I", "ASIH"),
            "25": ("Symposium: Ecology and Behavior of Cichlid Fishes of Great Lakes of Africa, Part Three", None),
            "26": ("Symposium: From Icons to Art: The Cultural Significance of Sharks and Man", "AES"),
            "27": ("ASIH: Ecology IV", "ASIH"),
            "28": ("ASIH: Molecular Systematics II", "ASIH"),
            "29": ("ASIH: Morphology-Histology I", "ASIH"),
            "30": ("ASIH: Conservation II", "ASIH"),
            "33": ("Symposium: Evolutionary and Conservation Biology of the Pupfishes", None),
            "34": ("ASIH: Ecology V", "ASIH"),
            "35": ("ASIH: Molecular Systematics III", "ASIH"),
            "36": ("ASIH: Phylogeography", "ASIH"),
            "37": ("ASIH: Biodiversity I", "ASIH"),
            "38": ("ASIH: Conservation II", "ASIH"),      # printed "II" twice (30 and 38)
            "39": ("Biodiversity II", None),
            "P-14": ("Poster Session 14", None),
            "P-24": ("Poster Session 24", None),
            "P-32": ("Poster Session 32", None),
        },
        # Hand repairs, read off the page image (IMG), the scanner's bold title
        # text (BOLD) or its text layer (LAYER), 2026-10-13. Each is found by a
        # phrase from the abstract's own body, never by an OCR spelling, so a
        # re-OCR that reads a name differently still lands on the right record.
        #   author / affiliation / title : replace that field
        #   mode 'body_head'     : the record's "title" is the body's first line,
        #                          because the real title ran into the affiliation
        #                          (cut there at the `affil_cut` regex)
        #   mode 'title_in_body' : the real title is the body's first sentence
        #   body_cut             : regex removed from the start of the body
        fixes=[
            dict(page=61, needle="Incorporating the effect of uncertainty", author="Cortés, Enric",
                 title="Demographic modeling under uncertainty: application to shark conservation"),  # IMG
            dict(page=67, needle="naked goby", author="*FENCIL, MEGAN C., YOUNG, JOHN, SCHULTZ, ERIC T.", title="Do depth preference and selective tidal stream transport facilitate upriver migration of larval naked goby (Gobiosoma bosc)?"),  # BOLD
            dict(page=73, needle="the Bermuda Islands", title="Taxonomic diversity, origin, and conservation status of Bermuda killifishes (Fundulus) based on mitochondrial cytochrome b phylogenies"),  # BOLD
            dict(page=75, needle="Charleston, South Carolina is surrounded", title="Contaminants in Sharks of the South Atlantic Bighty: An Assessment of Pesticides and PCBs in Shark Livers as an Environmental Risk"),  # BOLD; "Bighty" as printed, both engines agree
            dict(page=81, needle="Starvation is often implicated", title="Interannual variation in energy cycling during the first year of life of Hudson River striped bass"),  # BOLD
            dict(page=85, needle="Prior to the opening of public aquariums", author="Koob, Thomas J."),  # IMG
            dict(page=97, needle="Speciation is generally understood", body_cut=r"^.*?Cichlid Fishes\W*",
                 affiliation="(FAM, CR, MT) University Plain, University of East Anglia, Norwich, Norfolk NR4 7TJ UK; (GT, OS) Highfield, University of Hull, Hull HU6 7RX UK",
                 title="Testing for Sympatric Parallel Speciation through Sexual Selection in Lake Victoria Cichlid Fishes"),  # IMG
            dict(page=97, needle="Fishes of Alaska is a guide", title="Fishes of Alaska: The book"),  # BOLD
            dict(page=107, needle="acquisition of additional", title="Another look at the spinycheek sleepers (Eleotris, Teleostei) of the western Atlantic."),  # BOLD
            dict(page=112, needle="speciation modes in mbuna", author="Rico, Ciro"),  # LAYER
            dict(page=114, needle="The diet of young lemon sharks was studied", mode="body_head", affil_cut=r"\s*Diet of young lemon.*",
                 title="Diet of young lemon sharks (Negaprion brevirostris) at an isolated seamount, Atol das Rocas, Brazil."),
            dict(page=115, needle="fighting fish genus Betta (Belontiidae", mode="body_head", affil_cut=r"(?<=Republic of Singapore).*",
                 title="Molecular phylogeny of the fighting fish genus Betta: insights into the evolution of breeding behavior and Southeast Asian biogeography"),  # BOLD
            dict(page=117, needle="The nests of substrate brooding fishes", title="Breeding nests of substrate brooders as a resource for inter-specific reproductive activities among cichlids of Lakes Tanganyika and Malawi."),  # IMG
            dict(page=121, needle="Percidae (Order Perciformes)", title="Phylogenetic relationships within the Percidae based on the analysis of two mitochondrial DNA genes"),  # BOLD
            dict(page=121, needle="catostomid phylogenies disagree", mode="body_head", affil_cut=r"\s*\S*\s*of Incongruent.*",
                 title="Resolution of Incongruent Morphological, Molecular, and Paleontological Data on Phylogeny of Catostomid Fishes."),  # BOLD
            dict(page=121, needle="The cottid genus", author="Smith, W. L."),  # LAYER
            dict(page=123, needle="Ultrasonic telemetry was used to determine the movement", mode="body_head",
                 author="Steiner, Pascale A.", affiliation="Feldbergstrasse 22, Basel, Switzerland, Basel, Basel 4057 Switzerland",
                 title="The activity pattern of the two carcharhinid shark species bull shark, Carcharhinus leucas and blacktip shark, Carcharhinus limbatus, in the estuary of the Ten Thousand Islands, Florida"),  # IMG
            dict(page=127, needle="lamprologine cichlids", mode="body_head", author="Taborsky, Michael",
                 affiliation="Zoology, University of Bern, Hinterkappelen/Bern CH-3032 Switzerland",
                 title="Cichlids as a paradigm for social evolution in vertebrates"),  # LAYER
            dict(page=131, needle="Pygmy perches are small", mode="title_in_body",
                 author="*UNMACK, PETER J., HAMMER, MICHAEL, ADAMS, MARK, DOWLING, THOMAS E.",
                 title="Phylogenetic relationships, hybridisation, and biogeography within the Australian pygmy perches (Percichthyidae)."),
            dict(page=133, needle="Nitric oxide (NO) is a potent", title="Production of nitric oxide (NO) and inducible nitric oxide synthase (iNOS) by peripheral blood leukocytes from nurse sharks Ginglymostoma cirratum"),  # BOLD
            dict(page=135, needle="Laguna Chichancanab has about", title="Impact of introduced species on the endemic Cyprinodon species of Laguna Chichancanab"),  # BOLD
        ],
        # Printed entries with no body, a title and a session only (Clark Hubbs).
        title_only=("What happened on 5 July 1938",),
    ),
}


def _repair(r, book):
    hay = re.sub(r"\s+", " ", " ".join((r["author_raw"], r["affiliation"], r["title"], r["abstract_text"])))
    for f in book["fixes"]:
        if r["page"] != f["page"] or f["needle"] not in hay:
            continue
        mode = f.get("mode")
        if mode == "body_head" and f.get("affil_cut") and not re.search(f["affil_cut"], r["affiliation"]):
            mode = None          # the parse already kept the title out of the affiliation
        if mode == "body_head":
            if f.get("affil_cut"):
                r["affiliation"] = re.sub(f["affil_cut"], "", r["affiliation"]).strip()
            head = re.sub(r"^[^A-Za-z]+", "", r["title"])
            r["abstract_text"] = (head + " " + r["abstract_text"]).strip()
        elif mode == "title_in_body":
            k = r["abstract_text"].find(f["title"][:40])
            if 0 <= k < 20:
                r["abstract_text"] = r["abstract_text"][k + len(f["title"]):].strip()
        if f.get("body_cut"):
            r["abstract_text"] = re.sub(f["body_cut"], "", r["abstract_text"], count=1).strip()
        for field in ("author", "affiliation", "title"):
            if f.get(field):
                r["author_raw" if field == "author" else field] = f[field]
        r["repaired"], r["forced_start"] = mode or "fields", False


def finalise(recs, book):
    """Titles, repairs, session fields, review flags."""
    for r in recs:
        r["title"] = _clean_title(r["title"])
        _repair(r, book)
        r["needs_review"] = 0
        if r["forced_start"]:            # mangled author line with no hand repair
            r["needs_review"] = 1
        # debris at the start of a body: "D> Among", "ra Prior"
        r["abstract_text"] = re.sub(r"^(?:[^\w\s]+|[a-z]{1,2})\s+(?=[A-Z])", "",
                                    r["abstract_text"].replace("&#65279;", "")).strip()
        if not r["session_note"]:
            m = NOTE_TAIL.search(r["abstract_text"][-140:])
            if m:
                off = max(len(r["abstract_text"]) - 140, 0)
                r["session_note"] = "(" + m.group(1).strip() + ")"
                r["abstract_text"] = r["abstract_text"][:off + m.start()].strip()
            elif r["title"].startswith("(Session"):
                # title-only entry; its title was read onto the affiliation line
                r["session_note"], r["title"] = r["title"], ""
                m2 = re.search(r"\b[A-Z]{2} \d{5}\s+(.+)$", r["affiliation"])
                if m2:
                    r["title"] = m2.group(1).strip()
                    r["affiliation"] = r["affiliation"][:m2.start(1)].strip()
        title_only = any(k in r["title"] for k in book["title_only"])
        if ((len(r["abstract_text"].split()) < 25 and not title_only)
                or len(r["title"]) < 8 or not r["title"][:1].isupper()):
            r["needs_review"] = 1
        note = r["session_note"]
        if note:
            note = re.sub(r"\s*\|\s*", " ", note)
            note = note[:note.find(")") + 1] if ")" in note else note + ")"
            r["session_note"] = note
        m = re.match(r"\(\s*(?:Poster\s+)?Session\s+([^,]+?)\s*,\s*([A-Za-z]+day)?\s*,?\s*"
                     r"(July\s*\d{1,2})?", note or "")
        sid = m.group(1).replace(" ", "").upper() if m else None
        if sid and re.fullmatch(r"P\d+", sid):
            sid = "P-" + sid[1:]                      # "P24" -> "P-24"
        if sid and sid.isdigit() and "Deans Hall" in (note or "") and "P-" + sid in book["sessions"]:
            sid = "P-" + sid                          # posters hung in Deans Hall; OCR lost "P-"
        r["session_id"] = sid
        r["presentation_type"] = ("poster" if sid and sid.startswith("P") else "talk") if sid else None
        t = re.search(r",\s*(\d{1,2}[:;.]\d{2})\s*\)?\W*$", note or "")
        when = " ".join(x for x in ((m.group(2) + ",") if m and m.group(2) else None,
                                    re.sub(r"July\s*", "July ", m.group(3)) + ", 2001" if m and m.group(3) else None,
                                    t.group(1).replace(";", ":").replace(".", ":") if t else None) if x)
        r["session_datetime"] = when or None
        loc = re.search(r"(Penn Stater[^,)]*(?:,\s*(?:Room\s*\d+|[A-Z][a-z]+ Hall))?)", note or "")
        r["location"] = loc.group(1) if loc else None
    return recs


# ---------------------------------------------------------------------------
# Authors: "SURNAME, GIVEN, SURNAME, GIVEN" with a * on the presenter and
# suffixes either after the given name or between ("PRATT, JR., HAROLD L.").
def split_authors(raw):
    toks = [t.strip() for t in raw.split(",") if t.strip()]
    out = []
    i = 0
    while i < len(toks):
        sur = toks[i]; i += 1
        suffix = ""
        if i < len(toks) and SUFFIX.match(toks[i]):
            suffix = toks[i]; i += 1
        given = ""
        if i < len(toks):
            given = toks[i]; i += 1
        if i < len(toks) and SUFFIX.match(toks[i]):
            suffix = toks[i]; i += 1
        presenter = sur.startswith("*") or given.startswith("*")
        sur, given = sur.lstrip("* ").strip(), given.lstrip("* ").strip()
        m = re.match(r"(.+?)\s+(JR|SR|II|III|IV)\.?$", sur, re.I)
        if m:
            sur, suffix = m.group(1), suffix or m.group(2)
        out.append(dict(surname=sur, given=given, suffix=suffix, presenter=presenter))
    return out


def _initials(a):
    return "".join(w[0] for w in re.findall(r"[A-Za-z]+", a["given"]) +
                   re.findall(r"[A-Za-z]+", a["surname"])).upper()


def affiliations_by_author(affil, authors):
    """Map '(CFJ, LUN) addr; (SEC) addr' onto authors by their initials. An
    affiliation with no keys belongs to every author."""
    keyed = re.findall(r"\(([A-Za-z ,.]+)\)\s*([^;(]+)", affil or "")
    if not keyed:
        return [affil.strip() if affil else None] * len(authors)
    table = {}
    for keys, addr in keyed:
        for k in keys.split(","):
            table[re.sub(r"[^A-Za-z]", "", k).upper()] = addr.strip(" ;:")
    out = []
    for a in authors:
        ini = _initials(a)
        out.append(table.get(ini) or next((v for k, v in table.items()
                                           if k[:1] == ini[:1] and k[-1:] == ini[-1:]), None))
    return out


def parse_book(text, meeting, year, pdf):
    """Records for one book, repaired and surname-checked."""
    book = BOOKS[(meeting, year)]
    recs = finalise(parse_blocks(text, *book["abstract_pages"]), book)
    correct_surnames(recs, text, book, pdf)
    return recs


def ingest_jmih_caps(con, text, meeting_meta, pdf):
    """Parse a flatbed-OCR'd book and insert it. A phone-scan meeting of the
    same meeting-year is the version this replaces, so it is deleted once the
    new book has gone in. Returns (count, records)."""
    from conf_abstracts import load, tag, names, lexicon
    book = BOOKS[(meeting_meta["meeting"], meeting_meta["year"])]
    recs = parse_book(text, meeting_meta["meeting"], meeting_meta["year"], pdf)
    meta = dict(meeting_meta)
    meta.setdefault("doc_type", "abstract_book")
    meta.setdefault("parse_status", "ok")
    meta["is_ocr"] = 1
    meta.setdefault("name", f"{meta['meeting']} {meta['year']}")
    mid = load.upsert_meeting(con, meta)
    # a rerun replaces the book wholesale, so a changed parse leaves no stale rows
    con.execute("DELETE FROM authors WHERE abstract_id IN "
                "(SELECT abstract_id FROM abstracts WHERE meeting_id=?)", (mid,))
    con.execute("DELETE FROM abstracts WHERE meeting_id=?", (mid,))
    n = 0
    for r in recs:
        sess_name, society = book["sessions"].get(r["session_id"], (None, None))
        authors = split_authors(r["author_raw"])
        affs = affiliations_by_author(r["affiliation"], authors)
        if not any(a["presenter"] for a in authors) and authors:
            authors[0]["presenter_inferred"] = True
        rec = dict(
            program_number=None,
            title=r["title"] or None,
            abstract_text=r["abstract_text"] or None,
            presentation_type=r["presentation_type"],
            session_name=(f"Session {r['session_id']}: {sess_name}" if sess_name
                          else (f"Session {r['session_id']}" if r["session_id"] else None)),
            societies_explicit=[society] if society else [],
            award=None, society_inferred=None,
            session_datetime=r["session_datetime"], location=r["location"],
            keywords=None, confidence=0.6 if r["needs_review"] else 0.95,
            needs_review=r["needs_review"], source_page=r["page"],
            authors=[dict(full_name=names.normalise(
                              ", ".join(x for x in (a["surname"], a["given"], a["suffix"]) if x)),
                          position=k + 1, is_presenter=int(a["presenter"] or a.get("presenter_inferred", False)),
                          presenter_inferred=int(bool(a.get("presenter_inferred"))),
                          affiliation=aff, affiliation_country=None,
                          raw_author_string=r["author_raw"])
                     for k, (a, aff) in enumerate(zip(authors, affs))],
        )
        rec = tag.resolve(rec, meta["meeting"], meta["year"])
        # a shark talk in an ASIH session or symposium: the lexicon decides
        if not rec["is_elasmo"] and lexicon.is_elasmo_text(rec["title"] or "", rec["abstract_text"] or ""):
            rec["is_elasmo"], rec["elasmo_basis"] = 1, "content"
        if load.insert_abstract(con, mid, rec):
            n += 1
    con.execute("UPDATE meetings SET n_abstracts=? WHERE meeting_id=?", (n, mid))
    old = [row[0] for row in con.execute(
        "SELECT meeting_id FROM meetings WHERE meeting=? AND year=? AND meeting_id<>? "
        "AND source_pdf LIKE '%\\_phonescan%' ESCAPE '\\'",
        (meta["meeting"], meta["year"], mid))]
    for oid in old:
        con.execute("DELETE FROM authors WHERE abstract_id IN "
                    "(SELECT abstract_id FROM abstracts WHERE meeting_id=?)", (oid,))
        con.execute("DELETE FROM abstracts WHERE meeting_id=?", (oid,))
        con.execute("DELETE FROM meetings WHERE meeting_id=?", (oid,))
    con.commit()
    return n, recs


# ---------------------------------------------------------------------------
def _fold(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def index_entries(text, book):
    """(surname as printed in the index, {pages}) from the book's author index."""
    lo, hi = book["index_pages"]
    parts = re.split(r"\f=== PAGE (\d+) ===\n", text)[1:]
    idx = " ".join(b for p, b in zip(parts[0::2], parts[1::2]) if lo <= int(p) <= hi)
    idx = re.sub(r"\n(?=\d)", " ", idx)
    entry = re.compile(r"([A-Z][A-Za-z'\u2019\-]+(?: [A-Z][A-Za-z'\u2019\-]+)?)[,.]\s*[A-Z][^,\n]{0,25}?"
                       r"[,.]\s*((?:\d{2,3}\s*[,.]?\s*)+)")
    out = {}
    for m in entry.finditer(idx):
        out.setdefault(m.group(1), set()).update(int(n) for n in re.findall(r"\d{2,3}", m.group(2)))
    return out


def correct_surnames(recs, text, book, pdf):
    """Two-of-three vote on each surname. Our OCR is one reading; the author
    index (printed apart, OCR'd apart) is a second; the scanner's own text
    layer for that spread is a third. Where our surname is not in the index, an
    index surname listed for that page is a near match (ratio >= 0.8) AND the
    scanner layer has the index spelling but not ours, take the index spelling
    ("SIOSS"/Sloss, "PENCIL"/Fencil). The third vote matters: the index reading
    is incomplete, and without it ANDRASO became ANDERSON and NEAR became NER.
    Returns [(page, old, new)]."""
    import difflib
    import subprocess
    layer = {}

    def scanner_text(book_page):
        pdf_page = (book_page - book["first_book_page"]) // 2 + 1
        if pdf_page not in layer:
            layer[pdf_page] = _fold(subprocess.run(
                ["pdftotext", "-f", str(pdf_page), "-l", str(pdf_page), str(pdf), "-"],
                capture_output=True, text=True).stdout)
        return layer[pdf_page]
    entries = index_entries(text, book)
    known = {_fold(k) for k in entries}
    changed = []
    for r in recs:
        out = []
        for a in split_authors(r["author_raw"]):
            sur = a["surname"]
            if _fold(sur) not in known:
                cands = [k for k, pages in entries.items()
                         if pages & {r["page"], r["page"] + 1}]
                best = max(cands, key=lambda k: difflib.SequenceMatcher(None, _fold(k), _fold(sur)).ratio(),
                           default=None)
                lay = scanner_text(r["page"]) if best else ""
                if (best and difflib.SequenceMatcher(None, _fold(best), _fold(sur)).ratio() >= 0.8
                        and re.search(r"\b" + re.escape(_fold(best)) + r"\b", lay)
                        and not re.search(r"\b" + re.escape(_fold(sur)) + r"\b", lay)):
                    changed.append((r["page"], sur, best.upper()))
                    sur = best.upper()
            name = ", ".join(x for x in (("*" if a["presenter"] else "") + sur, a["given"], a["suffix"]) if x)
            out.append(name)
        r["author_raw"] = ", ".join(out)
    return changed


def qa_author_index(text, recs, book):
    """Fraction of the book's author-index (surname, page) pairs found among the
    parsed authors on that page or the one before. The index is printed apart
    from the abstracts, so it is an independent count. It is two-column, and a
    wrapped page list can land on a neighbouring entry, so treat it as a floor."""
    import unicodedata
    fold = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s)
                             if not unicodedata.combining(c)).lower()
    lo, hi = book["index_pages"]
    parts = re.split(r"\f=== PAGE (\d+) ===\n", text)[1:]
    idx = " ".join(b for p, b in zip(parts[0::2], parts[1::2]) if lo <= int(p) <= hi)
    idx = re.sub(r"\n(?=\d)", " ", idx)
    entry = re.compile(r"([A-Z][A-Za-z'’\-]+(?: [A-Z][A-Za-z'’\-]+)?)[,.]\s*[A-Z][^,\n]{0,25}?"
                       r"[,.]\s*((?:\d{2,3}\s*[,.]?\s*)+)")
    a0, a1 = book["abstract_pages"]
    pairs = {(fold(m.group(1)), int(n)) for m in entry.finditer(idx)
             for n in re.findall(r"\d{2,3}", m.group(2)) if a0 <= int(n) <= a1}
    bypage = {}
    for r in recs:
        bypage.setdefault(r["page"], []).append(fold(r["author_raw"]))
    miss = [(pg, s) for s, pg in sorted(pairs, key=lambda x: (x[1], x[0]))
            if not any(s in a for a in bypage.get(pg, []) + bypage.get(pg - 1, []))]
    return len(pairs), len(pairs) - len(miss), miss
