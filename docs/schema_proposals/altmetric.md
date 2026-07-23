# Data Source: Altmetric Attention Scores

**Status:** Complete (2026-03-17)
**Team lead:** David Shiffman

## Purpose

Measure the online attention each paper has received beyond traditional citation counts. Altmetric collates mentions from Twitter/X, news outlets, policy documents, Wikipedia, Reddit, blogs, Facebook, and peer-review platforms, producing a composite Altmetric Attention Score (AAS). This enables questions such as: which research topics attract public attention, whether open-access papers receive more social coverage, and how elasmobranch research is discussed outside academia.

## Data Source

[Altmetric](https://www.altmetric.com/) collects online mentions of scholarly outputs by DOI. API access was approved via the Scholarly Research Assistance and Data (SRAD) programme in March 2026. The API key is stored in `memory/reference_altmetric_api.md`.

- **Script:** `scripts/enrich_altmetric.py`
- **Output file:** `outputs/altmetric_scores.csv`
- **Coverage:** 10,897 papers with Altmetric records (65.5 % hit rate across the full database)

Papers without an Altmetric record receive no score; a score of zero isn't assigned — the row is simply absent from the output file.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `alt_score` | float | Overall Altmetric Attention Score (composite) |
| `alt_tweeters` | integer | Unique Twitter/X accounts that mentioned the paper |
| `alt_posts` | integer | Total Twitter/X posts |
| `alt_fbwalls` | integer | Facebook wall posts |
| `alt_blogs` | integer | Blog posts mentioning the paper |
| `alt_news` | integer | News outlet mentions |
| `alt_policy` | integer | Policy document mentions |
| `alt_wikipedia` | integer | Wikipedia article mentions |
| `alt_reddit` | integer | Reddit posts |
| `alt_peer_review` | integer | F1000/peer-review platform mentions |
| `alt_mendeley` | integer | Mendeley reader count (proxy for academic readership) |
| `alt_pct_journal` | float | Percentile rank within the same journal |
| `alt_pct_all` | float | Percentile rank across all outputs tracked by Altmetric |
| `alt_pct_similar_age` | float | Percentile rank among outputs of similar age |

## Score Bins

For descriptive summaries and figures, the composite AAS is grouped into six categories:

| Bin label | Score range | Interpretation |
|-----------|-------------|----------------|
| Minimal | < 1 | Little or no online attention |
| Low | 1–9 | Modest attention, primarily academic sharing |
| Moderate | 10–49 | Noticeable online presence |
| High | 50–99 | Broad coverage, likely news or policy mention |
| Very high | 100–499 | Major public attention |
| Exceptional | ≥ 500 | Viral or landmark paper |

## Known Issues

1. **Hit rate variation by era:** Altmetric coverage drops steeply for papers published before 2012, when social media uptake in academia was low. Pre-2012 papers with zero social trace will be absent from the output.
2. **Twitter/X data gaps:** Post-2023 tweet counts may be incomplete owing to API access changes following ownership change of the platform.
3. **DOI dependency:** Papers without a DOI (primarily older conference proceedings) can't be matched to Altmetric records.
4. **Mendeley reader count:** Represents library saves rather than full reads; it's a readership proxy, not a citation count.
5. **Score inflation for controversy:** A high AAS doesn't necessarily indicate scientific impact; controversial or sensational papers can score highly on social media without peer uptake.

## Validation

Cross-check a sample of high-scoring papers against the Altmetric website (https://www.altmetric.com/explorer/) to confirm field mapping. Verify that `alt_pct_all` values are plausible (most papers in a niche field will fall below the 50th percentile of all scholarly outputs).

---
*Draft created: 2026-04-16*
