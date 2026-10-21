"""Sentence-case every abstract title in the DB that was typed (mostly) in capitals.

Simon, 2026-10-21: "yes to converting the other all-caps titles in the corpus".
Idempotent, so it runs at the end of run_pipeline.py and merge_fable_into_main.py:
both rebuild titles from the books, and a one-off UPDATE would be undone by the
next rebuild. The rules are in sentence_case.py; HAND_TITLES (per source module)
override where the rules get a word wrong.

Usage:
  sentence_case_titles.py              # dry run: writes the before/after CSV, changes nothing
  sentence_case_titles.py --apply      # update the titles
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts import sentence_case as SC  # noqa: E402
from conf_abstracts.ingest_jmih_cdrom import HAND_TITLES  # noqa: E402


def convert(con, apply=False, report=None):
    vocab = SC.build_vocab_con(con)
    rows = con.execute("""SELECT a.abstract_id, m.meeting, m.year, a.title, a.abstract_text
                            FROM abstracts a JOIN meetings m USING(meeting_id)""").fetchall()
    changes, skipped = [], []
    for aid, mtg, yr, title, body in rows:
        if not title or not SC.is_mostly_caps(title):
            continue
        if SC.looks_like_author_list(title):
            skipped.append((aid, mtg, yr, title))
            continue
        new = HAND_TITLES.get(title) or SC.sentence_case(title, body or "", vocab)
        if new != title:
            changes.append((aid, mtg, yr, title, new))
    if report:
        with open(report, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["abstract_id", "meeting", "year", "before", "after"])
            w.writerows(changes)
    if report:
        with open(Path(report).with_name(Path(report).stem + "_author_lists.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["abstract_id", "meeting", "year", "title_field"])
            w.writerows(skipped)
    convert.skipped = skipped
    if apply:
        con.executemany("UPDATE abstracts SET title=? WHERE abstract_id=?",
                        [(new, aid) for aid, _m, _y, _t, new in changes])
        con.commit()
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", default=str(C.OUT / "sentence_case_titles.csv"))
    a = ap.parse_args()
    con = sqlite3.connect(str(C.DB_PATH))
    ch = convert(con, a.apply, a.report)
    left = sum(1 for (t,) in con.execute("SELECT title FROM abstracts") if t and SC.is_mostly_caps(t))
    print(f"{len(ch)} capitalised titles {'converted' if a.apply else 'would be converted'}; "
          f"{len(convert.skipped)} skipped (the title field holds an author list: OCR mis-parse); "
          f"{left} mostly-capital titles in the DB now; before/after in {a.report}")
    if not a.apply:
        print("dry run - nothing written; pass --apply")


if __name__ == "__main__":
    main()
