# Altmetric/Dimensions: Grants & Datasets Products

## Key Finding

Altmetric itself does **not** have standalone grants/datasets products. The real power lies in **Dimensions** (same parent company, Digital Science), which is accessible free via the SRAD programme.

## Grants (via Dimensions)

### Coverage
- **7.9 million grants** indexed from major global funders
- Funders include: NIH, NSF, EU Horizon, Wellcome Trust, UKRI, ARC, DFG, BMBF, CIHR, NSERC, and hundreds more
- Also includes private foundations (Save Our Seas Foundation, Shark Conservation Fund, etc.)

### Grant Record Fields
- Title, abstract, funding amounts (multi-currency)
- Start/end dates, duration
- Investigators (PI/Co-PI roles)
- Research organisations
- Funder organisations
- SDG categories
- Research classification schemes

### Grant-to-Publication Linkage
Dimensions provides two mechanisms per publication:
1. **`funders`** field: Lists funder organisations (text-mined from acknowledgement sections + CrossRef/PubMed metadata)
2. **`supporting_grant_ids`** field: Links to specific Dimensions grant records when a grant ID can be resolved
3. **`funding_section`** field: Raw acknowledgements text

### Query Example (batch DOIs)
```
search publications where doi in ["10.1016/...", "10.1038/...", ...]
return publications[doi+funders+supporting_grant_ids+funder_countries+funding_section]
```

### Analytical Value for Our Project
1. **Funding landscape**: Which funders dominate elasmobranch research? (NIH? EU? Private conservation foundations?)
2. **Funding-technique correlation**: Does NIH funding correlate with genetics? Does EU funding correlate with movement ecology?
3. **Funding-discipline mapping**: Which of our 8 disciplines receive the most/least funding?
4. **International funding flows**: Cross-border funding patterns
5. **Funding trends over time**: Is investment growing in specific disciplines?
6. **Cost-per-paper**: For papers with grant IDs, retrieve funding amounts to estimate research efficiency

## Datasets (via Dimensions)

### Coverage
- **42 million datasets** from 1,000+ repositories
- Sources: DataCite (Zenodo, Pangaea, Dryad, Mendeley), Figshare-hosted repositories
- GBIF: **not confirmed** as indexed source

### Dataset Record Fields
- Title, description, DOI
- `associated_publication_id`: Links dataset to its parent publication
- `associated_grant_ids`: Links dataset to its funding grants
- Repository, licence, date

### Dataset-to-Publication Linkage
- One-directional: search datasets → look up associated publications
- Cannot query "show me all datasets for this DOI" directly from publications

### Query Example
```
search datasets in full_data for "shark" OR "elasmobranch"
where associated_publication_id is not empty
return datasets[basics+associated_publication_id+associated_grant_ids+license_name]
```

### Analytical Value for Our Project
1. **Data sharing practices**: What proportion of elasmobranch papers have deposited datasets?
2. **Data sharing by discipline**: Likely highest in GEN (sequence data) and MOV (tracking data), lowest in CON/FISH
3. **Data sharing trends**: Growth over time alongside journal/funder mandates
4. **Open science composite**: Combine OA status + dataset availability for a per-paper open science score
5. **Repository preferences**: Which repositories dominate (Dryad, Zenodo, Figshare, GenBank, Movebank)?

## Altmetric Grants/Datasets Features (Distinct from Dimensions)

### Grants in Altmetric Explorer
- **Filter only**: Search research outputs by funder or grant ID
- No grant records returned; grant data comes from Dimensions
- Useful for: "Show me all attention metrics for papers funded by NSF grant #12345"

### Datasets in Altmetric
- Tracked as an **output type** (like journal articles)
- Same attention metrics (tweets, news, policy, etc.) applied to datasets with DOIs
- Useful for: "Which deposited datasets got the most public attention?"

## Practical Approach

With SRAD access to both Dimensions and Altmetric:

1. **Batch query 30,500 DOIs via Dimensions** (300-400 per query, 30 req/min → ~4 min total)
   - Extract: funders, supporting_grant_ids, funder_countries, funding_section
2. **Search Dimensions datasets** for elasmobranch keywords
   - Cross-reference associated_publication_ids with our DOI list
3. **Batch query 30,500 DOIs via Altmetric** (at 2-5 req/sec → 2-4 hours)
   - Extract: attention scores, mention counts by source

### Proposed New Database Columns (Grants/Datasets)

| Column | Type | Source |
|--------|------|--------|
| funder_names | text[] | Dimensions |
| funder_countries | text[] | Dimensions |
| grant_ids | text[] | Dimensions (where available) |
| funding_amount_usd | float | Dimensions (where available) |
| has_deposited_dataset | boolean | Dimensions dataset search |
| dataset_repository | text | Dimensions |
| dataset_doi | text | Dimensions |

---

*Created: 2026-03-09*
