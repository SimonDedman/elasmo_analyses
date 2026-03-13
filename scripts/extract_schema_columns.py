#!/usr/bin/env python3
"""
Extract ecosystem, pressure, gear, impact, and discipline metadata from elasmobranch papers.

Single-pass extraction: for each paper, extracts text from PDF (or falls back to
title + abstract), then searches for all four schema categories simultaneously.
Results are written as new columns to an enriched Parquet file.

Usage:
    python scripts/extract_schema_columns.py
    python scripts/extract_schema_columns.py --dry-run 100
    python scripts/extract_schema_columns.py --workers 4
    python scripts/extract_schema_columns.py --resume
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_BASE = Path(
    "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
)
PDF_BASE = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
INPUT_PARQUET = PROJECT_BASE / "outputs/literature_review.parquet"
OUTPUT_PARQUET = PROJECT_BASE / "outputs/literature_review_enriched.parquet"
EVIDENCE_CSV = PROJECT_BASE / "outputs/schema_extraction_evidence.csv"
RESUME_FILE = PROJECT_BASE / "outputs/.schema_extraction_progress.json"

TEXT_TIMEOUT = 10  # seconds for pdftotext
MAX_TEXT_BYTES = 500_000  # ~500 KB cap on extracted text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

@dataclass
class BinaryColumn:
    """A single binary (0/1) column produced by keyword matching.

    Attributes:
        name: Column name (e.g. "eco_marine").
        terms: Search terms (keywords, phrases, wildcards, raw regex).
        anchors: Co-occurrence anchors (impact columns). When set, at least
            one anchor must fire for binary=1.
        threshold: Minimum total mention count (summed across all terms)
            required for binary=1.  Higher values filter out passing mentions.
            Default 2 means a single mention is insufficient.
    """

    name: str
    terms: list[str]
    anchors: list[str] | None = None
    threshold: int = 2  # default: require ≥2 total mentions


@dataclass
class SchemaCategory:
    """A group of related binary columns (one of the four schemas)."""

    prefix: str
    columns: list[BinaryColumn] = field(default_factory=list)


# ---- Ecosystem schema ----------------------------------------------------

ECO = SchemaCategory(prefix="eco_", columns=[
    # Generic terms — high threshold (very common in elasmobranch lit)
    BinaryColumn("eco_marine", ["marine", "ocean", "sea", "saltwater"], threshold=3),
    BinaryColumn("eco_freshwater", ["freshwater", "freshwater river", "river shark", "river system", "riverine", "lake", "estuarine", "estuarin*", "brackish"], threshold=3),
    BinaryColumn("eco_brackish", ["estuar*", "brackish", "lagoon", "mangrove"], threshold=2),
    BinaryColumn("eco_pelagic", ["pelagic", "open ocean", "oceanic", "offshore", "epipelagic", "mesopelagic", "bathypelagic"], threshold=2),
    BinaryColumn("eco_coastal", ["coastal", "neritic", "inshore", "nearshore", "continental shelf"], threshold=3),
    BinaryColumn("eco_demersal", ["demersal", "benthic", "bottom-dwelling", "epibenthic", "benthopelagic"], threshold=2),
    # Specific habitat terms — lower threshold
    BinaryColumn("eco_reef", ["coral reef", "reef-associated", "rocky reef"], threshold=1),
    BinaryColumn("eco_deepwater", ["deep-sea", "deep-water", "abyssal", "hadal", "bathyal", "seamount"], threshold=2),
    BinaryColumn("eco_intertidal", ["intertidal", "tide pool", "littoral"], threshold=1),
    BinaryColumn("eco_mangrove", ["mangrove"], threshold=2),
    BinaryColumn("eco_seagrass", ["seagrass", "eelgrass", "Posidonia", "Zostera", "Thalassia"], threshold=1),
    BinaryColumn("eco_kelp", ["kelp forest", "kelp bed", "macroalgal"], threshold=1),
    BinaryColumn("eco_polar", ["polar", "arctic", "antarctic", "ice-edge", "sea ice"], threshold=2),
    BinaryColumn("eco_riverine", ["river shark", "freshwater stingray", "bull shark river"], threshold=1),
    BinaryColumn("eco_nursery", ["nursery habitat", "nursery ground", "nursery area", "essential fish habitat", "juvenile habitat"], threshold=1),
    BinaryColumn("eco_pupping", ["pupping ground", "pupping area", "parturition site", "birthing ground"], threshold=1),
    BinaryColumn("eco_epipelagic", ["epipelagic", "surface waters", "surface layer", "photic zone"], threshold=2),
    BinaryColumn("eco_mesopelagic", ["mesopelagic", "twilight zone"], threshold=1),
    BinaryColumn("eco_bathypelagic", ["bathypelagic", "deep scattering layer"], threshold=1),
    BinaryColumn("eco_abyssal", ["abyssal", "hadal"], threshold=1),
])

# ---- Pressure schema ------------------------------------------------------

PR = SchemaCategory(prefix="pr_", columns=[
    # Generic fishing terms — high threshold (mentioned in passing constantly)
    BinaryColumn("pr_fishing_commercial", ["commercial fish*", "industrial fish*", "fishing pressure", "fishing mortality", "exploitation"], threshold=3),
    BinaryColumn("pr_fishing_artisanal", ["artisanal", "small-scale fish*", "subsistence fish*", "traditional fish*"], threshold=2),
    BinaryColumn("pr_fishing_recreational", ["recreational fish*", "sport fish*", "game fish*", "catch-and-release", "angl*"], threshold=2),
    BinaryColumn("pr_fishing_iuu", ["illegal fish*", "unreported", "unregulated", "IUU", "poach*"], threshold=2),
    BinaryColumn("pr_bycatch", ["bycatch", "by-catch", "incidental capture", "non-target", "discards"], threshold=2),
    BinaryColumn("pr_shark_finning", ["shark fin*", "finning", "fin trade"], threshold=1),
    BinaryColumn("pr_targeted_fishing", ["targeted shark fish*", "directed shark fish*", "shark fish*"], threshold=2),
    # Environmental pressures — moderate threshold (threat-list problem)
    BinaryColumn("pr_climate_change", ["climate change", "global warming", "ocean warming"], threshold=3),
    BinaryColumn("pr_ocean_acidification", ["ocean acidification", "(acidification AND pH)", "(acidification AND pCO2)"], threshold=1),
    BinaryColumn("pr_hypoxia", ["hypoxia", "deoxygenation", "oxygen minimum zone", "OMZ"], threshold=1),
    BinaryColumn("pr_pollution_chemical", ["pollut*", "contaminant*", "heavy metal*", "mercury", "PCB", "PFAS", "pesticide*"], threshold=3),
    BinaryColumn("pr_pollution_plastic", ["plastic pollution", "microplastic*", "macroplastic*", "plastic ingestion", "plastic debris"], threshold=1),
    BinaryColumn("pr_pollution_noise", ["noise pollution", "anthropogenic noise", "shipping noise", "sonar", "acoustic disturbance"], threshold=1),
    BinaryColumn("pr_habitat_loss", ["habitat loss", "habitat degradation", "coastal development", "dredg*", "mangrove loss"], threshold=2),
    BinaryColumn("pr_shipping", ["ship strike", "vessel strike", "maritime traffic"], threshold=1),
    # Very specific terms — low threshold
    BinaryColumn("pr_tourism", ["dive tourism", "ecotourism", "shark tourism", "provisioning", "shark feed*", "cage div*"], threshold=1),
    BinaryColumn("pr_depredation", ["depredation", "depredating", "bait loss", "catch damage"], threshold=1),
    BinaryColumn("pr_aquaculture", ["aquaculture", "fish farm*", "mariculture"], threshold=1),
    BinaryColumn("pr_invasive", ["invasive species", "non-native species", "alien species"], threshold=1),
    BinaryColumn("pr_disease", ["disease", "pathogen", "parasite", "epizootic", "infection"], threshold=3),
    BinaryColumn("pr_light", ["light pollution", "artificial light", "ALAN"], threshold=1),
    BinaryColumn("pr_electromagnetic", ["electromagnetic field", "EMF", "submarine cable", "electroreception interference"], threshold=1),
    BinaryColumn("pr_cumulative", ["cumulative impact", "multiple stressor*", "synergistic", "additive effect"], threshold=2),
])

# ---- Gear schema ----------------------------------------------------------

GEAR = SchemaCategory(prefix="gear_", columns=[
    # Gear types — moderate threshold (often mentioned in methods of unrelated papers)
    BinaryColumn("gear_longline", ["longline", "long-line", "pelagic longline", "demersal longline", "bottom longline"], threshold=2),
    BinaryColumn("gear_gillnet", ["gillnet", "gill net", "trammel net", "entangling net", "drift net", "driftnet"], threshold=2),
    BinaryColumn("gear_trawl", ["trawl", "bottom trawl", "demersal trawl", "pelagic trawl", "otter trawl", "beam trawl", "shrimp trawl"], threshold=2),
    BinaryColumn("gear_purse_seine", ["purse seine", "purse-seine", "ring net"], threshold=1),
    BinaryColumn("gear_seine", ["beach seine", "Danish seine", "seine net"], threshold=1),
    BinaryColumn("gear_hook_line", ["hook and line", "handline", "rod and reel", "trolling", "jigging", "pole and line"], threshold=2),
    BinaryColumn("gear_trap", ["trap", "pot", "fish trap", "drumline", "SMART drumline"], threshold=2),
    BinaryColumn("gear_net_other", ["cast net", "lift net", "scoop net", "fyke net", "pound net", "weir"], threshold=1),
    BinaryColumn("gear_harpoon", ["harpoon", "spearfish*", "spear gun"], threshold=1),
    BinaryColumn("gear_survey", ["research vessel", "survey trawl", "BRUVs", "longline survey", "fishery-independent survey", "drone survey", "UAV survey", "ROV", "submersible"], threshold=2),
    BinaryColumn("gear_pelagic", ["pelagic longline", "pelagic trawl", "midwater trawl"], threshold=1),
    BinaryColumn("gear_demersal", ["demersal longline", "bottom trawl", "demersal trawl", "bottom longline"], threshold=1),
    BinaryColumn("gear_artisanal", ["artisanal", "traditional gear", "small-scale", "hand-operated"], threshold=2),
    # Mitigation — specific terms, low threshold
    BinaryColumn("gear_mit_circle_hook", ["circle hook", "non-offset hook"], threshold=1),
    BinaryColumn("gear_mit_brd", ["bycatch reduction device", "BRD", "turtle excluder", "TED"], threshold=1),
    BinaryColumn("gear_mit_deterrent", ["shark deterrent", "SharkGuard", "shark guard", "electropositive", "Rare Earth", "EPM", "LED deterrent", "magnetic deterrent"], threshold=1),
    BinaryColumn("gear_mit_time_area", ["time-area closure", "spatial closure", "fishing closure", "seasonal closure", "MPA"], threshold=2),
    BinaryColumn("gear_mit_handling", ["safe release", "handling practice*", "live release", "post-release mortality", "PRM"], threshold=1),
])

# ---- Impact schema (with scoring/anchors) ---------------------------------

IMP = SchemaCategory(prefix="imp_", columns=[
    # Impact columns use anchors for co-occurrence AND frequency thresholds
    BinaryColumn("imp_mortality", ["mortality", "survival rate", "lethality", "dead on arrival", "DOA", "at-vessel mortality", "AVM"], threshold=2),
    BinaryColumn("imp_post_release", ["post-release mortality", "PRM", "delayed mortality", "post-capture survival"], threshold=1),
    BinaryColumn("imp_abundance", ["abundance", "population size", "population decline", "population trend"], anchors=["population", "decline", "increase", "change", "trend", "status"], threshold=2),
    BinaryColumn("imp_cpue", ["CPUE", "catch per unit effort", "catch rate"], threshold=1),
    BinaryColumn("imp_biomass", ["biomass", "standing stock", "spawning stock biomass", "SSB"], threshold=2),
    BinaryColumn("imp_distribution", ["distribution shift", "range shift", "range contraction", "habitat shift"], threshold=1),
    BinaryColumn("imp_behaviour_change", ["behavioural change", "behavioral change", "avoidance behaviour", "flight response", "habituation"], anchors=["change", "response"], threshold=2),
    BinaryColumn("imp_physiology_stress", ["cortisol", "lactate", "blood chemistry", "acid-base", "reflex impairment", "RAMP", "physiological stress"], threshold=1),
    BinaryColumn("imp_injury", ["injury", "hooking injury", "scarring", "body condition index"], threshold=2),
    BinaryColumn("imp_reproduction", ["reproductive output", "fecundity change", "reproductive failure"], threshold=1),
    BinaryColumn("imp_growth", ["growth rate change", "stunting", "condition factor change"], anchors=["change", "impact"], threshold=2),
    BinaryColumn("imp_genetic", ["genetic diversity", "effective population size", r"Ne\b", "bottleneck", "inbreeding"], threshold=2),
    BinaryColumn("imp_trophic", ["trophic level change", "dietary shift", "prey depletion", "mesopredator release"], threshold=1),
    BinaryColumn("imp_habitat_quality", ["habitat quality", "habitat suitability", "degradation index"], threshold=2),
    BinaryColumn("imp_contamination", ["contaminant load", "bioaccumulation", "biomagnification", "tissue concentration"], threshold=1),
    BinaryColumn("imp_economic", ["economic value", "fishery value", "tourism revenue", "willingness to pay", "WTP"], threshold=1),
    BinaryColumn("imp_social", ["livelihood", "food security", "human dimension", "attitude", "perception"], threshold=3),
])

# ---- Discipline schema (research area classification) --------------------

DISC = SchemaCategory(prefix="d_", columns=[
    # Broad disciplines — higher threshold (terms appear in passing)
    BinaryColumn("d_biology", ["life history", "age and growth", "growth rate", "longevity", "maturity", "length-at-maturity", "length-weight", "vertebral band"], threshold=2),
    BinaryColumn("d_behaviour", ["behavio*", "behavioral ecology", "predator-prey", "diel vertical migration", "activity pattern", "social behavio*", "agonistic", "refuging"], threshold=3),
    BinaryColumn("d_trophic", ["trophic", "diet", "feeding ecology", "stomach content*", "prey composition", "stable isotope", "fatty acid", "food web"], threshold=2),
    BinaryColumn("d_genetics", ["genetic*", "genomic*", "eDNA", "environmental DNA", "microsatellite", "mitochondrial", "phylogenet*", "haplotype", "SNP", "RADseq", "population genetics"], threshold=2),
    BinaryColumn("d_movement", ["movement", "telemetry", "satellite tag*", "acoustic tag*", "archival tag*", "home range", "migration", "habitat use", "space use", "tracking"], threshold=3),
    BinaryColumn("d_fisheries", ["stock assessment", "fisheries management", "catch data", "fishing mortality", "maximum sustainable yield", "MSY", "fishery-dependent", "fishery-independent"], threshold=2),
    BinaryColumn("d_conservation", ["conservation", "endangered", "CITES", "IUCN", "Red List", "protected area", "marine protected area", "recovery plan", "conservation status"], threshold=3),
    BinaryColumn("d_data_science", ["machine learning", "deep learning", "neural network", "random forest", "Bayesian", "meta-analysis", "systematic review", "simulation model"], threshold=2),
    # Finer-grained disciplines — lower threshold (specific terms)
    BinaryColumn("d_husbandry", ["aquarium", "captive", "husbandry", "captive breeding", "ex situ", "tank-held", "aquaria"], threshold=2),
    BinaryColumn("d_paleontology", ["fossil", "paleontol*", "palaeontol*", "Cretaceous", "Jurassic", "Miocene", "Pliocene", "Eocene", "Oligocene", "Cenozoic", "Mesozoic", "Devonian", "Carboniferous"], threshold=1),
    BinaryColumn("d_taxonomy", ["taxonom*", "new species", "sp. nov.", "new genus", "morphometric*", "meristic*", "dichotomous key", "identification key", "redescription", "synonymy", "type specimen"], threshold=1),
    BinaryColumn("d_physiology", ["physiolog*", "metaboli*", "oxygen consumption", "ventilation rate", "blood gas", "haematocrit", "hematocrit", "osmoregulat*", "thermoregulat*", "bioenergetic*"], threshold=2),
    BinaryColumn("d_reproductive", ["reproductive biology", "fecundity", "gestation", "embryo*", "uterine", "ovipar*", "vivipar*", "mating", "parturition", "neonat*", "litter size", "reproductive cycle"], threshold=2),
    BinaryColumn("d_biomechanics", ["biomechani*", "functional morphology", "locomot*", "kinematics", "bite force", "jaw mechanics", "hydrodynamic*", "swimming performance"], threshold=1),
    BinaryColumn("d_sensory", ["electrorecept*", "ampullae of Lorenzini", "lateral line", "mechanosens*", "olfact*", "chemosens*", "visual acuity", "magnetorecept*"], threshold=1),
    BinaryColumn("d_ecotourism", ["ecotourism", "dive tourism", "shark tourism", "shark watching", "whale shark tourism", "shark encounter", "provisioning"], threshold=1),
    BinaryColumn("d_human_dimensions", ["human dimension*", "social science", "stakeholder", "perception", "attitude*", "willingness to pay", "WTP", "shark bite", "shark attack", "shark repellent"], threshold=2),
    BinaryColumn("d_immunology", ["immun*", "antibod*", "complement system", "innate immun*", "adaptive immun*", "leukocyte", "lymphocyte"], threshold=2),
    BinaryColumn("d_toxicology", ["toxicolog*", "contaminant*", "bioaccumulation", "biomagnification", "heavy metal*", "mercury", "methylmercury", "tissue concentration"], threshold=2),
])

# ---- Ocean basin schema (study geography) ---------------------------------

BASIN = SchemaCategory(prefix="b_", columns=[
    BinaryColumn("b_north_atlantic", [
        "North Atlantic", "Northwest Atlantic", "Northeast Atlantic",
        "NW Atlantic", "NE Atlantic", "North Sea", "Bay of Biscay",
        "Celtic Sea", "Norwegian Sea", "Barents Sea", "Baltic Sea",
        "Gulf of Mexico", "Sargasso Sea", "Azores",
    ], threshold=2),
    BinaryColumn("b_south_atlantic", [
        "South Atlantic", "Southwest Atlantic", "Southeast Atlantic",
        "SW Atlantic", "SE Atlantic", "Benguela", "Patagoni*",
        "South Africa*", "Namibia*", "Brazilian coast",
    ], threshold=2),
    BinaryColumn("b_north_pacific", [
        "North Pacific", "Northwest Pacific", "Northeast Pacific",
        "NW Pacific", "NE Pacific", "Bering Sea", "Sea of Japan",
        "East China Sea", "South China Sea", "Yellow Sea",
        "California Current", "Kuroshio", "Sea of Okhotsk",
        "Gulf of Alaska", "Hawaiian",
    ], threshold=2),
    BinaryColumn("b_south_pacific", [
        "South Pacific", "Southwest Pacific", "Southeast Pacific",
        "SW Pacific", "SE Pacific", "Coral Sea", "Tasman Sea",
        "Great Barrier Reef", "New Zealand*", "Fiji*",
        "French Polynesia", "Humboldt Current",
    ], threshold=2),
    BinaryColumn("b_indian_ocean", [
        "Indian Ocean", "Bay of Bengal", "Arabian Sea",
        "Mozambique Channel", "Red Sea", "Persian Gulf",
        "Andaman Sea", "Madagascar", "Maldives", "Seychelles",
        "Western Indian Ocean", "Eastern Indian Ocean",
    ], threshold=2),
    BinaryColumn("b_southern_ocean", [
        "Southern Ocean", "Antarctic", "sub-Antarctic",
        "Kerguelen", "South Georgia", "Patagonian shelf",
    ], threshold=1),
    BinaryColumn("b_arctic_ocean", [
        "Arctic Ocean", "Arctic", "Greenland Sea",
        "Beaufort Sea", "Chukchi Sea", "Canadian Arctic",
    ], threshold=2),
    BinaryColumn("b_mediterranean", [
        "Mediterranean", "Adriatic", "Aegean", "Tyrrhenian",
        "Ionian Sea", "Ligurian Sea", "Alboran Sea",
        "Strait of Gibraltar", "Strait of Sicily",
    ], threshold=1),
    BinaryColumn("b_caribbean", [
        "Caribbean", "Gulf of Mexico", "Bahamas", "Belize",
        "Mesoamerican Reef", "Antilles", "West Indies",
    ], threshold=2),
])

ALL_SCHEMAS = [ECO, PR, GEAR, IMP, DISC, BASIN]


# ---------------------------------------------------------------------------
# Regex compilation helpers
# ---------------------------------------------------------------------------

def _term_to_regex(term: str) -> re.Pattern[str]:
    """Convert a search term (possibly with wildcards or AND logic) to a compiled regex.

    Supports:
        - Wildcards: ``fish*`` becomes ``\\bfish\\w*``
        - Phrases: ``"post-release mortality"`` matches as a phrase
        - Whole-word anchors: ``\\bNe\\b`` passes through raw
        - AND logic: ``(acidification AND pH)`` returns a special marker
    """
    # AND logic is handled separately at match time; return None here
    if term.startswith("(") and " AND " in term:
        return None  # sentinel

    # If term already contains a regex word-boundary marker, compile as-is
    # Case-sensitive: raw regex terms have intentional casing (e.g. Ne\b)
    if r"\b" in term:
        return re.compile(term)

    # Wildcard expansion: fish* -> \bfish\w*
    if "*" in term:
        escaped = re.escape(term).replace(r"\*", r"\w*")
        return re.compile(r"\b" + escaped, re.IGNORECASE)

    # Plain phrase / keyword: whole-word match
    escaped = re.escape(term)
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


def _parse_and_term(term: str) -> tuple[str, str] | None:
    """Parse ``(acidification AND pH)`` into ``('acidification', 'pH')``."""
    m = re.match(r"^\((.+?)\s+AND\s+(.+?)\)$", term)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


@dataclass
class CompiledTerm:
    """A single search term compiled for matching."""

    raw: str
    regex: re.Pattern[str] | None  # None if AND-logic
    and_parts: tuple[re.Pattern[str], re.Pattern[str]] | None  # for AND terms


def compile_term(term: str) -> CompiledTerm:
    """Compile a single search term into a matchable structure."""
    and_pair = _parse_and_term(term)
    if and_pair:
        r1 = re.compile(r"\b" + re.escape(and_pair[0]) + r"\b", re.IGNORECASE)
        r2 = re.compile(r"\b" + re.escape(and_pair[1]) + r"\b", re.IGNORECASE)
        return CompiledTerm(raw=term, regex=None, and_parts=(r1, r2))
    return CompiledTerm(raw=term, regex=_term_to_regex(term), and_parts=None)


@dataclass
class CompiledColumn:
    """A binary column with all its terms and anchors pre-compiled."""

    name: str
    terms: list[CompiledTerm]
    anchors: list[re.Pattern[str]] | None
    threshold: int


def compile_schema(schema: SchemaCategory) -> list[CompiledColumn]:
    """Pre-compile all regex patterns for a schema category."""
    compiled: list[CompiledColumn] = []
    for col in schema.columns:
        c_terms = [compile_term(t) for t in col.terms]
        c_anchors = None
        if col.anchors:
            c_anchors = [
                re.compile(r"\b" + re.escape(a) + r"\b", re.IGNORECASE)
                for a in col.anchors
            ]
        compiled.append(CompiledColumn(
            name=col.name,
            terms=c_terms,
            anchors=c_anchors,
            threshold=col.threshold,
        ))
    return compiled


# ---------------------------------------------------------------------------
# Depth extraction
# ---------------------------------------------------------------------------

# Patterns like "0-200 m", "depths of 150 m", ">500 m", "shallow (<50 m)"
_DEPTH_RANGE_RE = re.compile(
    r"(\d{1,5}(?:\.\d+)?)\s*[-–—to]+\s*(\d{1,5}(?:\.\d+)?)\s*(?:m\b|meters?\b|metres?\b)",
    re.IGNORECASE,
)
_DEPTH_SINGLE_RE = re.compile(
    r"(?:depth[s]?\s+(?:of\s+)?|[><~≈]?\s*)(\d{1,5}(?:\.\d+)?)\s*(?:m\b|meters?\b|metres?\b)",
    re.IGNORECASE,
)


def extract_depth(text: str) -> dict[str, Any]:
    """Extract depth range information from text.

    Returns:
        Dictionary with keys depth_range, depth_min_m, depth_max_m.
    """
    result: dict[str, Any] = {
        "depth_range": None,
        "depth_min_m": None,
        "depth_max_m": None,
    }

    # Try range pattern first
    ranges = _DEPTH_RANGE_RE.findall(text)
    if ranges:
        all_vals = []
        for lo, hi in ranges:
            all_vals.extend([float(lo), float(hi)])
        result["depth_min_m"] = min(all_vals)
        result["depth_max_m"] = max(all_vals)
        result["depth_range"] = f"{result['depth_min_m']:.0f}-{result['depth_max_m']:.0f} m"
        return result

    # Fall back to individual depth mentions
    singles = _DEPTH_SINGLE_RE.findall(text)
    if singles:
        vals = [float(v) for v in singles]
        result["depth_min_m"] = min(vals)
        result["depth_max_m"] = max(vals)
        result["depth_range"] = f"{result['depth_min_m']:.0f}-{result['depth_max_m']:.0f} m"

    return result


# ---------------------------------------------------------------------------
# Target species extraction (gear context)
# ---------------------------------------------------------------------------

_TARGET_SPECIES_RE = re.compile(
    r"(?:targeting|target(?:ed)?\s+(?:species|catch)|"
    r"(\w+)\s+fishery|(\w+)\s+longline|(\w+)\s+trawl|"
    r"directed\s+at\s+(\w+))",
    re.IGNORECASE,
)


def extract_target_species(text: str) -> str | None:
    """Extract target species/group from gear-related context.

    Returns:
        Comma-separated species/group names, or None.
    """
    found: set[str] = set()
    for m in _TARGET_SPECIES_RE.finditer(text):
        for g in m.groups():
            if g and len(g) > 2 and g.lower() not in {
                "the", "and", "for", "was", "were", "with", "from", "this",
                "that", "each", "all", "its", "our", "their",
            }:
                found.add(g.lower())
    return ", ".join(sorted(found)) if found else None


# ---------------------------------------------------------------------------
# Impact direction & quantification
# ---------------------------------------------------------------------------

_NEGATIVE_CUES = re.compile(
    r"\b(?:decline[sd]?|decrease[sd]?|loss|reduce[sd]?|reduction|"
    r"deplet\w+|degrad\w+|lower|negative|threat|endanger|extinct|"
    r"collapse[sd]?|diminish\w*|worsen\w*)\b",
    re.IGNORECASE,
)
_POSITIVE_CUES = re.compile(
    r"\b(?:increase[sd]?|recover\w*|improve\w*|growth|positive|"
    r"restor\w+|enhance\w*|higher|gain|benefit|proliferat\w*)\b",
    re.IGNORECASE,
)
_QUANT_RE = re.compile(
    r"\d+\.?\d*\s*%|"                    # percentages
    r"\d+\.\d+|"                          # decimal numbers
    r"(?:CI|confidence interval)\s*[:=]|"  # confidence intervals
    r"p\s*[<>=]\s*0\.\d+|"               # p-values
    r"±\s*\d+",                           # plus-minus
    re.IGNORECASE,
)


def assess_impact_direction(text: str) -> str:
    """Determine overall impact direction from sentiment cues near impact terms."""
    neg = len(_NEGATIVE_CUES.findall(text))
    pos = len(_POSITIVE_CUES.findall(text))
    if neg > 0 and pos > 0:
        if neg > pos * 2:
            return "negative"
        if pos > neg * 2:
            return "positive"
        return "mixed"
    if neg > 0:
        return "negative"
    if pos > 0:
        return "positive"
    return "not stated"


def assess_impact_quantified(text: str) -> bool:
    """Check whether the paper provides quantitative impact measures."""
    return bool(_QUANT_RE.search(text))


# ---------------------------------------------------------------------------
# Ecosystem guess heuristics
# ---------------------------------------------------------------------------

_ECO_L1_MAP = {
    "eco_marine": "marine",
    "eco_freshwater": "freshwater",
    "eco_brackish": "brackish/estuarine",
}
_ECO_L2_MAP = {
    "eco_pelagic": "pelagic",
    "eco_coastal": "coastal",
    "eco_demersal": "demersal/benthic",
    "eco_reef": "reef",
    "eco_deepwater": "deep-water",
    "eco_intertidal": "intertidal",
    "eco_mangrove": "mangrove",
    "eco_seagrass": "seagrass",
    "eco_kelp": "kelp",
    "eco_polar": "polar",
    "eco_riverine": "riverine",
    "eco_nursery": "nursery",
    "eco_pupping": "pupping",
}
_ECO_L3_MAP = {
    "eco_epipelagic": "epipelagic",
    "eco_mesopelagic": "mesopelagic",
    "eco_bathypelagic": "bathypelagic",
    "eco_abyssal": "abyssal",
}


def eco_guesses(row: dict[str, Any]) -> dict[str, str | None]:
    """Generate best-guess ecosystem columns from binary results."""
    result: dict[str, str | None] = {
        "eco_1_guess": None,
        "eco_2_guess": None,
        "eco_3_guess": None,
    }
    # L1: realm
    for col, label in _ECO_L1_MAP.items():
        if row.get(col, 0) == 1:
            result["eco_1_guess"] = label
            break
    # L2: zone
    for col, label in _ECO_L2_MAP.items():
        if row.get(col, 0) == 1:
            result["eco_2_guess"] = label
            break
    # L3: depth zone
    for col, label in _ECO_L3_MAP.items():
        if row.get(col, 0) == 1:
            result["eco_3_guess"] = label
            break
    return result


# ---------------------------------------------------------------------------
# PDF lookup index
# ---------------------------------------------------------------------------

def _normalise_name(s: str) -> str:
    """Strip accents, hyphens, apostrophes, and spaces; lowercase.

    ``"Abd-Elhameed"`` → ``"abdelhameed"``
    ``"Araújo"``       → ``"araujo"``
    ``"O'Brien"``      → ``"obrien"``
    """
    import unicodedata

    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace("-", "").replace(" ", "").replace("'", "").replace("ʼ", "")


def _title_words(title: str) -> set[str]:
    """Extract a set of normalised content words from a title (for disambiguation)."""
    stops = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "or", "s",
        "that", "the", "to", "was", "were", "will", "with",
    }
    words = set(re.findall(r"[a-z]{3,}", _normalise_name(title)))
    return words - stops


def build_pdf_index(pdf_dir: Path) -> dict[tuple[str, int], list[Path]]:
    """Build a lookup from (normalised_first_author, year) to PDF paths.

    Normalisation strips accents, hyphens, and spaces so that
    ``"Abd-Elhameed"`` in the parquet matches ``"Abdelhameed"`` in the
    filename.

    Returns:
        Dictionary mapping (normalised_surname, year_int) to list of paths.
    """
    index: dict[tuple[str, int], list[Path]] = {}
    for year_dir in sorted(pdf_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for pdf in year_dir.glob("*.pdf"):
            parts = pdf.stem.split(".")
            if len(parts) >= 2:
                surname = _normalise_name(parts[0])
            else:
                # Legacy numeric naming
                surname = _normalise_name(pdf.stem.split("_")[0])
            key = (surname, year)
            index.setdefault(key, []).append(pdf)
    return index


def _first_surname(authors: str | None) -> str | None:
    """Extract the first author's normalised surname from the authors string.

    Handles formats like:
        ``"Smith, J. & Jones, K. (2020)"``
        ``"Abd-Elhameed, S. & Abd-Elhameed, M. (2025)"``
    """
    if not authors or not isinstance(authors, str):
        return None
    parts = authors.split(",")
    if parts:
        surname = parts[0].strip()
        surname = re.sub(r"\s*\(\d{4}\)\s*$", "", surname)
        return _normalise_name(surname) if surname else None
    return None


def _pick_best_pdf(
    candidates: list[Path], title: str | None
) -> Path | None:
    """Disambiguate when multiple PDFs match (surname, year).

    Compares title words from the parquet against title words embedded
    in the PDF filename.  Returns the candidate with the most overlap,
    or the first candidate if no title is available.
    """
    if not candidates:
        return None
    if len(candidates) == 1 or not title:
        return candidates[0]

    paper_words = _title_words(title)
    if not paper_words:
        return candidates[0]

    best_path = candidates[0]
    best_overlap = 0
    for pdf_path in candidates:
        # Extract title portion from filename: skip surname, "etal", year
        parts = pdf_path.stem.split(".")
        title_parts = [
            p for p in parts
            if p.lower() not in ("etal",) and not p.isdigit()
        ]
        # Skip the first part (surname)
        if len(title_parts) > 1:
            title_parts = title_parts[1:]
        file_words = set()
        for p in title_parts:
            file_words |= set(re.findall(r"[a-z]{3,}", p.lower()))
        overlap = len(paper_words & file_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_path = pdf_path
    return best_path


# ---------------------------------------------------------------------------
# Text extraction & cleaning
# ---------------------------------------------------------------------------

# Patterns for stripping non-body sections from extracted text.
# These sections inflate false positives (author names in headers,
# journal titles in references, affiliation place-names, etc.).

# References section: "References", "REFERENCES", "Bibliography", etc.
# on its own line (possibly with leading whitespace).
_REF_HEADER_RE = re.compile(
    r"^[\s]*(REFERENCES|References|BIBLIOGRAPHY|Bibliography|"
    r"LITERATURE\s+CITED|Literature\s+[Cc]ited|WORKS\s+CITED|Works\s+[Cc]ited)"
    r"[\s]*$",
    re.MULTILINE,
)

# Abstract header: marks the start of useful content.
# Matches both standalone headers ("Abstract\n") and inline ("Abstract: text..." / "ABSTRACT. text...")
_ABSTRACT_RE = re.compile(
    r"^[\s]*(ABSTRACT|Abstract|SUMMARY|Summary|INTRODUCTION|Introduction)"
    r"[\s]*[:.]*",
    re.MULTILINE,
)

# Acknowledgements section (strip to avoid institution/funder name matches).
_ACK_HEADER_RE = re.compile(
    r"^[\s]*(ACKNOWLEDG[E]?MENTS?|Acknowledg[e]?ments?|"
    r"FUNDING|Funding|AUTHOR\s+CONTRIBUTIONS?|Author\s+[Cc]ontributions?|"
    r"DATA\s+AVAILABILITY|Data\s+[Aa]vailability|"
    r"CONFLICT[S]?\s+OF\s+INTEREST|Conflict[s]?\s+of\s+[Ii]nterest|"
    r"DECLARATION|Declaration)"
    r"[\s]*$",
    re.MULTILINE,
)


def strip_non_body_sections(text: str) -> str:
    """Remove header/author block, references, and acknowledgements from PDF text.

    Keeps only the body of the paper (abstract through to the end of the
    discussion/conclusion).  Falls back to the full text if section markers
    cannot be found (better to search noisy text than no text).

    Sections removed:
        1. Everything **before** the first Abstract/Introduction header
           (catches journal metadata, author names, affiliations, editors).
        2. The **References / Bibliography** section and everything after it.
        3. **Acknowledgements, Author Contributions, Data Availability,
           Conflict of Interest, Funding** blocks (which sit between the
           discussion and the references in many journals).
    """
    # --- Step 1: trim front matter (before abstract/introduction) ---
    abstract_match = _ABSTRACT_RE.search(text)
    if abstract_match:
        text = text[abstract_match.start():]

    # --- Step 2: remove references and everything after ---
    ref_match = _REF_HEADER_RE.search(text)
    if ref_match:
        text = text[:ref_match.start()]

    # --- Step 3: remove acknowledgements / back-matter blocks ---
    # These may appear before references (already trimmed) or at the
    # very end of what remains.  Remove from the FIRST such header onward
    # only if it appears in the last 30% of the remaining text (to avoid
    # stripping a paragraph that merely mentions "acknowledgement" in passing).
    ack_match = _ACK_HEADER_RE.search(text)
    if ack_match and ack_match.start() > len(text) * 0.7:
        text = text[:ack_match.start()]

    return text


def extract_text_from_pdf(pdf_path: Path) -> str | None:
    """Extract text from a PDF using pdftotext with timeout.

    Returns body text only (header, references, and acknowledgements
    stripped).  Returns None on failure.
    """
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=TEXT_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        text = result.stdout
        if not text:
            return None
        if len(text.encode("utf-8", errors="ignore")) > MAX_TEXT_BYTES:
            text = text[:MAX_TEXT_BYTES]

        # Strip non-body sections to reduce false positives
        text = strip_non_body_sections(text)

        return text if text.strip() else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


# ---------------------------------------------------------------------------
# Core matching engine
# ---------------------------------------------------------------------------

# These are initialised once per worker via init_worker()
_COMPILED_SCHEMAS: list[tuple[str, list[CompiledColumn]]] = []
_PDF_INDEX: dict[tuple[str, int], list[Path]] = {}


def init_worker(pdf_index: dict[tuple[str, int], list[Path]]) -> None:
    """Initialise global state for each worker process."""
    global _COMPILED_SCHEMAS, _PDF_INDEX
    _COMPILED_SCHEMAS = [
        (schema.prefix.rstrip("_"), compile_schema(schema))
        for schema in ALL_SCHEMAS
    ]
    _PDF_INDEX = pdf_index


@dataclass
class MatchResult:
    """Result of matching a single column against text."""

    binary: int                    # 0 or 1
    total_freq: int                # total mention count across all terms
    term_count: int                # number of distinct terms that fired
    matched_terms: list[str]       # which search terms fired (with frequency)
    matched_anchors: list[str]     # which anchor terms fired
    sample_context: str | None     # short text snippet around first match


def _extract_context(text: str, pattern: re.Pattern[str], window: int = 80) -> str | None:
    """Return a short context snippet around the first match."""
    m = pattern.search(text)
    if not m:
        return None
    start = max(0, m.start() - window)
    end = min(len(text), m.end() + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


def _count_matches(pattern: re.Pattern[str], text: str) -> int:
    """Count non-overlapping occurrences of a pattern in text."""
    return len(pattern.findall(text))


def _match_column(text: str, col: CompiledColumn) -> MatchResult:
    """Match a single column's terms against text using frequency counting.

    Every term is counted (not just detected), and the total mention count
    across all terms is compared to the column's threshold to decide
    binary classification.  For columns with anchors, at least one anchor
    must also fire.

    Returns a MatchResult with frequencies, binary decision, and evidence.
    """
    fired_terms: list[tuple[str, int]] = []  # (term_raw, frequency)
    first_regex: re.Pattern[str] | None = None
    total_freq = 0

    for ct in col.terms:
        if ct.and_parts is not None:
            # AND logic: both parts must be present; count = min of the two
            c1 = _count_matches(ct.and_parts[0], text)
            c2 = _count_matches(ct.and_parts[1], text)
            if c1 > 0 and c2 > 0:
                freq = min(c1, c2)
                fired_terms.append((ct.raw, freq))
                total_freq += freq
                if first_regex is None:
                    first_regex = ct.and_parts[0]
        elif ct.regex is not None:
            freq = _count_matches(ct.regex, text)
            if freq > 0:
                fired_terms.append((ct.raw, freq))
                total_freq += freq
                if first_regex is None:
                    first_regex = ct.regex

    if not fired_terms:
        return MatchResult(binary=0, total_freq=0, term_count=0,
                           matched_terms=[], matched_anchors=[],
                           sample_context=None)

    term_count = len(fired_terms)
    # Format matched_terms with frequency: "marine(12); ocean(5)"
    matched_terms_str = [f"{t}({f})" for t, f in fired_terms]

    # Context snippet from the first matching term
    context = _extract_context(text, first_regex, window=80) if first_regex else None

    # Anchor matching
    fired_anchors: list[str] = []
    if col.anchors:
        for anc in col.anchors:
            if anc.search(text):
                fired_anchors.append(anc.pattern.replace(r"\b", "").replace("\\", ""))

    # Binary decision: threshold on total frequency, plus anchor gate
    if col.anchors and not fired_anchors:
        # Anchors defined but none fired — reject regardless of frequency
        binary = 0
    elif total_freq >= col.threshold:
        binary = 1
    else:
        binary = 0

    return MatchResult(binary=binary, total_freq=total_freq,
                       term_count=term_count, matched_terms=matched_terms_str,
                       matched_anchors=fired_anchors, sample_context=context)


def process_paper(row_dict: dict[str, Any]) -> dict[str, Any]:
    """Process a single paper: extract text, match all schemas.

    Args:
        row_dict: Dictionary of parquet columns for this paper.

    Returns:
        Dictionary of new column values for this paper.
    """
    global _COMPILED_SCHEMAS, _PDF_INDEX

    lit_id = row_dict.get("literature_id")
    title = row_dict.get("title") or ""
    abstract = row_dict.get("abstract") or ""
    authors = row_dict.get("authors")
    year_raw = row_dict.get("year")
    doi = row_dict.get("doi") or ""

    # Fallback identifier for orphan rows (no literature_id)
    if lit_id is None or (isinstance(lit_id, float) and math.isnan(lit_id)):
        # Use DOI if available, else row index
        lit_id_for_evidence = doi if doi else f"orphan_{row_dict.get('_row_idx', 'unknown')}"
    else:
        lit_id_for_evidence = lit_id

    # Safe year handling (float bug)
    year: int | None = None
    if year_raw is not None and not (isinstance(year_raw, float) and np.isnan(year_raw)):
        year = int(year_raw)

    # ---- Resolve PDF and extract text ----
    text_parts: list[str] = []
    pdf_found = False

    if authors and year:
        surname = _first_surname(authors)
        if surname:
            candidates = _PDF_INDEX.get((surname, year), [])
            best_pdf = _pick_best_pdf(candidates, title)
            if best_pdf is not None:
                extracted = extract_text_from_pdf(best_pdf)
                if extracted:
                    text_parts.append(extracted)
                    pdf_found = True

    # Only use PDF text — skip papers without PDFs
    full_text = "\n".join(text_parts)

    if not full_text.strip():
        # No PDF text available — return empty result (no title/abstract fallback)
        result: dict[str, Any] = {"literature_id": lit_id, "_pdf_found": False, "_evidence": []}
        for _, compiled_cols in _COMPILED_SCHEMAS:
            for col in compiled_cols:
                result[col.name] = 0
        # Text columns
        result.update({
            "eco_1_guess": None, "eco_2_guess": None, "eco_3_guess": None,
            "depth_range": None, "depth_min_m": None, "depth_max_m": None,
            "gear_target_species": None,
            "imp_direction": "not stated", "imp_quantified": False,
            "imp_confidence": "{}",
        })
        return result

    # ---- Match all schemas ----
    result = {"literature_id": lit_id, "_pdf_found": pdf_found}
    imp_scores: dict[str, int] = {}
    evidence_rows: list[dict[str, Any]] = []  # for evidence table

    for schema_name, compiled_cols in _COMPILED_SCHEMAS:
        for col in compiled_cols:
            mr = _match_column(full_text, col)
            result[col.name] = mr.binary
            if mr.total_freq > 0:
                imp_scores[col.name] = mr.total_freq
            # Record evidence for any column that had matches (even if binary=0)
            if mr.matched_terms:
                evidence_rows.append({
                    "literature_id": lit_id_for_evidence,
                    "title": title[:200] if title else "",
                    "column": col.name,
                    "binary": mr.binary,
                    "total_freq": mr.total_freq,
                    "term_count": mr.term_count,
                    "threshold": col.threshold,
                    "matched_terms": "; ".join(mr.matched_terms),
                    "matched_anchors": "; ".join(mr.matched_anchors) if mr.matched_anchors else "",
                    "context": mr.sample_context or "",
                })

    # Stash evidence on the result dict (collected later)
    result["_evidence"] = evidence_rows

    # ---- Ecosystem guesses ----
    result.update(eco_guesses(result))

    # ---- Depth extraction ----
    result.update(extract_depth(full_text))

    # ---- Gear target species ----
    result["gear_target_species"] = extract_target_species(full_text)

    # ---- Impact direction & quantification ----
    # Only assess if any impact column is flagged
    any_impact = any(
        result.get(col.name, 0) == 1
        for _, compiled_cols in _COMPILED_SCHEMAS
        if _ == "imp"
        for col in compiled_cols
    )
    if any_impact or imp_scores:
        result["imp_direction"] = assess_impact_direction(full_text)
        result["imp_quantified"] = assess_impact_quantified(full_text)
    else:
        result["imp_direction"] = "not stated"
        result["imp_quantified"] = False

    # ---- Impact confidence JSON ----
    result["imp_confidence"] = json.dumps(imp_scores) if imp_scores else "{}"

    return result


# ---------------------------------------------------------------------------
# Resume tracking
# ---------------------------------------------------------------------------

def load_processed_ids(resume_file: Path) -> set[str]:
    """Load set of already-processed literature_ids from the resume file."""
    if resume_file.exists():
        try:
            with open(resume_file, "r") as f:
                data = json.load(f)
            return set(data.get("processed_ids", []))
        except (json.JSONDecodeError, KeyError):
            return set()
    return set()


def save_processed_ids(resume_file: Path, ids: set[str]) -> None:
    """Save processed literature_ids to the resume file."""
    with open(resume_file, "w") as f:
        json.dump({"processed_ids": sorted(ids)}, f)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the schema extraction pipeline."""
    parser = argparse.ArgumentParser(
        description="Extract ecosystem, pressure, gear, impact, and discipline metadata from elasmobranch papers."
    )
    parser.add_argument(
        "--dry-run",
        type=int,
        default=0,
        metavar="N",
        help="Process only N papers and print results without writing.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, cpu_count() - 1),
        metavar="W",
        help="Number of parallel workers (default: cpu_count - 1).",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PDF_BASE,
        help="Root directory containing YYYY/ folders of PDFs.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_PARQUET,
        metavar="PATH",
        help="Input parquet file (default: literature_review.parquet).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip papers already processed in a previous run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        metavar="B",
        help="Write progress every B papers (default: 500).",
    )
    args = parser.parse_args()

    # ---- Load data ----
    input_path = args.input
    logger.info("Loading parquet: %s", input_path)
    df = pd.read_parquet(input_path)
    logger.info("Loaded %d papers with %d columns.", len(df), len(df.columns))

    # ---- Build PDF index ----
    logger.info("Building PDF index from %s ...", args.pdf_dir)
    pdf_index = build_pdf_index(args.pdf_dir)
    total_pdfs = sum(len(v) for v in pdf_index.values())
    logger.info("Indexed %d PDF files across %d (author, year) keys.", total_pdfs, len(pdf_index))

    # ---- Prepare rows to process ----
    # Columns we need from the parquet for matching
    needed_cols = ["literature_id", "title", "abstract", "authors", "year", "doi"]
    rows = df[needed_cols].to_dict("records")
    # Tag each row with its dataframe index for orphan identification
    for i, row in enumerate(rows):
        row["_row_idx"] = i

    # Resume: skip already-processed
    processed_ids: set[str] = set()
    if args.resume:
        processed_ids = load_processed_ids(RESUME_FILE)
        before = len(rows)
        rows = [r for r in rows if str(r.get("literature_id")) not in processed_ids]
        logger.info("Resume: skipping %d already-processed papers, %d remaining.", before - len(rows), len(rows))

    # Dry-run: limit
    if args.dry_run > 0:
        rows = rows[: args.dry_run]
        logger.info("Dry-run mode: processing %d papers.", len(rows))

    if not rows:
        logger.info("No papers to process. Exiting.")
        return

    # ---- Process papers ----
    results: list[dict[str, Any]] = []
    n_workers = min(args.workers, len(rows))
    logger.info("Processing %d papers with %d workers ...", len(rows), n_workers)

    if n_workers <= 1:
        # Single-process mode (easier debugging)
        init_worker(pdf_index)
        for row in tqdm(rows, desc="Extracting", unit="paper"):
            results.append(process_paper(row))
    else:
        # Multiprocessing
        with Pool(
            processes=n_workers,
            initializer=init_worker,
            initargs=(pdf_index,),
        ) as pool:
            for result in tqdm(
                pool.imap_unordered(process_paper, rows, chunksize=50),
                total=len(rows),
                desc="Extracting",
                unit="paper",
            ):
                results.append(result)

                # Periodic resume checkpoint
                if args.resume and len(results) % args.batch_size == 0:
                    new_ids = {str(r["literature_id"]) for r in results}
                    save_processed_ids(RESUME_FILE, processed_ids | new_ids)

    # ---- Collect evidence rows and strip from results ----
    all_evidence: list[dict[str, Any]] = []
    for r in results:
        all_evidence.extend(r.pop("_evidence", []))

    # ---- Summarise results ----
    results_df = pd.DataFrame(results)

    # Save intermediate results before the merge step (insurance against OOM)
    intermediate_path = PROJECT_BASE / "outputs/.schema_extraction_results.parquet"
    results_df.to_parquet(intermediate_path, index=False)
    logger.info("Intermediate results saved: %s (%d rows)", intermediate_path, len(results_df))

    # Count statistics
    pdf_count = results_df["_pdf_found"].sum()
    logger.info(
        "Text sources: %d with PDF text, %d skipped (no PDF).",
        pdf_count,
        len(results_df) - pdf_count,
    )

    # Binary column hit rates
    binary_cols = [
        col.name
        for schema in ALL_SCHEMAS
        for col in schema.columns
    ]
    print("\n=== Column hit rates ===")
    for col_name in binary_cols:
        if col_name in results_df.columns:
            n_hits = int(results_df[col_name].sum())
            pct = n_hits / len(results_df) * 100 if len(results_df) > 0 else 0
            if n_hits > 0:
                print(f"  {col_name:35s} {n_hits:>6d}  ({pct:5.1f}%)")

    # Depth extraction stats
    depth_count = results_df["depth_min_m"].notna().sum()
    print(f"\n  Depth extracted: {depth_count} papers")

    # Impact direction distribution
    if "imp_direction" in results_df.columns:
        print("\n=== Impact direction ===")
        for val, cnt in results_df["imp_direction"].value_counts().items():
            print(f"  {val:20s} {cnt:>6d}")

    # ---- Evidence summary ----
    evidence_df = pd.DataFrame(all_evidence)
    if not evidence_df.empty:
        print(f"\n=== Evidence rows: {len(evidence_df)} total ===")
        print(f"  Columns with evidence: {evidence_df['column'].nunique()}")
        print(f"  Papers with evidence:  {evidence_df['literature_id'].nunique()}")

    # ---- Write output ----
    if args.dry_run > 0:
        print("\n=== Dry-run: sample results (first 5 papers) ===")
        sample_cols = ["literature_id", "_pdf_found"] + binary_cols[:10] + [
            "eco_1_guess", "depth_range", "imp_direction", "imp_confidence",
        ]
        existing = [c for c in sample_cols if c in results_df.columns]
        print(results_df[existing].head(5).to_string(index=False))

        if not evidence_df.empty:
            print("\n=== Dry-run: sample evidence (first 10 rows) ===")
            print(evidence_df.head(10).to_string(index=False))
        logger.info("Dry-run complete. No files written.")
        return

    # Drop internal column before merge
    results_df = results_df.drop(columns=["_pdf_found"], errors="ignore")

    # Merge with original dataframe.
    # Cannot use literature_id as index (2,327 rows have empty/NaN IDs).
    # Instead, build a dict lookup and assign column-by-column to avoid
    # pd.merge allocating a huge intermediate array (62 GiB on 30K × 1546).
    df["literature_id"] = df["literature_id"].astype(str)
    results_df["literature_id"] = results_df["literature_id"].astype(str)

    new_cols = [c for c in results_df.columns if c != "literature_id"]

    # Drop any pre-existing schema columns from original to avoid conflicts
    df = df.drop(columns=[c for c in new_cols if c in df.columns], errors="ignore")

    # Build lookup: literature_id -> first matching result row index
    # (handles duplicates by taking first match)
    results_lookup: dict[str, int] = {}
    for i, lit_id in enumerate(results_df["literature_id"]):
        if lit_id not in results_lookup:
            results_lookup[lit_id] = i

    # Map each row in df to its result row
    result_indices = [results_lookup.get(str(lid), -1) for lid in df["literature_id"]]

    # Assign new columns one at a time (memory-efficient)
    for col_name in new_cols:
        col_values = results_df[col_name].values
        df[col_name] = [col_values[i] if i >= 0 else None for i in result_indices]

    # Fill NaN for binary columns (papers not processed)
    for col_name in binary_cols:
        if col_name in df.columns:
            df[col_name] = df[col_name].fillna(0).astype(int)

    logger.info("Writing enriched parquet: %s", OUTPUT_PARQUET)
    df.to_parquet(OUTPUT_PARQUET, index=False)
    logger.info(
        "Done. Output has %d rows and %d columns (%d new).",
        len(df),
        len(df.columns),
        len(new_cols),
    )

    # Write evidence table
    if not evidence_df.empty:
        evidence_df.to_csv(EVIDENCE_CSV, index=False)
        logger.info(
            "Evidence table: %s (%d rows across %d papers).",
            EVIDENCE_CSV,
            len(evidence_df),
            evidence_df["literature_id"].nunique(),
        )

    # Save resume state
    if args.resume:
        new_ids = {str(r["literature_id"]) for r in results}
        save_processed_ids(RESUME_FILE, processed_ids | new_ids)
        logger.info("Resume state saved: %d total processed.", len(processed_ids | new_ids))


if __name__ == "__main__":
    main()
