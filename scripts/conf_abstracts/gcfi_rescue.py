"""Settle the GCFI records the automatic fetch could not match.

fetch_gcfi_papers.py claims a paper only when the PDF's own opening lines carry
the wanted title. That is the right default, and it is also why three records in
FULLY probed volumes came back empty. Two of them turned out to be present all
along:

  v47-20  "SHARKS: OVERVIEW OF THE FISHERIES IN TRINIDAD"  — the printed title
          drops "and Tobago", so the longest common run is 37 characters against
          a threshold of 45. Author CHRISTINE CHAN A SHING corroborates it.
  v7-28   "Experimentos en el Laboratorio con Repelentes" — GCFI prints Spanish
          versions, and no amount of title matching in English will ever see one.
          Author STEWART SPRINGER corroborates it.

So a null from the matcher means "the title did not match", never "the paper is
not in the volume", and this script exists to close that gap two ways:

  --claim v-n=id   fetch one paper, OCR its first page IN FULL (the fetch keeps
                   only 160 characters), require a corroborating token to appear
                   before staging it, and record it in the state file as a hand
                   claim so it is never confused with an automatic match.

  --scan V         fetch every paper in a volume and OCR EVERY page, then report
                   which papers mention a keyword. Page 1 alone cannot answer
                   "is this paper in this volume": a third of the volume-4 PDFs
                   open mid-paragraph, so an article's title page sits inside a
                   different file than its body. This is the positive control
                   that separates "not there" from "we only looked at page 1".

Downloads are cached under outputs/gcfi_scan_cache/ so a re-run costs nothing,
and only successful fetches are cached — a cached 403 would make a transient
block permanent.
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conf_abstracts import config as C  # noqa: E402
from conf_abstracts.fetch_gcfi_papers import (  # noqa: E402
    BASE, DELAY, MISS_RUN, MAX_PAPER, OCR_LANGS, STAGING, STATE, _get, _norm, wanted,
)

CACHE = C.OUT / "gcfi_scan_cache"
OCR_DPI = 150            # a keyword needs far less resolution than a title does
OCR_WORKERS = 4


def _cached_get(vol, n, path):
    """The PDF bytes for one paper, from cache if we have it. None on a miss."""
    dest = CACHE / f"v{vol}" / f"gcfi_{vol}-{n}.pdf"
    if dest.exists():
        return dest.read_bytes(), "cache"
    status, body = _get(f"{BASE}/{path}/gcfi_{vol}-{n}.pdf")
    time.sleep(DELAY)
    if status == 404:
        return None, "404"
    if status != 200 or body[:4] != b"%PDF":
        return None, f"FAILED {status}"          # never cached, never a miss
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return body, "fetched"


def _page_count(pdf):
    try:
        out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True,
                             text=True, timeout=60).stdout
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        return int(m.group(1)) if m else 0
    except Exception:                                          # noqa: BLE001
        return 0


def _text_of(pdf, first=1, last=None):
    """Whole-document text: the text layer if there is a usable one, else OCR."""
    cmd = ["pdftotext", "-f", str(first)] + (["-l", str(last)] if last else []) + [str(pdf), "-"]
    try:
        txt = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    except Exception:                                          # noqa: BLE001
        txt = ""
    if len("".join(ch for ch in txt if ch.isalpha())) >= 200:
        return txt, "text"
    return _ocr(pdf, first, last or _page_count(pdf)), "ocr"


def _ocr(pdf, first, last):
    out = []
    for pg in range(first, max(first, last) + 1):
        stem = pdf.with_suffix("").with_name(f"{pdf.stem}_p{pg}")
        try:
            subprocess.run(["pdftoppm", "-f", str(pg), "-l", str(pg), "-r", str(OCR_DPI),
                            "-png", str(pdf), str(stem)], capture_output=True, timeout=180)
            png = next(iter(sorted(stem.parent.glob(stem.name + "-*.png"))), None)
            if not png:
                continue
            out.append(subprocess.run(
                ["tesseract", str(png), "stdout", "-l", OCR_LANGS],
                capture_output=True, text=True, timeout=240,
                env={**os.environ, "OMP_THREAD_LIMIT": "2"}).stdout)
            png.unlink(missing_ok=True)
        except Exception:                                      # noqa: BLE001
            continue
    return "\n".join(out)


def _fulltext_score(needle, hay):
    """How much of a title appears ANYWHERE in a whole document, 0-1.

    This exists because `_score` caps its haystack at 400 characters. That is
    right for matching a title against a PDF's opening lines, and catastrophic
    when reused against a full document: gcfi_4-32 contains "The Effect of
    Fluctuations in the Availability of / Sharks on a Shark Fishery" on line 40,
    and searching only the first 400 characters declared it absent. That one bug
    produced every "NOT FOUND in any page of this volume" verdict, so a search
    that claims to read a whole document must actually look at all of it.

    Exact substring first (cheap, and the common case). Otherwise the document
    is walked in overlapping windows, because SequenceMatcher over a 200k-char
    haystack is far too slow and its longest-match is local anyway.
    """
    if not needle or not hay:
        return 0.0
    lim = min(160, len(needle))
    probe = needle[:lim]
    if probe in hay:
        return 1.0
    # No early return on a partial prefix. Returning cut/lim the moment a 40- or
    # 60-character prefix matched both UNDER-reported the score and skipped the
    # window search entirely, so a title matching 40 characters scored 0.25, fell
    # under the 0.35 threshold, and was reported absent without ever being
    # measured. The windowed longest-match below is the actual measurement.
    best, W, STEP = 0.0, 1200, 900          # overlap so a title cannot straddle
    for start in range(0, max(1, len(hay)), STEP):
        win = hay[start:start + W]
        if len(win) < 30:
            break
        m = SequenceMatcher(None, probe, win, autojunk=False) \
            .find_longest_match(0, lim, 0, len(win))
        if m.size > best:
            best = m.size
        if best >= lim:
            break
    return best / lim


def _scan_one(args):
    pdf, keywords = args
    txt, src = _text_of(pdf)
    hits = {}
    for kw in keywords:
        for m in re.finditer(kw, txt, re.I):
            hits.setdefault(kw, []).append(txt[max(0, m.start() - 90):m.start() + 110]
                                           .replace("\n", " "))
    return pdf.name, src, _page_count(pdf), len(txt), hits


def scan(vol, keywords):
    """Every paper in a volume, every page, looking for the keywords."""
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    rec = state.get(str(vol), {})
    path = rec.get("path")
    if not path:
        print(f"v{vol}: no upload path known — run the fetch's --probe first")
        return
    known = sorted(int(k) for k in rec.get("papers", {}))
    ns = known or list(range(1, MAX_PAPER + 1))
    print(f"v{vol}: {len(ns)} papers at {path}; downloading (cached where possible)")
    pdfs, misses = [], 0
    for n in ns:
        body, how = _cached_get(vol, n, path)
        if body is None:
            print(f"  {vol}-{n}: {how}")
            if how == "404":
                misses += 1
                if not known and misses >= MISS_RUN:
                    break
            continue
        misses = 0
        pdfs.append(CACHE / f"v{vol}" / f"gcfi_{vol}-{n}.pdf")
    print(f"v{vol}: {len(pdfs)} PDFs in hand; OCR-ing every page at {OCR_DPI} dpi "
          f"({OCR_WORKERS} workers) — this is the slow part", flush=True)
    found = []
    with ProcessPoolExecutor(max_workers=OCR_WORKERS) as ex:
        for name, src, pages, chars, hits in ex.map(
                _scan_one, [(p, keywords) for p in pdfs]):
            flag = "  <<<" if hits else ""
            print(f"  {name:<22} {pages:>3}pp {src:<4} {chars:>7} chars "
                  f"{sum(len(v) for v in hits.values()):>3} hits{flag}", flush=True)
            if hits:
                found.append((name, hits))
    print(f"\n=== {len(found)} of {len(pdfs)} papers mention {keywords} ===")
    for name, hits in found:
        print(f"\n{name}")
        for kw, ctxs in hits.items():
            for c in ctxs[:4]:
                print(f"   [{kw}] ...{c}...")


def claim(vol, n, lit_id, token):
    """Stage one paper against a literature_id, after the PDF corroborates it."""
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    rec = state.setdefault(str(vol), {})
    path = rec.get("path")
    if not path:
        print(f"v{vol}: no upload path known")
        return False
    body, how = _cached_get(vol, n, path)
    if body is None:
        print(f"v{vol}-{n}: could not fetch ({how})")
        return False
    pdf = CACHE / f"v{vol}" / f"gcfi_{vol}-{n}.pdf"
    txt, src = _text_of(pdf, 1, 1)
    want = next((w for w in wanted() if w["literature_id"] == lit_id), None)
    if want is None:
        print(f"id {lit_id}: not in the wanted list")
        return False
    ok = _norm(token) in _norm(txt)
    print(f"v{vol}-{n} [{src}, {how}] -> id {lit_id}  {want['title'][:70]}")
    print(f"   corroborating token {token!r}: {'FOUND' if ok else 'ABSENT'}")
    if not ok:
        print("   REFUSED — page 1 does not corroborate the claim")
        return False
    dest = STAGING / f"gcfi_{vol}-{n}__{lit_id}.pdf"
    dest.write_bytes(body)
    rec.setdefault("papers", {})[str(n)] = dict(
        bytes=len(body), head=" ".join(txt.split())[:160], head_src=src,
        matched=lit_id, matched_by="hand", corroborated_on=token)
    STATE.write_text(json.dumps(state, indent=1))
    print(f"   STAGED {dest.name} ({len(body):,} bytes)")
    return True


def rematch(apply_changes=False):
    """Re-score every head already stored, with the corrected matcher.

    The matcher was fixed after six volumes had been declared done, and work
    declared finished by a method later found faulty is not finished, it is
    unexamined. So every stored head is re-scored rather than every volume
    re-fetched.

    This only ever REASSIGNS, never withdraws. Entries written before the fix
    hold 160 characters of a head that was matched in full, so a low score can
    mean the title simply fell outside the stored slice — gcfi_59-76 is
    correctly id 14774 and scores 0.29 on its truncated head. Comparing two
    records against the SAME stored text is safe; comparing one record against
    a threshold is not, so a low absolute score is only ever reported.
    """
    from conf_abstracts.fetch_gcfi_papers import _norm, _score
    state = json.loads(STATE.read_text())
    want = wanted()
    swaps, cands = [], []
    for vol in sorted(state, key=int):
        for n, p in sorted(state[vol].get("papers", {}).items(), key=lambda kv: int(kv[0])):
            if p.get("matched_by") == "hand":
                continue
            h = _norm(p.get("head", ""))
            if len(h) < 30:
                continue
            ranked = sorted(((_score(_norm(t["title"]), h), t) for t in want),
                            key=lambda s: -s[0])
            best, t = ranked[0]
            cur = p.get("matched")
            if cur:
                mine = next((s for s, x in ranked if x["literature_id"] == cur), 0.0)
                if t["literature_id"] != cur and best - mine >= 0.25:
                    swaps.append((vol, n, cur, t["literature_id"], mine, best,
                                  p.get("head", "")[:80]))
            elif best >= 0.75:
                cands.append((vol, n, t["literature_id"], best, t["title"][:60],
                              p.get("head", "")[:80]))
    print(f"=== WRONG PAPER: a different record fits the same text far better ({len(swaps)}) ===")
    for vol, n, cur, new_id, mine, best, head in swaps:
        print(f"  v{vol}-{n}: id {cur} scores {mine:.2f} but id {new_id} scores {best:.2f}")
        print(f"      {head}")
    print(f"\n=== unclaimed papers that now clear the threshold ({len(cands)}) ===")
    for vol, n, lid, sc, title, head in cands:
        print(f"  v{vol}-{n} -> id {lid} [{sc:.2f}]  {title}")
    if not apply_changes:
        print("\n(dry run — pass --apply to rewrite the state file and restage)")
        return
    for vol, n, cur, new_id, mine, best, head in swaps:
        state[vol]["papers"][n]["matched"] = new_id
        state[vol]["papers"][n]["note"] = f"reassigned from {cur} ({mine:.2f} -> {best:.2f})"
        src = STAGING / f"gcfi_{vol}-{n}__{cur}.pdf"
        if src.exists():
            src.rename(STAGING / f"gcfi_{vol}-{n}__{new_id}.pdf")
            print(f"  restaged gcfi_{vol}-{n}: {cur} -> {new_id}")
    for vol, n, lid, sc, title, head in cands:
        state[vol]["papers"][n]["matched"] = lid
        state[vol]["papers"][n]["note"] = f"claimed on re-match [{sc:.2f}]"
    STATE.write_text(json.dumps(state, indent=1))
    print("state file rewritten")


def stage_for_ingest(dest_dir):
    """Copy the staged PDFs out under library-convention filenames.

    ingest_pdfs.py identifies a PDF from its DOI, or from the author and year in
    its FILENAME. Our staging names carry the literature_id and nothing else, so
    every one of them would fail to match. Renaming is therefore necessary, and
    it is also a lossy round trip: the id we already know is thrown away and
    re-derived from a surname and a year.

    So this keeps the id and uses it as a CHECK. Run ingest with --check and
    confirm that the id it derives independently equals the one in
    gcfi_<vol>-<n>__<id>.pdf. Two channels agreeing is the point; the 59-80
    misfiling is what one channel on its own produces.
    """
    sys.path.insert(0, str(C.REPO / "scripts"))
    import ingest_pdfs as I
    papers = {str(p.get("literature_id") or "").replace(".0", ""): p
              for p in json.loads((C.REPO / "docs" / "papers_data.json").read_text())}
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    manifest, aside, by_name = [], [], {}
    for src in sorted(STAGING.glob("gcfi_*.pdf")):
        lit_id = src.stem.split("__")[-1]
        row = papers.get(lit_id)
        if row is None:
            print(f"  {src.name}: id {lit_id} not in papers_data.json — SKIPPED")
            continue
        name = I.build_filename({"authors": row.get("authors") or "",
                                 "year": row.get("year"),
                                 "title": row.get("title") or ""})
        # One record can legitimately have two PDFs — GCFI prints a full paper
        # and, separately, its poster abstract (id 12640 is both v55-23, 9pp,
        # and v55-120, 2pp). They build the SAME library filename, so writing
        # them in turn silently leaves whichever landed last and the count comes
        # out one short with no error anywhere. Keep the fuller document, and
        # say what was set aside rather than letting a copy vanish.
        pages = _page_count(src)
        prev = by_name.get(name)
        if prev and prev[1] >= pages:
            print(f"  {src.name}: {pages}pp — SET ASIDE, {prev[0].name} has "
                  f"{prev[1]}pp under the same library name")
            aside.append((src.name, lit_id, name, pages))
            continue
        if prev:
            print(f"  {prev[0].name}: {prev[1]}pp — SET ASIDE, {src.name} has "
                  f"{pages}pp under the same library name")
            aside.append((prev[0].name, lit_id, name, prev[1]))
            manifest[:] = [m for m in manifest if m[0] != prev[0].name]
        by_name[name] = (src, pages)
        (dest / name).write_bytes(src.read_bytes())
        manifest.append((src.name, lit_id, name))
        print(f"  {src.name}  ->  {name}  ({pages}pp)")
    if aside:
        print(f"\n{len(aside)} file(s) set aside as the shorter version of a "
              f"record that has two PDFs (paper + poster abstract):")
        for a, b, c, pg in aside:
            print(f"   {a}  ({pg}pp)  id {b}")
    out = C.OUT / "gcfi_ingest_manifest.csv"
    out.write_text("staged_name,literature_id,ingest_name\n"
                   + "".join(f'"{a}",{b},"{c}"\n' for a, b, c in manifest))
    print(f"\n{len(manifest)} file(s) in {dest}\nmanifest: {out}")
    print("NEXT: ingest_pdfs.py --check on that directory, then confirm every "
          "literature_id it reports equals the one in the manifest BEFORE the real run.")


def extent(vols=None):
    """HEAD-probe a volume's whole number range and compare it with what we read.

    Enumeration stops after MISS_RUN consecutive 404s, which is a guess about
    where a volume ends dressed up as a measurement. GCFI numbering has holes:
    v58 is missing papers 3 and 4, v57 starts at 8, v62 at 3. A hole of eight
    ends the volume early, and the run still reports "N papers seen, 0 FAILED"
    — truncation that passes every completeness test it has.

    A HEAD is cheap, so this asks for every number in the range and prints what
    EXISTS beside what was actually fetched. Papers listed as unread are papers
    that were never looked at, which is a different thing from papers with no
    shark in them.
    """
    from conf_abstracts.fetch_gcfi_papers import _head
    state = json.loads(STATE.read_text())
    for vol in (vols or sorted(state, key=int)):
        rec = state.get(str(vol), {})
        path = rec.get("path")
        if not path:
            print(f"v{vol}: no path known — skipped")
            continue
        read = {int(k) for k in rec.get("papers", {})}
        exists, fails = [], []
        for n in range(1, MAX_PAPER + 1):
            st = _head(f"{BASE}/{path}/gcfi_{vol}-{n}.pdf")
            time.sleep(0.35)
            if st == 200:
                exists.append(n)
            elif st != 404:
                fails.append((n, st))
        missed = sorted(set(exists) - read)
        ghost = sorted(read - set(exists))
        print(f"v{vol}: {len(exists)} papers exist, {len(read)} were read, "
              f"{len(missed)} NEVER LOOKED AT, {len(fails)} probe failures")
        if exists:
            print(f"   range {exists[0]}-{exists[-1]}, gaps at "
                  f"{sorted(set(range(exists[0], exists[-1]+1)) - set(exists)) or 'none'}")
        if missed:
            print(f"   UNREAD: {missed}")
        if ghost:
            print(f"   read but no longer present: {ghost}")
        if fails:
            print(f"   PROBE FAILURES (not misses): {fails}")
        rec["extent"] = exists
        rec["unread"] = missed
    STATE.write_text(json.dumps(state, indent=1))


def _tokens(text):
    """Words long enough to carry identity, accent-folded and lowercased."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return {w for w in re.findall(r"[a-z]{5,}", t)}


def crosslang(vols=None, apply_changes=False):
    """Find records whose paper is printed in a DIFFERENT LANGUAGE.

    GCFI prints many Latin American contributions in Spanish while our record
    carries the English rendering of the title, so title matching is blind to
    them however the threshold is tuned. v62-69, 62-80 and 62-81 are all in the
    volume, all wanted, and all invisible: "El Sistema de Maracaibo y su
    Importancia como Area de Criadero de Tiburones" shares almost no characters
    with "The Maracaibo System and its Importance as Shark Nursery Area".

    What DOES survive translation is the identifying vocabulary: Latin
    binomials, place names and author surnames. So candidates are scored on
    shared RARE tokens, where rare is measured against the volume itself rather
    than assumed from a stoplist — a word in most of a volume's papers
    identifies nothing, whatever language it is in.

    Nothing here is claimed on a title. Every proposal is printed with the
    evidence that produced it, and only a proposal backed by an author surname
    is auto-claimed, because a shared species name alone is a topic, not a paper.
    """
    from conf_abstracts.fetch_gcfi_papers import _norm, _score
    state = json.loads(STATE.read_text())
    papers = {str(p.get("literature_id") or "").replace(".0", ""): p
              for p in json.loads((C.REPO / "docs" / "papers_data.json").read_text())}
    want = wanted()
    claimed = {p["matched"] for v in state.values()
               for p in v.get("papers", {}).values() if p.get("matched")}
    proposals = []
    for vol in (vols or sorted(state, key=int)):
        rec = state.get(str(vol), {}).get("papers", {})
        if not rec:
            continue
        heads = {pid: _tokens(p.get("head", "")) for pid, p in rec.items()}
        df = collections.Counter(t for toks in heads.values() for t in toks)
        cap = max(2, len(heads) // 5)               # in >20% of the volume = common
        targets = [w for w in want if w["volume"] == int(vol)
                   and w["literature_id"] not in claimed]
        for w in targets:
            row = papers.get(w["literature_id"], {})
            surnames = {s for s in _tokens(str(row.get("authors") or ""))}
            title_toks = _tokens(w["title"])
            scored = []
            for pid, toks in heads.items():
                if rec[pid].get("matched"):
                    continue
                shared = {t for t in title_toks & toks if df[t] <= cap}
                names = {t for t in surnames & toks if df[t] <= cap}
                if shared or names:
                    scored.append((len(shared) + 2 * len(names), shared, names, pid))
            scored.sort(reverse=True)
            if not scored:
                print(f"  {w['literature_id']} v{vol}: no candidate shares any rare token")
                continue
            top = scored[0]
            runner = scored[1][0] if len(scored) > 1 else 0
            strong = top[0] >= 3 and top[2] and top[0] - runner >= 2
            print(f"\n  {w['literature_id']} v{vol}  {w['title'][:66]}")
            print(f"        authors: {str(row.get('authors'))[:70]}")
            for sc, shared, names, pid in scored[:3]:
                mark = "  <= PROPOSED" if (sc, shared, names, pid) == top and strong else ""
                print(f"     {sc:>2}  {vol}-{pid:<3} shared={sorted(shared)} "
                      f"authors={sorted(names)}{mark}")
                print(f"          {rec[pid]['head'][:96]}")
            if strong:
                proposals.append((vol, top[3], w["literature_id"], top[0]))
    print(f"\n=== {len(proposals)} proposal(s) carry an author surname as well as "
          f"shared vocabulary ===")
    for vol, pid, lit, sc in proposals:
        print(f"   v{vol}-{pid} -> id {lit}  (score {sc})")
    if not apply_changes:
        print("\n(dry run — pass --apply to fetch and stage these)")
        return
    for vol, pid, lit, sc in proposals:
        claim(int(vol), int(pid), lit, "")


def _text_cached(vol, n, path):
    """Whole-document text for one paper, cached on disk.

    Text is cached, not just the PDF, because OCR of a scanned volume is the
    expensive step and a re-run must not repeat it.
    """
    tdir = CACHE / f"v{vol}" / "text"
    tdir.mkdir(parents=True, exist_ok=True)
    tf = tdir / f"{n}.txt"
    if tf.exists():
        return tf.read_text(errors="replace")
    body, how = _cached_get(vol, n, path)
    if body is None:
        return ""
    pdf = CACHE / f"v{vol}" / f"gcfi_{vol}-{n}.pdf"
    txt, src = _text_of(pdf)
    tf.write_text(f"[[src={src}]]\n{txt}")
    return txt


def deepfind(vol, workers=OCR_WORKERS):
    """Search a volume's FULL TEXT for the records it still owes us.

    Page 1 answers "what is this paper called", never "is this paper in here".
    GCFI prints poster abstracts in combined sections — v55-120 is a page headed
    "Poster Session Abstracts" carrying several — so an abstract we want can sit
    on page 9 of a PDF whose head names a different paper entirely. Most of the
    records still missing are marked [Abstract], which is exactly that shape.

    Every page is therefore read, and each still-missing record is scored
    against the whole document rather than its opening lines. Results are
    printed with the surrounding text so the claim can be checked by eye.
    """
    from conf_abstracts.fetch_gcfi_papers import _norm, _score
    state = json.loads(STATE.read_text())
    rec = state.get(str(vol), {})
    path = rec.get("path")
    if not path:
        print(f"v{vol}: no path known")
        return
    nums = rec.get("extent") or sorted(int(k) for k in rec.get("papers", {}))
    claimed = {p["matched"] for v in state.values()
               for p in v.get("papers", {}).values() if p.get("matched")}
    targets = [w for w in wanted() if w["volume"] == int(vol)
               and w["literature_id"] not in claimed]
    if not targets:
        print(f"v{vol}: nothing outstanding")
        return
    print(f"v{vol}: reading {len(nums)} papers in full for {len(targets)} "
          f"outstanding record(s) — OCR where there is no text layer", flush=True)
    # Fetch SERIALLY before extracting in parallel. The workers each sleep DELAY
    # between requests, so a pool of four would put four times the intended rate
    # at the site; one process has to own the rate limit, and the expensive part
    # to parallelise is the OCR, not the download.
    todo = [n for n in nums if not (CACHE / f"v{vol}" / "text" / f"{n}.txt").exists()]
    for i, n in enumerate(todo, 1):
        _cached_get(vol, n, path)
        if i % 20 == 0:
            print(f"  ... {i}/{len(todo)} fetched", flush=True)
    print(f"  {len(todo)} fetched, extracting text", flush=True)
    texts = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_text_cached, vol, n, path): n for n in nums}
        for i, fut in enumerate(futs, 1):
            n = futs[fut]
            try:
                texts[n] = fut.result()
            except Exception as e:                                 # noqa: BLE001
                print(f"  {vol}-{n}: FAILED {type(e).__name__}", flush=True)
            if i % 20 == 0:
                print(f"  ... {i}/{len(nums)} read", flush=True)
    empty = [n for n, t in texts.items() if len(t.strip()) < 200]
    print(f"  {len(texts)} read, {len(empty)} yielded almost no text "
          f"{'(these could not be examined: ' + str(empty[:12]) + ')' if empty else ''}")
    for w in targets:
        n_t = _norm(w["title"])
        best = []
        for n, txt in texts.items():
            h = _norm(txt)
            if len(h) < 60:
                continue
            sc = _fulltext_score(n_t, h)
            if sc >= 0.35:
                i = h.find(n_t[:40])
                best.append((sc, n, i))
        best.sort(reverse=True)
        print(f"\n  {w['literature_id']}  {w['title'][:72]}")
        if not best:
            print("      NOT FOUND in any page of this volume")
        for sc, n, i in best[:3]:
            raw = " ".join(texts[n].split())
            j = raw.lower().find(w["title"][:34].lower())
            ctx = raw[max(0, j - 60):j + 190] if j >= 0 else raw[:200]
            print(f"      {sc:4.2f}  {vol}-{n}   ...{ctx}...")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", type=int, help="volume to read end to end")
    ap.add_argument("--keyword", action="append", default=[],
                    help="regex to look for (repeatable); default shark|squal|springer")
    ap.add_argument("--stage-for-ingest", metavar="DIR",
                    help="copy staged PDFs out under library-convention names")
    ap.add_argument("--deepfind", type=int, metavar="VOL",
                    help="read every page of a volume and search for the records "
                         "it still owes (finds abstracts inside combined PDFs)")
    ap.add_argument("--crosslang", action="store_true",
                    help="propose papers printed in another language, scored on "
                         "shared rare tokens (binomials, places, surnames)")
    ap.add_argument("--extent", action="store_true",
                    help="HEAD-probe every volume's full number range and report "
                         "which papers exist but were never read")
    ap.add_argument("--rematch", action="store_true",
                    help="re-score every head already in the state file with the "
                         "current matcher, and report what changes")
    ap.add_argument("--apply", action="store_true",
                    help="with --rematch, rewrite the state file and restage")
    ap.add_argument("--claim", action="append", default=[],
                    metavar="V-N=ID:TOKEN", help="stage v-n against a literature_id, "
                    "only if TOKEN appears on its first page")
    a = ap.parse_args()
    if a.claim:
        for spec in a.claim:
            vn, _, rest = spec.partition("=")
            lit_id, _, token = rest.partition(":")
            v, _, n = vn.partition("-")
            claim(int(v), int(n), lit_id, token)
    if a.stage_for_ingest:
        stage_for_ingest(a.stage_for_ingest)
    if a.deepfind:
        deepfind(a.deepfind)
    if a.crosslang:
        crosslang(apply_changes=a.apply)
    if a.extent:
        extent()
    if a.rematch:
        rematch(a.apply)
    if a.scan:
        scan(a.scan, a.keyword or [r"shark", r"squal", r"springer", r"tiburon", r"tiburón"])


if __name__ == "__main__":
    main()
