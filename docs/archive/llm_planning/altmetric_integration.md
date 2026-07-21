# Altmetric Integration Analysis

## Overview

[Altmetric](https://www.altmetric.com/) tracks online attention to scholarly research across social media, news, policy documents, and other non-academic channels. Integration would add a societal impact dimension to our academic citation data.

## What Altmetric Tracks Per Paper

### High-Impact Sources
| Source | Score Weight | Notes |
|--------|-------------|-------|
| News | 8 | Tiered by outlet reach |
| Blog | 5 | |
| Podcast | 5 | |
| Policy document | 3 | Government/NGO policy |
| Clinical guideline | 3 | |
| Patent | 3 | |
| Wikipedia | 3 | Capped at 3 total |

### Social/Community Sources
| Source | Score Weight | Notes |
|--------|-------------|-------|
| X/Twitter | 0.25 | |
| Bluesky | 0.25 | |
| Facebook | 0.25 | Curated public pages only |
| Reddit | 0.25 | |
| YouTube | 0.25 | |
| Peer review | 1 | Publons, PubPeer |
| F1000 | 1 | |
| Syllabi | 1 | Open Syllabus |

### Also Available (not scored)
- Mendeley reader counts
- Dimensions citation counts
- PMC/publisher download counts
- Demographic breakdowns (who is sharing: discipline, status, geography)

## API Access

### Authentication
- **All requests require an API key** (since November 2025)
- No unauthenticated tier available

### Endpoints
- Query by DOI: `GET https://api.altmetric.com/v1/doi/{DOI}?key={KEY}`
- Query by PMID: `GET https://api.altmetric.com/v1/pmid/{PMID}?key={KEY}`
- Returns JSON with attention score, mention counts by source, citation metadata

### Free Access: SRAD Programme

The **Scientometric Research Access to Data (SRAD)** programme provides free access to university-affiliated researchers.

**Eligibility:** University-affiliated, non-commercial, published research
**What it provides:**
- Altmetric Explorer access (search up to 25,000 identifiers, CSV export)
- Details Page API, Counts Only (mention counts per source)
- Details Page API, Full Access (no rate limits, user counts and post data)

**Duration:** 6-month term
**Application:** [Request form](https://www.altmetric.com/our-audience/researchers/research-access/request-researcher-access/)
**Response time:** Up to 30 business days

### Rate Limits
| Access Level | Rate Limit |
|-------------|-----------|
| Counts Only key | No limits on Counts endpoint |
| Full Access (SRAD) | No rate limits |

### Bulk Query Feasibility (30,500 DOIs)

With SRAD Full Access:
- At 2 req/sec: ~4.2 hours
- At 5 req/sec: ~1.7 hours
- Many papers will return 404 (not tracked) — especially older/niche papers
- This itself is an interesting finding (what *doesn't* get attention)

### R Package
```r
library(rAltmetric)  # rOpenSci
result <- altmetrics(doi = "10.1038/465860a")
df <- altmetric_data(result)
```

## Usage Restrictions

| Restriction | Detail |
|------------|--------|
| Bulk redistribution | Prohibited without written approval |
| Attribution | Must credit Altmetric on any page displaying data |
| Publication | Include acknowledgement in papers |
| SRAD term | 6 months maximum |
| X/Twitter data | Max 1.5M post IDs per 30 days |

## Integration Value for EEA Project

### What Altmetric adds to us:
1. **Societal attention scores** — which papers/disciplines/techniques reach the public
2. **News coverage** — which shark research gets journalist attention
3. **Policy citations** — which papers influence policy documents (high conservation relevance)
4. **Social media reach** — public engagement patterns by topic
5. **Citation vs. attention gap** — the core novel analysis

### Proposed New Database Columns

| Column | Type | Source |
|--------|------|--------|
| altmetric_score | integer | Composite attention score |
| altmetric_news_count | integer | News outlet mentions |
| altmetric_blog_count | integer | Blog mentions |
| altmetric_policy_count | integer | Policy document citations |
| altmetric_twitter_count | integer | X/Twitter mentions |
| altmetric_reddit_count | integer | Reddit mentions |
| altmetric_wikipedia_count | integer | Wikipedia citations |
| altmetric_mendeley_readers | integer | Mendeley reader count |
| altmetric_fetched_date | date | When data was retrieved |

### Key Analyses Enabled

1. **Discipline attention profiles** — which of our 8 disciplines get most public attention?
2. **Technique visibility** — do papers using certain methods get more/less attention?
3. **Species charisma effect** — do papers on "charismatic" species (great white, whale shark) get disproportionate attention?
4. **Conservation impact** — do policy-cited papers cluster in specific disciplines?
5. **Geographic attention bias** — do papers from certain countries get more media coverage?
6. **Temporal attention trends** — is public interest in shark science growing?

### Action Items

1. **Apply for SRAD immediately** — 30 business day review period
2. Frame application: "Scientometric study of attention patterns across 30,500 elasmobranch research papers classified by analytical method and discipline"
3. While waiting: test with small batch using basic API key
4. Plan incremental save (JSON/SQLite) for the bulk query

---

*Created: 2026-03-09*
