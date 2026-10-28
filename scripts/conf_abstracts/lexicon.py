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
    r"electric ray", r"torpedo ray", r"numbfish", r"wedgefish",
    r"shovelnose (?:ray|guitarfish|shark)",  # bare "shovelnose" flagged 18 sturgeon/salamander/catfish abstracts as elasmo (2026-10-21)
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

# Portuguese and Spanish names, added for the EBI proceedings (2026-10-28).
# Case matters for two of them: "Tubarão" is also a river and city in Santa
# Catarina (3 JMIH catfish abstracts) and "Tiburon" a place in California and
# Mexico, so the capitalised singular only counts in a hyphenated compound
# (TUBARÃO-MARTELO) and the plain singular only in lower case.
_IBERIAN = [
    r"(?i:tubar(?:ões|oes)\b)", r"(?i:tubarão-)", r"tubarão\b",
    r"(?i:tibur(?:ón|ones)\b)", r"tiburon\b",
    r"(?i:\barraias?\b)", r"(?i:\braias?\b)", r"(?i:\bcaç(?:ão|ões)\b)",
    r"(?i:elasmobr[aâ]nqu)", r"(?i:condr[ií]ct)", r"(?i:peixes?-serra)", r"(?i:\bquimeras?\b)",
]

# Family and order stems, and Neotropical genera missing above. Soares & Petean
# 2023 (Tab. S1) titles name taxa this way ("CHONDRICHTHYES, RHINOBATIDAE").
# "squaliformes" is whole-word: Squaliforma is a loricariid catfish genus.
_TAXA = [
    r"holoceph", r"rhinobat", r"dasyat", r"potamotrygon", r"myliobat", r"sphyrnid",
    r"scyliorhin", r"rajiform", r"\brajidae", r"lamniform", r"squaliformes\b", r"carcharhin",
    r"torpedinif", r"rhinopristi", r"pristiform", r"\bpristidae", r"orectolob",
    r"heterodont(?:us|idae|iform)", r"hexanch", r"squatin", r"urotrygon", r"gymnurid",
    r"narcinid", r"arhynchobat", r"triakid", r"etmopter", r"centrophor", r"pteroplatytrygon",
    r"gurgesiella", r"rioraja", r"atlantoraja", r"sympterygia", r"psammobatis", r"paratrygon",
    r"plesiotrygon", r"heliotrygon", r"styracura", r"fontitrygon",
]

_COMMON_RE = re.compile("|".join(_COMMON), re.I)
_GENERA_RE = re.compile(r"\b(" + "|".join(_GENERA) + r")\b")
_EXTRA_RE = re.compile("|".join(_IBERIAN + ["(?i:%s)" % t for t in _TAXA]))

# "ray" is the one term in _COMMON that is not diagnostic on its own: the
# ichthyology and herpetology literature is full of ray-finned fishes, fin ray
# counts, and X-ray imaging, and \bray\b matches every one of them. MEASURED
# 2026-09-04: 143 of 1,226 content-flagged elasmo records (11.7%) had NO elasmo
# evidence beyond a "ray" of this kind. Scrub those phrases before matching;
# scrubbing can only remove hits, so nothing that was non-elasmo becomes elasmo.
_RAY_NOISE = re.compile(
    r"""(?xi)
    \b (?:x|gamma|uv|cosmic|beta|alpha) [\s-]* rays? \b        # X-ray, gamma ray
  | \b rays? [\s-]* fin(?:ned|s)? \b                          # ray-finned fish
  | \b (?:fin|fins|dorsal|anal|caudal|pectoral|pelvic|soft|hard|
         branched|unbranched|segmented|procurrent|principal|median|
         gill|branchiostegal|spinous|lepidotrich(?:ia|ial)?)
    [\s-]* rays? \b                                            # fin-ray counts
  | \b rays? \s+ (?:and|or) \s+ spines? \b
  | \b spines? \s+ (?:and|or) \s+ rays? \b
  | \b synchrotron \b | \b radiograph \w* \b
  | \b \d+ \s+ rays? \b                                        # "17 to 30 rays" (2026-10-28, EBI)
  | \b scheirer [\s-]+ ray [\s-]+ hare \b                      # a rank test, not a batoid
  | \b mantas? \s+ (?:ou|e) \s+ postas? \b | \b mantas? \s+ de \s+ pirarucu \b  # salted fillet (pt)
    """)


def is_elasmo_text(title: str, abstract: str = "") -> bool:
    """True if title/abstract mentions an elasmobranch/chondrichthyan."""
    text = _RAY_NOISE.sub(" ", f"{title or ''} {abstract or ''}")
    return bool(_COMMON_RE.search(text) or _GENERA_RE.search(text) or _EXTRA_RE.search(text))
