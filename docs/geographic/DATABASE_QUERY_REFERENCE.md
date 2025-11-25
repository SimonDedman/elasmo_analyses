# Database Query Reference Guide

**Database**: `database/technique_taxonomy.db`
**Last Updated**: 2025-11-24
**Purpose**: Quick reference for analyzing shark research papers with geographic data

---

## Quick Start

### Connect to Database

**Python**:
```python
import sqlite3
conn = sqlite3.connect('database/technique_taxonomy.db')
cursor = conn.cursor()
```

**Command line**:
```bash
sqlite3 database/technique_taxonomy.db
```

---

## Table Overview

| Table | Records | Purpose |
|-------|---------|---------|
| `extraction_log` | 12,240 | Main paper metadata (title, year, author, species, techniques) |
| `paper_geography` | 6,183 | Geographic metadata (author country, institution, Global North/South) |
| `institutions` | 5,689 | Unique institutions with countries |
| `researchers` | 9,446 | Author records (country field ready for population) |
| `literature_review` | 0 | Detailed study location schema (empty - Phase 4) |

---

## Common Queries

### 1. Geographic Analysis

**Papers by country (top 20)**:
```sql
SELECT first_author_country, COUNT(*) as papers,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1), 1) as percentage
FROM paper_geography
WHERE first_author_country IS NOT NULL
GROUP BY first_author_country
ORDER BY papers DESC
LIMIT 20;
```

**Global North vs South**:
```sql
SELECT first_author_region, COUNT(*) as papers,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1), 1) as percentage
FROM paper_geography
WHERE first_author_region IS NOT NULL
GROUP BY first_author_region;
```

**Coverage statistics**:
```sql
SELECT
  (SELECT COUNT(*) FROM extraction_log) as total_papers,
  (SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1) as papers_with_country,
  ROUND((SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1) * 100.0 /
        (SELECT COUNT(*) FROM extraction_log), 1) as coverage_pct;
```

### 2. Institution Analysis

**Top institutions overall**:
```sql
SELECT p.first_author_institution, i.country, COUNT(*) as papers
FROM paper_geography p
JOIN institutions i ON p.first_author_institution = i.institution_name
GROUP BY p.first_author_institution, i.country
ORDER BY papers DESC
LIMIT 20;
```

**Top institutions by country**:
```sql
SELECT i.country, i.institution_name, COUNT(p.paper_id) as papers
FROM institutions i
JOIN paper_geography p ON i.institution_name = p.first_author_institution
WHERE i.country = 'USA'  -- Change country here
GROUP BY i.country, i.institution_name
ORDER BY papers DESC
LIMIT 10;
```

**Institutions with most papers (minimum 10 papers)**:
```sql
SELECT i.institution_name, i.country, COUNT(p.paper_id) as papers
FROM institutions i
JOIN paper_geography p ON i.institution_name = p.first_author_institution
GROUP BY i.institution_name, i.country
HAVING COUNT(p.paper_id) >= 10
ORDER BY papers DESC;
```

### 3. Combined Paper + Geography Queries

**Papers with full metadata (title, author, country, institution)**:
```sql
SELECT e.paper_id, e.title, e.year, e.first_author,
       p.first_author_country, p.first_author_institution, p.first_author_region
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_author_country = 1
ORDER BY e.year DESC;
```

**US papers from 2020-2024**:
```sql
SELECT e.paper_id, e.title, e.year, e.first_author, p.first_author_institution
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.first_author_country = 'USA'
  AND e.year BETWEEN 2020 AND 2024
ORDER BY e.year DESC;
```

**Global South papers with species information**:
```sql
SELECT e.paper_id, e.title, e.year, e.first_author,
       p.first_author_country, e.species
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.first_author_region = 'Global South'
  AND e.species IS NOT NULL
ORDER BY e.year DESC;
```

### 4. Temporal Analysis

**Papers by country and year**:
```sql
SELECT p.first_author_country, e.year, COUNT(*) as papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_author_country = 1
  AND e.year >= 2000  -- Last 25 years
GROUP BY p.first_author_country, e.year
ORDER BY p.first_author_country, e.year;
```

**Geographic diversity over time**:
```sql
SELECT e.year, COUNT(DISTINCT p.first_author_country) as countries_represented
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_author_country = 1
GROUP BY e.year
ORDER BY e.year;
```

**Global North/South trends by year**:
```sql
SELECT e.year, p.first_author_region, COUNT(*) as papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.first_author_region IS NOT NULL
GROUP BY e.year, p.first_author_region
ORDER BY e.year, p.first_author_region;
```

### 5. Data Quality Queries

**Papers missing geographic data**:
```sql
SELECT e.paper_id, e.filename, e.year, e.first_author, e.title
FROM extraction_log e
LEFT JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.paper_id IS NULL
ORDER BY e.year DESC;
```

**Papers with author but no institution**:
```sql
SELECT p.paper_id, p.first_author_country
FROM paper_geography p
WHERE p.first_author_country IS NOT NULL
  AND p.first_author_institution IS NULL;
```

**Institution name variations (for deduplication)**:
```sql
SELECT institution_name, country, COUNT(*) as occurrences
FROM (
    SELECT first_author_institution as institution_name, first_author_country as country
    FROM paper_geography
    WHERE first_author_institution IS NOT NULL
)
GROUP BY institution_name, country
HAVING occurrences > 1
ORDER BY occurrences DESC;
```

---

## Useful Aggregations for Abstract/Presentation

### Summary Statistics for Abstract

```sql
-- Total coverage
SELECT
    COUNT(*) as total_papers,
    SUM(CASE WHEN has_author_country = 1 THEN 1 ELSE 0 END) as papers_with_country,
    ROUND(SUM(CASE WHEN has_author_country = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as coverage_pct
FROM (
    SELECT DISTINCT e.paper_id,
           COALESCE(p.has_author_country, 0) as has_author_country
    FROM extraction_log e
    LEFT JOIN paper_geography p ON e.paper_id = p.paper_id
);

-- Top 3 countries with percentages
SELECT first_author_country, COUNT(*) as papers,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1), 1) as percentage
FROM paper_geography
WHERE first_author_country IS NOT NULL
GROUP BY first_author_country
ORDER BY papers DESC
LIMIT 3;

-- Global North/South breakdown
SELECT first_author_region, COUNT(*) as papers,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM paper_geography WHERE has_author_country = 1), 1) as percentage
FROM paper_geography
WHERE first_author_region IS NOT NULL
GROUP BY first_author_region;
```

**Output** (as of 2025-11-24):
```
Total papers: 12,240
Papers with country: 6,183 (50.5%)

Top 3 countries:
  USA        2,137 papers (34.6%)
  Australia    849 papers (13.7%)
  UK           708 papers (11.5%)

Global North: 5,485 papers (88.7%)
Global South:   698 papers (11.3%)
```

### Export Data for Figures

**Country distribution (for bar chart)**:
```sql
SELECT first_author_country, COUNT(*) as papers
FROM paper_geography
WHERE first_author_country IS NOT NULL
GROUP BY first_author_country
ORDER BY papers DESC;
```

**Save to CSV**:
```bash
sqlite3 -header -csv database/technique_taxonomy.db \
  "SELECT first_author_country, COUNT(*) as papers FROM paper_geography WHERE first_author_country IS NOT NULL GROUP BY first_author_country ORDER BY papers DESC;" \
  > outputs/country_distribution.csv
```

**Regional analysis (for pie chart)**:
```sql
SELECT first_author_region, COUNT(*) as papers
FROM paper_geography
WHERE first_author_region IS NOT NULL
GROUP BY first_author_region;
```

**Top 10 institutions (for horizontal bar chart)**:
```sql
SELECT i.institution_name, i.country, COUNT(p.paper_id) as papers
FROM institutions i
JOIN paper_geography p ON i.institution_name = p.first_author_institution
GROUP BY i.institution_name, i.country
ORDER BY papers DESC
LIMIT 10;
```

---

## Advanced Queries

### Multi-Country Collaboration (Phase 4 - Future)

When study location data is populated:

```sql
-- Parachute research: papers where author country != study country
SELECT e.paper_id, e.title, e.year,
       p.first_author_country as author_country,
       p.study_country,
       p.first_author_institution
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.is_parachute_research = 1
ORDER BY e.year DESC;
```

```sql
-- Global North authors studying Global South locations
SELECT p.first_author_country as author_country,
       p.study_country,
       COUNT(*) as papers
FROM paper_geography p
WHERE p.first_author_region = 'Global North'
  AND p.has_study_location = 1
  AND p.study_country IN (
      -- Global South countries
      SELECT DISTINCT first_author_country FROM paper_geography
      WHERE first_author_region = 'Global South'
  )
GROUP BY p.first_author_country, p.study_country
ORDER BY papers DESC;
```

### Species-Geography Analysis

```sql
-- Which countries study which species most?
SELECT p.first_author_country, e.species, COUNT(*) as papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_author_country = 1
  AND e.species IS NOT NULL
GROUP BY p.first_author_country, e.species
HAVING COUNT(*) >= 5
ORDER BY p.first_author_country, papers DESC;
```

### Technique-Geography Analysis

```sql
-- Geographic distribution of research techniques
SELECT p.first_author_country, e.techniques, COUNT(*) as papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_author_country = 1
  AND e.techniques IS NOT NULL
GROUP BY p.first_author_country, e.techniques
ORDER BY p.first_author_country, papers DESC;
```

---

## Data Export Scripts

### Export to CSV for R/Python Analysis

**All papers with geography**:
```bash
sqlite3 -header -csv database/technique_taxonomy.db \
  "SELECT e.*, p.first_author_country, p.first_author_institution, p.first_author_region
   FROM extraction_log e
   JOIN paper_geography p ON e.paper_id = p.paper_id
   WHERE p.has_author_country = 1;" \
  > outputs/papers_with_geography.csv
```

**Institution summary**:
```bash
sqlite3 -header -csv database/technique_taxonomy.db \
  "SELECT i.institution_name, i.country, COUNT(p.paper_id) as papers
   FROM institutions i
   JOIN paper_geography p ON i.institution_name = p.first_author_institution
   GROUP BY i.institution_name, i.country
   ORDER BY papers DESC;" \
  > outputs/institution_summary.csv
```

---

## Performance Tips

1. **Index usage**: Tables have indexes on primary keys and foreign keys
2. **Filter early**: Use `WHERE` clauses to reduce result sets before JOINs
3. **COUNT(*) optimization**: Use subqueries for denominator in percentages
4. **EXPLAIN QUERY PLAN**: Prefix queries to see execution plan

**Example**:
```sql
EXPLAIN QUERY PLAN
SELECT p.first_author_country, COUNT(*) FROM paper_geography p GROUP BY p.first_author_country;
```

---

## Common Pitfalls

### Issue 1: NULL values in JOINs
**Problem**: LEFT JOIN returns NULLs for papers without geography
**Solution**: Use `WHERE p.has_author_country = 1` or `WHERE p.paper_id IS NOT NULL`

### Issue 2: Duplicate counting
**Problem**: Multiple affiliations per paper can inflate counts
**Solution**: Use `DISTINCT paper_id` in counts:
```sql
SELECT COUNT(DISTINCT p.paper_id) FROM paper_geography p;
```

### Issue 3: Percentage calculations
**Problem**: Integer division returns 0
**Solution**: Multiply by 100.0 (float) before division:
```sql
ROUND(COUNT(*) * 100.0 / total, 1)  -- Correct
ROUND(COUNT(*) / total * 100, 1)    -- Wrong (integer division)
```

---

## Database Schema Reference

### `paper_geography` Table

```sql
paper_id TEXT PRIMARY KEY
first_author_institution TEXT
first_author_country TEXT
first_author_region TEXT  -- 'Global North' or 'Global South'
study_country TEXT  -- (Phase 4 - not yet populated)
study_ocean_basin TEXT  -- (Phase 4 - not yet populated)
study_latitude REAL  -- (Phase 4 - not yet populated)
study_longitude REAL  -- (Phase 4 - not yet populated)
study_location_text TEXT  -- (Phase 4 - not yet populated)
has_author_country BOOLEAN  -- 1 if country data available
has_study_location BOOLEAN  -- (Phase 4)
is_parachute_research BOOLEAN  -- (Phase 4)
created_date TIMESTAMP
updated_date TIMESTAMP
```

### `institutions` Table

```sql
institution_id INTEGER PRIMARY KEY AUTOINCREMENT
institution_name TEXT UNIQUE
country TEXT
created_date TIMESTAMP
```

### `extraction_log` Table

```sql
paper_id TEXT PRIMARY KEY
filename TEXT
year INTEGER
first_author TEXT
title TEXT
species TEXT
techniques TEXT
author_country TEXT  -- (newly added)
author_institution TEXT  -- (newly added)
-- ... other columns
```

---

## Getting Help

- **Schema inspection**: `.schema table_name` in sqlite3 CLI
- **Column info**: `PRAGMA table_info(table_name);`
- **Table list**: `.tables` in sqlite3 CLI
- **Query plan**: `EXPLAIN QUERY PLAN SELECT ...;`

---

**Last Updated**: 2025-11-24
**Database Version**: v1.0 with geographic data
**Coverage**: 6,183 / 12,240 papers (50.5%)
