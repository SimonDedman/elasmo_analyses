"""Cross-check a Fable-extracted abstract book against the SCHEDULE section of
the same book.

Why this exists: a scanned book's schedule lists every talk as
`HH:MM NNNN <Title>. <Surname I.I., ...>` — clean, complete, and produced by a
different part of the document from the abstract pages Fable reads. That makes
it a genuinely independent instrument for the extraction, not a restatement of
it: it fixes the expected abstract COUNT, and gives a reference title and author
surname set per programme number.

Reports, per book:
  - coverage      : Fable abstracts vs the schedule's numbered entries
  - title agreement: similarity distribution against the schedule title
  - author recall : fraction of schedule surnames Fable also found
  - body health   : records with a usable abstract body

Run (after a Fable extraction, before merging):
  PYTHONPATH=scripts ./venv/bin/python scripts/conf_abstracts/qa_schedule_crosscheck.py JMIH1998
"""
import argparse
import difflib
import json
import re
import statistics
import sys
from pathlib import Path

from conf_abstracts import config as C
from conf_abstracts import pdf_columns

# Where each book's schedule section lives, and how its pages are laid out.
# (book key -> pdf path resolved from the worklist; pages are 1-based inclusive)
SCHEDULE_PAGES = {
    "JMIH1998": (1, 19),
}

_ENTRY = re.compile(r'(?=(?:[0-2]?\d:[0-5]\d)\s+\d{4}\b)')
_HEAD = re.compile(r'([0-2]?\d:[0-5]\d)\s+(\d{4})\s+(.*)', re.S)
# the title runs up to the first "Surname I." author token
_AUTHOR_START = re.compile(r'(?<=[a-z\)\.\?])\.\s+(?=[A-Z][a-zA-Z\'’-]+\s+[A-Z]\.)')
_SURNAME = re.compile(r'\b([A-Z][a-zA-Z\'’-]{2,})\s+(?:[A-Z]\.\s*){1,3}')


def norm(s):
    return re.sub(r'[^a-z0-9 ]', '', (s or '').lower()).strip()


def schedule_ground_truth(pdf: Path, first: int, last: int):
    """{programme_number: (title, {surnames})} from the schedule pages."""
    text = pdf_columns.extract(pdf, first=first, last=last, fixed_gutters=None)
    text = text.replace("­", "").replace("\f", "\n")
    gt = {}
    for part in _ENTRY.split(re.sub(r'\n', ' \n', text)):
        m = _HEAD.match(part)
        if not m:
            continue
        num = int(m.group(2))
        body = re.sub(r'\s+', ' ', m.group(3)).strip()
        a = _AUTHOR_START.search(body)
        title = (body[:a.start() + 1] if a else body[:200]).strip()
        authors = body[a.end():] if a else ""
        if num in gt or len(title) <= 15:
            continue
        gt[num] = (title, {s.lower() for s in _SURNAME.findall(authors[:300])})
    return gt


def load_fable(book_key: str):
    """Every abstract from the book's Fable caches (all chunks), deduped by title."""
    wl = json.loads((C.OUT / "conf_abstracts" / "fable_worklist.json").read_text())
    out, seen = [], set()
    for w in wl:
        if w.get("book_key") != book_key and w["key"] != book_key:
            continue
        p = Path(w["cache_path"])
        if not p.exists() or p.stat().st_size < 2:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for a in (d if isinstance(d, list) else d.get("abstracts", [])):
            k = norm(a.get("title"))
            if k and k not in seen:
                seen.add(k)
                out.append(a)
    return out


def _num_of(a):
    for f in ("program_number", "programme_number", "number", "abstract_number", "id"):
        v = a.get(f)
        if v is None:
            continue
        m = re.search(r'\d{1,4}', str(v))
        if m:
            return int(m.group(0))
    return None


# Fable returns authors as [{"full_name", "affiliation", "is_presenter"}, ...].
# An earlier version of this function looked only for name/surname/family, found
# nothing, and reported 0% author recall for a set of records that in fact had
# complete author lists — the harness was wrong, not the extraction.
_NAME_KEYS = ("full_name", "name", "surname", "family", "last_name")


def _authors_of(a):
    v = a.get("authors")
    if isinstance(v, list):
        v = " ; ".join(
            x if isinstance(x, str)
            else " ".join(str(x.get(k, "")) for k in _NAME_KEYS if x.get(k))
            for x in v)
    return str(v or "")


def report(book_key: str):
    wl = json.loads((C.OUT / "conf_abstracts" / "fable_worklist.json").read_text())
    src = next((w["source_pdf"] for w in wl
                if w.get("book_key") == book_key or w["key"] == book_key), None)
    if not src:
        sys.exit(f"{book_key}: not in the worklist — run conf_fable_prep.py first")
    first, last = SCHEDULE_PAGES[book_key]
    gt = schedule_ground_truth(Path(src), first, last)
    fab = load_fable(book_key)

    print(f"=== {book_key} — schedule cross-check ===")
    print(f"source: {src}")
    print(f"schedule numbered entries : {len(gt)}  (numbers {min(gt)}-{max(gt)})")
    print(f"Fable abstracts extracted : {len(fab)}")
    if not fab:
        print("\nNo Fable cache yet — run the extraction first, then re-run this.")
        return
    print(f"coverage vs schedule      : {len(fab)/max(len(gt),1)*100:.1f}%")

    bodies = sum(1 for a in fab if len(str(a.get("abstract_text") or a.get("body") or "")) > 200)
    print(f"records with a body >200ch: {bodies} ({bodies/len(fab)*100:.1f}%)")
    withauth = sum(1 for a in fab if _authors_of(a).strip())
    print(f"records with authors      : {withauth} ({withauth/len(fab)*100:.1f}%)")

    # title agreement, matched by programme number where Fable captured one,
    # else by best fuzzy match against the unclaimed schedule titles
    by_num = {n: t for n, (t, _s) in gt.items()}
    scores, recalls, matched = [], [], 0
    pool = {n: norm(t) for n, t in by_num.items()}
    for a in fab:
        n = _num_of(a)
        t = norm(a.get("title"))
        if not t:
            continue
        if n not in by_num:
            n = max(pool, key=lambda k: difflib.SequenceMatcher(None, t, pool[k]).ratio(), default=None)
            if n is None:
                continue
        r = difflib.SequenceMatcher(None, t, pool[n]).ratio()
        if r < 0.5:
            continue
        matched += 1
        scores.append(r)
        want = gt[n][1]
        if want:
            got = _authors_of(a).lower()
            recalls.append(sum(1 for s in want if s in got) / len(want))
    if scores:
        print(f"\nmatched to a schedule entry: {matched} "
              f"({matched/max(len(gt),1)*100:.1f}% of the schedule)")
        print(f"title similarity  median {statistics.median(scores):.3f}  "
              f"mean {statistics.mean(scores):.3f}")
        for thr in (0.95, 0.90, 0.80):
            print(f"   >= {thr:.2f}: {sum(1 for s in scores if s >= thr)/len(scores)*100:5.1f}%")
    if recalls:
        print(f"author surname recall vs schedule: mean {statistics.mean(recalls)*100:.1f}%  "
              f"(fully recovered on {sum(1 for r in recalls if r >= 0.999)/len(recalls)*100:.1f}% of records)")

    # Only meaningful when the extraction actually carries programme numbers.
    # The current prompt does not ask for one, so every record matches by title
    # instead; reporting "533 numbers missing" in that case measures nothing.
    numbered = [n for n in (_num_of(a) for a in fab) if n]
    if numbered:
        missing = sorted(set(gt) - set(numbered))
        if missing:
            print(f"\nschedule numbers with no numbered Fable record: {len(missing)}"
                  f" e.g. {', '.join(map(str, missing[:15]))}")
    else:
        print("\nnote: records carry no programme number — matched by title only.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    ap = argparse.ArgumentParser()
    ap.add_argument("book", nargs="?", default="JMIH1998")
    report(ap.parse_args().book)
