#!/usr/bin/env python3
"""Suggest new keywords for a topic-review rule by contrasting IN and OUT papers.

Offline half of "the optimiser should suggest new keywords". Reads only the text of
labelled papers from outputs/topic_review/text_cache.sqlite (never the whole corpus),
scores unigrams and bigrams by the weighted log-odds ratio with an informative
Dirichlet prior (Monroe, Colaresi & Quinn 2008, "Fightin' Words"), and writes a review
workbook plus a JSON file under outputs/topic_review/<topic>/suggestions/.

Labels: --labels export.json [...] (dashboard export; inspected labels only unless
--include-bulk) or --fable (Fable silver labels from seed_labels.js, a stand-in).

Usage:
  ./venv/bin/python scripts/suggest_topic_terms.py --fable
  ./venv/bin/python scripts/suggest_topic_terms.py --labels a.json b.json --rule d_fisheries
"""
import argparse, datetime, json, math, re, sqlite3, sys, time, zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "outputs" / "topic_review" / "text_cache.sqlite"

# Standard English stopwords plus scientific-paper furniture. Junk classes that would
# otherwise dominate (citation/layout words, journal furniture) are listed in EXTRA.
BASE_STOP = set("""a about above across after again against all almost also although always am among an and any are as at be
because been before being below between both but by can cannot could did do does doing down during each either else
etc few for from further had has have having he her here hers herself him himself his how however i if in into is it
its itself just may me might more most much must my myself no nor not of off often on once one only or other our ours
ourselves out over own per rather same shall she should since so some such than that the their theirs them themselves
then there these they this those through thus to too under until up upon us very via was we were what when where whether
which while who whom whose why will with within without would yet you your yours two three four five six first second
third three four several many various using used use based within among thereby therefore whereas whilst
""".split())
EXTRA = set("""fig figs figure figures table tables et al doi pp vol eds ed suppl supplementary appendix http https www com org
pdf copyright elsevier springer wiley journal press university department received accepted published available online
corresponding author authors email email@ ltd inc cambridge oxford taylor francis plos pone sci res mar biol ecol
doi.org supporting information data set sets study studies result results show shown showed found however paper
""".split())
# generic academic prose that no reviewer would make a keyword or anchor
ACADEMIC = set("""high higher highest low lower lowest due similar different difference differences number numbers size sizes
reported report reports following followed follow well large larger largest small smaller smallest known present presented presence
time times along likely unlikely potential potentially collected collection important importance less given length lengths provide
provided provides compared compare comparison comparisons limited limit limits associated association particularly despite including
include included includes total totals observed observation observations analysis analyses research study studies result results
based used use using show showed shown shows found find findings suggest suggests suggested indicate indicates indicated increase
increased increases increasing decrease decreased decreases decreasing significant significantly significance mean means range ranges
within between among across over under per approximately respectively however therefore thus although whereas further additional
addition general generally overall several various specific specifically previous previously recent recently current currently
available data information approach approaches method methods model models value values level levels rate rates area areas region
regions period periods year years day days month months first second third two three four five six ten one new old main major minor
possible possibly obtained estimated estimate estimates estimation considered consider relative relatively greater lesser higher-
lower- least most more much many often common commonly rare rarely require required requires work works example examples case cases
part parts type types table figure section paper authors author version online press published publication copyright rights reserved
university department institute journal volume issue pages received accepted revised corresponding email abstract keywords introduction
discussion conclusion conclusions acknowledgements references appendix""".split())
STOP = BASE_STOP | EXTRA | ACADEMIC
TOK = re.compile(r"[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]")
SPLIT = re.compile(r"[.;:!?\n\r()\[\]\"“”,]+")


def tokens_of(text):
    """Token lists per clause; stopwords become None so bigrams never bridge them."""
    out = []
    for clause in SPLIT.split(text.lower()):
        toks = []
        for t in TOK.findall(clause):
            t = t.strip("-")
            if (len(t) < 3 or t in STOP or t.replace("-", "").isdigit()
                    or not re.search(r"[a-z]", t) or len(t) > 30):
                toks.append(None)
            else:
                toks.append(t)
        out.append(toks)
    return out


def ngram_set(clauses):
    s = set()
    for toks in clauses:
        for i, t in enumerate(toks):
            if t is None:
                continue
            s.add(t)
            if i + 1 < len(toks) and toks[i + 1] is not None:
                s.add(t + " " + toks[i + 1])
    return s


AUTHOR_CACHE = ROOT / "outputs" / "topic_review" / "author_surnames.json"
WORDLIST = Path("/usr/share/dict/words")


def author_tokens(min_papers=3):
    """Lower-cased surname tokens from the corpus author field that are NOT ordinary English words.
    An author's surname in the running text is a citation, not a concept: Dulvy appearing in fisheries
    papers says who they cite, not what they are about. Surnames that are also words (White, Brown,
    Last, Fish) are left alone, because the word is the likelier reading. Cached beside the text cache."""
    if AUTHOR_CACHE.exists():
        return set(json.loads(AUTHOR_CACHE.read_text()))
    import pandas as pd
    sys.path.insert(0, str(ROOT / "scripts"))
    import extract_schema_columns as X
    words = set()
    if WORDLIST.exists():
        words = {w.strip().lower() for w in WORDLIST.read_text(errors="ignore").splitlines() if w.strip().islower()}
    cnt = Counter()
    for a in pd.read_parquet(X.INPUT_PARQUET, columns=["authors"])["authors"].dropna():
        for part in re.split(r";|&| and ", str(a)):
            part = re.sub(r"\(\d{4}\)", "", part).strip()
            if not part:
                continue
            name = part.split(",")[0].strip() if "," in part else part.split()[-1]
            for tok in re.findall(r"[A-Za-zÀ-ÿ'’-]+", name):
                if len(tok) >= 3:
                    cnt[tok.lower()] += 1
    out = sorted(t for t, n in cnt.items() if n >= min_papers and t not in words and t not in STOP)
    AUTHOR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    AUTHOR_CACHE.write_text(json.dumps(out))
    return set(out)


def is_author(term, authors):
    return any(tok in authors for tok in term.split(" "))


def load_js(path, prefix):
    txt = Path(path).read_text()
    return json.loads(txt.split("=", 1)[1].strip().rstrip(";"))


def read_blob(conn, lid):
    r = conn.execute("SELECT blob FROM sections WHERE lid=?", (lid,)).fetchone()
    if not r:
        return None
    return [(a, b) for a, b in json.loads(zlib.decompress(r[0]))]


def term_matcher(term):
    """Existing vocabulary term -> (token tuple, wildcard flags). 'fish*' matches by prefix."""
    parts = re.findall(r"[a-z0-9*-]+", term.lower())
    return [(p.rstrip("*"), p.endswith("*")) for p in parts if p.strip("*-")]


def tok_match(tok, pat):
    stem, wild = pat
    return tok.startswith(stem) if wild else tok == stem


def existing_relation(cand, matchers):
    """None, ('same', term) or ('extends', term). Whole-word containment on tokens."""
    ct = cand.split()
    ext = None
    for term, m in matchers:
        n = len(m)
        if not n or n > len(ct):
            continue
        for i in range(len(ct) - n + 1):
            if all(tok_match(ct[i + j], m[j]) for j in range(n)):
                if n == len(ct):
                    return ("same", term)
                ext = ext or term
                break
    return ("extends", ext) if ext else None


def fightin(yi, ni, yj, nj, yp, np_, a0):
    a = a0 * yp / np_
    di = math.log((yi + a) / (ni + a0 - yi - a))
    dj = math.log((yj + a) / (nj + a0 - yj - a))
    var = 1.0 / (yi + a) + 1.0 / (yj + a)
    return (di - dj) / math.sqrt(var)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", default="fisheries")
    ap.add_argument("--rule", default="d_fisheries")
    ap.add_argument("--labels", nargs="+", help="dashboard export JSON file(s)")
    ap.add_argument("--fable", action="store_true", help="use Fable silver labels from seed_labels.js")
    ap.add_argument("--include-bulk", action="store_true", help="also use bulk/assumed labels")
    ap.add_argument("--keep-existing", action="store_true", help="do not exclude existing vocabulary (positive control)")
    ap.add_argument("--min-in", type=int, default=3)
    ap.add_argument("--prior", type=float, default=500.0, help="Dirichlet prior strength a0")
    ap.add_argument("--top", type=int, default=500, help="candidates kept")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    if not args.labels and not args.fable:
        sys.exit("give --labels <export.json> or --fable")
    t0 = time.time()
    tdir = ROOT / "docs" / "topic_review" / args.topic / "data"

    # ---- labels
    dropped = 0
    sources = []
    if args.fable:
        seed = load_js(tdir / "seed_labels.js", "window.TR_SEED")
        fab = seed["fable"].get(args.rule, {})
        seen = {str(x) for x in seed["fable_seen"]}
        lab = {l: (1 if fab.get(l, [0])[0] >= .5 else 0) for l in seen}
        sources.append(f"Fable silver labels ({len(seen)} papers seen)")
    else:
        votes = defaultdict(set)
        for f in args.labels:
            j = json.loads(Path(f).read_text())
            for lid, v in (j.get("labels", {}).get(args.rule) or {}).items():
                if v[0] not in (0, 1):
                    continue
                if v[1] != "i" and not args.include_bulk:
                    continue
                votes[str(lid).split(".")[0]].add(v[0])
            sources.append(f"{f}")
        lab = {}
        for lid, s in votes.items():
            if len(s) > 1:
                dropped += 1
            else:
                lab[lid] = next(iter(s))
    # NOTE: conflicts across files are dropped; first file does not override later ones.

    # ---- existing vocabulary
    existing = []
    vj = ROOT / "outputs" / "topic_review" / args.topic / "vocab.json"
    if vj.exists():
        existing += [v["term"] for v in json.loads(vj.read_text())["vocab"]]
    meta = load_js(tdir / "meta.js", "window.TR_META")
    for r in meta["rules"]:
        if r["id"] == args.rule:
            existing += [meta["vocab"][i] for i in r.get("term_ids", []) + r.get("anchor_ids", [])]
    rule_terms = [meta["vocab"][i] for r in meta["rules"] if r["id"] == args.rule
                  for i in r.get("term_ids", []) + r.get("anchor_ids", [])]
    existing = sorted(set(existing), key=str.lower)
    matchers = [(t, term_matcher(t)) for t in existing]

    # ---- read text of labelled papers only
    conn = sqlite3.connect(f"file:{CACHE}?mode=ro", uri=True, timeout=120)
    conn.execute("PRAGMA busy_timeout=120000")
    papers = {}  # lid -> (group, [(label, clauses)])
    missing = 0
    for lid, g in lab.items():
        secs = read_blob(conn, lid)
        if not secs:
            missing += 1
            continue
        papers[lid] = (g, [(l, tokens_of(t)) for l, t in secs if l != "OTHER" and t])
    n_in = sum(1 for g, _ in papers.values() if g == 1)
    n_out = len(papers) - n_in
    print(f"labelled {len(lab)}; text found {len(papers)} (IN {n_in}, OUT {n_out}); no text {missing}; conflicts dropped {dropped}")

    # ---- document frequencies
    df = {1: Counter(), 0: Counter()}
    for lid, (g, secs) in papers.items():
        s = set()
        for _, cl in secs:
            s |= ngram_set(cl)
        df[g].update(s)
    tot = {g: sum(c.values()) for g, c in df.items()}
    pooled = df[1] + df[0]
    ptot = tot[1] + tot[0]
    print(f"distinct n-grams {len(pooled):,}; {time.time()-t0:.0f}s")

    def score(w, i):
        j = 1 - i
        return fightin(df[i][w], tot[i], df[j][w], tot[j], pooled[w], ptot, args.prior)

    authors = author_tokens()
    cands = []
    for w, c in df[1].items():
        if c < args.min_in:
            continue
        rel = existing_relation(w, matchers)
        if rel and rel[0] == "same" and not args.keep_existing:
            continue
        if args.keep_existing:
            rel = None
        z = score(w, 1)
        if z > 0:
            cands.append((w, z, rel[1] if rel else ""))
    cands.sort(key=lambda x: -x[1])
    all_rank = {w: i + 1 for i, (w, _, _) in enumerate(cands)}  # full ranking, for the control
    cands = cands[:args.top]
    negs = []
    for w, c in df[0].items():
        if c < args.min_in:
            continue
        rel = existing_relation(w, matchers)
        if rel and rel[0] == "same" and not args.keep_existing:
            continue
        z = score(w, 0)
        if z > 0:
            negs.append((w, z))
    negs.sort(key=lambda x: -x[1])
    negs = negs[:50]

    # ---- anchor candidates: present in at least half the IN papers, whatever they do in OUT (existing terms included, flagged)
    anchors = []
    for w, c in df[1].items():
        cov = c / max(n_in, 1)
        if cov < .5:
            continue
        rel = existing_relation(w, matchers)
        anchors.append(dict(term=w.title() if is_author(w, authors) else w, author="yes" if is_author(w, authors) else "", in_cov=round(100 * cov, 1), out_cov=round(100 * df[0][w] / max(n_out, 1), 1),
                            n_in=c, n_out=df[0][w], existing=("yes" if rel and rel[0] == "same" else ("extends " + rel[1]) if rel else "")))
    anchors.sort(key=lambda a: (-a["in_cov"], a["out_cov"]))
    anchors = anchors[:60]

    # ---- section + snippet for final candidates (IN papers only)
    want = {w for w, _, _ in cands}
    sec_df = defaultdict(Counter)
    snip = {}
    for lid, (g, secs) in papers.items():
        if g != 1:
            continue
        seen_here = defaultdict(set)
        for label, cl in secs:
            for w in ngram_set(cl) & want:
                seen_here[w].add(label)
        for w, ls in seen_here.items():
            for l in ls:
                sec_df[w][l] += 1
    need = set(want)
    for lid, (g, _) in papers.items():
        if g != 1 or not need:
            continue
        for label, text in read_blob(conn, lid) or []:
            if label == "OTHER" or label not in ("ABSTRACT", "TITLE", "KEYWORDS", "INTRODUCTION", "METHODS", "RESULTS", "DISCUSSION", "CONCLUSIONS", "RESULTS_AND_DISCUSSION"):
                continue
            low = text.lower()
            for w in list(need):
                m = re.search(r"(?<![a-z0-9-])" + re.escape(w).replace(r"\ ", r"[\s-]+") + r"(?![a-z0-9-])", low)
                if m:
                    a = max(0, m.start() - 80)
                    snip[w] = re.sub(r"[\x00-\x1f\x7f-\x9f\ufffe\uffff]+", " ", text[a:a + 160 + len(w)]); snip[w] = re.sub(r"\s+", " ", snip[w]).strip()
                    need.discard(w)
    rows = []
    for w, z, ext in cands:
        nin, nout = df[1][w], df[0][w]
        sc = sec_df[w]
        au = is_author(w, authors)
        rows.append(dict(term=w.title() if au else w, author="yes" if au else "", n_in=nin, n_out=nout, share_in_pct=round(100 * nin / max(n_in, 1), 1),
                         z=round(z, 2), section=sc.most_common(1)[0][0] if sc else "",
                         extends=ext, snippet=snip.get(w, "")))

    # ---- positive control: rank of the rule's own terms (computed regardless of exclusion)
    ctrl = {}
    if args.keep_existing:
        rank_all = all_rank
        for t in rule_terms:
            key = " ".join(p for p, _ in term_matcher(t))
            ctrl[t] = rank_all.get(key) or rank_all.get(key.rstrip("s"))

    today = datetime.date.today().isoformat()
    od = Path(args.out_dir) if args.out_dir else ROOT / "outputs" / "topic_review" / args.topic / "suggestions"
    od.mkdir(parents=True, exist_ok=True)
    suffix = "_keepexisting" if args.keep_existing else ""
    xp = od / f"suggested_terms_{args.rule}_{today}{suffix}.xlsx"
    jp = od / f"suggested_terms_{args.rule}_{today}{suffix}.json"
    params = dict(prior_a0=args.prior, min_in_df=args.min_in, include_bulk=args.include_bulk,
                  keep_existing=args.keep_existing, top=args.top, topic=args.topic, rule=args.rule)
    cov = dict(papers_in_scope=len(lab), papers_with_text=len(papers), papers_without_text=missing,
               in_papers=n_in, out_papers=n_out, labels_used=len(papers), labels_dropped_conflict=dropped,
               label_sources=sources, existing_terms_excluded=len(existing), parameters=params,
               generated=datetime.datetime.now().isoformat(timespec="seconds"))
    jp.write_text(json.dumps(dict(candidates=[dict(term=r["term"], n_in=r["n_in"], n_out=r["n_out"], z=r["z"],
                                                   section=r["section"], extends_existing_term=r["extends"], author=r["author"])
                                              for r in rows],
                                  negative_terms=[dict(term=w, z=round(z, 2), n_out=df[0][w], n_in=df[1][w]) for w, z in negs],
                                  anchor_candidates=anchors,
                                  coverage=cov), indent=1))

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = "Info"
    info = [
        ("Suggested keywords for rule %s (%s), generated %s" % (args.rule, args.topic, today),),
        ("",),
        ("Why this workbook exists",),
        ("The topic rule only finds what its keywords cover. This list proposes NEW keywords that occur far more often in papers labelled IN than in papers labelled OUT, for you to accept or reject.",),
        ("",),
        ("Inputs",),
        ("Label source: " + "; ".join(sources) + (" (inspected labels only)" if args.labels and not args.include_bulk else ""),),
        (f"Papers with text: {len(papers)} of {len(lab)} labelled; IN {n_in}, OUT {n_out}; labels dropped for conflicting values: {dropped}; labelled papers without cached text: {missing}.",),
        (f"Existing vocabulary excluded: {len(existing)} terms (outputs/topic_review/{args.topic}/vocab.json plus the rule's own terms)." if not args.keep_existing else "Existing vocabulary NOT excluded (positive-control run).",),
        ("",),
        ("Method",),
        ("Each paper's title, keywords, abstract and body (not the OTHER section) is tokenised into words and two-word phrases, each counted once per paper.",),
        ("Phrases are scored by the weighted log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi & Quinn 2008), prior = both groups pooled; log_odds_z is its z-score, so larger means more distinctly IN.",),
        (f"A phrase must occur in at least {args.min_in} IN papers. Phrases containing an existing term as a whole word are kept but flagged in extends_existing_term.",),
        ("",),
        ("What to do",),
        ("1. Open the candidates tab. Read each term with its example_snippet.",),
        ("2. Fill the decision column with accept, reject, or anchor (anchor = accept and require it as an anchor word). Use note for anything unusual.",),
        ("3. Terms flagged in extends_existing_term are usually redundant; accept only if the longer phrase adds precision.",),
        ("4. The negative_terms tab lists words enriched in OUT papers: candidates for exclusion terms. It needs no decision unless you want one used.",),
        ("6. Author surnames are included, Title-cased and marked yes in the author column. A surname marks who the IN papers cite rather than what they are about, so it is usually a poor keyword; the decision is yours.",),
        ("5. The anchor_candidates tab ranks terms by the share of IN papers that contain them (at least half). An anchor gates the rule, so it must be nearly universal in IN papers; its OUT share matters less. Terms already in the vocabulary are included and marked in the existing column.",),
        ("",),
        ("What happens next",),
        (f"Accepted terms go into data/topic_review/{args.topic}.json under reviewer_terms and are counted by the re-count step; this workbook is not edited further.",),
    ]
    for r in info:
        ws.append(list(r))
    for rr in (1, 3, 6, 11, 16, 22):
        ws.cell(rr, 1).font = Font(bold=True)
    ws.column_dimensions["A"].width = 150
    for row in ws.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical="top")

    def sheet(name, head, data, widths):
        s = wb.create_sheet(name)
        s.append(head)
        for d in data:
            s.append(d)
        for c in s[1]:
            c.font = Font(bold=True)
        s.freeze_panes = "A2"
        s.auto_filter.ref = f"A1:{get_column_letter(len(head))}{max(len(data) + 1, 2)}"
        for i, w in enumerate(widths, 1):
            s.column_dimensions[get_column_letter(i)].width = w

    sheet("candidates",
          ["term", "author", "n_in_papers", "n_out_papers", "share_in_pct", "log_odds_z", "main_section",
           "extends_existing_term", "example_snippet", "decision", "note"],
          [[r["term"], r["author"], r["n_in"], r["n_out"], r["share_in_pct"], r["z"], r["section"], r["extends"], r["snippet"], "", ""] for r in rows],
          [28, 8, 11, 12, 11, 11, 22, 24, 90, 12, 30])
    sheet("negative_terms", ["term", "n_out_papers", "n_in_papers", "log_odds_z_out"],
          [[w, df[0][w], df[1][w], round(z, 2)] for w, z in negs], [32, 13, 12, 14])
    sheet("anchor_candidates", ["term", "author", "in_coverage_pct", "out_coverage_pct", "n_in_papers", "n_out_papers", "existing", "decision", "note"],
          [[a["term"], a["author"], a["in_cov"], a["out_cov"], a["n_in"], a["n_out"], a["existing"], "", ""] for a in anchors], [30, 8, 15, 16, 12, 13, 22, 12, 30])
    wb.save(xp)

    el = time.time() - t0
    print(f"\ntop 25 candidates ({'existing kept' if args.keep_existing else 'existing excluded'}):")
    for i, r in enumerate(rows[:25], 1):
        print(f"{i:3d} {r['term']:34s} z={r['z']:6.2f} in={r['n_in']:4d} out={r['n_out']:4d} {r['section']:12s} {('ext:' + r['extends']) if r['extends'] else ''}")
    print("\ntop 15 negative terms:", ", ".join(f"{w} ({z:.1f})" for w, z in negs[:15]))
    print("\nauthor surnames among candidates (marked):", sum(1 for r in rows if r["author"]), "e.g.", ", ".join(r["term"] for r in rows if r["author"])[:120])
    print("\ntop 12 anchor candidates (IN% / OUT%):", ", ".join(f"{a['term']} {a['in_cov']:.0f}/{a['out_cov']:.0f}{' [existing]' if a['existing'] == 'yes' else ''}" for a in anchors[:12]))
    if ctrl:
        print("\npositive control (rank of rule's own terms):", ctrl)
    print(f"\nwall-clock {el:.0f}s\n{xp}\n{jp}")


if __name__ == "__main__":
    main()
