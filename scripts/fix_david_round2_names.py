"""Fix the badly-named files from the first pass and handle FAO report parts."""

import os
import re
import shutil
from pathlib import Path

SHARK_PAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
DAVID_DIR = Path("/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/database/others_libraries/David/papers_DRG_round2")


def sanitise_title(title: str, max_words: int = 8, max_len: int = 60) -> str:
    """Create a filename-safe title fragment."""
    title = re.sub(r'[^\w\s-]', '', title)
    words = title.split()[:max_words]
    result = " ".join(words)
    return result[:max_len].strip()


def first_surname(authors: str) -> str:
    """Extract first author surname from author string like 'Surname, I. & ...'"""
    # Handle "De Oliveira, C.D.L." style
    m = re.match(r"([A-Za-zÀ-ÿ' -]+?),", authors)
    if m:
        surname = m.group(1).strip()
        # Convert spaces to camelCase for filename: "De Oliveira" -> "DeOliveira"
        parts = surname.split()
        return "".join(parts)
    return authors.split()[0] if authors else "Unknown"


def has_multiple_authors(authors: str) -> bool:
    return "&" in authors


def make_name(authors: str, year: int, title: str) -> str:
    surname = first_surname(authors)
    etal = ".etal" if has_multiple_authors(authors) else ""
    title_frag = sanitise_title(title)
    return f"{surname}{etal}.{year}.{title_frag}.pdf"


# Mapping: (current bad path relative to SHARK_PAPERS) -> (correct name, year)
# Built from parquet metadata lookup

renames = {
    # Springer papers with journal-name authors
    "2024/Aquatic.etal.2024.Aquatic Sciences 2024 86106.pdf":
        ("Pasti.etal.2024.Trophic relationships 13 small medium-sized elasmobranchs Central", 2024,
         "Pasti, A.T. et al."),
    "2023/Bulletin.etal.2023.Bulletin of Environmental Contamination and Toxicology 2023.pdf":
        ("Dutton.etal.2023.Mercury Concentrations Whale Shark Rhincodon typus Embryo Muscle", 2023,
         "Dutton, J. et al."),
    "2024/Marine.etal.2024.Marine Biology 2024 171209.pdf":
        ("Paez.etal.2024.potential influence photoperiod temperature male reproductive", 2024,
         "Paez, W.L. et al."),
    "2024/Archives.etal.2024.Archives of Environmental Contamination and Toxicology 2024.pdf":
        ("Rechimont.etal.2024.Hg Se Muscle Liver Blue Shark Prionace glauca", 2024,
         "Rechimont, M.E. et al."),
    "2023/Environ.etal.2023.Environ Biol Fish 2023 10615291538.pdf":
        ("Conan.etal.2023.Occurrence endangered whitespotted eagle ray Aetobatus narinari", 2023,
         "Conan, A. et al."),
    "2023/Environ.etal.2023.Environ Biol Fish 2023 10617671784.pdf":
        ("Bravo-Ormaza.etal.2023.Scalloped hammerhead shark Sphyrna lewini relative abundance", 2023,
         "Bravo-Ormaza, E. et al."),
    "2024/Environ.etal.2024.Environ Biol Fish 2024 107237248.pdf":
        ("Motta.etal.2024.Initial effects expansion enforcement subtropical marine reserve", 2024,
         "Motta, F.S. et al."),
    "2024/Environ.etal.2024.Environ Biol Fish 2024 1074757.pdf":
        ("Orlov.etal.2024.Eastward journey second capture first genetically confirmed record", 2024,
         "Orlov, A.M. & Orlova, S.Y."),
    "2025/Environ.etal.2025.Environ Biol Fish 2025 108691698.pdf":
        ("Pate.2025.Evidence reproductive feeding habitat manta rays Floridas Atlantic", 2025,
         "Pate, J."),  # single author
    "2025/Environ.etal.2025.Environ Biol Fish 2025 10817631782.pdf":
        ("Palmeira-Nunes.etal.2025.Salinity-driven habitat use marine-estuarine batoids Amazon Coast", 2025,
         "Palmeira-Nunes, A.R.O. et al."),
    "2024/Martha.etal.2024.Hydrobiologia 2024 85139433961.pdf":
        ("Rincon-Diaz.etal.2024.From gaps consideration framework prioritizing trophic studies", 2024,
         "Rincón-Díaz, M.P. et al."),
    "2023/Molecular.etal.2023.Molecular Biology Reports 2023 5032053215.pdf":
        ("Eustache.etal.2023.Characterization 35 new microsatellite markers blacktip reef shark", 2023,
         "Eustache, K.B. et al."),
    "2024/Rev.etal.2024.Rev Fish Biol Fisheries 2024 34703729.pdf":
        ("Orlov.etal.2024.Uninvited guests permanent residents long-term changes distribution", 2024,
         "Orlov, A.M. & Volvenko, I.V."),
    "2024/Rev.etal.2024.Rev Fish Biol Fisheries 2024 34869893.pdf":
        ("OConnell.etal.2024.global review white shark Carcharodon carcharias parturition", 2024,
         "O'Connell, C.P. et al."),
    "2024/Rev.etal.2024.Rev Fish Biol Fisheries 2024 3411011112.pdf":
        ("MurilloRendgifo.etal.2024.Determining species composition shark fin trade Singapore", 2024,
         "Murillo Rengifo, N. et al."),
    "2024/Rev.etal.2024.Rev Fish Biol Fisheries 2024 3417331742.pdf":
        ("Rabbani.etal.2024.What about meat uncovering unseen trade meat endangered sharks", 2024,
         "Rabbani, G. et al."),
    "2024/Syst.etal.2024.Syst Parasitol 2024 10118.pdf":
        ("Panchah.etal.2024.Two new species Scyphophyllidium Cestoda Phyllobothriidea Chaenogaleus", 2024,
         "Panchah, H.K. & Haseli, M."),
    "2025/Acta.etal.2025.Acta Parasitologica 2025 7065.pdf":
        ("Panchah.etal.2025.Scyphophyllidium garshai Grey Sharpnose Shark", 2025,
         "Panchah, H.K. & Haseli, M."),
    "2023/Journal.etal.2023.Patterns and trends in scientific production on marine.pdf":
        ("DeOliveira.etal.2023.Patterns trends scientific production marine elasmobranchs", 2023,
         "De Oliveira, C.D.L. et al."),
    "2024/Marine.etal.2024.Marine Biodiversity 2024 5475.pdf":
        ("McDavitt.etal.2024.New iEcology records range extension clown wedgefish Rhynchobatus", 2024,
         "McDavitt, M.T. & Simeon, B.M."),
    "2024/Thalassas.etal.2024.Thalassas An International Journal of Marine Sciences 2024.pdf":
        ("Estupinan-Montano.etal.2023.Albinism Galapagos Shark Carcharhinus galapagensis", 2023,
         "Estupiñán-Montaño, C. et al."),  # Note: actually 2023 paper in 2024 volume
    "2024/Thalassas.etal.2024.Thalassas An International Journal of Marine Sciences 2024_2.pdf":
        ("Mejia.etal.2024.Estimating Total Precaudal Lengths Main Shark Species", 2024,
         "Mejia, D. & Briones-Mendoza, J."),
}

# Also need to handle:
# 2010/United.etal.2010.IUCN... → this is from the FAO report, not year 2010
# 1948/Edited.etal.1948... → FAO report part 1, not 1948
# 1937/Unknown.etal.1937... → FAO report part 10, not 1937

# FAO report parts that got moved to wrong years - move back to David's folder
fao_misplaced = [
    "1948/Edited.etal.1948.The global status of sharks rays.pdf",
    "1937/Unknown.etal.1937.untitled.pdf",
    "2010/United.etal.2010.IUCN Species Survival Commission Shark Specialist Group Duba.pdf",
]

print("=" * 70)
print("PHASE 1: Move FAO report parts back to David's folder")
print("=" * 70)

for rel_path in fao_misplaced:
    src = SHARK_PAPERS / rel_path
    if src.exists():
        # Determine original name
        if "1948" in rel_path:
            orig = "2024-024-En_part_1.pdf"
        elif "1937" in rel_path:
            orig = "2024-024-En_part_10.pdf"
        elif "2010" in rel_path:
            orig = "2024-024-En_part_2.pdf"
        else:
            continue
        dest = DAVID_DIR / orig
        shutil.move(str(src), str(dest))
        print(f"  Restored: {rel_path} → {orig}")
    else:
        print(f"  NOT FOUND: {rel_path}")

# Clean up empty year dirs
for d in ["1948", "1937"]:
    p = SHARK_PAPERS / d
    if p.exists() and not list(p.iterdir()):
        p.rmdir()
        print(f"  Removed empty dir: {d}/")

print()
print("=" * 70)
print("PHASE 2: Rename badly-named Springer papers")
print("=" * 70)

for old_rel, (new_stem, year, authors) in renames.items():
    src = SHARK_PAPERS / old_rel
    new_name = f"{new_stem}.pdf"
    dest = SHARK_PAPERS / str(year) / new_name

    if src.exists():
        # Handle the Thalassas 2023 paper which needs to move from 2024/ to 2023/
        dest_dir = SHARK_PAPERS / str(year)
        dest_dir.mkdir(exist_ok=True)

        if dest.exists():
            new_name = f"{new_stem}_2.pdf"
            dest = dest_dir / new_name

        shutil.move(str(src), str(dest))
        print(f"  {old_rel}")
        print(f"    → {year}/{new_name}")
    else:
        print(f"  NOT FOUND: {old_rel}")

print()
print("=" * 70)
print("PHASE 3: Current state of David's folder")
print("=" * 70)

remaining = sorted(DAVID_DIR.glob("*.pdf"))
print(f"\n{len(remaining)} files remaining:")
for f in remaining:
    print(f"  {f.name}")
