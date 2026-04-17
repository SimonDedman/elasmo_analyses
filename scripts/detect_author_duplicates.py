#!/usr/bin/env python3
"""
Detect potential duplicate author entries in OpenAlex data.

Strategy: group authors by normalised surname + first-initial, then score
candidates within each group by shared attributes:
- Same institution_country: +3
- Same most_common_institution: +5
- Same NamSor gender: +1
- Same NamSor origin_country: +2
- Same NamSor ethnicity: +2
- Same first_name (not just initial): +3

Emit candidate pairs with score >= 4 to an XLSX for manual review.

Usage:
    python scripts/detect_author_duplicates.py
"""

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_unique_authors.csv"
NAMSOR_CSV = PROJECT_ROOT / "outputs" / "namsor_enrichment.csv"
PAPER_AUTHORS_CSV = PROJECT_ROOT / "outputs" / "openalex_paper_authors.csv"
OUT_XLSX = PROJECT_ROOT / "outputs" / "author_duplicate_candidates.xlsx"


def normalise_name(s) -> str:
    """Strip accents, hyphens, lowercase. Handles NaN/float/None."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z]", "", s)
    return s


def first_initial(first_name: str) -> str:
    if not first_name:
        return ""
    # Handle "D." "DW" "David W." etc.
    clean = re.sub(r"[^A-Za-z]", "", first_name)
    return clean[:1].lower() if clean else ""


def main():
    print("Loading authors...")
    authors = pd.read_csv(AUTHORS_CSV)
    authors["openalex_author_id"] = authors["openalex_author_id"].str.replace(
        "https://openalex.org/", "", regex=False
    )
    print(f"  {len(authors)} authors")

    print("Loading NamSor...")
    namsor = pd.read_csv(NAMSOR_CSV)
    namsor["openalex_author_id"] = namsor["id"].str.replace(
        "https://openalex.org/", "", regex=False
    )
    namsor = namsor[[
        "openalex_author_id", "namsor_gender", "namsor_origin_country",
        "namsor_origin_region", "namsor_ethnicity"
    ]]

    authors = authors.merge(namsor, on="openalex_author_id", how="left")

    print("Loading paper-author mapping for paper counts...")
    paper_auth = pd.read_csv(PAPER_AUTHORS_CSV, usecols=["literature_id", "openalex_author_id"])
    paper_auth["openalex_author_id"] = paper_auth["openalex_author_id"].str.replace(
        "https://openalex.org/", "", regex=False
    )
    papers_per = paper_auth.groupby("openalex_author_id").size().rename("n_papers").reset_index()
    authors = authors.merge(papers_per, on="openalex_author_id", how="left")
    authors["n_papers"] = authors["n_papers"].fillna(0).astype(int)

    # Build grouping key: normalised surname + first initial
    authors["surname_norm"] = authors["last_name"].fillna("").map(normalise_name)
    authors["initial"] = authors["first_name"].fillna("").map(first_initial)
    authors["group_key"] = authors["surname_norm"] + "_" + authors["initial"]

    authors = authors[authors["surname_norm"].str.len() >= 2]  # drop single-letter surnames
    print(f"  {len(authors)} after filtering short surnames")

    # Group and find candidate pairs
    groups = authors.groupby("group_key")
    group_sizes = groups.size()
    multi_groups = group_sizes[group_sizes >= 2].index
    print(f"  {len(multi_groups)} groups with 2+ members")

    candidates = []
    for key in multi_groups:
        members = groups.get_group(key).reset_index(drop=True)
        # Compare each pair
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a = members.iloc[i]
                b = members.iloc[j]

                score = 0
                reasons = []

                # Same full first name (not just initial)
                fn_a = normalise_name(a["first_name"] or "")
                fn_b = normalise_name(b["first_name"] or "")
                if fn_a and fn_b and fn_a == fn_b:
                    score += 3
                    reasons.append("same first name")

                # Same country
                if pd.notna(a["institution_country"]) and pd.notna(b["institution_country"]):
                    if a["institution_country"] == b["institution_country"]:
                        score += 3
                        reasons.append(f"same country ({a['institution_country']})")

                # Same institution
                inst_a = str(a.get("most_common_institution") or "").strip().lower()
                inst_b = str(b.get("most_common_institution") or "").strip().lower()
                if inst_a and inst_b and inst_a == inst_b:
                    score += 5
                    reasons.append("same institution")

                # Same NamSor gender
                if pd.notna(a["namsor_gender"]) and pd.notna(b["namsor_gender"]):
                    if a["namsor_gender"] == b["namsor_gender"]:
                        score += 1
                        reasons.append(f"same gender ({a['namsor_gender']})")
                    else:
                        score -= 2  # Conflicting gender is a negative signal
                        reasons.append(f"DIFFERENT gender ({a['namsor_gender']}/{b['namsor_gender']})")

                # Same NamSor origin country
                if pd.notna(a["namsor_origin_country"]) and pd.notna(b["namsor_origin_country"]):
                    if a["namsor_origin_country"] == b["namsor_origin_country"]:
                        score += 2
                        reasons.append(f"same origin ({a['namsor_origin_country']})")

                # Same NamSor ethnicity
                if pd.notna(a["namsor_ethnicity"]) and pd.notna(b["namsor_ethnicity"]):
                    if a["namsor_ethnicity"] == b["namsor_ethnicity"]:
                        score += 2
                        reasons.append(f"same ethnicity ({a['namsor_ethnicity']})")

                if score >= 4:
                    candidates.append({
                        "group_key": key,
                        "score": score,
                        "reasons": "; ".join(reasons),
                        "id_a": a["openalex_author_id"],
                        "name_a": a["display_name"],
                        "first_a": a["first_name"],
                        "inst_a": a.get("most_common_institution"),
                        "country_a": a["institution_country"],
                        "gender_a": a["namsor_gender"],
                        "origin_a": a["namsor_origin_country"],
                        "ethnicity_a": a["namsor_ethnicity"],
                        "papers_a": int(a["n_papers"]),
                        "id_b": b["openalex_author_id"],
                        "name_b": b["display_name"],
                        "first_b": b["first_name"],
                        "inst_b": b.get("most_common_institution"),
                        "country_b": b["institution_country"],
                        "gender_b": b["namsor_gender"],
                        "origin_b": b["namsor_origin_country"],
                        "ethnicity_b": b["namsor_ethnicity"],
                        "papers_b": int(b["n_papers"]),
                    })

    candidates.sort(key=lambda x: -x["score"])
    print(f"\nFound {len(candidates)} candidate pairs (score >= 4)")
    print(f"  Score 10+: {sum(1 for c in candidates if c['score'] >= 10)}")
    print(f"  Score 7-9: {sum(1 for c in candidates if 7 <= c['score'] < 10)}")
    print(f"  Score 4-6: {sum(1 for c in candidates if 4 <= c['score'] < 7)}")

    # Write XLSX
    df = pd.DataFrame(candidates)
    df["decision"] = ""  # empty column for reviewer to fill in: "merge", "keep", "unsure"
    df.to_excel(OUT_XLSX, index=False, sheet_name="Candidates")
    print(f"\nWrote {OUT_XLSX}")


if __name__ == "__main__":
    main()
