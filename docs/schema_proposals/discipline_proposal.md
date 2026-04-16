# Proposed Schema: Research Discipline

**Status:** Draft for team discussion
**Column prefix:** `d_`
**Team lead:** Guuske Tiktak
**Source:** Internal classification system; cross-referenced with Schiffman et al. 2020

## Purpose

Classify each paper into the research discipline(s) it represents. A paper can belong to multiple disciplines simultaneously (e.g., a study measuring movement and physiology of a captive animal would flag `d_movement`, `d_physiology`, and `d_husbandry`). Enables analyses like "how has the proportion of genetics papers grown over time?" or "which disciplines are most under-represented in the Global South?"

## Extraction Method

Search terms are matched against the **full text** of each PDF. A frequency-based scoring system is used: a column is set to `1` only when the cumulative term frequency across the document meets or exceeds the column's threshold. Higher thresholds guard against incidental mentions of discipline-adjacent terminology (e.g., a paper mentioning movement once in its introduction does not become a movement paper).

Case-sensitive terms (e.g., acronyms such as `IUCN`, `eDNA`, `MSY`) are matched exactly; all other terms use case-insensitive matching. Wildcard (`*`) terms match any suffix (e.g., `behavio*` matches both `behaviour` and `behavioral`).

## Proposed Categories

| Column | Label | Threshold | Terms | Case-sensitive |
|--------|-------|-----------|-------|----------------|
| `d_biology` | Life History & Biology | 2 | life history, age and growth, growth rate, longevity, maturity, length-at-maturity, length-weight, vertebral band | — |
| `d_behaviour` | Behaviour & Ecology | 3 | behavio\*, behavioral ecology, predator-prey, diel vertical migration, activity pattern, social behavio\*, agonistic, refuging | — |
| `d_trophic` | Trophic Ecology & Diet | 2 | trophic, diet, feeding ecology, stomach content\*, prey composition, stable isotope, fatty acid, food web | — |
| `d_genetics` | Genetics & Genomics | 2 | genetic\*, genomic\*, eDNA, environmental DNA, microsatellite, mitochondrial, phylogenet\*, haplotype, SNP, RADseq, population genetics | eDNA, SNP |
| `d_movement` | Movement & Telemetry | 3 | movement, telemetry, satellite tag\*, acoustic tag\*, archival tag\*, home range, migration, habitat use, space use, tracking | — |
| `d_fisheries` | Fisheries Science | 2 | stock assessment, fisheries management, catch data, fishing mortality, maximum sustainable yield, MSY, fishery-dependent, fishery-independent | MSY |
| `d_conservation` | Conservation Biology | 3 | conservation, endangered, CITES, IUCN, Red List, protected area, marine protected area, recovery plan, conservation status | CITES, IUCN |
| `d_data_science` | Data Science & Modelling | 2 | machine learning, deep learning, neural network, random forest, Bayesian, meta-analysis, systematic review, simulation model | — |
| `d_husbandry` | Captive Husbandry | 2 | aquarium, captive, husbandry, captive breeding, ex situ, tank-held, aquaria | — |
| `d_paleontology` | Palaeontology | 1 | fossil, paleontol\*, palaeontol\*, Cretaceous, Jurassic, Miocene, Pliocene, Eocene, Oligocene, Cenozoic, Mesozoic, Devonian, Carboniferous | — |
| `d_taxonomy` | Taxonomy & Systematics | 1 | taxonom\*, new species, sp. nov., new genus, morphometric\*, meristic\*, dichotomous key, identification key, redescription, synonymy, type specimen | — |
| `d_physiology` | Physiology | 2 | physiolog\*, metaboli\*, oxygen consumption, ventilation rate, blood gas, haematocrit, hematocrit, osmoregulat\*, thermoregulat\*, bioenergetic\* | — |
| `d_reproductive` | Reproductive Biology | 2 | reproductive biology, fecundity, gestation, embryo\*, uterine, ovipar\*, vivipar\*, mating, parturition, neonat\*, litter size, reproductive cycle | — |
| `d_biomechanics` | Biomechanics | 1 | biomechani\*, functional morphology, locomot\*, kinematics, bite force, jaw mechanics, hydrodynamic\*, swimming performance | — |
| `d_sensory` | Sensory Biology | 1 | electrorecept\*, ampullae of Lorenzini, lateral line, mechanosens\*, olfact\*, chemosens\*, visual acuity, magnetorecept\* | — |
| `d_ecotourism` | Ecotourism | 1 | ecotourism, dive tourism, shark tourism, shark watching, whale shark tourism, shark encounter, provisioning | — |
| `d_human_dimensions` | Human Dimensions | 2 | human dimension\*, social science, stakeholder, perception, attitude\*, willingness to pay, WTP, shark bite, shark attack, shark repellent | — |
| `d_immunology` | Immunology | 2 | immun\*, antibod\*, complement system, innate immun\*, adaptive immun\*, leukocyte, lymphocyte | — |
| `d_toxicology` | Toxicology & Contaminants | 2 | toxicolog\*, contaminant\*, bioaccumulation, biomagnification, heavy metal\*, mercury, methylmercury, tissue concentration | — |

## Notes on Specific Columns

**`d_biology`** — Covers life history parameters: age, growth, longevity, and size metrics. Does not overlap strongly with `d_reproductive` (which focuses on reproductive mode and cycle) or `d_physiology` (which focuses on physiological mechanisms). A paper reporting von Bertalanffy growth parameters will flag `d_biology`; a paper on osmoregulation will flag `d_physiology`.

**`d_behaviour`** — Threshold of 3 guards against papers that mention behaviour incidentally. Captures both field-based observational studies and laboratory behavioural experiments.

**`d_conservation`** — Threshold of 3 ensures that papers merely citing a species' IUCN status in passing do not receive this flag. Papers must engage substantively with conservation topics.

**`d_data_science`** — Covers methodological papers that apply advanced computational or statistical methods. Includes meta-analyses and systematic reviews, which synthesise literature rather than generating new field data.

**`d_movement`** — Threshold of 3 avoids false positives from papers that mention migration or tracking in passing. The term list covers all common telemetry modalities.

**`d_paleontology`** — Threshold of 1: any mention of geological epochs or fossil material is sufficient given the specificity of the terms.

**`d_sensory`** — Threshold of 1: all terms are highly discipline-specific (e.g., `ampullae of Lorenzini` has essentially no non-sensory usage).

**`d_taxonomy`** — Threshold of 1: terms such as `sp. nov.` and `type specimen` are unambiguous. High prevalence (22% of corpus) reflects the large number of descriptive taxonomic papers in elasmobranch literature.

**`d_husbandry`** — Threshold of 2 avoids papers that merely mention aquariums in a general context (e.g., public display statistics in a conservation paper).

## Validation

Individual paper classifications can be reviewed at:

```
https://simondedman.github.io/elasmo_analyses/validate/{openalex_id}.html
```

Replace `{openalex_id}` with the paper's OpenAlex identifier (e.g., `W2164874137`). The validation page shows the extracted evidence — matched terms, their frequencies, and the section of the document in which they appeared — for all schema columns.

## Known Issues

1. **`d_paleontology` (9.6% prevalence):** Geological epoch names (e.g., "Miocene", "Cretaceous") appear in biogeographic and evolutionary biology papers that are not primarily palaeontological. Review of flagged papers suggested the prevalence is broadly correct and these epoch references reflect genuine palaeontological content or explicit evolutionary context.

2. **`d_husbandry` (4.9% prevalence):** A small number of false positives arise from captive-experiment physiology or behaviour papers that are not primarily about husbandry practice. This is acceptable given that such papers do involve captive animals.

3. **`d_taxonomy` (22.1% prevalence):** High apparent prevalence is expected given the volume of taxonomic and morphological description papers in the elasmobranch literature, particularly for older decades. Threshold-1 columns are most susceptible to false positives; spot-checks are recommended when subsetting for this discipline.

4. **Multi-discipline papers:** Disciplines are not mutually exclusive by design. A genetics paper studying population structure of a commercially important species will correctly flag `d_genetics`, `d_fisheries`, and `d_conservation`. Analysts should be aware that column sums will exceed 100% of the paper count.

---
*Draft created: 2026-04-16*
