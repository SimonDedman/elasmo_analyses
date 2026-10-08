#!/usr/bin/env python3
"""
Compute female-presenter proportions for three 2026 conference reference
points (AES2026, SI2026, EEA2026), for overlay on the D6 gender-trend figure
(``outputs/figures/SI_D6_gender_trend.png``).

AES2026
-------
Parses the AES-only subset of the JMIH 2026 (New Orleans) agenda,
extracting every "Speaker:" line (the presenting author of each talk
or poster; moderators are excluded). Gender is inferred per first name
using, in order:
  1. The project's genderize.io cache (``outputs/.genderize_cache.json``).
  2. ``scripts/infer_author_gender.py``'s ``infer_gender()`` helper
     (gender_guesser, with hyphen/multi-word fallback).
Nicknames given in parentheses (e.g. "Mary E. (Beth) Bowers") are
preferred over the literal first token; leading initials are skipped.

SI2026
------
Reuses the already-computed Sharks International 2026 first-author
gender split from
``/home/simon/Documents/Si Work/PostDoc Work/SI/2026 Sri Lanka/Sessions info/SI2026_authors_long.xlsx``
(the same source and logic as ``viz_si2026_comparison.R``, which
produced the diamonds already baked into SI_D6_gender_trend.png back
on 2026-04-14): filter to ``Is First Author == True``, gender from
NamSor Gender first, OpenAlex Gender as fallback.

EEA2026
-------
Presenters of the EEA 2026 (online, 6-8 Oct) DRAFT schedule 4, as parsed by
the Shark Network project into ``data/eea2026_talks.csv`` (one row per
programme slot). Regular talks and speed talks are counted, one per
presentation; the panel and the side-event convener rows are not. Gender
is inferred exactly as for AES2026, then corrected from
``outputs/conference_gender_overrides.csv`` (columns conference, full_name,
gender) where a presenter is known to be misclassified by their first name.
That file is git-ignored with the rest of ``outputs/``: named, inferred
gender stays out of the public repository.

Output: outputs/conference_gender.csv with columns
    conference, year, gender, n, total, pct, unknown, unknown_pct
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
AES_AGENDA = Path(
    "/home/simon/Documents/Si Work/PostDoc Work/AES/2026-07-09 AES New Orleans/"
    "JMIH 2026 Agenda - AES only.txt"
)
SI_AUTHORS_XLSX = Path(
    "/home/simon/Documents/Si Work/PostDoc Work/SI/2026 Sri Lanka/Sessions info/"
    "SI2026_authors_long.xlsx"
)
EEA_TALKS_CSV = Path(
    "/home/simon/Documents/Si Work/PostDoc Work/Shark Network/data/eea2026_talks.csv"
)
EEA_TALK_ROLES = ("speaker", "speed_talk")
OVERRIDES_CSV = PROJECT_BASE / "outputs/conference_gender_overrides.csv"
GENDERIZE_CACHE = PROJECT_BASE / "outputs/.genderize_cache.json"
OUT_CSV = PROJECT_BASE / "outputs/conference_gender.csv"

sys.path.insert(0, str(PROJECT_BASE / "scripts"))
from infer_author_gender import infer_gender  # noqa: E402
import gender_guesser.detector as gender_detector  # noqa: E402

_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$")
_NICKNAME_RE = re.compile(r"\(([A-Za-z]+)\)")


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def extract_first_name(full_name: str) -> str | None:
    """Best-guess given first name for gender inference.

    Prefers a parenthetical nickname (e.g. "Joseph (Joe) Candia" -> "Joe"),
    else the first non-initial token (e.g. "R. Dean Grubbs" -> "Dean").
    """
    full_name = full_name.strip()
    nick = _NICKNAME_RE.search(full_name)
    if nick:
        return nick.group(1)

    # Remove parenthetical asides entirely before tokenising
    cleaned = re.sub(r"\([^)]*\)", " ", full_name)
    tokens = [t for t in cleaned.replace(".", ". ").split() if t]
    for tok in tokens:
        tok_clean = tok.strip(".")
        if tok_clean and not _INITIAL_RE.match(tok):
            return tok_clean
    return None


def infer_gender_layered(
    first_name: str, cache: dict, detector: gender_detector.Detector
) -> str:
    """genderize cache -> infer_author_gender.infer_gender (gender_guesser),
    trying both the literal and accent-stripped spelling at each step."""
    candidates = [first_name]
    stripped = strip_accents(first_name)
    if stripped != first_name:
        candidates.append(stripped)

    for cand in candidates:
        if cand in cache:
            g = cache[cand]
            if g in ("male", "female"):
                return g

    for cand in candidates:
        g = infer_gender(cand, detector)
        if g != "unknown":
            return g

    return "unknown"


def compute_aes2026() -> pd.DataFrame:
    text = AES_AGENDA.read_text(encoding="utf-8")
    speakers = re.findall(r"^\s*Speaker:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    print(f"AES2026: extracted {len(speakers)} 'Speaker:' presentation entries")

    cache = json.loads(GENDERIZE_CACHE.read_text(encoding="utf-8"))
    detector = gender_detector.Detector()

    rows = []
    for full_name in speakers:
        first = extract_first_name(full_name)
        gender = infer_gender_layered(first, cache, detector) if first else "unknown"
        rows.append({"full_name": full_name, "first_name": first, "gender": gender})

    df = pd.DataFrame(rows)
    print(df["gender"].value_counts(dropna=False))

    unresolved = df[df["gender"] == "unknown"]
    if len(unresolved):
        print(f"\n{len(unresolved)} unresolved first names (sample up to 20):")
        print(unresolved["first_name"].dropna().unique()[:20])

    return df


def compute_eea2026() -> pd.DataFrame:
    talks = pd.read_csv(EEA_TALKS_CSV)
    talks = talks[talks["role"].isin(EEA_TALK_ROLES)]
    print(f"EEA2026: {len(talks)} talk / speed-talk slots in the draft schedule")

    cache = json.loads(GENDERIZE_CACHE.read_text(encoding="utf-8"))
    detector = gender_detector.Detector()

    rows = []
    for full_name in talks["speaker"]:
        first = extract_first_name(full_name)
        gender = infer_gender_layered(first, cache, detector) if first else "unknown"
        rows.append({"full_name": full_name, "first_name": first, "gender": gender})
    df = pd.DataFrame(rows)
    print("  inferred:", df["gender"].value_counts(dropna=False).to_dict())

    if OVERRIDES_CSV.exists():
        ov = pd.read_csv(OVERRIDES_CSV)
        ov = ov[ov["conference"] == "EEA2026"].set_index("full_name")["gender"]
        hit = df["full_name"].isin(ov.index)
        df.loc[hit, "gender"] = df.loc[hit, "full_name"].map(ov)
        print(f"  {hit.sum()} rows corrected from {OVERRIDES_CSV.name}"
              f" ({len(ov) - df.loc[hit, 'full_name'].nunique()} override names unmatched)")
        print("  corrected:", df["gender"].value_counts(dropna=False).to_dict())

    unresolved = df[df["gender"] == "unknown"]
    if len(unresolved):
        print(f"  {len(unresolved)} unresolved first names:",
              list(unresolved["first_name"].dropna().unique()))
    return df


def summarise(df: pd.DataFrame, conference: str, year: int) -> pd.DataFrame:
    total = len(df)
    known = df[df["gender"].isin(["male", "female"])]
    n_known = len(known)
    unknown = total - n_known
    counts = known["gender"].value_counts()
    out_rows = []
    for g in ("male", "female"):
        n = int(counts.get(g, 0))
        out_rows.append(
            {
                "conference": conference,
                "year": year,
                "gender": g.capitalize(),
                "n": n,
                "total": total,
                "n_known": n_known,
                "pct": 100 * n / n_known if n_known else float("nan"),
                "unknown": unknown,
                "unknown_pct": 100 * unknown / total if total else float("nan"),
            }
        )
    return pd.DataFrame(out_rows)


def compute_si2026() -> pd.DataFrame:
    df = pd.read_excel(SI_AUTHORS_XLSX)
    first = df[df["Is First Author"] == True].copy()  # noqa: E712

    def gender_of(row) -> str:
        ng = str(row["NamSor Gender"]).lower()
        og = str(row["OA Gender"]).lower()
        if ng == "male":
            return "male"
        if ng == "female":
            return "female"
        if og == "male":
            return "male"
        if og == "female":
            return "female"
        return "unknown"

    first["gender"] = first.apply(gender_of, axis=1)
    print(f"SI2026: {len(first)} first-author abstract rows")
    print(first["gender"].value_counts(dropna=False))
    return first[["gender"]]


def main() -> None:
    aes_df = compute_aes2026()
    aes_summary = summarise(aes_df, "AES2026", 2026)

    si_df = compute_si2026()
    si_summary = summarise(si_df, "SI2026", 2026)

    eea_df = compute_eea2026()
    eea_summary = summarise(eea_df, "EEA2026", 2026)

    combined = pd.concat([aes_summary, si_summary, eea_summary], ignore_index=True)
    combined.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV}")
    print(combined.to_string(index=False))


if __name__ == "__main__":
    main()
