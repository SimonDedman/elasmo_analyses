#!/usr/bin/env python3
"""The topic register for topic review: one topic per discipline column, with the pressure, impact,
and gear columns that belong with it. Writes data/topic_review/<id>.json for every topic that has no
file yet (an existing file, such as fisheries.json with David's 66 proposals, is never overwritten;
pass --force to rewrite the generated ones), and docs/topic_review/topics.js, the landing page's list.

    python3 scripts/topic_review_topics.py [--force] [--dry-run]

Assignments were drafted 2026-10-06 (Simon: "all 18"). A column may sit in more than one topic:
light, noise and electromagnetic pressures matter to behaviour, sensory and physiology alike. The three
geography topics (habitat eco_, ocean basins b_, sub-basins sb_) have no discipline column and no
champion yet; Simon asked for them anyway ("even if they'll be messy").

ORDER is the landing-page order, in five groups, proposed 2026-10-06 from Simon's sketch "ecology,
behavioural biology, biology, cons&mgt, ecotourism, fisheries, toxicology, data science"; Biology and
Human interactions reordered to his numbers the same day.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402

GROUPS = {
    "Ecology": ["trophic", "movement", "habitat", "basins", "subbasins"],
    "Behavioural biology": ["behaviour", "sensory"],
    "Biology": ["taxonomy", "paleontology", "biology", "physiology", "biomechanics", "reproductive", "genetics", "immunology"],
    "Human interactions": ["conservation", "fisheries", "husbandry", "ecotourism", "human_dimensions", "toxicology"],
    "Methods": ["data_science"],
}
ORDER = [t for g in GROUPS.values() for t in g]
GROUP_OF = {t: g for g, ts in GROUPS.items() for t in ts}

TOPICS = [
    # id, title, discipline column (or first column, for the geography topics), attached columns
    ("fisheries", "Fisheries", "d_fisheries", None),   # defined by hand in fisheries.json
    ("habitat", "Habitat and ecosystems", "eco_coastal", "PREFIX:eco_"),
    ("basins", "Ocean basins", "b_north_atlantic", "PREFIX:b_"),
    ("subbasins", "Sub-basins and seas", "sb_north_sea", "PREFIX:sb_"),
    ("biology", "Biology and life history", "d_biology", ["imp_growth", "imp_size_structure"]),
    ("behaviour", "Behaviour", "d_behaviour",
     ["imp_behaviour_change", "pr_pollution_noise", "pr_light", "pr_electromagnetic", "pr_visual_disturbance"]),
    ("trophic", "Trophic ecology", "d_trophic", ["imp_trophic"]),
    ("genetics", "Genetics and genomics", "d_genetics", ["imp_genetic"]),
    ("movement", "Movement and spatial ecology", "d_movement", ["imp_distribution"]),
    ("conservation", "Conservation and management", "d_conservation",
     ["pr_climate_change", "pr_habitat_loss", "pr_cumulative", "pr_invasive", "pr_seabed_disturbance",
      "imp_abundance", "imp_biomass", "imp_distribution", "imp_habitat_quality", "imp_biodiversity",
      "imp_community_composition", "imp_size_structure", "imp_productivity"]),
    ("data_science", "Data science and methods", "d_data_science", []),
    ("husbandry", "Husbandry and aquaria", "d_husbandry", ["pr_aquaculture"]),
    ("paleontology", "Palaeontology", "d_paleontology", []),
    ("taxonomy", "Taxonomy and systematics", "d_taxonomy", []),
    ("physiology", "Physiology", "d_physiology",
     ["pr_hypoxia", "pr_ocean_acidification", "pr_light", "pr_electromagnetic", "pr_pollution_noise",
      "imp_physiology_stress", "imp_injury", "imp_growth"]),
    ("reproductive", "Reproductive biology", "d_reproductive", ["imp_reproduction"]),
    ("biomechanics", "Biomechanics", "d_biomechanics", []),
    ("sensory", "Sensory biology", "d_sensory",
     ["pr_light", "pr_electromagnetic", "pr_pollution_noise", "pr_visual_disturbance"]),
    ("ecotourism", "Ecotourism", "d_ecotourism", ["pr_tourism", "pr_visual_disturbance"]),
    ("human_dimensions", "Human dimensions", "d_human_dimensions",
     ["pr_tourism", "pr_shipping", "pr_depredation", "imp_economic", "imp_social"]),
    ("immunology", "Immunology and disease", "d_immunology", ["pr_disease"]),
    ("toxicology", "Toxicology and pollution", "d_toxicology",
     ["pr_pollution_chemical", "pr_pollution_plastic", "imp_contamination"]),
]


def all_columns():
    return {c.name for s in X.ALL_SCHEMAS for c in s.columns}


def prefix_columns(prefix):
    return [c.name for s in X.ALL_SCHEMAS if s.prefix == prefix for c in s.columns]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="rewrite generated topic files (never fisheries.json)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    known = all_columns()
    ddir = ROOT / "data" / "topic_review"
    ddir.mkdir(parents=True, exist_ok=True)
    register, written = [], []
    for tid, title, dcol, attached in TOPICS:
        path = ddir / f"{tid}.json"
        if attached is None:
            t = json.load(open(path))
            register.append({"id": tid, "title": t["title"], "champion": t.get("champion"), "discipline": dcol,
                             "n_live": len(t["live_columns"]), "n_proposed": len(t.get("proposed_rules", [])),
                             "order": ORDER.index(tid), "group": GROUP_OF[tid]})
            continue
        if isinstance(attached, str) and attached.startswith("PREFIX:"):
            cols = prefix_columns(attached.split(":", 1)[1])   # every column of the schema; the "discipline" is just the first
            geo = True
        else:
            cols = [dcol] + attached
            geo = False
        bad = [c for c in cols if c not in known]
        if bad:
            sys.exit(f"{tid}: unknown columns {bad}")
        featured = cols[:4]   # quotations are built for featured rules only (file size); the discipline column first
        t = {"id": tid, "title": title, "champion": "(unassigned)", "discipline": dcol, "geography": geo,
             "provenance": f"generated by scripts/topic_review_topics.py on {time.strftime('%Y-%m-%d')}; live_columns read "
                           "from scripts/extract_schema_columns.py at build time; no proposed rules yet (a champion's keyword "
                           "workbook would add them as for fisheries)",
             "live_columns": cols, "proposed_rules": [], "featured": featured}
        register.append({"id": tid, "title": title, "champion": t["champion"], "discipline": dcol,
                         "n_live": len(cols), "n_proposed": 0, "order": ORDER.index(tid), "group": GROUP_OF[tid], "geography": geo})
        if path.exists() and not args.force:
            continue
        if not args.dry_run:
            json.dump(t, open(path, "w"), indent=1, ensure_ascii=False)
        written.append(tid)
    reg_path = ROOT / "docs" / "topic_review" / "topics.js"
    existing = {}
    if reg_path.exists():   # keep per-topic build summaries that build_topic_review_pages.py merges in
        try:
            existing = {t["id"]: t for t in json.loads(reg_path.read_text().split("=", 1)[1].strip().rstrip(";"))["topics"]}
        except Exception:
            existing = {}
    for r in register:
        r.update({k: v for k, v in existing.get(r["id"], {}).items() if k.startswith("built") or k.startswith("papers_") or k == "n_rules"})
    if not args.dry_run:
        reg_path.write_text("window.TR_TOPICS = " + json.dumps({"topics": register, "generated": time.strftime("%Y-%m-%d %H:%M %Z")},
                                                              ensure_ascii=False) + ";\n")
    print(f"{len(register)} topics; wrote {len(written)}: {', '.join(written) or 'none'}; register {reg_path.relative_to(ROOT)}")
    for r in sorted(register, key=lambda r: r["order"]):
        print(f"  {r['order']+1:2d} {r['group']:20s} {r['id']:18s} {r['n_live']:3d} live cols  {r['title']}")


if __name__ == "__main__":
    main()
