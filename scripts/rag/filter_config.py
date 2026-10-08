#!/usr/bin/env python3
"""
Declarative filter registry for the RAG front-end.

A single source of truth describing which parquet columns are exposed as query
filters and how. Both build_filters.py (which materialises the sidecar) and
serve.py (which builds the /api/filters response and resolves selections) read
this. Adding a new filter family = append one FamilySpec; rebuild the sidecar.

Family kinds:
  bool_prefix  — every column with the given prefix becomes a boolean option
                 (e.g. d_genetics, d_taxonomy). Match = column truthy.
  bool_cols    — an explicit list of boolean columns (0/1 or bool).
  categorical  — one string column; options are its distinct values.
  range        — one numeric column; min/max bounds.
  author       — special: autocomplete over the OpenAlex author index.

See docs/superpowers/specs/2026-07-11-rag-schema-filters-web-frontend-design.md
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FamilySpec:
    key: str
    label: str
    kind: str                 # bool_prefix | bool_cols | categorical | range | author
    widget: str               # multiselect | search-multiselect | range | author
    prefix: str | None = None
    columns: tuple[str, ...] = field(default_factory=tuple)
    column: str | None = None
    note: str | None = None    # surfaced in the UI (caveats, coverage)
    sorts: tuple[str, ...] = ()   # UI sort toggles: freq | az | geo | best
    default_sort: str = "freq"


# Order here == display order in the UI.
FAMILY_SPECS: list[FamilySpec] = [
    FamilySpec("author", "Author", "author", "author",
               note="Reaches papers with OpenAlex author records (~half the "
                    "corpus); papers without them won't match an author."),
    FamilySpec("discipline", "Discipline", "bool_prefix", "multiselect", prefix="d_"),
    FamilySpec("technique", "Technique", "bool_prefix", "search-multiselect", prefix="a_"),
    FamilySpec("pressure", "Pressure", "bool_prefix", "multiselect", prefix="pr_"),
    FamilySpec("gear", "Gear", "bool_prefix", "multiselect", prefix="gear_"),
    FamilySpec("impact", "Impact", "bool_prefix", "multiselect", prefix="imp_"),
    FamilySpec("ecosystem", "Ecosystem", "bool_prefix", "multiselect", prefix="eco_"),
    FamilySpec("basin_textmined", "Ocean basin (text-mined)", "bool_prefix",
               "multiselect", prefix="b_"),
    FamilySpec("subbasin", "Sub-basin (text-mined)", "bool_prefix",
               "search-multiselect", prefix="sb_"),
    FamilySpec("study_country", "Study country", "categorical", "multiselect",
               column="geo_study_country", sorts=("freq", "az"),
               note="Country of the study site, read from each paper's methods "
                    "section by the geo pipeline (reliable)."),
    FamilySpec("study_basin", "Study ocean basin", "categorical", "multiselect",
               column="geo_study_ocean_basin",
               note="Ocean basin of the study site, read from the paper's methods section."),
    FamilySpec("author_country", "First-author country", "categorical", "multiselect",
               column="geo_first_author_country", sorts=("freq", "az"),
               note="Country of the first author's institution (OpenAlex)."),
    FamilySpec("author_region", "First-author region", "categorical", "multiselect",
               column="geo_first_author_region",
               note="Global North or Global South, from the first author's country."),
    FamilySpec("country_record", "Country (record field)", "categorical", "multiselect",
               column="country", sorts=("freq", "az"),
               note="Countries only; seas and regions are under Ocean basin and Sub-basin. "
                    "The place Shark-References itself filed the paper under "
                    "(last element of its 'keyword place' field), not something we "
                    "extracted. US states, regions, seas and territories in that field "
                    "(for example Kansas, Mediterranean) are not offered, and ~85% of "
                    "papers have no value."),
    # REMOVED "superregion" (column `superregion`): it is parsed from the same
    # Shark-References keyword-place field as Country, and its values include
    # countries and US states, so it is not a super-region field. 2026-10-08.
    FamilySpec("epoch", "Epoch", "categorical", "multiselect", column="epoch",
               sorts=("geo", "az", "freq"), default_sort="geo",
               note="Geological time of the material, from Shark-References. "
                    "'Recent' means living species (the source's 'rezent')."),
    FamilySpec("journal", "Journal", "categorical", "search-multiselect", column="journal",
               sorts=("freq", "az"),
               note="Journal name parsed from the Shark-References 'findspot' field."),
    FamilySpec("data_source", "Data source", "categorical", "multiselect", column="data_source",
               sorts=("freq", "az"),
               note="Where the record entered the corpus. Shark-References database: "
                    "the bibliography the corpus is built on (almost all papers). "
                    "Coauthor-contributed library: 5 papers added from a "
                    "coauthor's own library rather than from Shark-References. About 1,200 older records carry no source "
                    "tag and are not listed."),
    FamilySpec("oa_status", "Open-access (OA) status", "categorical", "multiselect",
               column="geo_oa_status", sorts=("freq", "best"),
               note="OA colour from OpenAlex/Unpaywall. Covers ~17% of papers."),
    FamilySpec("geo_oa_flags", "OA and geography flags", "bool_cols", "multiselect",
               columns=("geo_oa_is_oa", "geo_oa_journal_is_oa", "geo_oa_journal_is_in_doaj",
                        "geo_is_parachute_research")),
    # REMOVED options "Has study location" (geo_has_study_location) and "Has author
    # country" (geo_has_author_country): data-coverage flags, captured by the
    # Study country / First-author country families. 2026-10-08.
    FamilySpec("year", "Publication year", "range", "range", column="year"),
    # REMOVED "study_lat" / "study_lon" (geo_study_latitude / geo_study_longitude):
    # stored coordinates are magnitude-only (no negative values), so hemisphere
    # is lost upstream and Southern/Western ranges cannot match. Restore once
    # the upstream extraction is fixed. 2026-10-08.
]

# Display labels for the boolean flag columns. The parachute rule is the one in
# scripts/extract_study_locations_phase4*.py: author_country != study_country.
FLAG_LABELS = {
    "geo_oa_is_oa": "Paper is open access",
    "geo_oa_journal_is_oa": "Journal is fully open access",
    "geo_oa_journal_is_in_doaj": "Journal listed in DOAJ (Directory of Open Access Journals)",
    "geo_is_parachute_research":
        "Parachute research (first author's country differs from the study country)",
}

# Real countries only, for the "country_record" family (applied in serve.py's
# filters payload; the parquet is untouched). Sovereign states plus Taiwan, as in
# the study/first-author country families. Aliases map a raw spelling to the
# canonical name; a raw value is kept when its canonical form is in COUNTRIES.
# Deliberately absent: Georgia (a US state in this field), Antarctica, Greenland,
# Puerto Rico, French Guiana and other territories, continents, seas, US states
# and Canadian provinces. INFERRED: curated list, 2026-10-08.
COUNTRIES = frozenset(n.replace("~", " ") for n in """
Afghanistan Albania Algeria Angola Argentina Armenia Australia Austria Azerbaijan Bahamas Bahrain Ba
ngladesh Barbados Belarus Belgium Belize Benin Bhutan Bolivia Bosnia Botswana Brazil Brunei Bulgaria
 Burkina~Faso Burundi Cambodia Cameroon Canada Chad Chile China Colombia Comoros Congo Costa~Rica Cr
oatia Cuba Cyprus Czech~Republic Denmark Djibouti Dominican~Republic Ecuador Egypt El~Salvador Eritr
ea Estonia Ethiopia Fiji Finland France Gabon Gambia Germany Ghana Greece Guatemala Guinea Guyana Ha
iti Honduras Hungary Iceland India Indonesia Iran Iraq Ireland Israel Italy Jamaica Japan Jordan Kaz
akhstan Kenya Kuwait Kyrgyzstan Laos Latvia Lebanon Liberia Libya Lithuania Luxembourg Madagascar Ma
lawi Malaysia Maldives Mali Malta Mauritania Mauritius Mexico Micronesia Moldova Monaco Mongolia Mon
tenegro Morocco Mozambique Myanmar Namibia Nepal Netherlands New~Zealand Nicaragua Niger Nigeria Nor
th~Korea North~Macedonia Norway Oman Pakistan Palau Panama Papua~New~Guinea Paraguay Peru Philippine
s Poland Portugal Qatar Romania Russia Rwanda Samoa Saudi~Arabia Senegal Serbia Seychelles Sierra~Le
one Singapore Slovakia Slovenia Somalia South~Africa South~Korea South~Sudan Spain Sri~Lanka Sudan S
uriname Sweden Switzerland Syria Taiwan Tajikistan Tanzania Thailand Togo Tonga Trinidad Tunisia Tur
key Turkmenistan Uganda Ukraine United~Arab~Emirates United~Kingdom United~States Uruguay Uzbekistan
 Vanuatu Venezuela Vietnam Yemen Zambia Zimbabwe
""".split())
COUNTRY_ALIASES = {"UK": "United Kingdom", "USA": "United States", "US": "United States",
                   "Tunesia": "Tunisia", "Quatar": "Qatar", "Latvian": "Latvia"}


def is_country(v: str) -> bool:
    return COUNTRY_ALIASES.get(v, v) in COUNTRIES


# Display labels for categorical values whose raw text is a machine token.
VALUE_LABELS = {
    "country_record": {"Tunesia": "Tunisia", "Quatar": "Qatar", "Latvian": "Latvia"},
    "data_source": {"shark-references.com": "Shark-References database",
                    "coauthor_contribution": "Coauthor-contributed library"},
}

# Columns never offered as filters (identifiers / free-text / internals).
EXCLUDE = {
    "literature_id", "title", "authors", "abstract", "doi", "pdf_url",
    "date_added", "geo_first_author_institution", "geo_study_location_text",
    "geo_oa_url",
    # eco_1_guess / eco_2_guess / eco_3_guess: free-text first/second/third
    # habitat guesses (values like 'marine', 'brackish/estuarine'), not boolean
    # ecosystem flags; the panel showed them as "1 guess", "2 guess", "3 guess".
    "eco_1_guess", "eco_2_guess", "eco_3_guess",
}


def humanize(col: str, prefix: str | None) -> str:
    """Kept for callers; delegates to labels.label_for (acronyms, canonical names)."""
    from labels import label_for
    return label_for(col)


def sidecar_columns(all_columns: set[str]) -> list[str]:
    """Every parquet column the sidecar must carry, given the live schema."""
    cols: set[str] = {"literature_id"}
    for spec in FAMILY_SPECS:
        if spec.kind == "bool_prefix":
            cols.update(c for c in all_columns
                        if c.startswith(spec.prefix) and c not in EXCLUDE)
        elif spec.kind == "bool_cols":
            cols.update(c for c in spec.columns if c in all_columns)
        elif spec.kind in ("categorical", "range"):
            if spec.column in all_columns:
                cols.add(spec.column)
    return sorted(cols)


def resolve_families(present_columns: set[str]) -> list[FamilySpec]:
    """Drop specs whose backing column(s) are absent from the live schema."""
    live: list[FamilySpec] = []
    for spec in FAMILY_SPECS:
        if spec.kind == "author":
            live.append(spec)
        elif spec.kind == "bool_prefix":
            if any(c.startswith(spec.prefix) for c in present_columns):
                live.append(spec)
        elif spec.kind == "bool_cols":
            present = tuple(c for c in spec.columns if c in present_columns)
            if present:
                live.append(FamilySpec(**{**spec.__dict__, "columns": present}))
        elif spec.kind in ("categorical", "range"):
            if spec.column in present_columns:
                live.append(spec)
    return live
