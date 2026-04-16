# Data Source: Open Access Status

**Status:** Complete
**Team lead:** Elena Fernández-Corredor

## Purpose

Record whether each paper is freely available to readers without a paywall, and through which mechanism. Open access (OA) status affects who can read and cite a study, with implications for public engagement, parachute research dynamics, and equitable knowledge exchange. Understanding OA patterns across journals, time periods, and disciplines reveals which areas of elasmobranch research are accessible to practitioners, managers, and the public in data-poor regions.

## Data Source

[Unpaywall](https://unpaywall.org/) maintains a database of legal free-to-read versions of scholarly articles, matched by DOI. It is a non-profit service that indexes OA repositories, publisher OA journals, and hybrid OA papers.

- **Output file:** `outputs/unpaywall_oa_by_doi.csv` (16,651 rows)
- **Matching key:** `doi` (joined to main database via `literature_id`)

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `literature_id` | string | Internal paper identifier (joins to main parquet) |
| `doi` | string | Digital Object Identifier used for Unpaywall lookup |
| `oa_is_oa` | boolean | True if any legal free-to-read version exists |
| `oa_status` | string | OA route category (see below) |
| `oa_url` | string | URL of the best available free version |
| `oa_host_type` | string | Where the free version is hosted (publisher, repository, etc.) |
| `oa_license` | string | Licence applied to the free version (e.g. CC BY, CC BY-NC) |
| `oa_version` | string | Version of the free copy (submittedVersion, acceptedVersion, publishedVersion) |
| `oa_journal_is_oa` | boolean | True if the publishing journal is fully open access |
| `oa_journal_is_in_doaj` | boolean | True if the journal is listed in the Directory of Open Access Journals |

## OA Status Categories

| Status | Description |
|--------|-------------|
| `closed` | No legal free version available; paywalled |
| `gold` | Published in a fully OA journal (no subscription required) |
| `hybrid` | Published in a subscription journal but the specific article was made OA by the authors/funders paying an APC |
| `green` | Free version available in an institutional or subject repository (e.g. PubMed Central, institutional repository), but the journal itself is not OA |
| `bronze` | Free to read on the publisher's site, but without an explicit open licence (publisher-controlled; may be removed) |

## Known Issues

1. **DOI dependency:** Papers without a DOI cannot be matched. Older conference proceedings and grey literature are likely absent.
2. **Bronze instability:** Bronze OA papers are free at the time of lookup but can be moved behind a paywall without notice. Dates of retrieval should be recorded for reproducibility.
3. **Green version currency:** Repository copies are not always the final published version. The `oa_version` field distinguishes preprints, accepted manuscripts, and published versions.
4. **DOAJ coverage:** Not all legitimate OA journals are listed in DOAJ; `oa_journal_is_in_doaj = FALSE` does not mean the journal is not OA.
5. **Unpaywall update lag:** Newly published OA papers can take weeks to be indexed by Unpaywall.

## Validation

Check a stratified sample of 20–30 papers across each status category by clicking `oa_url` links to confirm they resolve to accessible content. Verify that journals known to be fully OA (e.g. *PLOS ONE*, *Frontiers in Marine Science*) are correctly classified as `gold`.

---
*Draft created: 2026-04-16*
