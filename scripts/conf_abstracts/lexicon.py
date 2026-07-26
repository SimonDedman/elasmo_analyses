"""Deterministic elasmobranch lexicon for content-based is_elasmo detection.

More reliable than a small LLM for the binary elasmo flag (e.g. qwen2.5:3b
mis-classified smalltooth sawfish). Covers common names, higher taxa, and a
broad set of chondrichthyan genera.
"""
import re

# Common names & higher taxa (word-boundary, case-insensitive).
_COMMON = [
    r"elasmobranch", r"chondrichthy", r"selachi", r"batoid", r"neoselachi",
    r"\bshark", r"\bray\b", r"\brays\b", r"skate", r"sawfish", r"guitarfish",
    r"stingray", r"stingaree", r"eagle ray", r"manta", r"mobulid", r"devil ray",
    r"electric ray", r"torpedo ray", r"numbfish", r"wedgefish", r"shovelnose",
    r"chimaer", r"ratfish", r"rabbitfish", r"ghost shark", r"elephant fish",
    r"dogfish", r"catshark", r"houndshark", r"hammerhead", r"requiem shark",
    r"thresher", r"mako", r"wobbegong", r"angelshark", r"sawshark", r"lamnid",
    r"carcharhinid", r"squalid", r"whaler", r"gummy shark", r"school shark",
    r"nurse shark", r"reef shark", r"bull shark", r"tiger shark", r"lemon shark",
    r"white shark", r"basking shark", r"whale shark", r"megamouth",
    r"cownose", r"butterfly ray", r"round ray", r"bat ray",
]

# Chondrichthyan genera (common in abstract titles).
_GENERA = [
    "Carcharhinus", "Carcharodon", "Carcharias", "Sphyrna", "Galeocerdo",
    "Negaprion", "Prionace", "Rhizoprionodon", "Mustelus", "Triakis", "Galeorhinus",
    "Squalus", "Squatina", "Isurus", "Lamna", "Alopias", "Cetorhinus", "Rhincodon",
    "Ginglymostoma", "Stegostoma", "Orectolobus", "Chiloscyllium", "Hemiscyllium",
    "Scyliorhinus", "Hemitriakis", "Notorynchus", "Hexanchus", "Heptranchias",
    "Pristis", "Anoxypristis", "Rhynchobatus", "Rhina", "Glaucostegus",
    "Rhinobatos", "Pseudobatos", "Raja", "Leucoraja", "Amblyraja", "Dipturus",
    "Bathyraja", "Okamejei", "Dasyatis", "Hypanus", "Bathytoshia", "Neotrygon",
    "Taeniura", "Himantura", "Urobatis", "Urolophus", "Aetobatus", "Myliobatis",
    "Rhinoptera", "Mobula", "Manta", "Gymnura", "Torpedo", "Narcine", "Tetronarce",
    "Pristiophorus", "Etmopterus", "Centrophorus", "Dalatias", "Somniosus",
    "Chimaera", "Hydrolagus", "Callorhinchus", "Chlamydoselachus", "Pristiophorus",
    "Zapteryx", "Trygonorrhina", "Aptychotrema", "Narke", "Potamotrygon",
]

_COMMON_RE = re.compile("|".join(_COMMON), re.I)
_GENERA_RE = re.compile(r"\b(" + "|".join(_GENERA) + r")\b")


def is_elasmo_text(title: str, abstract: str = "") -> bool:
    """True if title/abstract mentions an elasmobranch/chondrichthyan."""
    text = f"{title or ''} {abstract or ''}"
    return bool(_COMMON_RE.search(text) or _GENERA_RE.search(text))
