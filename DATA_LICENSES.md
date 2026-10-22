# Data licences: what Shark Oracle may redistribute

Shark Oracle's own code is licensed under the [Apache License 2.0](LICENSE). Its own data, documentation, and figures are licensed under [CC BY 4.0](LICENSE-DATA). Material from other sources keeps its own terms, listed below. Before adding a field from a new source, add a row here.

**Redistribute?** Yes = included in public releases. Limited = included only as described. No = never released, whatever the licence of the surrounding file.

| Component | Licence or handling | Redistribute? | Basis |
|---|---|---|---|
| Project code (Python, R, JavaScript) | Apache 2.0 | Yes | The project's own work |
| Schemas, technique taxonomy, extraction rules, prompts, documentation, figures | CC BY 4.0 | Yes | The project's own work |
| Derived classifications and provenance (labels, confidence, method, reviewer decisions), keyed by DOI or record identifier | CC BY 4.0 | Yes | The project's own work |
| Bibliographic metadata from OpenAlex and Crossref | Redistribute, naming the source | Yes | OpenAlex is CC0; Crossref treats bibliographic metadata as facts (CC0). Abstracts stay under publisher or author copyright |
| Shark-References record fields (citation and findspot strings, curated fields) | Not in bulk until the editors agree in writing; releases are keyed by DOI and Shark-References ID meanwhile | Limited | Site terms allow reproduction with acknowledgement but don't address bulk reuse; EU database right (Directive 96/9/EC, Art. 7) |
| Supporting excerpts (the evidence table) | At most 200 characters each, with a cap per paper, served through the rate-limited query service only, never as a bulk download | Limited | Elsevier's text-mining FAQ permits snippets of up to 200 characters with a DOI link |
| Conference-abstract text | Only where the society grants permission; otherwise metadata and derived tags only | Limited | AES reserves all rights; no reuse statement found for the other meeting series |
| Full text and PDFs | Never redistributed | No | Publisher copyright |
| Altmetric scores | Not redistributed; Altmetric's own badge, or written approval | No | Altmetric Researcher Access is for non-commercial internal research |
| SCImago journal ranks | Not redistributed without written authorisation | No | SCImago Lab legal notice |
| IUCN Red List | Category codes only | Limited | Redistributing Red List data needs IUCN's prior written permission |
| Inferred gender, origin, and ethnicity (NamSor, Genderize, gender-guesser) | Never per named person; aggregates only, with small-cell suppression, labelled as estimates | No (per person) | NamSor terms Art. 2; Genderize terms; GDPR Article 9 |
| Sharkipedia values | CC BY 4.0, citing the 2022 Zenodo snapshot (10.5281/zenodo.6656525) | Yes | Snapshot licence |
| Biodiversity Heritage Library scans | Per item: public domain, or CC BY-NC-SA 4.0 for in-copyright items; BHL metadata CC0 | Limited | BHL copyright page |
| Semantic Scholar fields | ODC-BY with attribution if from the bulk datasets; the API terms are stricter | Limited | To confirm which route the pipeline used |
| Natural Earth | Public domain | Yes | No conditions |

Source: the licence review of 14 September 2026, adopted by Simon Dedman on 21 October 2026.
