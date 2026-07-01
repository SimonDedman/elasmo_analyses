"""Match Ulrich's RIS library against our remaining-downloads list.

Inputs:
  - database/others_libraries/Ulrich/download/database_ub/SharkLit_ub.ris
  - docs/papers_data.json (remaining papers we still need)
  - outputs/literature_review_enriched.parquet (full DB, for "we already have it" check)

Outputs:
  - outputs/ulrich_papers_we_need.csv       — simple: DOI, year, authors, title, LB, RN
  - outputs/ulrich_papers_we_need.ris       — filtered RIS (same format as input)
  - outputs/ulrich_match_summary.txt        — tallies by category
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path('/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel')
RIS_PATH = ROOT / 'database/others_libraries/Ulrich/download/database_ub/SharkLit_ub.ris'
PAPERS_DATA_JSON = ROOT / 'docs/papers_data.json'
ENRICHED_PARQUET = ROOT / 'outputs/literature_review_enriched.parquet'
OUT_CSV = ROOT / 'outputs/ulrich_papers_we_need.csv'
OUT_RIS = ROOT / 'outputs/ulrich_papers_we_need.ris'
OUT_SUMMARY = ROOT / 'outputs/ulrich_match_summary.txt'


def normalise_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = str(doi).strip().lower()
    d = re.sub(r'^https?://(dx\.)?doi\.org/', '', d)
    d = d.strip().rstrip('.,;')
    return d or None


def normalise_title(title: str | None) -> str | None:
    if not title:
        return None
    t = unicodedata.normalize('NFKD', str(title))
    t = t.encode('ascii', 'ignore').decode('ascii')
    t = t.lower()
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    t = re.sub(r'\s+', ' ', t)
    return t or None


def first_author_surname(authors_field) -> str | None:
    """Handle either a string "Surname, First" or list thereof."""
    if not authors_field:
        return None
    if isinstance(authors_field, list):
        if not authors_field:
            return None
        a = authors_field[0]
    else:
        a = str(authors_field).split('&')[0].split(';')[0].split(',')[0]
        return normalise_title(a)
    s = str(a).split(',')[0]
    return normalise_title(s)


def title_prefix(title_norm: str | None, n: int = 40) -> str | None:
    if not title_norm:
        return None
    return title_norm[:n] if len(title_norm) >= 10 else None


def journal_norm(journal: str | None) -> str | None:
    """Lose 'the ', abbreviations, punctuation, case."""
    if not journal:
        return None
    j = unicodedata.normalize('NFKD', str(journal)).encode('ascii', 'ignore').decode('ascii')
    j = j.lower()
    j = re.sub(r'\bthe\b', '', j)
    j = re.sub(r'[^a-z0-9]+', ' ', j).strip()
    j = re.sub(r'\s+', ' ', j)
    return j or None


# -------- RIS parsing --------

def parse_ris(path: Path):
    text = path.read_text(encoding='utf-8', errors='replace')
    # Each record ends with "ER  - "
    entries = []
    current_lines: list[str] = []
    current: dict[str, list[str]] = defaultdict(list)
    current_tag: str | None = None

    TAG_RE = re.compile(r'^([A-Z][A-Z0-9])  - (.*)$')

    for raw_line in text.splitlines():
        line = raw_line.rstrip('\r\n')
        current_lines.append(raw_line)
        m = TAG_RE.match(line)
        if m:
            current_tag = m.group(1)
            val = m.group(2)
            if current_tag == 'ER':
                # Record complete
                entry = {k: v for k, v in current.items()}
                entry['_raw'] = '\n'.join(current_lines)
                entries.append(entry)
                current = defaultdict(list)
                current_lines = []
                current_tag = None
            else:
                current[current_tag].append(val)
        else:
            # continuation line — append to last tag if any
            if current_tag is not None and line:
                current[current_tag][-1] = current[current_tag][-1] + '\n' + line
    return entries


def main() -> int:
    print(f'Loading RIS from {RIS_PATH}...')
    ris_entries = parse_ris(RIS_PATH)
    print(f'  Parsed {len(ris_entries)} entries')

    ris_rows = []
    for e in ris_entries:
        doi = normalise_doi(e.get('DO', [None])[0] if e.get('DO') else None)
        title = e.get('TI', [None])[0] if e.get('TI') else None
        year_raw = e.get('PY', [None])[0] if e.get('PY') else None
        try:
            year = int(str(year_raw)[:4]) if year_raw else None
        except Exception:
            year = None
        authors = e.get('AU', [])
        lb = (e.get('LB', [None])[0] if e.get('LB') else None) or ''
        rn = ' | '.join(e.get('RN', [])) if e.get('RN') else ''
        t2 = e.get('T2', [None])[0] if e.get('T2') else None
        t_norm = normalise_title(title)
        ris_rows.append({
            'doi': doi,
            'title': title,
            'title_norm': t_norm,
            'title_prefix': title_prefix(t_norm),
            'year': year,
            'authors': '; '.join(authors) if authors else '',
            'first_author_key': first_author_surname(authors),
            'lb_code': lb,
            'rn': rn,
            'journal': t2,
            'journal_norm': journal_norm(t2),
            'raw': e['_raw'],
        })
    ris_df = pd.DataFrame(ris_rows)
    print(f'  RIS: {len(ris_df)} entries; with DOI: {ris_df["doi"].notna().sum()}')

    # -------- Load our "still need" list --------
    print(f'Loading papers_data.json...')
    with open(PAPERS_DATA_JSON) as f:
        needed = json.load(f)
    need_df = pd.DataFrame(needed)
    need_df['doi_norm'] = need_df['doi'].apply(normalise_doi)
    need_df['title_norm'] = need_df['title'].apply(normalise_title)
    need_df['title_prefix'] = need_df['title_norm'].apply(title_prefix)
    need_df['first_author_key'] = need_df['authors'].apply(first_author_surname)
    need_df['journal_norm'] = need_df['journal'].apply(journal_norm)
    need_df['year'] = pd.to_numeric(need_df['year'], errors='coerce').astype('Int64')
    print(f'  papers_data: {len(need_df)} entries; with DOI: {need_df["doi_norm"].notna().sum()}')

    # -------- Load our full DB --------
    print(f'Loading enriched parquet...')
    db = pd.read_parquet(ENRICHED_PARQUET,
                        columns=['literature_id', 'doi', 'title', 'year', 'authors', 'journal'])
    db['doi_norm'] = db['doi'].apply(normalise_doi)
    db['title_norm'] = db['title'].apply(normalise_title)
    db['title_prefix'] = db['title_norm'].apply(title_prefix)
    db['first_author_key'] = db['authors'].apply(first_author_surname)
    db['journal_norm'] = db['journal'].apply(journal_norm)
    db['year'] = pd.to_numeric(db['year'], errors='coerce').astype('Int64')
    print(f'  DB: {len(db)} papers')

    def build_keys(df: pd.DataFrame):
        doi_keys = set(df['doi_norm'].dropna())
        title_keys = set(
            (t, int(y)) for t, y in zip(df['title_norm'], df['year'])
            if pd.notna(t) and pd.notna(y)
        )
        author_title_keys = set(
            (a, int(y), tp)
            for a, y, tp in zip(df['first_author_key'], df['year'], df['title_prefix'])
            if pd.notna(a) and pd.notna(y) and pd.notna(tp)
        )
        author_journal_keys = set(
            (a, int(y), j)
            for a, y, j in zip(df['first_author_key'], df['year'], df['journal_norm'])
            if pd.notna(a) and pd.notna(y) and pd.notna(j)
        )
        return doi_keys, title_keys, author_title_keys, author_journal_keys

    need_dois, need_titles, need_at, need_aj = build_keys(need_df)
    db_dois, db_titles, db_at, db_aj = build_keys(db)

    # Classify each Ulrich entry
    categories: list[str] = []
    match_methods: list[str] = []
    for _, r in ris_df.iterrows():
        doi = r['doi']
        year_ok = pd.notna(r['year'])
        tkey = (r['title_norm'], int(r['year'])) if r['title_norm'] and year_ok else None
        atkey = (r['first_author_key'], int(r['year']), r['title_prefix']) \
            if r['first_author_key'] and year_ok and r['title_prefix'] else None
        ajkey = (r['first_author_key'], int(r['year']), r['journal_norm']) \
            if r['first_author_key'] and year_ok and r['journal_norm'] else None

        def classify(dois, titles, at, aj):
            if doi and doi in dois:
                return 'doi'
            if tkey and tkey in titles:
                return 'title+year'
            if atkey and atkey in at:
                return 'author+year+titleprefix'
            if ajkey and ajkey in aj:
                return 'author+year+journal'
            return None

        need_via = classify(need_dois, need_titles, need_at, need_aj)
        db_via = classify(db_dois, db_titles, db_at, db_aj)

        if need_via:
            cat = 'NEEDED'
            via = need_via
        elif db_via:
            cat = 'ALREADY_HAVE'
            via = db_via
        else:
            cat = 'NOT_IN_DB'
            via = ''
        categories.append(cat)
        match_methods.append(via)
    ris_df['category'] = categories
    ris_df['match_method'] = match_methods

    # Ulrich access status (fulltext vs citation)
    def rn_to_status(rn: str) -> str:
        rn_l = rn.lower()
        if 'fulltext' in rn_l:
            return 'fulltext'
        if 'citation' in rn_l or 'abstract' in rn_l or 'paywall' in rn_l:
            return 'citation_only'
        return 'unknown'

    ris_df['ulrich_access'] = ris_df['rn'].apply(rn_to_status)

    # -------- Output: papers we need --------
    need_out = ris_df[ris_df['category'] == 'NEEDED'].copy()
    need_out = need_out.sort_values(['ulrich_access', 'year', 'first_author_key'],
                                    ascending=[True, True, True])

    # Simple CSV
    csv_cols = ['doi', 'year', 'authors', 'title', 'journal',
                'lb_code', 'ulrich_access', 'match_method', 'rn']
    need_out[csv_cols].to_csv(OUT_CSV, index=False)
    print(f'Wrote {OUT_CSV} ({len(need_out)} rows)')

    # Filtered RIS (preserve original format)
    with open(OUT_RIS, 'w', encoding='utf-8') as f:
        for raw in need_out['raw']:
            f.write(raw)
            if not raw.endswith('\n'):
                f.write('\n')
            f.write('\n')
    print(f'Wrote {OUT_RIS}')

    # -------- Summary --------
    cat_counts = ris_df['category'].value_counts().to_dict()
    access_counts = ris_df.groupby(['category', 'ulrich_access']).size().unstack(fill_value=0)

    method_counts = ris_df.groupby(['category', 'match_method']).size().unstack(fill_value=0)
    no_doi_methods = (ris_df[ris_df['doi'].isna()]
                      .groupby(['category', 'match_method']).size().unstack(fill_value=0))

    summary_lines = [
        f'Ulrich RIS match summary — {pd.Timestamp.now():%Y-%m-%d %H:%M}',
        f'RIS entries parsed: {len(ris_df)}',
        f'  with DOI: {ris_df["doi"].notna().sum()}',
        f'  without DOI: {ris_df["doi"].isna().sum()}',
        '',
        'Category breakdown:',
    ]
    for k in ['NEEDED', 'ALREADY_HAVE', 'NOT_IN_DB']:
        summary_lines.append(f'  {k}: {cat_counts.get(k, 0)}')
    summary_lines += [
        '',
        'Category × Ulrich access (fulltext vs citation_only vs unknown):',
        access_counts.to_string(),
        '',
        'Match methods (all entries):',
        method_counts.to_string(),
        '',
        'Match methods (no-DOI entries only):',
        no_doi_methods.to_string(),
        '',
        f'Papers Ulrich has fulltext AND we still need: '
        f'{((ris_df.category == "NEEDED") & (ris_df.ulrich_access == "fulltext")).sum()}',
        '',
        f'Outputs:',
        f'  CSV: {OUT_CSV}',
        f'  RIS: {OUT_RIS}',
    ]

    OUT_SUMMARY.write_text('\n'.join(summary_lines))
    print('\n'.join(summary_lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
