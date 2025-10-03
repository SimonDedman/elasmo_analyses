---
editor_options: 
  markdown: 
    wrap: 72
---

# Shark-References Automated Literature Review Workflow

## Overview

This document outlines the automated workflow for conducting systematic
literature reviews using the Shark-References database
(<https://shark-references.com>) for the EEA 2025 Data Panel project.

**Database:** Shark-References contains \>30,000 scientific references
on extant and fossil chondrichthyans (sharks, skates, rays, chimaeras)

**Primary Advantage:** All references are chondrichthyan-specific,
eliminating need for species-level filtering

------------------------------------------------------------------------

## 1. Shark-References Database Capabilities

### Search Features

#### Fulltext Search (`query_fulltext` parameter)

-   Searches entire article text (not just title/abstract)
-   **Limitation:** Database indexed with **first 3 letters only**
-   Older articles may have OCR typos affecting results
-   Downloads contain **citations only** (no article content due to
    copyright)

#### Search Operators

| Operator | Description | Example | Expected Results |
|----------------|-----------------|----------------|------------------------|
| (none) | OR logic - any keyword | `albinism pigmentation` | \>870 results |
| `+` | Keyword MUST be included | `+albinism` | \>170 results |
| `-` | Keyword excluded (requires `+` first) | `+albinism -atlantic` | \>40 results |
| `*` | Wildcard - prefix matching | `+albin*` | \>400 (albinism, albino, etc.) |
| `"..."` | Exact phrase match | `"partial albinism"` | \>40 results |
| `@distance` | Proximity search | `+albinism @10 +"deep water"` | \>50 results |

### Additional Filters

1.  **Taxonomic:**
    -   Described Genus (dropdown menu)
    -   Described Species (dropdown menu)
2.  **Temporal:**
    -   Year range (from/to)
    -   Geological time keywords (hierarchical: period → epoch → age)
    -   Use "recent" or "rezent" for extant species
3.  **Geographic:**
    -   Place keywords (fossil references only)
    -   Hierarchical structure (continent → country → state/province)
4.  **Content Type:**
    -   "Only with Download" checkbox → open access articles only
    -   "Only Figure from teeth" → tooth/denticle figures (extant only)

### Download Limitations

-   **Maximum 2000 references per download**
-   Downloads return **citation lists only** (CSV format)
-   If download fails: reload page, clear browser cache
-   Reset search mask between queries (recommended)

------------------------------------------------------------------------

## 2. Automation Strategy Assessment

### Current Access Methods

#### ✅ Available: Form-Based POST Requests

``` bash
curl -X POST "https://shark-references.com/search" \
  -d "query_fulltext=SEARCH_TERM" \
  -d "opts[]=download" \
  -d "clicked_button=export" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -o "sharkrefs_SEARCH_TERM_$(date +%Y%m%d).csv"
```

**Parameters:**
- `query_fulltext`: Search term with operators
- `query`: Title/abstract/publication title search
- `genus_described`: Genus filter
- `species_described`: Species filter
- `year_from`, `year_to`: Year range
- `kt[]`: Time keywords (array)
- `kp[]`: Place keywords (array)
- `opts[]`: Options array (`download`, `teeth`)
- `clicked_button`: `export` for download

**Algorithmic CSV Naming:**

Downloaded CSVs can be named automatically using search parameters and timestamp:

```bash
# Format: sharkrefs_{search_term}_{YYYYMMDD}.csv
# Examples:
sharkrefs_telemetry_20251003.csv
sharkrefs_edna_20251003.csv
sharkrefs_acoustic+telemetry_20251003.csv
```

**Automated naming script:**
```bash
#!/bin/bash
SEARCH_TERM="$1"
OUTPUT_FILE="sharkrefs_${SEARCH_TERM}_$(date +%Y%m%d).csv"

curl -s "https://shark-references.com/search" \
  -X POST \
  -d "query_fulltext=${SEARCH_TERM}" \
  -d "opts[]=download" \
  -d "clicked_button=export" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: text/csv" \
  -o "${OUTPUT_FILE}"

echo "Downloaded: ${OUTPUT_FILE}"
```

**Usage:**
```bash
./download_sharkrefs.sh "acoustic+telemetry"
# Creates: sharkrefs_acoustic+telemetry_20251003.csv
```

#### ✅ Available: Species-Specific CSV Export

``` bash
# Direct CSV download by species ID
curl -o output.csv "https://shark-references.com/export/literature/species/<SPECIES_ID>"
```

-   Species ID found in "remarks" on species summary page
-   Automatically downloads .csv file
-   No search operators needed

#### ❌ Not Available: Official API

-   No REST API endpoints identified
-   No API documentation on website
-   No authentication/token system visible

#### ❌ Not Available: Batch Query Interface

-   No bulk search submission
-   No programmatic rate limit information
-   Manual suggests one search at a time

### Automation Feasibility

**✅ FEASIBLE:** Scripted form submissions with delays **✅ FEASIBLE:**
CSV parsing and database integration **⚠️ CAUTIOUS:** Rate limiting
unknown - implement conservative delays **❌ NOT RECOMMENDED:**
Parallel/concurrent requests without permission

------------------------------------------------------------------------

## 3. Recommended Workflow

### Phase 1: Search Term Generation

Based on 8 refined disciplines and analytical methods:

``` python
# Example search term structure
disciplines = {
    "Biology_Health": [
        "+telomere* +aging",
        "+reproduct* +endocrin*",
        "+parasit* +disease",
        "+"stress +cortisol"
    ],
    "Behaviour_Sensory": [
        "+behav* +predation",
        "+vision +electr*",
        "+olfact* +chemorecept*",
        "+learning +cognition"
    ],
    "Trophic_Ecology": [
        "+stable +isotop*",
        "+diet +prey",
        "+trophic +level",
        "+food +web"
    ],
    "Genetics_Genomics": [
        "+population +geneti*",
        "+genom* +sequenc*",
        "+eDNA +environmental",
        "+phylogeny +molecular"
    ],
    "Movement_Spatial": [
        "+telemetry +acoustic",
        "+satellite +tracking",
        "+habitat +model*",
        "+home +range",
        "+SDM +distribution"
    ],
    "Fisheries_Management": [
        "+stock +assessment",
        "+fishery +CPUE",
        "+bycatch +discard",
        "+mortality +fishing"
    ],
    "Conservation_Policy": [
        "+conservation +status",
        "+CITES +protection",
        "+MPA +marine +protected",
        "+policy +management"
    ],
    "Data_Science": [
        "+machine +learning",
        "+random +forest",
        "+neural +network",
        "+Bayesian +model*",
        "+artificial +intelligence"
    ]
}
```

**Search Term Design Principles:** 1. Use `+` for required terms (AND
logic) 2. Use `*` for method variations (e.g., `model*` → modeling,
models, modelling) 3. Combine discipline + method (e.g.,
`+telemetry +habitat +model*`) 4. Keep searches under 2000 results
(refine if exceeded) 5. **Remember 3-letter indexing** (e.g., `+tel`
matches `telemetry`)

### Phase 2: Automated Search Execution

#### Python Script Structure

``` python
import requests
import pandas as pd
import time
from datetime import datetime

def search_shark_references(query_fulltext, year_from=None, year_to=None,
                            delay=5):
    """
    Execute search on Shark-References and return results

    Args:
        query_fulltext: Search term with operators
        year_from: Start year (optional)
        year_to: End year (optional)
        delay: Seconds between requests (default 5)

    Returns:
        requests.Response object
    """

    url = "https://shark-references.com/search"

    data = {
        "query_fulltext": query_fulltext,
        "opts[]": "download",
        "clicked_button": "export"
    }

    if year_from:
        data["year_from"] = year_from
    if year_to:
        data["year_to"] = year_to

    # Log request
    print(f"[{datetime.now()}] Searching: {query_fulltext}")

    # Execute request
    response = requests.post(url, data=data)

    # Implement delay to avoid overwhelming server
    time.sleep(delay)

    return response

def parse_csv_response(response):
    """
    Parse CSV from response content

    Returns:
        pandas.DataFrame with references
    """
    # Implementation depends on CSV format
    # May need to extract from HTML or direct CSV
    pass

def batch_search(search_terms, output_dir="./shark_refs"):
    """
    Execute batch searches across all disciplines
    """
    results = {}

    for discipline, terms in search_terms.items():
        print(f"\n=== Discipline: {discipline} ===")
        discipline_results = []

        for term in terms:
            try:
                response = search_shark_references(term)
                refs = parse_csv_response(response)
                discipline_results.append({
                    "search_term": term,
                    "references": refs,
                    "count": len(refs)
                })
            except Exception as e:
                print(f"ERROR: {term} - {e}")

        results[discipline] = discipline_results

    return results
```

#### R Script Structure

``` r
library(httr)
library(dplyr)
library(lubridate)

search_shark_references <- function(query_fulltext, year_from = NULL,
                                   year_to = NULL, delay = 5) {
  #' Execute search on Shark-References and return results
  #'
  #' @param query_fulltext Search term with operators
  #' @param year_from Start year (optional)
  #' @param year_to End year (optional)
  #' @param delay Seconds between requests (default 5)
  #' @return httr response object

  url <- "https://shark-references.com/search"

  # Prepare POST body
  body_data <- list(
    query_fulltext = query_fulltext,
    clicked_button = "export"
  )

  if (!is.null(year_from)) {
    body_data$year_from <- as.character(year_from)
  }
  if (!is.null(year_to)) {
    body_data$year_to <- as.character(year_to)
  }

  # Log request
  message(sprintf("[%s] Searching: %s", Sys.time(), query_fulltext))

  # Execute POST request
  response <- POST(
    url = url,
    body = body_data,
    encode = "form"
  )

  # Implement delay to avoid overwhelming server
  Sys.sleep(delay)

  return(response)
}

parse_csv_response <- function(response) {
  #' Parse CSV from response content
  #'
  #' @param response httr response object
  #' @return data.frame with references

  # Implementation depends on CSV format
  # May need to extract from HTML or direct CSV
  # Placeholder for now
  return(data.frame())
}

batch_search <- function(search_terms, output_dir = "./shark_refs") {
  #' Execute batch searches across all disciplines
  #'
  #' @param search_terms Named list of search terms by discipline
  #' @param output_dir Directory for outputs
  #' @return List of results by discipline

  results <- list()

  for (discipline in names(search_terms)) {
    message(sprintf("\n=== Discipline: %s ===", discipline))

    terms <- search_terms[[discipline]]
    discipline_results <- list()

    for (term in terms) {
      tryCatch({
        response <- search_shark_references(term)
        refs <- parse_csv_response(response)

        discipline_results[[length(discipline_results) + 1]] <- list(
          search_term = term,
          references = refs,
          count = nrow(refs)
        )
      }, error = function(e) {
        message(sprintf("ERROR: %s - %s", term, e$message))
      })
    }

    results[[discipline]] <- discipline_results
  }

  return(results)
}
```

### Phase 3: CSV Processing & Database Integration

#### CSV Structure (Expected Fields)

Based on typical bibliographic exports: - Author(s) - Year - Title -
Journal/Source - Volume/Issue - Pages - DOI (if available) - Keywords -
Abstract (if available)

#### Database Schema

``` sql
CREATE TABLE shark_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term VARCHAR(255),
    discipline VARCHAR(100),
    method_category VARCHAR(100),
    authors TEXT,
    year INTEGER,
    title TEXT,
    journal VARCHAR(255),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    doi VARCHAR(100),
    abstract TEXT,
    keywords TEXT,
    date_retrieved DATE,
    shark_ref_id VARCHAR(100),  -- Original Shark-Ref database ID
    UNIQUE(doi, title)  -- Prevent duplicates
);

CREATE TABLE search_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term VARCHAR(255),
    discipline VARCHAR(100),
    result_count INTEGER,
    timestamp DATETIME,
    status VARCHAR(50)
);
```

#### Integration Workflow - Python

``` python
import sqlite3
import pandas as pd
from datetime import datetime

def create_database(db_path="shark_literature.db"):
    """Initialize database with schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (SQL above)
    # Add indexes for common queries
    cursor.execute("""
        CREATE INDEX idx_discipline ON shark_references(discipline);
    """)
    cursor.execute("""
        CREATE INDEX idx_year ON shark_references(year);
    """)
    cursor.execute("""
        CREATE INDEX idx_method ON shark_references(method_category);
    """)

    conn.commit()
    return conn

def import_csv_to_db(csv_path, discipline, method, search_term, conn):
    """
    Import CSV results into database
    """
    df = pd.read_csv(csv_path)

    # Add metadata columns
    df['discipline'] = discipline
    df['method_category'] = method
    df['search_term'] = search_term
    df['date_retrieved'] = datetime.now().date()

    # Write to database (ignore duplicates)
    df.to_sql('shark_references', conn, if_exists='append',
              index=False, method='multi')

    # Log search
    log_entry = pd.DataFrame([{
        'search_term': search_term,
        'discipline': discipline,
        'result_count': len(df),
        'timestamp': datetime.now(),
        'status': 'success'
    }])
    log_entry.to_sql('search_log', conn, if_exists='append', index=False)

def deduplicate_database(conn):
    """
    Remove duplicate entries based on DOI or title
    """
    cursor = conn.cursor()

    # Keep first occurrence of each DOI/title combination
    cursor.execute("""
        DELETE FROM shark_references
        WHERE ref_id NOT IN (
            SELECT MIN(ref_id)
            FROM shark_references
            GROUP BY COALESCE(doi, ''), COALESCE(title, '')
        );
    """)

    conn.commit()
    deleted = cursor.rowcount
    print(f"Removed {deleted} duplicate entries")
```

#### Integration Workflow - R

``` r
library(RSQLite)
library(dplyr)
library(readr)

create_database <- function(db_path = "shark_literature.db") {
  #' Initialize database with schema
  #'
  #' @param db_path Path to SQLite database
  #' @return Database connection object

  conn <- dbConnect(SQLite(), db_path)

  # Create tables (using SQL schema above)
  # Add indexes for common queries
  dbExecute(conn, "
    CREATE INDEX IF NOT EXISTS idx_discipline
    ON shark_references(discipline)
  ")
  dbExecute(conn, "
    CREATE INDEX IF NOT EXISTS idx_year
    ON shark_references(year)
  ")
  dbExecute(conn, "
    CREATE INDEX IF NOT EXISTS idx_method
    ON shark_references(method_category)
  ")

  return(conn)
}

import_csv_to_db <- function(csv_path, discipline, method,
                             search_term, conn) {
  #' Import CSV results into database
  #'
  #' @param csv_path Path to CSV file
  #' @param discipline Discipline category
  #' @param method Method category
  #' @param search_term Search term used
  #' @param conn Database connection

  df <- read_csv(csv_path, show_col_types = FALSE)

  # Add metadata columns
  df <- df %>%
    mutate(
      discipline = !!discipline,
      method_category = !!method,
      search_term = !!search_term,
      date_retrieved = as.character(Sys.Date())
    )

  # Write to database (append)
  dbWriteTable(conn, "shark_references", df,
               append = TRUE, row.names = FALSE)

  # Log search
  log_entry <- data.frame(
    search_term = search_term,
    discipline = discipline,
    result_count = nrow(df),
    timestamp = as.character(Sys.time()),
    status = "success",
    stringsAsFactors = FALSE
  )
  dbWriteTable(conn, "search_log", log_entry,
               append = TRUE, row.names = FALSE)
}

deduplicate_database <- function(conn) {
  #' Remove duplicate entries based on DOI or title
  #'
  #' @param conn Database connection

  # Keep first occurrence of each DOI/title combination
  deleted <- dbExecute(conn, "
    DELETE FROM shark_references
    WHERE ref_id NOT IN (
      SELECT MIN(ref_id)
      FROM shark_references
      GROUP BY COALESCE(doi, ''), COALESCE(title, '')
    )
  ")

  message(sprintf("Removed %d duplicate entries", deleted))
}
```

### Phase 4: Google Scholar Cross-Referencing

#### Purpose

-   Verify citation counts
-   Find additional citing papers
-   Access papers not in Shark-References
-   Track recent citations (post-Shark-Ref update)

#### Implementation Options

**Option A: Manual Review** (Recommended initially) - Export
high-priority papers from database - Manual Google Scholar searches -
Document additional papers found

**Option B: Automated with `scholarly` Python package**

``` python
from scholarly import scholarly
import time

def google_scholar_lookup(title, authors=None):
    """
    Search Google Scholar for paper and get citation count

    Args:
        title: Paper title
        authors: Author list (optional, improves accuracy)

    Returns:
        dict with citation_count, scholar_url, related_papers
    """

    search_query = title
    if authors:
        search_query += f" {authors}"

    try:
        search_result = scholarly.search_pubs(search_query)
        paper = next(search_result)

        return {
            'citation_count': paper['num_citations'],
            'scholar_url': paper['pub_url'],
            'related_papers': paper.get('related', []),
            'year': paper.get('bib', {}).get('pub_year')
        }
    except StopIteration:
        return {'error': 'Not found'}
    except Exception as e:
        return {'error': str(e)}

    # Rate limiting essential
    time.sleep(10)  # Google blocks aggressive scraping

def enrich_database_with_scholar(conn, limit=None):
    """
    Add Google Scholar data to existing references
    """
    cursor = conn.cursor()

    # Get papers without Scholar data
    query = """
        SELECT ref_id, title, authors
        FROM shark_references
        WHERE citation_count IS NULL
    """
    if limit:
        query += f" LIMIT {limit}"

    refs = pd.read_sql(query, conn)

    for idx, row in refs.iterrows():
        scholar_data = google_scholar_lookup(row['title'], row['authors'])

        if 'error' not in scholar_data:
            cursor.execute("""
                UPDATE shark_references
                SET citation_count = ?,
                    scholar_url = ?
                WHERE ref_id = ?
            """, (scholar_data['citation_count'],
                  scholar_data['scholar_url'],
                  row['ref_id']))

        conn.commit()

        # Progress logging
        if idx % 10 == 0:
            print(f"Processed {idx}/{len(refs)} papers")
```

**Option B-R: Automated with `scholar` R package**

``` r
library(scholar)

google_scholar_lookup <- function(title, authors = NULL) {
  #' Search Google Scholar for paper and get citation count
  #'
  #' @param title Paper title
  #' @param authors Author list (optional)
  #' @return List with citation data

  search_query <- title
  if (!is.null(authors)) {
    search_query <- paste(search_query, authors)
  }

  tryCatch({
    # Note: scholar package has limited functionality
    # May need to use custom web scraping with rvest

    # Placeholder - actual implementation requires careful scraping
    result <- list(
      citation_count = NA,
      scholar_url = NA,
      error = "Not implemented - use Semantic Scholar API instead"
    )

    return(result)

  }, error = function(e) {
    return(list(error = e$message))
  })

  # Rate limiting essential
  Sys.sleep(10)
}

enrich_database_with_scholar <- function(conn, limit = NULL) {
  #' Add Google Scholar data to existing references
  #'
  #' @param conn Database connection
  #' @param limit Maximum number of papers to process

  # Get papers without Scholar data
  query <- "
    SELECT ref_id, title, authors
    FROM shark_references
    WHERE citation_count IS NULL
  "

  if (!is.null(limit)) {
    query <- paste(query, sprintf("LIMIT %d", limit))
  }

  refs <- dbGetQuery(conn, query)

  for (i in seq_len(nrow(refs))) {
    row <- refs[i, ]

    scholar_data <- google_scholar_lookup(row$title, row$authors)

    if (is.null(scholar_data$error)) {
      dbExecute(conn, "
        UPDATE shark_references
        SET citation_count = ?,
            scholar_url = ?
        WHERE ref_id = ?
      ", params = list(
        scholar_data$citation_count,
        scholar_data$scholar_url,
        row$ref_id
      ))
    }

    # Progress logging
    if (i %% 10 == 0) {
      message(sprintf("Processed %d/%d papers", i, nrow(refs)))
    }
  }
}
```

**⚠️ Caution:** Google Scholar has rate limits and blocks automated
scraping - Implement long delays (10+ seconds) - Consider using
institutional proxy - May require CAPTCHA solving - Alternative: Use
Semantic Scholar API (more permissive)

------------------------------------------------------------------------

## 4. Alternative: Semantic Scholar API

**Why Semantic Scholar?** - Free academic API - No authentication
required for basic use - 100 requests/5 minutes (rate limit) - Provides
citation context, influential citations - Better for programmatic access
than Google Scholar

### Python Implementation

``` python
import requests

def semantic_scholar_lookup(title=None, doi=None):
    """
    Lookup paper on Semantic Scholar

    Args:
        title: Paper title
        doi: DOI (more reliable than title)

    Returns:
        Paper metadata with citations
    """

    if doi:
        url = f"https://api.semanticscholar.org/v1/paper/{doi}"
    else:
        # Search by title
        url = f"https://api.semanticscholar.org/v1/paper/search"
        params = {'query': title, 'limit': 1}
        response = requests.get(url, params=params)
        if response.json()['total'] == 0:
            return {'error': 'Not found'}
        paper_id = response.json()['data'][0]['paperId']
        url = f"https://api.semanticscholar.org/v1/paper/{paper_id}"

    response = requests.get(url)
    return response.json()

# Example usage
result = semantic_scholar_lookup(doi="10.1111/jfb.12345")
print(f"Citations: {result.get('numCitations', 0)}")
print(f"Influential citations: {result.get('numInfluentialCitations', 0)}")
```

### R Implementation

``` r
library(httr)
library(jsonlite)

semantic_scholar_lookup <- function(title = NULL, doi = NULL) {
  #' Lookup paper on Semantic Scholar
  #'
  #' @param title Paper title
  #' @param doi DOI (more reliable than title)
  #' @return List with paper metadata and citations

  if (!is.null(doi)) {
    url <- sprintf("https://api.semanticscholar.org/v1/paper/%s", doi)

    response <- GET(url)

    if (status_code(response) == 200) {
      return(content(response, "parsed"))
    } else {
      return(list(error = "Not found"))
    }

  } else if (!is.null(title)) {
    # Search by title
    url <- "https://api.semanticscholar.org/v1/paper/search"

    response <- GET(url, query = list(query = title, limit = 1))

    if (status_code(response) != 200) {
      return(list(error = "Search failed"))
    }

    search_result <- content(response, "parsed")

    if (search_result$total == 0) {
      return(list(error = "Not found"))
    }

    paper_id <- search_result$data[[1]]$paperId
    url <- sprintf("https://api.semanticscholar.org/v1/paper/%s", paper_id)

    response <- GET(url)
    return(content(response, "parsed"))

  } else {
    stop("Must provide either title or doi")
  }
}

# Example usage
result <- semantic_scholar_lookup(doi = "10.1111/jfb.12345")
cat(sprintf("Citations: %d\n", result$numCitations %||% 0))
cat(sprintf("Influential citations: %d\n",
            result$numInfluentialCitations %||% 0))
```

------------------------------------------------------------------------

## 5. Complete Workflow Summary

### Step-by-Step Process

1.  **Preparation** (Week 1)
    -   Finalize discipline-method search terms matrix
    -   Set up Python/R environment with required packages
    -   Create database schema
    -   Test single search manually to verify CSV format
2.  **Batch Search Execution** (Week 2-3)
    -   Run automated searches for each discipline
    -   Implement 5-10 second delays between requests
    -   Log all searches and result counts
    -   Handle errors gracefully (retry logic)
    -   Monitor for searches exceeding 2000 results (refine terms)
3.  **CSV Processing** (Week 3)
    -   Parse all downloaded CSVs
    -   Import to SQLite/PostgreSQL database
    -   Deduplicate based on DOI/title
    -   Generate summary statistics by discipline
4.  **Quality Control** (Week 3-4)
    -   Manual review of sample results per discipline
    -   Verify search term effectiveness
    -   Identify gaps requiring additional searches
    -   Refine search terms if needed
5.  **Citation Enrichment** (Week 4) - OPTIONAL
    -   Use Semantic Scholar API for citation counts
    -   Identify highly-cited papers (\>100 citations)
    -   Flag recent papers (last 2-3 years) for tracking
6.  **Expert Review Preparation** (Week 4-5)
    -   Export discipline-specific reference lists
    -   Generate summary reports (top papers, method trends)
    -   Prepare for expert panel evaluation

### Deliverables

1.  **SQLite Database:** All references with metadata
2.  **Search Log:** Complete audit trail
3.  **Summary Reports:** Per discipline
    -   Total references found
    -   Top 20 most-cited papers
    -   Method frequency analysis
    -   Temporal trends (papers/year)
4.  **Expert Packages:** Reference lists for each panelist

------------------------------------------------------------------------

## 6. Technical Requirements

### Software Dependencies

**Python:**

``` bash
pip install requests pandas sqlite3 scholarly beautifulsoup4
```

**R (Alternative):**

``` r
install.packages(c("httr", "jsonlite", "RSQLite", "dplyr"))
```

### System Requirements

-   Storage: \~500MB for database (estimated 10,000 refs)
-   Processing: Standard laptop sufficient
-   Network: Stable connection for batch requests

### Ethical Considerations

-   **Respect robots.txt** (check
    <https://shark-references.com/robots.txt>)
-   **Conservative rate limiting** (5-10 sec delays)
-   **Contact database maintainers** if errors occur
-   **Acknowledge Shark-References** in publications
-   **No redistribution** of copyrighted content

------------------------------------------------------------------------

## 7. Risk Mitigation

### Potential Issues & Solutions

| Risk | Likelihood | Impact | Mitigation |
|----------------|-------------------|----------------|---------------------|
| IP blocking from excessive requests | Medium | High | Implement 10-sec delays, monitor response codes |
| CSV format changes | Low | Medium | Parse flexibly, log unexpected formats |
| Search results exceed 2000 | Medium | Low | Auto-refine with year ranges or additional terms |
| Database contains duplicates | High | Low | Deduplication script post-import |
| Missing DOIs for citation lookup | High | Medium | Use title-based search as fallback |
| Google Scholar blocking | High | High | Use Semantic Scholar API instead |
| Incomplete coverage of methods | Medium | Medium | Expert review + manual gap filling |

### Contingency Plan

If automated approach fails: 1. **Fallback to semi-automated:** - Manual
search term entry - Scripted CSV download and processing - Maintain
database integration

2.  **Fallback to manual:**
    -   Expert-identified key papers
    -   Forward/backward citation chaining
    -   Targeted Shark-References searches

------------------------------------------------------------------------

## 8. Next Steps

### Immediate Actions

1.  ✅ **Test single search manually**
    -   Navigate to <https://shark-references.com/search>
    -   Enter test query: `+telemetry +acoustic`
    -   Click Download button
    -   Inspect CSV format and fields
2.  **Develop proof-of-concept script**
    -   Single automated search → CSV download
    -   Parse CSV into pandas DataFrame
    -   Insert into test database
3.  **Contact Shark-References maintainers**
    -   Email:
        [info\@shark-references.com](mailto:info@shark-references.com){.email}
    -   Explain project scope and automated search intent
    -   Request permission or guidance
    -   Ask about rate limits and best practices
4.  **Refine search term matrix**
    -   Review with discipline experts
    -   Test term effectiveness on Shark-Ref
    -   Adjust based on result counts

### Timeline Integration

Aligns with EEA 2025 Data Panel preparation timeline: - **Weeks 1-2:**
Setup and testing - **Weeks 2-3:** Batch execution - **Weeks 3-4:**
Processing and QC - **Weeks 4-5:** Expert distribution

------------------------------------------------------------------------

## 9. Contact Information

**Shark-References Database:** - Website:
<https://shark-references.com> - Email:
[info\@shark-references.com](mailto:info@shark-references.com){.email} -
Manual:
<https://shark-references.com/images/meine_bilder/downloads/Manual_Advanced_Search_Shark_references_english_version.pdf> -
Institution: Zoologische Staatssammlung München (ZSM)

**Technical Support:** - ResearchGate manual:
<https://www.researchgate.net/publication/395261929>

------------------------------------------------------------------------

## Appendix A: Example Search Terms by Discipline

### 1. Biology, Life History, & Health

```         
+reproduct* +matur*
+growth +age
+telomere* +aging
+stress +physiol*
+parasit* +disease
+endocrin* +hormone
+metabol* +energetic*
```

### 2. Behaviour & Sensory Ecology

```         
+behav* +predation
+vision +visual
+electr* +sensory
+olfact* +chemosens*
+magnet* +navigation
+social +aggregation
+learning +cognition
```

### 3. Trophic & Community Ecology

```         
+stable +isotop*
+diet +prey
+trophic +level
+food +web
+stomach +content
+energy +flow
+niche +partition*
```

### 4. Genetics, Genomics, & eDNA

```         
+population +geneti*
+genom* +sequenc*
+eDNA +environmental
+phylogeny +molecular
+microsatellite +SNP
+transcriptom* +gene
+conservation +genetic*
```

### 5. Movement, Space Use, & Habitat Modeling

```         
+telemetry +acoustic
+satellite +tracking
+habitat +model*
+home +range
+SDM +distribution
+spatial +ecology
+migration +movement
+circuit* +connectivity
```

### 6. Fisheries, Stock Assessment, & Management

```         
+stock +assessment
+fishery +CPUE
+bycatch +discard*
+mortality +fishing
+catch +per +unit
+surplus +production
+harvest +strategy
```

### 7. Conservation Policy & Human Dimensions

```         
+conservation +status
+CITES +protection
+MPA +marine +protected
+policy +management
+stakeholder +community
+ecosystem +service*
+human +dimension*
```

### 8. Data Science & Integrative Methods

```         
+machine +learning
+random +forest
+neural +network
+Bayesian +model*
+AI +artificial
+ensemble +model*
+data +integration
+GAM +generalized
```

------------------------------------------------------------------------

## Appendix B: Database Query Examples

### Most-Cited Papers by Discipline

``` sql
SELECT discipline, title, authors, year, citation_count
FROM shark_references
WHERE citation_count IS NOT NULL
ORDER BY discipline, citation_count DESC
LIMIT 20;
```

### Method Frequency Analysis

``` sql
SELECT method_category, COUNT(*) as paper_count
FROM shark_references
GROUP BY method_category
ORDER BY paper_count DESC;
```

### Temporal Trends

``` sql
SELECT year, discipline, COUNT(*) as papers
FROM shark_references
WHERE year >= 2000
GROUP BY year, discipline
ORDER BY year DESC, papers DESC;
```

### Papers by Multiple Disciplines (Cross-Cutting)

``` sql
SELECT title, GROUP_CONCAT(DISTINCT discipline) as disciplines, COUNT(*) as hits
FROM shark_references
GROUP BY title
HAVING COUNT(DISTINCT discipline) > 1
ORDER BY hits DESC;
```

### Recent Papers for Expert Review

``` sql
SELECT discipline, title, authors, year, journal
FROM shark_references
WHERE year >= 2020
ORDER BY discipline, year DESC;
```
