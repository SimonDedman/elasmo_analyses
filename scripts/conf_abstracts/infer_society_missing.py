"""Fill `society` for JMIH/ASIH abstracts that have a body but no session-prefix
society (Fable-extracted books carry session headings for only ~20-40% of
records). Uses the local Ollama qwen2.5:3b via llm.infer_society (fish
ASIH/NIA vs herp HL/SSAR; AES is decided by the lexicon, not the LLM).
Resumable: only rows with society IS NULL are visited. Logs to
logs/infer_society_missing.log; prints one line per 50 rows.
"""
import argparse, sqlite3, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C, llm

LOG = C.REPO / "logs" / "infer_society_missing.log"

def main():
    # A book still awaiting its Fable re-extraction is worth excluding: its
    # regex records are title stubs ("Pennsylvania", "of Campinas (UNICAMP)"),
    # the model hedges "HL|SSAR" on them, and every write is discarded when the
    # book is replaced. 2026-09-09: 3 of the first 100 rows resolved, all of
    # them JMIH 2012.  Usage: infer_society_missing.py --exclude-year 2012
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude-year", type=int, action="append", default=[],
                    help="skip a meeting year (repeatable)")
    args = ap.parse_args()
    if not llm.available():
        print("Ollama not available at", C.OLLAMA_HOST); return 2
    con = sqlite3.connect(str(C.DB_PATH))
    skip = args.exclude_year
    rows = con.execute(f"""SELECT a.abstract_id, a.title, a.abstract_text, a.is_elasmo
                          FROM abstracts a JOIN meetings m USING(meeting_id)
                          WHERE m.meeting IN ('JMIH','ASIH') AND a.society IS NULL
                            AND a.abstract_text IS NOT NULL AND length(a.abstract_text) > 50
                            {"AND m.year NOT IN (%s)" % ",".join("?" * len(skip)) if skip else ""}
                          ORDER BY a.needs_review, a.abstract_id""", skip).fetchall()
    if skip:
        print(f"excluding year(s) {skip}")
    # Clean records first. The unresolved rate tracks record QUALITY, not the
    # model: on the OCR-mangled 1997-2004 titles ("Avrorn, Ross A., *Bripnenp,
    # Kav S.") it hedges "HL|SSAR" — which is honest, since HL and SSAR are both
    # herpetology societies and content cannot say whose session a talk was in.
    # Ordering by needs_review puts the answerable rows first, so a run that is
    # cut short has done the useful part.
    total = len(rows); done = fail = 0; t0 = time.time()
    with open(LOG, "a") as fh:
        fh.write(f"START {time.strftime('%F %T')} {total} rows\n")
        for aid, title, body, is_el in rows:
            if is_el:
                soc = "AES"; conf = 1.0
            else:
                out = llm.infer_society(title or "", body or "")
                soc = out.get("society"); conf = out.get("confidence")
                if soc not in ("ASIH", "HL", "SSAR", "NIA"):
                    fail += 1; soc = None
            if soc:
                con.execute("UPDATE abstracts SET society=?, society_inferred=?, society_basis='content', confidence=COALESCE(confidence,?) WHERE abstract_id=?",
                            (soc, soc, conf, aid))
            done += 1
            if done % 50 == 0:
                con.commit()
                rate = done / (time.time() - t0)
                eta = (total - done) / rate if rate else 0
                fh.write(f"{time.strftime('%T')} {done}/{total} done, {fail} unresolved, eta {eta/60:.0f} min ({time.strftime('%H:%M', time.localtime(time.time()+eta))})\n"); fh.flush()
        con.commit()
        fh.write(f"DONE {time.strftime('%F %T')} {done}/{total}, {fail} unresolved\n")
    print(f"done {done}/{total}, unresolved {fail}")

if __name__ == "__main__":
    sys.exit(main() or 0)
