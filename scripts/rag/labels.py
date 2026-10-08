#!/usr/bin/env python3
"""
Human-readable labels for filter options (Shark Oracle filter panel).

label_for(column)  -> display label for a sidecar column such as ``a_akde``
                      or ``b_north_atlantic``.
title_case(text)   -> Title Case with small words lowercase ("Gulf of Mexico").
epoch_rank / oa_rank -> sort keys for the Epoch and OA-status families.

Techniques use the canonical names in data/master_techniques.csv
(``technique_name``; the column id is ``a_`` + the name lower-cased with runs of
non-alphanumerics, other than & and /, collapsed to ``_``). Columns the
taxonomy no longer names fall back to the humanised column text.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

TECHNIQUES_CSV = Path(__file__).resolve().parents[2] / "data" / "master_techniques.csv"

# Display form of acronyms, lower-case token -> form. Whole tokens only.
ACRONYMS = {t.lower(): t for t in (
    "AKDE", "CPUE", "BRUV", "BRUVS", "eDNA", "GLM", "GAM", "GLMM", "BRT", "SDM",
    "MaxEnt", "PIT", "DNA", "RNA", "SNP", "mtDNA", "PCR", "ROV", "AUV", "UAV",
    "DIDSON", "MPA", "IUCN", "CITES", "FAO", "EEZ", "OA", "DOAJ", "SST", "ENSO",
    "PSAT", "SPOT", "VHF", "UV", "IUU", "BRD")}

# Short expansion, added only when the WHOLE label is that acronym.
EXPANSIONS = {
    "akde": "autocorrelated kernel density estimation",
    "cpue": "catch per unit effort",
    "bruv": "baited remote underwater video",
    "bruvs": "baited remote underwater video system",
    "sdm": "species distribution model",
    "glm": "generalised linear model",
    "gam": "generalised additive model",
    "glmm": "generalised linear mixed model",
    "brt": "boosted regression trees",
    "psat": "pop-up satellite archival tag",
    "edna": "environmental DNA",
    "pit": "passive integrated transponder",
    "rov": "remotely operated vehicle",
    "auv": "autonomous underwater vehicle",
    "uav": "unmanned aerial vehicle",
    "snp": "single-nucleotide polymorphism",
    "mpa": "marine protected area",
    "eez": "exclusive economic zone",
    "doaj": "Directory of Open Access Journals",
    "sst": "sea surface temperature",
    "iuu": "illegal, unreported and unregulated",
    "brd": "bycatch reduction device",
}

SMALL_WORDS = {"of", "the", "and", "in", "de", "la", "du", "on", "a", "an", "for", "to", "von", "van"}


def _fix_tokens(words: list[str]) -> list[str]:
    return [ACRONYMS.get(w.lower(), w) for w in words]


def title_case(text: str) -> str:
    """Title Case, small words lower-case except first; acronyms restored."""
    out = []
    for i, w in enumerate(str(text).replace("_", " ").split()):
        lw = w.lower()
        if lw in ACRONYMS:
            out.append(ACRONYMS[lw])
        elif i and lw in SMALL_WORDS:
            out.append(lw)
        else:
            out.append(w[:1].upper() + w[1:].lower() if w.isupper() or w.islower() else w)
    return " ".join(out)


def _slug(name: str) -> str:
    return "a_" + re.sub(r"[^a-z0-9&/]+", "_", str(name).lower()).strip("_")


@lru_cache(maxsize=1)
def _technique_names() -> dict[str, str]:
    try:
        import pandas as pd
        t = pd.read_csv(TECHNIQUES_CSV, usecols=["technique_name"])
    except Exception:  # noqa: BLE001 - labels must never break the server
        return {}
    return {_slug(n): str(n).strip() for n in t["technique_name"].dropna()}


def _humanise(core: str) -> str:
    """Sentence-ish text from a column core: first word capitalised, rest
    lower-case, acronyms restored."""
    words = re.split(r"[_\s]+", core.strip())
    words = [w for w in words if w]
    words = _fix_tokens([w.lower() for w in words])
    if words and words[0] == words[0].lower() and words[0] not in ACRONYMS.values():
        words[0] = words[0].capitalize()
    return " ".join(words)


def _decorate(label: str) -> str:
    """Upper-case acronym tokens in a label; add the expansion if the label is
    exactly one acronym."""
    key = label.strip().lower()
    if key in ACRONYMS:
        base = ACRONYMS[key]
        exp = EXPANSIONS.get(key)
        return f"{base} ({exp})" if exp else base
    return " ".join(_fix_tokens(label.split()))


def label_for(column: str) -> str:
    """Display label for a sidecar column (prefix aware)."""
    if column.startswith("a_"):
        name = _technique_names().get(column)
        label = name if name else _humanise(column[2:])
        return _decorate(label)
    for p in ("b_", "sb_"):
        if column.startswith(p):
            return title_case(column[len(p):])
    if column.startswith("gear_mit_"):
        return "Mitigation: " + _decorate(_humanise(column[len("gear_mit_"):]))
    for p in ("d_", "pr_", "gear_", "imp_", "eco_"):
        if column.startswith(p):
            return _decorate(_humanise(column[len(p):]))
    return _decorate(_humanise(column))


# --- ordering -------------------------------------------------------------

EPOCH_ORDER = ["Recent", "Holocene", "Pleistocene", "Pliocene", "Miocene", "Oligocene",
               "Eocene", "Paleocene", "Cretaceous", "Jurassic", "Triassic", "Permian",
               "Carboniferous", "Devonian", "Silurian", "Ordovician", "Cambrian"]
_EPOCH_RANK = {e.lower(): i for i, e in enumerate(EPOCH_ORDER)}


def epoch_label(value: str) -> str:
    return "Recent" if str(value).strip().lower() == "rezent" else str(value)


def epoch_rank(value: str) -> int:
    """Geological rank, newest first. 'Late Jurassic' ranks as Jurassic.
    Unknown labels (stages such as Maastrichtian) rank after all known ones."""
    s = epoch_label(value).strip().lower()
    s = re.sub(r"^(early|middle|late|lower|upper)\s+", "", s)
    return _EPOCH_RANK.get(s, len(EPOCH_ORDER))


OA_ORDER = ["diamond", "gold", "hybrid", "green", "bronze", "closed"]


def oa_rank(value: str) -> int:
    v = str(value).strip().lower()
    return OA_ORDER.index(v) if v in OA_ORDER else len(OA_ORDER)


def is_blank(v) -> bool:
    return v is None or str(v).strip().lower() in {"", "none", "nan", "null", "<na>"}
