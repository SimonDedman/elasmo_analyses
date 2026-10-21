"""Turn an ALL-CAPS title into sentence case without losing proper nouns.

Plain lowercasing would give 'rio negro', 'hemigrammus bleheri', 'inpa'. Instead
each word takes the capitalisation it is actually written with elsewhere, mid-
sentence (sentence-initial capitals say nothing):
  1. the record's own abstract body (the author's spelling of their own place
     names, genera, and acronyms), then
  2. every mixed-case title and body in the abstracts DB (`build_vocab`),
     needing at least MIN_VOTES sightings before a capital is trusted;
otherwise the word is lowercased. The first word is capitalised.

Simon, 2026-10-21: "convert any instances of all-upper-case titles to normal
sentence case".
"""
import re
import sqlite3
from collections import Counter, defaultdict

MIN_VOTES = 3
_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’][A-Za-zÀ-ÖØ-öø-ÿ]+)?")
_ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}


def is_all_caps(title):
    letters = [c for c in title or "" if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def is_mostly_caps(title):
    """Typed in capitals apart from a pasted species name ('FISHERY BIOLOGY OF
    BIGEYE THRESHER SHARK, Alopias superciliosus'): 60% or more of its words of
    three or more letters are in capitals."""
    words = [w for w in _WORD.findall(title or "") if len(w) >= 3]
    return len(words) >= 3 and sum(w.isupper() for w in words) / len(words) >= 0.6


def _mid_sentence_forms(text, into):
    """Count each word's written form, skipping sentence-initial words."""
    for sent in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        for k, m in enumerate(_WORD.finditer(sent)):
            if k == 0:
                continue
            w = m.group(0)
            if not w.isupper() or len(w) <= 6:      # all-caps runs are headings, except short acronyms
                into[w.lower()][w] += 1


def build_vocab(db_path):
    """{lowercase word: Counter(written forms)} from every mixed-case title and body."""
    vocab = defaultdict(Counter)
    con = sqlite3.connect(str(db_path))
    for title, body in con.execute("SELECT title, abstract_text FROM abstracts"):
        if title and not is_all_caps(title):
            _mid_sentence_forms(title, vocab)
        if body and not is_all_caps(body[:200]):
            _mid_sentence_forms(body, vocab)
    con.close()
    return vocab


_TAXON_SUFFIX = re.compile(r"(?:idae|inae|iformes|oidea|oidei)$", re.I)


def _choose(word, local, vocab):
    """(form, had_evidence)."""
    lw = word.lower()
    if word in _ROMAN:
        return word, True
    if _TAXON_SUFFIX.search(lw):            # family/order names, misspelt ones included
        return lw[:1].upper() + lw[1:], True
    for source, need in ((local, 1), (vocab, MIN_VOTES)):
        forms = source.get(lw)
        if not forms:
            continue
        lower_n = forms.get(lw, 0)
        best, n = max(((f, c) for f, c in forms.items() if f != lw), key=lambda x: x[1], default=(None, 0))
        if best and n >= need and n > lower_n:
            return best, True
        if lower_n:
            return lw, True
    return lw, False


def sentence_case(title, body="", vocab=None):
    """Sentence case for a title typed (mostly) in capitals; any other title is
    returned unchanged. Words already in mixed case are kept as typed."""
    if not is_mostly_caps(title):
        return title
    local = defaultdict(Counter)
    _mid_sentence_forms(body, local)
    vocab = vocab or {}
    toks = list(_WORD.finditer(title))
    picks = [_choose(m.group(0), local, vocab) if m.group(0).isupper() else (m.group(0), True)
             for m in toks]
    forms = [f for f, _ in picks]
    for k, (m, (f, known)) in enumerate(zip(toks, picks)):
        # an authority ('BARNARD, 1923') is a surname
        if re.match(r"\s*,?\s*\d{4}", title[m.end():]):
            forms[k] = f[:1].upper() + f[1:]
        # a word seen nowhere, beside a capitalised word, is a place name
        # ('PACHITEA River', 'Rio JAVAES'); unseen typos beside common words stay lowercase
        elif not known:
            nb = [forms[j] for j in (k - 1, k + 1) if 0 <= j < len(forms)]
            if any(x[:1].isupper() for x in nb):
                forms[k] = f[:1].upper() + f[1:]
    if forms:
        forms[0] = forms[0][:1].upper() + forms[0][1:]
    out, pos = [], 0
    for m, f in zip(toks, forms):
        out.append(title[pos:m.start()]); out.append(f); pos = m.end()
    out.append(title[pos:])
    return "".join(out)
