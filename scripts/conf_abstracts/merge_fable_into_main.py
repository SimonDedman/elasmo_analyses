"""Fold the Fable-extracted EEA books (conference_abstracts_fable.db) into the
main conference_abstracts.db, making one DB of record (Simon, 2026-08-25).

Idempotent: every EEA meeting in the main DB is replaced by the Fable set on
each run (the Fable DB is itself rebuilt from caches by conf_fable_merge.py).
Refreshes the exports beside both DBs afterwards.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C, schema, export  # noqa: E402

FABLE = C.REPO / "database" / "conference_abstracts_fable.db"


def merge():
    main = schema.create_db(C.DB_PATH)
    fab = sqlite3.connect(str(FABLE))
    fab.row_factory = sqlite3.Row
    old = main.execute("SELECT meeting_id FROM meetings WHERE meeting='EEA'").fetchall()
    for (mid,) in old:
        main.execute("DELETE FROM authors WHERE abstract_id IN (SELECT abstract_id FROM abstracts WHERE meeting_id=?)", (mid,))
        main.execute("DELETE FROM abstracts WHERE meeting_id=?", (mid,))
        main.execute("DELETE FROM meetings WHERE meeting_id=?", (mid,))
    mcols = [r[1] for r in fab.execute("PRAGMA table_info(meetings)") if r[1] != "meeting_id"]
    acols = [r[1] for r in fab.execute("PRAGMA table_info(abstracts)") if r[1] not in ("abstract_id", "meeting_id")]
    ucols = [r[1] for r in fab.execute("PRAGMA table_info(authors)") if r[1] not in ("author_id", "abstract_id")]
    n_m = n_a = n_u = 0
    for m in fab.execute("SELECT * FROM meetings ORDER BY year"):
        cur = main.execute(f"INSERT INTO meetings ({','.join(mcols)}) VALUES ({','.join('?'*len(mcols))})",
                           [m[c] for c in mcols])
        new_mid = cur.lastrowid; n_m += 1
        for a in fab.execute("SELECT * FROM abstracts WHERE meeting_id=?", (m["meeting_id"],)):
            cur = main.execute(f"INSERT INTO abstracts (meeting_id,{','.join(acols)}) VALUES (?,{','.join('?'*len(acols))})",
                               [new_mid] + [a[c] for c in acols])
            new_aid = cur.lastrowid; n_a += 1
            for u in fab.execute("SELECT * FROM authors WHERE abstract_id=? ORDER BY position", (a["abstract_id"],)):
                main.execute(f"INSERT INTO authors (abstract_id,{','.join(ucols)}) VALUES (?,{','.join('?'*len(ucols))})",
                             [new_aid] + [u[c] for c in ucols])
                n_u += 1
    main.execute("UPDATE meetings SET n_abstracts=(SELECT COUNT(*) FROM abstracts WHERE abstracts.meeting_id=meetings.meeting_id)")
    main.commit()
    print(f"replaced {len(old)} EEA meetings with {n_m} from Fable: {n_a} abstracts, {n_u} authors")
    tot = main.execute("SELECT COUNT(*), SUM(is_elasmo) FROM abstracts").fetchone()
    print(f"main DB now {tot[0]} abstracts / {tot[1]} elasmo")
    for base in (C.OUT, C.REPO / "database"):
        export.to_parquet_elasmo(main, str(base / "conference_abstracts_elasmo.parquet"))
        export.to_json(main, str(base / "conference_abstracts.json"))
        export.to_xlsx(main, str(base / "conference_abstracts.xlsx"))
        print(f"exports refreshed in {base}")
    main.close(); fab.close()


if __name__ == "__main__":
    merge()
