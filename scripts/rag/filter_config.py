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
               column="geo_study_country",
               note="Reliable study-location field (geo pipeline)."),
    FamilySpec("study_basin", "Study ocean basin", "categorical", "multiselect",
               column="geo_study_ocean_basin"),
    FamilySpec("author_country", "First-author country", "categorical", "multiselect",
               column="geo_first_author_country"),
    FamilySpec("author_region", "First-author region", "categorical", "multiselect",
               column="geo_first_author_region"),
    FamilySpec("country_record", "Country (record field)", "categorical", "multiselect",
               column="country"),
    FamilySpec("superregion", "Super-region", "categorical", "multiselect",
               column="superregion"),
    FamilySpec("epoch", "Epoch", "categorical", "multiselect", column="epoch"),
    FamilySpec("journal", "Journal", "categorical", "search-multiselect", column="journal"),
    FamilySpec("data_source", "Data source", "categorical", "multiselect", column="data_source"),
    FamilySpec("oa_status", "Open-access status", "categorical", "multiselect",
               column="geo_oa_status"),
    FamilySpec("geo_oa_flags", "Open-access / geography flags", "bool_cols", "multiselect",
               columns=("geo_oa_is_oa", "geo_oa_journal_is_oa", "geo_oa_journal_is_in_doaj",
                        "geo_is_parachute_research", "geo_has_study_location",
                        "geo_has_author_country")),
    FamilySpec("year", "Publication year", "range", "range", column="year"),
    FamilySpec("study_lat", "Study latitude", "range", "range",
               column="geo_study_latitude",
               note="CAVEAT: stored coordinates are magnitude-only (no negative "
                    "values in the data) — hemisphere sign is lost upstream, so "
                    "Southern/Western ranges will not match. Upstream extraction "
                    "fix pending."),
    FamilySpec("study_lon", "Study longitude", "range", "range",
               column="geo_study_longitude",
               note="CAVEAT: magnitude-only (see latitude). Upstream fix pending."),
]

# Columns never offered as filters (identifiers / free-text / internals).
EXCLUDE = {
    "literature_id", "title", "authors", "abstract", "doi", "pdf_url",
    "date_added", "geo_first_author_institution", "geo_study_location_text",
    "geo_oa_url",
}


def humanize(col: str, prefix: str | None) -> str:
    core = col[len(prefix):] if prefix and col.startswith(prefix) else col
    return core.replace("_", " ").replace("&", "&").strip().capitalize()


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
