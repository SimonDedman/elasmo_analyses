"""Export non-English abstracts for translation, and import the translations.

The original text is never replaced: title_en / abstract_text_en hold the
English, translation_by says who made it and when. The one change to the
original is the CASE of a title published in capitals: the translator returns
the title re-cased (sentence case, proper nouns and taxa kept), and the import
refuses it unless it matches the published title letter for letter, ignoring
case and spacing. (The English casing vocabulary in sentence_case.py gets
Portuguese wrong, see ingest_ebi.py.)

  export: one JSONL line per abstract, in batches:
            {"abstract_id", "language", "title", "abstract_text"?}
          abstract_text is included per --bodies (elasmo | all | none).
          English-language rows in capitals are exported for re-casing only.
  import: JSONL lines {"abstract_id", "title_cased", "title_en", "abstract_text_en"?}
          dry run unless --apply; reports accepted / refused by reason.

Usage:
  translate_abstracts.py export --meeting EBI --bodies elasmo --batch 250 --out DIR
  translate_abstracts.py import FILE.jsonl [...] --by "Claude Sonnet 5.5, 2026-10-28" [--apply]
"""
import argparse
import difflib  # noqa: F401  (used in transfer_case)
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import sentence_case  # noqa: E402


def _letters(s):
    return re.sub(r"\s+", "", s or "").upper()


def transfer_case(published, cased):
    """The published title, character for character, with the letter case of
    the translator's re-cased copy wherever the two align. Translators drop
    characters (en dashes once mis-decoded) and silently 'correct' spellings
    (GEOMÊTRICA -> GEOMÉTRICA); taking only the CASE means neither can alter
    the record. Unaligned letters keep their case unless the translator's copy
    is mostly lower case, when an unaligned capital is lowered only if it
    follows a lower-case letter in the same word."""
    import difflib
    a, b = published, cased
    out = list(a)
    sm = difflib.SequenceMatcher(None, a.upper(), b.upper(), autojunk=False)
    aligned = set()
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            if a[i + k].isalpha():
                out[i + k] = b[j + k]
                aligned.add(i + k)
    for i, ch in enumerate(a):
        if ch.isalpha() and i not in aligned and i > 0 and out[i - 1].isalpha() and out[i - 1].islower():
            out[i] = ch.lower()
    return "".join(out)


def export(con, meeting, bodies, batch, out):
    out.mkdir(parents=True, exist_ok=True)
    rows = con.execute(
        "SELECT a.abstract_id, a.language, a.title, a.abstract_text, a.is_elasmo "
        "FROM abstracts a JOIN meetings m USING(meeting_id) "
        "WHERE m.meeting=? AND a.title_en IS NULL ORDER BY a.abstract_id", (meeting,)).fetchall()
    recs = []
    for aid, lang, title, body, el in rows:
        if lang == "en" and not sentence_case.is_mostly_caps(title):
            continue                     # nothing to do
        r = dict(abstract_id=aid, language=lang, title=title)
        if lang != "en" and (bodies == "all" or (bodies == "elasmo" and el)):
            r["abstract_text"] = body
        recs.append(r)
    files = []
    for i in range(0, len(recs), batch):
        f = out / f"batch_{i // batch + 1:02d}.jsonl"
        f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs[i:i + batch]))
        files.append(f)
    n_body = sum("abstract_text" in r for r in recs)
    print(f"{meeting}: {len(recs)} to export ({n_body} with a body, "
          f"{sum(r['language'] == 'en' for r in recs)} English for re-casing only) in {len(files)} files")
    for f in files:
        print(" ", f)


def import_(con, files, by, apply):
    have = {aid: (t, b, lang) for aid, t, b, lang in con.execute(
        "SELECT abstract_id, title, abstract_text, language FROM abstracts")}
    ok, refused = [], {}
    for f in files:
        for n, line in enumerate(Path(f).read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                refused.setdefault("bad json", []).append(f"{f}:{n}")
                continue
            aid = r.get("abstract_id")
            if aid not in have:
                refused.setdefault("unknown abstract_id", []).append(aid)
                continue
            title, body, lang = have[aid]
            cased = (r.get("title_cased") or "").strip()
            if cased and _letters(cased) != _letters(title):
                r["title_cased"] = transfer_case(title, cased)
                r["_transferred"] = True
            if cased and _letters(r["title_cased"]) != _letters(title):
                refused.setdefault("re-cased title changes letters", []).append(aid)
                continue
            if lang != "en" and not (r.get("title_en") or "").strip():
                refused.setdefault("no title_en", []).append(aid)
                continue
            if r.get("abstract_text_en") is not None and not r["abstract_text_en"].strip():
                refused.setdefault("empty abstract_text_en", []).append(aid)
                continue
            ok.append(r)
    print(f"accepted {len(ok)}, with English body {sum(bool(r.get('abstract_text_en')) for r in ok)}, "
          f"case transferred onto the published characters for {sum(bool(r.get('_transferred')) for r in ok)}")
    for why, ids in refused.items():
        print(f"REFUSED {len(ids)}: {why}: {ids[:20]}")
    if not apply:
        print("dry run - nothing written (add --apply)")
        return
    for r in ok:
        aid = r["abstract_id"]
        lang = have[aid][2]
        sets, vals = [], []
        if r.get("title_cased"):
            sets.append("title=?"); vals.append(r["title_cased"].strip())
        if lang != "en":
            sets += ["title_en=?", "translation_by=?"]; vals += [r["title_en"].strip(), by]
        if r.get("abstract_text_en"):
            sets.append("abstract_text_en=?"); vals.append(r["abstract_text_en"].strip())
        con.execute(f"UPDATE abstracts SET {', '.join(sets)} WHERE abstract_id=?", vals + [aid])
    con.commit()
    print(f"applied {len(ok)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--meeting", required=True)
    e.add_argument("--bodies", choices=["elasmo", "all", "none"], default="elasmo")
    e.add_argument("--batch", type=int, default=250)
    e.add_argument("--out", type=Path, required=True)
    i = sub.add_parser("import")
    i.add_argument("files", nargs="+")
    i.add_argument("--by", required=True, help='e.g. "Machine translation from Portuguese (Claude Sonnet 5.5, 2026-10-28)"')
    i.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(str(C.DB_PATH))
    if a.cmd == "export":
        export(con, a.meeting, a.bodies, a.batch, a.out)
    else:
        import_(con, a.files, a.by, a.apply)


if __name__ == "__main__":
    main()
